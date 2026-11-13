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


class ReviewPackageQuery(Model):
    revision_id: UUID
    stage_id: str = "requirements"


class BOMQuery(Model):
    revision_id: UUID


class ReviewRequestQuery(Model):
    revision_id: UUID
    stage_id: str = "requirements"
    submitter: str
    reason: str = "Requested formal human review"
    idempotency_key: str = Field(min_length=1, max_length=128)


class ReviewDecisionQuery(Model):
    revision_id: UUID
    stage_id: str = "requirements"
    attempt: int = Field(ge=1)
    decision: Literal["APPROVED", "REJECTED", "CHANGES_REQUESTED"]
    reviewer_name: str = Field(min_length=1, max_length=200)
    expected_document_hashes: dict[str, str]
    expected_evidence_hashes: dict[str, str]
    comments: str
    conflicts: list[dict] = Field(default_factory=list)
    deferrals: list[dict] = Field(default_factory=list)
    expected_requirements_digest: str
    expected_specification_hash: str
    idempotency_key: str = Field(min_length=1, max_length=128)


class BridgeRequest(Model):
    protocol_version: Literal["3.1.0"]
    id: str = Field(min_length=1, max_length=128)
    method: str = Field(min_length=1, max_length=80)
    params: dict = Field(default_factory=dict)
