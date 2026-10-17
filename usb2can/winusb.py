"""Minimal ctypes bindings for WinUSB, plus device lookup. Windows only."""
import ctypes
import uuid
from ctypes import wintypes as wt


class GUID(ctypes.Structure):
    _fields_ = [("Data1", ctypes.c_ulong), ("Data2", ctypes.c_ushort),
                ("Data3", ctypes.c_ushort), ("Data4", ctypes.c_ubyte * 8)]

    @classmethod
    def parse(cls, text):
        u = uuid.UUID(text)
        return cls(u.time_low, u.time_mid, u.time_hi_version,
                   (ctypes.c_ubyte * 8)(*u.bytes[8:]))


class OVERLAPPED(ctypes.Structure):
    _fields_ = [("Internal", ctypes.c_size_t), ("InternalHigh", ctypes.c_size_t),
                ("Offset", wt.DWORD), ("OffsetHigh", wt.DWORD), ("hEvent", wt.HANDLE)]


# Registered by the USB hub driver for every device. Opening it reaches
# whatever function driver is bound, here WinUSB.
GUID_DEVINTERFACE_USB_DEVICE = GUID.parse("a5dcbf10-6530-11d2-901f-00c04fb951ed")

GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
FILE_SHARE_READ = 0x1
FILE_SHARE_WRITE = 0x2
OPEN_EXISTING = 3
FILE_ATTRIBUTE_NORMAL = 0x80
FILE_FLAG_OVERLAPPED = 0x40000000
INVALID_HANDLE_VALUE = wt.HANDLE(-1).value

ERROR_ACCESS_DENIED = 5
ERROR_SEM_TIMEOUT = 121
ERROR_IO_PENDING = 997
STATUS_PENDING = 0x103
CR_SUCCESS = 0
CR_BUFFER_SMALL = 0x1A

# WinUsb_SetPipePolicy policy types
PIPE_TRANSFER_TIMEOUT = 0x03   # ULONG, milliseconds, 0 = never
RAW_IO = 0x07                  # UCHAR

_k32 = ctypes.WinDLL("kernel32", use_last_error=True)
_cfg = ctypes.WinDLL("cfgmgr32")
_wu = ctypes.WinDLL("winusb", use_last_error=True)


def _proto(fn, restype, *argtypes):
    fn.restype = restype
    fn.argtypes = argtypes
    return fn


_LPOV = ctypes.POINTER(OVERLAPPED)
_PULONG = ctypes.POINTER(wt.ULONG)

CreateFileW = _proto(_k32.CreateFileW, wt.HANDLE, wt.LPCWSTR, wt.DWORD, wt.DWORD,
                     ctypes.c_void_p, wt.DWORD, wt.DWORD, wt.HANDLE)
CloseHandle = _proto(_k32.CloseHandle, wt.BOOL, wt.HANDLE)
CreateEventW = _proto(_k32.CreateEventW, wt.HANDLE, ctypes.c_void_p, wt.BOOL, wt.BOOL, wt.LPCWSTR)
ResetEvent = _proto(_k32.ResetEvent, wt.BOOL, wt.HANDLE)

WinUsb_Initialize = _proto(_wu.WinUsb_Initialize, wt.BOOL, wt.HANDLE, ctypes.POINTER(ctypes.c_void_p))
WinUsb_Free = _proto(_wu.WinUsb_Free, wt.BOOL, ctypes.c_void_p)
WinUsb_SetPipePolicy = _proto(_wu.WinUsb_SetPipePolicy, wt.BOOL, ctypes.c_void_p, ctypes.c_ubyte,
                              wt.ULONG, wt.ULONG, ctypes.c_void_p)
WinUsb_ReadPipe = _proto(_wu.WinUsb_ReadPipe, wt.BOOL, ctypes.c_void_p, ctypes.c_ubyte,
                         ctypes.c_void_p, wt.ULONG, _PULONG, _LPOV)
WinUsb_WritePipe = _proto(_wu.WinUsb_WritePipe, wt.BOOL, ctypes.c_void_p, ctypes.c_ubyte,
                          ctypes.c_void_p, wt.ULONG, _PULONG, _LPOV)
WinUsb_GetOverlappedResult = _proto(_wu.WinUsb_GetOverlappedResult, wt.BOOL, ctypes.c_void_p,
                                    _LPOV, ctypes.POINTER(wt.DWORD), wt.BOOL)
WinUsb_AbortPipe = _proto(_wu.WinUsb_AbortPipe, wt.BOOL, ctypes.c_void_p, ctypes.c_ubyte)


def _error(what, code=None):
    code = ctypes.get_last_error() if code is None else code
    msg = f"{what}: {ctypes.FormatError(code).strip()}"
    if code == ERROR_SEM_TIMEOUT:
        return TimeoutError(msg)
    return ctypes.WinError(code, msg)


def find_devices(vid, pid):
    """Return [(serial, interface_path)] for present USB devices with this VID/PID."""
    guid = ctypes.byref(GUID_DEVINTERFACE_USB_DEVICE)
    while True:
        size = wt.ULONG()
        if _cfg.CM_Get_Device_Interface_List_SizeW(ctypes.byref(size), guid, None, 0) != CR_SUCCESS:
            return []
        buf = ctypes.create_unicode_buffer(size.value)
        rc = _cfg.CM_Get_Device_Interface_ListW(guid, None, buf, size.value, 0)
        if rc == CR_SUCCESS:
            break
        if rc != CR_BUFFER_SMALL:  # list grew between the two calls: retry
            return []
    tag = f"vid_{vid:04x}&pid_{pid:04x}"
    found = []
    for path in buf[:size.value].split("\0"):
        if tag in path.lower():
            # \\?\USB#VID_0483&PID_1234#ED000200#{guid}
            found.append((path.split("#")[2], path))
    return found


class WinUsbDevice:
    """An open WinUSB device: synchronous pipe I/O plus pipe policies."""

    def __init__(self, path):
        self._file = CreateFileW(path, GENERIC_READ | GENERIC_WRITE,
                                 FILE_SHARE_READ | FILE_SHARE_WRITE, None, OPEN_EXISTING,
                                 FILE_ATTRIBUTE_NORMAL | FILE_FLAG_OVERLAPPED, None)
        if self._file == INVALID_HANDLE_VALUE:
            code = ctypes.get_last_error()
            if code == ERROR_ACCESS_DENIED:
                raise _error("open device (is another program using it?)", code)
            raise _error("open device", code)
        handle = ctypes.c_void_p()
        if not WinUsb_Initialize(self._file, ctypes.byref(handle)):
            err = _error("WinUsb_Initialize")
            CloseHandle(self._file)
            raise err
        self.handle = handle

    def set_policy(self, pipe, policy, value, size=4):
        v = (ctypes.c_ubyte if size == 1 else wt.ULONG)(value)
        if not WinUsb_SetPipePolicy(self.handle, pipe, policy, size, ctypes.byref(v)):
            raise _error(f"set policy 0x{policy:02x} on pipe 0x{pipe:02x}")

    def write(self, pipe, data):
        buf = ctypes.create_string_buffer(bytes(data), len(data))
        n = wt.ULONG()
        if not WinUsb_WritePipe(self.handle, pipe, buf, len(data), ctypes.byref(n), None):
            raise _error(f"write to pipe 0x{pipe:02x}")
        return n.value

    def read(self, pipe, size):
        buf = ctypes.create_string_buffer(size)
        n = wt.ULONG()
        if not WinUsb_ReadPipe(self.handle, pipe, buf, size, ctypes.byref(n), None):
            raise _error(f"read from pipe 0x{pipe:02x}")
        return buf.raw[:n.value]

    def abort(self, pipe):
        WinUsb_AbortPipe(self.handle, pipe)

    def close(self):
        if self.handle:
            WinUsb_Free(self.handle)
            self.handle = None
        if self._file:
            CloseHandle(self._file)
            self._file = None


class AsyncRead:
    """One reusable overlapped read on a pipe. Keep several queued so the
    host controller always has a buffer ready for the device."""

    def __init__(self, dev, pipe, size):
        self.dev, self.pipe, self.size = dev, pipe, size
        self.buf = ctypes.create_string_buffer(size)
        self.ov = OVERLAPPED()
        self.ov.hEvent = CreateEventW(None, True, False, None)
        if not self.ov.hEvent:
            raise _error("CreateEvent")
        self._n = wt.ULONG()

    def submit(self):
        ResetEvent(self.ov.hEvent)
        if not WinUsb_ReadPipe(self.dev.handle, self.pipe, self.buf, self.size,
                               ctypes.byref(self._n), ctypes.byref(self.ov)):
            code = ctypes.get_last_error()
            if code != ERROR_IO_PENDING:
                raise _error(f"queue read on pipe 0x{self.pipe:02x}", code)

    def done(self):
        return self.ov.Internal != STATUS_PENDING

    def wait(self):
        """Block until the read completes; return the bytes received.
        Raises OSError (winerror 995) if the read was aborted."""
        n = wt.DWORD()
        if not WinUsb_GetOverlappedResult(self.dev.handle, ctypes.byref(self.ov), ctypes.byref(n), True):
            raise _error(f"read from pipe 0x{self.pipe:02x}")
        return self.buf.raw[:n.value]

    def close(self):
        """Wait out any pending I/O (abort the pipe first), then free the event."""
        try:
            self.wait()
        except OSError:
            pass
        CloseHandle(self.ov.hEvent)
