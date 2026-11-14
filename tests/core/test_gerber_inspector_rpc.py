"""Unit and integration tests for Milestone Option C: RS-274X Gerber Layer Inspector & Drill Overlay RPC."""
from __future__ import annotations

from pathlib import Path
import pytest

from mendex_core.controller import MendexEngineeringController
from mendex_core.desktop.service import DesktopService
from mendex_core.models import Specification


def _setup_test_project_with_pcb(tmp_path: Path):
    controller = MendexEngineeringController(tmp_path)
    proj = controller.create_project("Gerber Test Project", code="GTP", auto_enroll=True)
    studio = controller.service
    product = studio.get_product(proj["project_id"])
    rev = studio.get_revision(product.active_revision_id)

    spec = Specification(
        vin_min_v=20.0,
        vin_nom_v=24.0,
        vin_max_v=28.0,
        vout_v=12.0,
        iout_a=5.0,
        switching_frequency_hz=100000.0,
        isolation_requirement="Reinforced 1500V",
    )
    studio.update_specification(rev.revision_id, spec)
    rev = studio.get_revision(rev.revision_id)

    ws_dir = studio.workspace_path(rev)
    pcb_dir = ws_dir / "pcb"
    pcb_dir.mkdir(parents=True, exist_ok=True)

    # Create synthetic PCB layout with footprints, tracks, through-hole pads, vias, and edge cuts
    pcb_content = """(kicad_pcb
	(version 20260206)
	(generator "pcbnew")
	(generator_version "10.0")
	(general (thickness 1.6))
	(layers
		(0 "F.Cu" signal)
		(2 "B.Cu" signal)
		(5 "F.SilkS" user "F.Silkscreen")
		(1 "F.Mask" user)
		(3 "B.Mask" user)
		(25 "Edge.Cuts" user)
	)
	(gr_rect (start 50 50) (end 150 120) (stroke (width 0.1)) (layer "Edge.Cuts"))
	(segment (start 60 60) (end 90 60) (width 0.5) (layer "F.Cu") (net 1))
	(segment (start 90 60) (end 90 80) (width 0.5) (layer "B.Cu") (net 1))
	(via (at 90 60) (size 0.8) (drill 0.3) (layers "F.Cu" "B.Cu") (net 1))
	(footprint "Package_TO_SOT_THT:TO-220-3_Vertical"
		(at 100 80 0)
		(property "Reference" "Q1")
		(property "Value" "MOSFET")
		(pad "1" thru_hole circle (at 0 0) (size 1.8 1.8) (drill 1.0))
		(pad "2" thru_hole circle (at 2.54 0) (size 1.8 1.8) (drill 1.0))
		(pad "3" thru_hole circle (at 5.08 0) (size 1.8 1.8) (drill 1.0))
	)
	(footprint "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal"
		(at 70 90 0)
		(property "Reference" "R1")
		(property "Value" "10k")
		(pad "1" thru_hole circle (at -5.08 0) (size 1.6 1.6) (drill 0.8))
		(pad "2" thru_hole circle (at 5.08 0) (size 1.6 1.6) (drill 0.8))
	)
)"""
    (pcb_dir / "board.kicad_pcb").write_text(pcb_content, encoding="utf-8")

    # Create synthetic Gerber and Drill outputs
    gerbers_dir = pcb_dir / "gerbers"
    gerbers_dir.mkdir(parents=True, exist_ok=True)
    (gerbers_dir / "board-F_Cu.gtl").write_text("%TF.FileFunction,Copper,L1,Top*%\n%MOMM*%\nG01*", encoding="utf-8")
    (gerbers_dir / "board-B_Cu.gbl").write_text("%TF.FileFunction,Copper,L2,Bot*%\n%MOMM*%\nG01*", encoding="utf-8")
    (gerbers_dir / "board-F_Mask.gts").write_text("%TF.FileFunction,SolderMask,Top*%\n%MOMM*%\nG01*", encoding="utf-8")
    (gerbers_dir / "board-B_Mask.gbs").write_text("%TF.FileFunction,SolderMask,Bot*%\n%MOMM*%\nG01*", encoding="utf-8")
    (gerbers_dir / "board-F_Silkscreen.gto").write_text("%TF.FileFunction,Legend,Top*%\n%MOMM*%\nG01*", encoding="utf-8")
    (gerbers_dir / "board-Edge_Cuts.gm1").write_text("%TF.FileFunction,Profile*%\n%MOMM*%\nG01*", encoding="utf-8")

    drl_content = """M48
; DRILL file KiCad 10.0.7
; FORMAT={-:-/ absolute / metric / decimal}
FMAT,2
METRIC
; #@! TA.AperFunction,Plated,PTH,ComponentDrill
T1C0.300
; #@! TA.AperFunction,Plated,PTH,ComponentDrill
T2C0.800
; #@! TA.AperFunction,Plated,PTH,ComponentDrill
T3C1.000
%
G90
G05
T1
X90.00Y-60.00
T2
X64.92Y-90.00
X75.08Y-90.00
T3
X100.00Y-80.00
X102.54Y-80.00
X105.08Y-80.00
M30
"""
    (gerbers_dir / "board.drl").write_text(drl_content, encoding="utf-8")

    import zipfile
    zip_path = gerbers_dir / "board_gerbers.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for gf in gerbers_dir.iterdir():
            if gf.suffix != ".zip":
                zf.write(gf, gf.name)

    return controller, studio, product, rev


def test_inspect_gerber_layers_rpc(tmp_path: Path):
    """Verifies that inspect_gerber_layers RPC extracts layers, tools, hits, and board primitives."""
    controller, studio, product, rev = _setup_test_project_with_pcb(tmp_path)
    desktop = DesktopService(studio)

    res = desktop.dispatch("inspect_gerber_layers", {
        "revision_id": str(rev.revision_id),
        "auto_export": False,
    })

    assert res["success"] is True
    assert res["board_name"] == "board"
    assert res["layer_count"] == 2
    assert res["is_4layer"] is False

    # Check extracted layers
    layer_ids = [l["layer_id"] for l in res["layers"]]
    assert "F.Cu" in layer_ids
    assert "B.Cu" in layer_ids
    assert "F.Mask" in layer_ids
    assert "Edge.Cuts" in layer_ids
    assert "Drill" in layer_ids

    # Check Excellon Drill schedule
    drill_tools = res["drill_tools"]
    assert len(drill_tools) == 3
    t_dias = [t["diameter_mm"] for t in drill_tools]
    assert 0.3 in t_dias
    assert 0.8 in t_dias
    assert 1.0 in t_dias

    summary = res["drill_summary"]
    assert summary["total_holes"] == 6
    assert summary["pth_count"] == 6
    assert summary["npth_count"] == 0
    assert summary["tool_count"] == 3

    # Check CAD vectors
    assert len(res["edge_cuts"]) == 1
    assert len(res["tracks"]) == 2
    assert len(res["footprints"]) == 2

    # Check Gerber ZIP metadata
    assert res["has_gerber_zip"] is True
    assert res["gerber_zip_filename"] == "board_gerbers.zip"
    assert len(res["gerber_zip_sha256"]) == 64


def test_parse_excellon_file_direct():
    """Verifies that _parse_excellon_file parses tools and coordinates accurately."""
    sample_drl = """M48
METRIC
; #@! TA.AperFunction,Plated,PTH,ComponentDrill
T1C0.400
; #@! TA.AperFunction,NonPlated,NPTH,MechanicalHole
T2C3.200
%
T1
X10.50Y-20.50
X15.50Y-25.50
T2
X5.00Y-5.00
M30
"""
    tools, hits = DesktopService._parse_excellon_file(sample_drl)
    assert len(tools) == 2
    assert "T01" in tools
    assert tools["T01"]["diameter_mm"] == 0.4
    assert tools["T01"]["plated"] is True
    assert tools["T01"]["count"] == 2
    assert tools["T01"]["usage"] == "Signal / Thermal Via"

    assert "T02" in tools
    assert tools["T02"]["diameter_mm"] == 3.2
    assert tools["T02"]["plated"] is False
    assert tools["T02"]["count"] == 1
    assert tools["T02"]["usage"] == "Mounting / Mechanical Hole"

    assert len(hits) == 3
    assert hits[0]["x"] == 10.5
    assert hits[0]["y"] == 20.5  # abs Cartesian coordinate
    assert hits[0]["plated"] is True
    assert hits[2]["plated"] is False
