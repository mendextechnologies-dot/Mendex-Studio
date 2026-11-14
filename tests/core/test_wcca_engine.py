"""Unit & Integration Tests for Worst-Case & Monte Carlo Tolerance Analysis (WCCA) Engine."""
from __future__ import annotations

from pathlib import Path
from uuid import uuid4
import pytest
import numpy as np

from mendex_core.service import StudioService
from mendex_core.desktop.service import DesktopService
from mendex_core.design.wcca_engine import WCCAEngine


def test_wcca_engine_statistical_computation(tmp_path: Path):
    engine = WCCAEngine(tmp_path)
    spec = {
        "product_id": str(uuid4()),
        "vout_v": 1000.0,
        "vin_nom_v": 24.0,
        "vin_min_v": 20.4,
        "vin_max_v": 27.6,
        "pout_w": 50.0,
        "switching_frequency_hz": 100000.0,
        "vout_ripple_max_mv": 500.0,
    }

    res = engine.run_analysis(
        revision_id=uuid4(),
        specification=spec,
        num_iterations=50,
        distribution="gaussian",
        seed=42,
    )

    assert res["success"] is True
    assert res["num_iterations"] == 50
    assert "statistics" in res
    stats = res["statistics"]
    assert np.isclose(stats["mean_v"], 1000.0, atol=15.0)
    assert stats["std_dev_v"] > 0
    assert stats["cpk"] > 0
    assert stats["statistical_yield_percent"] >= 95.0
    assert len(res["histogram_bins"]) == 10
    assert len(res["eva_corners"]) == 4
    assert len(res["sensitivities"]) >= 4
    assert len(res["monte_carlo_runs"]) == 30


def test_wcca_eva_corners():
    engine = WCCAEngine(Path("."))
    spec = {
        "vout_v": 1000.0,
        "vin_nom_v": 24.0,
        "pout_w": 50.0,
    }
    res = engine.run_analysis(revision_id=uuid4(), specification=spec, num_iterations=20)
    corners = {c["corner_name"]: c for c in res["eva_corners"]}

    assert "Cold Min Line (Worst Undershoot)" in corners
    assert "Hot Max Line (Worst Overshoot)" in corners
    assert "Maximum Switch Stress Corner" in corners
    assert "Maximum Ripple Corner" in corners

    # Cold undershoot should be below Hot overshoot
    assert corners["Cold Min Line (Worst Undershoot)"]["vout_v"] < corners["Hot Max Line (Worst Overshoot)"]["vout_v"]


def test_wcca_studio_and_desktop_rpc(tmp_path: Path):
    studio = StudioService(tmp_path)
    product = studio.create_product(code="WCCA-01", name="WCCA Test", category="dc_dc_converter", owner="Test Lead")
    revision = studio.get_revision(product.active_revision_id)

    # Run WCCA via StudioService
    report = studio.run_wcca_analysis(
        revision_id=revision.revision_id,
        num_iterations=40,
        distribution="gaussian",
    )
    assert report["success"] is True
    assert report["num_iterations"] == 40
    assert "overall_readiness" in report

    # Fetch report via get_wcca_analysis
    fetched = studio.get_wcca_analysis(revision.revision_id)
    assert fetched["success"] is True
    assert fetched["num_iterations"] == 40

    # Test via DesktopService dispatch
    desktop = DesktopService(studio)
    rpc_res = desktop.dispatch("get_wcca_analysis", {"revision_id": revision.revision_id})
    assert rpc_res["success"] is True
    assert rpc_res["statistics"]["mean_v"] > 0
