from __future__ import annotations

import shutil
import subprocess
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
from .base import BaseToolAdapter


class GitAdapter(BaseToolAdapter):
    """Adapter for Git source and version control."""

    def __init__(self):
        super().__init__(
            tool_id="git",
            name="Git",
            kind=ToolKind.APPLICATION,
            category="core",
            license_name="GPLv2",
            official_url="https://git-scm.com/",
            candidate_binaries=["git.exe", "git"],
        )

    def detect(self, configured_path: str | None = None) -> ToolDescriptor:
        git_path = configured_path or shutil.which("git")
        if not git_path:
            for fallback in [
                r"C:\Program Files\Git\cmd\git.exe",
                r"C:\Program Files\Git\bin\git.exe",
            ]:
                if Path(fallback).exists():
                    git_path = fallback
                    break

        ver = None
        state = ToolState.NOT_INSTALLED
        diag = "Git CLI not detected in system PATH."
        if git_path:
            try:
                res = subprocess.run([git_path, "--version"], capture_output=True, text=True, timeout=15)
                if res.returncode == 0:
                    ver = res.stdout.strip().replace("git version ", "")
                    state = ToolState.READY
                    diag = f"Git CLI available at {git_path} ({ver})"
            except Exception as e:
                diag = f"Failed to execute git: {e}"

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
            executable_path=git_path,
            diagnostic=diag,
        )
        return self._descriptor

    def supported_operations(self) -> list[str]:
        return ["status", "rev_parse", "hash_object"]
