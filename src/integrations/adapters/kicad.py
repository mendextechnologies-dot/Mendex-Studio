from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from integrations.contracts import (
    ToolDescriptor,
    ToolKind,
    ToolState,
    JobRequest,
    JobResult,
    JobState,
)
from integrations.parsers.kicad_parser import parse_kicad_drc_json
from integrations.runners.safe_runner import manifest_directory
from .base import BaseToolAdapter


class KiCadAdapter(BaseToolAdapter):
    """Adapter for KiCad CLI (ERC/DRC and manufacturing export)."""

    def __init__(self):
        super().__init__(
            tool_id="kicad",
            name="KiCad CLI",
            kind=ToolKind.APPLICATION,
            category="core",
            license_name="GPLv3+",
            official_url="https://www.kicad.org/",
            candidate_binaries=["kicad-cli.exe", "kicad-cli"],
            candidate_paths=["KiCad/*/bin/kicad-cli.exe", "KiCad/bin/kicad-cli.exe"],
        )

    def supported_operations(self) -> list[str]:
        return ["erc", "drc", "export_gerber", "export_step", "render_3d", "route", "version"]

    def execute(self, request: JobRequest, workdir: Path | None = None) -> JobResult:
        if self.descriptor.state == ToolState.NOT_INSTALLED or not self.descriptor.executable_path:
            now_iso = datetime.now(timezone.utc).isoformat()
            return JobResult(
                job_id=request.job_id,
                tool_id=self.tool_id,
                status=JobState.FAILED,
                start_time=now_iso,
                end_time=now_iso,
                exit_code=1,
                error_message="KiCad CLI is NOT_INSTALLED on this machine",
                diagnostics=[self.descriptor.diagnostic],
            )

        exe = Path(self.descriptor.executable_path)
        if not workdir:
            workdir = Path(request.workdir or Path.cwd() / "kicad_run").resolve()
        workdir.mkdir(parents=True, exist_ok=True)

        operation = request.operation or "version"
        log_file = workdir / f"kicad_{operation}.log"

        if operation == "version":
            cmd = [str(exe), "version"]
        elif operation == "drc":
            input_file = Path(request.input_paths[0]) if request.input_paths else (workdir / "board.kicad_pcb")
            output_report = workdir / "drc_report.json"
            cmd = [str(exe), "pcb", "drc", "--output", str(output_report.resolve()), "--format", "json", str(input_file.resolve())]
        elif operation == "erc":
            input_file = Path(request.input_paths[0]) if request.input_paths else (workdir / "schematic.kicad_sch")
            output_report = workdir / "erc_report.json"
            cmd = [str(exe), "sch", "erc", "--output", str(output_report.resolve()), "--format", "json", str(input_file.resolve())]
        elif operation == "export_step":
            input_file = Path(request.input_paths[0]) if request.input_paths else (workdir / "board.kicad_pcb")
            output_step = workdir / f"{input_file.stem}.step"
            cmd = [str(exe), "pcb", "export", "step", "--output", str(output_step.resolve()), str(input_file.resolve())]
        elif operation in ("export_gerber", "export_gerbers"):
            input_file = Path(request.input_paths[0]) if request.input_paths else (workdir / "board.kicad_pcb")
            force = bool((request.parameters or {}).get("force", False))
            auto_route_param = bool((request.parameters or {}).get("auto_route", False))

            if not force and input_file.exists() and auto_route_param:
                from integrations.adapters.copper_kicad_adapter import CopperKiCadAdapter
                copper = CopperKiCadAdapter(kicad_cli_path=str(exe))
                copper.route_pcb(input_file)

            if not force and input_file.exists():
                from mendex_core.pcb import native_structure
                struct = None
                try:
                    struct = native_structure(input_file)
                except (ValueError, OSError):
                    pass
                if struct is not None:
                    routed_tracks = struct.get("segment", 0) + struct.get("arc", 0)
                    if routed_tracks == 0:
                        from datetime import datetime, timezone
                        now_iso = datetime.now(timezone.utc).isoformat()
                        return JobResult(
                            job_id=request.job_id,
                            tool_id=self.tool_id,
                            status=JobState.FAILED,
                            start_time=now_iso,
                            end_time=now_iso,
                            exit_code=1,
                            stdout="",
                            stderr=f"Refusing to export Gerbers: board has 0 routed tracks (placement only, {struct.get('footprint', 0)} footprints). Complete routing and verify DRC passes before manufacturing export.",
                            error_message="Refusing to export Gerbers: board has 0 routed copper tracks (placement only).",
                            diagnostics=["Board is placement-only (0 copper tracks). Manufacturing Gerber export blocked."],
                            artifacts=[],
                        )

            gerber_dir = workdir / "gerbers"
            gerber_dir.mkdir(parents=True, exist_ok=True)
            cmd = [str(exe), "pcb", "export", "gerbers", "--output", str(gerber_dir.resolve()), str(input_file.resolve())]
        elif operation == "render_3d":
            input_file = Path(request.input_paths[0]) if request.input_paths else (workdir / "board.kicad_pcb")
            output_png = workdir / f"{input_file.stem}_3d.png"
            from integrations.adapters.copper_kicad_adapter import CopperKiCadAdapter
            copper = CopperKiCadAdapter(kicad_cli_path=str(exe))
            view = (request.parameters or {}).get("view", "iso")
            width = int((request.parameters or {}).get("width", 1200))
            copper.render_3d(input_file, output_png=output_png, view=view, width=width)
            cmd = [str(exe), "version"]
        elif operation == "route":
            input_file = Path(request.input_paths[0]) if request.input_paths else (workdir / "board.kicad_pcb")
            from integrations.adapters.copper_kicad_adapter import CopperKiCadAdapter
            copper = CopperKiCadAdapter(kicad_cli_path=str(exe))
            pour = bool((request.parameters or {}).get("pour_ground", True))
            ground_net = (request.parameters or {}).get("ground_net", "GND")
            copper.route_pcb(input_file, pour_ground=pour, ground_net=ground_net)
            cmd = [str(exe), "version"]
        else:
            raise NotImplementedError(f"Unsupported KiCad operation: {operation}")

        exec_out = self._runner.run(
            command_args=cmd,
            cwd=workdir,
            timeout_s=request.timeout_s,
            log_file=log_file,
        )

        metrics: dict[str, float] = {}
        diagnostics: list[str] = []

        drc_json = workdir / "drc_report.json"
        erc_json = workdir / "erc_report.json"
        target_report = drc_json if drc_json.exists() else erc_json if erc_json.exists() else None
        if target_report:
            try:
                summary = parse_kicad_drc_json(target_report)
                for k, v in summary.items():
                    metrics[k] = float(v)
            except Exception as e:
                diagnostics.append(f"Failed to parse report: {e}")

        artifacts = manifest_directory(workdir, job_id=request.job_id)

        status = JobState.SUCCEEDED if exec_out.exit_code == 0 else JobState.FAILED

        return JobResult(
            job_id=request.job_id,
            tool_id=self.tool_id,
            status=status,
            start_time=exec_out.start_time,
            end_time=exec_out.end_time,
            exit_code=exec_out.exit_code,
            stdout=exec_out.stdout,
            stderr=exec_out.stderr,
            log_path=str(log_file) if log_file.exists() else None,
            artifacts=artifacts,
            metrics=metrics,
            diagnostics=diagnostics,
            error_message=exec_out.stderr if status == JobState.FAILED else None,
        )
