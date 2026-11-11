"""End-to-End Generic Engineering Workflow Integration Test for Mendex v2.1."""
from pathlib import Path
import pytest

from mendex_core.controller import MendexEngineeringController
from mendex_core.models import Category


def test_v21_generic_engineering_e2e_workflow(tmp_path):
    """Verifies complete end-to-end lifecycle:

    Workspace -> Spec -> Synthesis -> Calculations -> Artifacts -> Dossier.
    """
    controller = MendexEngineeringController(tmp_path)

    # 1. Create Workspace
    ws_res = controller.create_workspace(
        name="Industrial Buck 20W",
        description="24V to 5V 4A DC-DC Converter for E2E qualification",
    )
    assert ws_res["status"] == "CREATED"
    ws_id = ws_res["workspace_id"]
    ws_dir = tmp_path / "workspaces" / ws_id
    assert ws_dir.exists()

    # 2. Validate Electrical Specification
    spec_data = {
        "vin_min_v": 18.0,
        "vin_nom_v": 24.0,
        "vin_max_v": 32.0,
        "vout_v": 5.0,
        "iout_a": 4.0,
        "switching_frequency_hz": 100000.0,
    }
    val_res = controller.validate_specification(spec_data)
    assert val_res["valid"] is True
    assert val_res["supplied_fields"] >= 6

    # 3. Synthesize Engineering Design & Generate Native CAD Artifacts
    synth_res = controller.generate_design(
        workspace_id=ws_id,
        title="Industrial Synchronous Buck 20W",
        category="dc_dc_converter",
        vin_nom=24.0,
        vin_min=18.0,
        vin_max=32.0,
        vout=5.0,
        iout=4.0,
        fsw_hz=100000.0,
        ripple_v=0.05,
    )
    assert synth_res["status"] == "SYNTHESIZED"
    design_id = synth_res["design_id"]
    assert len(synth_res["candidates"]) > 0

    # 4. Verify Generated Artifacts (.kicad_sch, .kicad_pcb, .asc, .net)
    artifacts = controller.list_design_artifacts(ws_id)
    assert len(artifacts) >= 3
    exts = {a["extension"] for a in artifacts}
    assert ".kicad_sch" in exts
    assert ".kicad_pcb" in exts
    assert ".asc" in exts

    # Verify each artifact exists and has valid sha256
    for art in artifacts:
        p = Path(art["absolute_path"])
        assert p.exists()
        assert len(art["sha256"]) == 64
        assert art["size_bytes"] > 0

    # 5. Run Pure Deterministic Analytical Calculations
    # 5a. Dowell Winding Loss
    dowell = controller.run_calculation("dowell", {
        "frequency_hz": 100000.0,
        "layers": 2,
        "conductor_diameter_mm": 0.5,
        "r_dc_ohm": 0.05,
        "layer_porosity_factor": 0.85,
        "temperature_c": 100.0,
    })
    assert dowell["calculation"] == "dowell_ac_winding_factor"
    assert dowell["f_r"] >= 1.0

    # 5b. Semiconductor Losses
    losses = controller.run_calculation("losses", {
        "part_number": "BSC010NE2LS",
        "r_ds_on_ohm": 0.015,
        "i_rms_a": 4.0,
        "duty_cycle": 0.45,
        "e_on_j": 12e-6,
        "e_off_j": 8e-6,
        "frequency_hz": 100000.0,
    })
    assert losses["p_total_w"] > 0

    # 5c. Steinmetz Core Loss
    stein = controller.run_calculation("steinmetz", {
        "material": "N87",
        "frequency_hz": 100000.0,
        "b_peak_t": 0.15,
        "core_volume_m3": 1.5e-5,
        "k": 1.5,
        "alpha": 1.3,
        "beta": 2.5,
    })
    assert stein["total_core_loss_w"] > 0

    # 6. Check Host Tools
    tools = controller.list_tools()
    assert len(tools) >= 3
    for tool in tools:
        assert "status" in tool
        assert "tool_id" in tool

    # 7. Generate Formal Verification Dossier
    # Register product to create baseline revision
    prod = controller.service.create_product(
        code="BC-20W",
        name="Industrial Synchronous Buck 20W",
        category=Category.DC_DC,
        owner="Lead Engineer",
        description="E2E Qualification Product",
    )
    revs = controller.list_revisions(str(prod.product_id))
    assert len(revs) == 1
    rev_id = revs[0]["revision_id"]

    dossier = controller.generate_report(rev_id)
    assert dossier["status"] == "GENERATED"
    assert Path(dossier["report_path"]).exists()
    assert len(dossier["hash"]) == 64

    # 8. Check Final Workspace Status
    status = controller.get_workspace_status(ws_id)
    assert status["design_count"] == 1
    assert status["artifact_summary"]["schematics"] >= 1
    assert status["artifact_summary"]["pcb_layouts"] >= 1
