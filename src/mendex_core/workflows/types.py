"""Workflow port data types, value wrappers, and unit compatibility rules."""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class PortDataType(str, Enum):
    SCALAR = "scalar"
    BOOLEAN = "boolean"
    STRING = "string"
    QUANTITY = "quantity"
    VECTOR = "vector"
    TIME_SERIES = "time_series"
    FILE_REF = "file_ref"
    DATASET_REF = "dataset_ref"
    SIM_RESULT = "sim_result"
    ARTIFACT = "artifact"
    VALIDATION_RESULT = "validation_result"
    ANY = "any"


class QuantityValue(BaseModel):
    value: float
    unit: str = ""

    def to_canonical(self) -> tuple[float, str]:
        """Convert standard engineering units to SI canonical base units."""
        u = self.unit.strip().lower()
        v = self.value
        
        # Frequency
        if u in ("hz", "hertz"): return v, "hz"
        if u == "khz": return v * 1e3, "hz"
        if u == "mhz": return v * 1e6, "hz"
        if u == "ghz": return v * 1e9, "hz"
        
        # Voltage
        if u == "v": return v, "v"
        if u == "mv": return v * 1e-3, "v"
        if u == "kv": return v * 1e3, "v"
        if u == "uv": return v * 1e-6, "v"
        
        # Current
        if u == "a": return v, "a"
        if u == "ma": return v * 1e-3, "a"
        if u == "ua": return v * 1e-6, "a"
        
        # Inductance
        if u == "h": return v, "h"
        if u == "mh": return v * 1e-3, "h"
        if u == "uh": return v * 1e-6, "h"
        if u == "nh": return v * 1e-9, "h"
        
        # Capacitance
        if u == "f": return v, "f"
        if u == "mf": return v * 1e-3, "f"
        if u == "uf": return v * 1e-6, "f"
        if u == "nf": return v * 1e-9, "f"
        if u == "pf": return v * 1e-12, "f"
        
        # Resistance
        if u in ("ohm", "ohms", "Ω"): return v, "ohm"
        if u in ("kohm", "kΩ"): return v * 1e3, "ohm"
        if u in ("mohm", "mΩ"): return v * 1e-3, "ohm"  # milliohm
        if u in ("megohm", "m", "meg"): return v * 1e6, "ohm"
        
        # Length
        if u == "m": return v, "m"
        if u == "mm": return v * 1e-3, "m"
        if u == "um": return v * 1e-6, "m"
        if u == "cm": return v * 1e-2, "m"
        if u == "in": return v * 0.0254, "m"
        if u == "mil": return v * 2.54e-5, "m"
        
        # Power
        if u == "w": return v, "w"
        if u == "mw": return v * 1e-3, "w"
        if u == "kw": return v * 1e3, "w"
        
        # Magnetic Flux Density
        if u == "t": return v, "t"
        if u == "mt": return v * 1e-3, "t"
        
        # Temperature
        if u in ("c", "°c", "degc"): return v + 273.15, "k"
        if u in ("k", "kelvin"): return v, "k"
        
        return v, u


class TimeSeriesData(BaseModel):
    time: List[float] = Field(default_factory=list)
    signals: Dict[str, List[float]] = Field(default_factory=dict)
    units: Dict[str, str] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class FileReference(BaseModel):
    path: str
    filename: str
    mime_type: str = "application/octet-stream"
    sha256: Optional[str] = None
    size_bytes: Optional[int] = None


class DatasetReference(BaseModel):
    dataset_id: str
    version: str
    tool_id: str = "generic"
    record_count: Optional[int] = None


class SimulationResultData(BaseModel):
    job_id: str
    tool_id: str
    status: str
    output_files: List[str] = Field(default_factory=list)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    raw_path: Optional[str] = None
    manifest_sha256: Optional[str] = None


class ArtifactData(BaseModel):
    path: str
    artifact_type: str
    sha256: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ValidationResultData(BaseModel):
    check_id: str
    passed: bool
    status: str = "PASS"  # PASS, FAIL, NOT_EVALUATED
    actual_value: Any = None
    expected_value: Any = None
    tolerance: Optional[float] = None
    unit: str = ""
    message: str = ""


class PortDefinition(BaseModel):
    name: str
    display_name: str
    data_type: PortDataType
    required: bool = True
    default_value: Any = None
    unit: Optional[str] = None
    description: str = ""


def check_type_compatibility(source_type: PortDataType, target_type: PortDataType) -> bool:
    """Validate whether source port can connect to target port."""
    if target_type == PortDataType.ANY or source_type == PortDataType.ANY:
        return True
    if source_type == target_type:
        return True
    # Quantity can feed into Scalar (extracting the raw magnitude)
    if source_type == PortDataType.QUANTITY and target_type == PortDataType.SCALAR:
        return True
    # Scalar can feed into Quantity (with default unit)
    if source_type == PortDataType.SCALAR and target_type == PortDataType.QUANTITY:
        return True
    # String can accept any scalar or quantity representation
    if target_type == PortDataType.STRING:
        return True
    # Simulation Result can feed into TimeSeries or Artifact
    if source_type == PortDataType.SIM_RESULT and target_type in (PortDataType.TIME_SERIES, PortDataType.ARTIFACT, PortDataType.FILE_REF):
        return True
    # FileRef can feed into Artifact
    if source_type == PortDataType.FILE_REF and target_type == PortDataType.ARTIFACT:
        return True
    return False


def check_unit_compatibility(source_unit: Optional[str], target_unit: Optional[str]) -> bool:
    """Validate whether two units have identical dimensional base."""
    if not source_unit or not target_unit:
        return True  # Open unit
    q1 = QuantityValue(value=1.0, unit=source_unit)
    q2 = QuantityValue(value=1.0, unit=target_unit)
    _, base1 = q1.to_canonical()
    _, base2 = q2.to_canonical()
    return base1 == base2
