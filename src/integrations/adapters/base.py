from __future__ import annotations

import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from integrations.contracts import (
    ToolDescriptor,
    ToolKind,
    ToolState,
    JobRequest,
    JobResult,
    JobState,
)
from integrations.runners.safe_runner import SafeRunner


def read_pe_version(exe_path: Path) -> str | None:
    """Safely extracts Windows PE version resource without importing win32 extensions."""
    if not exe_path.exists() or os.name != "nt":
        return None
    try:
        from mendex_core.adapters.version import windows_file_version
        return windows_file_version(exe_path)
    except Exception:
        return None


class BaseToolAdapter:
    """Base class for all Mendex Studio v1.5 tool adapters."""

    def __init__(
        self,
        tool_id: str,
        name: str,
        kind: ToolKind = ToolKind.APPLICATION,
        category: str = "core",
        license_name: str = "Unknown",
        official_url: str = "",
        candidate_binaries: list[str] | None = None,
        candidate_paths: list[str] | None = None,
    ):
        self.tool_id = tool_id
        self.name = name
        self.kind = kind
        self.category = category
        self.license_name = license_name
        self.official_url = official_url
        self.candidate_binaries = candidate_binaries or []
        self.candidate_paths = candidate_paths or []
        self._runner = SafeRunner()
        self._descriptor = self.detect()

    @property
    def descriptor(self) -> ToolDescriptor:
        return self._descriptor

    def supported_operations(self) -> list[str]:
        return []

    def detect(self, configured_path: str | None = None) -> ToolDescriptor:
        resolved_exe: Path | None = None
        if configured_path:
            p = Path(configured_path)
            if p.exists() and p.is_file():
                resolved_exe = p.resolve()
        else:
            for b in self.candidate_binaries:
                which_p = shutil.which(b)
                if which_p:
                    resolved_exe = Path(which_p).resolve()
                    break

            if not resolved_exe:
                roots = [
                    Path(os.environ.get("ProgramFiles", "C:/Program Files")),
                    Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)")),
                    Path(os.environ.get("LOCALAPPDATA", "C:/Users/Default/AppData/Local")) / "Programs",
                ]
                for root in roots:
                    for pat in self.candidate_paths:
                        matches = list(root.glob(pat))
                        if matches:
                            resolved_exe = matches[0].resolve()
                            break
                    if resolved_exe:
                        break

        if resolved_exe:
            version = read_pe_version(resolved_exe)
            state = ToolState.DETECTED if not self.verify_executable(resolved_exe) else ToolState.READY
            diag = f"Executable found at {resolved_exe}"
            if version:
                diag += f" (Version: {version})"
        else:
            version = None
            state = ToolState.NOT_INSTALLED
            diag = f"{self.name} is not installed or not found in standard paths."

        self._descriptor = ToolDescriptor(
            tool_id=self.tool_id,
            name=self.name,
            kind=self.kind,
            category=self.category,
            version=version,
            license_name=self.license_name,
            official_url=self.official_url,
            capabilities=self.supported_operations(),
            state=state,
            executable_path=str(resolved_exe) if resolved_exe else None,
            diagnostic=diag,
        )
        return self._descriptor

    def verify_executable(self, exe_path: Path) -> bool:
        """Non-destructive validation of executable existence and basic usability."""
        return exe_path.exists() and exe_path.is_file()

    def verify(self) -> bool:
        return self._descriptor.state in (ToolState.READY, ToolState.DETECTED)

    def execute(self, request: JobRequest, workdir: Path | None = None) -> JobResult:
        if self._descriptor.state in (ToolState.NOT_INSTALLED, ToolState.OPTIONAL_UNLICENSED):
            now_iso = datetime.now(timezone.utc).isoformat()
            return JobResult(
                job_id=request.job_id,
                tool_id=self.tool_id,
                status=JobState.FAILED,
                start_time=now_iso,
                end_time=now_iso,
                exit_code=1,
                error_message=f"Cannot execute job: {self.name} is {self._descriptor.state.value}",
                diagnostics=[self._descriptor.diagnostic],
            )
        raise NotImplementedError(f"Operation '{request.operation}' not implemented for {self.name}")
