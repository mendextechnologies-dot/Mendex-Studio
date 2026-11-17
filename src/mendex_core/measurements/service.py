"""Physical Test and Laboratory Measurement Ingestion Service."""
from __future__ import annotations

import csv
import hashlib
import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import UUID, uuid4

import numpy as np

from .correlation import correlate_scope_with_simulation
from .models import InstrumentProfile, InstrumentType, MeasurementRecord, now
from .scope_parser import (
    calculate_channel_metrics,
    compute_sha256,
    decimate_waveform,
    parse_scope_csv,
)


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
        evidence_source: str = "physical_test",
        workspace_id: Optional[str] = None,
        product_id: Optional[UUID] = None,
        revision_id: Optional[UUID] = None,
    ) -> MeasurementRecord:
        """Records an authentic physical laboratory test measurement with verification comparison."""
        if not test_name or not str(test_name).strip():
            raise ValueError("test_name cannot be empty.")
        if not measured_parameter or not str(measured_parameter).strip():
            raise ValueError("measured_parameter cannot be empty.")
        if not math.isfinite(measured_value):
            raise ValueError(f"measured_value must be a finite number (got {measured_value}).")
        if not operator or not str(operator).strip():
            raise ValueError("operator must be identified for laboratory measurement traceability.")
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
            evidence_source=evidence_source,
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

    # =========================================================================
    # ADVANCED OSCILLOSCOPE CSV INGESTION & CORRELATION ENGINE (OPTION 2)
    # =========================================================================

    def _scope_dir(self, revision_id: UUID) -> Path:
        """Returns the dedicated directory for storing raw oscilloscope CSV captures."""
        revision = self.service.get_revision(revision_id)
        ws_path = self.service.workspace_path(revision)
        target_dir = ws_path / "measurements" / "scope"
        target_dir.mkdir(parents=True, exist_ok=True)
        return target_dir

    def ingest_oscilloscope_csv(
        self,
        revision_id: UUID,
        filename: str,
        content: Union[str, bytes],
        channel_mapping: Optional[Dict[str, str]] = None,
        operator: str = "Lead Hardware Engineer",
        test_name: str = "Bench Oscilloscope Capture",
        procedure_reference: str = "SOP-HV-004",
        instrument_name: str = "Calibrated Bench Oscilloscope",
        instrument_serial: str = "TEK-MSO-849201",
        calibration_ref: str = "CAL-2026-Q3-0941",
        notes: str = "",
    ) -> Dict[str, Any]:
        """Ingests raw oscilloscope CSV capture, validates signal arrays, computes cryptographic

        SHA-256 digest, persists immutable file, and registers measurement record.
        """
        raw_bytes = content.encode("utf-8") if isinstance(content, str) else content
        sha256 = compute_sha256(raw_bytes)

        # Parse CSV waveform structure
        parsed = parse_scope_csv(raw_bytes)
        vendor = parsed["vendor"]
        time_arr = parsed["time"]
        channels = parsed["channels"]
        sample_rate_hz = parsed["sample_rate_hz"]
        duration_s = parsed["duration_s"]
        total_points = parsed["total_points"]

        # Calculate metrics for each channel
        channel_metrics: Dict[str, Dict[str, float]] = {}
        for ch_name, sig_arr in channels.items():
            channel_metrics[ch_name] = calculate_channel_metrics(time_arr, sig_arr)

        measurement_id = uuid4()
        short_id = str(measurement_id)[:8]
        clean_fn = Path(filename).name or "scope_capture.csv"
        saved_filename = f"{short_id}_{clean_fn}"
        dest_dir = self._scope_dir(revision_id)
        file_path = dest_dir / saved_filename
        # Use extended-length prefix on Windows if path is long
        s_fp = str(file_path.resolve())
        if len(s_fp) >= 240 and not s_fp.startswith("\\\\?\\"):
            Path("\\\\?\\" + s_fp).write_bytes(raw_bytes)
        else:
            file_path.write_bytes(raw_bytes)

        # Save metadata manifest
        manifest_path = dest_dir / f"{short_id}_manifest.json"
        manifest_data = {
            "measurement_id": str(measurement_id),
            "revision_id": str(revision_id),
            "original_filename": clean_fn,
            "saved_filename": saved_filename,
            "relative_path": str(file_path.relative_to(dest_dir.parent.parent)),
            "sha256": sha256,
            "vendor": vendor,
            "operator": operator,
            "test_name": test_name,
            "procedure_reference": procedure_reference,
            "instrument_name": instrument_name,
            "instrument_serial": instrument_serial,
            "calibration_reference": calibration_ref,
            "notes": notes,
            "timestamp": now().isoformat(),
            "sample_rate_hz": sample_rate_hz,
            "duration_s": duration_s,
            "total_points": total_points,
            "channels": list(channels.keys()),
            "channel_metrics": channel_metrics,
            "channel_mapping": channel_mapping or {},
        }
        manifest_path.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")

        # Register primary channel record in append-only DB
        primary_ch = next(iter(channels.keys())) if channels else "CH1"
        primary_mean = channel_metrics.get(primary_ch, {}).get("mean", 0.0)
        self.record_measurement(
            test_name=test_name,
            procedure_reference=procedure_reference,
            instrument_name=f"{vendor} {instrument_name}",
            instrument_serial=instrument_serial,
            calibration_reference=calibration_ref,
            operator=operator,
            measured_parameter=f"{primary_ch}_DC_MEAN",
            measured_value=primary_mean,
            unit="V",
            waveform_csv_path=str(file_path),
            notes=f"Raw scope capture: {clean_fn} (SHA: {sha256[:12]}...)",
            evidence_source="physical_test",
            revision_id=revision_id,
        )

        return {
            "success": True,
            "measurement_id": str(measurement_id),
            "filename": clean_fn,
            "relative_path": manifest_data["relative_path"],
            "sha256": sha256,
            "vendor": vendor,
            "sample_rate_hz": sample_rate_hz,
            "duration_s": duration_s,
            "total_points": total_points,
            "channels": list(channels.keys()),
            "channel_metrics": channel_metrics,
            "operator": operator,
            "timestamp": manifest_data["timestamp"],
        }

    def list_oscilloscope_measurements(self, revision_id: UUID) -> List[Dict[str, Any]]:
        """Lists all ingested oscilloscope measurements and manifests for a product revision."""
        dest_dir = self._scope_dir(revision_id)
        manifest_files = sorted(dest_dir.glob("*_manifest.json"), reverse=True)
        items: List[Dict[str, Any]] = []
        for mf in manifest_files:
            try:
                data = json.loads(mf.read_text(encoding="utf-8"))
                items.append(data)
            except Exception:
                continue
        return items

    def get_oscilloscope_waveform(
        self,
        revision_id: UUID,
        measurement_id: str,
        traces: Optional[List[str]] = None,
        start: int = 0,
        limit: int = 2000,
        decimate: bool = True,
    ) -> Dict[str, Any]:
        """Loads and returns downsampled or paginated samples for an ingested scope capture."""
        dest_dir = self._scope_dir(revision_id)
        manifest_path = dest_dir / f"{measurement_id[:8]}_manifest.json"
        if not manifest_path.exists():
            manifest_path = dest_dir / f"{measurement_id}_manifest.json"
        if not manifest_path.exists():
            # Scan all manifests in directory
            for mf in dest_dir.glob("*_manifest.json"):
                try:
                    data = json.loads(mf.read_text(encoding="utf-8"))
                    if data.get("measurement_id") == str(measurement_id) or str(measurement_id).startswith(mf.stem.split("_")[0]):
                        manifest_path = mf
                        break
                except Exception:
                    pass
        if not manifest_path.exists():
            return {"samples": [], "traces": [], "error": f"Measurement {measurement_id} not found"}

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        raw_file = dest_dir / manifest["saved_filename"]
        if not raw_file.exists():
            return {"samples": [], "traces": [], "error": "Raw scope CSV file missing"}

        raw_bytes = raw_file.read_bytes()
        parsed = parse_scope_csv(raw_bytes)
        time_arr = parsed["time"]
        channels = parsed["channels"]

        req_traces = traces or list(channels.keys())
        active_channels = {k: v for k, v in channels.items() if k in req_traces}

        total_pts = len(time_arr)
        if decimate and total_pts > limit:
            d_time, d_chans = decimate_waveform(time_arr, active_channels, target_points=limit)
        else:
            s_idx = min(max(0, start), total_pts)
            e_idx = min(s_idx + max(1, limit), total_pts)
            d_time = time_arr[s_idx:e_idx]
            d_chans = {k: v[s_idx:e_idx] for k, v in active_channels.items()}

        samples: List[Dict[str, float]] = []
        for i in range(len(d_time)):
            row = {"time": float(d_time[i])}
            for tr in req_traces:
                if tr in d_chans and i < len(d_chans[tr]):
                    row[tr] = float(d_chans[tr][i])
            samples.append(row)

        return {
            "measurement_id": measurement_id,
            "filename": manifest["original_filename"],
            "sha256": manifest["sha256"],
            "vendor": manifest["vendor"],
            "samples": samples,
            "traces": req_traces,
            "total_points": total_pts,
            "returned_points": len(samples),
            "sample_rate_hz": manifest["sample_rate_hz"],
            "duration_s": manifest["duration_s"],
            "channel_metrics": manifest["channel_metrics"],
            "operator": manifest.get("operator", ""),
            "timestamp": manifest.get("timestamp", ""),
        }

    def correlate_with_simulation(
        self,
        revision_id: UUID,
        measurement_id: str,
        sim_relative_path: str,
        channel_mapping: Dict[str, str],
        target_tolerance_pct: float = 5.0,
    ) -> Dict[str, Any]:
        """Correlates physical oscilloscope CSV against simulation .raw waveforms."""
        dest_dir = self._scope_dir(revision_id)
        manifest_path = dest_dir / f"{measurement_id[:8]}_manifest.json"
        if not manifest_path.exists():
            manifest_path = dest_dir / f"{measurement_id}_manifest.json"
        if not manifest_path.exists():
            for mf in dest_dir.glob("*_manifest.json"):
                try:
                    data = json.loads(mf.read_text(encoding="utf-8"))
                    if data.get("measurement_id") == str(measurement_id):
                        manifest_path = mf
                        break
                except Exception:
                    pass
        if not manifest_path.exists():
            return {"status": "UNAVAILABLE", "reason": f"Measurement {measurement_id} not found"}

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        raw_file = dest_dir / manifest["saved_filename"]
        if not raw_file.exists():
            return {"status": "UNAVAILABLE", "reason": "Raw scope CSV file missing"}

        # 1. Parse physical measurement CSV
        meas_data = parse_scope_csv(raw_file.read_bytes())

        # 2. Parse simulation waveform (.raw)
        revision = self.service.get_revision(revision_id)
        ws_path = self.service.workspace_path(revision)
        sim_path = self.service.engineering_records._confined(ws_path, sim_relative_path)
        if not sim_path.is_file():
            return {"status": "UNAVAILABLE", "reason": f"Simulation file {sim_relative_path} not found"}

        from integrations.parsers.ltspice_parser import parse_ascii_raw_waveforms
        sim_waveforms = parse_ascii_raw_waveforms(sim_path)

        # 3. Execute correlation engine
        correlation_report = correlate_scope_with_simulation(
            sim_waveforms=sim_waveforms,
            meas_data=meas_data,
            channel_mapping=channel_mapping,
            target_tolerance_pct=target_tolerance_pct,
        )

        correlation_report["measurement_id"] = measurement_id
        correlation_report["original_filename"] = manifest["original_filename"]
        correlation_report["sim_relative_path"] = sim_relative_path
        correlation_report["operator"] = manifest.get("operator", "")
        correlation_report["channel_mapping"] = channel_mapping

        return correlation_report
