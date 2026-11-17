"""Tests for Audit Remediation G04 (Thermal Evidence), G05 (WCCA), and G06 (Laboratory Test Plan)."""
import pytest
from mendex_core.models import Category
from mendex_core.service import StudioService
from mendex_core.design.thermal_engine import PCBThermalEngine
from mendex_core.design.wcca_engine import WCCAEngine


def test_g04_thermal_engine_on_empty_board_returns_not_evaluated(tmp_path):
    """G04: Thermal calculation on empty board returns NOT_EVALUATED and does not claim compliance."""
    service = StudioService(tmp_path)
    product = service.create_product("TH-01", "Thermal Test", Category.DC_DC, "Lead Engineer")
    rev_id = product.active_revision_id

    # Compute thermal field on blank PCB
    res = service.calculate_pcb_thermal_field(rev_id)
    assert res["overall_status"] == "NOT_EVALUATED"
    assert res["max_component"] is None
    assert res["min_thermal_margin_c"] is None
    assert res["standards_compliance"]["evaluation_status"] == "NOT_EVALUATED"
    assert res["standards_compliance"]["ipc_9592b_derated"] is False
    assert res["standards_compliance"]["navmat_derating"] is False
    assert "thermal compliance not evaluated" in res["standards_compliance"]["note"].lower()


def test_g05_wcca_engine_handles_unspecified_vout(tmp_path):
    """G05: Missing Vout target leaves overall_readiness NOT_EVALUATED."""
    service = StudioService(tmp_path)
    product = service.create_product("WCCA-01", "WCCA Test", Category.DC_DC, "Lead Engineer")
    rev_id = product.active_revision_id

    # Product revision created without vout in spec
    res = service.run_wcca_analysis(rev_id)
    assert res["overall_readiness"] == "NOT_EVALUATED"
    # Dynamic sensitivity rankings must exist and sum sensibly (~100%)
    assert len(res["sensitivities"]) > 0
    total_pct = sum(r["sensitivity_pct"] for r in res["sensitivities"])
    assert 99.0 <= total_pct <= 101.0


def test_g06_laboratory_test_plan_missing_inputs_and_authorization_disclaimer(tmp_path):
    """G06: Missing electrical inputs do not crash test plan generator, and prominent disclaimer is included."""
    service = StudioService(tmp_path)
    product = service.create_product("LAB-01", "Lab Protocol Test", Category.DC_DC, "Lead Engineer")
    rev_id = product.active_revision_id

    # Newly created product has no specified vin/vout/iout in specification
    res = service.generate_laboratory_test_plan(rev_id)
    assert res["success"] is True
    assert "authorize energization" in res["markdown_content"].lower()
    assert "authorize energization" in res["html_content"].lower()

    # Verify formatting with None inputs in nominal_ratings does not crash
    ratings = res["test_plan"]["nominal_ratings"]
    assert ratings["vout_v"] is None or ratings["vout_v"] == "NOT_SPECIFIED"
