"""Component and Material Library contracts for Mendex Engineering Studio v1.9."""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import uuid4
from pydantic import BaseModel, Field


class ComponentRecord(BaseModel):
    """Verified physical component with ratings, CAD footprints, and SPICE models."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    mpn: str
    manufacturer: str
    category: str  # mosfet, diode, core, capacitor, resistor, driver
    description: str = ""
    package: str = "TO-220"
    voltage_rating_v: float = 0.0
    current_rating_a: float = 0.0
    power_rating_w: float = 0.0
    rds_on_ohm: Optional[float] = None
    esr_ohm: Optional[float] = None
    kicad_footprint: Optional[str] = None
    kicad_symbol: Optional[str] = None
    spice_model_name: Optional[str] = None
    datasheet_url: Optional[str] = None
    provenance: str = "Mendex Verified Component Library"


class MaterialRecord(BaseModel):
    """Magnetic core and thermal material characteristics with physics model parameters."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str  # e.g. N87, N97, 3C90, KoolMu
    material_type: str = "Ferrite"
    initial_permeability_ui: float = 2200.0
    saturation_flux_t: float = 0.49
    curie_temp_c: float = 210.0
    steinmetz_cm: float = 10.0
    steinmetz_alpha: float = 1.3
    steinmetz_beta: float = 2.5
    freq_min_hz: float = 25000.0
    freq_max_hz: float = 500000.0
    provenance: str = "Manufacturer Material Datasheet"


class MagneticCoreRecord(BaseModel):
    """Verified magnetic core geometry with effective area, path length, and volume."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str  # e.g. Planar E22/6/16, PQ26/20, RM8, EFD20, ETD29
    geometry_type: str = "Planar E"
    ae_mm2: float
    le_mm: float
    ve_mm3: float
    amin_mm2: float = 0.0
    aw_mm2: float = 0.0
    manufacturer: str = "Ferroxcube / TDK"
    provenance: str = "Verified Magnetic Core Datasheet"

