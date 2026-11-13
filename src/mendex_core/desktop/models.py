from typing import Literal
from uuid import UUID

from pydantic import Field, model_validator

from ..models import Model

PROTOCOL_VERSION = "3.1.0"


class Empty(Model):
    pass


class ProjectQuery(Model):
    project_id: UUID
    revision_id: UUID | None = None


class JobQuery(Model):
    job_id: UUID


class FileQuery(Model):
    revision_id: UUID
    relative_path: str = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def relative(self):
        from ..integration_contracts import safe_relative
        if self.relative_path != ".":
            safe_relative(self.relative_path)
        return self


class WaveformQuery(FileQuery):
    start: int = Field(default=0, ge=0, strict=True)
    limit: int = Field(default=10000, ge=1, le=20000, strict=True)
    traces: list[str] = Field(default_factory=list, max_length=8)


class ReportQuery(Model):
    report_id: UUID


class ExportReportQuery(ReportQuery):
    idempotency_key: str = Field(min_length=1, max_length=128)


class EvidenceQuery(Model):
    record_id: UUID


class BridgeRequest(Model):
    protocol_version: Literal["3.1.0"]
    id: str = Field(min_length=1, max_length=128)
    method: str = Field(min_length=1, max_length=80)
    params: dict = Field(default_factory=dict)
