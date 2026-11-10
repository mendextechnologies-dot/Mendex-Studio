from __future__ import annotations

import enum
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol, runtime_checkable
from pydantic import BaseModel, ConfigDict, Field


class ToolKind(str, enum.Enum):
    APPLICATION = "application"
    DATASET = "dataset"
    BENCHMARK = "benchmark"
    RESEARCH_RESOURCE = "research_resource"
    RUNTIME = "runtime"


class ToolState(str, enum.Enum):
    NOT_CONFIGURED = "NOT_CONFIGURED"
    NOT_INSTALLED = "NOT_INSTALLED"
    DETECTED = "DETECTED"
    READY = "READY"
    UNSUPPORTED = "UNSUPPORTED"
    ERROR = "ERROR"
    OPTIONAL_UNLICENSED = "OPTIONAL_UNLICENSED"


class JobState(str, enum.Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    TIMED_OUT = "TIMED_OUT"


class IntegrationModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ToolDescriptor(IntegrationModel):
    tool_id: str
    name: str
    kind: ToolKind
    category: str = "core"  # core, high, optional
    supported_os: list[str] = Field(default_factory=lambda: ["Windows"])
    version: str | None = None
    license_name: str = "Unknown"
    official_url: str = ""
    capabilities: list[str] = Field(default_factory=list)
    state: ToolState = ToolState.NOT_INSTALLED
    executable_path: str | None = None
    diagnostic: str = ""


class ArtifactManifest(IntegrationModel):
    relative_path: str
    file_type: str
    sha256: str
    size_bytes: int
    source_job: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class JobRequest(IntegrationModel):
    schema_version: str = "1.0"
    job_id: str
    workspace_id: str
    tool_id: str
    operation: str
    input_paths: list[str] = Field(default_factory=list)
    parameters: dict[str, Any] = Field(default_factory=dict)
    timeout_s: int = Field(default=60, gt=0)
    workdir: str | None = None
    provenance: dict[str, str] = Field(default_factory=dict)


class JobResult(IntegrationModel):
    job_id: str
    tool_id: str
    status: JobState
    start_time: str
    end_time: str
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    log_path: str | None = None
    artifacts: list[ArtifactManifest] = Field(default_factory=list)
    metrics: dict[str, float] = Field(default_factory=dict)
    diagnostics: list[str] = Field(default_factory=list)
    error_message: str | None = None


@runtime_checkable
class ToolAdapter(Protocol):
    @property
    def descriptor(self) -> ToolDescriptor: ...

    def detect(self, configured_path: str | None = None) -> ToolDescriptor: ...

    def verify(self) -> bool: ...

    def supported_operations(self) -> list[str]: ...

    def execute(self, request: JobRequest, workdir: Path | None = None) -> JobResult: ...
