"""Tests for Audit Remediation G03 (Immutability and Read-Only Getters)."""
import pytest
from mendex_core.models import Category
from mendex_core.service import StudioError, StudioService


def test_g03_getters_are_strictly_read_only(tmp_path):
    """G03: Getters must be pure read-only queries and return NOT_EVALUATED / PENDING without mutating data."""
    service = StudioService(tmp_path)
    product = service.create_product("IMM-01", "Immutability Test", Category.DC_DC, "Lead Engineer")
    rev_id = product.active_revision_id

    # 1. WCCA getter
    wcca = service.get_wcca_analysis(rev_id)
    assert wcca["status"] == "NOT_EVALUATED" or wcca.get("overall_readiness") == "NOT_EVALUATED"

    # 2. PCB thermal getter
    thermal = service.get_pcb_thermal_field(rev_id)
    assert thermal["status"] == "NOT_EVALUATED" or thermal.get("overall_status") == "NOT_EVALUATED"

    # 3. Enclosure model getter
    enclosure = service.get_enclosure_model(rev_id)
    assert enclosure["status"] == "NOT_EVALUATED" or enclosure.get("fit_evaluation") == "NOT_EVALUATED"

    # 4. Laboratory test plan getter
    test_plan = service.get_laboratory_test_plan(rev_id)
    assert test_plan["status"] == "NOT_EVALUATED"

    # 5. BOM pricing schedule getter
    bom_pricing = service.get_bom_pricing_schedule(rev_id)
    assert bom_pricing["status"] == "NOT_EVALUATED"

    # 6. Release package getter
    rel_pkg = service.get_release_package(rev_id)
    assert rel_pkg["status"] == "PENDING_GENERATION"
    assert rel_pkg["package_exists"] is False


def test_g03_mutations_blocked_on_frozen_baselines(tmp_path):
    """G03: Mutating calculations, test plans, BOM pricing, or packages on non-draft baselines is blocked."""
    service = StudioService(tmp_path)
    product = service.create_product("IMM-02", "Frozen Baseline", Category.DC_DC, "Lead Engineer")
    rev_id = product.active_revision_id

    # Move revision from draft to in_review
    service.set_revision_status(rev_id, "in_review")

    # 1. run_wcca_analysis must fail
    with pytest.raises(StudioError) as exc1:
        service.run_wcca_analysis(rev_id)
    assert exc1.value.code == "IMMUTABLE"

    # 2. calculate_pcb_thermal_field must fail
    with pytest.raises(StudioError) as exc2:
        service.calculate_pcb_thermal_field(rev_id)
    assert exc2.value.code == "IMMUTABLE"

    # 3. generate_enclosure_model must fail
    with pytest.raises(StudioError) as exc3:
        service.generate_enclosure_model(rev_id)
    assert exc3.value.code == "IMMUTABLE"

    # 4. generate_laboratory_test_plan must fail
    with pytest.raises(StudioError) as exc4:
        service.generate_laboratory_test_plan(rev_id)
    assert exc4.value.code == "IMMUTABLE"

    # 5. generate_bom_pricing_schedule must fail
    with pytest.raises(StudioError) as exc5:
        service.generate_bom_pricing_schedule(rev_id)
    assert exc5.value.code == "IMMUTABLE"

    # 6. generate_release_package must fail
    with pytest.raises(StudioError) as exc6:
        service.generate_release_package(rev_id)
    assert exc6.value.code == "IMMUTABLE"
