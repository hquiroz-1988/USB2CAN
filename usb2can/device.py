"""8devices USB2CAN driver on top of WinUSB.

The protocol is ported from the Linux kernel driver
drivers/net/can/usb/usb_8dev.c (copy in vendor/linux/usb_8dev.c).
"""
import collections
import queue
import struct
import threading
import time
from dataclasses import dataclass

from . import winusb

VID, PID = 0x0483, 0x1234
CLOCK_HZ = 32_000_000

EP_DATA_IN, EP_DATA_OUT, EP_CMD_IN, EP_CMD_OUT = 0x81, 0x02, 0x83, 0x04

# Commands
CMD_RESET = 1   # reboots the MCU without re-enumerating USB: unplug/replug needed after
CMD_OPEN = 2
CMD_CLOSE = 3
CMD_SET_SPEED = 4
CMD_SET_MASK_FILTER = 5
CMD_GET_STATUS = 6
CMD_GET_STATISTICS = 7
CMD_GET_SERIAL = 8
CMD_GET_SOFTW_VER = 9
CMD_GET_HARDW_VER = 10
CMD_RESET_TIMESTAMP = 11
CMD_GET_SOFTW_HARDW_VER = 12

CMD_START, CMD_END = 0x11, 0x22
BAUD_MANUAL = 0x09

# CMD_OPEN flags
FLAG_SILENT = 0x01
FLAG_LOOPBACK = 0x02
FLAG_DISABLE_AUTO_RESTRANS = 0x04
FLAG_STATUS_FRAME = 0x08

# Data messages
DATA_START, DATA_END = 0x55, 0xAA
TYPE_CAN_FRAME, TYPE_ERROR_FRAME = 0, 3
MSG_EXTID, MSG_RTR, MSG_ERR = 0x01, 0x02, 0x04

CMD_MSG = struct.Struct(">BBBBB10sB")   # begin channel command opt1 opt2 data[10] end
TX_MSG = struct.Struct(">BBIB8sB")      # begin flags id dlc data[8] end
RX_MSG = struct.Struct(">BBBIB8sIB")    # begin type flags id dlc data[8] timestamp end

RX_SLOTS = 64       # reads kept queued on the data-in pipe (~7 ms of frames at full rate)

# Firmware 1.7 breaks down near its limits: the receive path stalls near its
# ~9,000 frames/s ceiling, and at 6,000 frames/s it once hung completely.
# Standard-only soaks ran clean at 3,000 and 4,500 frames/s (docs/FINDINGS.md),
# so send() paces itself to 3,000 by default.
DEFAULT_MAX_TX_RATE = 3000
RX_BUFFER = 64      # one full-speed bulk packet: up to 3 messages

STATUS_NAMES = {
    0x00: "ok", 0x01: "overrun", 0x02: "warning (errors >= 96)",
    0x03: "error passive (errors >= 128)", 0x04: "bus off",
    0x20: "stuff error", 0x21: "form error", 0x23: "ack error",
    0x24: "bit1 error", 0x25: "bit0 error", 0x27: "crc error",
}


class ProtocolError(Exception):
    pass


class CommandError(Exception):
    def __init__(self, command, code):
        super().__init__(f"command {command} failed with code {code}")
        self.command, self.code = command, code


@dataclass
class Frame:
    id: int
    data: bytes = b""
    extended: bool = False
    rtr: bool = False
    dlc: int | None = None          # defaults to len(data)
    timestamp: int | None = None    # device clock, received frames only

    def __post_init__(self):
        self.data = bytes(self.data)
        if self.dlc is None:
            self.dlc = len(self.data)

    def __str__(self):
        ident = f"{self.id:08X}" if self.extended else f"{self.id:03X}"
        body = "remote request" if self.rtr else self.data.hex(" ").upper()
        return f"{ident}  [{self.dlc}]  {body}"


@dataclass
class BusStatus:
    code: int
    rx_errors: int
    tx_errors: int
    rx_passive: bool
    timestamp: int

    @property
    def name(self):
        return STATUS_NAMES.get(self.code, f"unknown 0x{self.code:02x}")

    def __str__(self):
        return f"{self.name}  rx_errors={self.rx_errors}  tx_errors={self.tx_errors}"


@dataclass(frozen=True)
class BitTiming:
    """CAN bit timing in time quanta of brp / 32 MHz."""
    brp: int        # 1..1024
    tseg1: int      # prop_seg + phase_seg1, 1..16
    tseg2: int      # phase_seg2, 1..8
    sjw: int = 1    # 1..4

    def __post_init__(self):
        if not (1 <= self.brp <= 1024 and 1 <= self.tseg1 <= 16
                and 1 <= self.tseg2 <= 8 and 1 <= self.sjw <= 4):
            raise ValueError(f"bit timing out of range: {self}")

    @property
    def bitrate(self):
        return CLOCK_HZ / (self.brp * (1 + self.tseg1 + self.tseg2))

    @property
    def sample_point(self):
        return (1 + self.tseg1) / (1 + self.tseg1 + self.tseg2)

    @classmethod
    def from_bitrate(cls, bitrate, sample_point=0.875):
        """Exact timing for this bitrate, closest to the sample point,
        preferring more time quanta per bit."""
        best = None
        for ntq in range(25, 2, -1):
            brp, rem = divmod(CLOCK_HZ, bitrate * ntq)
            if rem or not 1 <= brp <= 1024:
                continue
            for tseg2 in range(1, 9):
                tseg1 = ntq - 1 - tseg2
                if not 1 <= tseg1 <= 16:
                    continue
                err = round(abs((1 + tseg1) / ntq - sample_point), 6)
                if best is None or err < best[0]:
                    best = (err, cls(brp, tseg1, tseg2, sjw=max(1, min(4, tseg2 // 2))))
        if best is None:
            raise ValueError(f"no exact bit timing for {bitrate} bit/s from a 32 MHz clock")
        return best[1]


def list_devices():
    """Serial numbers of the USB2CAN devices bound to WinUSB."""
    return [serial for serial, _ in winusb.find_devices(VID, PID)]


class USB2CAN:
    """One USB2CAN converter.

        with USB2CAN() as dev:
            dev.start(500_000)
            dev.send(Frame(0x123, b"\\x01\\x02"))
            frame = dev.recv(timeout=1.0)
    """

    def __init__(self, serial=None):
        devices = winusb.find_devices(VID, PID)
        if serial is not None:
            devices = [d for d in devices if d[0].upper() == serial.upper()]
        if not devices:
            raise FileNotFoundError(
                f"no USB2CAN{' ' + serial if serial else ''} found bound to WinUSB")
        self.serial, path = devices[0]
        self._usb = winusb.WinUsbDevice(path)
        try:
            for ep in (EP_CMD_IN, EP_CMD_OUT, EP_DATA_OUT):
                self._usb.set_policy(ep, winusb.PIPE_TRANSFER_TIMEOUT, 1000)
            # Hand reads straight to the USB stack: lowest latency with
            # several reads queued. Needs buffers sized in whole packets.
            self._usb.set_policy(EP_DATA_IN, winusb.RAW_IO, 1, size=1)
        except Exception:
            self._usb.close()
            raise
        self._cmd_lock = threading.Lock()
        self._tx_lock = threading.Lock()
        self._rx = queue.Queue(maxsize=100_000)
        self._reader = None
        self._reader_error = None
        self._stopping = False
        self._slots = []
        self.running = False
        self.timing = None
        self.max_tx_rate = DEFAULT_MAX_TX_RATE
        self._next_tx = 0.0
        self.bus_status = None
        self.status_log = collections.deque(maxlen=256)   # recent BusStatus messages
        self.stats = dict(rx_frames=0, rx_transfers=0, tx_frames=0, status_msgs=0,
                          rx_dropped=0, rx_starved=0, framing_errors=0, unknown_msgs=0)

    # -- commands ------------------------------------------------------

    def command(self, command, opt1=0, opt2=0, data=b""):
        """Send a command and return the 10 data bytes of the reply."""
        msg = CMD_MSG.pack(CMD_START, 0, command, opt1, opt2, bytes(data).ljust(10, b"\0"), CMD_END)
        with self._cmd_lock:
            self._usb.write(EP_CMD_OUT, msg)
            reply = self._usb.read(EP_CMD_IN, 64)
        if len(reply) != CMD_MSG.size:
            raise ProtocolError(f"command {command}: {len(reply)}-byte reply: {reply.hex(' ')}")
        begin, _, _, result, _, rdata, end = CMD_MSG.unpack(reply)
        if begin != CMD_START or end != CMD_END:
            raise ProtocolError(f"command {command}: bad reply framing: {reply.hex(' ')}")
        if result != 0:
            raise CommandError(command, result)
        return rdata

    def version(self):
        """(firmware, hardware) version strings."""
        v = struct.unpack_from(">I", self.command(CMD_GET_SOFTW_HARDW_VER))[0]
        return f"{v >> 24 & 0xFF}.{v >> 16 & 0xFF}", f"{v >> 8 & 0xFF}.{v & 0xFF}"

    # -- channel -------------------------------------------------------

    def start(self, bitrate=500_000, *, timing=None, sample_point=0.875,
              loopback=False, silent=False, one_shot=False,
              max_tx_rate=DEFAULT_MAX_TX_RATE):
        """Open the CAN channel (LED turns steady green).

        loopback: sent frames come back as received frames.
        silent: listen only, never drive the bus (not even ACKs).
        loopback + silent: internal self-test, nothing reaches the bus.
        one_shot: do not retransmit frames that fail.
        max_tx_rate: frames/s that send() will not exceed; None = unpaced
            (risks the firmware stall, see DEFAULT_MAX_TX_RATE).
        """
        if self.running:
            raise RuntimeError("channel already started")
        t = timing or BitTiming.from_bitrate(bitrate, sample_point)
        flags = (FLAG_STATUS_FRAME
                 | (FLAG_LOOPBACK if loopback else 0)
                 | (FLAG_SILENT if silent else 0)
                 | (FLAG_DISABLE_AUTO_RESTRANS if one_shot else 0))
        self._start_reader()
        try:
            self.command(CMD_OPEN, BAUD_MANUAL, 0,
                         struct.pack(">BBBHI", t.tseg1, t.tseg2, t.sjw, t.brp, flags))
        except Exception:
            self._stop_reader()
            raise
        self.timing = t
        self.max_tx_rate = max_tx_rate
        self._next_tx = 0.0
        self.running = True

    def stop(self):
        """Close the CAN channel (LED back to steady red)."""
        if not self.running:
            return
        try:
            self.command(CMD_CLOSE)
        finally:
            self._stop_reader()
            self.running = False

    def close(self):
        """Close the channel and release the device. Doesn't raise if the
        device has stopped responding, so it can't mask the original error."""
        try:
            self.stop()
        except OSError:
            pass
        finally:
            self._usb.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    # -- data ----------------------------------------------------------

    def send(self, frame):
        """Queue one frame for transmission. Blocks to stay under
        max_tx_rate and while the device's ~70-frame transmit buffer is
        full; TimeoutError if the device accepts nothing for 1 s."""
        if not self.running:
            raise RuntimeError("channel not started")
        max_id = 0x1FFFFFFF if frame.extended else 0x7FF
        if not 0 <= frame.id <= max_id:
            raise ValueError(f"CAN id 0x{frame.id:X} out of range")
        if len(frame.data) > 8 or not 0 <= frame.dlc <= 8:
            raise ValueError("CAN frames carry at most 8 data bytes")
        flags = (MSG_EXTID if frame.extended else 0) | (MSG_RTR if frame.rtr else 0)
        msg = TX_MSG.pack(DATA_START, flags, frame.id, frame.dlc,
                          frame.data.ljust(8, b"\0"), DATA_END)
        with self._tx_lock:
            if self.max_tx_rate:
                self._pace()
            self._usb.write(EP_DATA_OUT, msg)
            self.stats["tx_frames"] += 1

    def _pace(self):
        """Wait until the next send slot. Evenly spaced, no bursts: the
        device would otherwise drain a burst at its full rate."""
        now = time.perf_counter()
        if now < self._next_tx:
            if self._next_tx - now > 0.002:
                time.sleep(self._next_tx - now - 0.001)
            while time.perf_counter() < self._next_tx:
                time.sleep(0)   # yield, so the receive thread keeps running
            now = self._next_tx
        self._next_tx = now + 1.0 / self.max_tx_rate

    def recv(self, timeout=None):
        """Next received Frame, or None after `timeout` seconds."""
        deadline = None if timeout is None else time.monotonic() + timeout
        while True:
            wait = 0.1 if deadline is None else max(0.0, min(0.1, deadline - time.monotonic()))
            try:
                return self._rx.get(timeout=wait)
            except queue.Empty:
                pass
            if self._reader_error:
                raise self._reader_error
            if deadline is not None and time.monotonic() >= deadline:
                return None

    # -- receive thread ------------------------------------------------

    def _start_reader(self):
        self._stopping = False
        self._reader_error = None
        self._rx = queue.Queue(maxsize=100_000)
        self._slots = [winusb.AsyncRead(self._usb, EP_DATA_IN, RX_BUFFER) for _ in range(RX_SLOTS)]
        for slot in self._slots:
            slot.submit()
        self._reader = threading.Thread(target=self._reader_loop, name="usb2can-rx", daemon=True)
        self._reader.start()

    def _stop_reader(self):
        self._stopping = True
        while self._reader.is_alive():
            self._usb.abort(EP_DATA_IN)
            self._reader.join(0.2)
        self._usb.abort(EP_DATA_IN)
        for slot in self._slots:
            slot.close()
        self._slots = []

    def _reader_loop(self):
        try:
            while True:
                # The pipe completes reads in the order they were queued.
                slots = self._slots
                for i, slot in enumerate(slots):
                    data = slot.wait()
                    # Reads complete in queue order: if the newest one is done
                    # too, no read was pending and the device had to hold data.
                    if slots[i - 1].done():
                        self.stats["rx_starved"] += 1
                    self._parse(data)
                    if self._stopping:
                        return
                    slot.submit()
        except OSError as e:
            if not self._stopping:
                self._reader_error = e

    def _parse(self, buf):
        size = RX_MSG.size
        self.stats["rx_transfers"] += 1
        if len(buf) % size:
            self.stats["framing_errors"] += 1
        for pos in range(0, len(buf) - size + 1, size):
            begin, typ, flags, can_id, dlc, data, ts, end = RX_MSG.unpack_from(buf, pos)
            if begin != DATA_START or end != DATA_END:
                self.stats["framing_errors"] += 1
                continue
            if typ == TYPE_CAN_FRAME:
                dlc &= 0x0F
                rtr = bool(flags & MSG_RTR)
                frame = Frame(can_id & 0x1FFFFFFF, b"" if rtr else data[:min(dlc, 8)],
                              bool(flags & MSG_EXTID), rtr, dlc, ts)
                try:
                    self._rx.put_nowait(frame)
                    self.stats["rx_frames"] += 1
                except queue.Full:
                    self.stats["rx_dropped"] += 1
            elif typ == TYPE_ERROR_FRAME and flags == MSG_ERR:
                self.bus_status = BusStatus(data[0], data[1] & 0x7F, data[2], bool(data[1] & 0x80), ts)
                self.status_log.append(self.bus_status)
                self.stats["status_msgs"] += 1
            else:
                self.stats["unknown_msgs"] += 1
