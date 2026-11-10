"""Read Windows PE file-version metadata without starting a native tool."""
import ctypes
import os


def windows_file_version(path):
    if os.name != "nt":
        return None
    try:
        library = ctypes.WinDLL("version", use_last_error=True)
        size_api = library.GetFileVersionInfoSizeW
        size_api.argtypes = [ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_uint32)]
        size_api.restype = ctypes.c_uint32
        ignored = ctypes.c_uint32()
        size = size_api(str(path), ctypes.byref(ignored))
        if not size:
            return None
        buffer = ctypes.create_string_buffer(size)
        info_api = library.GetFileVersionInfoW
        info_api.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p]
        info_api.restype = ctypes.c_int
        if not info_api(str(path), 0, size, buffer):
            return None
        pointer, length = ctypes.c_void_p(), ctypes.c_uint32()
        query_api = library.VerQueryValueW
        query_api.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_uint32)]
        query_api.restype = ctypes.c_int
        if not query_api(buffer, "\\", ctypes.byref(pointer), ctypes.byref(length)) or length.value < 16:
            return None
        values = ctypes.cast(pointer, ctypes.POINTER(ctypes.c_uint32))
        if values[0] != 0xFEEF04BD:
            return None
        high, low = values[2], values[3]
        return f"{high >> 16}.{high & 65535}.{low >> 16}.{low & 65535}"
    except (OSError, AttributeError):
        return None
