import hashlib
import json
from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import Field, model_validator

from .models import Model, Specification, now


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def specification_hash(specification: Specification) -> str:
    return digest(json.dumps(specification.model_dump(mode="json"), sort_keys=True, separators=(",", ":")).encode())


class ValidationStatus(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    NOT_EVALUATED = "not_evaluated"
    PHYSICAL_REQUIRED = "physical_verification_required"


class ManualCheck(Model):
    check_id: str = Field(min_length=1, max_length=100)
    status: ValidationStatus = ValidationStatus.NOT_EVALUATED
    rule_version: str = Field(default="manual-1.0", min_length=1)
    reviewer: str = Field(min_length=1, max_length=200)
    notes: str = Field(min_length=1)
    evidence_kind: str = Field(default="MANUAL", pattern=r"^(MANUAL|CALCULATED|SIMULATED|MEASURED)$")
    measured_value: float | None = None
    unit: str = ""
    minimum: float | None = None
    maximum: float | None = None

    @model_validator(mode="after")
    def evaluated_rule(self):
        if self.minimum is not None and self.maximum is not None and self.minimum > self.maximum:
            raise ValueError("Minimum must not exceed maximum")
        if self.status in (ValidationStatus.PASS, ValidationStatus.FAIL):
            if self.measured_value is None or not self.unit or (self.minimum is None and self.maximum is None):
                raise ValueError("PASS/FAIL requires a value, SI unit and explicit numerical criterion")
            passed = (self.minimum is None or self.measured_value >= self.minimum) and (self.maximum is None or self.measured_value <= self.maximum)
            if passed != (self.status == ValidationStatus.PASS):
                raise ValueError("Requested status disagrees with the evaluated numerical rule")
        return self


class ValidationRecord(Model):
    record_id: UUID = Field(default_factory=uuid4)
    revision_id: UUID
    timestamp: datetime = Field(default_factory=now)
    specification: Specification
    input_hash: str
    check: ManualCheck
    evidence_uri: str | None = None
    evidence_sha256: str | None = None
    evidence_filename: str | None = None
    provenance: str = "Manually supplied evidence and values; not independently verified by Mendex"


class SimulationRun(Model):
    schema_version: str = Field(default="1.0", pattern=r"^1\.0$")
    run_id: UUID = Field(default_factory=uuid4)
    revision_id: UUID
    tool_id: str
    adapter_version: str = "0.1.0"
    status: str = Field(default="not_supported", pattern=r"^(not_started|queued|running|succeeded|failed|not_supported)$")
    started_at: datetime | None = None
    ended_at: datetime | None = None
    input_hash: str | None = None
    artifacts: list[str] = Field(default_factory=list)
    log_path: str | None = None
    requested_at: datetime = Field(default_factory=now)
    limitation: str = "Solver execution is unavailable; no simulation has been performed"
    specification: Specification | None = None
    tool_version: str | None = None


class Report(Model):
    report_id: UUID = Field(default_factory=uuid4)
    revision_id: UUID
    generated_at: datetime = Field(default_factory=now)
    input_hash: str
    report_path: str
    included_check_ids: list[str]
    warnings: list[str]
