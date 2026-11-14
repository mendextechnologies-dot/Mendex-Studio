"""
Tests for P1-3 audit remediation:
- Waveform endpoint parsing real LTspice .raw files (binary and ASCII)
- Vector downsampling and statistical metrics (RMS, peak-to-peak ripple, mean, bounds)
- Revision simulation jobs visibility and measurements exposure in Studio DesktopService
"""
from pathlib import Path
import pytest
from mendex_core.service import StudioService, StudioError
from mendex_core.desktop.service import DesktopService
from mendex_core.desktop.models import ProjectQuery, WaveformQuery


@pytest.fixture
def desktop_service():
    # Use repo root where SV-1000 product and raw simulation files are located
    studio = StudioService(Path("."))
    return DesktopService(studio)


def test_waveform_endpoint_parses_real_raw_file(desktop_service):
    # SpectraVolt SV-1000 revision 1
    rev_id = "9b7c1396-64da-41f8-8649-77dc0f24e103"
    raw_rel = "simulations/flyback_circuit.raw"

    res = desktop_service.waveform(WaveformQuery(
        revision_id=rev_id,
        relative_path=raw_rel,
    ))

    assert "samples" in res
    assert "traces" in res
    assert "total_points" in res
    assert "metrics" in res

    samples = res["samples"]
    traces = res["traces"]
    total_pts = res["total_points"]
    metrics = res["metrics"]

    # Verify high-resolution points and downsampled vectors
    assert total_pts == 26038
    assert len(samples) > 100  # Downsampled to ~1000 points
    assert "time" in samples[0]

    # Verify physical traces
    expected_traces = {"V(gate)", "V(in)", "V(pri_drain)", "V(vout)", "I(D1)"}
    assert expected_traces.issubset(set(traces))

    # Verify output voltage metrics
    vout_metric = metrics["V(vout)"]
    assert 995.0 <= vout_metric["mean"] <= 1005.0  # 1000V target
    assert vout_metric["p2p"] < 1.0  # Low ripple (< 1V)

    # Verify input voltage
    vin_metric = metrics["V(in)"]
    assert abs(vin_metric["mean"] - 24.0) < 0.1  # 24V input steady state

    # Verify drain voltage peak
    pri_vds = metrics["V(pri_drain)"]
    assert pri_vds["max"] < 100.0  # Well within 900V SiC rating


def test_waveform_endpoint_rejects_non_raw_file(desktop_service):
    rev_id = "9b7c1396-64da-41f8-8649-77dc0f24e103"
    with pytest.raises(StudioError) as exc_info:
        desktop_service.waveform(WaveformQuery(
            revision_id=rev_id,
            relative_path="simulations/flyback_circuit.net",
        ))
    assert exc_info.value.code == "UNSUPPORTED"


def test_simulations_and_measurements_visible_in_project_detail(desktop_service):
    prod_id = "8f697275-3a8d-456c-ae20-138a7698df61"
    rev_id = "9b7c1396-64da-41f8-8649-77dc0f24e103"

    proj = desktop_service.project(ProjectQuery(
        project_id=prod_id,
        revision_id=rev_id,
    ))

    # Verify simulation jobs are visible and attributed
    sims = proj.get("simulations", [])
    assert len(sims) >= 2
    tool_ids = {s["tool_id"] for s in sims}
    assert "ltspice" in tool_ids
    assert "femm" in tool_ids
    assert all(s["status"] == "SUCCEEDED" for s in sims)

    # Verify measurements are exposed
    meas = proj.get("measurements", [])
    assert len(meas) >= 5
    params = {m["parameter"]: m["value"] for m in meas}

    # Verify LTspice .meas parameters
    assert "vout_avg" in params
    assert 995.0 <= params["vout_avg"] <= 1005.0
    assert "vout_ripple" in params
    assert params["vout_ripple"] < 0.1  # 0.0095% ripple
    assert "pri_vds_pk" in params
    assert params["pri_vds_pk"] < 100.0

    # Verify FEMM 2D magnetics parameters
    assert "Bpk_center_leg_T" in params
    assert params["Bpk_center_leg_T"] < 0.35  # Linear region
    assert "Bmax_core_T" in params
    assert params["Bmax_core_T"] < 0.35


def test_global_simulation_center_lists_jobs(desktop_service):
    jobs = desktop_service.simulations()
    assert len(jobs) >= 2
    tools = {j["tool_id"] for j in jobs}
    assert "ltspice" in tools
    assert "femm" in tools
    assert all(j["project_name"] == "SpectraVolt SV-1000" for j in jobs)
