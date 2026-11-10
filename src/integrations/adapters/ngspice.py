from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
import os

from integrations.contracts import (
    ToolDescriptor,
    ToolKind,
    ToolState,
    JobRequest,
    JobResult,
    JobState,
)
from integrations.runners.safe_runner import manifest_directory
from .base import BaseToolAdapter


class NgspiceAdapter(BaseToolAdapter):
    """Adapter for ngspice open-source mixed-level/mixed-signal circuit simulator."""

    def __init__(self):
        super().__init__(
            tool_id="ngspice",
            name="ngspice",
            kind=ToolKind.APPLICATION,
            category="core",
            license_name="BSD 3-Clause (Open Source)",
            official_url="https://ngspice.sourceforge.io/",
            candidate_binaries=["ngspice.exe", "ngspice"],
            candidate_paths=[
                "Spice64/bin/ngspice.exe",
                "Spice64/bin/ngspice_con.exe",
                "ngspice/bin/ngspice.exe",
                "Program Files/Spice64/bin/ngspice.exe",
            ],
        )

    def supported_operations(self) -> list[str]:
        return ["batch_simulate", "operating_point", "transient"]

    def execute(self, request: JobRequest, workdir: Path | None = None) -> JobResult:
        now_iso = datetime.now(timezone.utc).isoformat()
        target_dir = workdir or Path.cwd()

        if self.descriptor.state not in (ToolState.READY, ToolState.DETECTED):
            return JobResult(
                job_id=request.job_id,
                tool_id=self.descriptor.tool_id,
                status=JobState.FAILED,
                error_message=f"Tool {self.descriptor.name} is not installed or available for execution.",
                start_time=now_iso,
                end_time=now_iso,
            )

        exe = self.descriptor.executable_path
        if not exe or not Path(exe).exists():
            return JobResult(
                job_id=request.job_id,
                tool_id=self.descriptor.tool_id,
                status=JobState.FAILED,
                error_message="ngspice executable path not found",
                start_time=now_iso,
                end_time=now_iso,
            )

        # Prepare netlist
        netlist_file: Path | None = None
        if "netlist_path" in request.parameters:
            cand = Path(request.parameters["netlist_path"])
            if cand.exists():
                netlist_file = cand
        elif "netlist_text" in request.parameters:
            netlist_file = target_dir / "circuit.cir"
            netlist_file.write_text(request.parameters["netlist_text"], encoding="utf-8")

        if not netlist_file or not netlist_file.exists():
            return JobResult(
                job_id=request.job_id,
                tool_id=self.descriptor.tool_id,
                status=JobState.FAILED,
                error_message="No valid netlist provided in parameters (netlist_path or netlist_text).",
                start_time=now_iso,
                end_time=now_iso,
            )

        log_file = target_dir / "circuit.log"
        raw_file = target_dir / "circuit.raw"
        command = [exe, "-b", "-r", str(raw_file.name), "-o", str(log_file.name), str(netlist_file.resolve())]

        exec_res = self.runner.run(
            command_args=command,
            cwd=target_dir,
            timeout_s=request.timeout_s,
            log_file=log_file,
        )

        status = JobState.SUCCEEDED if exec_res.exit_code == 0 else JobState.FAILED
        artifacts = manifest_directory(target_dir)

        return JobResult(
            job_id=request.job_id,
            tool_id=self.descriptor.tool_id,
            status=status,
            exit_code=exec_res.exit_code,
            log_path=str(log_file) if log_file.exists() else None,
            artifacts=artifacts,
            start_time=now_iso,
            end_time=datetime.now(timezone.utc).isoformat(),
        )
