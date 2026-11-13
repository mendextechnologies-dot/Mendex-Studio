import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32
winsta = user32.OpenWindowStationW('WinSta0', False, 0x037F)
user32.SetProcessWindowStation(winsta)
hdesk = user32.OpenDesktopW('Default', 0, False, 0x01FF)
user32.SetThreadDesktop(hdesk)

def enum_cb(hwnd, lparam):
    pid = wintypes.DWORD()
    tid = user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    length = user32.GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buf, length + 1)
    visible = user32.IsWindowVisible(hwnd)
    
    # Get class name
    cls_buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, cls_buf, 256)
    
    if visible or length > 0:
        print(f"HWND {hwnd:8d} | PID {pid.value:5d} | TID {tid:5d} | Vis {visible} | Class {cls_buf.value:25s} | Title: {buf.value}")
    return True

CB = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
user32.EnumDesktopWindows(hdesk, CB(enum_cb), 0)
