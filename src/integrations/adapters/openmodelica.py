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
from integrations.runners.safe_runner import manifest_directory
from .base import BaseToolAdapter


class OpenModelicaAdapter(BaseToolAdapter):
    """Adapter for OpenModelica Compiler (omc)."""

    def __init__(self):
        super().__init__(
            tool_id="openmodelica",
            name="OpenModelica",
            kind=ToolKind.APPLICATION,
            category="high",
            license_name="OSMC-PL",
            official_url="https://openmodelica.org/",
            candidate_binaries=["omc.exe", "omc"],
            candidate_paths=["OpenModelica*/bin/omc.exe"],
        )

    def supported_operations(self) -> list[str]:
        return ["check_model", "simulate_modelica", "version"]

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
                error_message="OpenModelica is NOT_INSTALLED on this machine",
                diagnostics=[self.descriptor.diagnostic],
            )

        exe = Path(self.descriptor.executable_path)
        if not workdir:
            workdir = Path(request.workdir or Path.cwd() / "omc_run").resolve()
        workdir.mkdir(parents=True, exist_ok=True)

        operation = request.operation or "version"
        log_file = workdir / f"omc_{operation}.log"

        if operation == "version":
            cmd = [str(exe), "--version"]
        elif operation == "check_model":
            model_name = request.parameters.get("model_name", "SimpleResistor")
            if "model_code" in request.parameters:
                model_code = request.parameters["model_code"]
            else:
                model_code = (
                    f"model {model_name}\n"
                    "  parameter Real R = 100.0;\n"
                    "  parameter Real Vin = 10.0;\n"
                    "  Real v;\n"
                    "  Real i;\n"
                    "equation\n"
                    "  v = Vin;\n"
                    "  v = i * R;\n"
                    f"end {model_name};\n"
                )
            mos_content = (
                f'loadString("{model_code}");\n'
                f'getErrorString();\n'
                f'checkModel({model_name});\n'
                f'getErrorString();\n'
            )
            mos_file = workdir / "check.mos"
            mos_file.write_text(mos_content, encoding="utf-8")
            cmd = [str(exe), str(mos_file.resolve())]
        elif operation == "simulate_modelica":
            if request.input_paths:
                mos_file = Path(request.input_paths[0])
            else:
                from integrations.generators.modelica_generator import generate_openmodelica_flyback_script
                script = generate_openmodelica_flyback_script()
                mos_file = workdir / "flyback.mos"
                mos_file.write_text(script, encoding="utf-8")
            cmd = [str(exe), str(mos_file.resolve())]
        else:
            raise NotImplementedError(f"Unsupported OpenModelica operation: {operation}")

        exec_out = self._runner.run(
            command_args=cmd,
            cwd=workdir,
            timeout_s=request.timeout_s,
            log_file=log_file,
        )

        artifacts = manifest_directory(workdir, job_id=request.job_id)
        diagnostics: list[str] = []
        if exec_out.stderr:
            diagnostics.append(exec_out.stderr)

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
            diagnostics=diagnostics,
            error_message=exec_out.stderr if status == JobState.FAILED else None,
        )
