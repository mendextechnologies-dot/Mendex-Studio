"""KiCad schematic and PCB workflow service for product lifecycle engineering."""
from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from integrations.parsers.kicad_parser import parse_kicad_drc_json


class KiCadLifecycleService:
    """Manages KiCad schematic capture, PCB layout, ERC/DRC runs, and manufacturing exports."""

    def __init__(self, kicad_cli_path: Optional[str] = None):
        self.kicad_cli = self._resolve_kicad_cli(kicad_cli_path)
        self.kicad_gui = self._resolve_kicad_gui()

    def _resolve_kicad_cli(self, candidate: Optional[str]) -> Optional[Path]:
        if candidate and Path(candidate).exists():
            return Path(candidate).resolve()
        common = [
            Path(r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe"),
            Path(r"C:\Program Files\KiCad\8.0\bin\kicad-cli.exe"),
            Path(r"C:\Program Files\KiCad\7.0\bin\kicad-cli.exe"),
        ]
        for p in common:
            if p.exists():
                return p
        which = shutil.which("kicad-cli.exe") or shutil.which("kicad-cli")
        return Path(which).resolve() if which else None

    def _resolve_kicad_gui(self) -> Optional[Path]:
        if self.kicad_cli:
            gui_cand = self.kicad_cli.parent / "kicad.exe"
            if gui_cand.exists():
                return gui_cand
        return None

    def is_available(self) -> bool:
        return self.kicad_cli is not None and self.kicad_cli.exists()

    def discover_files(self, workspace_path: Path) -> Dict[str, List[Path]]:
        """Scans workspace directory for KiCad schematics, boards, and reports."""
        schematics = list(workspace_path.glob("**/*.kicad_sch"))
        pcbs = list(workspace_path.glob("**/*.kicad_pcb"))
        erc_reports = list(workspace_path.glob("**/*erc*.json")) + list(workspace_path.glob("**/*erc*.txt"))
        drc_reports = list(workspace_path.glob("**/*drc*.json")) + list(workspace_path.glob("**/*drc*.txt"))
        gerbers = list(workspace_path.glob("**/gerbers/*"))
        return {
            "schematics": schematics,
            "pcbs": pcbs,
            "erc_reports": erc_reports,
            "drc_reports": drc_reports,
            "gerbers": gerbers,
        }

    def run_erc(self, schematic_path: Path, output_json: Optional[Path] = None) -> Dict[str, Any]:
        """Runs KiCad ERC in JSON format and returns structured violation metrics."""
        if not self.is_available():
            raise RuntimeError("KiCad CLI (kicad-cli) is not installed on this workstation.")
        sch = schematic_path.resolve()
        if not sch.exists():
            raise FileNotFoundError(f"Schematic file not found: {sch}")

        out_json = output_json.resolve() if output_json else (sch.parent / f"{sch.stem}_erc_{uuid4()}.json").resolve()
        if out_json.exists():
            raise FileExistsError("Choose a new report path; previous evidence cannot be overwritten")
        cmd = [
            str(self.kicad_cli),
            "sch",
            "erc",
            "--output",
            str(out_json),
            "--format",
            "json",
            str(sch),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=60, shell=False)
        
        parsed = {}
        diagnostic = ""
        if out_json.exists():
            try:
                parsed = parse_kicad_drc_json(out_json)
            except (ValueError, OSError) as exc:
                diagnostic = f"Report could not be evaluated: {exc}"
        else:
            diagnostic = "KiCad did not produce a report"

        return {
            "exit_code": res.returncode,
            "output_report": str(out_json),
            "stdout": res.stdout,
            "stderr": res.stderr,
            "parsed": parsed,
            "command": cmd,
            "diagnostic": diagnostic,
            "passed": res.returncode == 0 and parsed.get("total_issues", 1) == 0,
        }

    def run_drc(self, pcb_path: Path, output_json: Optional[Path] = None) -> Dict[str, Any]:
        """Runs KiCad PCB DRC in JSON format and returns clearance/track violation metrics."""
        if not self.is_available():
            raise RuntimeError("KiCad CLI (kicad-cli) is not installed on this workstation.")
        board = pcb_path.resolve()
        if not board.exists():
            raise FileNotFoundError(f"PCB file not found: {board}")

        out_json = output_json.resolve() if output_json else (board.parent / f"{board.stem}_drc_{uuid4()}.json").resolve()
        if out_json.exists():
            raise FileExistsError("Choose a new report path; previous evidence cannot be overwritten")
        cmd = [
            str(self.kicad_cli),
            "pcb",
            "drc",
            "--output",
            str(out_json),
            "--format",
            "json",
            str(board),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=60, shell=False)

        parsed = {}
        diagnostic = ""
        if out_json.exists():
            try:
                parsed = parse_kicad_drc_json(out_json)
            except (ValueError, OSError) as exc:
                diagnostic = f"Report could not be evaluated: {exc}"
        else:
            diagnostic = "KiCad did not produce a report"

        return {
            "exit_code": res.returncode,
            "output_report": str(out_json),
            "stdout": res.stdout,
            "stderr": res.stderr,
            "parsed": parsed,
            "command": cmd,
            "diagnostic": diagnostic,
            "passed": res.returncode == 0 and parsed.get("total_issues", 1) == 0,
        }

    def export_gerbers(self, pcb_path: Path, output_dir: Optional[Path] = None) -> Path:
        """Exports manufacturing Gerbers for a KiCad PCB layout."""
        if not self.is_available():
            raise RuntimeError("KiCad CLI (kicad-cli) is not installed on this workstation.")
        board = pcb_path.resolve()
        if not board.exists():
            raise FileNotFoundError(f"PCB file not found: {board}")

        out_dir = output_dir.resolve() if output_dir else (board.parent / "gerbers").resolve()
        out_dir.mkdir(parents=True, exist_ok=True)
        cmd = [
            str(self.kicad_cli),
            "pcb",
            "export",
            "gerbers",
            "--output",
            str(out_dir),
            str(board),
        ]
        subprocess.run(cmd, capture_output=True, text=True, timeout=90, check=True)
        return out_dir

    def export_step(self, pcb_path: Path, output_step: Optional[Path] = None) -> Path:
        """Exports a 3D STEP solid model of the populated PCB layout."""
        if not self.is_available():
            raise RuntimeError("KiCad CLI (kicad-cli) is not installed on this workstation.")
        board = pcb_path.resolve()
        if not board.exists():
            raise FileNotFoundError(f"PCB file not found: {board}")

        out_step = output_step.resolve() if output_step else (board.parent / f"{board.stem}.step").resolve()
        cmd = [
            str(self.kicad_cli),
            "pcb",
            "export",
            "step",
            "--output",
            str(out_step),
            str(board),
        ]
        subprocess.run(cmd, capture_output=True, text=True, timeout=90, check=True)
        return out_step

    def export_bom(self, schematic_path: Path, output_csv: Optional[Path] = None) -> Path:
        """Exports Bill of Materials CSV from schematic."""
        if not self.is_available():
            raise RuntimeError("KiCad CLI (kicad-cli) is not installed on this workstation.")
        sch = schematic_path.resolve()
        if not sch.exists():
            raise FileNotFoundError(f"Schematic file not found: {sch}")

        out_csv = output_csv.resolve() if output_csv else (sch.parent / f"{sch.stem}_bom.csv").resolve()
        cmd = [
            str(self.kicad_cli),
            "sch",
            "export",
            "bom",
            "--output",
            str(out_csv),
            str(sch),
        ]
        subprocess.run(cmd, capture_output=True, text=True, timeout=60, check=True)
        return out_csv
