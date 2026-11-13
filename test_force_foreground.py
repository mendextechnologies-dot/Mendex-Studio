import ctypes
from ctypes import wintypes
import time

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

winsta = user32.OpenWindowStationW('WinSta0', False, 0x037F)
user32.SetProcessWindowStation(winsta)
hdesk = user32.OpenDesktopW('Default', 0, False, 0x01FF)
user32.SetThreadDesktop(hdesk)

# Target KiCad window
target_hwnd = 7079152 # sv1000 - Schematic Editor

def force_foreground(hwnd):
    # 1. Restore/Show
    user32.ShowWindow(hwnd, 9) # SW_RESTORE
    user32.ShowWindow(hwnd, 3) # SW_MAXIMIZE
    
    # 2. Simulate Alt key press to break Windows Foreground Lockout
    VK_MENU = 0x12
    KEYEVENTF_KEYUP = 0x0002
    user32.keybd_event(VK_MENU, 0, 0, 0)
    user32.keybd_event(VK_MENU, 0, KEYEVENTF_KEYUP, 0)
    
    # 3. Set TOPMOST
    HWND_TOPMOST = -1
    HWND_NOTOPMOST = -2
    SWP_FLAGS = 0x0001 | 0x0002 | 0x0040 # SWP_NOSIZE | SWP_NOMOVE | SWP_SHOWWINDOW
    user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_FLAGS)
    
    # 4. Bring to top & set foreground
    user32.BringWindowToTop(hwnd)
    user32.SetForegroundWindow(hwnd)
    user32.SetActiveWindow(hwnd)
    
    # 5. Brief sleep then remove topmost so normal window behavior resumes
    time.sleep(0.5)
    user32.SetWindowPos(hwnd, HWND_NOTOPMOST, 0, 0, 0, 0, SWP_FLAGS)
    user32.BringWindowToTop(hwnd)
    user32.SetForegroundWindow(hwnd)

print("Forcing KiCad to foreground...")
force_foreground(target_hwnd)

# Check what window is now at (500, 500)
pt = wintypes.POINT(500, 500)
h = user32.GetAncestor(user32.WindowFromPoint(pt), 2)
buf = ctypes.create_unicode_buffer(256)
user32.GetWindowTextW(h, buf, 256)
print(f"Window at (500, 500) is now: HWND {h} \"{buf.value}\"")

# Check foreground window
fg = user32.GetForegroundWindow()
user32.GetWindowTextW(fg, buf, 256)
print(f"Foreground window is now: HWND {fg} \"{buf.value}\"")
