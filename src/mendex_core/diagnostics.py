"""Workstation diagnostics: read-only checks, no native tool processes."""
from importlib import metadata
import platform
import shutil
import sys

from .launch import find_vscode
from .models import now


def diagnose(service):
    checks = []
    checks.append({"id": "python", "ok": sys.version_info[:2] == (3, 13), "detail": platform.python_version()})
    for distribution in ("pydantic", "PySide6"):
        try:
            version = metadata.version(distribution)
            checks.append({"id": distribution, "ok": True, "detail": version})
        except metadata.PackageNotFoundError:
            checks.append({"id": distribution, "ok": False, "detail": "Missing. Install requirements-lock.txt in the active virtual environment."})
    with service.connection() as db:
        integrity = db.execute("PRAGMA quick_check").fetchall()
        foreign_keys = db.execute("PRAGMA foreign_key_check").fetchall()
        schema_version = db.execute("PRAGMA user_version").fetchone()[0]
    checks.append({"id": "sqlite", "ok": integrity == [("ok",)] and not foreign_keys, "detail": f"schema={schema_version}; quick_check={integrity}; foreign_key_errors={len(foreign_keys)}"})
    vscode = find_vscode()
    checks.append({"id": "vscode", "ok": vscode is not None, "detail": str(vscode) if vscode else "VS Code not found; install separately."})
    checks.append({"id": "git", "ok": shutil.which("git") is not None, "detail": shutil.which("git") or "Git not found; needed for source development."})
    tools = [tool.model_dump(mode="json") for tool in service.list_tools()]
    framework_ready = all(check["ok"] for check in checks if check["id"] in ("python", "pydantic", "PySide6", "sqlite"))
    return {
        "schema_version": "1.0", "generated_at": now().isoformat(),
        "status": "PARTIAL" if framework_ready else "BLOCKED",
        "framework_ready": framework_ready,
        "environment": {"os": platform.platform(), "architecture": platform.machine(), "python_executable": sys.executable},
        "checks": checks, "tools": tools,
        "limitations": ["Native tool compatibility and reference benchmarks are unverified; engineering workstation readiness is PARTIAL.", "No simulator or hardware test is executed by diagnostics.", "Second-machine qualification and manufacturing approval are not established."],
    }
