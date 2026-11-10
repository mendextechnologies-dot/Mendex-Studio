"""Data models and enums for the Product Engineering Lifecycle and Verification Framework."""
from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


def now() -> datetime:
    return datetime.now(timezone.utc)


class Model(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        allow_inf_nan=False,
        str_strip_whitespace=True,
        revalidate_instances="always",
        validate_assignment=True,
    )


class LifecycleStage(StrEnum):
    # Core 15 Stages (v2.0)
    REQUIREMENTS = "requirements"
    ARCHITECTURE = "architecture"
    ELECTRICAL_DESIGN = "electrical_design"
    ENGINEERING_CALCULATIONS = "engineering_calculations"
    CIRCUIT_SIMULATION = "circuit_simulation"
    MAGNETIC_ANALYSIS = "magnetic_analysis"
    SCHEMATIC_VERIFICATION = "schematic_verification"
    PCB_DESIGN = "pcb_design"
    PCB_VERIFICATION = "pcb_verification"
    THERMAL_MECHANICAL = "thermal_mechanical"
    BOM_SOURCING = "bom_sourcing"
    ENGINEERING_VALIDATION = "engineering_validation"
    PROTOTYPE_READINESS = "prototype_readiness"
    PHYSICAL_TESTING = "physical_testing"
    ENGINEERING_RELEASE = "engineering_release"

    # Backward-compatibility aliases for v1.9 tests and artifacts
    ELECTRICAL_ARCHITECTURE = "electrical_architecture"
    CIRCUIT_DESIGN = "circuit_design"
    ELECTRICAL_SIMULATION = "electrical_simulation"
    PCB_LAYOUT = "pcb_layout"
    PCB_DRC = "pcb_drc"
    BOM_REVIEW = "bom_review"


class StageStatus(StrEnum):
    NOT_STARTED = "NOT STARTED"
    IN_PROGRESS = "IN PROGRESS"
    PENDING_REVIEW = "PENDING REVIEW"
    PENDING_VERIFICATION = "PENDING REVIEW"
    PASSED = "PASSED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    NOT_APPLICABLE = "NOT APPLICABLE"


class ArtifactType(StrEnum):
    REQUIREMENTS_SPEC = "requirements_spec"
    CALCULATION_RECORD = "calculation_record"
    SPICE_NETLIST = "spice_netlist"
    MODELICA_SCRIPT = "modelica_script"
    SIMULATION_OUTPUT = "simulation_output"
    WAVEFORM_RAW = "waveform_raw"
    MAGNETIC_MODEL = "magnetic_model"
    BOBBIN_CAD = "bobbin_cad"
    SCHEMATIC_KICAD = "schematic_kicad"
    PCB_KICAD = "pcb_kicad"
    ERC_REPORT = "erc_report"
    DRC_REPORT = "drc_report"
    BOM_FILE = "bom_file"
    VALIDATION_CHECK = "validation_check"
    ENGINEERING_REPORT = "engineering_report"
    GERBER_PACKAGE = "gerber_package"
    OTHER = "other"


class UnifiedEvidenceRecord(Model):
    evidence_id: UUID = Field(default_factory=uuid4)
    product_id: Optional[UUID] = None
    revision_id: Optional[UUID] = None
    workspace_id: Optional[str] = None
    activity_id: Optional[str] = None
    stage_id: LifecycleStage
    artifact_type: ArtifactType
    source_tool: str
    tool_version: Optional[str] = None
    source_file: str
    output_file: Optional[str] = None
    sha256: str
    file_size_bytes: int = 0
    execution_timestamp: datetime = Field(default_factory=now)
    validation_result: str = "NOT_EVALUATED"  # PASSED, FAILED, NOT_EVALUATED, WARNING
    engineering_revision: str = "R001"
    reviewer_approval: Optional[str] = None
    notes: str = ""


class StageEvaluation(Model):
    stage_id: LifecycleStage
    title: str
    category_number: int
    status: StageStatus
    mandatory: bool = True
    required_evidence_desc: str
    actual_evidence_desc: str
    evidence_records: List[UnifiedEvidenceRecord] = Field(default_factory=list)
    blockers: List[str] = Field(default_factory=list)
    last_verified_at: Optional[datetime] = None
    reviewer: Optional[str] = None
    notes: str = ""
    nav_target: str = ""


class ReadinessGate(Model):
    gate_id: str
    title: str
    stage_id: LifecycleStage
    mandatory: bool = True
    passed: bool = False
    status: str = "PENDING"
    reason: str = ""


class ProductLifecycleAssessment(Model):
    product_id: Optional[UUID] = None
    product_code: Optional[str] = None
    revision_id: Optional[UUID] = None
    revision_label: Optional[str] = None
    workspace_id: Optional[str] = None
    workspace_name: Optional[str] = None
    overall_status: StageStatus
    prototype_ready: bool
    stages: Dict[str, StageEvaluation] = Field(default_factory=dict)
    readiness_gates: List[ReadinessGate] = Field(default_factory=list)
    critical_blockers: List[str] = Field(default_factory=list)
    total_evidence_count: int = 0
    last_assessed_at: datetime = Field(default_factory=now)
