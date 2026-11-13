"""Domain models for Engineering Design, Requirements, Candidates, and Artifacts."""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4
from pydantic import BaseModel, Field

from .ir import DesignIntermediateRepresentation


class DesignStatus(str, Enum):
    DRAFT = "DRAFT"
    SYNTHESIZED = "SYNTHESIZED"
    IN_REVIEW = "IN_REVIEW"
    VERIFIED = "VERIFIED"
    RELEASED = "RELEASED"
    ARCHIVED = "ARCHIVED"


class CandidateApprovalStatus(str, Enum):
    PROPOSED = "PROPOSED"
    SELECTED = "SELECTED"
    REJECTED = "REJECTED"


class RequirementApprovalStatus(str, Enum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    SUPERSEDED = "SUPERSEDED"


class Requirement(BaseModel):
    """Structured engineering requirement with tolerance and validation criteria."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    parameter: str
    target_value: float
    unit: str
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    tolerance_pct: Optional[float] = None
    mandatory: bool = True
    provenance: str = "User Specification"
    assumptions: str = ""
    approval_status: RequirementApprovalStatus = RequirementApprovalStatus.DRAFT
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    version: int = 1


class DesignCandidate(BaseModel):
    """Synthesized design candidate topology with rationale and calculated parameters."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    topology: str
    name: str
    description: str = ""
    parameters: Dict[str, float] = Field(default_factory=dict)
    calculated_metrics: Dict[str, float] = Field(default_factory=dict)  # e.g. efficiency, est_loss, component_count
    rationale: str = ""
    constraints_satisfied: bool = True
    feasibility_score: float = 1.0  # 0.0 - 1.0
    status: CandidateApprovalStatus = CandidateApprovalStatus.PROPOSED
    reviewer_notes: Optional[str] = None
    ir_snapshot: Optional[DesignIntermediateRepresentation] = None

    @property
    def topology_name(self) -> str:
        return self.name or self.topology

    @property
    def score(self) -> float:
        return self.feasibility_score


class ArtifactKind(str, Enum):
    NETLIST = "netlist"
    KICAD_SCH = "kicad_sch"
    KICAD_PCB = "kicad_pcb"
    FEMM_MODEL = "femm_model"
    STEP_SOLID = "step_solid"
    WAVEFORM = "waveform"
    REPORT = "report"
    CALCULATION_SHEET = "calculation_sheet"
    BOM = "bom"
    GERBER_BUNDLE = "gerber_bundle"


class DesignArtifact(BaseModel):
    """Tracked native file artifact generated or imported into the design."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    design_id: str
    revision_id: str
    kind: ArtifactKind
    name: str
    path: str
    format: str
    sha256: str
    source_service: str
    parent_ids: List[str] = Field(default_factory=list)
    edit_provenance: str = "Deterministic Generator"
    is_external_modified: bool = False
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class DesignRevision(BaseModel):
    """Immutable snapshot of an engineering design revision."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    design_id: str
    revision_index: int = 1
    label: str = "Rev 1"
    ir: DesignIntermediateRepresentation
    requirements_hash: str = ""
    summary: str = "Initial baseline"
    artifacts: List[DesignArtifact] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    created_by: str = "Engineer"

    @property
    def topology(self) -> str:
        return self.ir.topology if self.ir else "UNSPECIFIED"


class EngineeringDesign(BaseModel):
    """Primary engineering creation entity in Mendex Studio v1.9."""
    schema_version: str = "1.9.0"
    id: str = Field(default_factory=lambda: str(uuid4()))
    workspace_id: str
    title: str = "Untitled Design"
    category: str = "dc_dc_converter"
    status: DesignStatus = DesignStatus.DRAFT
    active_revision_id: Optional[str] = None
    product_id: Optional[str] = None  # Optional product association
    core_revision_id: Optional[str] = None
    requirements: List[Requirement] = Field(default_factory=list)
    candidates: List[DesignCandidate] = Field(default_factory=list)
    revisions: List[DesignRevision] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def get_active_revision(self) -> Optional[DesignRevision]:
        if not self.active_revision_id:
            return self.revisions[-1] if self.revisions else None
        for r in self.revisions:
            if r.id == self.active_revision_id:
                return r
        return None
