"""Validated desktop handoff. Never invokes a shell or runs project scripts."""
import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import shutil
import subprocess
import threading
import time

if os.name == "nt":
    class _STARTUPINFO(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD),
            ("lpReserved", wintypes.LPWSTR),
            ("lpDesktop", wintypes.LPWSTR),
            ("lpTitle", wintypes.LPWSTR),
            ("dwX", wintypes.DWORD),
            ("dwY", wintypes.DWORD),
            ("dwXSize", wintypes.DWORD),
            ("dwYSize", wintypes.DWORD),
            ("dwXCountChars", wintypes.DWORD),
            ("dwYCountChars", wintypes.DWORD),
            ("dwFillAttribute", wintypes.DWORD),
            ("dwFlags", wintypes.DWORD),
            ("wShowWindow", wintypes.WORD),
            ("cbReserved2", wintypes.WORD),
            ("lpReserved2", ctypes.c_void_p),
            ("hStdInput", wintypes.HANDLE),
            ("hStdOutput", wintypes.HANDLE),
            ("hStdError", wintypes.HANDLE),
        ]

    class _PROCESS_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("hProcess", wintypes.HANDLE),
            ("hThread", wintypes.HANDLE),
            ("dwProcessId", wintypes.DWORD),
            ("dwThreadId", wintypes.DWORD),
        ]


def _activate_window(top_hwnd: int) -> bool:
    """Elevates and locks focus on the targeted GUI window on top of any maximized browser window."""
    if not top_hwnd or os.name != "nt":
        return False
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    winsta = user32.OpenWindowStationW("WinSta0", False, 0x037F)
    if winsta:
        user32.SetProcessWindowStation(winsta)
    hdesk = user32.OpenDesktopW("Default", 0, False, 0x01FF)
    if hdesk:
        user32.SetThreadDesktop(hdesk)

    if not user32.IsWindow(top_hwnd):
        if hdesk:
            user32.CloseDesktop(hdesk)
        return False

    ret_attach = False
    fg_thread = 0
    curr_thread = 0
    try:
        # Ensure the calling thread has a Win32 message queue for AttachThreadInput
        msg = wintypes.MSG()
        user32.PeekMessageW(ctypes.byref(msg), 0, 0, 0, 0)

        fg = user32.GetForegroundWindow()
        if fg and fg != top_hwnd:
            fg_thread = user32.GetWindowThreadProcessId(fg, None)
            curr_thread = kernel32.GetCurrentThreadId()
            if fg_thread and curr_thread and fg_thread != curr_thread:
                ret_attach = bool(user32.AttachThreadInput(curr_thread, fg_thread, True))

        # 1. Restore if iconic, then maximize
        if user32.IsIconic(top_hwnd):
            user32.ShowWindow(top_hwnd, 9)  # SW_RESTORE
        user32.ShowWindow(top_hwnd, 3)      # SW_SHOWMAXIMIZED

        # 2. Synthesize Alt key down + up to unlock Windows foreground lockout
        VK_MENU = 0x12
        KEYEVENTF_KEYUP = 0x0002
        user32.keybd_event(VK_MENU, 0, 0, 0)
        user32.keybd_event(VK_MENU, 0, KEYEVENTF_KEYUP, 0)

        # 3. Elevate to TOPMOST to pop above maximized Chrome/Island browser
        HWND_TOPMOST = -1
        HWND_NOTOPMOST = -2
        SWP_FLAGS = 0x0001 | 0x0002 | 0x0040  # SWP_NOSIZE | SWP_NOMOVE | SWP_SHOWWINDOW
        user32.SetWindowPos(top_hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_FLAGS)

        # 4. Bring to top, activate, set foreground
        user32.BringWindowToTop(top_hwnd)
        user32.SetForegroundWindow(top_hwnd)
        user32.SetActiveWindow(top_hwnd)
        try:
            user32.SwitchToThisWindow(top_hwnd, True)
        except Exception:
            pass

        # 5. Hold TOPMOST for 350ms so the window paints completely in front of the browser, then clear topmost
        time.sleep(0.35)
        user32.SetWindowPos(top_hwnd, HWND_NOTOPMOST, 0, 0, 0, 0, SWP_FLAGS)
        user32.BringWindowToTop(top_hwnd)
        user32.SetForegroundWindow(top_hwnd)
    finally:
        if ret_attach and curr_thread and fg_thread:
            try:
                user32.AttachThreadInput(curr_thread, fg_thread, False)
            except Exception:
                pass
        if hdesk:
            user32.CloseDesktop(hdesk)

    return True


def _find_window_on_desktop(
    target_pid: int | None = None,
    required_hints: list[str] | None = None,
    hints: list[str] | None = None,
) -> int | None:
    """Finds an existing top-level interactive window matching target_pid or window title hints."""
    if os.name != "nt":
        return None
    user32 = ctypes.windll.user32
    winsta = user32.OpenWindowStationW("WinSta0", False, 0x037F)
    if winsta:
        user32.SetProcessWindowStation(winsta)
    hdesk = user32.OpenDesktopW("Default", 0, False, 0x01FF)
    if hdesk:
        user32.SetThreadDesktop(hdesk)

    found_hwnds = []
    def _cb(hwnd, _lp):
        if not user32.IsWindowVisible(hwnd):
            return True
        p_id = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(p_id))
        length = user32.GetWindowTextLengthW(hwnd)
        if length > 0:
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            title = buf.value
            if title not in ("Default IME", "MSCTFIME UI"):
                matched = False
                if target_pid and p_id.value == target_pid:
                    matched = True
                elif required_hints:
                    if all(req.lower() in title.lower() for req in required_hints):
                        matched = True
                elif hints and any(h.lower() in title.lower() for h in hints if len(h) >= 3):
                    matched = True
                if matched:
                    found_hwnds.append(hwnd)
        return True

    try:
        CB = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
        user32.EnumDesktopWindows(hdesk if hdesk else 0, CB(_cb), 0)
    finally:
        if hdesk:
            user32.CloseDesktop(hdesk)

    return found_hwnds[0] if found_hwnds else None


def _spawn_on_desktop(
    cmd_line: str,
    work_dir: str | None = None,
    required_hints: list[str] | None = None,
    window_hints: list[str] | None = None,
) -> int:
    """Spawns an interactive GUI process directly on the user's physical desktop (WinSta0\\Default).
    
    This ensures that applications like KiCad, FreeCAD, LTspice, and Explorer open
    directly on the user's active monitor rather than being trapped in an isolated runner desktop.
    """
    if os.name != "nt":
        proc = subprocess.Popen(cmd_line, shell=True, cwd=work_dir)
        return proc.pid

    # 1. Check if a matching window is ALREADY running on the desktop
    if required_hints:
        existing_hwnd = _find_window_on_desktop(required_hints=required_hints)
        if existing_hwnd:
            _activate_window(existing_hwnd)
            p_id = wintypes.DWORD()
            ctypes.windll.user32.GetWindowThreadProcessId(existing_hwnd, ctypes.byref(p_id))
            return p_id.value
    elif window_hints:
        existing_hwnd = _find_window_on_desktop(hints=window_hints)
        if existing_hwnd:
            _activate_window(existing_hwnd)
            p_id = wintypes.DWORD()
            ctypes.windll.user32.GetWindowThreadProcessId(existing_hwnd, ctypes.byref(p_id))
            return p_id.value

    # Allow spawned process to immediately grab foreground focus
    try:
        ctypes.windll.user32.AllowSetForegroundWindow(-1)
    except Exception:
        pass

    si = _STARTUPINFO()
    si.cb = ctypes.sizeof(_STARTUPINFO)
    si.lpDesktop = r"WinSta0\Default"
    si.dwFlags = 0x00000001
    si.wShowWindow = 3
    pi = _PROCESS_INFORMATION()

    creation_flags = 0x00000200
    try:
        creation_flags |= 0x01000000
    except Exception:
        pass

    ret = ctypes.windll.kernel32.CreateProcessW(
        None,
        cmd_line,
        None,
        None,
        False,
        creation_flags,
        None,
        work_dir,
        ctypes.byref(si),
        ctypes.byref(pi),
    )
    if not ret:
        creation_flags = 0x00000200
        ret = ctypes.windll.kernel32.CreateProcessW(
            None,
            cmd_line,
            None,
            None,
            False,
            creation_flags,
            None,
            work_dir,
            ctypes.byref(si),
            ctypes.byref(pi),
        )
        if not ret:
            err = ctypes.GetLastError()
            si.lpDesktop = "Default"
            ret = ctypes.windll.kernel32.CreateProcessW(
                None,
                cmd_line,
                None,
                None,
                False,
                creation_flags,
                None,
                work_dir,
                ctypes.byref(si),
                ctypes.byref(pi),
            )
            if not ret:
                try:
                    proc = subprocess.Popen(cmd_line, cwd=work_dir)
                    return proc.pid
                except Exception as exc:
                    raise OSError(f"CreateProcessW failed with Win32 error {err}: {exc}") from exc

    pid = pi.dwProcessId
    ctypes.windll.kernel32.CloseHandle(pi.hProcess)
    ctypes.windll.kernel32.CloseHandle(pi.hThread)

    # Fast synchronous check (up to 1.5 seconds) so that the application pops into view
    # BEFORE the HTTP response returns "Operation succeeded" to the browser
    t_start = time.time()
    while time.time() - t_start < 1.5:
        time.sleep(0.15)
        hw = _find_window_on_desktop(target_pid=pid, required_hints=required_hints, hints=window_hints)
        if hw:
            _activate_window(hw)
            break

    # Background watchdog thread keeps monitoring in case the application takes longer to initialize
    def _watchdog(target_pid: int, req_hints: list[str] | None, hints: list[str] | None):
        winsta = ctypes.windll.user32.OpenWindowStationW("WinSta0", False, 0x037F)
        if winsta:
            ctypes.windll.user32.SetProcessWindowStation(winsta)
        hdesk = ctypes.windll.user32.OpenDesktopW("Default", 0, False, 0x01FF)
        if hdesk:
            ctypes.windll.user32.SetThreadDesktop(hdesk)
        try:
            for _ in range(40):
                time.sleep(0.25)
                hw = _find_window_on_desktop(target_pid=target_pid, required_hints=req_hints, hints=hints)
                if hw:
                    _activate_window(hw)
                    break
        finally:
            if hdesk:
                ctypes.windll.user32.CloseDesktop(hdesk)

    threading.Thread(target=_watchdog, args=(pid, required_hints, window_hints), daemon=True).start()
    return pid


def find_vscode() -> Path | None:
    candidates = []
    if found := shutil.which("code"):
        path = Path(found)
        candidates.append(path.parent.parent / "Code.exe" if path.suffix.lower() in (".cmd", ".bat") else path)
    if os.name == "nt":
        candidates.extend([
            Path(os.environ.get("LOCALAPPDATA", "C:/Users/Default/AppData/Local")) / "Programs/Microsoft VS Code/Code.exe",
            Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Microsoft VS Code/Code.exe",
        ])
    return next((path.resolve() for path in candidates if path.is_absolute() and path.is_file()), None)


def launch_vscode(folder: Path):
    executable = find_vscode()
    if executable is None:
        raise FileNotFoundError("VS Code not found. Install VS Code or expose its code command on PATH, then retry.")
    cmd = f'"{executable}" --new-window "{folder}"'
    pid = _spawn_on_desktop(cmd, str(folder), window_hints=["Visual Studio Code", "Code", folder.name])
    return {"executable": str(executable), "workspace": str(folder), "pid": pid}


def _spawn_gui(exe: Path, target: Path | None = None, work_dir: Path | None = None, hints: list[str] | None = None) -> dict:
    """Spawns an interactive Windows GUI application cleanly on the user's physical desktop.
    
    Uses Win32 CreateProcessW targeting WinSta0\\Default to guarantee that the application
    appears with a visible, interactive top-level window on the user's active screen.
    """
    # Native applications own editing locks and crash recovery. Launching must
    # never delete potentially active locks or recoverable unsaved documents.
    cwd = str(work_dir or (target.parent if target else exe.parent))
    cmd_line = f'"{exe}" "{target}"' if target else f'"{exe}"'

    required_hints: list[str] = []
    window_hints = list(hints) if hints else []
    if target:
        window_hints.extend([target.stem, target.name])
    window_hints.extend([exe.stem, exe.name])
    stem_lower = exe.stem.lower()
    if "eeschema" in stem_lower:
        required_hints = ["Schematic"]
        if target:
            required_hints.append(target.stem)
        window_hints.extend(["Schematic", "sv1000", "KiCad"])
    elif "pcbnew" in stem_lower:
        required_hints = ["PCB"]
        if target:
            required_hints.append(target.stem)
        window_hints.extend(["PCB", "sv1000", "KiCad"])
    elif "kicad" in stem_lower:
        required_hints = ["KiCad"]
        window_hints.extend(["KiCad", "sv1000"])
    elif "freecad" in stem_lower:
        required_hints = ["FreeCAD"]
        window_hints.extend(["FreeCAD", "bobbin", "Document Recovery"])
    elif "ltspice" in stem_lower:
        required_hints = ["LTspice"]
        window_hints.extend(["LTspice", "XVII"])
    elif "femm" in stem_lower:
        required_hints = ["FEMM"]
        window_hints.extend(["FEMM", "Magnetics"])
    elif "omedit" in stem_lower:
        required_hints = ["OMEdit"]
        window_hints.extend(["OMEdit", "OpenModelica"])
    elif "msedge" in stem_lower:
        if target:
            cmd_line = f'"{exe}" --new-window "{target}"'
            required_hints = ["Edge", target.stem]
        window_hints.extend(["Edge"])
    elif "chrome" in stem_lower:
        if target:
            cmd_line = f'"{exe}" --new-window "{target}"'
            required_hints = ["Chrome", target.stem]
        window_hints.extend(["Chrome"])
    elif "winword" in stem_lower:
        if target:
            required_hints = ["Word", target.stem]
        window_hints.extend(["Word", "Document"])
    elif target and not required_hints:
        required_hints = [exe.stem, target.stem]

    pid = _spawn_on_desktop(cmd_line, cwd, required_hints=required_hints, window_hints=window_hints)
    return {
        "status": "launched",
        "method": "CreateProcessW(WinSta0\\Default)",
        "executable": str(exe),
        "target": str(target) if target else None,
        "pid": pid,
    }


def _open_document(p: Path) -> None:
    """Safely opens documents, source files, netlists, scripts, or reports on the user's desktop.
    
    Handles missing Windows shell associations gracefully by routing directly to VS Code,
    Notepad++, Windows Notepad, or revealing in File Explorer on the physical desktop.
    """
    # Fallback 1: VS Code
    vscode = find_vscode()
    if vscode and vscode.exists():
        _spawn_on_desktop(f'"{vscode}" "{p}"', str(p.parent), window_hints=["Code", p.name])
        return

    # Fallback 2: Notepad++
    if os.name == "nt":
        for npp in (
            Path(r"C:\Program Files\Notepad++\notepad++.exe"),
            Path(r"C:\Program Files (x86)\Notepad++\notepad++.exe"),
        ):
            if npp.exists():
                _spawn_on_desktop(f'"{npp}" "{p}"', str(p.parent), window_hints=["Notepad++", p.name])
                return

        # Fallback 3: Standard Windows Notepad
        notepad = Path(r"C:\Windows\System32\notepad.exe")
        if notepad.exists():
            _spawn_on_desktop(f'"{notepad}" "{p}"', str(p.parent), window_hints=["Notepad", p.name])
            return

    # Fallback 4: Reveal file in Explorer
    reveal_in_explorer(p)


def reveal_in_explorer(p: Path) -> None:
    """Reveals the given file or opens the directory directly in Windows File Explorer on the interactive desktop."""
    path = Path(p).resolve()
    if not path.exists():
        raise FileNotFoundError(f"Path does not exist: {path}")

    if os.name == "nt":
        if path.is_dir():
            cmd = f'explorer.exe "{path}"'
            work_dir = str(path)
        else:
            cmd = f'explorer.exe /select,"{path}"'
            work_dir = str(path.parent)
        _spawn_on_desktop(cmd, work_dir, window_hints=["Explorer", "File Explorer", path.name, path.parent.name])
        return

    subprocess.Popen(["xdg-open", str(path)])


def open_native(path: Path):
    if os.name != "nt":
        raise OSError("Native file opening is implemented for Windows only")
    p = Path(path).resolve()
    if not p.exists():
        raise FileNotFoundError(f"File or directory does not exist: {p}")
    ext = p.suffix.lower()

    # Route directories directly to explorer.exe
    if p.is_dir():
        reveal_in_explorer(p)
        return

    # Route 3D CAD (.step / .stp / .stl / .fcstd) directly to FreeCAD
    if ext in (".step", ".stp", ".stl", ".fcstd"):
        fc_paths = [
            Path(r"C:\Program Files\FreeCAD 1.1\bin\freecad.exe"),
            Path(r"C:\Program Files\FreeCAD 1.0\bin\freecad.exe"),
            Path(r"C:\Program Files\FreeCAD 0.21\bin\freecad.exe"),
        ]
        if found_fc := shutil.which("freecad"):
            fc_paths.insert(0, Path(found_fc))
        for candidate in fc_paths:
            if candidate.exists():
                _spawn_gui(candidate, p)
                return
        raise FileNotFoundError(
            f"FreeCAD is required to open 3D model '{p.name}'. No compatible FreeCAD installation was found at C:\\Program Files\\FreeCAD."
        )

    # Route KiCad schematic to eeschema.exe
    if ext in (".kicad_sch", ".sch"):
        sch_paths = [
            Path(r"C:\Program Files\KiCad\10.0\bin\eeschema.exe"),
            Path(r"C:\Program Files\KiCad\9.0\bin\eeschema.exe"),
            Path(r"C:\Program Files\KiCad\8.0\bin\eeschema.exe"),
        ]
        if found_sch := shutil.which("eeschema"):
            sch_paths.insert(0, Path(found_sch))
        for candidate in sch_paths:
            if candidate.exists():
                _spawn_gui(candidate, p)
                return
        raise FileNotFoundError(f"KiCad Schematic Editor (eeschema.exe) not found to open '{p.name}'.")

    # Route KiCad PCB to pcbnew.exe
    if ext == ".kicad_pcb":
        pcb_paths = [
            Path(r"C:\Program Files\KiCad\10.0\bin\pcbnew.exe"),
            Path(r"C:\Program Files\KiCad\9.0\bin\pcbnew.exe"),
            Path(r"C:\Program Files\KiCad\8.0\bin\pcbnew.exe"),
        ]
        if found_pcb := shutil.which("pcbnew"):
            pcb_paths.insert(0, Path(found_pcb))
        for candidate in pcb_paths:
            if candidate.exists():
                _spawn_gui(candidate, p)
                return
        raise FileNotFoundError(f"KiCad PCB Editor (pcbnew.exe) not found to open '{p.name}'.")

    # Route KiCad Project Manager (.kicad_pro / .pro)
    if ext in (".kicad_pro", ".pro"):
        kicad_paths = [
            Path(r"C:\Program Files\KiCad\10.0\bin\kicad.exe"),
            Path(r"C:\Program Files\KiCad\9.0\bin\kicad.exe"),
            Path(r"C:\Program Files\KiCad\8.0\bin\kicad.exe"),
        ]
        if found_kicad := shutil.which("kicad"):
            kicad_paths.insert(0, Path(found_kicad))
        for candidate in kicad_paths:
            if candidate.exists():
                _spawn_gui(candidate, p)
                return
        raise FileNotFoundError(f"KiCad Project Manager was not found to open '{p.name}'.")

    # Route SPICE circuits / waveforms to LTspice.exe
    if ext in (".raw", ".net", ".cir", ".asc", ".op.raw"):
        lt_paths = [
            Path(r"C:\Program Files\ADI\LTspice\LTspice.exe"),
            Path(r"C:\Program Files\LTC\LTspiceXVII\XVIIx64.exe"),
        ]
        if found_lt := (shutil.which("LTspice") or shutil.which("XVIIx64")):
            lt_paths.insert(0, Path(found_lt))
        for candidate in lt_paths:
            if candidate.exists():
                _spawn_gui(candidate, p)
                return
        raise FileNotFoundError(f"LTspice was not found to open simulation file '{p.name}'.")

    # Route FEMM magnetics & electrostatics models to femm.exe
    if ext in (".fem", ".ans", ".fee"):
        femm_paths = [
            Path(r"C:\femm42\bin\femm.exe"),
            Path(r"C:\Program Files\femm42\bin\femm.exe"),
            Path(r"C:\Program Files (x86)\femm42\bin\femm.exe"),
        ]
        if found_femm := shutil.which("femm"):
            femm_paths.insert(0, Path(found_femm))
        for candidate in femm_paths:
            if candidate.exists():
                _spawn_gui(candidate, p)
                return
        raise FileNotFoundError(f"FEMM 4.2 was not found to open magnetics model '{p.name}'.")

    # Route OpenModelica models to OMEdit.exe
    if ext in (".mo", ".moe"):
        om_paths = [
            Path(r"C:\Program Files\OpenModelica1.26.3-64bit\bin\OMEdit.exe"),
            Path(r"C:\Program Files\OpenModelica\bin\OMEdit.exe"),
        ]
        if found_om := shutil.which("OMEdit"):
            om_paths.insert(0, Path(found_om))
        for candidate in om_paths:
            if candidate.exists():
                _spawn_gui(candidate, p)
                return
        raise FileNotFoundError(f"OpenModelica OMEdit was not found to open '{p.name}'.")

    # Route Gerbers & drill files to KiCad GerbView
    if ext in (".gbr", ".gtl", ".gbl", ".gts", ".gbs", ".gto", ".gbo", ".gm1", ".drl"):
        gerb_paths = [
            Path(r"C:\Program Files\KiCad\10.0\bin\gerbview.exe"),
            Path(r"C:\Program Files\KiCad\9.0\bin\gerbview.exe"),
            Path(r"C:\Program Files\KiCad\8.0\bin\gerbview.exe"),
        ]
        if found_gerb := shutil.which("gerbview"):
            gerb_paths.insert(0, Path(found_gerb))
        for candidate in gerb_paths:
            if candidate.exists():
                _spawn_gui(candidate, p)
                return
        raise FileNotFoundError(f"KiCad GerbView was not found to open Gerber file '{p.name}'.")

    # Route Word documents (.docx, .doc) to Microsoft Word
    if ext in (".docx", ".doc"):
        word_paths = [
            Path(r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE"),
            Path(r"C:\Program Files (x86)\Microsoft Office\root\Office16\WINWORD.EXE"),
            Path(r"C:\Program Files\Microsoft Office\Office16\WINWORD.EXE"),
            Path(r"C:\Program Files (x86)\Microsoft Office\Office16\WINWORD.EXE"),
        ]
        if found_word := shutil.which("winword"):
            word_paths.insert(0, Path(found_word))
        for candidate in word_paths:
            if candidate.exists():
                _spawn_gui(candidate, p, hints=["Word", p.stem, "Document"])
                return
        try:
            os.startfile(str(p))
            return
        except Exception:
            _open_document(p)
            return

    # Route PDF documents (.pdf) to Microsoft Edge or Chrome PDF Viewer
    if ext == ".pdf":
        pdf_viewers = [
            Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
            Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
            Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
            Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
        ]
        if found_edge := shutil.which("msedge"):
            pdf_viewers.insert(0, Path(found_edge))
        if found_chrome := shutil.which("chrome"):
            pdf_viewers.append(Path(found_chrome))
        for candidate in pdf_viewers:
            if candidate.exists():
                _spawn_gui(candidate, p, hints=["Edge", "Chrome", p.stem])
                return
        try:
            os.startfile(str(p))
            return
        except Exception:
            _open_document(p)
            return

    # Route Excel spreadsheets (.xlsx, .xls) to Microsoft Excel
    if ext in (".xlsx", ".xls"):
        excel_paths = [
            Path(r"C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE"),
            Path(r"C:\Program Files (x86)\Microsoft Office\root\Office16\EXCEL.EXE"),
            Path(r"C:\Program Files\Microsoft Office\Office16\EXCEL.EXE"),
        ]
        if found_excel := shutil.which("excel"):
            excel_paths.insert(0, Path(found_excel))
        for candidate in excel_paths:
            if candidate.exists():
                _spawn_gui(candidate, p, hints=["Excel", p.stem])
                return
        try:
            os.startfile(str(p))
            return
        except Exception:
            _open_document(p)
            return

    # Safe general documentation, data, scripts, and logs
    if ext in (
        ".txt", ".json", ".md", ".csv", ".html", ".htm", ".log",
        ".lua", ".xml", ".kicad_prl",
    ):
        _open_document(p)
        return

    raise ValueError(
        f"Unsupported or unrecognized engineering file type '{ext}' for file '{p.name}'. "
        "Native tool routing only dispatches recognized CAD, EDA, SPICE, FEA, and system simulation artifacts."
    )


NATIVE_EXTENSIONS = {
    ".kicad_pro", ".kicad_pcb", ".kicad_sch", ".kicad_prl", ".pro", ".sch",
    ".asc", ".cir", ".net", ".raw", ".op.raw",
    ".fem", ".ans", ".fee", ".step", ".stp", ".stl", ".fcstd", ".mo", ".moe",
    ".gbr", ".gtl", ".gbl", ".gts", ".gbs", ".gto", ".gbo", ".gm1", ".drl",
    ".txt", ".json", ".md", ".csv", ".html", ".htm", ".pdf", ".log",
    ".lua", ".docx", ".xlsx", ".xml",
}


def get_tool_for_extension(path: Path | str) -> tuple[str, str] | None:
    """Returns the dedicated (tool_id, display_name) tuple for a given file path based on extension."""
    ext = Path(path).suffix.lower()
    mapping = {
        ".step": ("freecad", "FreeCAD 3D CAD"),
        ".stp": ("freecad", "FreeCAD 3D CAD"),
        ".stl": ("freecad", "FreeCAD 3D CAD"),
        ".fcstd": ("freecad", "FreeCAD 3D CAD"),
        ".kicad_sch": ("kicad_sch", "KiCad Schematic Editor"),
        ".sch": ("kicad_sch", "KiCad Schematic Editor"),
        ".kicad_pcb": ("kicad_pcb", "KiCad PCB Editor"),
        ".kicad_pro": ("kicad", "KiCad Project Manager"),
        ".pro": ("kicad", "KiCad Project Manager"),
        ".asc": ("ltspice", "ADI LTspice (Schematic)"),
        ".net": ("ltspice", "ADI LTspice (Netlist)"),
        ".cir": ("ltspice", "ADI LTspice (Circuit)"),
        ".raw": ("ltspice", "ADI LTspice (Waveforms)"),
        ".op.raw": ("ltspice", "ADI LTspice (Operating Point)"),
        ".fem": ("femm", "FEMM 4.2 Magnetics"),
        ".ans": ("femm", "FEMM 4.2 Magnetics"),
        ".fee": ("femm", "FEMM 4.2 Electrostatics"),
        ".mo": ("omedit", "OpenModelica OMEdit"),
        ".moe": ("omedit", "OpenModelica OMEdit"),
        ".gbr": ("kicad_gerbview", "KiCad GerbView"),
        ".drl": ("kicad_gerbview", "KiCad GerbView"),
    }
    return mapping.get(ext)


def launch_tool(tool_id: str, path: Path) -> dict:
    """Launches a specific engineering tool directly with the target file as input."""
    p = Path(path).resolve()
    if not p.exists():
        raise FileNotFoundError(f"Target path does not exist: {p}")

    ext = p.suffix.lower()
    tool_id = tool_id.lower().strip()
    executable: Path | None = None

    if tool_id in ("ltspice", "spice"):
        if ext not in (".asc", ".net", ".cir", ".raw", ".op.raw"):
            raise ValueError(f"LTspice requires a SPICE schematic (.asc), netlist (.net/.cir), or waveform (.raw), but received '{p.name}' ({ext}).")
        for cand in [
            Path(r"C:\Program Files\ADI\LTspice\LTspice.exe"),
            Path(r"C:\Program Files\LTC\LTspiceXVII\XVIIx64.exe"),
        ]:
            if cand.exists():
                executable = cand
                break
        if not executable and (found := shutil.which("LTspice")):
            executable = Path(found)
        if not executable:
            raise FileNotFoundError("LTspice executable was not found on this system.")
        return _spawn_gui(executable, p)

    elif tool_id in ("freecad", "cad"):
        if ext not in (".step", ".stp", ".stl", ".fcstd"):
            raise ValueError(f"FreeCAD requires a 3D CAD model (.step, .stp, .stl, .fcstd), but received '{p.name}' ({ext}).")
        for cand in [
            Path(r"C:\Program Files\FreeCAD 1.1\bin\freecad.exe"),
            Path(r"C:\Program Files\FreeCAD 1.0\bin\freecad.exe"),
            Path(r"C:\Program Files\FreeCAD 0.21\bin\freecad.exe"),
        ]:
            if cand.exists():
                executable = cand
                break
        if not executable and (found := shutil.which("freecad")):
            executable = Path(found)
        if not executable:
            raise FileNotFoundError("FreeCAD executable was not found on this system.")
        return _spawn_gui(executable, p)

    elif tool_id in ("kicad_sch", "eeschema"):
        if ext not in (".kicad_sch", ".sch"):
            raise ValueError(f"KiCad Schematic Editor requires a schematic file (.kicad_sch), but received '{p.name}' ({ext}). For 3D CAD models, open in FreeCAD.")
        for cand in [
            Path(r"C:\Program Files\KiCad\10.0\bin\eeschema.exe"),
            Path(r"C:\Program Files\KiCad\9.0\bin\eeschema.exe"),
            Path(r"C:\Program Files\KiCad\8.0\bin\eeschema.exe"),
        ] + [
            Path(r"C:\Program Files\KiCad\10.0\bin\kicad.exe"),
            Path(r"C:\Program Files\KiCad\9.0\bin\kicad.exe"),
        ]:
            if cand.exists():
                executable = cand
                break
        if not executable and (found := shutil.which("eeschema") or shutil.which("kicad")):
            executable = Path(found)
        if not executable:
            raise FileNotFoundError("KiCad Schematic Editor (eeschema.exe) was not found.")
        return _spawn_gui(executable, p)

    elif tool_id in ("kicad_pcb", "pcbnew"):
        if ext not in (".kicad_pcb",):
            raise ValueError(f"KiCad PCB Editor requires a board layout file (.kicad_pcb), but received '{p.name}' ({ext}).")
        for cand in [
            Path(r"C:\Program Files\KiCad\10.0\bin\pcbnew.exe"),
            Path(r"C:\Program Files\KiCad\9.0\bin\pcbnew.exe"),
            Path(r"C:\Program Files\KiCad\8.0\bin\pcbnew.exe"),
        ] + [
            Path(r"C:\Program Files\KiCad\10.0\bin\kicad.exe"),
            Path(r"C:\Program Files\KiCad\9.0\bin\kicad.exe"),
        ]:
            if cand.exists():
                executable = cand
                break
        if not executable and (found := shutil.which("pcbnew") or shutil.which("kicad")):
            executable = Path(found)
        if not executable:
            raise FileNotFoundError("KiCad PCB Editor (pcbnew.exe) was not found.")
        return _spawn_gui(executable, p)

    elif tool_id in ("kicad", "kicad_project"):
        if ext in (".kicad_sch", ".sch"):
            return launch_tool("kicad_sch", p)
        if ext in (".kicad_pcb",):
            return launch_tool("kicad_pcb", p)
        if ext not in (".kicad_pro", ".pro") and not p.is_dir():
            raise ValueError(f"KiCad Project Manager requires a project file (.kicad_pro) or directory, but received '{p.name}' ({ext}). For 3D CAD models, open in FreeCAD.")
        for cand in [
            Path(r"C:\Program Files\KiCad\10.0\bin\kicad.exe"),
            Path(r"C:\Program Files\KiCad\9.0\bin\kicad.exe"),
            Path(r"C:\Program Files\KiCad\8.0\bin\kicad.exe"),
        ]:
            if cand.exists():
                executable = cand
                break
        if not executable and (found := shutil.which("kicad")):
            executable = Path(found)
        if not executable:
            raise FileNotFoundError("KiCad Project Manager (kicad.exe) was not found.")
        return _spawn_gui(executable, p)

    elif tool_id in ("femm", "magnetics"):
        if ext not in (".fem", ".ans", ".fee"):
            raise ValueError(f"FEMM 4.2 requires a finite element magnetics model (.fem, .ans), but received '{p.name}' ({ext}).")
        for cand in [
            Path(r"C:\femm42\bin\femm.exe"),
            Path(r"C:\Program Files\femm42\bin\femm.exe"),
        ]:
            if cand.exists():
                executable = cand
                break
        if not executable and (found := shutil.which("femm")):
            executable = Path(found)
        if not executable:
            raise FileNotFoundError("FEMM 4.2 executable was not found.")
        return _spawn_gui(executable, p)

    elif tool_id in ("omedit", "openmodelica"):
        if ext not in (".mo", ".moe"):
            raise ValueError(f"OpenModelica OMEdit requires a Modelica model (.mo), but received '{p.name}' ({ext}).")
        for cand in [
            Path(r"C:\Program Files\OpenModelica1.26.3-64bit\bin\OMEdit.exe"),
            Path(r"C:\Program Files\OpenModelica\bin\OMEdit.exe"),
        ]:
            if cand.exists():
                executable = cand
                break
        if not executable and (found := shutil.which("OMEdit")):
            executable = Path(found)
        if not executable:
            raise FileNotFoundError("OpenModelica OMEdit was not found.")
        return _spawn_gui(executable, p)

    elif tool_id in ("vscode", "code"):
        return launch_vscode(p if p.is_dir() else p.parent)

    else:
        # Fall back to native extension routing
        open_native(p)
        return {"tool": tool_id, "file": str(p), "status": "dispatched"}
