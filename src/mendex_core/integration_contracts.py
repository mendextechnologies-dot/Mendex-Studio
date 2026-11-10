"""Frozen v1.5.0 Agent 1/Agent 2 boundary; independent of legacy adapters."""
from datetime import datetime
from enum import StrEnum
from pathlib import Path, PureWindowsPath
from threading import Event
from time import monotonic
from typing import Literal, Protocol
from uuid import UUID, uuid4

from pydantic import Field, model_validator

from .models import Model, now

CONTRACT_VERSION = "1.5.0"


class ToolState(StrEnum):
    NOT_CONFIGURED = "NOT_CONFIGURED"
    NOT_INSTALLED = "NOT_INSTALLED"
    DETECTED = "DETECTED"
    READY = "READY"
    UNSUPPORTED = "UNSUPPORTED"
    ERROR = "ERROR"
    UNKNOWN = "UNKNOWN"


class JobStatus(StrEnum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    TIMED_OUT = "TIMED_OUT"


TERMINAL = {JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELLED, JobStatus.TIMED_OUT}


class ErrorCode(StrEnum):
    NOT_CONFIGURED = "NOT_CONFIGURED"
    NOT_INSTALLED = "NOT_INSTALLED"
    UNSUPPORTED = "UNSUPPORTED"
    INVALID_INPUT = "INVALID_INPUT"
    PATH_VIOLATION = "PATH_VIOLATION"
    LICENSE_REQUIRED = "LICENSE_REQUIRED"
    EXECUTION_FAILED = "EXECUTION_FAILED"
    MALFORMED_OUTPUT = "MALFORMED_OUTPUT"
    CANCELLED = "CANCELLED"
    TIMED_OUT = "TIMED_OUT"
    INTERRUPTED = "INTERRUPTED"


def safe_relative(value: str) -> str:
    windows = PureWindowsPath(value)
    if not value or Path(value).is_absolute() or windows.anchor or ".." in windows.parts or ".." in Path(value).parts or ":" in value:
        raise ValueError("Expected a workspace-relative path without parent traversal or drive")
    return value


class Capability(Model):
    operation: str = Field(min_length=1)
    supported: bool = False
    tested_version: str | None = None
    verification_evidence: str | None = None
    diagnostic: str = "Awaiting Agent 2 connector and repeatable smoke evidence"


class ToolDescriptor(Model):
    schema_version: Literal["1.5.0"] = CONTRACT_VERSION
    tool_id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]*$")
    name: str = Field(min_length=1)
    category: Literal["application", "dataset", "benchmark", "research_resource", "runtime", "developer_tool", "demo"]
    supported_os: list[str] = Field(default_factory=list)
    version: str | None = None
    license_status: Literal["UNKNOWN", "REVIEW_REQUIRED", "USER_CONFIRMED", "NOT_REQUIRED"] = "REVIEW_REQUIRED"
    license_notes: str = "Review the installed distribution's actual terms before use or redistribution"
    optional_paid: bool = False
    source_url: str | None = None
    source_notes: str = ""
    capabilities: list[Capability] = Field(default_factory=list)
    configuration_schema: dict = Field(default_factory=lambda: {"executable_path": "absolute existing path", "license_reference": "local review reference; no keys or secrets"})


class ToolConfiguration(Model):
    executable_path: str | None = None
    resource_path: str | None = None
    license_reference: str = ""


class ToolHealth(Model):
    tool_id: str
    state: ToolState
    version: str | None = None
    checked_at: datetime = Field(default_factory=now)
    executable_path: str | None = None
    diagnostic: str
    verified_operations: list[str] = Field(default_factory=list)


class JobRequest(Model):
    schema_version: Literal["1.5.0"] = CONTRACT_VERSION
    job_id: UUID = Field(default_factory=uuid4)
    workspace_id: UUID = Field(default_factory=uuid4)
    tool_id: str = Field(min_length=1)
    operation: str = Field(min_length=1)
    input_paths: list[str] = Field(default_factory=list, max_length=32)
    parameters: dict = Field(default_factory=dict)
    timeout_s: float = Field(default=30, gt=0, le=3600)
    provenance: str = Field(min_length=1)

    @model_validator(mode="after")
    def paths(self):
        for path in self.input_paths:
            safe_relative(path)
        return self


class Diagnostic(Model):
    code: ErrorCode
    message: str


class JobResult(Model):
    schema_version: Literal["1.5.0"] = CONTRACT_VERSION
    job_id: UUID
    tool_id: str
    tool_version: str | None = None
    status: JobStatus
    started_at: datetime | None = None
    ended_at: datetime = Field(default_factory=now)
    exit_code: int | None = None
    diagnostics: list[Diagnostic] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)
    evidence_paths: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def final_result(self):
        if self.status not in TERMINAL:
            raise ValueError("JobResult must have a terminal status")
        if self.status == JobStatus.SUCCEEDED and (self.exit_code != 0 or self.started_at is None):
            raise ValueError("Successful software execution requires start time and exit code zero")
        for path in self.outputs + self.evidence_paths:
            safe_relative(path)
        return self


class ArtifactManifest(Model):
    relative_path: str
    file_type: str
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    size_bytes: int = Field(ge=0)
    source_job: UUID
    provenance: str
    created_at: datetime = Field(default_factory=now)
    source_label: Literal["SYNTHETIC", "SIMULATED", "MEASURED", "IMPORTED", "SOFTWARE_LOG"]
    raw_vs_derived: Literal["raw", "derived", "log"]
    unit_conventions: str = "SI where applicable; no engineering quantities in synthetic fixtures"
    review_state: Literal["NOT_REVIEWED"] = "NOT_REVIEWED"

    @model_validator(mode="after")
    def relative(self):
        safe_relative(self.relative_path)
        return self


class EvidenceManifest(Model):
    schema_version: Literal["1.5.0"] = CONTRACT_VERSION
    job_id: UUID
    request: JobRequest
    result: JobResult
    input_hashes: dict[str, str] = Field(default_factory=dict)
    artifacts: list[ArtifactManifest]
    engineering_status: Literal["NOT_EVALUATED"] = "NOT_EVALUATED"

    @model_validator(mode="after")
    def identities(self):
        if self.job_id != self.request.job_id or self.job_id != self.result.job_id or self.request.tool_id != self.result.tool_id:
            raise ValueError("Evidence/request/result job identity or tool mismatch")
        if any(a.source_job != self.job_id for a in self.artifacts):
            raise ValueError("Artifact source job mismatch")
        return self


class JobRecord(Model):
    request: JobRequest
    status: JobStatus = JobStatus.QUEUED
    created_at: datetime = Field(default_factory=now)
    started_at: datetime | None = None
    progress: float = Field(default=0, ge=0, le=1)
    result: JobResult | None = None
    retry_of: UUID | None = None
    manifest_path: str | None = None


class ExecutionCancelled(Exception):
    pass


class ExecutionTimedOut(Exception):
    pass


class ExecutionContext:
    """Agent 2 owns process isolation/tree termination; this boundary is cooperative."""
    def __init__(self, workdir: Path, cancel_event: Event, deadline: float, log, progress):
        self.workdir, self.cancel_event, self.deadline = workdir, cancel_event, deadline
        self.log, self.progress = log, progress

    def checkpoint(self):
        if self.cancel_event.is_set():
            raise ExecutionCancelled()
        if monotonic() >= self.deadline:
            raise ExecutionTimedOut()


class ToolAdapter(Protocol):
    descriptor: ToolDescriptor
    def detect(self, configuration: ToolConfiguration) -> ToolHealth: ...
    def verify(self, configuration: ToolConfiguration) -> ToolHealth: ...
    def supported_operations(self) -> list[Capability]: ...
    def execute(self, request: JobRequest, context: ExecutionContext) -> JobResult: ...
