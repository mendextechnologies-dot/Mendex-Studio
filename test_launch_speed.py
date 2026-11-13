import ctypes
from ctypes import wintypes
import time
import subprocess
from pathlib import Path

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

winsta = user32.OpenWindowStationW('WinSta0', False, 0x037F)
user32.SetProcessWindowStation(winsta)
hdesk = user32.OpenDesktopW('Default', 0, False, 0x01FF)
user32.SetThreadDesktop(hdesk)

sch_file = r"C:\Mendex studio\products\8f697275-3a8d-456c-ae20-138a7698df61\revisions\9b7c1396-64da-41f8-8649-77dc0f24e103\pcb\sv1000.kicad_sch"
exe = r"C:\Program Files\KiCad\10.0\bin\eeschema.exe"

t0 = time.time()
cmd = f'"{exe}" "{sch_file}"'

class _STARTUPINFO(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD), ("lpReserved", wintypes.LPWSTR), ("lpDesktop", wintypes.LPWSTR),
        ("lpTitle", wintypes.LPWSTR), ("dwX", wintypes.DWORD), ("dwY", wintypes.DWORD),
        ("dwXSize", wintypes.DWORD), ("dwYSize", wintypes.DWORD), ("dwXCountChars", wintypes.DWORD),
        ("dwYCountChars", wintypes.DWORD), ("dwFillAttribute", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
        ("wShowWindow", wintypes.WORD), ("cbReserved2", wintypes.WORD), ("lpReserved2", ctypes.c_void_p),
        ("hStdInput", wintypes.HANDLE), ("hStdOutput", wintypes.HANDLE), ("hStdError", wintypes.HANDLE),
    ]

class _PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("hProcess", wintypes.HANDLE), ("hThread", wintypes.HANDLE),
        ("dwProcessId", wintypes.DWORD), ("dwThreadId", wintypes.DWORD),
    ]

si = _STARTUPINFO()
si.cb = ctypes.sizeof(_STARTUPINFO)
si.lpDesktop = r"WinSta0\Default"
si.dwFlags = 0x00000001
si.wShowWindow = 1
pi = _PROCESS_INFORMATION()

user32.AllowSetForegroundWindow(-1)
ret = kernel32.CreateProcessW(None, cmd, None, None, False, 0x00000200, None, str(Path(sch_file).parent), ctypes.byref(si), ctypes.byref(pi))
pid = pi.dwProcessId
kernel32.CloseHandle(pi.hProcess)
kernel32.CloseHandle(pi.hThread)

print(f"Spawned eeschema PID {pid}. Waiting for window...")

target_hwnd = None
for i in range(50):
    time.sleep(0.1)
    found = []
    def _cb(hwnd, _lp):
        if not user32.IsWindowVisible(hwnd):
            return True
        p_id = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(p_id))
        length = user32.GetWindowTextLengthW(hwnd)
        if length > 0:
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            if p_id.value == pid or "Schematic" in buf.value:
                found.append((hwnd, buf.value))
        return True
    CB = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    user32.EnumDesktopWindows(hdesk, CB(_cb), 0)
    if found:
        target_hwnd = found[0][0]
        dt = time.time() - t0
        print(f"Found window in {dt:.2f}s: HWND {target_hwnd} \"{found[0][1]}\"")
        break

if target_hwnd:
    # Activate and maximize
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

    fg = user32.GetForegroundWindow()
    buf = ctypes.create_unicode_buffer(256)
    user32.GetWindowTextW(fg, buf, 256)
    print(f"Active foreground is now: HWND {fg} \"{buf.value}\"")
