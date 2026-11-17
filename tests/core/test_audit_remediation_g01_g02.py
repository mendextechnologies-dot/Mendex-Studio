"""Tests for Audit Remediation G01 (Release Completeness) and G02 (Release Integrity)."""
import json
import time
import zipfile
from pathlib import Path
from uuid import uuid4
import pytest

from mendex_core.models import Category
from mendex_core.service import StudioError, StudioService
from mendex_core.design.release_packager import (
    MANDATORY_DISCIPLINES,
    categorize_deliverable,
    scan_workspace_candidates,
)


def test_g01_release_categorization():
    """G01: Deliverable file taxonomy properly categorizes power electronics deliverables."""
    assert categorize_deliverable("board.kicad_sch") == "cad"
    assert categorize_deliverable("board.kicad_pcb") == "cad"
    assert categorize_deliverable("gerbers.zip") == "fabrication"
    assert categorize_deliverable("copper_top.gbr") == "fabrication"
    assert categorize_deliverable("drill.drl") == "fabrication"
    assert categorize_deliverable("board.d356") == "fabrication"
    assert categorize_deliverable("board-pos.csv") == "assembly"
    assert categorize_deliverable("bom.csv") == "bom"
    assert categorize_deliverable("bom_procurement.docx") == "bom"
    assert categorize_deliverable("enclosure.step") == "mechanical"
    assert categorize_deliverable("chassis_drawing.svg") == "mechanical"
    assert categorize_deliverable("transient.raw") == "simulation"
    assert categorize_deliverable("thermal_analysis.json") == "simulation"
    assert categorize_deliverable("requirements.json") == "requirements"
    assert categorize_deliverable("test_plan.docx") == "testing_qa"


def test_g01_release_packager_reports_incomplete_when_mandatory_disciplines_missing(tmp_path):
    """G01: Release package is marked INCOMPLETE when mandatory disciplines are missing."""
    service = StudioService(tmp_path)
    product = service.create_product("REL-01", "Release Test", Category.DC_DC, "Lead Engineer")
    rev = service.get_revision(product.active_revision_id)
    ws_dir = service.workspace_path(rev)

    # Populate only CAD and BOM files (missing fabrication, assembly, mechanical)
    (ws_dir / "circuit").mkdir(parents=True, exist_ok=True)
    (ws_dir / "circuit" / "top.kicad_sch").write_text("(kicad_sch ...)", encoding="utf-8")
    (ws_dir / "bom").mkdir(parents=True, exist_ok=True)
    (ws_dir / "bom" / "bom.csv").write_text("Ref,Value\nR1,10k\n", encoding="utf-8")

    pkg = service.generate_release_package(product.active_revision_id)
    assert pkg["status"] == "INCOMPLETE"
    assert len(pkg["missing_mandatory_disciplines"]) > 0
    assert "fabrication" in pkg["missing_mandatory_disciplines"]
    assert "mechanical" in pkg["missing_mandatory_disciplines"]
    assert "assembly" in pkg["missing_mandatory_disciplines"]


def test_g02_self_contained_manifest_in_package(tmp_path):
    """G02: Release package contains a self-contained release_manifest.json inside the ZIP root."""
    service = StudioService(tmp_path)
    product = service.create_product("REL-02", "Release Test 2", Category.DC_DC, "Lead Engineer")
    rev = service.get_revision(product.active_revision_id)
    ws_dir = service.workspace_path(rev)

    # Populate basic files
    (ws_dir / "circuit").mkdir(parents=True, exist_ok=True)
    (ws_dir / "circuit" / "top.kicad_sch").write_text("(kicad_sch ...)", encoding="utf-8")

    pkg = service.generate_release_package(product.active_revision_id)
    zip_path = ws_dir / pkg["package_relative_path"]
    assert zip_path.is_file()

    with zipfile.ZipFile(zip_path, "r") as zf:
        namelist = zf.namelist()
        assert "release_manifest.json" in namelist
        manifest_data = json.loads(zf.read("release_manifest.json").decode("utf-8"))
        assert manifest_data["product_code"] == "REL-02"
        assert manifest_data["revision_label"] == "R001"
        assert "contents" in manifest_data


def test_g02_validation_detects_crc_corruption(tmp_path):
    """G02: Corrupted ZIP archive with modified payload is detected fail-closed."""
    service = StudioService(tmp_path)
    product = service.create_product("REL-03", "Corruption Test", Category.DC_DC, "QA Engineer")
    rev = service.get_revision(product.active_revision_id)
    ws_dir = service.workspace_path(rev)

    (ws_dir / "bom.csv").write_text("Ref,Value\nR1,10k\n", encoding="utf-8")
    pkg = service.generate_release_package(product.active_revision_id)
    zip_path = ws_dir / pkg["package_relative_path"]

    # Tamper with archive bytes directly
    raw_bytes = bytearray(zip_path.read_bytes())
    # Modify a byte inside the data stream (around middle of file)
    mid = len(raw_bytes) // 2
    raw_bytes[mid] = (raw_bytes[mid] + 1) % 256
    zip_path.write_bytes(raw_bytes)

    # Validate after corruption
    pkg_after = service.get_release_package(product.active_revision_id)
    assert pkg_after["status"] == "CORRUPTED"
    assert pkg_after["integrity_status"] == "CORRUPTED"
    assert "failed" in pkg_after["integrity_reason"].lower() or "cannot be opened" in pkg_after["integrity_reason"].lower() or "mismatch" in pkg_after["integrity_reason"].lower()


def test_g02_validation_detects_stale_package(tmp_path):
    """G02: Editing workspace source files after release packaging marks package STALE."""
    service = StudioService(tmp_path)
    product = service.create_product("REL-04", "Freshness Test", Category.DC_DC, "Lead Engineer")
    rev = service.get_revision(product.active_revision_id)
    ws_dir = service.workspace_path(rev)

    circuit_file = ws_dir / "schematic.kicad_sch"
    circuit_file.write_text("(kicad_sch baseline)", encoding="utf-8")

    pkg = service.generate_release_package(product.active_revision_id)
    zip_path = ws_dir / pkg["package_relative_path"]

    # Ensure archive has earlier timestamp
    old_time = time.time() - 100
    import os
    os.utime(zip_path, (old_time, old_time))

    # Modify workspace source file with newer timestamp
    circuit_file.write_text("(kicad_sch updated)", encoding="utf-8")
    new_time = time.time() + 10
    os.utime(circuit_file, (new_time, new_time))

    pkg_stale = service.get_release_package(product.active_revision_id)
    assert pkg_stale["status"] == "STALE"
    assert pkg_stale["freshness_status"] == "STALE"
    assert "modified after" in pkg_stale["integrity_reason"]
