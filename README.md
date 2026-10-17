# USB2CAN

Software for the **8devices USB2CAN** converter (USB `0483:1234`).

## `python/`: working Windows driver (start here)

A user-mode Python driver that talks to the device through Microsoft's built-in WinUSB driver. It works
on current Windows 10/11 with Memory Integrity turned on, and needs no vendor drivers and no third-party
packages. Tested in loopback so far.

- [python/README.md](python/README.md): setup, usage, performance and limitations
- [python/docs/PROTOCOL.md](python/docs/PROTOCOL.md): the device's USB protocol
- [python/docs/FINDINGS.md](python/docs/FINDINGS.md): investigation and soak-test results

## `USB2CAN/` and `usb2canTest/`: earlier attempt (2020)

A Visual Studio desktop application (C#) that calls the vendor's CANAL DLL, plus a copy of the vendor's
test application. `CANAL_API.pdf` is the vendor's documentation for that DLL.

These don't run on current Windows. The vendor kernel driver the DLL depends on is blocked by Memory
Integrity, and the app targets x64 while the DLL is 32-bit. Details are in
[FINDINGS.md](python/docs/FINDINGS.md#the-earlier-c-attempt-2020).
