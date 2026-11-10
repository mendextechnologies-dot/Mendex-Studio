from __future__ import annotations

import csv
import json
from pathlib import Path
from pydantic import BaseModel, ConfigDict
from .provenance import DatasetMetadata, verify_dataset_file


class DeviceSwitchLossRecord(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    part_number: str
    manufacturer: str
    device_type: str  # MOSFET, IGBT, GaN, SiC
    v_ds_rated_v: float
    i_d_rated_a: float
    r_ds_on_mohm: float | None = None
    e_on_uj: float | None = None
    e_off_uj: float | None = None
    v_test_v: float | None = None
    i_test_a: float | None = None
    t_j_c: float | None = None


class SwitchLossDB:
    """Interface to SwitchLossDB semiconductor switching loss dataset."""

    DATASET_ID = "switchloss_db"
    OFFICIAL_URL = "https://github.com/switchloss/switchloss-db"
    LICENSE = "CC-BY-4.0"

    def __init__(self, data_file: Path | None = None, metadata: DatasetMetadata | None = None):
        self.data_file = data_file
        self.metadata = metadata
        self._records: list[DeviceSwitchLossRecord] = []

    def load_csv(self, csv_path: Path, expected_sha256: str | None = None) -> int:
        if expected_sha256 and not verify_dataset_file(csv_path, expected_sha256):
            raise ValueError(f"SwitchLossDB file integrity check failed for {csv_path}")

        records: list[DeviceSwitchLossRecord] = []
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rec = DeviceSwitchLossRecord(
                    part_number=row.get("part_number", ""),
                    manufacturer=row.get("manufacturer", ""),
                    device_type=row.get("device_type", "MOSFET"),
                    v_ds_rated_v=float(row.get("v_ds_rated_v", 0.0)),
                    i_d_rated_a=float(row.get("i_d_rated_a", 0.0)),
                    r_ds_on_mohm=float(row["r_ds_on_mohm"]) if row.get("r_ds_on_mohm") else None,
                    e_on_uj=float(row["e_on_uj"]) if row.get("e_on_uj") else None,
                    e_off_uj=float(row["e_off_uj"]) if row.get("e_off_uj") else None,
                    v_test_v=float(row["v_test_v"]) if row.get("v_test_v") else None,
                    i_test_a=float(row["i_test_a"]) if row.get("i_test_a") else None,
                    t_j_c=float(row["t_j_c"]) if row.get("t_j_c") else None,
                )
                records.append(rec)
        self._records = records
        return len(records)

    def find_devices(self, min_voltage: float = 0.0, min_current: float = 0.0) -> list[DeviceSwitchLossRecord]:
        return [r for r in self._records if r.v_ds_rated_v >= min_voltage and r.i_d_rated_a >= min_current]
