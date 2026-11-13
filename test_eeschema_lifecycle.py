import ctypes
from ctypes import wintypes
import time
from pathlib import Path

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

winsta = user32.OpenWindowStationW('WinSta0', False, 0x037F)
user32.SetProcessWindowStation(winsta)
hdesk = user32.OpenDesktopW('Default', 0, False, 0x01FF)
user32.SetThreadDesktop(hdesk)

sch_file = r"C:\Mendex studio\products\8f697275-3a8d-456c-ae20-138a7698df61\revisions\9b7c1396-64da-41f8-8649-77dc0f24e103\pcb\sv1000.kicad_sch"
exe = r"C:\Program Files\KiCad\10.0\bin\eeschema.exe"

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

ret = kernel32.CreateProcessW(None, cmd, None, None, False, 0x00000200, None, str(Path(sch_file).parent), ctypes.byref(si), ctypes.byref(pi))
hProcess = pi.hProcess
pid = pi.dwProcessId
kernel32.CloseHandle(pi.hThread)

print(f"Spawned PID {pid}")

for sec in range(15):
    time.sleep(1)
    exit_code = wintypes.DWORD()
    kernel32.GetExitCodeProcess(hProcess, ctypes.byref(exit_code))
    is_alive = (exit_code.value == 259) # STILL_ACTIVE = 259
    
    # check windows
    found = []
    def _cb(hwnd, _lp):
        p_id = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(p_id))
        if p_id.value == pid:
            length = user32.GetWindowTextLengthW(hwnd)
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            found.append((hwnd, user32.IsWindowVisible(hwnd), buf.value))
        return True
    CB = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    user32.EnumDesktopWindows(hdesk, CB(_cb), 0)
    print(f"Sec {sec+1}: alive={is_alive}, exit_code={exit_code.value}, windows={found}")
    if not is_alive:
        break

kernel32.CloseHandle(hProcess)
