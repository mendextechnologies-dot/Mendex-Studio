"""Component and Material Library contracts for Mendex Engineering Studio v1.9."""
from __future__ import annotations

from typing import Literal, Optional
from uuid import uuid4
from pydantic import BaseModel, Field, ConfigDict


class ReferenceRecord(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    datasheet_url: Optional[str] = None
    source_checked_on: Optional[str] = None
    verification_status: Literal["NOT_EVALUATED"] = "NOT_EVALUATED"
    provenance: str = "Reference only; application qualification NOT_EVALUATED"
    conditions: str = ""
    lifecycle_status: str = "UNKNOWN"


class ComponentRecord(ReferenceRecord):
    """Sourced component reference; absent ratings and models are unknown."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    mpn: str
    manufacturer: str
    category: str  # mosfet, diode, core, capacitor, resistor, driver
    description: str = ""
    package: Optional[str] = None
    record_kind: Literal["PART", "FAMILY"] = "PART"
    voltage_rating_v: Optional[float] = Field(default=None, gt=0)
    current_rating_a: Optional[float] = Field(default=None, gt=0)
    power_rating_w: Optional[float] = Field(default=None, gt=0)
    rds_on_ohm: Optional[float] = Field(default=None, gt=0)
    esr_ohm: Optional[float] = Field(default=None, gt=0)
    kicad_footprint: Optional[str] = None
    kicad_symbol: Optional[str] = None
    kicad_3d_model: Optional[str] = None
    spice_model_name: Optional[str] = None


class MaterialRecord(ReferenceRecord):
    """Magnetic core and thermal material characteristics with physics model parameters."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str  # e.g. N87, N97, 3C90, KoolMu
    material_type: str = "Unspecified"
    manufacturer: str = ""
    initial_permeability_ui: Optional[float] = Field(default=None, gt=0)
    saturation_flux_t: Optional[float] = Field(default=None, gt=0)
    curie_temp_c: Optional[float] = None
    curie_temp_qualifier: str = ""
    steinmetz_cm: Optional[float] = None
    steinmetz_alpha: Optional[float] = None
    steinmetz_beta: Optional[float] = None
    freq_min_hz: Optional[float] = Field(default=None, gt=0)
    freq_max_hz: Optional[float] = Field(default=None, gt=0)

    @property
    def loss_model_ready(self) -> bool:
        return all(value is not None and value > 0 for value in (
            self.steinmetz_cm, self.steinmetz_alpha, self.steinmetz_beta, self.saturation_flux_t
        ))


class MagneticCoreRecord(ReferenceRecord):
    """Geometry reference; a shape name alone does not identify a characterized part."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str  # e.g. Planar E22/6/16, PQ26/20, RM8, EFD20, ETD29
    geometry_type: str = "Unspecified"
    ae_mm2: Optional[float] = Field(default=None, gt=0)
    le_mm: Optional[float] = Field(default=None, gt=0)
    ve_mm3: Optional[float] = Field(default=None, gt=0)
    amin_mm2: Optional[float] = Field(default=None, gt=0)
    aw_mm2: Optional[float] = Field(default=None, gt=0)
    manufacturer: str = "Unspecified; select exact manufacturer and part"

    @property
    def geometry_ready(self) -> bool:
        return all(value is not None and value > 0 for value in (
            self.ae_mm2, self.le_mm, self.ve_mm3, self.aw_mm2
        ))

