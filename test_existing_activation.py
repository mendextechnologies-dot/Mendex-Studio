import ctypes
from ctypes import wintypes
import time

user32 = ctypes.windll.user32
winsta = user32.OpenWindowStationW('WinSta0', False, 0x037F)
user32.SetProcessWindowStation(winsta)
hdesk = user32.OpenDesktopW('Default', 0, False, 0x01FF)
user32.SetThreadDesktop(hdesk)

# Put Chrome in foreground first to simulate user clicking in browser
chrome_hwnd = 329662
user32.SetForegroundWindow(chrome_hwnd)
time.sleep(0.5)

fg0 = user32.GetForegroundWindow()
buf0 = ctypes.create_unicode_buffer(256)
user32.GetWindowTextW(fg0, buf0, 256)
print(f"Foreground before: HWND {fg0} \"{buf0.value}\"")

# Now find existing KiCad window and pop to front
target_hwnd = None
def _cb(hwnd, _lp):
    if not user32.IsWindowVisible(hwnd):
        return True
    length = user32.GetWindowTextLengthW(hwnd)
    if length > 0:
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        if "Schematic" in buf.value or "eeschema" in buf.value.lower():
            target_hwnd_list.append((hwnd, buf.value))
    return True

target_hwnd_list = []
CB = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
user32.EnumDesktopWindows(hdesk, CB(_cb), 0)

if target_hwnd_list:
    target_hwnd = target_hwnd_list[0][0]
    print(f"Found existing KiCad window: HWND {target_hwnd} \"{target_hwnd_list[0][1]}\"")
    
    # Activate
    if user32.IsIconic(target_hwnd):
        user32.ShowWindow(target_hwnd, 9)
    user32.ShowWindow(target_hwnd, 3)
    VK_MENU = 0x12
    KEYEVENTF_KEYUP = 0x0002
    user32.keybd_event(VK_MENU, 0, 0, 0)
    user32.keybd_event(VK_MENU, 0, KEYEVENTF_KEYUP, 0)
    HWND_TOPMOST = -1
    HWND_NOTOPMOST = -2
    SWP_FLAGS = 0x0001 | 0x0002 | 0x0040
    user32.SetWindowPos(target_hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_FLAGS)
    user32.BringWindowToTop(target_hwnd)
    user32.SetForegroundWindow(target_hwnd)
    user32.SetActiveWindow(target_hwnd)
    try:
        user32.SwitchToThisWindow(target_hwnd, True)
    except Exception:
        pass
    time.sleep(0.3)
    user32.SetWindowPos(target_hwnd, HWND_NOTOPMOST, 0, 0, 0, 0, SWP_FLAGS)
    user32.BringWindowToTop(target_hwnd)
    user32.SetForegroundWindow(target_hwnd)

    fg1 = user32.GetForegroundWindow()
    buf1 = ctypes.create_unicode_buffer(256)
    user32.GetWindowTextW(fg1, buf1, 256)
    print(f"Foreground after: HWND {fg1} \"{buf1.value}\"")
