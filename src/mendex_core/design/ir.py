"""Design Intermediate Representation (IR) for Mendex Engineering Studio v1.9.

Provides a canonical, syntax-independent circuit and multiphysics representation
decoupled from specific simulator or CAD file formats (LTspice, KiCad, FEMM, FreeCAD).
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4
from pydantic import BaseModel, Field


class ComponentType(str, Enum):
    RESISTOR = "resistor"
    CAPACITOR = "capacitor"
    INDUCTOR = "inductor"
    TRANSFORMER = "transformer"
    SWITCH_MOSFET = "mosfet"
    SWITCH_IGBT = "igbt"
    SWITCH_GAN = "gan"
    SWITCH_SIC = "sic"
    DIODE = "diode"
    VOLTAGE_SOURCE = "voltage_source"
    CURRENT_SOURCE = "current_source"
    GROUND = "ground"
    IC_CONTROLLER = "controller"
    CONNECTOR = "connector"
    GENERIC = "generic"


class PortDirection(str, Enum):
    INPUT = "input"
    OUTPUT = "output"
    BIDIRECTIONAL = "bidirectional"
    POWER = "power"
    GROUND = "ground"


class IRParameter(BaseModel):
    """Named parametric property with unit, tolerance, and formula expression."""
    name: str
    expression: Optional[str] = None
    value: float
    unit: str = ""
    tolerance_pct: float = 0.0
    description: str = ""


class IRPin(BaseModel):
    """Component terminal pin."""
    pin_id: str
    name: str
    direction: PortDirection = PortDirection.BIDIRECTIONAL


class IRComponent(BaseModel):
    """Abstract circuit or hardware component in Design IR."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    designator: str  # e.g. R1, C1, T1, Q1
    name: str
    type: ComponentType
    value: float = 0.0
    unit: str = ""
    pins: List[IRPin] = Field(default_factory=list)
    parameters: Dict[str, Any] = Field(default_factory=dict)
    footprint: Optional[str] = None
    spice_model: Optional[str] = None
    mpn: Optional[str] = None
    manufacturer: Optional[str] = None


class IRNetPinRef(BaseModel):
    """Reference to a specific component pin connected to a net."""
    component_id: str
    pin_id: str


class IRNet(BaseModel):
    """Electrical net interconnecting component pins."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    connections: List[IRNetPinRef] = Field(default_factory=list)
    is_power: bool = False
    is_ground: bool = False


class IRPort(BaseModel):
    """External boundary port of the design."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    direction: PortDirection
    net_name: str
    nominal_voltage: Optional[float] = None


class IRMagneticGeometry(BaseModel):
    """Physical dimensions for magnetic core and bobbin components."""
    core_type: str = "ETD34"
    core_material: str = "N87"
    effective_area_ae_mm2: float = 97.1
    effective_length_le_mm: float = 78.6
    effective_volume_ve_mm3: float = 7630.0
    air_gap_mm: float = 0.5
    al_nh: float = 210.0
    primary_turns: int = 24
    secondary_turns: int = 4
    bobbin_height_mm: float = 21.0
    flange_od_mm: float = 34.0
    barrel_od_mm: float = 18.0
    core_id_mm: float = 16.0


class DesignIntermediateRepresentation(BaseModel):
    """Canonical syntax-independent design container."""
    schema_version: str = "1.9.0"
    id: str = Field(default_factory=lambda: str(uuid4()))
    title: str = "Untitled Design"
    topology: str = "Generic"
    category: str = "power_electronics"
    parameters: Dict[str, IRParameter] = Field(default_factory=dict)
    components: List[IRComponent] = Field(default_factory=list)
    nets: List[IRNet] = Field(default_factory=list)
    ports: List[IRPort] = Field(default_factory=list)
    magnetic_geometry: Optional[IRMagneticGeometry] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def get_component(self, designator: str) -> Optional[IRComponent]:
        for c in self.components:
            if c.designator.upper() == designator.upper():
                return c
        return None

    def get_net(self, name: str) -> Optional[IRNet]:
        for n in self.nets:
            if n.name.upper() == name.upper():
                return n
        return None

    def add_component(self, comp: IRComponent) -> None:
        self.components.append(comp)

    def add_net_connection(self, net_name: str, component_id: str, pin_id: str) -> None:
        net = self.get_net(net_name)
        if not net:
            net = IRNet(name=net_name)
            self.nets.append(net)
        net.connections.append(IRNetPinRef(component_id=component_id, pin_id=pin_id))
