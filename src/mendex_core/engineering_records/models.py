from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, model_validator

from ..engineering_lifecycle.models import Identifier, Text, VersionedRequest
from ..evidence import ManualCheck
from ..models import Model, Specification

SHA256 = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]


class Attributed(VersionedRequest):
    source: Text
    reason: Text
    idempotency_key: str = Field(min_length=1, max_length=128)


class RevisionQuery(VersionedRequest):
    revision_id: UUID


class RecordList(RevisionQuery):
    stage_id: Identifier | None = None
    after_sequence: int = Field(default=0, ge=0, strict=True)
    limit: int = Field(default=100, ge=1, le=500, strict=True)


class RecordQuery(VersionedRequest):
    record_id: UUID


class ProjectQuery(VersionedRequest):
    project_id: UUID


class StageWrite(Attributed):
    revision_id: UUID
    stage_id: Identifier
    expected_input_hash: SHA256


class ProjectUpdate(Attributed):
    project_id: UUID
    name: str = Field(min_length=1, max_length=200)
    owner: str = Field(min_length=1, max_length=200)
    description: str = Field(max_length=20000)
    expected_updated_at: datetime


class Requirement(Model):
    id: Identifier
    discipline: Literal["electrical", "mechanical", "environmental", "safety", "performance", "standards", "thermal", "reliability", "manufacturing"]
    description: Text
    source: Text
    acceptance_criterion: str = Field(default="", max_length=4000)
    mandatory: bool = True
    specification_field: str | None = None
    target_value: float | None = None
    min_value: float | None = None
    max_value: float | None = None
    tolerance_pct: float | None = Field(default=None, ge=0)
    unit: str = Field(default="", max_length=100)
    verification_method: Literal["simulation", "calculation", "test", "inspection", "analysis", "review"] = "simulation"
    verification_status: Literal["UNTESTED", "NOT_EVALUATED", "PASSED", "FAILED"] = "NOT_EVALUATED"
    verification_artifact: str | None = None
    assumptions: list[Text] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def parameters(self):
        if self.specification_field is not None and self.specification_field not in Specification.model_fields:
            raise ValueError("Unknown specification field")
        if self.target_value is not None and not self.unit:
            raise ValueError("Numerical requirements need an explicit unit")
        if self.min_value is not None and self.max_value is not None and self.min_value > self.max_value:
            raise ValueError("min_value cannot exceed max_value")
        return self


class RequirementsWrite(StageWrite):
    requirements: list[Requirement] = Field(min_length=1, max_length=200)

    @model_validator(mode="after")
    def unique(self):
        if len({r.id for r in self.requirements}) != len(self.requirements):
            raise ValueError("Requirement IDs must be unique")
        return self


class CalculationWrite(StageWrite):
    calculation: Literal["dowell", "losses", "steinmetz", "flyback", "semiconductor_thermal", "magnetic_thermal", "ipc2152_thermal"]
    parameters: dict
    assumptions: list[Text] = Field(min_length=1, max_length=100)


class ArtifactWrite(StageWrite):
    relative_path: str = Field(min_length=1, max_length=1000)
    expected_sha256: SHA256
    classification: Literal["circuit", "netlist", "waveform", "magnetic_model", "schematic", "pcb", "calculation", "documentation", "report", "other"]
    design_id: UUID | None = None
    design_revision_id: UUID | None = None

    @model_validator(mode="after")
    def identifiers(self):
        from ..integration_contracts import safe_relative
        safe_relative(self.relative_path)
        if (self.design_id is None) != (self.design_revision_id is None):
            raise ValueError("Supply both design and design revision IDs")
        return self


class ValidationWrite(StageWrite):
    check: ManualCheck
    evidence_path: str | None = Field(default=None, max_length=2000)
    expected_evidence_sha256: SHA256 | None = None
    evidence_source: Literal["simulation", "calculation", "physical_test", "visual_inspection"] = "simulation"

    @model_validator(mode="after")
    def evidence(self):
        if (self.evidence_path is None) != (self.expected_evidence_sha256 is None):
            raise ValueError("Evidence path and expected digest must be supplied together")
        if self.evidence_source == "physical_test" and self.check.evidence_kind != "MEASURED":
            raise ValueError("Physical test evidence records must declare MEASURED evidence_kind")
        if self.evidence_source == "physical_test" and self.evidence_path is None:
            raise ValueError("Physical test records require an explicit measurement evidence file and digest")
        return self


class JobQuery(VersionedRequest):
    job_id: UUID


class JobCancel(Attributed):
    job_id: UUID


class JobArtifact(JobQuery):
    relative_path: str = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def confined(self):
        from ..integration_contracts import safe_relative
        safe_relative(self.relative_path)
        return self


class ReportQuery(VersionedRequest):
    report_id: UUID


class ReportGenerate(StageWrite):
    pass


class ReportExport(Attributed):
    report_id: UUID
