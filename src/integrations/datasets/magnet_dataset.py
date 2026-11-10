from __future__ import annotations

import json
from pathlib import Path
from pydantic import BaseModel, ConfigDict
from .provenance import DatasetMetadata, verify_dataset_file


class CoreLossRecord(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    material: str
    temperature_c: float
    frequency_hz: float
    b_peak_t: float
    waveform: str  # sinusoidal, triangular, trapezoidal
    volumetric_loss_w_m3: float


class MagNetDataset:
    """Interface to MagNet (Princeton University) high-frequency magnetic core loss dataset."""

    DATASET_ID = "magnet_dataset"
    OFFICIAL_URL = "https://www.princeton.edu/~minjie/magnet.html"
    LICENSE = "CC-BY-4.0 / Academic"
    CITATION = "Minjie Chen et al., MagNet: A Machine Learning Framework for Magnetic Core Loss Modeling."

    def __init__(self, data_file: Path | None = None, metadata: DatasetMetadata | None = None):
        self.data_file = data_file
        self.metadata = metadata
        self._records: list[CoreLossRecord] = []

    def load_json(self, json_path: Path, expected_sha256: str | None = None) -> int:
        if expected_sha256 and not verify_dataset_file(json_path, expected_sha256):
            raise ValueError(f"MagNet dataset file integrity check failed for {json_path}")

        data = json.loads(json_path.read_text(encoding="utf-8"))
        records: list[CoreLossRecord] = []
        for row in data.get("measurements", []):
            rec = CoreLossRecord(
                material=row.get("material", "N87"),
                temperature_c=float(row.get("temperature_c", 25.0)),
                frequency_hz=float(row.get("frequency_hz", 100000.0)),
                b_peak_t=float(row.get("b_peak_t", 0.1)),
                waveform=row.get("waveform", "sinusoidal"),
                volumetric_loss_w_m3=float(row.get("volumetric_loss_w_m3", 0.0)),
            )
            records.append(rec)
        self._records = records
        return len(records)

    def query(self, material: str, max_freq_hz: float) -> list[CoreLossRecord]:
        return [r for r in self._records if r.material.lower() == material.lower() and r.frequency_hz <= max_freq_hz]
