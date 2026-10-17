# Vendor files

Everything 8devices publishes for the USB2CAN on <https://wiki.8devices.com/usb2can>, downloaded
2026-10-16. **None of it is needed to use this driver.** This page records what each file is, so the
files themselves don't have to be kept. Any you do keep go in a local `vendor/` folder, which git ignores.

All files are at `https://www.8devices.com/media/products/usb2can/downloads/<file>`.

| File | Size | SHA-256 (first 16) | What it is | Worth keeping? |
|---|---|---|---|---|
| `usb2can_user_guide.pdf` | 1.8 MB | `931f19f822edacfa` | User guide 1.0 (2016-12-23): specs, pinout, LEDs, Linux and Windows setup, firmware upgrade | yes, reference (key facts are in [PROTOCOL.md](PROTOCOL.md#device)) |
| `usb2can_datasheet.pdf` | 805 KB | `097d39c2705273aa` | 2-page marketing datasheet | optional |
| `usb2can_schematics.pdf` | 20 KB | `63a134ba2337614a` | Full schematic (STR750, MCP2551, ISO7221, M24C16) | yes, reference |
| `CANAL_API.pdf` | 55 KB | `1afc9148a9e8b2e8` | CANAL DLL API | no, the DLL is a dead end |
| `usb2can_win32_v1.0.2.1.zip` | 1.4 MB | `0b3e437787436056` | 32-bit kernel driver | no, see below |
| `usb2can_win64_v1.0.2.1.zip` | 1.6 MB | `a79dbdc317781ed7` | 64-bit kernel driver | no, see below |
| `usb2can_win64_v1.0.2.1_170220.zip` | 1.6 MB | `6f1666f8aacbcbae` | Same 64-bit driver, Microsoft-signed (2017) | no, see below |
| `usb2can_canal_dll_v1.0.6.zip` | 32 KB | `db5ee77c02a84019` | CANAL API DLL (`usb2can.dll`) | no, 32-bit and needs the kernel driver |
| `usb2canTestApp_1_0.zip` | 568 KB | `58738c20f4bf27eb` | 32-bit MFC test app using the CANAL DLL | no |
| `usb2canTest_source_1_0.zip` | 117 KB | `1268408b680b7425` | Source of that test app | no |
| `DfuseDemo_2_2.zip` | 1.7 MB | `dcdacf70e7f14796` | ST DfuSe Demo 2.2 + `STTub30` DFU driver (signed 2009): firmware upgrade and serial change on Windows | yes, the only Windows flashing tool (untested; its driver may also be blocked by Memory Integrity) |
| `DfuseDemo_3_0_3.zip` | 5.8 MB | `4c6cb17d5b17ca05` | DfuSe Demo 3.0.3 | no, **truncated on the server** (no zip directory; md5 `224a92846fa841a7a7c27a12b6ced17d`, same on two downloads) |
| `dfu-util.gz` | 59 KB | `c87e3553e5087aef` | dfu-util modified by 8devices, Linux x86-64 binary | no, doesn't run on Windows |
| `usb2can_1_7.zip` | 41 KB | `4b7253fc2f0053c0` | Firmware 1.7 (DfuSe image), the latest | yes, to reflash if ever needed |
| `usb2can_1_6.zip` | 41 KB | `d14a83809986dd3d` | Firmware 1.6 | no, superseded |
| `usb2can_1_5.zip` | 24 KB | `47173a5fcdb5fc38` | Firmware 1.5 | no, superseded |
| `usb2can_eeproms_dfu_ED000100-ED000226.zip` | 8 KB | `4c5476bfd9f83d2c` | DFU EEPROM images, one per serial number ED000100–ED000226 | yes, needed to run several units on one PC (all ship as ED000200) |

Linux driver, the source of the protocol:

| File | Size | SHA-256 (first 16) | Where | Worth keeping? |
|---|---|---|---|---|
| `usb_8dev.c` | 24 KB | `223677c7a880c1e6` | mainline Linux, `drivers/net/can/usb/usb_8dev.c` ([git.kernel.org](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/plain/drivers/net/can/usb/usb_8dev.c)), GPL-2.0 | yes, protocol reference |
| `krumboeck/usb2can` | — | — | <https://github.com/krumboeck/usb2can>, the original out-of-tree version | no, older copy of the same driver |

## The vendor kernel driver

- **Two builds, three packages.** The win32/win64 v1.0.2.1 packages are KMDF 1.9 drivers with the
  WDF 1.9 co-installer. Their catalogs are signed by 8devices with a VeriSign certificate valid
  2011-07-06 to 2012-07-06; the `.sys` files themselves are unsigned. The 2017-02-20 win64 package is
  the same driver, but its `.sys` and `.cat` are signed by *Microsoft Windows Hardware Compatibility
  Publisher*, so Windows 11 would accept the signature.
- **It's Microsoft's sample code.** The PDB path is `c:\works\8devices\usb2can\usbsamp\sys\...\objfre_win7_amd64\...`,
  i.e. the WDK 7 **usbsamp** sample built for Windows 7. The INF also turns on KMDF verifier settings
  (`VerifierOn`, `DbgBreakOnError`).
- **Memory Integrity blocks it.** Every build has an `INIT` section that is both writable and
  executable. Memory Integrity (HVCI) refuses to load such drivers, and it's on on this PC
  (`SecurityServicesRunning = 2`). This is static analysis; the driver was never installed.

## The CANAL DLL

`usb2can.dll` v1.0.6 is **32-bit only** (PE32). It finds the device through SetupAPI and talks to the
vendor kernel driver with `DeviceIoControl`, so it can't work over WinUSB, and 64-bit programs can't
load it. Its open string is `"<serial> ; <kbit/s>"`, or `"<serial> ; 0 ;` plus four bit-timing values
for a custom rate. The CANAL doc orders those as `tseg2 ; tseg1 ; sjw ; brp` and the user guide as
`tseg1 ; tseg2 ; sjw ; brp`. Flags: 1 loopback, 2 silent, 4 one-shot, 8 status messages.
