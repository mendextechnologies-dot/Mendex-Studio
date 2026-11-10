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
    ext = p.suffix.lower()

    # Route 3D CAD (.step / .stp) directly to FreeCAD to prevent improper association with KiCad schematic editor
    if ext in (".step", ".stp"):
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

    # Route FEMM magnetics & electrostatics models to femm.exe
    if ext in (".fem", ".ans"):
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

    # Route directories directly to explorer.exe
    if p.is_dir():
        subprocess.Popen(["explorer.exe", str(p)])
        return

    os.startfile(str(p))


NATIVE_EXTENSIONS = {
    ".kicad_pro", ".kicad_pcb", ".kicad_sch", ".asc", ".cir", ".net", ".raw", ".op.raw",
    ".fem", ".ans", ".step", ".stp", ".mo", ".moe", ".gbr", ".gtl", ".gbl", ".drl",
    ".txt", ".json", ".md", ".csv", ".html", ".pdf"
}
