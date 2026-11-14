"""Tests for High-Voltage Laboratory Test Plan & Staged Bring-Up Protocol Generator (Option 2 / G16, G17, G23)."""
from pathlib import Path
import json
import pytest

from mendex_core.service import StudioService
from mendex_core.design.test_plan_generator import generate_laboratory_test_plan, get_laboratory_test_plan


@pytest.fixture
def repo_studio():
    return StudioService(Path("."))


def test_laboratory_test_plan_generation_emc_100(repo_studio):
    """Verifies test plan protocol generation for EMC-100 reference card."""
    products = {p.code: p for p in repo_studio.list_products()}
    assert "EMC-100" in products
    emc = products["EMC-100"]
    rev = repo_studio.get_revision(emc.active_revision_id)

    res = repo_studio.generate_laboratory_test_plan(rev.revision_id)
    assert res["success"] is True
    assert res["protocol_id"] == f"LTP-EMC-100-{rev.revision_label}"
    assert "CAT III" in res["safety_category"]
    assert res["is_high_voltage"] is True
    assert len(res["sha256"]) == 64

    # Verify JSON, Markdown, and HTML files exist on disk
    ws = repo_studio.workspace_path(rev)
    assert (ws / res["json_path"]).is_file()
    assert (ws / res["markdown_path"]).is_file()
    assert (ws / res["html_path"]).is_file()

    # Verify 4-phase bring up structure
    plan = res["test_plan"]
    assert len(plan["phases"]) == 4
    assert plan["phases"][0]["title"].startswith("Cold Inspection")
    assert plan["phases"][1]["title"].startswith("Auxiliary Low-Voltage")
    assert plan["phases"][2]["title"].startswith("Staged High-Voltage Ramp")
    assert plan["phases"][3]["title"].startswith("Full-Load Operating")

    # Verify oscilloscope probe points
    assert len(plan["test_points"]) == 4
    channels = [tp["channel"] for tp in plan["test_points"]]
    assert any("CH1" in c for c in channels)
    assert any("CH2" in c for c in channels)
    assert any("CH3" in c for c in channels)
    assert any("CH4" in c for c in channels)

    # Verify abort criteria and scorecard template
    assert len(plan["abort_criteria"]) >= 4
    assert plan["scorecard_template"]["overall_result"] == "PENDING_PHYSICAL_EXECUTION"


def test_laboratory_test_plan_generation_sv_1000(repo_studio):
    """Verifies test plan protocol generation for SV-1000 extreme high voltage converter."""
    products = {p.code: p for p in repo_studio.list_products()}
    assert "SV-1000" in products
    sv = products["SV-1000"]
    rev = repo_studio.get_revision(sv.active_revision_id)

    res = repo_studio.generate_laboratory_test_plan(rev.revision_id)
    assert res["success"] is True
    assert res["protocol_id"] == f"LTP-SV-1000-{rev.revision_label}"
    assert "Extreme High Voltage" in res["safety_category"]
    assert res["is_high_voltage"] is True

    # Check cached retrieval
    cached = repo_studio.get_laboratory_test_plan(rev.revision_id)
    assert cached["protocol_id"] == res["protocol_id"]
    assert cached["sha256"] == res["sha256"]
