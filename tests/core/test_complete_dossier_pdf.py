"""Tests for Complete Product Engineering Dossier (CPED) Report & Automated PDF Generation."""

import base64
import hashlib
import json
from pathlib import Path
import pytest

from mendex_core.controller import MendexEngineeringController
from mendex_core.desktop.service import DesktopService
from mendex_core.dossier_generator import (
    render_schematic_svg,
    render_pcb_svg,
    render_waveform_svg,
    render_3d_assembly_card,
    render_femm_magnetics_card,
    render_erc_drc_scorecard,
    render_kpi_cards,
    render_sizing_section,
    render_bom_section,
    render_manufacturing_section,
    render_ecr_section,
    render_lifecycle_section,
    render_validation_section,
    build_complete_dossier_html,
    compile_html_to_pdf,
)
from mendex_core.design.models import ArtifactKind


def test_dossier_svg_and_card_renderers(tmp_path):
    """Verifies all visual SVG renderers and card builders in isolation."""
    # 1. Schematic SVG
    sch_path = tmp_path / "test.kicad_sch"
    sch_path.write_text(
        '(kicad_sch (version 20231120)\n'
        '  (symbol (lib_id "Device:R") (at 100 80 0)\n'
        '    (property "Reference" "R1") (property "Value" "10k"))\n'
        '  (wire (pts (xy 100 85) (xy 120 85)))\n'
        '  (label "VOUT" (at 120 85 0))\n'
        ')\n',
        encoding="utf-8"
    )
    svg_sch = render_schematic_svg(sch_path)
    assert "<svg" in svg_sch
    assert "R1" in svg_sch
    assert "VOUT" in svg_sch
    assert "line" in svg_sch

    # 2. PCB Layout SVG
    pcb_path = tmp_path / "test.kicad_pcb"
    pcb_path.write_text(
        '(kicad_pcb (version 20240108)\n'
        '  (gr_rect (start 90 90) (end 190 170) (layer "Edge.Cuts"))\n'
        '  (gr_rect (start 138 92) (end 142 168) (layer "Edge.Cuts"))\n'
        '  (segment (start 105 100) (end 125 100) (width 0.8) (layer "F.Cu") (net 1))\n'
        '  (segment (start 145 100) (end 165 100) (width 1.2) (layer "B.Cu") (net 2))\n'
        '  (footprint "Package_TO_SOT_SMD:SOT-223"\n'
        '    (at 110 100)\n'
        '    (property "Reference" "Q1")\n'
        '    (pad "1" smd rect (at 0 0) (size 1.2 1.8))\n'
        '  )\n'
        ')\n',
        encoding="utf-8"
    )
    svg_pcb = render_pcb_svg(pcb_path)
    assert "<svg" in svg_pcb
    assert "HV ISOLATION BARRIER (5mm)" in svg_pcb
    assert "Q1" in svg_pcb
    assert "#10b981" in svg_pcb  # F.Cu green
    assert "#3b82f6" in svg_pcb  # B.Cu blue

    # 3. Waveform SVG
    raw_path = tmp_path / "sim.raw"
    raw_path.write_text(
        "Title: Test Transient\n"
        "Date: Today\n"
        "Plotname: Transient Analysis\n"
        "Flags: real forward\n"
        "No. Variables: 3\n"
        "No. Points: 4\n"
        "Variables:\n"
        "  0 time time\n"
        "  1 V(vout) voltage\n"
        "  2 I(L1) current\n"
        "Values:\n"
        "  0 0.0\n"
        "    0.0\n"
        "    0.0\n"
        "  1 0.001\n"
        "    12.0\n"
        "    2.5\n"
        "  2 0.002\n"
        "    12.1\n"
        "    2.4\n"
        "  3 0.003\n"
        "    11.9\n"
        "    2.6\n",
        encoding="utf-8"
    )
    svg_wf, metrics = render_waveform_svg(raw_path)
    assert "<svg" in svg_wf
    assert "V(vout)" in svg_wf
    assert "I(L1)" in svg_wf
    assert metrics.get("v_max") == 12.1
    assert metrics.get("i_max") == 2.6

    # 4. FEMM Magnetics Card
    mag_dir = tmp_path / "magnetics"
    mag_dir.mkdir()
    (mag_dir / "actuator_results.json").write_text(
        json.dumps({
            "actuator_model": "Pulse Electromagnet Core",
            "peak_flux_density_b_max_t": 0.0118,
            "core_saturation_threshold_t": 1.6,
            "saturation_margin_pct": 99.3,
            "core_saturated": False,
            "primary_turns": 450,
            "coil_excitation_current_a": 2.36,
            "ampere_turns": 1062.0,
            "core_material": "Soft Magnetic Iron",
            "fe_model_path": "magnetics/electromagnet.fem",
            "fe_solution_path": "magnetics/electromagnet.ans"
        }),
        encoding="utf-8"
    )
    femm_card = render_femm_magnetics_card(tmp_path)
    assert "Finite Element Magnetic Analysis" in femm_card
    assert "99.3 %" in femm_card
    assert "PASS (99.3% Margin)" in femm_card

    # 5. 3D Assembly Card
    pcb_dir = tmp_path / "pcb"
    pcb_dir.mkdir()
    # Dummy 1x1 transparent PNG
    dummy_png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")
    (pcb_dir / "board_3d_render.png").write_bytes(dummy_png)
    mech_dir = tmp_path / "mechanical"
    mech_dir.mkdir()
    (mech_dir / "board.step").write_text("ISO-10303-21;\nHEADER;\nENDSEC;\nDATA;\nENDSEC;\nEND-ISO-10303-21;\n", encoding="utf-8")
    
    card_3d = render_3d_assembly_card(tmp_path)
    assert "data:image/png;base64," in card_3d
    assert "Mechanical 3D Solid Model:" in card_3d
    assert "board.step" in card_3d


def test_complete_dossier_html_and_pdf_compilation(tmp_path):
    """End-to-end integration test creating a product, populating workspace, and compiling vector PDF."""
    controller = MendexEngineeringController(tmp_path)
    proj = controller.create_project("Pulse Driver Dossier Test", code="PDD-100", auto_enroll=True)
    studio = controller.service
    product = studio.get_product(proj["project_id"])
    rev = studio.get_revision(product.active_revision_id)
    ws = studio.workspace_path(rev)

    # 1. Populate workspace artifacts
    pcb_dir = ws / "pcb"
    pcb_dir.mkdir(parents=True, exist_ok=True)
    (pcb_dir / "driver.kicad_sch").write_text(
        '(kicad_sch (version 20231120)\n'
        '  (symbol (lib_id "Transistor_FET:IKW40N65H5") (at 100 80 0)\n'
        '    (property "Reference" "Q1") (property "Value" "IKW40N65H5"))\n'
        '  (symbol (lib_id "Device:L") (at 140 80 0)\n'
        '    (property "Reference" "L1") (property "Value" "100uH"))\n'
        '  (wire (pts (xy 100 85) (xy 140 85)))\n'
        '  (label "GATE" (at 100 80 0))\n'
        '  (label "COIL_SW" (at 120 85 0))\n'
        ')\n',
        encoding="utf-8"
    )
    (pcb_dir / "driver.kicad_pcb").write_text(
        '(kicad_pcb (version 20240108)\n'
        '  (gr_rect (start 90 90) (end 190 170) (layer "Edge.Cuts"))\n'
        '  (gr_rect (start 138 92) (end 142 168) (layer "Edge.Cuts"))\n'
        '  (segment (start 105 100) (end 125 100) (width 0.8) (layer "F.Cu") (net 1))\n'
        '  (footprint "Package_TO_SOT_SMD:TO-247-3"\n'
        '    (at 110 100)\n'
        '    (property "Reference" "Q1")\n'
        '    (pad "1" thru_hole circle (at 0 0) (size 2.0 2.0))\n'
        '  )\n'
        ')\n',
        encoding="utf-8"
    )
    (pcb_dir / "erc_report.json").write_text(json.dumps({"violations": []}), encoding="utf-8")
    (pcb_dir / "drc_report.json").write_text(json.dumps({"violations": [], "unconnected_items": []}), encoding="utf-8")

    # 3D render & STEP
    dummy_png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")
    (pcb_dir / "board_3d_render.png").write_bytes(dummy_png)
    mech_dir = ws / "mechanical"
    mech_dir.mkdir(parents=True, exist_ok=True)
    (mech_dir / "driver.step").write_text("ISO-10303-21;\nHEADER;\nENDSEC;\nDATA;\nENDSEC;\nEND-ISO-10303-21;\n", encoding="utf-8")

    # Simulations
    sim_dir = ws / "simulations"
    sim_dir.mkdir(parents=True, exist_ok=True)
    (sim_dir / "pulse.raw").write_text(
        "Title: Pulse Sim\nNo. Variables: 3\nNo. Points: 2\nVariables:\n  0 time time\n  1 V(COIL_SW) voltage\n  2 I(L1) current\nValues:\n  0 0.0\n    0.0\n    0.0\n  1 0.001\n    330.0\n    2.35\n",
        encoding="utf-8"
    )
    (sim_dir / "pulse.log").write_text(
        "v_peak: MAX(v(coil_sw))=330.0 FROM 0 TO 0.001\ni_peak: MAX(i(l1))=2.35 FROM 0 TO 0.001\n",
        encoding="utf-8"
    )

    # Magnetics
    mag_dir = ws / "magnetics"
    mag_dir.mkdir(parents=True, exist_ok=True)
    (mag_dir / "actuator_results.json").write_text(
        json.dumps({
            "actuator_model": "Pulse Electromagnet Actuator",
            "peak_flux_density_b_max_t": 0.0118,
            "core_saturation_threshold_t": 1.6,
            "saturation_margin_pct": 99.3,
            "core_saturated": False,
            "primary_turns": 450,
            "coil_excitation_current_a": 2.36,
            "ampere_turns": 1062.0,
            "core_material": "Soft Magnetic Iron"
        }),
        encoding="utf-8"
    )

    # BOM
    bom_dir = ws / "bom"
    bom_dir.mkdir(parents=True, exist_ok=True)
    (bom_dir / "bom.csv").write_text(
        "Item,Designator,Qty,Description,Manufacturer,MPN,Package,Voltage_Rating,Current_Rating,Primary_Side\n"
        "1,Q1,1,IGBT 650V 40A,Infineon,IKW40N65H5,TO-247,650V,40A,Yes\n"
        "2,L1,1,Power Inductor 100uH,Coilcraft,MSS1210-104,SMD,100V,3A,No\n",
        encoding="utf-8"
    )

    # Manufacturing Gerber ZIP
    gerb_dir = pcb_dir / "gerbers"
    gerb_dir.mkdir(parents=True, exist_ok=True)
    (gerb_dir / "driver-F_Cu.gbr").write_text("%FSLAX36Y36*%\n%MOMM*%\n", encoding="utf-8")
    import zipfile
    zip_path = gerb_dir / "driver_gerbers.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("driver-F_Cu.gbr", "%FSLAX36Y36*%\n")

    # 2. Dispatch generate_report via DesktopService
    desktop = DesktopService(studio)
    res = desktop.dispatch("generate_report", {"revision_id": str(rev.revision_id)})

    assert res["success"] is True
    assert res["report_id"] is not None
    assert "report.html" in res["report_path"]

    # Verify HTML contents
    full_html = studio.root / res["report_path"]
    assert full_html.exists()
    content = full_html.read_text(encoding="utf-8")

    assert "CPED-PDD-100" in content
    assert "DRAFT ONLY: no manufacturing approval" in content
    assert "IKW40N65H5" in content
    assert "Coilcraft" in content
    assert "Finite Element Magnetic Analysis" in content
    assert "99.3 %" in content
    assert "HV ISOLATION BARRIER (5mm)" in content
    assert "data:image/png;base64," in content
    assert "driver.step" in content
    assert "Manufacturing Fabrication Package" in content

    # 3. Verify automated PDF compilation
    if res["pdf_available"]:
        assert res["pdf_path"] is not None
        full_pdf = studio.root / res["pdf_path"]
        assert full_pdf.exists()
        pdf_bytes = full_pdf.read_bytes()
        assert len(pdf_bytes) > 1000
        assert pdf_bytes.startswith(b"%PDF-")
        assert res["sha256"] is not None
        assert res["sha256"] == hashlib.sha256(pdf_bytes).hexdigest()

        # Verify REPORT design artifact ingestion
        designs = studio.design.list_designs()
        matched = [d for d in designs if getattr(d, "core_revision_id", None) == str(rev.revision_id)]
        if matched:
            rep_artifacts = [a for a in matched[0].artifacts if a.kind == ArtifactKind.REPORT]
            assert len(rep_artifacts) >= 1
            assert rep_artifacts[0].sha256 == res["sha256"]


def test_dossier_missing_data_remains_not_evaluated(tmp_path):
    """Verifies that missing artifacts are faithfully marked NOT_EVALUATED per engineering rules."""
    controller = MendexEngineeringController(tmp_path)
    proj = controller.create_project("Empty Baseline Proj", code="EMP-001", auto_enroll=True)
    studio = controller.service
    product = studio.get_product(proj["project_id"])
    rev = studio.get_revision(product.active_revision_id)
    ws = studio.workspace_path(rev)

    desktop = DesktopService(studio)
    res = desktop.dispatch("generate_report", {"revision_id": str(rev.revision_id)})
    assert res["success"] is True

    full_html = studio.root / res["report_path"]
    content = full_html.read_text(encoding="utf-8")

    # In empty workspace, all visual cards should report NOT_EVALUATED
    assert "Schematic Diagram: NOT_EVALUATED" in content
    assert "2D PCB Layout: NOT_EVALUATED" in content
    assert "3D CAD Representation: NOT_EVALUATED" in content
    assert "SPICE Transient Simulation: NOT_EVALUATED" in content
    assert "FEMM 4.2 FEA Magnetics: NOT_EVALUATED" in content
    assert "Bill of Materials: NOT_EVALUATED" in content
    assert "Fabrication Release Package: NOT_EVALUATED" in content


def test_desktop_service_get_report_rpc(tmp_path):
    """Verifies DesktopService.dispatch('get_report') returns complete HTML content and PDF metadata for in-app preview."""
    controller = MendexEngineeringController(tmp_path)
    proj = controller.create_project("Preview Dossier Test", code="PVW-100", auto_enroll=True)
    studio = controller.service
    product = studio.get_product(proj["project_id"])
    rev = studio.get_revision(product.active_revision_id)

    desktop = DesktopService(studio)
    gen_res = desktop.dispatch("generate_report", {"revision_id": str(rev.revision_id)})
    assert gen_res["success"] is True
    report_id = gen_res["report_id"]

    # Call get_report
    rep_data = desktop.dispatch("get_report", {"report_id": report_id})
    assert rep_data["report_id"] == report_id
    assert rep_data["revision_id"] == str(rev.revision_id)
    assert "html_content" in rep_data
    assert "CPED-PVW-100" in rep_data["html_content"]
    assert "has_pdf" in rep_data
    if rep_data["has_pdf"]:
        assert rep_data["pdf_size_bytes"] > 0
