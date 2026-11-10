from datetime import datetime, timezone
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator


def now() -> datetime:
    return datetime.now(timezone.utc)


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, str_strip_whitespace=True)


class Category(StrEnum):
    TRANSFORMER = "transformer"
    DC_DC = "dc_dc_converter"
    DEVICE = "power_semiconductor"
    PCB = "pcb"


class Lifecycle(StrEnum):
    DRAFT = "draft"
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
