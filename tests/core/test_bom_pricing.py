"""Tests for Production BOM Cost Rollup & Purchasing Intelligence (Option 3 / G05)."""
from pathlib import Path
import json
import pytest

from mendex_core.service import StudioService
from mendex_core.design.bom_pricing import generate_bom_pricing_schedule, get_bom_pricing_schedule


@pytest.fixture
def repo_studio():
    return StudioService(Path("."))


def test_bom_pricing_schedule_emc_100(repo_studio):
    """Verifies volume cost rollup and purchasing intelligence for EMC-100."""
    products = {p.code: p for p in repo_studio.list_products()}
    assert "EMC-100" in products
    emc = products["EMC-100"]
    rev = repo_studio.get_revision(emc.active_revision_id)

    res = repo_studio.generate_bom_pricing_schedule(rev.revision_id, currency="USD")
    assert res["success"] is True
    assert res["product_code"] == "EMC-100"
    assert res["total_line_items"] == 30
    assert res["currency"] == "USD"

    s = res["summary"]
    assert s["board_cost_1"] > s["board_cost_25"] > s["board_cost_100"] > s["board_cost_1000"]
    assert s["volume_savings_pct"] > 40.0  # Significant volume discount
    assert s["batch_cost_1000"] == round(s["board_cost_1000"] * 1000, 2)

    # Pareto cost drivers
    assert len(res["top_cost_drivers"]) > 0
    top = res["top_cost_drivers"][0]
    assert top["rank"] == 1
    assert "share_pct" in top
    assert top["cumulative_share_pct"] > 0

    # Category breakdown
    assert len(res["category_breakdown"]) >= 3
    cats = [c["category"] for c in res["category_breakdown"]]
    assert "Power Semiconductors" in cats or "Capacitors" in cats

    # Check generated files
    ws = repo_studio.workspace_path(rev)
    assert (ws / res["csv_path"]).is_file()
    assert (ws / res["json_path"]).is_file()
    assert (ws / res["markdown_path"]).is_file()
    assert (ws / res["html_path"]).is_file()

    # Integrity & disclaimer
    assert len(res["sha256"]) == 64
    assert "NOT_EVALUATED" in res["disclaimer"]


def test_bom_pricing_schedule_sv_1000(repo_studio):
    """Verifies volume cost rollup and Pareto ranking for SV-1000."""
    products = {p.code: p for p in repo_studio.list_products()}
    assert "SV-1000" in products
    sv = products["SV-1000"]
    rev = repo_studio.get_revision(sv.active_revision_id)

    res = repo_studio.generate_bom_pricing_schedule(rev.revision_id, currency="USD")
    assert res["success"] is True
    assert res["product_code"] == "SV-1000"
    assert res["total_line_items"] == 32

    # Sourced components must have active lifecycle and distributors
    for itm in res["items"][:5]:
        assert itm["lifecycle"] == "ACTIVE"
        assert itm["distributor"] != ""
        assert itm["lead_time_weeks"] != ""
        t = itm["pricing_tiers"]
        assert t["tier_1"]["unit_price"] >= t["tier_1000"]["unit_price"]

    # Retrieval via get_bom_pricing_schedule
    cached = repo_studio.get_bom_pricing_schedule(rev.revision_id)
    assert cached["product_code"] == "SV-1000"
    assert cached["total_line_items"] == 32
