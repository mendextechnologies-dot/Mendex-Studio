"""Tests for Parametric Mechanical Enclosure Generator and 3D Solid Model Pipeline."""
from __future__ import annotations

from pathlib import Path
from uuid import uuid4
import pytest

from mendex_core.service import StudioService
from mendex_core.desktop.service import DesktopService
from mendex_core.desktop.models import EnclosureQuery
from integrations.generators.enclosure_generator import (
    generate_enclosure_freecad_script,
    generate_enclosure_svg_drawing,
    generate_thermal_interface_specification,
)


def test_enclosure_script_and_svg_generation():
    # 1. Test FreeCAD script generation
    script = generate_enclosure_freecad_script(
        pcb_length_mm=85.0,
        pcb_width_mm=65.0,
        output_dir="mechanical",
    )
    assert "import FreeCAD" in script
    assert "Part.makeBox" in script
    assert "EnclosureBase" in script
    assert "EnclosureLid" in script
    assert "enclosure_assembly.step" in script

    # 2. Test 2D mechanical drafting SVG
    svg = generate_enclosure_svg_drawing(
        pcb_length_mm=85.0,
        pcb_width_mm=65.0,
        product_code="SV-1000",
        revision_label="R001",
    )
    assert "<svg" in svg
    assert "VIEW A: TOP ORTHOGRAPHIC PLAN VIEW" in svg
    assert "VIEW B: CROSS-SECTIONAL ELEVATION" in svg
    assert "Q1 TIM BOSS" in svg
    assert "NOMEX 410 DIELECTRIC SHIELD" in svg
    assert "85.0" in svg or "PCB" in svg

    # 3. Test TIM specification
    tim_spec = generate_thermal_interface_specification(
        product_code="SV-1000",
        revision_label="R001",
    )
    assert "Bergquist Gap Pad 5000S35" in tim_spec
    assert "5.0" in tim_spec
    assert "0.60" in tim_spec
    assert "55.8" in tim_spec


def test_studio_service_enclosure_generation(tmp_path: Path):
    studio = StudioService(tmp_path)
    prod = studio.create_product(code="ENC-01", name="Enclosure Test", category="dc_dc_converter", owner="Mechanical Lead")
    rev = studio.get_revision(prod.active_revision_id)

    # Generate enclosure model via StudioService
    res = studio.generate_enclosure_model(rev.revision_id, export_step=True)
    assert res["success"] is True
    assert res["product_code"] == "ENC-01"
    assert res["dimensions"]["wall_thickness_mm"] == 3.0
    assert res["thermal_interface"]["tim_part"] == "Bergquist Gap Pad 5000S35"
    assert res["thermal_interface"]["junction_temp_chassis_c"] < res["thermal_interface"]["junction_temp_bare_c"]

    # Verify files created in workspace
    ws_dir = studio.workspace_path(rev)
    assert (ws_dir / "mechanical" / "enclosure_drawing.svg").exists()
    assert (ws_dir / "mechanical" / "thermal_interface_specification.md").exists()
    assert (ws_dir / "mechanical" / "make_enclosure.py").exists()

    # Query cached via get_enclosure_model
    cached = studio.get_enclosure_model(rev.revision_id)
    assert cached["success"] is True
    assert cached["dimensions"]["standoff_height_mm"] == 6.0

    # Desktop RPC route
    desktop = DesktopService(studio)
    rpc_res = desktop.dispatch("get_enclosure_model", EnclosureQuery(revision_id=rev.revision_id))
    assert rpc_res["success"] is True
    assert rpc_res["product_code"] == "ENC-01"
