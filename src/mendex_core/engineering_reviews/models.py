"""Versioned, data-only review contracts and reviewer authorization models."""
from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, model_validator, field_validator

from ..engineering_lifecycle.models import Identifier, Text, VersionedRequest
from ..engineering_records.models import SHA256
from ..models import Model


class ReviewDecision(StrEnum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CHANGES_REQUESTED = "CHANGES_REQUESTED"


class ReviewerStatus(StrEnum):
    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"


class ReviewerProfile(Model):
    id: Identifier
    name: str = Field(min_length=1, max_length=200)
    email: str = Field(min_length=3, max_length=200)
    roles: list[str] = Field(min_length=1, max_length=20)
    status: ReviewerStatus = ReviewerStatus.ACTIVE
    created_at: str


class ReviewerRegistration(VersionedRequest):
    id: Identifier
    name: str = Field(min_length=1, max_length=200)
    email: str = Field(min_length=3, max_length=200)
    roles: list[str] = Field(min_length=1, max_length=20)
    secret: str = Field(min_length=8, max_length=256)


class RequirementConflict(Model):
    requirement_id: str = Field(min_length=1, max_length=100)
    conflict_type: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1, max_length=4000)
    severity: Literal["CRITICAL", "MAJOR", "MINOR"] = "CRITICAL"
    disposition: Literal["RESOLVED", "DEFERRED", "UNRESOLVED"] = "UNRESOLVED"


class AuthorizedDeferral(Model):
    requirement_id: str = Field(min_length=1, max_length=100)
    rationale: str = Field(min_length=5, max_length=4000)
    owner: str = Field(min_length=1, max_length=200)
    scope: str = Field(min_length=1, max_length=1000)
    downstream_gate: str = Field(min_length=1, max_length=200)


class ReviewPackageQuery(VersionedRequest):
    revision_id: UUID
    stage_id: Identifier = "requirements"


class ReviewRequestCommand(VersionedRequest):
    revision_id: UUID
    stage_id: Identifier = "requirements"
    submitter: str = Field(min_length=1, max_length=200)
    reason: Text = "Engineer requested formal human review"
    idempotency_key: str = Field(min_length=1, max_length=128)


class ReviewDecisionBase(VersionedRequest):
    revision_id: UUID
    stage_id: Identifier = "requirements"
    attempt: int = Field(ge=1)
    decision: ReviewDecision
    comments: Text
    conflicts: list[RequirementConflict] = Field(default_factory=list, max_length=100)
    deferrals: list[AuthorizedDeferral] = Field(default_factory=list, max_length=100)
    expected_requirements_digest: SHA256
    expected_specification_hash: SHA256
    idempotency_key: str = Field(min_length=1, max_length=128)

    @model_validator(mode="after")
    def validate_safety_deferrals(self):
        # Ensure deferrals uniquely reference valid requirement IDs
        deferred_ids = [d.requirement_id for d in self.deferrals]
        if len(deferred_ids) != len(set(deferred_ids)):
            raise ValueError("Duplicate requirement ID in authorized deferrals")
        return self


class ReviewDecisionCommand(ReviewDecisionBase):
    """Legacy credential-based API; retained for existing integrations."""
    reviewer_id: Identifier
    reviewer_secret: str = Field(min_length=1, max_length=256)


class ManualReviewDecisionCommand(ReviewDecisionBase):
    """Local operator attribution, explicitly not authenticated identity."""
    reviewer_name: str = Field(min_length=1, max_length=200)
    expected_document_hashes: dict[str, SHA256]
    expected_evidence_hashes: dict[str, SHA256]

    @field_validator("reviewer_name", mode="before")
    @classmethod
    def strip_name(cls, value):
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def nonblank(self):
        if not self.reviewer_name or not self.comments.strip():
            raise ValueError("Reviewer name and review comments are required")
        return self


class ReviewRecord(Model):
    schema_version: Literal["3.1.0"] = "3.1.0"
    review_id: str
    sequence: int = 0
    project_id: str
    revision_id: str
    stage_id: str
    attempt: int
    requirements_record_id: str | None = None
    requirements_digest: str
    specification_hash: str
    document_hashes: dict[str, str] = Field(default_factory=dict)
    evidence_hashes: dict[str, str] = Field(default_factory=dict)
    conflicts: list[dict] = Field(default_factory=list)
    deferrals: list[dict] = Field(default_factory=list)
    submitter: str
    reviewer_id: str
    reviewer_name: str
    decision: ReviewDecision
    comments: str
    signature: str
    timestamp: str
    stale: bool = False
    unresolved_safety_blockers: list[str] = Field(default_factory=list)
    effective_status: str = "RECORDED"
    review_mode: str = "LEGACY_CREDENTIAL_REVIEW"
    identity_authenticated: bool = False
    signature_kind: str = "LEGACY"
