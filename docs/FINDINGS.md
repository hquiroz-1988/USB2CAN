# Findings

Investigation of the 8devices USB2CAN on Windows 11 (build 26300), 2026-10-16.
Device: serial ED000200, firmware 1.7, hardware 1.0. Host: Python 3.12.3 64-bit, Memory Integrity on.

## Summary

- The vendor's Windows stack can't be used here. Its kernel driver is incompatible with Memory Integrity,
  and its API DLL is 32-bit only and tied to that driver.
- The device works well through Microsoft's built-in **WinUSB** driver plus a user-mode driver in Python
  (`usb2can/`), using the protocol from the Linux kernel driver.
- Performance is set by the device: a 0.3–0.75 ms round trip and at most ~9,000 frames/s.
- **Standard-only traffic is reliable** at the default rate and above: 4.25 million frames at 3,000 and
  4,500 frames/s with nothing lost, altered or reordered.
- **Firmware 1.7 breaks down near its limits.** Near ~9,000 frames/s it can stop delivering received
  frames, and at 6,000 frames/s it hung completely once. Both need a replug. The driver paces sends to
  3,000 frames/s by default.
- **Mixed standard/extended traffic is unreliable at any tested rate.** Single standard frames get lost
  (~1 per minute at 3,000/s). After seconds to minutes the device starts flagging every standard frame
  as extended until the channel is restarted. A standard frame can also overtake a queued extended one.

## 1. Vendor Windows stack

All downloads from <https://wiki.8devices.com/usb2can> are in `vendor/downloads/`, each archive extracted
into its own folder in `vendor/extracted/`. That folder exists only locally; it isn't in git.

| Item | Finding |
|---|---|
| Windows drivers v1.0.2.1 (win32, win64) | KMDF 1.9 drivers with the WDF 1.9 co-installer. The catalogs are signed by 8devices with a VeriSign certificate valid 2011-07-06 to 2012-07-06; the `.sys` files themselves are unsigned. |
| Win64 driver v1.0.2.1, 2017-02-20 package | Same driver, but the `.sys` and `.cat` are signed by *Microsoft Windows Hardware Compatibility Publisher* (attestation-signed), so Windows 11 would accept the signature. |
| Driver build | The PDB path is `c:\works\8devices\usb2can\usbsamp\sys\...\objfre_win7_amd64\...`: Microsoft's WDK 7 **usbsamp** sample, built for Win7. The INF also turns on KMDF verifier settings (`VerifierOn`, `DbgBreakOnError`). |
| Memory Integrity (HVCI) | Every driver build has an `INIT` section that is both **writable and executable**. Memory Integrity refuses to load such drivers, and it's on on this PC (`SecurityServicesRunning = 2`). We didn't install the driver to confirm; this is static analysis. |
| CANAL DLL v1.0.6 (`usb2can.dll`) | **32-bit only** (PE32). It finds the device through SetupAPI and talks to the vendor kernel driver with `DeviceIoControl`, so it can't work over WinUSB. The API is documented in `CANAL_API.pdf`. |
| Test application v1.0 | 32-bit MFC app built on the CANAL DLL; its source is included. |
| DfuSe Demo v2.2 | Intact. Includes ST's `STTub30` DFU driver (signed 2009). |
| DfuSe Demo v3.0.3 | **Truncated on 8devices' server**: two downloads gave identical files (md5 `224a92846fa841a7a7c27a12b6ced17d`) with no zip directory. |
| `dfu-util` | A Linux x86-64 ELF binary (modified by 8devices for this device), so it doesn't run on Windows. |
| Firmware images | `usb2can_1_5/1_6/1_7.dfu`. The device already runs 1.7, the latest. |
| Serial-number images | DFU EEPROM images for ED000100–ED000226. Every unit ships as ED000200, so several units on one PC need unique serials. |
| Documentation | User guide, datasheet, schematic and CANAL API PDFs. Hardware facts are collected in [PROTOCOL.md](PROTOCOL.md#device). |

Before WinUSB was attached, Windows showed the device with problem code 28 (no driver installed).

### The earlier C# attempt (2020)

The repository's first version (2020, still in git history before the WinUSB driver replaced it) was a
WinForms app (`USB2CAN/`, C# / .NET Framework 4.7.2) that called the CANAL DLL through P/Invoke. Apart
from the kernel driver being blocked on current Windows, it had three problems of its own:

- The Debug build targets **x64**, and a 64-bit process can't load the 32-bit `usb2can.dll`
  (`BadImageFormatException`).
- `CanalOpen` is declared as `long CanalOpen(ref string, long)`. C#'s `long` is 64-bit while the
  DLL's C `long` is 32-bit, and `ref string` passes a pointer to a pointer instead of the string. It
  should be `int CanalOpen(string pConfigStr, uint flags)` with `CharSet.Ansi`.
- The DLL is loaded from a hard-coded absolute path on one particular machine.

## 2. Approach: WinUSB + user-mode driver

- The Linux driver `usb_8dev.c` (mainline since Linux 3.9, by Bernd Krumboeck with 8devices' help) fully
  describes the protocol. Copies are in `vendor/linux/`.
- The device's own descriptors, read through its USB hub with `tools/dump_descriptors.py` before any
  driver was attached, match that driver exactly: one vendor-specific interface with four 64-byte bulk
  endpoints (`0x81`, `0x02`, `0x83`, `0x04`). Live string requests (manufacturer, product) failed while
  the device had no driver; the serial was answered from Windows' cache.
- WinUSB was attached through Device Manager using the built-in `winusb.inf` ("WinUsb Device"). It's
  signed by Microsoft and compatible with Memory Integrity. No custom INF or certificate is needed.
- The driver opens the device through the standard USB device interface
  (`GUID_DEVINTERFACE_USB_DEVICE`, `\\?\USB#VID_0483&PID_1234#ED000200#{a5dcbf10-...}`). It keeps 64
  overlapped reads queued on the data-in pipe in `RAW_IO` mode (the Linux driver keeps 20), and a
  receive thread parses frames into a queue.

## 3. Measurements

All in **silent loopback** unless noted, so the device both sends and receives every frame.

### Correctness
Standard, extended, remote-request and 0–8-byte frames, including ids `0x000`, `0x7FF`, `0x1FFFFFFF`,
all come back bit-exact. In runs that didn't stall, about 14,000 frames were compared bit-for-bit
(self-tests) and about 20,000 more were counted (other experiments): zero mismatches, zero lost,
zero framing errors.

### Latency (1 Mbit/s, `send()` until the frame returns from `recv()`, 500 frames)
First runs: median **741 µs**, p99 924 µs, max 1,351 µs. Later runs on the same PC: medians of 749,
366 and 294 µs, all with p99 under 1 ms. Most of this is USB full speed's 1 ms frame scheduling, and
it shifts with the PC's state. Building a frame in Python costs 1.3 µs.

### Run-to-run variation
Throughput isn't stable between runs on this PC. Unpaced 0-byte frames reached 8,916 frames/s in one
run and 6,246 in the next, within the same script. Treat single throughput numbers as ±30%.

### Bit timing on the wire
Measured from device timestamps while sending `0x555`/0-byte frames (exactly 48 bits on the wire,
including stuff bits and interframe space):

| Bitrate | Expected per frame | Measured per frame | |
|---|---|---|---|
| 10 kbit/s | 4,800 µs | 4,839 µs | 100.8%: the bit timing is correct |
| 125 kbit/s | 384 µs | 407 µs | +23 µs firmware gap |
| 500 kbit/s | 96 µs | 144 µs | +48 µs |
| 1 Mbit/s | 48 µs | 112 µs | +64 µs: the firmware limit is ~9,000 frames/s |

The firmware sends one frame at a time and adds a 25–65 µs gap after each. That's why throughput tops
out at ~9,000 frames/s for 0-byte frames and ~6,300 for 8-byte frames at 1 Mbit/s, below the bus's
theoretical 21,000 and 9,000.

### Flow control and buffering
- **Transmit:** at 10 kbit/s the first 71 `send()` calls returned at once, and later ones waited for room.
  So the device buffers about 70 frames, then holds off USB transfers until it has space. Nothing was lost.
- **Several sends in flight** (1, 2, 4, 8 or 16 overlapped writes) barely helped, 6,300 → 6,800 frames/s,
  so the firmware is the bottleneck, not the PC.
- **Receive:** the firmware sends almost always one frame per USB packet (2,000 frames in 1,999
  transfers), even though a packet could carry three.
- **Timestamps:** 1,007 ticks/s against the PC clock, so milliseconds. They count from power-up and
  RESET_TIMESTAMP doesn't change them.

### Commands
See the command table in [PROTOCOL.md](PROTOCOL.md#commands-ep-0x04--reply-on-ep-0x83). Notable: OPEN while
already open is accepted, CLOSE while closed succeeds, GET_SERIAL returns ASCII, GET_STATISTICS has a
frame counter in its first u32, and RESET reboots the MCU without USB re-enumeration.

### Error reporting (normal mode, nothing connected, 500 kbit/s)
- One-shot send: a single status message, `stuff error, rx_errors=1, tx_errors=0`.
- With automatic retransmission, within 0.5 s: `stuff error` (rx 1) → `warning` (rx 99) →
  `error passive` (rx 127). The transmit counter stayed 0. A second `send()` was still accepted (buffered).
- CLOSE then OPEN in loopback worked normally afterwards, and the stuck frames weren't sent.
- The stuff errors (instead of ACK errors) fit an unterminated, floating bus: there's no 120 Ω to pull
  the lines back to recessive.

## 4. Firmware reliability

Four failure modes, all in silent loopback at 1 Mbit/s with 0-byte frames:

| Failure | When | Recovery |
|---|---|---|
| Receive stall | ~9,000 frames/s (twice) | replug |
| Complete hang | 6,000 frames/s, standard frames, under 2 minutes (once) | replug |
| Standard frames flagged as extended | mixed traffic, 3,000 and 6,000 frames/s, after 0.9 s to 274 s (3 of 3 runs) | restart the channel |
| Silent frame loss | mixed traffic only: 1 in ~200,000 at 3,000/s, 1 in 30,000 at 6,000/s | none needed |

### Receive stall

**Symptom:** the device stops sending anything on the data-in endpoint (`0x81`), including status
messages, and doesn't resume. Commands and sends keep working.

| | Stall 1 | Stall 2 |
|---|---|---|
| Traffic | 0-byte standard frames, random ids, 1 Mbit/s, sent as fast as the device accepted them (overlapped writes, 1 in flight) | Same frames sent through `send()` without pacing (`tools/selftest.py`, before pacing existed) |
| Earlier in the same session | 5,000 8-byte frames fine | 3,000 8-byte frames fine (plus earlier probe runs) |
| Returned before the stall | 1,652 of 5,000 | 2,014 of 3,000 |
| Queued reads on the PC | 16 | 64 |
| Moments with no read queued (`rx_starved`) | not measured | **0** |

The average send rate in both runs (10,100 and 9,600 frames/s) was higher than the device can actually
transmit, because sending speeds up once the firmware stops handling received frames. So the stall began
at the device's natural maximum, about 9,000 frames/s.

**Runs at similar rates that did not stall:** 5,000 random 0-byte frames at 8,800/s, 4,000 frames at
9,000/s (fixed id `0x555`), and about 13,000 8-byte frames at ~6,300/s. The bug looks like a race that
gets more likely with frame rate, not a hard threshold.

**Ruled out: the PC not reading fast enough.** During stall 2 the PC always had reads queued, but the
device sent nothing. The bug is inside the firmware.

### Recovery attempts

| Attempt | Result |
|---|---|
| CLOSE + OPEN the channel | ✗ |
| Close and reopen the WinUSB handle | ✗ |
| `WinUsb_ResetPipe(0x81)` (clear halt + data toggle) | ✗ |
| Reset all four pipes | ✗, and the next command reply was lost (data toggle not reset in firmware) |
| `SET_INTERFACE` alt 0 | ✗ (accepted, no effect) |
| RESET command (1) | ✗✗: the MCU reboots, USB doesn't re-enumerate, every transfer fails ("device not functioning") |
| **Unplug and replug** | ✓ |

Untested idea: RESET followed by a USB port cycle (`IOCTL_USB_HUB_CYCLE_PORT`, needs admin rights) might
give a software-only full recovery.

### Soak tests

`tools/selftest.py --soak`: frames carry a sequence number in their id and are sent in batches of 1,000
at the paced rate. Every received frame is identified, so the test can tell lost frames from frames
that arrived out of order.

| Pacing | Frames | Run | Result |
|---|---|---|---|
| 6,000/s | mixed standard/extended, 0-byte | 9 s (older soak code) | 39,000 frames, 1 lost (that version stopped at the first loss) |
| 6,000/s | mixed standard/extended, 0-byte | 600 s | 2,864,000 frames at 4,773/s average. **No stall.** 94 frames truly lost in 88 separate events (82 single, 6 pairs), spread evenly (~1 every 6–7 s), no status messages. From 0.9 s on, nearly every standard frame (1.43 million) came back **flagged as extended**. I first misread this as reordering; the older checker couldn't tell the two apart. |
| 6,000/s | standard only, 0-byte | 120 s planned | **Complete hang** partway through: every transfer on every pipe failed with `ERROR_GEN_FAILURE` ("A device attached to the system is not functioning"), commands included. Windows still listed the device as OK with no reconnect, the same state RESET leaves it in. The microcontroller probably crashed or rebooted without dropping off USB. |
| 3,000/s | standard only, 0-byte | 540 s (the session ended before the planned 600 s finished) | **1,603,000 frames, 0 lost, no hang**, ~2,970/s average. The case that hung at 6,000/s. |
| 4,500/s | standard only, 0-byte | 600 s | **2,654,000 frames at 4,422/s: 0 lost, 0 reordered, 0 altered, no hang.** |
| 3,000/s | mixed standard/extended, 0-byte | 600 s | 1,767,000 frames at 2,945/s. 9 truly lost. From 43.5 s on, nearly every standard frame came back flagged as extended (~820,000). |
| 3,000/s | mixed standard/extended, 0-byte | until the flag fault (capture run) | 805,000 frames. 4 single losses (at 18, 34, 257 and 273 s, all standard frames), then the flag fault at 273.8 s. An earlier attempt lost one standard frame after 2.2 s. |

A loopback loss can't be pinned to the transmit or receive side. The loss is silent either way: no
overrun or error status was reported. **Every lost frame that was identified was a standard frame,
and standard-only traffic never lost one.**

### Standard frames flagged as extended

Captured at 3,000/s with mixed traffic (frame ids carry a sequence number):

```
SENT #263    Frame(id=1447,   extended=False)                 timestamp 2147894
SENT #264    Frame(id=804264, extended=True)                  timestamp 2147895
SENT #265    Frame(id=804265, extended=True)                  timestamp 2147896
received     Frame(id=1450,   extended=True)   sent as False  timestamp 2147896
received     Frame(id=1451,   extended=True)   sent as False  timestamp 2147896
...
```

- Only the extended flag is wrong. The id, data, length and order are intact, and extended frames
  stay correct.
- **It persists:** single standard frames sent a second later still came back as extended.
- **CLOSE + OPEN of the channel clears it:** the same frames came back correctly straight after.
- It happened in all three mixed-traffic runs and never in standard-only traffic. The likely cause is
  a race in the firmware when it switches between standard and extended frames, leaving the
  "extended" setting stuck.
- **Unknown:** whether the device also *transmits* these frames as extended on a real bus, or only
  mislabels them on receive. That needs a second node.

### Complete hang

Seen once, in the standard-only soak above. Same symptom as after the RESET command; needs a replug.
That run printed no progress, so how long it ran before hanging is unknown. The soak now reports
progress every 30 s.

### Frame ordering

Tested at 10 kbit/s, where frames certainly queue up in the device:

| Sent | Received |
|---|---|
| 30 standard ids, descending `7FF … 7E2` | in order |
| 20 extended ids, descending | in order |
| 20 frames with the same id `0x123`, sequence in the data | in order |
| 4 standard then 4 extended | in order |
| 4 extended then 4 standard: `x10 x11 x12 x13 700 701 702 703` | `x10 x11 x12 700 701 702 703 x13` |
| alternating, extended first: `x100 101 x102 103 x104 105 …` | `x100 101 103 x102 105 x104 …` |
| alternating, standard first: `100 x101 102 x103 …` | `100 102 x101 104 x103 …` |
| `700 x10 600 x20 001` | `700 600 x10 001 x20` |

So the order isn't by CAN priority: the extended ids here outrank all the standard ones on the bus.
A standard frame overtakes an extended frame that's still waiting. This fits firmware that keeps
separate transmit slots for the two frame types and always serves the standard one first.
**Only same-type order can be relied on.** (The 1 Mbit/s soaks don't add evidence here: the
"reordering" first reported there turned out to be the extended-flag fault.)

### Mitigation in the driver
- `send()` is paced to **3,000 frames/s** by default (`start(max_tx_rate=...)`). Standard-only traffic
  ran clean at 3,000 (9 min) and 4,500 (10 min); 6,000 hung once. 3,000 keeps a margin below both.
  The spacing is even, with no bursts: the device would otherwise drain a burst at its full rate.
  Measured: 5,950 frames/s with a 6,000 cap, for both 0- and 8-byte frames.
- Lowering the rate **doesn't fix mixed-traffic faults**: both the losses and the extended-flag fault
  happened at 3,000/s. The workaround is to use one frame type, or to watch for standard ids arriving
  with `extended=True` and restart the channel (`stop()` + `start()`).
- **Can't be mitigated by the PC:** heavy *received* traffic from other nodes. Untested.
- `close()` swallows USB errors so a dead device doesn't mask the original exception; `send()` and
  `recv()` raise the `OSError`.

## 5. Python vs C++

- **Latency:** USB full speed delivers in 1 ms frames, and Python adds tens of microseconds to a
  ~740 µs round trip.
- **Throughput:** the firmware caps it (~9,000 frames/s), and it barely moved with up to 16 writes in
  flight. A faster host can't push more through the device.
- **Faster host code makes the stall more likely:** stall 1 came from the leanest, fastest send loop.
- **Where C/C++ would help:** heavy per-frame application logic at ~6,000+ frames/s, or hard timing
  guarantees while other Python threads keep the interpreter busy. Even then, only the
  receive/transmit loop would need moving into a small C extension; the protocol stays the same.

## 6. Open questions and next tests

- Real bus with a second node and 120 Ω termination: ACK behaviour, error frames, received traffic at
  high load (does stall risk depend on receive rate alone?).
- Extended-only traffic over a long soak (common for J1939). Mixed traffic misbehaves; extended-only
  hasn't been soak-tested.
- With a second node: are "flagged as extended" frames also sent as extended on the wire? Is the
  mixed-traffic loss on the transmit or the receive side?
- Does mixed traffic misbehave at low rates too (for example 500 frames/s), or only under load?
- Field meanings of GET_STATUS and GET_STATISTICS; formats of SET_SPEED and SET_MASK_FILTER.
- Unplugging while running (the driver should raise from `recv()`); several devices at once; serial
  change and firmware update over DFU on Windows.
- The Linux driver uses `0x27` for CRC error, the CANAL doc `0x26`.

## Sources

- Vendor wiki: <https://wiki.8devices.com/usb2can>
- Linux driver: `drivers/net/can/usb/usb_8dev.c` (mainline) and <https://github.com/krumboeck/usb2can>
- User guide (2016-12-23), datasheet, schematic, CANAL API: `vendor/downloads/`
