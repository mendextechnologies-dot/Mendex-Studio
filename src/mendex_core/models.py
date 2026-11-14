from datetime import datetime, timezone
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator


def now() -> datetime:
    return datetime.now(timezone.utc)


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, str_strip_whitespace=True, revalidate_instances="always", validate_assignment=True)


class Category(StrEnum):
    TRANSFORMER = "transformer"
    DC_DC = "dc_dc_converter"
    DEVICE = "power_semiconductor"
    PCB = "pcb"


class Lifecycle(StrEnum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    ARCHIVED = "archived"


class Specification(Model):
    schema_version: str = Field(default="1.0", pattern=r"^1\.0$")
    vin_min_v: float | None = Field(default=None, gt=0)
    vin_nom_v: float | None = Field(default=None, gt=0)
    vin_max_v: float | None = Field(default=None, gt=0)
    vout_v: float | None = Field(default=None, gt=0)
    iout_a: float | None = Field(default=None, ge=0)
    switching_frequency_hz: float | None = Field(default=None, gt=0)
    ambient_temperature_k: float | None = Field(default=None, gt=0)
    ambient_temperature_c: float | None = Field(default=None, ge=-273.15)
    target_efficiency_pct: float | None = Field(default=None, gt=0, le=100)
    vout_ripple_max_mv: float | None = Field(default=None, gt=0)
    line_regulation_pct: float | None = Field(default=None, ge=0)
    load_regulation_pct: float | None = Field(default=None, ge=0)
    max_junction_temperature_c: float | None = Field(default=150.0, gt=0)
    cooling_method: str = Field(default="natural_convection")
    max_pcb_width_mm: float | None = Field(default=None, gt=0)
    max_pcb_height_mm: float | None = Field(default=None, gt=0)
    target_cost_usd: float | None = Field(default=None, ge=0)
    reliability_mtbf_hours: float | None = Field(default=None, gt=0)
    topology: str = ""
    isolation_requirement: str = ""
    standards_profile: str = "UNASSIGNED"
    source: str = ""
    assumptions: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def ordered_voltage(self):
        values = [v for v in (self.vin_min_v, self.vin_nom_v, self.vin_max_v) if v is not None]
        if values != sorted(values):
            raise ValueError("Input voltages must satisfy minimum <= nominal <= maximum")
        if self.ambient_temperature_k is not None and self.ambient_temperature_c is not None:
            if abs((self.ambient_temperature_c + 273.15) - self.ambient_temperature_k) > 1.0:
                raise ValueError("ambient_temperature_c and ambient_temperature_k must be thermodynamically consistent")
        if self.vout_ripple_max_mv is not None and self.vout_v is not None:
            if self.vout_ripple_max_mv >= (self.vout_v * 1000.0):
                raise ValueError("vout_ripple_max_mv must be strictly less than nominal output voltage")
        return self


class Product(Model):
    product_id: UUID = Field(default_factory=uuid4)
    code: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
    name: str = Field(min_length=1, max_length=200)
    category: Category
    owner: str = Field(min_length=1, max_length=200)
    description: str = ""
    created_at: datetime = Field(default_factory=now)
    updated_at: datetime = Field(default_factory=now)
    active_revision_id: UUID


class Revision(Model):
    revision_id: UUID = Field(default_factory=uuid4)
    product_id: UUID
    revision_label: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
    lifecycle_status: Lifecycle = Lifecycle.DRAFT
    specification: Specification = Field(default_factory=Specification)
    created_at: datetime = Field(default_factory=now)


class EngineeringWorkspace(Model):
    workspace_id: UUID = Field(default_factory=uuid4)
    name: str = Field(min_length=1, max_length=200)
    description: str = ""
    owner: str = Field(default="Engineer", min_length=1, max_length=200)
    storage_path: str = ""
    product_id: UUID | None = None
    created_at: datetime = Field(default_factory=now)
    updated_at: datetime = Field(default_factory=now)
    metadata: dict = Field(default_factory=dict)


class EngineeringActivity(Model):
    activity_id: UUID = Field(default_factory=uuid4)
    workspace_id: UUID
    name: str = Field(min_length=1, max_length=200)
    activity_type: str = Field(default="simulation", min_length=1, max_length=64)
    tool_id: str | None = None
    parameters: dict = Field(default_factory=dict)
    input_files: list[str] = Field(default_factory=list)
    status: str = Field(default="PENDING", pattern=r"^(PENDING|RUNNING|COMPLETED|FAILED|CANCELLED)$")
    product_id: UUID | None = None
    created_at: datetime = Field(default_factory=now)
    updated_at: datetime = Field(default_factory=now)

