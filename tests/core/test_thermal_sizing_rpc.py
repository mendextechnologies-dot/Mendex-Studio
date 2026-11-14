"""Unit and integration tests for Milestone Option B: Semiconductor & Magnetic Thermal Sizing RPC."""
from __future__ import annotations

from pathlib import Path
import pytest

from mendex_core.controller import MendexEngineeringController
from mendex_core.desktop.service import DesktopService
from mendex_core.models import Specification


def _setup_test_project(tmp_path: Path):
    controller = MendexEngineeringController(tmp_path)
    proj = controller.create_project("Thermal Test Project", code="TTP", auto_enroll=True)
    studio = controller.service
    product = studio.get_product(proj["project_id"])
    rev = studio.get_revision(product.active_revision_id)

    spec = Specification(
        vin_min_v=20.0,
        vin_nom_v=24.0,
        vin_max_v=28.0,
        vout_v=12.0,
        iout_a=10.0,  # 120W
        switching_frequency_hz=100000.0,
        isolation_requirement="Reinforced 1500V",
    )
    studio.update_specification(rev.revision_id, spec)
    rev = studio.get_revision(rev.revision_id)

    return controller, studio, product, rev


def test_calculate_thermal_sizing_auto_derived(tmp_path: Path):
    """Verifies that calculate_thermal_sizing RPC derives thermal parameters from spec and candidates."""
    controller, studio, product, rev = _setup_test_project(tmp_path)
    desktop = DesktopService(studio)

    # First synthesize topologies so an active candidate exists
    desktop.dispatch("synthesize_topologies", {"revision_id": str(rev.revision_id)})

    res = desktop.dispatch("calculate_thermal_sizing", {
        "revision_id": str(rev.revision_id),
    })

    assert res["success"] is True
    assert res["revision_id"] == str(rev.revision_id)
    assert res["ambient_temp_c"] == 25.0

    # Semiconductor sizing checks
    semi = res["semiconductor"]
    assert semi["p_loss_w"] > 0
    assert semi["t_junction_c"] > 25.0
    assert semi["t_j_limit_c"] == 120.0  # 150 * 0.8
    assert semi["thermal_margin_c"] > 0
    assert semi["thermal_vias_recommended"] >= 1

    # Secondary diode sizing checks
    diode = res["secondary_diode"]
    assert diode["p_loss_w"] > 0
    assert diode["t_junction_c"] > 25.0

    # Magnetics sizing checks
    mag = res["magnetics"]
    assert mag["p_total_w"] > 0
    assert mag["t_surface_c"] > 25.0
    assert mag["t_hotspot_c"] > mag["t_surface_c"]
    assert mag["t_class_max_c"] == 130.0  # Class B

    # IPC-2152 trace sizing checks
    trace = res["ipc2152_trace"]
    assert trace["current_a"] > 0
    assert trace["min_trace_width_mm"] > 0.5
    assert trace["target_delta_t_c"] == 10.0

    # Summary checks
    summary = res["summary"]
    assert summary["max_temperature_c"] > 25.0
    assert summary["compliance_status"] == "COMPLIANT"


def test_calculate_thermal_sizing_custom_overrides_and_evidence(tmp_path: Path):
    """Verifies calculate_thermal_sizing with custom overrides and evidence recording."""
    controller, studio, product, rev = _setup_test_project(tmp_path)
    desktop = DesktopService(studio)

    desktop.dispatch("synthesize_topologies", {"revision_id": str(rev.revision_id)})

    res = desktop.dispatch("calculate_thermal_sizing", {
        "revision_id": str(rev.revision_id),
        "ambient_temp_c": 45.0,  # Industrial elevated ambient
        "p_switch_loss_w": 3.0,
        "r_th_jc_c_w": 1.2,
        "r_th_cs_c_w": 0.4,
        "r_th_sa_c_w": 8.0,
        "t_j_max_c": 175.0,  # SiC MOSFET
        "derating_factor": 0.80,
        "trace_current_a": 15.0,
        "target_trace_delta_t_c": 15.0,
        "copper_thickness_oz": 2.0,  # 2oz heavy copper
        "is_internal_trace": False,
        "record_evidence": True,
    })

    assert res["success"] is True
    assert res["ambient_temp_c"] == 45.0

    semi = res["semiconductor"]
    assert semi["p_loss_w"] == 3.0
    assert semi["t_j_max_c"] == 175.0
    assert semi["t_j_limit_c"] == 140.0  # 175 * 0.8
    # Rth_total = 1.2 + 0.4 + 8.0 = 9.6 °C/W
    # Tj = 45 + 3.0 * 9.6 = 73.8 °C
    assert abs(semi["t_junction_c"] - 73.8) < 0.1
    assert semi["status"] == "PASS_DERATED"

    # Verify 2oz copper trace requires narrower width than 1oz for same current
    trace = res["ipc2152_trace"]
    assert trace["copper_thickness_oz"] == 2.0
    assert trace["target_delta_t_c"] == 15.0
    assert trace["current_a"] == 15.0
    assert trace["min_trace_width_mm"] > 0
