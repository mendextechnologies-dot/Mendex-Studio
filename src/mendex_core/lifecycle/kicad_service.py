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

    def __init__(self, kicad_cli_path: Optional[str] = None, service: Optional[Any] = None):
        self.service = service
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

    def run_drc(
        self,
        pcb_path: Path,
        output_json: Optional[Path] = None,
        timeout: int = 300,
        severity_error: bool = False,
    ) -> Dict[str, Any]:
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
        ]
        if severity_error:
            cmd.append("--severity-error")
        cmd.append(str(board))
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
        layers: Optional[str] = None,
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
                drc_res = self.run_drc(board, severity_error=True)
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
            "--no-protel-ext",
            "--layers",
            layers or "F.Cu,B.Cu,F.Paste,B.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts",
            "--output",
            str(out_dir),
            str(board),
        ]
        subprocess.run(cmd, capture_output=True, text=True, timeout=90, check=True)
        return out_dir

    def export_pos(
        self,
        pcb_path: Path,
        output_file: Optional[Path] = None,
        side: str = "both",
        format: str = "csv",
        units: str = "mm",
    ) -> Path:
        """Exports component placement / pick-and-place (.pos / CPL) file."""
        if not self.is_available():
            raise RuntimeError("KiCad CLI (kicad-cli) is not installed on this workstation.")
        board = pcb_path.resolve()
        if not board.exists():
            raise FileNotFoundError(f"PCB file not found: {board}")

        out_pos = output_file.resolve() if output_file else (board.parent / "gerbers" / f"{board.stem}_cpl.csv").resolve()
        out_pos.parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            str(self.kicad_cli),
            "pcb",
            "export",
            "pos",
            "--side",
            side,
            "--format",
            format,
            "--units",
            units,
            "--output",
            str(out_pos),
            str(board),
        ]
        subprocess.run(cmd, capture_output=True, text=True, timeout=60, check=True)
        return out_pos

    def export_ipcd356(
        self,
        pcb_path: Path,
        output_file: Optional[Path] = None,
    ) -> Path:
        """Exports IPC-D-356 bare board electrical test netlist file."""
        if not self.is_available():
            raise RuntimeError("KiCad CLI (kicad-cli) is not installed on this workstation.")
        board = pcb_path.resolve()
        if not board.exists():
            raise FileNotFoundError(f"PCB file not found: {board}")

        out_d356 = output_file.resolve() if output_file else (board.parent / "gerbers" / f"{board.stem}.d356").resolve()
        out_d356.parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            str(self.kicad_cli),
            "pcb",
            "export",
            "ipcd356",
            "--output",
            str(out_d356),
            str(board),
        ]
        subprocess.run(cmd, capture_output=True, text=True, timeout=60, check=True)
        return out_d356

    def export_stats(
        self,
        pcb_path: Path,
        output_file: Optional[Path] = None,
        format: str = "json",
    ) -> Path:
        """Exports board statistics report (dimensions, drill counts, pad density)."""
        if not self.is_available():
            raise RuntimeError("KiCad CLI (kicad-cli) is not installed on this workstation.")
        board = pcb_path.resolve()
        if not board.exists():
            raise FileNotFoundError(f"PCB file not found: {board}")

        out_stats = output_file.resolve() if output_file else (board.parent / "gerbers" / f"{board.stem}_stats.json").resolve()
        out_stats.parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            str(self.kicad_cli),
            "pcb",
            "export",
            "stats",
            "--format",
            format,
            "--output",
            str(out_stats),
            str(board),
        ]
        subprocess.run(cmd, capture_output=True, text=True, timeout=60, check=True)
        return out_stats

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
            "--force",
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

    def export_schematic_svg(
        self,
        schematic_path: Path,
        output_dir: Optional[Path] = None,
        theme: Optional[str] = None,
    ) -> Path:
        """Exports a publication-grade native vector SVG of a KiCad schematic sheet."""
        if not self.is_available():
            raise RuntimeError("KiCad CLI (kicad-cli) is not installed on this workstation.")
        sch = schematic_path.resolve()
        if not sch.exists():
            raise FileNotFoundError(f"Schematic file not found: {sch}")

        out_dir = output_dir.resolve() if output_dir else (sch.parent / "svg").resolve()
        out_dir.mkdir(parents=True, exist_ok=True)
        cmd = [
            str(self.kicad_cli),
            "sch",
            "export",
            "svg",
            "--output",
            str(out_dir),
        ]
        if theme:
            cmd.extend(["--theme", theme])
        cmd.append(str(sch))
        subprocess.run(cmd, capture_output=True, text=True, timeout=60, check=True)
        
        cand_svgs = list(out_dir.glob(f"{sch.stem}*.svg")) or list(out_dir.glob("*.svg"))
        if not cand_svgs:
            raise FileNotFoundError(f"KiCad CLI did not produce an SVG in {out_dir}")
        return cand_svgs[0]

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
        thermal_spoke: float = 0.5,
        thermal_gap: float = 0.5,
        pad_connection: str = "tht_thermal",
        stitch_ground: bool = False,
        stitch_pitch: float = 5.0,
        zone_clearance: float = 0.5,
        pour_layers: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Routes unrouted PCB tracks and pours ground planes with customizable thermal spokes and zone clearances."""
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
            thermal_spoke=thermal_spoke,
            thermal_gap=thermal_gap,
            pad_connection=pad_connection,
            stitch_ground=stitch_ground,
            stitch_pitch=stitch_pitch,
            zone_clearance=zone_clearance,
            pour_layers=pour_layers,
        )

    def mill_isolation_slot(
        self,
        pcb_path: Path,
        slot_width: float = 2.5,
        slot_length: Optional[float] = None,
        center_x: Optional[float] = None,
        center_y: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Mills an Edge.Cuts isolation air slot and refills copper zones."""
        from integrations.adapters.copper_kicad_adapter import CopperKiCadAdapter

        adapter = CopperKiCadAdapter(kicad_cli_path=str(self.kicad_cli) if self.kicad_cli else None)
        return adapter.mill_isolation_slot(
            pcb_path=pcb_path,
            slot_width=slot_width,
            slot_length=slot_length,
            center_x=center_x,
            center_y=center_y,
        )

    def setup_4layer_planes(
        self,
        pcb_path: Path,
        gnd_net: str = "PRI_GND",
        pwr_net: str = "VIN",
        zone_clearance: float = 0.5,
        thermal_spoke: float = 0.5,
        pad_connection: str = "tht_thermal",
    ) -> Dict[str, Any]:
        """Configures IPC-2152 4-layer internal power and ground planes on In1.Cu and In2.Cu."""
        from integrations.adapters.copper_kicad_adapter import CopperKiCadAdapter

        adapter = CopperKiCadAdapter(kicad_cli_path=str(self.kicad_cli) if self.kicad_cli else None)
        return adapter.setup_four_layer_power_planes(
            pcb_path=pcb_path,
            gnd_net=gnd_net,
            pwr_net=pwr_net,
            zone_clearance=zone_clearance,
            thermal_spoke=thermal_spoke,
            pad_connection=pad_connection,
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


    def forward_annotate_pcb(
        self,
        pcb_path: Path,
        sch_path: Optional[Path] = None,
        remove_extra: bool = True,
        auto_place_new: bool = True,
        refill_zones: bool = True,
    ) -> Dict[str, Any]:
        """Forward-annotates incremental schematic changes to the PCB layout using Copper ECO Engine."""
        from integrations.adapters.copper_kicad_adapter import CopperKiCadAdapter

        adapter = CopperKiCadAdapter(kicad_cli_path=str(self.kicad_cli) if self.kicad_cli else None)
        return adapter.forward_annotate_pcb(
            pcb_path=pcb_path,
            sch_path=sch_path,
            remove_extra=remove_extra,
            auto_place_new=auto_place_new,
            refill_zones=refill_zones,
        )


    def export_fab_pack(
        self,
        pcb_path: Path,
        profile: str = "jlcpcb",
        output_zip: Optional[Path] = None,
        waive: Optional[List[str]] = None,
        auto_route: bool = True,
    ) -> Dict[str, Any]:
        """Exports a production fabrication bundle (Gerbers + Drill + IPC-D-356) using Copper export_fab.

        If auto_route=True and the board has 0 tracks, it routes first.
        Returns metadata including output zip path, sha256, and profile.
        """
        board = pcb_path.resolve()
        if not board.exists():
            raise FileNotFoundError(f"PCB file not found: {board}")

        structure = _structure(board)
        routed_tracks = structure.get("segment", 0) + structure.get("arc", 0)
        if auto_route and routed_tracks == 0:
            self.auto_route(board, pour_ground=True)

        from integrations.adapters.copper_kicad_adapter import CopperKiCadAdapter

        adapter = CopperKiCadAdapter(kicad_cli_path=str(self.kicad_cli) if self.kicad_cli else None)

        norm_profile = "jlcpcb" if profile.lower() in ("jlc", "jlcpcb", "default") else profile

        res = adapter.export_fab(
            pcb_path=board,
            profile=norm_profile,
            waive=waive if waive is not None else ["parts"],
        )
        if res.get("success") and res.get("zip_path"):
            zip_p = Path(res["zip_path"])
            if zip_p.exists():
                import hashlib
                hasher = hashlib.sha256()
                with open(zip_p, "rb") as fh:
                    while chunk := fh.read(65536):
                        hasher.update(chunk)
                res["sha256"] = hasher.hexdigest()

                # Automated Lifecycle Artifact Ingestion
                svc = getattr(self, "service", None)
                if svc:
                    try:
                        for prod in svc.list_products():
                            for rev in svc.list_revisions(prod.product_id):
                                ws = svc.workspace_path(rev)
                                if board.is_relative_to(ws):
                                    from ..design.models import ArtifactKind
                                    from ..desktop.service import _ingest_design_artifact
                                    _ingest_design_artifact(
                                        svc,
                                        rev,
                                        ArtifactKind.GERBER_BUNDLE,
                                        zip_p,
                                        zip_p.name,
                                        "zip",
                                        f"Production Fabrication Package ({norm_profile.upper()})",
                                    )
                                    break
                    except Exception:
                        pass
        return res
