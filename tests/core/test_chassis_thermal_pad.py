"""Tests for Chassis Heat Sinking & Thermal Interface Material (TIM) Modeling."""
from __future__ import annotations

from pathlib import Path
from uuid import uuid4
import pytest

from mendex_core.service import StudioService
from mendex_core.desktop.service import DesktopService
from mendex_core.desktop.models import PCBThermalQuery
from mendex_core.design.thermal_engine import PCBThermalEngine


def test_chassis_thermal_pad_calculations(tmp_path: Path):
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
    ]
    bbox = {"min_x": 0.0, "min_y": 0.0, "max_x": 100.0, "max_y": 80.0, "width": 100.0, "height": 80.0}

    # 1. Bare PCB in still air (no chassis cooling)
    res_bare = engine.calculate_thermal_field(
        revision_id=uuid4(),
        specification=spec,
        footprints=footprints,
        board_bbox=bbox,
        ambient_c=25.0,
        copper_weight_oz=2.0,
        chassis_cooling=False,
    )
    q1_bare = next(h for h in res_bare["hotspots"] if h["ref"] == "Q1")
    assert q1_bare["tim_applied"] is False
    assert q1_bare["t_junction_c"] > 130.0  # High thermal stress on bare PCB

    # 2. Chassis-mounted with Bergquist Gap Pad 5000S35
    res_chassis = engine.calculate_thermal_field(
        revision_id=uuid4(),
        specification=spec,
        footprints=footprints,
        board_bbox=bbox,
        ambient_c=25.0,
        copper_weight_oz=2.0,
        chassis_cooling=True,
        tim_conductivity_w_mk=5.0,
        tim_thickness_mm=1.5,
        tim_area_mm2=400.0,
        chassis_r_th_c_w=3.2,
    )
    q1_chassis = next(h for h in res_chassis["hotspots"] if h["ref"] == "Q1")
    assert q1_chassis["tim_applied"] is True
    assert q1_chassis["t_junction_c"] < 70.0   # Significantly cooled down below 70C
    assert q1_chassis["status"] == "PASS"

    # Quantitative delta-T reduction
    delta_t = q1_bare["t_junction_c"] - q1_chassis["t_junction_c"]
    assert delta_t > 70.0  # Massive cooling benefit (>70C drop)
    assert res_chassis["cooling_mode"] == "CHASSIS_TIM_SINK"
    assert res_chassis["tim_specification"]["part_number"] == "Bergquist Gap Pad 5000S35"
    assert res_chassis["tim_specification"]["delta_t_reduction_c"] > 70.0


def test_desktop_service_chassis_cooling_rpc(tmp_path: Path):
    studio = StudioService(tmp_path)
    prod = studio.create_product(code="TIM-01", name="TIM Test", category="dc_dc_converter", owner="Thermal Lead")
    rev = studio.get_revision(prod.active_revision_id)

    desktop = DesktopService(studio)

    # RPC query with chassis cooling enabled
    query = PCBThermalQuery(
        revision_id=rev.revision_id,
        ambient_c=25.0,
        copper_weight_oz=2.0,
        chassis_cooling=True,
    )
    res = desktop.dispatch("calculate_pcb_thermal_field", query)
    assert res["success"] is True
    assert res["cooling_mode"] == "CHASSIS_TIM_SINK"
    assert res["tim_specification"] is not None
