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
from integrations.parsers.ltspice_parser import parse_ltspice_log, parse_ascii_raw_header
from integrations.runners.safe_runner import manifest_directory
from .base import BaseToolAdapter


class LTspiceAdapter(BaseToolAdapter):
    """Adapter for Analog Devices LTspice circuit simulator."""

    def __init__(self):
        super().__init__(
            tool_id="ltspice",
            name="LTspice",
            kind=ToolKind.APPLICATION,
            category="core",
            license_name="Proprietary Freeware (Analog Devices)",
            official_url="https://www.analog.com/ltspice",
            candidate_binaries=["LTspice.exe"],
            candidate_paths=[
                "ADI/LTspice/LTspice.exe",
                "LTC/LTspiceXVII/XVIIx64.exe",
            ],
        )

    def supported_operations(self) -> list[str]:
        return ["batch_simulate", "operating_point", "transient"]

    def verify_executable(self, exe_path: Path) -> bool:
        return exe_path.exists() and exe_path.is_file()

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
                error_message="LTspice is NOT_INSTALLED on this machine",
                diagnostics=[self.descriptor.diagnostic],
            )

        exe = Path(self.descriptor.executable_path)
        if not workdir:
            workdir = Path(request.workdir or Path.cwd() / "ltspice_run").resolve()
        workdir.mkdir(parents=True, exist_ok=True)

        netlist_file: Path | None = None
        if request.input_paths:
            candidate = Path(request.input_paths[0])
            if candidate.exists():
                netlist_file = candidate
        elif "netlist_text" in request.parameters:
            netlist_file = workdir / "circuit.net"
            netlist_file.write_text(request.parameters["netlist_text"], encoding="utf-8")

        if not netlist_file or not netlist_file.exists():
            now_iso = datetime.now(timezone.utc).isoformat()
            return JobResult(
                job_id=request.job_id,
                tool_id=self.tool_id,
                status=JobState.FAILED,
                start_time=now_iso,
                end_time=now_iso,
                exit_code=2,
                error_message="No valid netlist input provided for LTspice simulation",
                diagnostics=["Provide netlist file path in input_paths or netlist_text parameter"],
            )

        log_path = workdir / f"{netlist_file.stem}_run.log"
        # LTspice batch execution command: LTspice.exe -b -ascii <netlist>
        cmd = [str(exe), "-b", "-ascii", str(netlist_file.resolve())]

        exec_out = self._runner.run(
            command_args=cmd,
            cwd=workdir,
            timeout_s=request.timeout_s,
            log_file=log_path,
        )

        metrics: dict[str, float] = {}
        diagnostics: list[str] = []

        # Find generated .log and .raw
        ltspice_log = workdir / f"{netlist_file.stem}.log"
        ltspice_raw = workdir / f"{netlist_file.stem}.raw"

        if ltspice_log.exists():
            try:
                parsed_log = parse_ltspice_log(ltspice_log)
                metrics.update(parsed_log.metrics)
                for k, v in parsed_log.operating_points.items():
                    metrics[f"op_{k}"] = v
                if parsed_log.errors:
                    diagnostics.extend(parsed_log.errors)
            except Exception as e:
                diagnostics.append(f"Failed to parse LTspice log: {e}")

        if ltspice_raw.exists():
            try:
                raw_info = parse_ascii_raw_header(ltspice_raw)
                for k, v in raw_info.items():
                    if isinstance(v, (int, float)):
                        metrics[k] = float(v)
            except Exception:
                pass

        artifacts = manifest_directory(workdir, job_id=request.job_id)

        # Status determination: if errors found in log even with returncode 0
        final_status = exec_out.status
        if metrics.get("error_count", 0) > 0 and final_status == JobState.SUCCEEDED:
            final_status = JobState.FAILED

        return JobResult(
            job_id=request.job_id,
            tool_id=self.tool_id,
            status=final_status,
            start_time=exec_out.start_time,
            end_time=exec_out.end_time,
            exit_code=exec_out.exit_code,
            stdout=exec_out.stdout,
            stderr=exec_out.stderr,
            log_path=str(log_path) if log_path.exists() else None,
            artifacts=artifacts,
            metrics=metrics,
            diagnostics=diagnostics,
            error_message=exec_out.stderr if final_status == JobState.FAILED else None,
        )
