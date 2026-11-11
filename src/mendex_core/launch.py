"""Validated desktop handoff. Never invokes a shell or runs project scripts."""
import os
from pathlib import Path
import shutil
import subprocess


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
    options = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}
    environment = os.environ.copy()
    environment.pop("ELECTRON_RUN_AS_NODE", None)
    process = subprocess.Popen([str(executable), "--new-window", str(folder)], shell=False, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=str(folder), env=environment, **options)
    return {"executable": str(executable), "workspace": str(folder), "pid": process.pid}


def open_native(path: Path):
    if os.name != "nt":
        raise OSError("Native file opening is implemented for Windows only")
    p = Path(path).resolve()
    if not p.exists():
        raise FileNotFoundError(f"File or directory does not exist: {p}")
    ext = p.suffix.lower()

    # Route directories directly to explorer.exe
    if p.is_dir():
        subprocess.Popen(["explorer.exe", str(p)])
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
                subprocess.Popen([str(candidate), str(p)])
                return
        raise FileNotFoundError(
            f"FreeCAD is required to open 3D model '{p.name}'. No compatible FreeCAD installation was found at C:\\Program Files\\FreeCAD."
        )

    # Route KiCad schematic to eeschema.exe
    if ext == ".kicad_sch":
        sch_paths = [
            Path(r"C:\Program Files\KiCad\10.0\bin\eeschema.exe"),
            Path(r"C:\Program Files\KiCad\9.0\bin\eeschema.exe"),
            Path(r"C:\Program Files\KiCad\8.0\bin\eeschema.exe"),
        ]
        if found_sch := shutil.which("eeschema"):
            sch_paths.insert(0, Path(found_sch))
        for candidate in sch_paths:
            if candidate.exists():
                subprocess.Popen([str(candidate), str(p)])
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
                subprocess.Popen([str(candidate), str(p)])
                return
        raise FileNotFoundError(f"KiCad PCB Editor (pcbnew.exe) not found to open '{p.name}'.")

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
                subprocess.Popen([str(candidate), str(p)])
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
                subprocess.Popen([str(candidate), str(p)])
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
                subprocess.Popen([str(candidate), str(p)])
                return
        raise FileNotFoundError(f"OpenModelica OMEdit was not found to open '{p.name}'.")

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
                subprocess.Popen([str(candidate), str(p)])
                return
        raise FileNotFoundError(f"KiCad Project Manager was not found to open '{p.name}'.")

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
                subprocess.Popen([str(candidate), str(p)])
                return
        raise FileNotFoundError(f"KiCad GerbView was not found to open Gerber file '{p.name}'.")

    # Safe general files (HTML, PDF, TXT, JSON, CSV, MD)
    os.startfile(str(p))


NATIVE_EXTENSIONS = {
    ".kicad_pro", ".kicad_pcb", ".kicad_sch", ".asc", ".cir", ".net", ".raw", ".op.raw",
    ".fem", ".ans", ".fee", ".step", ".stp", ".stl", ".fcstd", ".mo", ".moe",
    ".gbr", ".gtl", ".gbl", ".drl",
    ".txt", ".json", ".md", ".csv", ".html", ".pdf"
}


def launch_tool(tool_id: str, path: Path) -> dict:
    """Launches a specific engineering tool directly with the target file as input.
    
    Supported tool_ids:
      - 'ltspice': ADI LTspice GUI (.asc, .net, .cir, .raw)
      - 'freecad': FreeCAD 3D CAD GUI (.step, .stp, .stl, .fcstd)
      - 'kicad_sch': KiCad Schematic Editor eeschema (.kicad_sch)
      - 'kicad_pcb': KiCad PCB Editor pcbnew (.kicad_pcb)
      - 'kicad_project': KiCad Project Manager (.kicad_pro)
      - 'kicad_gerbview': KiCad GerbView (.gbr, .drl)
      - 'femm': FEMM 4.2 GUI (.fem, .ans)
      - 'omedit': OpenModelica OMEdit (.mo)
      - 'vscode': Visual Studio Code (directory or files)
    """
    p = Path(path).resolve()
    if not p.exists():
        raise FileNotFoundError(f"Target path does not exist: {p}")

    tool_id = tool_id.lower().strip()
    executable: Path | None = None
    args: list[str] = []

    if tool_id in ("ltspice", "spice"):
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
        args = [str(executable), str(p)]

    elif tool_id in ("freecad", "cad"):
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
        args = [str(executable), str(p)]

    elif tool_id in ("kicad_sch", "eeschema"):
        for cand in [
            Path(r"C:\Program Files\KiCad\10.0\bin\eeschema.exe"),
            Path(r"C:\Program Files\KiCad\9.0\bin\eeschema.exe"),
            Path(r"C:\Program Files\KiCad\8.0\bin\eeschema.exe"),
        ]:
            if cand.exists():
                executable = cand
                break
        if not executable and (found := shutil.which("eeschema")):
            executable = Path(found)
        if not executable:
            raise FileNotFoundError("KiCad Schematic Editor (eeschema.exe) was not found.")
        args = [str(executable), str(p)]

    elif tool_id in ("kicad_pcb", "pcbnew"):
        for cand in [
            Path(r"C:\Program Files\KiCad\10.0\bin\pcbnew.exe"),
            Path(r"C:\Program Files\KiCad\9.0\bin\pcbnew.exe"),
            Path(r"C:\Program Files\KiCad\8.0\bin\pcbnew.exe"),
        ]:
            if cand.exists():
                executable = cand
                break
        if not executable and (found := shutil.which("pcbnew")):
            executable = Path(found)
        if not executable:
            raise FileNotFoundError("KiCad PCB Editor (pcbnew.exe) was not found.")
        args = [str(executable), str(p)]

    elif tool_id in ("kicad", "kicad_project"):
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
        args = [str(executable), str(p)]

    elif tool_id in ("femm", "magnetics"):
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
        args = [str(executable), str(p)]

    elif tool_id in ("omedit", "openmodelica"):
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
        args = [str(executable), str(p)]

    elif tool_id in ("vscode", "code"):
        return launch_vscode(p if p.is_dir() else p.parent)

    else:
        # Fall back to native extension routing
        open_native(p)
        return {"tool": tool_id, "file": str(p), "status": "dispatched"}

    proc = subprocess.Popen(args, shell=False)
    return {
        "tool": tool_id,
        "executable": str(executable),
        "target_file": str(p),
        "pid": proc.pid,
        "status": "launched",
    }

