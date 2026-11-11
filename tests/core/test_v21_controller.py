"""Tests for Mendex Engineering Controller v2.1."""
import tempfile
from pathlib import Path
from uuid import uuid4
import pytest

from mendex_core.controller import MendexEngineeringController
from mendex_core.models import Category, Specification


@pytest.fixture
def test_controller(tmp_path):
    return MendexEngineeringController(tmp_path)


def test_workspace_operations(test_controller, tmp_path):
    # Initial list
    workspaces = test_controller.list_workspaces()
    initial_count = len(workspaces)

    # Create workspace
    res = test_controller.create_workspace(
        name="Test Converter Project",
        description="High efficiency DC-DC stage",
    )
    assert res["status"] == "CREATED"
    ws_id = res["workspace_id"]
    assert (tmp_path / "workspaces" / ws_id).exists()

    # List again
    workspaces_after = test_controller.list_workspaces()
    assert len(workspaces_after) == initial_count + 1

    # Get status
    status = test_controller.get_workspace_status(ws_id)
    assert status["workspace_id"] == ws_id
    assert status["directory_exists"] is True
    assert status["design_count"] == 0


def test_specification_validation(test_controller):
    # Valid specification
    valid_data = {
        "vin_min_v": 18.0,
        "vin_nom_v": 24.0,
        "vin_max_v": 32.0,
        "vout_v": 5.0,
        "iout_a": 4.0,
        "switching_frequency_hz": 100000.0,
    }
    val_res = test_controller.validate_specification(valid_data)
    assert val_res["valid"] is True
    assert val_res["supplied_fields"] >= 6

    # Invalid specification (vin_min > vin_max)
    invalid_data = {
        "vin_min_v": 40.0,
        "vin_nom_v": 24.0,
        "vin_max_v": 30.0,
        "vout_v": 5.0,
        "iout_a": 4.0,
    }
    inv_res = test_controller.validate_specification(invalid_data)
    assert inv_res["valid"] is False
    assert len(inv_res["errors"]) > 0


def test_deterministic_calculations(test_controller):
    # 1. Dowell AC winding resistance
    dowell_res = test_controller.run_calculation(
        "dowell",
        {
            "frequency_hz": 100000.0,
            "layers": 2,
            "conductor_diameter_mm": 0.5,
            "layer_porosity_factor": 0.85,
            "r_dc_ohm": 0.05,
            "temperature_c": 100.0,
        },
    )
    assert dowell_res["calculation"] == "dowell_ac_winding_factor"
    assert dowell_res["f_r"] >= 1.0
    assert dowell_res["skin_depth_mm"] > 0

    # 2. Semiconductor losses
    loss_res = test_controller.run_calculation(
        "losses",
        {
            "part_number": "BSC010NE2LS",
            "r_ds_on_ohm": 0.015,
            "i_rms_a": 4.0,
            "duty_cycle": 0.45,
            "e_on_j": 12e-6,
            "e_off_j": 8e-6,
            "frequency_hz": 100000.0,
        },
    )
    assert loss_res["calculation"] == "semiconductor_losses"
    assert loss_res["p_conduction_w"] > 0
    assert loss_res["p_switching_w"] > 0
    assert loss_res["p_total_w"] == loss_res["p_conduction_w"] + loss_res["p_switching_w"]

    # 3. Steinmetz core loss
    stein_res = test_controller.run_calculation(
        "steinmetz",
        {
            "material": "N87",
            "k": 1.5,
            "alpha": 1.3,
            "beta": 2.5,
            "frequency_hz": 100000.0,
            "b_peak_t": 0.15,
            "core_volume_m3": 1.5e-5,
        },
    )
    assert stein_res["calculation"] == "steinmetz_core_loss"
    assert stein_res["total_core_loss_w"] > 0
    assert stein_res["volumetric_loss_w_m3"] > 0

    # 4. Flyback transformer design
    flyback_res = test_controller.run_calculation(
        "flyback",
        {
            "vin_min_v": 18.0,
            "vin_nom_v": 24.0,
            "vout_v": 12.0,
            "iout_a": 3.0,
            "frequency_hz": 100000.0,
            "d_max": 0.45,
            "efficiency": 0.88,
            "b_max_t": 0.25,
            "core_ae_mm2": 125.0,
        },
    )
    assert flyback_res["calculation"] == "flyback_transformer_design"
    assert flyback_res["inputs"]["core_ae_mm2"] == 125.0
    assert flyback_res["primary_turns"] >= 1
    assert flyback_res["secondary_turns"] >= 1
    assert flyback_res["air_gap_mm"] > 0


def test_calculations_refuse_missing_inputs(test_controller):
    """No calculation may run on silently assumed engineering values."""
    import pytest
    with pytest.raises(ValueError, match="Missing required inputs"):
        test_controller.run_calculation("dowell", {})
    with pytest.raises(ValueError, match="core_ae_mm2"):
        test_controller.run_calculation("flyback", {"vin_min_v": 18.0, "vin_nom_v": 24.0, "vout_v": 12.0, "iout_a": 3.0,
                                                    "frequency_hz": 1e5, "d_max": 0.45, "efficiency": 0.88, "b_max_t": 0.25})


def test_design_synthesis_and_artifacts(test_controller, tmp_path):
    # Create workspace
    ws_res = test_controller.create_workspace("Synthesis Test WS")
    ws_id = ws_res["workspace_id"]

    # Synthesize Buck converter
    synth_res = test_controller.generate_design(
        workspace_id=ws_id,
        title="Buck 24V to 5V 4A",
        category="dc_dc_converter",
        vin_nom=24.0,
        vout=5.0,
        iout=4.0,
        fsw_hz=100000.0,
        ripple_v=0.05,
    )
    assert synth_res["status"] == "SYNTHESIZED"
    design_id = synth_res["design_id"]
    assert len(synth_res["candidates"]) > 0
    assert len(synth_res["generated_artifacts"]) > 0

    # Get design
    design_info = test_controller.get_design(design_id)
    assert design_info["design_id"] == design_id
    assert len(design_info["components"]) > 0

    # List candidates
    cands = test_controller.list_design_candidates(design_id)
    assert len(cands) > 0

    # List artifacts
    artifacts = test_controller.list_design_artifacts(ws_id)
    assert len(artifacts) >= 2
    extensions = {a["extension"] for a in artifacts}
    assert ".kicad_sch" in extensions
    assert ".kicad_pcb" in extensions
    assert ".asc" in extensions


def test_tools_and_diagnostics(test_controller):
    tools = test_controller.list_tools()
    assert len(tools) >= 3
    tool_ids = {t["tool_id"] for t in tools}
    assert "ltspice" in tool_ids or "kicad" in tool_ids

    check = test_controller.check_tool(tools[0]["tool_id"])
    assert "status" in check
    assert "installed_path" in check


def test_report_generation(test_controller):
    # Create product and revision
    prod = test_controller.service.create_product(
        code="PRD-V21",
        name="Test v2.1 Product",
        category=Category.DC_DC,
        owner="Test Engineer",
        description="Controller unit testing",
    )
    revs = test_controller.list_revisions(str(prod.product_id))
    assert len(revs) == 1
    rev_id = revs[0]["revision_id"]

    # Generate dossier
    report_res = test_controller.generate_report(rev_id)
    assert report_res["status"] == "GENERATED"
    assert Path(report_res["report_path"]).exists()
    assert len(report_res["hash"]) == 64
