import json
from pathlib import Path
from uuid import uuid4

from mendex_core.controller import MendexEngineeringController
from mendex_core.desktop.models import CADPreviewQuery
from mendex_core.desktop.service import DesktopService


def test_cad_preview_extracts_pcb_and_drc_summary(tmp_path):
    controller = MendexEngineeringController(tmp_path)
    proj = controller.create_project("CAD Test Proj", code="CTP", auto_enroll=True)
    studio = controller.service
    product = studio.get_product(proj["project_id"])
    rev = studio.get_revision(product.active_revision_id)
    ws = studio.workspace_path(rev)
    pcb_dir = ws / "pcb"
    pcb_dir.mkdir(parents=True, exist_ok=True)

    # 1. Write sample .kicad_pcb
    sample_pcb = """(kicad_pcb
  (version 20240108)
  (general (thickness 1.6))
  (gr_line (start 10.0 10.0) (end 110.0 10.0) (stroke (width 0.15) (type solid)) (layer "Edge.Cuts"))
  (gr_line (start 110.0 10.0) (end 110.0 80.0) (stroke (width 0.15) (type solid)) (layer "Edge.Cuts"))
  (segment (start 20.0 20.0) (end 30.0 20.0) (width 0.5) (layer "F.Cu") (net 1))
  (footprint "Package_TO_SOT_SMD:TO-252-2" (layer "F.Cu")
    (at 50.0 40.0)
    (property "Reference" "Q1")
    (property "Value" "C3M0065090J")
    (model "${KICAD10_3DMODEL_DIR}/Package_TO_SOT_SMD.3dshapes/TO-252-2.step" (offset (xyz 0 0 0)))
    (pad "1" smd roundrect (at -2.3 0.0) (size 1.6 3.0))
    (pad "2" smd roundrect (at 2.3 0.0) (size 1.6 3.0))
  )
)"""
    (pcb_dir / "board.kicad_pcb").write_text(sample_pcb, encoding="utf-8")

    # 2. Write sample drc_report.json
    drc_payload = {
        "date": "2026-11-14T12:00:00",
        "violations": [
            {"severity": "warning", "type": "lib_footprint_mismatch", "description": "Footprint warning"},
            {"severity": "error", "type": "clearance", "description": "Track too close to pad"}
        ],
        "unconnected_items": []
    }
    (pcb_dir / "drc_report.json").write_text(json.dumps(drc_payload), encoding="utf-8")

    desktop = DesktopService(studio)
    res = desktop.cad_preview(CADPreviewQuery(revision_id=rev.revision_id, kind="pcb"))
    assert res["available"] is True
    assert res["kind"] == "pcb"
    assert len(res["edge_cuts"]) == 2
    assert len(res["tracks"]) == 1
    assert len(res["footprints"]) == 1
    fp = res["footprints"][0]
    assert fp["ref"] == "Q1"
    assert fp["has_3d_model"] is True
    assert len(fp["pads"]) == 2

    # Verify DRC Summary
    assert res["drc_summary"] is not None
    assert res["drc_summary"]["errors"] == 1
    assert res["drc_summary"]["warnings"] == 1
    assert res["drc_summary"]["status"] == "FAIL"  # 1 error causes FAIL


def test_cad_preview_extracts_schematic_and_erc_summary(tmp_path):
    controller = MendexEngineeringController(tmp_path)
    proj = controller.create_project("CAD Test Proj 2", code="CTP2", auto_enroll=True)
    studio = controller.service
    product = studio.get_product(proj["project_id"])
    rev = studio.get_revision(product.active_revision_id)
    ws = studio.workspace_path(rev)
    pcb_dir = ws / "pcb"
    pcb_dir.mkdir(parents=True, exist_ok=True)

    # 1. Write sample .kicad_sch
    sample_sch = """(kicad_sch
  (version 20231120)
  (generator "mendex_core")
  (title_block
    (title "Flyback Power Stage")
  )
  (symbol (lib_id "Device:C_Polarized") (at 50.0 60.0)
    (property "Reference" "C1")
    (property "Value" "100uF")
  )
  (wire (pts (xy 50.0 60.0) (xy 80.0 60.0)))
  (label "VBUS" (at 80.0 60.0))
)"""
    (pcb_dir / "circuit.kicad_sch").write_text(sample_sch, encoding="utf-8")

    # 2. Write sample erc_report.json with 0 errors
    erc_payload = {
        "date": "2026-11-14T12:00:00",
        "sheets": [
            {
                "path": "/",
                "violations": [
                    {"severity": "warning", "type": "single_global_label", "description": "Single label"}
                ]
            }
        ]
    }
    (pcb_dir / "erc_report.json").write_text(json.dumps(erc_payload), encoding="utf-8")

    desktop = DesktopService(studio)
    res = desktop.cad_preview(CADPreviewQuery(revision_id=rev.revision_id, kind="schematic"))
    assert res["available"] is True
    assert res["kind"] == "schematic"
    assert res["title"] == "Flyback Power Stage"
    assert len(res["symbols"]) == 1
    assert res["symbols"][0]["ref"] == "C1"
    assert len(res["wires"]) == 1
    assert len(res["labels"]) == 1
    assert res["labels"][0]["name"] == "VBUS"

    # Verify ERC Summary
    assert res["erc_summary"] is not None
    assert res["erc_summary"]["errors"] == 0
    assert res["erc_summary"]["warnings"] == 1
    assert res["erc_summary"]["status"] == "PASS"  # 0 errors = PASS


def test_cad_preview_extracts_3d_render(tmp_path):
    controller = MendexEngineeringController(tmp_path)
    proj = controller.create_project("CAD Test Proj 3", code="CTP3", auto_enroll=True)
    studio = controller.service
    product = studio.get_product(proj["project_id"])
    rev = studio.get_revision(product.active_revision_id)
    ws = studio.workspace_path(rev)
    pcb_dir = ws / "pcb"
    pcb_dir.mkdir(parents=True, exist_ok=True)

    # 1. Write dummy board.kicad_pcb and dummy board_3d_render.png
    (pcb_dir / "board.kicad_pcb").write_text("(kicad_pcb)", encoding="utf-8")
    dummy_png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    (pcb_dir / "board_3d_render.png").write_bytes(dummy_png_bytes)

    desktop = DesktopService(studio)
    res = desktop.cad_preview(CADPreviewQuery(revision_id=rev.revision_id, kind="3d"))
    assert res["available"] is True
    assert res["kind"] == "3d"
    assert res["filename"] == "board.kicad_pcb"
    assert res["render_bytes"] == len(dummy_png_bytes)
    assert res["render_image"].startswith("data:image/png;base64,")
