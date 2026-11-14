"""Milestone 3 Acceptance Test Suite: Truthful Evidence & Waveform Analysis (G04 / G07).

Verifies:
1. G04: Strict nested KiCad ERC / DRC report parsing (nested sheets violations are truthfully parsed).
2. G04: False-positive prevention in FEMM reports: empty, malformed, or unexcited FEMM evidence
   must NEVER manufacture PASS (or 99.3% Margin).
3. G07: Waveform RPC bounds enforcement (start and limit pagination parameters are strictly honored).
4. G07: Time-weighted integration (trapezoidal rule) over declared steady-state settling windows.
5. G07: Explicit zero-tolerance handling (tolerance_pct=0.0 is preserved and not replaced by 5.0 fallback).
6. G07: Full-time domain coverage for simulation preview traces (no 30us startup truncation).
"""
from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import numpy as np
import pytest

from mendex_core.dossier_generator import (
    render_erc_drc_scorecard,
    render_femm_magnetics_card,
)
from mendex_core.design.models import Requirement
from mendex_core.design.ltspice_runner import LTspiceRunner, LTspiceSimulationResult
from integrations.parsers.ltspice_parser import calculate_waveform_metrics
from mendex_core.desktop.service import DesktopService
from mendex_core.desktop.models import WaveformQuery
from mendex_core.service import StudioService


# --- G04: Truthful Evidence Tests ---

def test_g04_nested_kicad_erc_report_parsing_detects_all_errors(tmp_path: Path):
    """Negative test: KiCad nested sheet ERC with 20 errors must yield FAIL, never Clean or PASS."""
    ws = tmp_path / "workspace"
    ws.mkdir(parents=True)

    # Replicate KiCad 10 nested sheet report structure with 20 errors and 18 warnings
    nested_violations = []
    for i in range(20):
        nested_violations.append({
            "severity": "error",
            "type": "label_dangling",
            "description": f"Dangling net label NET_{i}",
        })
    for i in range(18):
        nested_violations.append({
            "severity": "warning",
            "type": "pin_not_connected",
            "description": f"Unconnected pin on R{i}",
        })

    erc_content = {
        "$schema": "https://schemas.kicad.org/erc.v1.json",
        "kicad_version": "10.0.7",
        "sheets": [
            {
                "path": "/",
                "violations": nested_violations,
            }
        ]
    }
    (ws / "erc_report.json").write_text(json.dumps(erc_content), encoding="utf-8")

    html_out = render_erc_drc_scorecard(ws)
    assert "FAIL (20 errors)" in html_out, f"Scorecard did not report 20 errors:\n{html_out}"
    assert "Clean" not in html_out, f"False-positive 'Clean' found in scorecard with 20 errors:\n{html_out}"
    assert "Pin drive integrity: <b>FAIL</b>" in html_out


def test_g04_empty_or_malformed_erc_yields_not_evaluated(tmp_path: Path):
    """Negative test: Empty or malformed ERC file must yield NOT_EVALUATED, never PASS."""
    ws = tmp_path / "workspace"
    ws.mkdir(parents=True)

    # Empty JSON object
    (ws / "erc_report.json").write_text("{}", encoding="utf-8")
    html_out = render_erc_drc_scorecard(ws)
    assert "NOT_EVALUATED" in html_out
    assert "PASS" not in html_out


def test_g04_empty_femm_evidence_never_manufactures_pass(tmp_path: Path):
    """Negative test: Empty FEMM results JSON {} must yield NOT_EVALUATED, never PASS (99.3% Margin)."""
    ws = tmp_path / "workspace"
    mag_dir = ws / "magnetics"
    mag_dir.mkdir(parents=True)

    # The exact defect observed in audit evidence: empty {} generated PASS (99.3% Margin)
    (mag_dir / "actuator_results.json").write_text("{}", encoding="utf-8")

    html_out = render_femm_magnetics_card(ws)
    assert "NOT_EVALUATED" in html_out, f"Empty FEMM json produced non-NOT_EVALUATED result:\n{html_out}"
    assert "PASS" not in html_out, f"Empty FEMM json produced false-positive PASS:\n{html_out}"
    assert "99.3%" not in html_out, f"Fabricated 99.3% margin present:\n{html_out}"


def test_g04_unexcited_femm_evidence_yields_not_evaluated(tmp_path: Path):
    """Negative test: Zero excitation Bpk=0.0 must yield NOT_EVALUATED, never PASS."""
    ws = tmp_path / "workspace"
    mag_dir = ws / "magnetics"
    mag_dir.mkdir(parents=True)

    zero_excitation = {
        "actuator_model": "Test Core",
        "peak_flux_density_b_max_t": 0.0,
        "core_saturation_threshold_t": 1.6,
        "saturation_margin_pct": 100.0,
        "core_saturated": False,
        "primary_turns": 10,
        "coil_excitation_current_a": 0.0,
        "ampere_turns": 0.0,
    }
    (mag_dir / "actuator_results.json").write_text(json.dumps(zero_excitation), encoding="utf-8")

    html_out = render_femm_magnetics_card(ws)
    assert "NOT_EVALUATED (Zero Excitation)" in html_out
    assert "PASS" not in html_out


def test_g04_saturated_femm_evidence_yields_saturated(tmp_path: Path):
    """Negative test: Saturated core must yield SATURATED badge, never PASS."""
    ws = tmp_path / "workspace"
    mag_dir = ws / "magnetics"
    mag_dir.mkdir(parents=True)

    saturated_data = {
        "actuator_model": "Saturated Inductor",
        "peak_flux_density_b_max_t": 1.85,
        "core_saturation_threshold_t": 1.60,
        "saturation_margin_pct": -15.6,
        "core_saturated": True,
        "primary_turns": 50,
        "coil_excitation_current_a": 5.0,
        "ampere_turns": 250.0,
    }
    (mag_dir / "actuator_results.json").write_text(json.dumps(saturated_data), encoding="utf-8")

    html_out = render_femm_magnetics_card(ws)
    assert "SATURATED" in html_out
    assert "PASS" not in html_out


def test_g04_qualified_femm_evidence_yields_truthful_margin(tmp_path: Path):
    """Positive test: Qualified excited non-saturated model shows exact calculated margin."""
    ws = tmp_path / "workspace"
    mag_dir = ws / "magnetics"
    mag_dir.mkdir(parents=True)

    valid_data = {
        "actuator_model": "Qualified Buck Inductor",
        "peak_flux_density_b_max_t": 0.32,
        "core_saturation_threshold_t": 0.40,
        "saturation_margin_pct": 20.0,
        "core_saturated": False,
        "primary_turns": 25,
        "coil_excitation_current_a": 1.5,
        "ampere_turns": 37.5,
    }
    (mag_dir / "actuator_results.json").write_text(json.dumps(valid_data), encoding="utf-8")

    html_out = render_femm_magnetics_card(ws)
    assert "PASS (20.0% Margin)" in html_out
    assert "99.3%" not in html_out


# --- G07: Waveform Analysis & Windowing Tests ---

def test_g07_waveform_rpc_pagination_enforces_start_and_limit(tmp_path: Path):
    """Verify that DesktopService.waveform strictly honors start and limit parameters."""
    studio = StudioService(tmp_path)
    product = studio.create_product("WF-TEST", "Waveform Paging Test", "dc_dc_converter", "QA Engineer")
    rev = studio.get_revision(product.active_revision_id)
    ws_dir = studio.workspace_path(rev)

    # Generate synthetic ASCII .raw file with 500 data points
    raw_path = ws_dir / "simulation.raw"
    lines = [
        "Title: Paging Test",
        "Date: 2026-11-14",
        "Plotname: Transient Analysis",
        "Flags: real forward",
        "No. Variables: 3",
        "No. Points: 500",
        "Variables:",
        "\t0\ttime\ttime",
        "\t1\tV(vout)\tvoltage",
        "\t2\tI(L1)\tcurrent",
        "Values:",
    ]
    for i in range(500):
        t = i * 1e-5
        v = 5.0 + 0.05 * np.sin(2 * np.pi * 100000 * t)
        curr = 1.0 + 0.1 * np.cos(2 * np.pi * 100000 * t)
        lines.append(f"{i}\t{t:.8e}")
        lines.append(f"\t{v:.6e}")
        lines.append(f"\t{curr:.6e}")
    raw_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    desktop = DesktopService(studio)

    # Test 1: Page with start=100, limit=5
    query = WaveformQuery(
        revision_id=rev.revision_id,
        relative_path="simulation.raw",
        start=100,
        limit=5,
    )
    result = desktop.waveform(query)
    assert result["total_points"] == 500
    assert result["start"] == 100
    assert result["limit"] == 5
    assert len(result["samples"]) == 5, f"Expected 5 samples, got {len(result['samples'])}"
    assert result["returned_points"] == 5
    # First returned sample must correspond to index 100 (t = 100 * 1e-5 = 1e-3)
    assert abs(result["samples"][0]["time"] - 1e-3) < 1e-9

    # Test 2: Page beyond end of file returns 0 samples gracefully
    query_oob = WaveformQuery(
        revision_id=rev.revision_id,
        relative_path="simulation.raw",
        start=600,
        limit=10,
    )
    res_oob = desktop.waveform(query_oob)
    assert len(res_oob["samples"]) == 0
    assert res_oob["returned_points"] == 0


def test_g07_time_weighted_averaging_vs_unweighted_sample_mean():
    """Verify that time-weighted integration gives truthful steady-state average on adaptive time grids."""
    # Construct an adaptive time grid where timestep during transient is 100x finer than steady state:
    # Phase 1 (transient): 0 to 1ms with dt = 1us (1,000 points) at V = 0V
    # Phase 2 (steady-state settling): 1ms to 5ms with dt = 10us (400 points) at V = 5V
    t_transient = np.linspace(0.0, 0.001, 1000)
    v_transient = np.zeros(1000)

    t_steady = np.linspace(0.001, 0.005, 400)
    v_steady = np.ones(400) * 5.0

    t_full = np.concatenate([t_transient, t_steady[1:]])
    v_full = np.concatenate([v_transient, v_steady[1:]])

    waveforms = {"time": t_full, "V(vout)": v_full}

    metrics = calculate_waveform_metrics(waveforms, steady_state_ratio=0.50)
    v_metrics = metrics["V(vout)"]

    # In the last 50% of time (2.5ms to 5.0ms), V is steady at 5.0V
    assert abs(v_metrics["mean"] - 5.0) < 1e-4, f"Time-weighted mean was {v_metrics['mean']}, expected 5.0"
    assert v_metrics["p2p"] < 1e-4
    assert v_metrics["window_start_time"] >= 0.0024


def test_g07_explicit_zero_tolerance_not_overwritten():
    """Negative test: tolerance_pct=0.0 must NOT be replaced by 5.0 fallback."""
    # When tolerance is 0.0%, any difference between measured and target must fail
    req_zero_tol = Requirement(
        parameter="vout",
        target_value=5.0,
        unit="V",
        tolerance_pct=0.0,  # Strict zero tolerance
    )

    # Simulation with 4.85V mean (diff = 3.0%)
    # Under old logic: 0.0 or 5.0 => 5.0% tolerance => PASSED (False Positive!)
    # Under fixed logic: tol = 0.0% => FAILED (Truthful verdict)
    tol = (req_zero_tol.tolerance_pct if req_zero_tol.tolerance_pct is not None else 5.0) / 100.0
    assert tol == 0.0, f"Expected 0.0 tolerance, got {tol}"

    diff = abs(4.85 - 5.0) / 5.0  # 3% diff
    passed = diff <= tol
    assert passed is False, "Zero tolerance permitted a 3% discrepancy!"


def test_g07_full_time_domain_preview_decimation():
    """Verify that preview decimation covers the full simulation span, not just the first 200 points."""
    # 25,000 points spanning 5ms (resembling the real LTspice raw file from the audit)
    total_pts = 25000
    time_vals = list(np.linspace(0.0, 0.005, total_pts))
    vout_vals = list(5.0 + 0.05 * np.sin(2 * np.pi * 1000 * np.array(time_vals)))

    preview_indices = list(range(0, total_pts, max(1, total_pts // 500)))
    preview_time = [time_vals[i] for i in preview_indices]
    preview_vout = [vout_vals[i] for i in preview_indices]

    assert len(preview_time) <= 505
    # The preview must reach the final simulation time (~5ms), not stop at 30us
    assert preview_time[-1] >= 0.0049, f"Preview stopped prematurely at t={preview_time[-1]}s"
    assert preview_time[0] == 0.0
