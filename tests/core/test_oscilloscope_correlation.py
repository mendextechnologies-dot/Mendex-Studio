"""Tests for Oscilloscope CSV Ingestion and Real-vs-Simulated Waveform Correlation."""
from __future__ import annotations

import io
import json
from pathlib import Path
from uuid import uuid4

import numpy as np
import pytest

from mendex_core.desktop.service import DesktopService
from mendex_core.measurements.correlation import (
    correlate_channels,
    correlate_scope_with_simulation,
)
from mendex_core.measurements.scope_parser import (
    calculate_channel_metrics,
    clean_channel_name,
    compute_sha256,
    decimate_waveform,
    detect_scope_vendor,
    parse_scope_csv,
)
from mendex_core.service import StudioService


# --- Sample CSV Fixtures ---

TEKTRONIX_CSV_SAMPLE = """Model,TDS2024B,,
Source,CH1,,
Vertical Units,V,,
Vertical Scale,200,,
Horizontal Scale,1.0e-05,,
Sample Interval,1.0e-07,,
Trigger Point,500,,

TIME,CH1,CH2
-5.0000e-05,1000.12,24.05
-4.9900e-05,1000.25,24.10
-4.9800e-05,1000.18,24.08
-4.9700e-05,1000.30,24.12
-4.9600e-05,1000.22,24.07
-4.9500e-05,1000.28,24.11
"""

KEYSIGHT_CSV_SAMPLE = """# Model: DSOX3024T
# Serial: MY58102934
# Format: CSV
# Acquisition: Normal
x-axis,1,2
-0.00005,1000.20,24.05
-0.00004,1000.22,24.08
-0.00003,1000.19,24.06
-0.00002,1000.21,24.07
-0.00001,1000.23,24.09
0.00000,1000.25,24.11
"""

RIGOL_CSV_SAMPLE = """Sample Rate, 1.000000e+08
Time(s),CH1(V),CH2(V)
0.0000000,1000.15,24.02
0.0000001,1000.18,24.05
0.0000002,1000.22,24.08
0.0000003,1000.19,24.04
"""


def test_scope_vendor_detection():
    assert detect_scope_vendor(["Model,TDS2024B", "Sample Interval,1e-6"]) == "Tektronix"
    assert detect_scope_vendor(["# Model: DSOX3024T", "x-axis,1,2"]) == "Keysight"
    assert detect_scope_vendor(["Sample Rate, 1e8", "Rigol Technologies"]) == "Rigol"
    assert detect_scope_vendor(["Siglent Technologies", "Second,Volt"]) == "Siglent"
    assert detect_scope_vendor(["time,ch1,ch2"]) == "Generic"


def test_parse_tektronix_csv():
    parsed = parse_scope_csv(TEKTRONIX_CSV_SAMPLE)
    assert parsed["vendor"] == "Tektronix"
    assert parsed["total_points"] == 6
    assert "CH1" in parsed["channels"]
    assert "CH2" in parsed["channels"]
    assert np.isclose(parsed["channels"]["CH1"][0], 1000.12)
    assert np.isclose(parsed["channels"]["CH2"][0], 24.05)
    assert len(parsed["time"]) == 6
    assert parsed["sample_rate_hz"] > 0
    assert len(parsed["sha256"]) == 64


def test_parse_keysight_csv():
    parsed = parse_scope_csv(KEYSIGHT_CSV_SAMPLE)
    assert parsed["vendor"] == "Keysight"
    assert parsed["total_points"] == 6
    assert "CH1" in parsed["channels"] or "1" in parsed["channels"]
    assert len(parsed["time"]) == 6


def test_parse_rigol_csv():
    parsed = parse_scope_csv(RIGOL_CSV_SAMPLE)
    assert parsed["vendor"] == "Rigol"
    assert parsed["total_points"] == 4
    assert "CH1" in parsed["channels"]
    assert "CH2" in parsed["channels"]


def test_decimate_waveform_envelope_preservation():
    # Create synthetic waveform with a sharp ringing spike
    t = np.linspace(0, 1e-3, 10000)
    sig = np.sin(2 * np.pi * 1000 * t)
    # Inject 50V spike at index 5000
    sig[5000] = 50.0

    channels = {"CH1": sig}
    dec_t, dec_chans = decimate_waveform(t, channels, target_points=500)

    assert len(dec_t) <= 600
    assert "CH1" in dec_chans
    # The 50.0 V spike must be preserved by min-max decimation!
    assert np.isclose(np.max(dec_chans["CH1"]), 50.0)


def test_channel_metrics():
    t = np.linspace(0, 1e-3, 1000)
    sig = 1000.0 + 2.0 * np.sin(2 * np.pi * 50000 * t)
    metrics = calculate_channel_metrics(t, sig)

    assert np.isclose(metrics["mean"], 1000.0, atol=0.2)
    assert np.isclose(metrics["pk_pk"], 4.0, atol=0.2)
    assert metrics["est_freq_hz"] > 40000


def test_waveform_correlation_pass():
    sim_t = np.linspace(0, 1e-3, 2000)
    sim_v = 1000.0 + 1.5 * np.sin(2 * np.pi * 50000 * sim_t)

    # Measured matches simulated within 0.1% DC and similar ripple
    meas_t = np.linspace(0, 1e-3, 3000)
    meas_v = 1000.5 + 1.6 * np.sin(2 * np.pi * 50000 * meas_t)

    res = correlate_channels(
        sim_time=sim_t,
        sim_signal=sim_v,
        meas_time=meas_t,
        meas_signal=meas_v,
        channel_name="CH1 -> V(vout)",
        target_tolerance_pct=3.0,
    )

    assert res["status"] == "CORRELATED_PASS"
    assert res["dc_error_percent"] < 0.1
    assert res["r_squared"] > 0.80
    assert np.isclose(res["dc_measured"], 1000.5, atol=0.2)


def test_waveform_correlation_tolerance_exceeded():
    sim_t = np.linspace(0, 1e-3, 2000)
    sim_v = 1000.0 + 1.5 * np.sin(2 * np.pi * 50000 * sim_t)

    # Measured has 15% DC error (e.g. 850V instead of 1000V)
    meas_t = np.linspace(0, 1e-3, 3000)
    meas_v = 850.0 + 1.5 * np.sin(2 * np.pi * 50000 * meas_t)

    res = correlate_channels(
        sim_time=sim_t,
        sim_signal=sim_v,
        meas_time=meas_t,
        meas_signal=meas_v,
        channel_name="CH1 -> V(vout)",
        target_tolerance_pct=5.0,
    )

    assert res["status"] == "EXCEEDED_TOLERANCE"
    assert res["dc_error_percent"] > 10.0


def test_studio_service_oscilloscope_ingestion_and_rpc(tmp_path: Path):
    studio = StudioService(tmp_path)
    product = studio.create_product(code="TST-100", name="Scope Ingestion Test", category="dc_dc_converter", owner="Lead Hardware Engineer")
    revision = studio.get_revision(product.active_revision_id)

    # Ingest Tektronix CSV
    result = studio.ingest_oscilloscope_csv(
        revision_id=revision.revision_id,
        filename="tek_bench_capture.csv",
        content=TEKTRONIX_CSV_SAMPLE,
        channel_mapping={"CH1": "V(vout)", "CH2": "V(vin)"},
        operator="Test Engineer Alex",
        notes="Pre-compliance prototype verification",
    )

    assert result["success"] is True
    assert result["vendor"] == "Tektronix"
    assert len(result["sha256"]) == 64
    assert result["total_points"] == 6
    measurement_id = result["measurement_id"]

    # List measurements
    meas_list = studio.list_oscilloscope_measurements(revision.revision_id)
    assert len(meas_list) == 1
    assert meas_list[0]["measurement_id"] == measurement_id
    assert meas_list[0]["sha256"] == result["sha256"]

    # Get waveform
    waveform = studio.get_oscilloscope_waveform(
        revision_id=revision.revision_id,
        measurement_id=measurement_id,
    )
    assert len(waveform["samples"]) == 6
    assert waveform["traces"] == ["CH1", "CH2"]
    assert "CH1" in waveform["channel_metrics"]

    # Test via DesktopService dispatch
    desktop = DesktopService(studio)
    rpc_res = desktop.dispatch("list_oscilloscope_measurements", {"revision_id": revision.revision_id})
    assert len(rpc_res) == 1
    assert rpc_res[0]["measurement_id"] == measurement_id
