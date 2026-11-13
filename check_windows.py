import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32
winsta = user32.OpenWindowStationW('WinSta0', False, 0x037F)
user32.SetProcessWindowStation(winsta)
hdesk = user32.OpenDesktopW('Default', 0, False, 0x01FF)
user32.SetThreadDesktop(hdesk)

class RECT(ctypes.Structure):
    _fields_ = [('left', wintypes.LONG), ('top', wintypes.LONG), ('right', wintypes.LONG), ('bottom', wintypes.LONG)]

class WINDOWPLACEMENT(ctypes.Structure):
    _fields_ = [
        ('length', wintypes.UINT),
        ('flags', wintypes.UINT),
        ('showCmd', wintypes.UINT),
        ('ptMinPosition', wintypes.POINT),
        ('ptMaxPosition', wintypes.POINT),
        ('rcNormalPosition', RECT)
    ]

fg = user32.GetForegroundWindow()
fg_len = user32.GetWindowTextLengthW(fg)
fg_buf = ctypes.create_unicode_buffer(fg_len + 1)
user32.GetWindowTextW(fg, fg_buf, fg_len + 1)
print(f'CURRENT FOREGROUND WINDOW: HWND {fg} "{fg_buf.value}"')

hwnds = [329662, 7079152, 10095800, 463246, 1249590, 1773396, 137880, 1249676]
for h in hwnds:
    txt_len = user32.GetWindowTextLengthW(h)
    txt_buf = ctypes.create_unicode_buffer(txt_len + 1)
    user32.GetWindowTextW(h, txt_buf, txt_len + 1)
    
    rect = RECT()
    user32.GetWindowRect(h, ctypes.byref(rect))
    
    is_iconic = user32.IsIconic(h)
    is_visible = user32.IsWindowVisible(h)
    
    wp = WINDOWPLACEMENT()
    wp.length = ctypes.sizeof(WINDOWPLACEMENT)
    user32.GetWindowPlacement(h, ctypes.byref(wp))
    
    print(f'HWND {h} ({txt_buf.value}): Visible={is_visible}, Iconic={is_iconic}, showCmd={wp.showCmd}, Rect=({rect.left},{rect.top},{rect.right},{rect.bottom})')
