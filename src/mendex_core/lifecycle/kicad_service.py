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


def _structure(path: Path) -> Dict[str, Any]:
    """Native population check (symbols / footprints with pads); failures count as unpopulated."""
    from ..pcb import native_structure
    try:
        return native_structure(path)
    except (ValueError, OSError, UnicodeDecodeError) as exc:
        return {"populated": False, "reason": f"Document could not be inspected: {exc}"}


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
        structure = _structure(sch)
        
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
            "structure": structure,
            # Rule checks on an unpopulated document check nothing: never report them as a pass.
            "evaluation": "NOT_EVALUATED" if not structure.get("populated") else ("PASSED" if res.returncode == 0 and parsed.get("total_issues", 1) == 0 else "FAILED"),
            "passed": bool(structure.get("populated")) and res.returncode == 0 and parsed.get("total_issues", 1) == 0,
        }

    def run_drc(self, pcb_path: Path, output_json: Optional[Path] = None, timeout: int = 300) -> Dict[str, Any]:
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
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, shell=False)
        structure = _structure(board)

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
            "structure": structure,
            # Rule checks on an unpopulated document check nothing: never report them as a pass.
            "evaluation": "NOT_EVALUATED" if not structure.get("populated") else ("PASSED" if res.returncode == 0 and parsed.get("total_issues", 1) == 0 else "FAILED"),
            "passed": bool(structure.get("populated")) and res.returncode == 0 and parsed.get("total_issues", 1) == 0,
        }

    def export_gerbers(
        self,
        pcb_path: Path,
        output_dir: Optional[Path] = None,
        require_routed: bool = True,
        check_drc: bool = True,
        force: bool = False,
        auto_route: bool = False,
    ) -> Path:
        """Exports manufacturing Gerbers for a KiCad PCB layout.

        Gated by routing completion and DRC verification. If auto_route=True, unrouted
        boards are automatically guided-routed and poured prior to Gerber generation.
        """
        board = pcb_path.resolve()
        if not board.exists():
            raise FileNotFoundError(f"PCB file not found: {board}")

        structure = _structure(board)
        routed_tracks = structure.get("segment", 0) + structure.get("arc", 0)

        if not force and auto_route and routed_tracks == 0:
            self.auto_route(board, pour_ground=True)
            structure = _structure(board)
            routed_tracks = structure.get("segment", 0) + structure.get("arc", 0)

        if not force:
            if require_routed and routed_tracks == 0:
                raise ValueError(
                    f"Refusing to export manufacturing Gerbers for {board.name}: "
                    f"board has 0 routed copper tracks (placement-only, {structure.get('footprint', 0)} footprints placed). "
                    "Complete PCB routing and pass DRC before generating manufacturing outputs."
                )
            if check_drc:
                if not self.is_available():
                    raise RuntimeError("KiCad CLI (kicad-cli) is not installed on this workstation.")
                drc_res = self.run_drc(board)
                if not drc_res.get("passed"):
                    total_issues = drc_res.get("parsed", {}).get("total_issues", "unknown")
                    raise ValueError(
                        f"Refusing to export manufacturing Gerbers for {board.name}: "
                        f"DRC failed with {total_issues} issues. "
                        "Resolve all DRC violations before exporting manufacturing Gerbers."
                    )

        if not self.is_available():
            raise RuntimeError("KiCad CLI (kicad-cli) is not installed on this workstation.")

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

    def export_drill(
        self,
        pcb_path: Path,
        output_dir: Optional[Path] = None,
        require_routed: bool = True,
        force: bool = False,
        auto_route: bool = False,
    ) -> Path:
        """Exports Excellon drill files for a KiCad PCB layout."""
        board = pcb_path.resolve()
        if not board.exists():
            raise FileNotFoundError(f"PCB file not found: {board}")

        structure = _structure(board)
        routed_tracks = structure.get("segment", 0) + structure.get("arc", 0)

        if not force and auto_route and routed_tracks == 0:
            self.auto_route(board, pour_ground=True)
            structure = _structure(board)
            routed_tracks = structure.get("segment", 0) + structure.get("arc", 0)

        if not force and require_routed and routed_tracks == 0:
            raise ValueError(
                f"Refusing to export drill files for {board.name}: "
                f"board has 0 routed copper tracks (placement-only, {structure.get('footprint', 0)} footprints placed). "
                "Complete PCB routing before generating manufacturing outputs."
            )

        if not self.is_available():
            raise RuntimeError("KiCad CLI (kicad-cli) is not installed on this workstation.")

        out_dir = output_dir.resolve() if output_dir else (board.parent / "gerbers").resolve()
        out_dir.mkdir(parents=True, exist_ok=True)
        cmd = [
            str(self.kicad_cli),
            "pcb",
            "export",
            "drill",
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

    def render_3d(
        self,
        pcb_path: Path,
        output_png: Optional[Path] = None,
        view: str = "iso",
        width: int = 1200,
        height: int = 900,
    ) -> Path:
        """Renders raytraced 3D image of the PCB layout using internal KiCad 10 raytracer."""
        from integrations.adapters.copper_kicad_adapter import CopperKiCadAdapter

        adapter = CopperKiCadAdapter(kicad_cli_path=str(self.kicad_cli) if self.kicad_cli else None)
        return adapter.render_3d(
            pcb_path=pcb_path,
            output_png=output_png,
            view=view,
            width=width,
            height=height,
        )

    def auto_route(
        self,
        pcb_path: Path,
        pour_ground: bool = True,
        ground_net: str = "GND",
        ripup: str = "all",
        default_track: float = 0.4,
        power_track: float = 1.2,
        power_patterns: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Routes unrouted PCB tracks and pours ground planes using internal Copper router."""
        from integrations.adapters.copper_kicad_adapter import CopperKiCadAdapter

        adapter = CopperKiCadAdapter(kicad_cli_path=str(self.kicad_cli) if self.kicad_cli else None)
        return adapter.route_pcb(
            pcb_path=pcb_path,
            pour_ground=pour_ground,
            ground_net=ground_net,
            ripup=ripup,
            default_track=default_track,
            power_track=power_track,
            power_patterns=power_patterns,
        )

    def apply_schematic(
        self,
        sch_path: Path,
        ops: List[Dict[str, Any]],
        verify: bool = True,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Applies batch schematic updates (symbol swaps, field edits) using internal Copper engine."""
        from integrations.adapters.copper_kicad_adapter import CopperKiCadAdapter

        adapter = CopperKiCadAdapter(kicad_cli_path=str(self.kicad_cli) if self.kicad_cli else None)
        return adapter.apply_schematic(sch_path, ops, verify=verify, dry_run=dry_run)
