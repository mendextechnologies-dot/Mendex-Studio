import json
import zipfile
from pathlib import Path
from uuid import uuid4

import pytest

from mendex_core.controller import MendexEngineeringController
from mendex_core.desktop.models import GerberDownloadQuery, GerberExportQuery, GerberInspectQuery
from mendex_core.desktop.service import DesktopService
from mendex_core.lifecycle.kicad_service import KiCadLifecycleService


def test_kicad_service_exports_pos_d356_and_stats(tmp_path):
    kicad = KiCadLifecycleService()
    if not kicad.is_available():
        pytest.skip("KiCad CLI not available on workstation")

    sample_pcb = """(kicad_pcb
  (version 20240108)
  (general (thickness 1.6))
  (layers
    (0 "F.Cu" signal)
    (31 "B.Cu" signal)
    (36 "B.SilkS" user "B.Silkscreen")
    (37 "F.SilkS" user "F.Silkscreen")
    (38 "B.Mask" user)
    (39 "F.Mask" user)
    (40 "Edge.Cuts" user)
  )
  (net 0 "")
  (net 1 "VCC")
  (net 2 "GND")
  (gr_rect (start 10.0 10.0) (end 60.0 40.0) (stroke (width 0.15) (type solid)) (layer "Edge.Cuts"))
  (segment (start 20.0 20.0) (end 30.0 20.0) (width 0.5) (layer "F.Cu") (net 1))
  (footprint "Resistor_SMD:R_0805_2012Metric" (layer "F.Cu")
    (at 20.0 20.0)
    (property "Reference" "R1")
    (property "Value" "10k")
    (pad "1" smd roundrect (at -0.95 0.0) (size 1.0 1.3) (layers "F.Cu" "F.Mask") (net 1 "VCC"))
    (pad "2" smd roundrect (at 0.95 0.0) (size 1.0 1.3) (layers "F.Cu" "F.Mask") (net 2 "GND"))
  )
  (footprint "Package_TO_SOT_SMD:TO-252-2" (layer "F.Cu")
    (at 40.0 25.0)
    (property "Reference" "Q1")
    (property "Value" "MOSFET_N")
    (pad "1" smd roundrect (at -2.3 0.0) (size 1.6 3.0) (layers "F.Cu" "F.Mask") (net 2 "GND"))
    (pad "2" smd roundrect (at 2.3 0.0) (size 1.6 3.0) (layers "F.Cu" "F.Mask") (net 1 "VCC"))
  )
)"""
    pcb_file = tmp_path / "board.kicad_pcb"
    pcb_file.write_text(sample_pcb, encoding="utf-8")

    out_pos = tmp_path / "board_cpl.csv"
    res_pos = kicad.export_pos(pcb_file, output_file=out_pos, side="both", format="csv", units="mm")
    assert res_pos.exists()
    cpl_lines = res_pos.read_text(encoding="utf-8").strip().splitlines()
    assert len(cpl_lines) >= 3  # Header + R1 + Q1
    assert "Ref,Val,Package,PosX,PosY,Rot,Side" in cpl_lines[0]
    assert any("R1" in l for l in cpl_lines)
    assert any("Q1" in l for l in cpl_lines)

    out_d356 = tmp_path / "board.d356"
    res_d356 = kicad.export_ipcd356(pcb_file, output_file=out_d356)
    assert res_d356.exists()
    assert res_d356.stat().st_size > 0

    out_stats = tmp_path / "board_stats.json"
    res_stats = kicad.export_stats(pcb_file, output_file=out_stats, format="json")
    assert res_stats.exists()
    stats_data = json.loads(res_stats.read_text(encoding="utf-8"))
    assert "board" in stats_data
    assert "components" in stats_data


def test_turnkey_manufacturing_package_flow(tmp_path):
    controller = MendexEngineeringController(tmp_path)
    proj = controller.create_project("Turnkey PCB Proj", code="TPB", auto_enroll=True)
    studio = controller.service
    product = studio.get_product(proj["project_id"])
    rev = studio.get_revision(product.active_revision_id)
    ws = studio.workspace_path(rev)
    pcb_dir = ws / "pcb"
    pcb_dir.mkdir(parents=True, exist_ok=True)

    sample_pcb = """(kicad_pcb
  (version 20240108)
  (general (thickness 1.6))
  (layers
    (0 "F.Cu" signal)
    (31 "B.Cu" signal)
    (36 "B.SilkS" user "B.Silkscreen")
    (37 "F.SilkS" user "F.Silkscreen")
    (38 "B.Mask" user)
    (39 "F.Mask" user)
    (40 "Edge.Cuts" user)
  )
  (net 0 "")
  (net 1 "VCC")
  (net 2 "GND")
  (gr_rect (start 10.0 10.0) (end 80.0 60.0) (stroke (width 0.15) (type solid)) (layer "Edge.Cuts"))
  (segment (start 20.0 20.0) (end 40.0 20.0) (width 0.5) (layer "F.Cu") (net 1))
  (footprint "Resistor_SMD:R_0805_2012Metric" (layer "F.Cu")
    (at 20.0 20.0)
    (property "Reference" "R1")
    (property "Value" "10k")
    (pad "1" smd roundrect (at -0.95 0.0) (size 1.0 1.3) (layers "F.Cu" "F.Mask") (net 1 "VCC"))
    (pad "2" smd roundrect (at 0.95 0.0) (size 1.0 1.3) (layers "F.Cu" "F.Mask") (net 2 "GND"))
  )
)"""
    pcb_file = pcb_dir / "board.kicad_pcb"
    pcb_file.write_text(sample_pcb, encoding="utf-8")

    # Add dummy BOM
    bom_dir = ws / "bom" / "exports"
    bom_dir.mkdir(parents=True, exist_ok=True)
    (bom_dir / "procurement_bom.csv").write_text("Ref,MPN,Qty\nR1,RC0805FR-0710KL,1\n", encoding="utf-8")

    desktop = DesktopService(studio)

    # 1. Export manufacturing package
    res_exp = desktop.export_gerbers(GerberExportQuery(revision_id=rev.revision_id, auto_route=False, check_drc=False))
    assert res_exp["success"] is True

    # 2. Inspect layer stack and turnkey contents
    res_inspect = desktop.inspect_gerber_layers(GerberInspectQuery(revision_id=rev.revision_id, auto_export=False))
    assert res_inspect["success"] is True
    assert "cpl_summary" in res_inspect
    cpl = res_inspect["cpl_summary"]
    assert cpl["available"] is True
    assert cpl["total_components"] == 1
    assert cpl["smd_count"] == 1
    assert cpl["top_side_count"] == 1

    turnkey = res_inspect["turnkey_package"]
    assert turnkey["available"] is True
    assert turnkey["filename"].endswith("_turnkey_manufacturing.zip")
    assert turnkey["has_cpl"] is True
    assert turnkey["has_d356"] is True
    assert turnkey["has_board_stats"] is True

    # 3. Test download endpoints
    dl_gerber = desktop.download_gerbers(GerberDownloadQuery(revision_id=rev.revision_id, package_type="gerber"))
    assert dl_gerber["success"] is True
    assert dl_gerber["filename"].endswith("_gerbers.zip")
    assert dl_gerber["data_uri"].startswith("data:application/zip;base64,")

    dl_turnkey = desktop.download_gerbers(GerberDownloadQuery(revision_id=rev.revision_id, package_type="turnkey"))
    assert dl_turnkey["success"] is True
    assert dl_turnkey["filename"].endswith("_turnkey_manufacturing.zip")
    assert dl_turnkey["data_uri"].startswith("data:application/zip;base64,")

    # Verify that turnkey zip contains cpl.csv, d356, and bom.csv
    turnkey_path = ws / "pcb" / "gerbers" / dl_turnkey["filename"]
    with zipfile.ZipFile(turnkey_path, "r") as zf:
        names = zf.namelist()
        assert any(n.endswith("_cpl.csv") for n in names)
        assert any(n.endswith(".d356") for n in names)
        assert any(n.endswith("_board_stats.json") for n in names)
        assert any(n.endswith("_bom.csv") for n in names)
