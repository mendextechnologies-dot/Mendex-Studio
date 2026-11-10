from __future__ import annotations

import sys
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


class PythonRuntimeAdapter(BaseToolAdapter):
    """Adapter for the local Python execution runtime."""

    def __init__(self):
        super().__init__(
            tool_id="python",
            name="Python Runtime",
            kind=ToolKind.RUNTIME,
            category="core",
            license_name="PSF License",
            official_url="https://www.python.org/",
            candidate_binaries=[sys.executable],
        )

    def detect(self, configured_path: str | None = None) -> ToolDescriptor:
        exe = Path(configured_path or sys.executable).resolve()
        ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        state = ToolState.READY if exe.exists() else ToolState.NOT_INSTALLED
        self._descriptor = ToolDescriptor(
            tool_id=self.tool_id,
            name=self.name,
            kind=self.kind,
            category=self.category,
            version=ver,
            license_name=self.license_name,
            official_url=self.official_url,
            capabilities=self.supported_operations(),
            state=state,
            executable_path=str(exe),
            diagnostic=f"Active Python interpreter {ver} at {exe}",
        )
        return self._descriptor

    def supported_operations(self) -> list[str]:
        return ["run_script", "evaluate_formula"]

    def execute(self, request: JobRequest, workdir: Path | None = None) -> JobResult:
        if not workdir:
            workdir = Path(request.workdir or Path.cwd() / "py_run").resolve()
        workdir.mkdir(parents=True, exist_ok=True)

        script_file: Path | None = None
        if request.input_paths:
            script_file = Path(request.input_paths[0])
        elif "script_text" in request.parameters:
            script_file = workdir / "script.py"
            script_file.write_text(request.parameters["script_text"], encoding="utf-8")

        if not script_file or not script_file.exists():
            now_iso = datetime.now(timezone.utc).isoformat()
            return JobResult(
                job_id=request.job_id,
                tool_id=self.tool_id,
                status=JobState.FAILED,
                start_time=now_iso,
                end_time=now_iso,
                exit_code=1,
                error_message="No script input provided for Python execution",
            )

        log_path = workdir / "python_run.log"
        cmd = [self._descriptor.executable_path or sys.executable, str(script_file.resolve())]
        exec_out = self._runner.run(
            command_args=cmd,
            cwd=workdir,
            timeout_s=request.timeout_s,
            log_file=log_path,
        )

        artifacts = manifest_directory(workdir, job_id=request.job_id)
        return JobResult(
            job_id=request.job_id,
            tool_id=self.tool_id,
            status=exec_out.status,
            start_time=exec_out.start_time,
            end_time=exec_out.end_time,
            exit_code=exec_out.exit_code,
            stdout=exec_out.stdout,
            stderr=exec_out.stderr,
            log_path=str(log_path) if log_path.exists() else None,
            artifacts=artifacts,
            error_message=exec_out.stderr if exec_out.status != JobState.SUCCEEDED else None,
        )
