import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32
winsta = user32.OpenWindowStationW('WinSta0', False, 0x037F)
user32.SetProcessWindowStation(winsta)
hdesk = user32.OpenDesktopW('Default', 0, False, 0x01FF)
user32.SetThreadDesktop(hdesk)

visible_windows = []

def enum_cb(hwnd, lparam):
    if user32.IsWindowVisible(hwnd):
        length = user32.GetWindowTextLengthW(hwnd)
        if length > 0:
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            cls_buf = ctypes.create_unicode_buffer(256)
            user32.GetClassNameW(hwnd, cls_buf, 256)
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            visible_windows.append((hwnd, pid.value, cls_buf.value, buf.value))
    return True

CB = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
user32.EnumDesktopWindows(hdesk, CB(enum_cb), 0)

for h, p, c, t in visible_windows:
    print(f"HWND {h:8d} | PID {p:5d} | Class {c:25s} | Title: {t}")
