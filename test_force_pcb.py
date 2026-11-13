import ctypes
from ctypes import wintypes
import time

user32 = ctypes.windll.user32
winsta = user32.OpenWindowStationW('WinSta0', False, 0x037F)
user32.SetProcessWindowStation(winsta)
hdesk = user32.OpenDesktopW('Default', 0, False, 0x01FF)
user32.SetThreadDesktop(hdesk)

# Target KiCad PCB Editor
target_hwnd = 1773396 # sv1000 - PCB Editor

def force_foreground(hwnd):
    user32.ShowWindow(hwnd, 9) # SW_RESTORE
    user32.ShowWindow(hwnd, 3) # SW_MAXIMIZE
    
    VK_MENU = 0x12
    KEYEVENTF_KEYUP = 0x0002
    user32.keybd_event(VK_MENU, 0, 0, 0)
    user32.keybd_event(VK_MENU, 0, KEYEVENTF_KEYUP, 0)
    
    HWND_TOPMOST = -1
    HWND_NOTOPMOST = -2
    SWP_FLAGS = 0x0001 | 0x0002 | 0x0040
    user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_FLAGS)
    user32.BringWindowToTop(hwnd)
    user32.SetForegroundWindow(hwnd)
    user32.SetActiveWindow(hwnd)
    
    time.sleep(0.5)
    user32.SetWindowPos(hwnd, HWND_NOTOPMOST, 0, 0, 0, 0, SWP_FLAGS)
    user32.BringWindowToTop(hwnd)
    user32.SetForegroundWindow(hwnd)

print("Forcing KiCad PCB to foreground...")
force_foreground(target_hwnd)

pt = wintypes.POINT(500, 500)
h = user32.GetAncestor(user32.WindowFromPoint(pt), 2)
buf = ctypes.create_unicode_buffer(256)
user32.GetWindowTextW(h, buf, 256)
print(f"Window at (500, 500) is now: HWND {h} \"{buf.value}\"")
