"""Tests for 2D PCB Thermal Heatmap and Electro-Thermal Loss Diffusion Engine."""
from __future__ import annotations

from pathlib import Path
from uuid import uuid4
import pytest

from mendex_core.service import StudioService
from mendex_core.desktop.service import DesktopService
from mendex_core.design.thermal_engine import PCBThermalEngine


def test_pcb_thermal_engine_calculations(tmp_path: Path):
    engine = PCBThermalEngine(tmp_path)
    spec = {
        "product_id": str(uuid4()),
        "pout_w": 50.0,
        "vout_v": 1000.0,
        "vin_nom_v": 24.0,
        "switching_frequency_hz": 100000.0,
    }
    footprints = [
        {"ref": "Q1", "value": "SiC MOSFET", "name": "TO-252", "x": 135.0, "y": 140.0},
        {"ref": "T1", "value": "ETD34 Transformer", "name": "ETD34", "x": 108.0, "y": 140.0},
        {"ref": "D1", "value": "SiC Diode", "name": "SMA", "x": 166.0, "y": 133.0},
    ]
    bbox = {"min_x": 92.0, "min_y": 92.0, "max_x": 193.0, "max_y": 173.0, "width": 101.0, "height": 81.0}

    # Test 1 oz copper
    res_1oz = engine.calculate_thermal_field(
        revision_id=uuid4(),
        specification=spec,
        footprints=footprints,
        board_bbox=bbox,
        ambient_c=25.0,
        copper_weight_oz=1.0,
    )
    assert res_1oz["success"] is True
    assert len(res_1oz["hotspots"]) == 3
    q1_1oz = next(h for h in res_1oz["hotspots"] if h["ref"] == "Q1")

    # Test 2 oz copper: higher spreading reduces thermal resistance and junction temperature!
    res_2oz = engine.calculate_thermal_field(
        revision_id=uuid4(),
        specification=spec,
        footprints=footprints,
        board_bbox=bbox,
        ambient_c=25.0,
        copper_weight_oz=2.0,
    )
    q1_2oz = next(h for h in res_2oz["hotspots"] if h["ref"] == "Q1")

    assert q1_2oz["r_th_ja_c_w"] < q1_1oz["r_th_ja_c_w"]
    assert q1_2oz["t_junction_c"] < q1_1oz["t_junction_c"]
    assert q1_2oz["spreading_radius_mm"] > q1_1oz["spreading_radius_mm"]


def test_pcb_thermal_studio_and_rpc(tmp_path: Path):
    studio = StudioService(tmp_path)
    product = studio.create_product(code="THRM-01", name="Thermal Test", category="dc_dc_converter", owner="Thermal Lead")
    revision = studio.get_revision(product.active_revision_id)

    report = studio.calculate_pcb_thermal_field(revision.revision_id, ambient_c=25.0, copper_weight_oz=2.0)
    assert report["success"] is True
    assert "max_temperature_c" in report
    assert "hotspots" in report

    desktop = DesktopService(studio)
    rpc_res = desktop.dispatch("get_pcb_thermal_field", {"revision_id": revision.revision_id})
    assert rpc_res["success"] is True
    assert rpc_res["ambient_c"] == 25.0
