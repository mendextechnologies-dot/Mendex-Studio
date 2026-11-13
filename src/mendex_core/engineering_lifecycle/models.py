"""Versioned, data-only lifecycle contracts. No agent approval operation exists."""
from enum import StrEnum
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, model_validator

from ..models import Model, Specification

Identifier = Annotated[str, Field(min_length=1, max_length=80, pattern=r"^[a-z][a-z0-9_]*$")]
Text = Annotated[str, Field(min_length=1, max_length=4000)]
EvidenceKind = Literal["MANUAL", "CALCULATED", "SIMULATED", "MEASURED"]


class StageStatus(StrEnum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    BLOCKED = "BLOCKED"
    AWAITING_REVIEW = "AWAITING_REVIEW"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class Criterion(Model):
    id: Identifier
    description: Text
    kind: Literal["project_context", "specification_fields", "validation_record", "human_review"]
    fields: list[str] = Field(default_factory=list, max_length=30)
    check_id: str | None = Field(default=None, min_length=1, max_length=100)
    evidence_kind: EvidenceKind | None = None

    @model_validator(mode="after")
    def valid_parameters(self):
        if self.kind == "validation_record":
            if not self.check_id or not self.evidence_kind or self.fields:
                raise ValueError("validation_record needs check_id and evidence_kind, without fields")
        elif self.kind == "human_review":
            if self.fields or self.evidence_kind is not None:
                raise ValueError("human_review does not accept fields or evidence_kind")
        elif self.check_id is not None or self.evidence_kind is not None:
            raise ValueError("Only validation_record accepts check_id/evidence_kind")
        if self.kind == "specification_fields":
            if not self.fields or len(set(self.fields)) != len(self.fields):
                raise ValueError("specification_fields needs unique fields")
            if not set(self.fields).issubset(Specification.model_fields):
                raise ValueError("Unknown specification field")
        elif self.fields:
            raise ValueError("Only specification_fields accepts fields")
        return self


class StageDefinition(Model):
    id: Identifier
    name: Text
    purpose: Text
    required_inputs: list[Text] = Field(default_factory=list, max_length=50)
    expected_outputs: list[Text] = Field(default_factory=list, max_length=50)
    dependencies: list[Identifier] = Field(default_factory=list, max_length=100)
    optional: bool = False
    review_required: bool = True
    criteria: list[Criterion] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def unique_ids(self):
        if len({c.id for c in self.criteria}) != len(self.criteria):
            raise ValueError("Duplicate criterion ID")
        if len(set(self.dependencies)) != len(self.dependencies):
            raise ValueError("Duplicate dependency")
        return self


class LifecycleDefinition(Model):
    schema_version: Literal["3.1.0"] = "3.1.0"
    id: Identifier
    version: str = Field(min_length=1, max_length=40, pattern=r"^[0-9]+\.[0-9]+\.[0-9]+$")
    name: Text
    stages: list[StageDefinition] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def valid_graph(self):
        stages = {s.id: s for s in self.stages}
        if len(stages) != len(self.stages):
            raise ValueError("Duplicate stage ID")
        visiting, visited = set(), set()

        def visit(identifier):
            if identifier not in stages:
                raise ValueError(f"Unknown dependency: {identifier}")
            if identifier in visiting:
                raise ValueError("Lifecycle dependencies must be acyclic; iterations use new attempts")
            if identifier in visited:
                return
            visiting.add(identifier)
            for dependency in stages[identifier].dependencies:
                visit(dependency)
            visiting.remove(identifier)
            visited.add(identifier)

        for identifier in stages:
            visit(identifier)
        return self


class VersionedRequest(Model):
    schema_version: Literal["3.1.0"] = "3.1.0"


class DefinitionQuery(VersionedRequest):
    definition_id: Identifier = "engineering"
    version: str = Field(default="3.1.0", min_length=1, max_length=40)


class RegisterDefinition(VersionedRequest):
    definition: LifecycleDefinition
    source: Text


class LifecycleQuery(VersionedRequest):
    revision_id: UUID


class HistoryQuery(LifecycleQuery):
    stage_id: Identifier | None = None
    after_sequence: int = Field(default=0, ge=0, strict=True)
    limit: int = Field(default=100, ge=1, le=500, strict=True)


class Enrollment(LifecycleQuery):
    definition_id: Identifier = "engineering"
    version: str = Field(default="3.1.0", min_length=1, max_length=40)
    source: Text
    reason: Text
    idempotency_key: str = Field(min_length=1, max_length=128)


class StageCommand(LifecycleQuery):
    stage_id: Identifier
    action: Literal["start", "block", "fail", "request_review", "complete", "not_applicable", "reopen", "attach_evidence"]
    source: Text
    reason: Text
    idempotency_key: str = Field(min_length=1, max_length=128)
    expected_sequence: int | None = Field(default=None, ge=0, strict=True)
    evidence_record_id: UUID | None = None

    @model_validator(mode="after")
    def evidence_parameter(self):
        if (self.action == "attach_evidence") != (self.evidence_record_id is not None):
            raise ValueError("Only attach_evidence requires evidence_record_id")
        return self
