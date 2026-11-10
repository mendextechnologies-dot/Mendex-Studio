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
    os.startfile(str(path))


NATIVE_EXTENSIONS = {".kicad_pro", ".kicad_pcb", ".kicad_sch", ".asc", ".cir", ".fem", ".step", ".stp", ".txt", ".json", ".md", ".csv", ".html", ".pdf"}
