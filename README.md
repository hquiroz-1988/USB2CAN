# USB2CAN for Windows

A user-mode Python driver for the **8devices USB2CAN** converter (USB `0483:1234`), built on Microsoft's
built-in WinUSB driver. No vendor drivers and no third-party packages are needed.

The vendor's own Windows driver can't load on current Windows with Memory Integrity turned on, and their
API DLL is 32-bit only (see [docs/FINDINGS.md](docs/FINDINGS.md)). This driver talks to the device directly
using the protocol of the Linux kernel driver `usb_8dev`.

**Status (2026-10-16):** the driver works; the device's firmware is the weak point. Tested only in
loopback mode (no second CAN node available yet), including nearly 10 million frames of soak testing,
on Windows 11, Python 3.12 64-bit, device firmware 1.7 / hardware 1.0. **Standard-id traffic is
reliable** at the default rate and above. **Mixing standard and extended frames isn't**, and pushing
the device near its limits can lock it up. Read [Limitations](#limitations).

## Setup

1. **Attach WinUSB to the device** (one time, per USB2CAN unit):
   Device Manager → right-click **USB2CAN converter** (under *Other devices*) → **Update driver** →
   **Browse my computer** → **Let me pick from a list** → **Universal Serial Bus devices** →
   manufacturer **WinUsb Device** → model **WinUsb Device** → accept the warning.
   The device then shows up as *USB2CAN converter* under *Universal Serial Bus devices*.
   To undo it, uninstall the device in Device Manager and replug it.
2. **Python 3.10 or newer** on Windows. Nothing to install: the driver uses `ctypes` and system DLLs.
   Run things from this folder (or add it to `PYTHONPATH`) so `import usb2can` finds the package.
3. Check it works: `python tools/selftest.py`. This runs in silent loopback, so nothing goes onto the bus.

## Usage

```python
from usb2can import USB2CAN, Frame

with USB2CAN() as dev:                      # first device found, or USB2CAN("ED000200")
    print(dev.version())                    # ('1.7', '1.0')
    dev.start(500_000)                      # open the CAN channel at 500 kbit/s
    dev.send(Frame(0x123, b"\x01\x02\x03"))
    dev.send(Frame(0x18FF50E5, bytes(8), extended=True))
    frame = dev.recv(timeout=1.0)           # Frame, or None on timeout
    if frame:
        print(frame, frame.timestamp)       # "123  [3]  01 02 03", device time in ms
    print(dev.bus_status, dev.stats)
```

### API

| | |
|---|---|
| `list_devices()` | Serial numbers of USB2CANs bound to WinUSB. |
| `USB2CAN(serial=None)` | Opens the device. Only one program can have it open at a time. Use it as a context manager or call `close()`. |
| `.version()` | `(firmware, hardware)`, for example `('1.7', '1.0')`. |
| `.start(bitrate=500_000, *, timing=None, sample_point=0.875, loopback=False, silent=False, one_shot=False, max_tx_rate=3000)` | Opens the CAN channel. `loopback` echoes sent frames back as received frames. `silent` listens only and never drives the bus, not even ACKs. `loopback` + `silent` is an internal self-test. `one_shot` disables automatic retransmission. `max_tx_rate` caps sends per second; `None` removes the cap (see [Limitations](#limitations)). |
| `.stop()` | Closes the CAN channel. Frames still waiting to be sent are discarded. |
| `.send(frame)` | Sends one frame. Blocks while the device's ~70-frame buffer is full or to respect `max_tx_rate`. Raises `TimeoutError` if the device accepts nothing for 1 s. |
| `.recv(timeout=None)` | Next received `Frame`, or `None` after `timeout` seconds. Raises the USB error if the receive thread died, for example when the device was unplugged. |
| `.bus_status` / `.status_log` | Latest `BusStatus` (state, rx/tx error counters) and the last 256 status messages. |
| `.stats` | Counters: `rx_frames`, `tx_frames`, `rx_transfers`, `status_msgs`, `rx_dropped` (Python-side queue full), `rx_starved` (moments with no USB read queued), `framing_errors`, `unknown_msgs`. |
| `.command(cmd, opt1, opt2, data)` | Raw vendor command, returns the 10 reply data bytes. See [docs/PROTOCOL.md](docs/PROTOCOL.md). |
| `Frame(id, data=b"", extended=False, rtr=False, dlc=None, timestamp=None)` | A CAN 2.0A/B frame. `dlc` defaults to `len(data)`. For remote requests set `rtr=True, dlc=n`. |
| `BitTiming(brp, tseg1, tseg2, sjw=1)` | Explicit bit timing (32 MHz clock). `BitTiming.from_bitrate(br, sample_point)` finds exact settings. Pass one as `start(timing=...)`. |

**Bitrates:** any rate that divides 32 MHz exactly works: 32 MHz / (brp × (1 + tseg1 + tseg2)), with
tseg1 1–16, tseg2 1–8 and brp 1–1024. The standard rates all resolve to an 87.5% sample point:
10k, 20k, 50k, 100k, 125k, 250k, 500k, 800k and 1M.

### Tools

- `tools/selftest.py`: version, loopback round trip of edge-case frames, latency and throughput.
  `--soak 300` adds a 5-minute run with numbered frames that reports every lost frame;
  `--soak-dlc 0` and `--soak-ids std|ext|mixed` choose the frames. `--max-rate N` changes the send
  pacing, and `--max-rate 0` disables it. **Soaks and high rates can lock the device up; expect to replug it.**
- `tools/dump_descriptors.py`: reads the device's USB descriptors through its hub. Works with no driver attached.

## Performance

Measured in silent loopback at 1 Mbit/s, so the device both sends and receives every frame:

| | |
|---|---|
| Round trip (`send()` → frame back from `recv()`) | median 0.3–0.75 ms depending on the run, p99 under 1 ms, max 1.35 ms |
| Maximum frame rate (firmware-limited) | ~9,000 frames/s with 0-byte frames, ~6,300 frames/s with 8-byte frames, but not sustainable, see Limitations |
| Run-to-run variation | throughput varied up to ~30% between runs on the same PC (e.g. 8,900 vs 6,200 frames/s) |
| Device transmit buffer | ~70 frames, then USB flow control. No frames were lost in any test that didn't stall. |
| Timestamps | 32-bit, 1 ms resolution, counted from power-up |
| Python's own cost | ~1.3 µs to build a frame; the rest is USB and firmware |

The device is USB full speed, which works in 1 ms steps, and its firmware sends one frame at a time with a
25–65 µs gap. Those two things set the latency and throughput, not Python. A C or C++ driver would not
be meaningfully faster; see [docs/FINDINGS.md](docs/FINDINGS.md#5-python-vs-c).

## Limitations

- **Firmware reliability (serious).** Firmware 1.7, the latest, has these failure modes, all seen in
  loopback soak tests at 1 Mbit/s with 0-byte frames:

  | Failure | Seen with | Symptom | Recovery |
  |---|---|---|---|
  | Receive stall | ~9,000 frames/s, the device's maximum (twice) | `recv()` gets nothing; commands and `send()` still work | unplug + replug |
  | Complete hang | 6,000 frames/s, standard frames, within 2 minutes (once) | every call fails with "A device attached to the system is not functioning" | unplug + replug |
  | Standard frames flagged as extended | **mixed** standard/extended traffic, at 3,000 and 6,000 frames/s, after 1 s to 5 min | every standard frame comes back with `extended=True` (id, data, length intact) until fixed | `stop()` then `start()` the channel |
  | Silent frame loss | **mixed** traffic only: ~1 frame per minute at 3,000/s, ~1 every 6 s at 6,000/s | a single standard frame missing, no status message | none needed |

  **Standard-only traffic had none of this:** 0 lost and no errors in 1.6 million frames at 3,000/s
  and 2.65 million at 4,500/s (10 minutes). Closing and reopening the channel or the device, USB pipe
  resets and an interface reset don't recover a stalled or hung device.
  - `send()` is paced to **3,000 frames/s by default** (`max_tx_rate`). 4,500 was also clean for
    10 minutes with standard frames; 6,000 hung once. Pacing protects only against overload you cause
    yourself, and **doesn't fix mixed-traffic problems**, which happened at 3,000/s too.
  - **Prefer one frame type.** If you must mix standard and extended frames, expect occasional loss,
    and watch for standard ids arriving with `extended=True`. Restart the channel when you see that.
    Loopback can't tell whether such frames also go onto the bus as extended.
  - Pacing **cannot** protect against a busy bus: received traffic is set by the other nodes.
    A bus carrying thousands of frames/s may trigger the same failures. Untested without a second node.
  - If frames matter, add your own sequence numbers or acknowledgements; the device won't report a loss.
- **Order between standard and extended frames isn't preserved.** Frames of the same type always kept
  their order (same id, ascending or descending ids). But a standard frame can overtake an extended
  frame that's still waiting to go out. Example at 10 kbit/s: sent `ext 10, ext 11, ext 12, ext 13, 700, 701, 702, 703`,
  received `ext 10, ext 11, ext 12, 700, 701, 702, 703, ext 13`.
- **Don't send the RESET command (1).** It reboots the device's microcontroller without reconnecting on
  USB, so Windows keeps talking to a device that no longer answers. Replug afterwards.
- **Don't reset USB pipes.** The firmware doesn't reset its packet sequencing (data toggle), so the next
  packet on a reset pipe is silently lost.
- **No built-in termination.** The bus needs 120 Ω at each end. With nothing connected, sends fail with
  *stuff errors*, not the ACK errors you might expect, and the receive error counter climbs to
  error-passive within half a second.
- **Hardware filtering isn't available:** the vendor documents mask/filter as unimplemented in the firmware.
  Filter in Python.
- **One program at a time.** WinUSB gives exclusive access. A second `USB2CAN()` fails with
  "is another program using it?".
- **Every unit ships with serial ED000200.** To use several at once, give each a unique serial with the
  vendor's DFU EEPROM images. That procedure hasn't been tested on Windows here.
- **When the device fails mid-run,** `send()` and `recv()` raise `OSError` ("device attached to the
  system is not functioning"). `close()` doesn't raise, so it won't hide the original error.
- **Not yet tested:** extended-only traffic over long runs, a real bus with other nodes (including
  whether "flagged as extended" frames are wrong on the wire), heavy receive traffic, unplugging while
  running, multiple devices, firmware update over DFU.

## Repository layout

```
usb2can/            the driver (device.py: protocol and API, winusb.py: WinUSB ctypes bindings)
tools/              selftest.py, dump_descriptors.py
docs/PROTOCOL.md    USB protocol reference
docs/FINDINGS.md    investigation, measurements, experiment log
docs/VENDOR.md      every vendor download: URL, hash, what it is, worth keeping or not
vendor/             third-party downloads (local only, not in git)
```

`vendor/` isn't committed: it's material from 8devices, STMicroelectronics and the Linux kernel
(`usb_8dev.c` is GPL-2.0), about 16 MB of downloads. To recreate it, download the files linked from
<https://wiki.8devices.com/usb2can> (each one is listed in [docs/VENDOR.md](docs/VENDOR.md), with what it's good for)
and `drivers/net/can/usb/usb_8dev.c` from the Linux kernel.
