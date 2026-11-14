"""Tests for Formal Production Release Handover Package Builder & Manifest Synthesizer."""
import json
import zipfile
import pytest
from pathlib import Path
from mendex_core.service import StudioService, StudioError
from mendex_core.desktop.service import DesktopService


def test_release_package_end_to_end(tmp_path):
    """Verifies scanning, packaging, cryptographic SHA-256 manifest synthesis, and RPC dispatch."""
    service = StudioService(tmp_path)
    desktop = DesktopService(service)

    prod = service.create_product("REL-TEST", "Release Qualification Product", "dc_dc_converter", "Lead Engineer")
    rev = service.get_revision(prod.active_revision_id)
    ws_dir = service.workspace_path(rev)
    ws_dir.mkdir(parents=True, exist_ok=True)

    # 1. Initially without deliverables, querying get_release_package returns PENDING_GENERATION
    initial_res = desktop.dispatch("get_release_package", {"revision_id": str(rev.revision_id)})
    assert initial_res["status"] == "PENDING_GENERATION"
    assert initial_res["package_exists"] is False
    assert initial_res["available_candidates_count"] == 0

    # Attempting to build with 0 deliverables raises StudioError
    with pytest.raises(StudioError):
        desktop.dispatch("build_release_package", {"revision_id": str(rev.revision_id)})

    # 2. Populate mock engineering deliverables across 5 multidisciplinary domains
    (ws_dir / "cad").mkdir(parents=True, exist_ok=True)
    (ws_dir / "cad" / "power_stage.kicad_sch").write_text("(kicad_sch (version 20240108))", encoding="utf-8")
    (ws_dir / "cad" / "power_stage.kicad_pcb").write_text("(kicad_pcb (version 20240108))", encoding="utf-8")
    (ws_dir / "cad" / "power_stage.kicad_pro").write_text("{}", encoding="utf-8")

    (ws_dir / "gerbers").mkdir(parents=True, exist_ok=True)
    (ws_dir / "gerbers" / "power_stage-F_Cu.gbr").write_text("%FSLAX46Y46*%", encoding="utf-8")
    (ws_dir / "gerbers" / "power_stage.drl").write_text("M48\nMETRIC\nM30", encoding="utf-8")

    (ws_dir / "assembly").mkdir(parents=True, exist_ok=True)
    (ws_dir / "assembly" / "cpl.csv").write_text("Designator,Val,Package,Mid X,Mid Y,Rotation,Layer\nC1,10uF,0805,10,20,0,Top", encoding="utf-8")
    (ws_dir / "assembly" / "3d_render.png").write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR")
    (ws_dir / "assembly" / "assembly_guide.md").write_text("# Assembly & Inspection Guide\nFollow IPC-A-610 Class 3.", encoding="utf-8")

    (ws_dir / "bom").mkdir(parents=True, exist_ok=True)
    (ws_dir / "bom" / "bom.json").write_text(json.dumps([{"item": 1, "mpn": "GRM21BR61E106KA73L"}]), encoding="utf-8")
    (ws_dir / "bom" / "bom.csv").write_text("Item,Qty,Reference,MPN\n1,1,C1,GRM21BR61E106KA73L", encoding="utf-8")

    (ws_dir / "reports").mkdir(parents=True, exist_ok=True)
    (ws_dir / "reports" / "test_plan.html").write_text("<html><body>Staged Bring-up Protocol</body></html>", encoding="utf-8")
    (ws_dir / "reports" / "report.pdf").write_bytes(b"%PDF-1.4 mock content")

    # 3. Query get_release_package before build: detects candidate files
    res_candidates = desktop.dispatch("get_release_package", {"revision_id": str(rev.revision_id)})
    assert res_candidates["status"] == "PENDING_GENERATION"
    assert res_candidates["package_exists"] is False
    assert res_candidates["available_candidates_count"] >= 10

    # 4. Build formal release handover package
    build_res = desktop.dispatch("build_release_package", {
        "revision_id": str(rev.revision_id),
        "author": "Chief Systems Architect",
    })
    assert build_res["status"] == "READY"
    assert build_res["package_exists"] is True
    assert build_res["product_code"] == "REL-TEST"
    assert build_res["revision_label"] == rev.revision_label
    assert build_res["package_filename"].endswith(".zip")
    assert build_res["package_size_bytes"] > 0
    assert len(build_res["package_sha256"]) == 64
    assert build_res["generator"] == "Chief Systems Architect"
    assert "governance_notice" in build_res

    # Check categories
    cats = build_res["categories"]
    assert len(cats["cad"]) >= 3
    assert len(cats["fabrication"]) >= 2
    assert len(cats["assembly"]) >= 3
    assert len(cats["bom"]) >= 2
    assert len(cats["testing_qa"]) >= 2

    # 5. Check actual ZIP archive contents on disk
    zip_path = ws_dir / "release_package" / build_res["package_filename"]
    assert zip_path.exists()
    with zipfile.ZipFile(zip_path, "r") as zf:
        namelist = zf.namelist()
        assert any("power_stage.kicad_pcb" in n for n in namelist)
        assert any("power_stage-F_Cu.gbr" in n for n in namelist)
        assert any("cpl.csv" in n for n in namelist)
        assert any("bom.json" in n for n in namelist)
        assert any("test_plan.html" in n for n in namelist)

    # 6. Check release_manifest.json on disk
    manifest_path = ws_dir / "release_package" / "release_manifest.json"
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["schema_version"] == "3.1.0"
    assert manifest["product_code"] == "REL-TEST"
    assert manifest["package_sha256"] == build_res["package_sha256"]
    assert len(manifest["contents"]) >= 10

    # Every item has valid sha256
    for item in manifest["contents"]:
        assert len(item["sha256"]) == 64
        assert item["size_bytes"] > 0

    # 7. Subsequent get_release_package call returns persisted READY state
    query_res = desktop.dispatch("get_release_package", {"revision_id": str(rev.revision_id)})
    assert query_res["status"] == "READY"
    assert query_res["package_sha256"] == build_res["package_sha256"]
    assert len(query_res["contents"]) == len(build_res["contents"])
