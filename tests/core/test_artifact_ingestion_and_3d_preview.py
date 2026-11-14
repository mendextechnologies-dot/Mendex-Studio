"""Unit tests for Task 3: Automated Lifecycle Artifact Ingestion and 3D Raytraced View."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from mendex_core.controller import MendexEngineeringController
from mendex_core.design.models import (
    ArtifactKind,
    DesignArtifact,
    DesignRevision,
    DesignStatus,
    EngineeringDesign,
)
from mendex_core.desktop.models import CADPreviewQuery, GerberExportQuery, STEPExportQuery
from mendex_core.desktop.service import DesktopService
from mendex_core.lifecycle.kicad_service import KiCadLifecycleService


def _create_test_environment(tmp_path: Path):
    """Sets up a test project, core revision, workspace, and linked EngineeringDesign."""
    controller = MendexEngineeringController(tmp_path)
    proj = controller.create_project("Ingestion Test Project", code="ITP", auto_enroll=True)
    studio = controller.service
    product = studio.get_product(proj["project_id"])
    core_rev = studio.get_revision(product.active_revision_id)
    ws_dir = studio.workspace_path(core_rev)
    pcb_dir = ws_dir / "pcb"
    pcb_dir.mkdir(parents=True, exist_ok=True)

    # Create linked EngineeringDesign
    design = EngineeringDesign(
        workspace_id=str(proj["project_id"]),
        product_id=str(product.product_id),
        core_revision_id=str(core_rev.revision_id),
        title="Test Power Design",
        category="dc_dc_converter",
        status=DesignStatus.DRAFT,
    )
    from mendex_core.design.ir import DesignIntermediateRepresentation
    ir = DesignIntermediateRepresentation(design_id=design.id, name="Test Circuit")
    design_rev = DesignRevision(
        design_id=design.id,
        revision_index=1,
        label="Rev 1",
        ir=ir,
        summary="Test baseline",
    )
    design.revisions.append(design_rev)
    design.active_revision_id = design_rev.id
    studio.design._persist(design)

    return controller, studio, product, core_rev, design, pcb_dir


def test_export_gerbers_ingests_artifact_with_sha256(tmp_path):
    controller, studio, product, core_rev, design, pcb_dir = _create_test_environment(tmp_path)

    # 1. Place a board file
    pcb_path = pcb_dir / "board.kicad_pcb"
    pcb_path.write_text("""(kicad_pcb (version 20240108) (general (thickness 1.6))
      (segment (start 10 10) (end 20 20) (width 0.5) (layer "F.Cu") (net 1))
      (footprint "Resistor_SMD:R_0805_2012Metric" (at 15 15) (pad "1" smd roundrect (at -1 0) (size 1 1.2)))
    )""", encoding="utf-8")

    # 2. Mock kicad export_gerbers and export_drill to produce dummy gerber files
    def fake_export_gerbers(board, **kwargs):
        out_dir = board.parent / "gerbers"
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "board-F_Cu.gbr").write_bytes(b"G04 Dummy Gerber Copper Top*")
        (out_dir / "board-Edge_Cuts.gbr").write_bytes(b"G04 Dummy Edge Cuts*")
        return out_dir

    def fake_export_drill(board, **kwargs):
        out_dir = board.parent / "gerbers"
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "board.drl").write_bytes(b"M48 Dummy Drill*")
        return out_dir

    desktop = DesktopService(studio)

    with patch.object(KiCadLifecycleService, "export_gerbers", side_effect=fake_export_gerbers), \
         patch.object(KiCadLifecycleService, "export_drill", side_effect=fake_export_drill):
        res = desktop.export_gerbers(GerberExportQuery(revision_id=core_rev.revision_id, auto_route=False, check_drc=False))

    assert res["success"] is True
    assert "sha256" in res
    assert len(res["sha256"]) == 64

    # Verify physical zip exists and matches sha256
    zip_full_path = studio.root / res["zip_path"]
    assert zip_full_path.exists()
    expected_digest = hashlib.sha256(zip_full_path.read_bytes()).hexdigest()
    assert res["sha256"] == expected_digest

    # Verify DesignArtifact was registered in the EngineeringDesign
    persisted_design = studio.design.get_design(design.id)
    assert persisted_design is not None
    active_rev = persisted_design.get_active_revision()
    assert active_rev is not None

    gerber_artifacts = [a for a in active_rev.artifacts if a.kind == ArtifactKind.GERBER_BUNDLE]
    assert len(gerber_artifacts) == 1
    art = gerber_artifacts[0]
    assert art.name == "board_gerbers.zip"
    assert art.sha256 == expected_digest
    assert art.format == "zip"
    assert art.source_service == "KiCadLifecycleService"
    assert art.edit_provenance == "Deterministic Manufacturing Release"


def test_export_cad_step_ingests_step_solid_artifact(tmp_path):
    controller, studio, product, core_rev, design, pcb_dir = _create_test_environment(tmp_path)

    # 1. Place a board file
    pcb_path = pcb_dir / "board.kicad_pcb"
    pcb_path.write_text("(kicad_pcb (version 20240108))", encoding="utf-8")

    # 2. Mock kicad export_step to create a dummy STEP file
    def fake_export_step(board, output_step=None):
        out_step = output_step or (board.parent / f"{board.stem}.step")
        out_step.write_bytes(b"ISO-10303-21; HEADER; DUMMY STEP SOLID DATA; ENDSEC; END-ISO-10303-21;")
        return out_step

    desktop = DesktopService(studio)

    with patch.object(KiCadLifecycleService, "is_available", return_value=True), \
         patch.object(KiCadLifecycleService, "export_step", side_effect=fake_export_step):
        res = desktop.export_cad_step(STEPExportQuery(revision_id=core_rev.revision_id, open_native=False))

    assert res["available"] is True
    assert "sha256" in res
    assert len(res["sha256"]) == 64

    # Verify step file exists and matches sha256
    step_file = pcb_dir / "board.step"
    assert step_file.exists()
    expected_digest = hashlib.sha256(step_file.read_bytes()).hexdigest()
    assert res["sha256"] == expected_digest

    # Verify DesignArtifact was registered in EngineeringDesign
    persisted_design = studio.design.get_design(design.id)
    active_rev = persisted_design.get_active_revision()
    step_artifacts = [a for a in active_rev.artifacts if a.kind == ArtifactKind.STEP_SOLID]
    assert len(step_artifacts) == 1
    art = step_artifacts[0]
    assert art.name == "board.step"
    assert art.sha256 == expected_digest
    assert art.format == "step"
    assert art.source_service == "KiCadLifecycleService"
    assert art.edit_provenance == "KiCad CLI 3D Solid Model"


def test_cad_preview_3d_includes_step_sha256(tmp_path):
    controller, studio, product, core_rev, design, pcb_dir = _create_test_environment(tmp_path)

    # 1. Place dummy board, png render, and step model
    pcb_path = pcb_dir / "board.kicad_pcb"
    pcb_path.write_text("(kicad_pcb)", encoding="utf-8")

    dummy_png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    (pcb_dir / "board_3d_render.png").write_bytes(dummy_png_bytes)

    dummy_step_bytes = b"ISO-10303-21; HEADER; STEP 3D MODEL; ENDSEC;"
    step_path = pcb_dir / "board.step"
    step_path.write_bytes(dummy_step_bytes)
    step_hash = hashlib.sha256(dummy_step_bytes).hexdigest()

    desktop = DesktopService(studio)
    res = desktop.cad_preview(CADPreviewQuery(revision_id=core_rev.revision_id, kind="3d", view="iso"))

    assert res["available"] is True
    assert res["kind"] == "3d"
    assert res["has_step"] is True
    assert res["step_filename"] == "board.step"
    assert res["step_bytes"] == len(dummy_step_bytes)
    assert res["step_sha256"] == step_hash
    assert res["render_image"].startswith("data:image/png;base64,")


def test_artifact_ingestion_idempotency(tmp_path):
    controller, studio, product, core_rev, design, pcb_dir = _create_test_environment(tmp_path)

    pcb_path = pcb_dir / "board.kicad_pcb"
    pcb_path.write_text("(kicad_pcb)", encoding="utf-8")

    def fake_export_gerbers(board, **kwargs):
        out_dir = board.parent / "gerbers"
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "board-F_Cu.gbr").write_bytes(b"G04 Copper Top*")
        return out_dir

    def fake_export_drill(board, **kwargs):
        out_dir = board.parent / "gerbers"
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "board.drl").write_bytes(b"M48 Drill*")
        return out_dir

    def fake_export_step(board, output_step=None):
        out_step = output_step or (board.parent / f"{board.stem}.step")
        out_step.write_bytes(b"ISO-10303-21; DUMMY STEP;")
        return out_step

    desktop = DesktopService(studio)

    # Run Gerbers export twice
    with patch.object(KiCadLifecycleService, "export_gerbers", side_effect=fake_export_gerbers), \
         patch.object(KiCadLifecycleService, "export_drill", side_effect=fake_export_drill):
        desktop.export_gerbers(GerberExportQuery(revision_id=core_rev.revision_id, auto_route=False, check_drc=False))
        desktop.export_gerbers(GerberExportQuery(revision_id=core_rev.revision_id, auto_route=False, check_drc=False))

    # Run STEP export twice
    with patch.object(KiCadLifecycleService, "is_available", return_value=True), \
         patch.object(KiCadLifecycleService, "export_step", side_effect=fake_export_step):
        desktop.export_cad_step(STEPExportQuery(revision_id=core_rev.revision_id, open_native=False))
        desktop.export_cad_step(STEPExportQuery(revision_id=core_rev.revision_id, open_native=False))

    persisted_design = studio.design.get_design(design.id)
    active_rev = persisted_design.get_active_revision()

    # Verify no duplicate artifact kinds
    gerber_arts = [a for a in active_rev.artifacts if a.kind == ArtifactKind.GERBER_BUNDLE]
    step_arts = [a for a in active_rev.artifacts if a.kind == ArtifactKind.STEP_SOLID]

    assert len(gerber_arts) == 1, "Duplicate GERBER_BUNDLE artifacts found"
    assert len(step_arts) == 1, "Duplicate STEP_SOLID artifacts found"


def test_kicad_service_export_fab_pack(tmp_path):
    service = KiCadLifecycleService()
    pcb_path = tmp_path / "board.kicad_pcb"
    pcb_path.write_text("(kicad_pcb (segment (start 0 0) (end 10 10) (width 0.4) (layer F.Cu) (net 1)))", encoding="utf-8")

    dummy_zip = tmp_path / "board_fab.zip"
    dummy_zip.write_bytes(b"PK\x03\x04DUMMY FAB PACK CONTENT")
    expected_hash = hashlib.sha256(dummy_zip.read_bytes()).hexdigest()

    fake_fab_res = {
        "success": True,
        "fab": "jlcpcb",
        "zip_path": str(dummy_zip),
        "zip_files": ["board-F_Cu.gbr", "board.drl"],
        "waived": ["parts"],
    }

    with patch("integrations.adapters.copper_kicad_adapter.CopperKiCadAdapter.export_fab", return_value=fake_fab_res) as mock_fab:
        res = service.export_fab_pack(pcb_path, profile="jlc", auto_route=False)
        assert res["success"] is True
        assert res["fab"] == "jlcpcb"
        assert res["sha256"] == expected_hash
        # Verify profile normalization: "jlc" was converted to "jlcpcb"
        mock_fab.assert_called_once_with(
            pcb_path=pcb_path.resolve(),
            profile="jlcpcb",
            waive=["parts"],
        )


def test_download_gerbers_and_pcb_preview_detection(tmp_path):
    """Verifies download_gerbers RPC returns valid base64 data URI and PCB preview detects Gerber package."""
    import base64
    controller, studio, product, core_rev, design, pcb_dir = _create_test_environment(tmp_path)

    pcb_path = pcb_dir / "board.kicad_pcb"
    pcb_path.write_text("(kicad_pcb (segment (start 0 0) (end 10 10) (width 0.4) (layer F.Cu) (net 1)))", encoding="utf-8")

    def fake_export_gerbers(board, **kwargs):
        out_dir = board.parent / "gerbers"
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "board-F_Cu.gbr").write_bytes(b"G04 Copper Top*")
        return out_dir

    def fake_export_drill(board, **kwargs):
        out_dir = board.parent / "gerbers"
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "board.drl").write_bytes(b"M48 Drill*")
        return out_dir

    desktop = DesktopService(studio)

    # 1. Initially no gerbers exist
    preview_before = desktop.cad_preview(CADPreviewQuery(revision_id=core_rev.revision_id, kind="pcb"))
    assert preview_before["available"] is True
    assert preview_before["has_gerbers"] is False

    # 2. Export Gerbers
    with patch.object(KiCadLifecycleService, "export_gerbers", side_effect=fake_export_gerbers), \
         patch.object(KiCadLifecycleService, "export_drill", side_effect=fake_export_drill):
        export_res = desktop.export_gerbers(GerberExportQuery(revision_id=core_rev.revision_id, auto_route=False, check_drc=False))

    assert export_res["success"] is True
    assert "data_uri" in export_res
    assert export_res["data_uri"].startswith("data:application/zip;base64,")

    # 3. Preview now detects Gerbers
    preview_after = desktop.cad_preview(CADPreviewQuery(revision_id=core_rev.revision_id, kind="pcb"))
    assert preview_after["has_gerbers"] is True
    assert preview_after["gerber_filename"] == "board_gerbers.zip"
    assert preview_after["gerber_bytes"] > 0
    assert preview_after["gerber_sha256"] == export_res["sha256"]

    # 4. Download Gerbers RPC
    from mendex_core.desktop.models import GerberDownloadQuery
    download_res = desktop.download_gerbers(GerberDownloadQuery(revision_id=core_rev.revision_id))
    assert download_res["success"] is True
    assert download_res["filename"] == "board_gerbers.zip"
    assert download_res["sha256"] == export_res["sha256"]
    assert download_res["size_bytes"] == preview_after["gerber_bytes"]
    assert download_res["data_uri"].startswith("data:application/zip;base64,")

    # Decode and verify exact SHA-256 match
    raw_b64 = download_res["data_uri"].split(",", 1)[1]
    decoded_bytes = base64.b64decode(raw_b64)
    assert hashlib.sha256(decoded_bytes).hexdigest() == download_res["sha256"]


def test_export_fab_pack_auto_ingests_into_design(tmp_path):
    """Verifies KiCadLifecycleService.export_fab_pack automatically ingests artifact into EngineeringDesign when service is attached."""
    controller, studio, product, core_rev, design, pcb_dir = _create_test_environment(tmp_path)

    pcb_path = pcb_dir / "board.kicad_pcb"
    pcb_path.write_text("(kicad_pcb (segment (start 0 0) (end 10 10) (width 0.4) (layer F.Cu) (net 1)))", encoding="utf-8")

    dummy_zip = pcb_dir / "board_jlcpcb.zip"
    dummy_zip.write_bytes(b"PK\x03\x04JLCPCB FAB PACK CONTENT")
    expected_hash = hashlib.sha256(dummy_zip.read_bytes()).hexdigest()

    fake_fab_res = {
        "success": True,
        "fab": "jlcpcb",
        "zip_path": str(dummy_zip),
        "zip_files": ["board-F_Cu.gbr", "board.drl"],
        "waived": ["parts"],
    }

    # Pass service to KiCadLifecycleService
    lifecycle_kicad = KiCadLifecycleService(service=studio)

    with patch("integrations.adapters.copper_kicad_adapter.CopperKiCadAdapter.export_fab", return_value=fake_fab_res):
        res = lifecycle_kicad.export_fab_pack(pcb_path, profile="jlcpcb", auto_route=False)

    assert res["success"] is True
    assert res["sha256"] == expected_hash

    # Verify auto-ingestion into EngineeringDesign
    persisted_design = studio.design.get_design(design.id)
    active_rev = persisted_design.get_active_revision()
    fab_artifacts = [a for a in active_rev.artifacts if a.kind == ArtifactKind.GERBER_BUNDLE]
    assert len(fab_artifacts) == 1
    art = fab_artifacts[0]
    assert art.sha256 == expected_hash
    assert art.name == "board_jlcpcb.zip"
    assert "JLCPCB" in art.edit_provenance
