"""Dump the USB2CAN's USB descriptors by asking its parent hub.

Works with no driver bound to the device (Device Manager code 28), because
the request goes to the hub driver, not to the device's own driver.
Read-only: it only issues GET_DESCRIPTOR requests.
"""
import ctypes
import struct
import sys
from ctypes import wintypes as wt

VID_PID = "VID_0483&PID_1234"
GUID_DEVINTERFACE_USB_HUB = "{f18a0e88-c30c-11d0-8815-00a0c906bed8}"
IOCTL_USB_GET_DESCRIPTOR_FROM_NODE_CONNECTION = 0x220410
CM_GETIDLIST_FILTER_ENUMERATOR = 0x1
CM_GETIDLIST_FILTER_PRESENT = 0x100
CM_DRP_ADDRESS = 0x1D
GENERIC_WRITE = 0x40000000
FILE_SHARE_WRITE = 0x2
OPEN_EXISTING = 3
INVALID_HANDLE_VALUE = wt.HANDLE(-1).value

cfg = ctypes.WinDLL("cfgmgr32")
k32 = ctypes.WinDLL("kernel32", use_last_error=True)
k32.CreateFileW.restype = wt.HANDLE
k32.CreateFileW.argtypes = [wt.LPCWSTR, wt.DWORD, wt.DWORD, ctypes.c_void_p,
                            wt.DWORD, wt.DWORD, wt.HANDLE]
k32.DeviceIoControl.argtypes = [wt.HANDLE, wt.DWORD, ctypes.c_void_p, wt.DWORD,
                                ctypes.c_void_p, wt.DWORD,
                                ctypes.POINTER(wt.DWORD), ctypes.c_void_p]
k32.CloseHandle.argtypes = [wt.HANDLE]


def find_device():
    """Return (instance_id, hub_instance_id, port) of the first USB2CAN found."""
    flags = CM_GETIDLIST_FILTER_ENUMERATOR | CM_GETIDLIST_FILTER_PRESENT
    size = wt.ULONG()
    cfg.CM_Get_Device_ID_List_SizeW(ctypes.byref(size), "USB", flags)
    buf = ctypes.create_unicode_buffer(size.value)
    cfg.CM_Get_Device_ID_ListW("USB", buf, size.value, flags)
    for inst in buf[:size.value].split("\0"):
        if VID_PID not in inst.upper():
            continue
        devinst, parent = wt.DWORD(), wt.DWORD()
        cfg.CM_Locate_DevNodeW(ctypes.byref(devinst), inst, 0)
        cfg.CM_Get_Parent(ctypes.byref(parent), devinst, 0)
        pbuf = ctypes.create_unicode_buffer(512)
        cfg.CM_Get_Device_IDW(parent, pbuf, 512, 0)
        addr, alen = wt.DWORD(), wt.ULONG(4)
        cfg.CM_Get_DevNode_Registry_PropertyW(devinst, CM_DRP_ADDRESS, None,
                                              ctypes.byref(addr), ctypes.byref(alen), 0)
        return inst, pbuf.value, addr.value
    return None


def get_descriptor(hub, port, dtype, index=0, langid=0, length=255):
    # USB_DESCRIPTOR_REQUEST: ConnectionIndex + 8-byte setup packet + data
    req = struct.pack("<IBBHHH", port, 0x80, 6, (dtype << 8) | index, langid, length)
    buf = ctypes.create_string_buffer(req + bytes(length), len(req) + length)
    got = wt.DWORD()
    if not k32.DeviceIoControl(hub, IOCTL_USB_GET_DESCRIPTOR_FROM_NODE_CONNECTION,
                               buf, len(buf), buf, len(buf), ctypes.byref(got), None):
        raise ctypes.WinError(ctypes.get_last_error())
    return buf.raw[12:got.value]


def get_string(hub, port, index):
    if not index:
        return None
    try:
        d = get_descriptor(hub, port, 3, index, 0x0409)
    except OSError as e:
        # The hub only caches device/config descriptors; string requests go
        # to the device, which may not answer while it is unconfigured.
        return f"<index {index}: {e.strerror}>"
    return d[2:d[0]].decode("utf-16-le")


def main():
    found = find_device()
    if not found:
        sys.exit(f"No present USB device with {VID_PID}")
    inst, hub_id, port = found
    print(f"device   {inst}\nhub      {hub_id}\nport     {port}")

    path = "\\\\?\\" + hub_id.replace("\\", "#") + "#" + GUID_DEVINTERFACE_USB_HUB
    hub = k32.CreateFileW(path, GENERIC_WRITE, FILE_SHARE_WRITE, None, OPEN_EXISTING, 0, None)
    if hub == INVALID_HANDLE_VALUE:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        dev = get_descriptor(hub, port, 1, length=18)
        (bLength, _, bcdUSB, cls, sub, proto, mps0, vid, pid, bcdDevice,
         iMfr, iProd, iSer, nCfg) = struct.unpack("<BBHBBBBHHHBBBB", dev)
        print(f"\nDEVICE  USB {bcdUSB:04x}  class {cls:02x}/{sub:02x}/{proto:02x}  "
              f"EP0 max {mps0}  {vid:04x}:{pid:04x}  bcdDevice {bcdDevice:04x}  configs {nCfg}")
        print(f"  manufacturer  {get_string(hub, port, iMfr)!r}")
        print(f"  product       {get_string(hub, port, iProd)!r}")
        print(f"  serial        {get_string(hub, port, iSer)!r}")

        head = get_descriptor(hub, port, 2, length=9)
        total = struct.unpack_from("<H", head, 2)[0]
        conf = get_descriptor(hub, port, 2, length=total)
        print(f"\nRAW CONFIG ({len(conf)} bytes) {conf.hex(' ')}")
        pos = 0
        while pos + 2 <= len(conf):
            ln, typ = conf[pos], conf[pos + 1]
            d = conf[pos:pos + ln]
            if typ == 2:
                _, _, tot, nif, val, icfg, attr, maxp = struct.unpack("<BBHBBBBB", d)
                print(f"CONFIG  value {val}  interfaces {nif}  attributes {attr:02x}  "
                      f"max power {maxp * 2} mA")
            elif typ == 4:
                _, _, num, alt, neps, c, s, p, istr = struct.unpack("<BBBBBBBBB", d)
                print(f"  INTERFACE {num} alt {alt}  endpoints {neps}  class {c:02x}/{s:02x}/{p:02x}")
            elif typ == 5:
                _, _, addr, attr, mps, interval = struct.unpack("<BBBBHB", d)
                kind = ["control", "isochronous", "bulk", "interrupt"][attr & 3]
                direction = "IN " if addr & 0x80 else "OUT"
                print(f"    ENDPOINT 0x{addr:02x} {direction} {kind:9s} max packet {mps}  interval {interval}")
            else:
                print(f"  descriptor type 0x{typ:02x}: {d.hex(' ')}")
            if ln == 0:
                break
            pos += ln
    finally:
        k32.CloseHandle(hub)


if __name__ == "__main__":
    main()
