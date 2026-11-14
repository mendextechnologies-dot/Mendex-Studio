"""Physical Test and Laboratory Measurement Ingestion Service."""
from __future__ import annotations

import csv
import hashlib
import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4

from .models import InstrumentProfile, InstrumentType, MeasurementRecord, now


def compute_file_hash(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except Exception:
        return ""


class MeasurementService:
    """Manages physical laboratory measurements, CSV waveform imports, and simulated-vs-measured comparisons."""

    def __init__(self, service: Any):
        self.service = service
        self._init_db()

    def _init_db(self):
        try:
            with self.service.connection() as db:
                db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS measurements (
                        measurement_id TEXT PRIMARY KEY,
                        workspace_id TEXT,
                        product_id TEXT,
                        revision_id TEXT,
                        test_name TEXT NOT NULL,
                        measured_parameter TEXT NOT NULL,
                        measured_value REAL NOT NULL,
                        pass_fail TEXT NOT NULL,
                        payload TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    )
                    """
                )
                db.execute("CREATE TRIGGER IF NOT EXISTS measurements_no_update BEFORE UPDATE ON measurements BEGIN SELECT RAISE(ABORT, 'Measurement records are append-only'); END;")
                db.execute("CREATE TRIGGER IF NOT EXISTS measurements_no_delete BEFORE DELETE ON measurements BEGIN SELECT RAISE(ABORT, 'Measurement records are append-only'); END;")
        except Exception:
            pass

    def parse_csv_waveform(self, csv_path: Path) -> Tuple[List[float], List[float]]:
        """Parses laboratory oscilloscope CSV trace into (time_vector, value_vector)."""
        time_vec: List[float] = []
        val_vec: List[float] = []

        if not csv_path.exists():
            return time_vec, val_vec

        with open(csv_path, "r", encoding="utf-8", errors="ignore") as f:
            reader = csv.reader(f)
            for row in reader:
                if not row or len(row) < 2:
                    continue
                # Skip comments or text headers
                try:
                    t = float(row[0].strip())
                    v = float(row[1].strip())
                    time_vec.append(t)
                    val_vec.append(v)
                except ValueError:
                    continue
        return time_vec, val_vec

    def record_measurement(
        self,
        test_name: str,
        procedure_reference: str,
        instrument_name: str,
        instrument_serial: str,
        calibration_reference: str,
        operator: str,
        measured_parameter: str,
        measured_value: float,
        unit: str,
        simulated_value: Optional[float] = None,
        tolerance_min: Optional[float] = None,
        tolerance_max: Optional[float] = None,
        waveform_csv_path: Optional[str] = None,
        notes: str = "",
        workspace_id: Optional[str] = None,
        product_id: Optional[UUID] = None,
        revision_id: Optional[UUID] = None,
    ) -> MeasurementRecord:
        """Records an authentic physical laboratory test measurement with verification comparison."""
        error_pct = None
        if simulated_value is not None and simulated_value != 0:
            error_pct = abs(measured_value - simulated_value) / abs(simulated_value) * 100.0

        pass_fail = "NOT_EVALUATED"
        if tolerance_min is not None and tolerance_max is not None:
            if tolerance_min <= measured_value <= tolerance_max:
                pass_fail = "PASSED"
            else:
                pass_fail = "FAILED"
        elif tolerance_max is not None:
            pass_fail = "PASSED" if measured_value <= tolerance_max else "FAILED"
        elif tolerance_min is not None:
            pass_fail = "PASSED" if measured_value >= tolerance_min else "FAILED"

        csv_hash = None
        if waveform_csv_path:
            p = Path(waveform_csv_path)
            if p.exists():
                csv_hash = compute_file_hash(p)

        rec = MeasurementRecord(
            test_name=test_name,
            procedure_reference=procedure_reference,
            instrument_name=instrument_name,
            instrument_serial=instrument_serial,
            calibration_reference=calibration_reference,
            operator=operator,
            waveform_csv_path=waveform_csv_path,
            waveform_sha256=csv_hash,
            measured_parameter=measured_parameter,
            measured_value=measured_value,
            unit=unit,
            simulated_value=simulated_value,
            error_percentage=error_pct,
            tolerance_min=tolerance_min,
            tolerance_max=tolerance_max,
            pass_fail=pass_fail,
            notes=notes,
            workspace_id=workspace_id,
            product_id=product_id,
            revision_id=revision_id,
        )

        with self.service.connection() as db:
            db.execute(
                """
                INSERT INTO measurements (measurement_id, workspace_id, product_id, revision_id, test_name, measured_parameter, measured_value, pass_fail, payload, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(rec.measurement_id),
                    workspace_id,
                    str(product_id) if product_id else None,
                    str(revision_id) if revision_id else None,
                    rec.test_name,
                    rec.measured_parameter,
                    rec.measured_value,
                    rec.pass_fail,
                    rec.model_dump_json(),
                    rec.timestamp.isoformat(),
                ),
            )
        return rec

    def list_measurements(
        self,
        workspace_id: Optional[str] = None,
        product_id: Optional[UUID] = None,
        revision_id: Optional[UUID] = None,
    ) -> List[MeasurementRecord]:
        records = []
        try:
            with self.service.connection() as db:
                query = "SELECT payload FROM measurements WHERE 1=1"
                params = []
                if workspace_id:
                    query += " AND workspace_id=?"
                    params.append(workspace_id)
                if revision_id:
                    query += " AND revision_id=?"
                    params.append(str(revision_id))
                elif product_id:
                    query += " AND product_id=?"
                    params.append(str(product_id))
                query += " ORDER BY created_at DESC"
                rows = db.execute(query, params).fetchall()
                for r in rows:
                    records.append(MeasurementRecord.model_validate_json(r[0]))
        except Exception:
            pass
        return records

    def compare_waveforms(
        self,
        measured_csv: Path,
        simulated_time: List[float],
        simulated_val: List[float],
    ) -> Dict[str, Any]:
        """Compares physical oscilloscope CSV trace against simulated vector points."""
        m_t, m_v = self.parse_csv_waveform(measured_csv)
        if not m_t or not simulated_time:
            return {
                "status": "UNAVAILABLE",
                "reason": "Missing or empty waveform vectors",
            }

        # Calculate basic metrics
        m_mean = sum(m_v) / len(m_v)
        s_mean = sum(simulated_val) / len(simulated_val)
        m_pk_pk = max(m_v) - min(m_v)
        s_pk_pk = max(simulated_val) - min(simulated_val)

        return {
            "status": "COMPUTED",
            "measured_points": len(m_t),
            "simulated_points": len(simulated_time),
            "measured_mean": round(m_mean, 4),
            "simulated_mean": round(s_mean, 4),
            "mean_error_percent": round(abs(m_mean - s_mean) / max(abs(s_mean), 1e-9) * 100.0, 2),
            "measured_pk_pk": round(m_pk_pk, 4),
            "simulated_pk_pk": round(s_pk_pk, 4),
        }
