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


def test_cad_preview_multi_angle_3d_render(tmp_path):
    controller = MendexEngineeringController(tmp_path)
    proj = controller.create_project("CAD Test Proj Multi", code="CTPM", auto_enroll=True)
    try:
        studio = controller.service
        product = studio.get_product(proj["project_id"])
        rev = studio.get_revision(product.active_revision_id)
        ws = studio.workspace_path(rev)
        pcb_dir = ws / "pcb"
        pcb_dir.mkdir(parents=True, exist_ok=True)

        (pcb_dir / "board.kicad_pcb").write_text("(kicad_pcb)", encoding="utf-8")
        dummy_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
        (pcb_dir / "board_3d_top.png").write_bytes(dummy_png)
        (pcb_dir / "board_3d_bottom.png").write_bytes(dummy_png)

        desktop = DesktopService(studio)
        res_top = desktop.cad_preview(CADPreviewQuery(revision_id=rev.revision_id, kind="3d", view="top"))
        assert res_top["available"] is True
        assert res_top["view"] == "top"
        assert "Top View" in res_top["title"]

        res_bot = desktop.cad_preview(CADPreviewQuery(revision_id=rev.revision_id, kind="3d", view="bottom"))
        assert res_bot["available"] is True
        assert res_bot["view"] == "bottom"
        assert "Bottom View" in res_bot["title"]
    finally:
        ed = tmp_path / "engineering_designs"
        if ed.exists():
            for f in list(ed.iterdir()):
                try:
                    f.unlink()
                except Exception:
                    pass
            try:
                ed.rmdir()
            except Exception:
                pass


def test_export_cad_step_service_and_metadata(tmp_path):
    controller = MendexEngineeringController(tmp_path)
    proj = controller.create_project("STEP Test Proj", code="STP1", auto_enroll=True)
    studio = controller.service
    product = studio.get_product(proj["project_id"])
    rev = studio.get_revision(product.active_revision_id)
    ws = studio.workspace_path(rev)
    pcb_dir = ws / "pcb"
    pcb_dir.mkdir(parents=True, exist_ok=True)

    # Write minimal valid kicad_pcb
    sample_pcb = """(kicad_pcb
  (version 20240108)
  (general (thickness 1.6))
  (gr_rect (start 10.0 10.0) (end 50.0 50.0) (stroke (width 0.15) (type solid)) (layer "Edge.Cuts"))
)"""
    pcb_path = pcb_dir / "board.kicad_pcb"
    pcb_path.write_text(sample_pcb, encoding="utf-8")

    from mendex_core.desktop.models import STEPExportQuery, BridgeRequest
    desktop = DesktopService(studio)

    # 1. Export STEP model
    res = desktop.export_cad_step(STEPExportQuery(revision_id=rev.revision_id, open_native=False))
    assert res["available"] is True
    assert res["filename"] == "board.step"
    assert res["size_bytes"] > 0
    assert (pcb_dir / "board.step").exists()

    # 2. Verify 3D Preview metadata reflects STEP solid
    dummy_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    (pcb_dir / "board_3d_render.png").write_bytes(dummy_png)

    res_3d = desktop.cad_preview(CADPreviewQuery(revision_id=rev.revision_id, kind="3d"))
    assert res_3d["available"] is True
    assert res_3d["has_step"] is True
    assert res_3d["step_filename"] == "board.step"
    assert res_3d["step_bytes"] == (pcb_dir / "board.step").stat().st_size

    # 3. Test RPC dispatch handler
    rpc_res = desktop.dispatch("export_cad_step", {"revision_id": str(rev.revision_id), "open_native": False})
    assert rpc_res["available"] is True
    assert rpc_res["filename"] == "board.step"


def test_generate_report_dispatch_and_dossier(tmp_path):
    controller = MendexEngineeringController(tmp_path)
    proj = controller.create_project("Report Test Proj", code="RTP1", auto_enroll=True)
    studio = controller.service
    product = studio.get_product(proj["project_id"])
    rev = studio.get_revision(product.active_revision_id)
    ws = studio.workspace_path(rev)

    # 1. Add mock BOM CSV
    bom_dir = ws / "bom"
    bom_dir.mkdir(parents=True, exist_ok=True)
    (bom_dir / "bom.csv").write_text(
        "Item,Designator,Qty,Description,Manufacturer,MPN,Package,Voltage_Rating,Current_Rating,Primary_Side\n"
        "1,Q1,1,IGBT 650V 40A,Infineon,IKW40N65H5,TO-247,650V,40A,Yes\n",
        encoding="utf-8"
    )

    desktop = DesktopService(studio)
    res = desktop.dispatch("generate_report", {"revision_id": str(rev.revision_id)})

    assert res["success"] is True
    assert res["report_id"] is not None
    assert "report.html" in res["report_path"]

    # Verify report HTML contains populated BOM
    rep_html = (studio.root / res["report_path"]).read_text(encoding="utf-8")
    assert "IKW40N65H5" in rep_html
    assert "Infineon" in rep_html
    assert "Q1" in rep_html
    assert "DRAFT ONLY: no manufacturing approval" in rep_html

    # Check PDF export status
    if res["pdf_available"]:
        assert res["pdf_path"] is not None
        assert (studio.root / res["pdf_path"]).exists()


def test_export_gerbers_dispatch_and_zip(tmp_path):
    controller = MendexEngineeringController(tmp_path)
    proj = controller.create_project("Gerber Test Proj", code="GTP1", auto_enroll=True)
    studio = controller.service
    product = studio.get_product(proj["project_id"])
    rev = studio.get_revision(product.active_revision_id)
    ws = studio.workspace_path(rev)
    pcb_dir = ws / "pcb"
    pcb_dir.mkdir(parents=True, exist_ok=True)

    # Minimal board with 1 track to satisfy routed requirement
    sample_pcb = """(kicad_pcb
  (version 20240108)
  (general (thickness 1.6))
  (gr_rect (start 10.0 10.0) (end 50.0 50.0) (stroke (width 0.15) (type solid)) (layer "Edge.Cuts"))
  (segment (start 15.0 15.0) (end 25.0 25.0) (width 0.5) (layer "F.Cu") (net 0))
)"""
    (pcb_dir / "board.kicad_pcb").write_text(sample_pcb, encoding="utf-8")

    desktop = DesktopService(studio)
    res = desktop.dispatch("export_gerbers", {"revision_id": str(rev.revision_id), "check_drc": False})

    assert res["success"] is True
    assert res["file_count"] > 0
    assert "zip_path" in res
    assert (studio.root / res["zip_path"]).exists()


def test_auto_route_heavy_copper_thermal_relief_rpc(tmp_path):
    """Verifies that auto_route_pcb RPC accepts and forwards heavy copper thermal relief parameters."""
    from unittest.mock import patch
    controller = MendexEngineeringController(tmp_path)
    proj = controller.create_project("Thermal Relief Proj", code="TRP", auto_enroll=True)
    studio = controller.service
    product = studio.get_product(proj["project_id"])
    rev = studio.get_revision(product.active_revision_id)
    ws = studio.workspace_path(rev)
    pcb_dir = ws / "pcb"
    pcb_dir.mkdir(parents=True, exist_ok=True)
    (pcb_dir / "board.kicad_pcb").write_text("(kicad_pcb)", encoding="utf-8")

    desktop = DesktopService(studio)

    fake_route_res = {
        "routing_completed": True,
        "tracks": 8,
        "vias": 2,
        "unrouted_after": 0,
        "pour_completed": True,
        "drc_errors": 0,
        "drc_warnings": 0,
        "messages": ["Ground pour filled with heavy copper thermals"],
        "netclasses": {"Power": {"width": 2.0}},
    }

    with patch("integrations.adapters.copper_kicad_adapter.CopperKiCadAdapter.route_pcb", return_value=fake_route_res) as mock_route:
        res = desktop.dispatch("auto_route_pcb", {
            "revision_id": str(rev.revision_id),
            "pour_ground": True,
            "power_track": 2.0,
            "default_track": 0.4,
            "thermal_spoke": 0.8,
            "thermal_gap": 0.6,
            "pad_connection": "tht_thermal",
            "zone_clearance": 0.6,
        })

    assert res["success"] is True
    assert res["tracks"] == 8
    assert res["pour_completed"] is True
    mock_route.assert_called_once()
    kwargs = mock_route.call_args[1]
    assert kwargs["power_track"] == 2.0
    assert kwargs["thermal_spoke"] == 0.8
    assert kwargs["thermal_gap"] == 0.6
    assert kwargs["pad_connection"] == "tht_thermal"
    assert kwargs["zone_clearance"] == 0.6


def test_mill_isolation_slot_dispatch_and_cad_preview(tmp_path):
    """Verifies physical Edge.Cuts isolation air slot milling and detection by 2D CAD preview."""
    controller = MendexEngineeringController(tmp_path)
    proj = controller.create_project("Isolation Proj", code="ISOP", auto_enroll=True)
    studio = controller.service
    product = studio.get_product(proj["project_id"])
    rev = studio.get_revision(product.active_revision_id)
    ws = studio.workspace_path(rev)
    pcb_dir = ws / "pcb"
    pcb_dir.mkdir(parents=True, exist_ok=True)

    sample_pcb = """(kicad_pcb
  (version 20240108)
  (general (thickness 1.6))
  (gr_rect (start 0.0 0.0) (end 100.0 60.0) (stroke (width 0.15) (type solid)) (layer "Edge.Cuts"))
  (segment (start 10.0 10.0) (end 20.0 10.0) (width 0.5) (layer "F.Cu") (net 1))
)"""
    pcb_file = pcb_dir / "board.kicad_pcb"
    pcb_file.write_text(sample_pcb, encoding="utf-8")

    desktop = DesktopService(studio)

    # 1. Dispatch mill_isolation_slot
    res = desktop.dispatch("mill_isolation_slot", {
        "revision_id": str(rev.revision_id),
        "slot_width": 3.0,
        "slot_length": 35.0,
        "center_x": 50.0,
        "center_y": 30.0,
    })

    assert res["success"] is True
    assert res["slot_geometry"]["width_mm"] == 3.0
    assert res["slot_geometry"]["length_mm"] == 35.0
    assert res["slot_geometry"]["start"] == [48.5, 12.5]
    assert res["slot_geometry"]["end"] == [51.5, 47.5]

    # Verify physical file updated
    pcb_updated = pcb_file.read_text(encoding="utf-8")
    assert '48.5 12.5' in pcb_updated and '51.5 47.5' in pcb_updated
    assert '"Edge.Cuts"' in pcb_updated

    # 2. Verify CAD Preview detects the isolation slot
    preview = desktop.cad_preview(CADPreviewQuery(revision_id=rev.revision_id, kind="pcb"))
    assert preview["available"] is True
    assert len(preview["edge_cuts"]) >= 2
    # Find the milled slot rectangle
    slots = [ec for ec in preview["edge_cuts"] if ec["type"] == "rect" and (ec["x2"] - ec["x1"]) <= 5.0 and (ec["y2"] - ec["y1"]) >= 20.0]
    assert len(slots) == 1
    slot = slots[0]
    assert round(slot["x2"] - slot["x1"], 1) == 3.0
    assert round(slot["y2"] - slot["y1"], 1) == 35.0


def test_setup_four_layer_power_planes_dispatch_and_cad_preview(tmp_path):
    """Verifies IPC-2152 compliant 4-layer internal copper plane setup (In1.Cu GND + In2.Cu VIN) and CAD preview detection."""
    controller = MendexEngineeringController(tmp_path)
    proj = controller.create_project("FourLayer Proj", code="FLAY", auto_enroll=True)
    studio = controller.service
    product = studio.get_product(proj["project_id"])
    rev = studio.get_revision(product.active_revision_id)
    ws = studio.workspace_path(rev)
    pcb_dir = ws / "pcb"
    pcb_dir.mkdir(parents=True, exist_ok=True)

    # Standard 2-layer board with PRI_GND and VIN nets
    sample_pcb = """(kicad_pcb
  (version 20240108)
  (general (thickness 1.6))
  (layers
    (0 "F.Cu" signal)
    (31 "B.Cu" signal)
    (25 "Edge.Cuts" user)
  )
  (net 0 "")
  (net 1 "PRI_GND")
  (net 2 "VIN")
  (gr_rect (start 0.0 0.0) (end 100.0 60.0) (stroke (width 0.15) (type solid)) (layer "Edge.Cuts"))
  (footprint "Resistor_SMD:R_0805_2012Metric" (layer "F.Cu")
    (at 20 20)
    (property "Reference" "R1" (at 0 -1.5 0) (layer "F.SilkS"))
    (property "Value" "10k" (at 0 1.5 0) (layer "F.Fab"))
    (pad "1" smd roundrect (at -0.95 0) (size 1 1.3) (layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio 0.25) (net 1 "PRI_GND"))
    (pad "2" smd roundrect (at 0.95 0) (size 1 1.3) (layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio 0.25) (net 2 "VIN"))
  )
  (segment (start 10.0 10.0) (end 20.0 10.0) (width 0.5) (layer "F.Cu") (net 1))
)"""
    pcb_file = pcb_dir / "board.kicad_pcb"
    pcb_file.write_text(sample_pcb, encoding="utf-8")

    desktop = DesktopService(studio)

    # 1. Dispatch setup_4layer_planes
    res = desktop.dispatch("setup_4layer_planes", {
        "revision_id": str(rev.revision_id),
        "gnd_net": "PRI_GND",
        "pwr_net": "VIN",
        "zone_clearance": 0.5,
        "thermal_spoke": 0.6,
        "pad_connection": "tht_thermal",
    })

    assert res["success"] is True
    assert res["layers"] == ["F.Cu", "In1.Cu", "In2.Cu", "B.Cu"]
    assert res["in1_gnd_poured"] is True
    assert res["in2_pwr_poured"] is True
    assert res["gnd_net"] == "PRI_GND"
    assert res["pwr_net"] == "VIN"

    # 2. Verify physical .kicad_pcb file updated with In1.Cu and In2.Cu
    pcb_updated = pcb_file.read_text(encoding="utf-8")
    assert '"In1.Cu"' in pcb_updated
    assert '"In2.Cu"' in pcb_updated

    # 3. Verify CAD Preview detects 4-layer stackup and zones
    preview = desktop.cad_preview(CADPreviewQuery(revision_id=rev.revision_id, kind="pcb"))
    assert preview["available"] is True
    assert preview["is_4layer"] is True
    assert preview["layer_count"] == 4
    assert len(preview["zones"]) >= 2
    zone_layers = [z["layer"] for z in preview["zones"]]
    assert "In1.Cu" in zone_layers
    assert "In2.Cu" in zone_layers
