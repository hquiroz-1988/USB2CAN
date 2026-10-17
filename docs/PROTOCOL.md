# USB2CAN USB protocol

Reference for the 8devices USB2CAN, firmware 1.7 / hardware 1.0. The source is the Linux kernel driver
`drivers/net/can/usb/usb_8dev.c` (copy in `vendor/linux/`). Everything marked **observed** was measured on
our device on 2026-10-16 and goes beyond what that driver documents.

## Device

| | |
|---|---|
| USB IDs | VID `0x0483` (STMicroelectronics), PID `0x1234`, bcdDevice `0x0100` |
| Strings | manufacturer `edevices`, product `USB2CAN converter`, serial `ED000200` (the factory default on every unit) |
| Speed | USB 2.0 full speed (12 Mbit/s), 100 mA |
| Class | device `ff/ff/00`, interface 0 `ff/ff/ff` (vendor-specific), one configuration |
| MCU | ST STR750 (ARM7), 8 MHz crystal, **CAN clock 32 MHz** |
| CAN side | MCP2551 transceiver, ISO7221 isolator plus isolated DC/DC (500 V), no termination, M24C16 EEPROM (holds the serial) |
| Connector | DSUB-9 male: pin 2 CANL, pin 7 CANH, pins 3 and 6 GND, pin 5 shield (100 Ω/0.1 µF to GND) |
| Bootloader | hold the reset button (next to the cable) while plugging in → DFU device `0483:df11` "STR75x-DFU" |

LED, per the vendor guide: red/green toggling = no host driver; steady red = driver loaded, CAN closed;
steady green = CAN open; slow green blink = error warning (≥ 96); fast green blink = error passive (≥ 128);
fast red blink = bus off; red and green both steady = bootloader.

## Endpoints

All four are bulk endpoints with a 64-byte max packet on interface 0 (observed descriptors match the Linux driver):

| Endpoint | Direction | Use |
|---|---|---|
| `0x81` | IN | received CAN frames and status messages, 21 bytes each |
| `0x02` | OUT | CAN frames to send, 16 bytes, **one per transfer** |
| `0x83` | IN | command replies, 16 bytes |
| `0x04` | OUT | commands, 16 bytes |

Multi-byte fields are **big-endian**.

## Commands (EP `0x04` → reply on EP `0x83`)

```
offset  0     1        2        3     4     5..14      15
        0x11  channel  command  opt1  opt2  data[10]   0x22
                (0)
```

The reply has the same layout. `opt1` = 0 means success (the Linux driver treats 255 as an error).
Send one command and read its reply before sending the next.

| # | Command | Parameters | Reply data (observed) |
|---|---|---|---|
| 1 | RESET | none | Succeeds, then the MCU reboots **without USB re-enumeration**: every later transfer fails until the device is replugged. **Don't use.** |
| 2 | OPEN | `opt1` = `0x09` (manual bit timing); data: `[0]` tseg1, `[1]` tseg2, `[2]` sjw, `[3..4]` brp (u16), `[5..8]` flags (u32) | Zeros. Also accepted while already open; the channel keeps working. |
| 3 | CLOSE | none | Zeros. Also succeeds when already closed. Frames still waiting to be sent are discarded. |
| 4 | SET_SPEED | unknown | Not probed. |
| 5 | SET_MASK_FILTER | unknown | Not probed. The vendor says mask/filter isn't implemented in the firmware. |
| 6 | GET_STATUS | none | All zeros with the channel closed and open (no errors). Field meaning unknown. |
| 7 | GET_STATISTICS | none | `00 00 00 05 00…` after 5 loopback frames: the first u32 counts frames (tx or rx not yet determined). |
| 8 | GET_SERIAL | none | ASCII serial: `45 44 30 30 30 32 30 30` = `ED000200` |
| 9 | GET_SOFTW_VER | none | `01 07` = firmware 1.7 |
| 10 | GET_HARDW_VER | none | `01 00` = hardware 1.0 |
| 11 | RESET_TIMESTAMP | none | Succeeds, but **has no visible effect**: the next frame's timestamp was still the time since power-up. |
| 12 | GET_SOFTW_HARDW_VER | none | `01 07 01 00` = firmware 1.7, hardware 1.0. Used by the Linux driver at probe. |

### OPEN flags

| Bit | Meaning |
|---|---|
| `0x01` | silent (listen only, no ACKs) |
| `0x02` | loopback (sent frames are also received) |
| `0x04` | disable automatic retransmission (one-shot) |
| `0x08` | send status messages (the Linux driver and ours always set this) |

### Bit timing

bitrate = 32 MHz / (brp × (1 + tseg1 + tseg2)), with tseg1 = prop_seg + phase_seg1 in 1–16, tseg2 in 1–8,
sjw in 1–4 and brp in 1–1024. Values go in as plain numbers (not minus 1). Example: 500 kbit/s, 87.5% sample
point = brp 4, tseg1 13, tseg2 2. On-wire timing was **observed** to match within 1% at 10 kbit/s
(see FINDINGS).

## Sending a frame (EP `0x02`)

```
offset  0     1      2..5       6    7..14     15
        0x55  flags  id (u32)   dlc  data[8]   0xAA
```

`flags`: `0x01` extended (29-bit) id, `0x02` remote request. Unused data bytes are zero. Send exactly one
message per transfer. **Observed:** the device buffers about 70 frames, then holds off further transfers
(USB NAK) until it has room. Nothing is dropped.

## Received messages (EP `0x81`)

```
offset  0     1     2      3..6       7    8..15     16..19           20
        0x55  type  flags  id (u32)   dlc  data[8]   timestamp (u32)  0xAA
```

A transfer can hold several 21-byte messages back to back. **Observed:** in practice the firmware sends one
per USB packet (2,000 frames arrived in 1,999 transfers). Keep reads queued (multiples of 64 bytes) so the
device always has somewhere to put data.

- `type` 0, CAN frame: `flags` `0x01` extended, `0x02` remote request. The data length is `dlc & 0x0F`, capped at 8.
- `type` 3 with `flags` = `0x04`, status message: `data[0]` status code, `data[1]` bit 7 = receive-passive and
  bits 0–6 = receive error counter, `data[2]` transmit error counter.
- `timestamp`: **observed** to tick in milliseconds since power-up (1,007 ticks/s measured against the PC clock).

| Status code | Meaning |
|---|---|
| `0x00` | OK / back to error-active |
| `0x01` | overrun |
| `0x02` | error warning (a counter ≥ 96) |
| `0x03` | error passive (a counter ≥ 128) |
| `0x04` | bus off |
| `0x20` / `0x21` / `0x23` | stuff / form / ACK error |
| `0x24` / `0x25` | bit errors. Both the Linux and CANAL sources name `0x24` "BIT0" but comment it "Bit1 Error" (and vice versa), so which is which is unconfirmed. Linux reports `0x24` as a bit0 error. |
| `0x27` | CRC error (the CANAL doc says `0x26`; Linux uses `0x27`) |

**Observed** with nothing connected to the CAN connector, in normal mode, sending at 500 kbit/s:
`stuff error rx=1 tx=0`, then with automatic retransmission `warning rx=99`, then `error passive rx=127`
within 0.5 s. The transmit counter stayed 0.

## Protocol quirks

- `CLEAR_FEATURE(ENDPOINT_HALT)` (WinUSB `ResetPipe`) doesn't reset the firmware's data toggle, so the
  next packet on that pipe is lost. Don't reset pipes.
- RESET (command 1) reboots the MCU without USB re-enumeration; CLOSE discards frames still waiting to be
  sent (see the command table).
- A standard frame can overtake an extended frame that is still waiting to be sent; same-type frames
  keep their order.

The firmware's reliability limits under load (receive stall, complete hang, frame loss, standard frames
flagged as extended) are summarised in the README's Limitations, with the evidence in
[FINDINGS.md](FINDINGS.md#4-firmware-reliability).
