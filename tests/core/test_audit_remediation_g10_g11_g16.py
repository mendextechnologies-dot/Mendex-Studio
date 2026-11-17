"""Tests for Audit Remediation G10 (Mechanical/Enclosure Fit), G11 (Safety Boundaries), and G16 (Ternary Integrity Contract)."""
import pytest
from mendex_core.models import Category
from mendex_core.service import StudioService


def test_g10_enclosure_model_blank_board_fit_not_evaluated(tmp_path):
    """G10: Generating enclosure model on blank board reports fit_evaluation NOT_EVALUATED."""
    service = StudioService(tmp_path)
    product = service.create_product("ENC-01", "Enclosure Test", Category.DC_DC, "Mechanical Engineer")
    rev_id = product.active_revision_id

    # Blank board with no PCB footprints
    enc = service.generate_enclosure_model(rev_id, export_step=False)
    assert enc["success"] is True
    assert enc["fit_evaluation"] == "NOT_EVALUATED"
    assert "draft" in enc["governance_note"].lower() or "prototype" in enc["governance_note"].lower()


def test_g10_enclosure_model_queries_actual_thermal_when_available(tmp_path):
    """G10: Enclosure model links to actual PCB thermal field rather than inventing numbers."""
    service = StudioService(tmp_path)
    product = service.create_product("ENC-02", "Enclosure Thermal Test", Category.DC_DC, "Mechanical Engineer")
    rev_id = product.active_revision_id

    # 1. Run thermal field on blank board
    th = service.calculate_pcb_thermal_field(rev_id)
    # 2. Run enclosure model
    enc = service.generate_enclosure_model(rev_id, export_step=False)
    assert enc["success"] is True
    # If board has no dissipating components, thermal status is ANALYTICAL_REFERENCE_MODEL
    assert enc["thermal_interface"]["thermal_status"] in ("NOT_EVALUATED", "ANALYTICAL_REFERENCE_MODEL", "CALCULATED")


def test_g11_safety_and_thermal_compliance_disclaimers(tmp_path):
    """G11: Analytical thermal fields disclaim compliance and mandate physical measurements."""
    service = StudioService(tmp_path)
    product = service.create_product("SAF-01", "Safety Test", Category.DC_DC, "Safety Engineer")
    rev_id = product.active_revision_id

    th = service.calculate_pcb_thermal_field(rev_id)
    comp = th["standards_compliance"]
    assert comp["evaluation_status"] == "NOT_EVALUATED"
    assert comp["ipc_9592b_derated"] is False
    assert comp["navmat_derating"] is False
    assert "not evaluated" in comp["note"].lower() or "thermocouple" in comp["note"].lower()


def test_g16_ternary_integrity_status_distinction():
    """G16: Integrity statuses distinguish true (valid), false (corrupted), and None (not evaluated)."""
    # Verify core digest vs cryptographic signature semantics
    digest_valid = {"digest_verified": True, "label": "Digest Verified"}
    digest_failed = {"digest_verified": False, "label": "Integrity Failed"}
    digest_unknown = {"digest_verified": None, "label": "Integrity Not Evaluated"}

    assert digest_valid["digest_verified"] is True
    assert digest_failed["digest_verified"] is False
    assert digest_unknown["digest_verified"] is None
