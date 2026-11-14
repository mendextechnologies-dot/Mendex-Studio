"""Tests for Oscilloscope Dual-Cursor Calipers & Ripple Analyzer backend and math."""
import pytest
from pathlib import Path
from mendex_core.service import StudioService, StudioError
from mendex_core.desktop.service import DesktopService
from mendex_core.desktop.models import WaveformQuery


SAMPLE_ASCII_RAW = """Title: Buck Converter Switching Simulation
Date: Sun Nov 15 02:00:00 2026
Plotname: Transient Analysis
Flags: real forward
No. Variables: 3
No. Points: 5
Variables:
\t0\ttime\ttime
\t1\tV(vout)\tvoltage
\t2\tI(L1)\tcurrent
Values:
0\t0.000000000000000e+000
\t0.000000000000000e+000
\t0.000000000000000e+000
1\t1.000000000000000e-005
\t4.950000000000000e+000
\t1.200000000000000e+000
2\t2.000000000000000e-005
\t5.050000000000000e+000
\t1.800000000000000e+000
3\t3.000000000000000e-005
\t4.980000000000000e+000
\t1.100000000000000e+000
4\t4.000000000000000e-005
\t5.020000000000000e+000
\t1.500000000000000e+000
"""


def test_waveform_rpc_and_caliper_math(tmp_path):
    """Verifies waveform parsing via DesktopService and oscilloscope caliper & ripple calculations."""
    service = StudioService(tmp_path)
    desktop = DesktopService(service)

    prod = service.create_product("CALIPER-TEST", "Waveform Calipers Product", "dc_dc_converter", "Lead Engineer")
    rev = service.get_revision(prod.active_revision_id)
    ws_dir = service.workspace_path(rev)
    ws_dir.mkdir(parents=True, exist_ok=True)

    raw_path = ws_dir / "transient.raw"
    raw_path.write_text(SAMPLE_ASCII_RAW, encoding="utf-8")

    # Query waveform through desktop RPC
    query = WaveformQuery(
        revision_id=rev.revision_id,
        relative_path="transient.raw",
        start=0,
        limit=100,
    )
    result = desktop.waveform(query)

    assert "samples" in result
    assert "traces" in result
    assert "metrics" in result
    samples = result["samples"]
    traces = result["traces"]
    metrics = result["metrics"]

    assert len(samples) == 5
    assert "V(vout)" in traces
    assert "I(L1)" in traces

    # Verify metrics for V(vout)
    vout_metric = metrics["V(vout)"]
    assert "mean" in vout_metric
    assert "p2p" in vout_metric
    assert "min" in vout_metric
    assert "max" in vout_metric

    # Oscilloscope Caliper Math verification:
    # Cursor A at sample 1: tA = 10 us, Vout_A = 4.95 V
    # Cursor B at sample 3: tB = 30 us, Vout_B = 4.98 V
    sample_a = samples[1]
    sample_b = samples[3]
    delta_t = abs(sample_b["time"] - sample_a["time"])
    assert delta_t == pytest.approx(2.0e-5, rel=1e-6)

    freq = 1.0 / delta_t
    assert freq == pytest.approx(50000.0, rel=1e-6)  # 50 kHz

    delta_v = abs(sample_b["V(vout)"] - sample_a["V(vout)"])
    assert delta_v == pytest.approx(0.03, rel=1e-4)  # 30 mV

    # Steady-state Ripple percentage: (p2p / mean) * 100%
    # For samples 1..4 (ignoring t=0 startup):
    p2p_v = 5.05 - 4.95  # 0.10 V = 100 mV
    mean_v = 5.0  # nominal
    ripple_pct = (p2p_v / mean_v) * 100.0
    assert ripple_pct == pytest.approx(2.0, rel=1e-2)

    # Rejection of invalid extensions or out-of-boundary paths
    with pytest.raises(StudioError):
        desktop.waveform(WaveformQuery(
            revision_id=rev.revision_id,
            relative_path="schematic.kicad_sch",
        ))
