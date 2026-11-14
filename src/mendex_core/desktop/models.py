from typing import Literal, Optional, Optional
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
    format: Optional[str] = 'html'


class ExportReportQuery(ReportQuery):
    idempotency_key: str = Field(min_length=1, max_length=128)


class ReportGenerateQuery(Model):
    idempotency_key: Optional[str] = None
    revision_id: UUID


class EvidenceQuery(Model):
    record_id: UUID


class ReviewPackageQuery(Model):
    revision_id: UUID
    stage_id: str = "requirements"


class BOMQuery(Model):
    revision_id: UUID


class CADPreviewQuery(Model):
    idempotency_key: Optional[str] = None
    revision_id: UUID
    kind: Literal["pcb", "schematic", "3d"] = "pcb"
    view: str = "iso" 


class AutoRouteQuery(Model):
    idempotency_key: Optional[str] = None
    revision_id: UUID
    pour_ground: bool = True
    ground_net: str = "GND"
    ripup: str = "all"
    default_track: float = 0.4
    power_track: float = 1.2
    thermal_spoke: float = 0.5
    thermal_gap: float = 0.5
    pad_connection: Literal["tht_thermal", "thermal", "solid", "none"] = "tht_thermal"
    stitch_ground: bool = False
    stitch_pitch: float = 5.0
    zone_clearance: float = 0.5
    pour_layers: Optional[list[str]] = None


class IsolationSlotQuery(Model):
    idempotency_key: Optional[str] = None
    revision_id: UUID
    slot_width: float = 2.5
    slot_length: Optional[float] = None
    center_x: Optional[float] = None
    center_y: Optional[float] = None

class FourLayerPlanesQuery(Model):
    idempotency_key: Optional[str] = None
    revision_id: UUID
    gnd_net: str = "PRI_GND"
    pwr_net: str = "VIN"
    zone_clearance: float = 0.5
    thermal_spoke: float = 0.5
    pad_connection: Literal["tht_thermal", "thermal", "solid", "none"] = "tht_thermal" 


class GerberExportQuery(Model):
    idempotency_key: Optional[str] = None
    revision_id: UUID
    auto_route: bool = True
    check_drc: bool = True
    design_id: Optional[str] = None


class GerberInspectQuery(Model):
    revision_id: UUID
    auto_export: bool = True


class TopologySynthesizeQuery(Model):
    revision_id: UUID
    idempotency_key: Optional[str] = None


class CandidateSelectQuery(Model):
    revision_id: UUID
    candidate_id: str
    auto_export_kicad: bool = True


class GerberDownloadQuery(Model):
    revision_id: UUID


class SchematicApplyQuery(Model):
    revision_id: UUID
    ops: list[dict]
    verify: bool = True


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


class BackupQuery(Model):
    destination: Optional[str] = None


class ECRListQuery(Model):
    workspace_id: Optional[str] = None
    product_id: Optional[UUID] = None
    revision_id: Optional[UUID] = None


class ECRCreateQuery(Model):
    title: str
    description: str
    reason: str
    impact_analysis: str
    requested_by: str
    affected_stages: Optional[list[str]] = None
    workspace_id: Optional[str] = None
    product_id: Optional[UUID] = None
    revision_id: Optional[UUID] = None
    schematic_ops: Optional[list[dict]] = None


class ECRReviewQuery(Model):
    ecr_id: UUID
    reviewer: str
    status: str
    review_notes: str = ""


class ECRApplySchematicQuery(Model):
    ecr_id: UUID
    implemented_by: Optional[str] = None
    forward_annotate: bool = True


class ForwardAnnotatePcbQuery(Model):
    revision_id: UUID
    ecr_id: Optional[UUID] = None
    remove_extra: bool = True
    auto_place_new: bool = True
    refill_zones: bool = True


class STEPExportQuery(Model):
    idempotency_key: Optional[str] = None
    revision_id: UUID
    open_native: bool = False
    design_id: Optional[str] = None


class BridgeRequest(Model):
    protocol_version: Literal["3.1.0"]
    id: str = Field(min_length=1, max_length=128)
    method: str = Field(min_length=1, max_length=80)
    params: dict = Field(default_factory=dict)

class ThermalSizingQuery(Model):
    revision_id: UUID
    ambient_temp_c: Optional[float] = None
    p_switch_loss_w: Optional[float] = None
    r_th_jc_c_w: Optional[float] = None
    r_th_cs_c_w: Optional[float] = None
    r_th_sa_c_w: Optional[float] = None
    t_j_max_c: Optional[float] = None
    derating_factor: Optional[float] = None
    transformer_surface_area_cm2: Optional[float] = None
    trace_current_a: Optional[float] = None
    target_trace_delta_t_c: Optional[float] = None
    copper_thickness_oz: Optional[float] = None
    is_internal_trace: Optional[bool] = None
    record_evidence: bool = False
    idempotency_key: Optional[str] = None


class Render3DQuery(Model):
    idempotency_key: Optional[str] = None
    revision_id: UUID
    view: str = "iso"
    width: int = Field(default=1200, ge=400, le=3840)
    height: int = Field(default=900, ge=300, le=2160)
    quality: str = "basic"


class OperationReceiptQuery(Model):
    operation_id: Optional[UUID] = None
    idempotency_key: Optional[str] = None
    revision_id: Optional[UUID] = None

class TestPlanQuery(Model):
    revision_id: UUID


class BOMPricingQuery(Model):
    revision_id: UUID
    currency: str = "USD"

