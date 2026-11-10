"""Data models for laboratory physical tests, instrument profiles, and measurement data."""
from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


def now() -> datetime:
    return datetime.now(timezone.utc)


class InstrumentType(StrEnum):
    OSCILLOSCOPE = "oscilloscope"
    POWER_ANALYZER = "power_analyzer"
    LCR_METER = "lcr_meter"
    MULTIMETER = "multimeter"
    SPECTRUM_ANALYZER = "spectrum_analyzer"
    THERMAL_IMAGER = "thermal_imager"
    DATA_LOGGER = "data_logger"
    OTHER = "other"


class InstrumentProfile(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    instrument_id: str
    instrument_name: str
    instrument_type: InstrumentType
    manufacturer: str
    serial_number: str
    calibration_reference: str
    last_calibrated: Optional[str] = None
    calibration_due: Optional[str] = None
    interface_type: str = "CSV_IMPORT"  # CSV_IMPORT, USB-TMC, VISA, VXI-11


class MeasurementRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    measurement_id: UUID = Field(default_factory=uuid4)
    test_name: str
    procedure_reference: str
    instrument_name: str
    instrument_serial: str
    calibration_reference: str
    operator: str
    timestamp: datetime = Field(default_factory=now)
    waveform_csv_path: Optional[str] = None
    waveform_sha256: Optional[str] = None
    measured_parameter: str
    measured_value: float
    unit: str
    simulated_value: Optional[float] = None
    error_percentage: Optional[float] = None
    tolerance_min: Optional[float] = None
    tolerance_max: Optional[float] = None
    pass_fail: str = "NOT_EVALUATED"  # PASSED, FAILED, NOT_EVALUATED
    notes: str = ""
    workspace_id: Optional[str] = None
    product_id: Optional[UUID] = None
    revision_id: Optional[UUID] = None
