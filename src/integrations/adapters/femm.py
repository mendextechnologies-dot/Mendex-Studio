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
from integrations.generators.femm_generator import generate_femm_transformer_script
from integrations.parsers.femm_parser import parse_femm_results
from integrations.runners.safe_runner import manifest_directory
from .base import BaseToolAdapter


class FEMMAdapter(BaseToolAdapter):
    """Adapter for Finite Element Method Magnetics (FEMM 4.2)."""

    def __init__(self):
        super().__init__(
            tool_id="femm",
            name="FEMM",
            kind=ToolKind.APPLICATION,
            category="core",
            license_name="Aladdin Free Public License",
            official_url="https://www.femm.info/",
            candidate_binaries=["femm.exe"],
            candidate_paths=["femm42/bin/femm.exe", "femm*/bin/femm.exe"],
        )

    def supported_operations(self) -> list[str]:
        return ["solve_2d_magnetic", "inductance_matrix", "core_loss"]

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
                error_message="FEMM is NOT_INSTALLED on this machine",
                diagnostics=[self.descriptor.diagnostic],
            )

        exe = Path(self.descriptor.executable_path)
        if not workdir:
            workdir = Path(request.workdir or Path.cwd() / "femm_run").resolve()
        workdir.mkdir(parents=True, exist_ok=True)

        lua_file: Path | None = None
        if request.input_paths:
            candidate = Path(request.input_paths[0])
            if candidate.exists():
                lua_file = candidate
        elif "lua_script" in request.parameters:
            lua_file = workdir / "femm_input.lua"
            lua_file.write_text(request.parameters["lua_script"], encoding="utf-8")
        else:
            core_type = request.parameters.get("core_type", "EE")
            primary_turns = int(request.parameters.get("primary_turns", 24))
            secondary_turns = int(request.parameters.get("secondary_turns", 1000))
            primary_current_a = float(request.parameters.get("primary_current_a", 2.5))
            air_gap_mm = float(request.parameters.get("air_gap_mm", 0.5))
            freq_hz = float(request.parameters.get("frequency_hz", 100000.0))
            script_text = generate_femm_transformer_script(
                core_type=core_type,
                primary_turns=primary_turns,
                secondary_turns=secondary_turns,
                primary_current_a=primary_current_a,
                air_gap_mm=air_gap_mm,
                frequency_hz=freq_hz,
                output_ans_path="transformer.ans",
                results_txt_path="results.txt",
            )
            lua_file = workdir / "femm_model.lua"
            lua_file.write_text(script_text, encoding="utf-8")

        # Ensure script explicitly quits so FEMM closes headless
        content = lua_file.read_text(encoding="utf-8")
        if "quit()" not in content:
            lua_file.write_text(content + "\nquit()\n", encoding="utf-8")

        log_path = workdir / "femm_runner.log"
        cmd = [str(exe), "-windowhide", f"-lua-script={lua_file.resolve()}"]

        exec_out = self._runner.run(
            command_args=cmd,
            cwd=workdir,
            timeout_s=request.timeout_s,
            log_file=log_path,
        )

        metrics: dict[str, float] = {}
        diagnostics: list[str] = []

        results_txt = workdir / "results.txt"
        if results_txt.exists():
            parsed = parse_femm_results(results_txt)
            metrics.update(parsed.metrics)
            diagnostics.extend(parsed.diagnostics)

        artifacts = manifest_directory(workdir, job_id=request.job_id)

        final_status = exec_out.status
        if exec_out.exit_code != 0:
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
