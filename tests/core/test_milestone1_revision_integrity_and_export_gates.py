"""Milestone 1 Verification Test Suite: Revision Integrity, Mutator Freeze Gates, Design Isolation, and Export Gates.

Addresses G01, G03, and G20:
- Immutable freeze gates on all DesktopService and core CAD mutators.
- Verification that native adapters are never invoked on archived/in_review revisions.
- Absolute preservation of workspace baselines and SHA-256 hashes.
- Design-to-revision isolation preventing cross-revision design leakage or mutation.
- Removal of force=True bypass in manufacturing export gates.
- Truthful propagation of routing completeness and DRC error metrics.
- Read-only preview caches outside frozen revision baselines.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4
import pytest

from mendex_core.controller import MendexEngineeringController
from mendex_core.design.ir import DesignIntermediateRepresentation
from mendex_core.design.models import (
    ArtifactKind,
    DesignArtifact,
    DesignRevision,
    DesignStatus,
    EngineeringDesign,
)
from mendex_core.desktop.models import (
    AutoRouteQuery,
    CADPreviewQuery,
    CandidateSelectQuery,
    ForwardAnnotatePcbQuery,
    FourLayerPlanesQuery,
    GerberExportQuery,
    IsolationSlotQuery,
    ProjectQuery,
    SchematicApplyQuery,
    STEPExportQuery,
    TopologySynthesizeQuery,
)
from mendex_core.desktop.service import DesktopService, _ingest_design_artifact
from mendex_core.lifecycle.kicad_service import KiCadLifecycleService
from mendex_core.models import Lifecycle
from mendex_core.service import StudioError


def _hash_directory(dir_path: Path) -> dict[str, str]:
    hashes = {}
    if not dir_path.exists():
        return hashes
    for p in sorted(dir_path.rglob("*")):
        if p.is_file():
            hashes[str(p.relative_to(dir_path))] = hashlib.sha256(p.read_bytes()).hexdigest()
    return hashes


def test_frozen_revision_rejects_all_mutators_before_adapter_execution(tmp_path):
    """G01 Acceptance Test: Verify every native mutator rejects frozen revisions before any adapter is called."""
    controller = MendexEngineeringController(tmp_path)
    proj = controller.create_project("Frozen Project", code="FRZ", auto_enroll=True)
    studio = controller.service
    product = studio.get_product(proj["project_id"])
    rev = studio.get_revision(product.active_revision_id)
    ws_dir = studio.workspace_path(rev)
    pcb_dir = ws_dir / "pcb"
    pcb_dir.mkdir(parents=True, exist_ok=True)

    # Place dummy kicad_pcb and kicad_sch
    (pcb_dir / "board.kicad_pcb").write_text("(kicad_pcb (version 20240108))", encoding="utf-8")
    (pcb_dir / "board.kicad_sch").write_text("(kicad_sch (version 20240108))", encoding="utf-8")

    # Creating a new revision archives the old baseline
    new_rev = studio.create_revision(product.product_id, "R002")
    frozen_rev = studio.get_revision(rev.revision_id)
    assert getattr(frozen_rev.lifecycle_status, "value", frozen_rev.lifecycle_status) == "archived"

    baseline_hashes = _hash_directory(ws_dir)
    desktop = DesktopService(studio)

    # 1. auto_route_pcb must raise IMMUTABLE before calling Copper
    with patch("integrations.adapters.copper_kicad_adapter.CopperKiCadAdapter.route_pcb") as mock_route:
        with pytest.raises(StudioError) as exc_info:
            desktop.auto_route_pcb(AutoRouteQuery(revision_id=rev.revision_id))
        assert exc_info.value.code == "IMMUTABLE"
        mock_route.assert_not_called()

    # 2. mill_isolation_slot must raise IMMUTABLE before calling Copper
    with patch("integrations.adapters.copper_kicad_adapter.CopperKiCadAdapter.mill_isolation_slot") as mock_mill:
        with pytest.raises(StudioError) as exc_info:
            desktop.mill_isolation_slot(IsolationSlotQuery(revision_id=rev.revision_id))
        assert exc_info.value.code == "IMMUTABLE"
        mock_mill.assert_not_called()

    # 3. setup_4layer_planes must raise IMMUTABLE before calling Copper
    with patch("integrations.adapters.copper_kicad_adapter.CopperKiCadAdapter.setup_four_layer_power_planes") as mock_planes:
        with pytest.raises(StudioError) as exc_info:
            desktop.setup_4layer_planes(FourLayerPlanesQuery(revision_id=rev.revision_id))
        assert exc_info.value.code == "IMMUTABLE"
        mock_planes.assert_not_called()

    # 4. apply_schematic must raise IMMUTABLE before calling KiCadLifecycleService / Copper
    with patch("mendex_core.lifecycle.kicad_service.KiCadLifecycleService.apply_schematic") as mock_sch:
        with pytest.raises(StudioError) as exc_info:
            desktop.apply_schematic(SchematicApplyQuery(revision_id=rev.revision_id, ops=[]))
        assert exc_info.value.code == "IMMUTABLE"
        mock_sch.assert_not_called()

    # 5. forward_annotate_pcb must raise IMMUTABLE before calling Copper ECO
    with patch("integrations.adapters.copper_kicad_adapter.CopperKiCadAdapter.forward_annotate_pcb") as mock_eco:
        with pytest.raises(StudioError) as exc_info:
            desktop.forward_annotate_pcb(ForwardAnnotatePcbQuery(revision_id=rev.revision_id))
        assert exc_info.value.code == "IMMUTABLE"
        mock_eco.assert_not_called()

    # 6. export_gerbers must raise IMMUTABLE before calling KiCad CLI
    with patch("mendex_core.lifecycle.kicad_service.KiCadLifecycleService.export_gerbers") as mock_gerber:
        with pytest.raises(StudioError) as exc_info:
            desktop.export_gerbers(GerberExportQuery(revision_id=rev.revision_id))
        assert exc_info.value.code == "IMMUTABLE"
        mock_gerber.assert_not_called()

    # 7. export_cad_step must raise IMMUTABLE before calling KiCad export
    with patch("mendex_core.lifecycle.kicad_service.KiCadLifecycleService.export_step") as mock_step:
        with pytest.raises(StudioError) as exc_info:
            desktop.export_cad_step(STEPExportQuery(revision_id=rev.revision_id))
        assert exc_info.value.code == "IMMUTABLE"
        mock_step.assert_not_called()

    # 8. synthesize_topologies must raise IMMUTABLE
    with pytest.raises(StudioError) as exc_info:
        desktop.synthesize_topologies(TopologySynthesizeQuery(revision_id=rev.revision_id))
    assert exc_info.value.code == "IMMUTABLE"

    # 9. select_candidate must raise IMMUTABLE
    with pytest.raises(StudioError) as exc_info:
        desktop.select_candidate(CandidateSelectQuery(revision_id=rev.revision_id, candidate_id="buck"))
    assert exc_info.value.code == "IMMUTABLE"

    # 10. _ingest_design_artifact must raise IMMUTABLE
    dummy_file = tmp_path / "artifact.zip"
    dummy_file.write_bytes(b"PK000")
    with pytest.raises(StudioError) as exc_info:
        _ingest_design_artifact(studio, frozen_rev, ArtifactKind.GERBER_BUNDLE, dummy_file, "art.zip", "zip", "test")
    assert exc_info.value.code == "IMMUTABLE"

    # Workspace directory must remain 100% byte-for-byte identical to baseline
    after_hashes = _hash_directory(ws_dir)
    assert baseline_hashes == after_hashes, "Frozen revision workspace was mutated by rejected operations!"


def test_cad_preview_on_archived_revision_writes_to_cache_outside_workspace(tmp_path):
    """G01 Acceptance Test: cad_preview on archived revision does not pollute the frozen revision folder."""
    controller = MendexEngineeringController(tmp_path)
    proj = controller.create_project("Preview Proj", code="PREV", auto_enroll=True)
    studio = controller.service
    product = studio.get_product(proj["project_id"])
    rev = studio.get_revision(product.active_revision_id)
    ws_dir = studio.workspace_path(rev)
    pcb_dir = ws_dir / "pcb"
    pcb_dir.mkdir(parents=True, exist_ok=True)
    (pcb_dir / "board.kicad_pcb").write_text("(kicad_pcb)", encoding="utf-8")

    # Archive rev
    studio.create_revision(product.product_id, "R002")
    baseline_hashes = _hash_directory(ws_dir)

    desktop = DesktopService(studio)
    dummy_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"

    def fake_render(board_file, output_png, **kwargs):
        Path(output_png).write_bytes(dummy_png)
        return output_png

    with patch("integrations.adapters.copper_kicad_adapter.CopperKiCadAdapter.render_3d", side_effect=fake_render):
        res = desktop.cad_preview(CADPreviewQuery(revision_id=rev.revision_id, kind="3d"))

    assert res["available"] is True
    # The render must NOT have been written inside the workspace directory!
    assert not (pcb_dir / "board_3d_render.png").exists()
    # It must have been written in the external preview cache
    cache_png = studio.root / ".mendex" / "previews" / str(rev.revision_id) / "board_3d_render.png"
    assert cache_png.exists()

    # Workspace directory must remain 100% identical
    assert _hash_directory(ws_dir) == baseline_hashes


def test_design_revision_isolation_strictness(tmp_path):
    """G01/G20 Acceptance Test: designs must match explicit product_id AND core_revision_id."""
    controller = MendexEngineeringController(tmp_path)
    a = controller.create_project("Proj A", code="PA", auto_enroll=True)
    b = controller.create_project("Proj B", code="PB", auto_enroll=True)
    studio = controller.service
    pa = studio.get_product(a["project_id"])
    pb = studio.get_product(b["project_id"])
    reva = studio.get_revision(pa.active_revision_id)

    # 1. Linked design explicitly matching both product_id and reva.revision_id
    da = EngineeringDesign(
        workspace_id=str(pa.product_id),
        product_id=str(pa.product_id),
        core_revision_id=str(reva.revision_id),
        title="Design Linked to Rev A",
        category="pcb",
    )
    rev_da = DesignRevision(
        design_id=da.id,
        revision_index=1,
        label="DRev 1",
        ir=DesignIntermediateRepresentation(design_id=da.id, name="Test Circuit A"),
    )
    da.revisions.append(rev_da)
    da.active_revision_id = rev_da.id
    studio.design._persist(da)

    # 2. Design with same product_id but None core_revision_id (legacy unassigned)
    da_unassigned = EngineeringDesign(
        workspace_id=str(pa.product_id),
        product_id=str(pa.product_id),
        core_revision_id=None,
        title="Unassigned Legacy Design",
        category="pcb",
    )
    rev_unassigned = DesignRevision(
        design_id=da_unassigned.id,
        revision_index=1,
        label="DRev Legacy",
        ir=DesignIntermediateRepresentation(design_id=da_unassigned.id, name="Test Circuit Legacy"),
    )
    da_unassigned.revisions.append(rev_unassigned)
    da_unassigned.active_revision_id = rev_unassigned.id
    studio.design._persist(da_unassigned)

    # 3. Design belonging to another product
    db = EngineeringDesign(
        workspace_id=str(pb.product_id),
        product_id=str(pb.product_id),
        core_revision_id=str(pb.active_revision_id),
        title="Design of Project B",
        category="pcb",
    )
    rev_db = DesignRevision(
        design_id=db.id,
        revision_index=1,
        label="DRev B",
        ir=DesignIntermediateRepresentation(design_id=db.id, name="Test Circuit B"),
    )
    db.revisions.append(rev_db)
    db.active_revision_id = rev_db.id
    studio.design._persist(db)

    desktop = DesktopService(studio)
    view = desktop.project(ProjectQuery(project_id=pa.product_id, revision_id=reva.revision_id))
    # Must only contain da.id, NEVER da_unassigned.id or db.id!
    assert [d["id"] for d in view["designs"]] == [da.id]

    # Ingesting an artifact into reva must only update da, NOT da_unassigned or db!
    test_art_path = tmp_path / "test_gerber.zip"
    test_art_path.write_bytes(b"PK000_sample")
    _ingest_design_artifact(studio, reva, ArtifactKind.GERBER_BUNDLE, test_art_path, "test.zip", "zip", "provenance")

    da_reloaded = studio.design.get_design(da.id)
    da_unassigned_reloaded = studio.design.get_design(da_unassigned.id)
    db_reloaded = studio.design.get_design(db.id)

    assert len(da_reloaded.get_active_revision().artifacts) == 1
    assert len(da_unassigned_reloaded.get_active_revision().artifacts) == 0
    assert len(db_reloaded.get_active_revision().artifacts) == 0


def test_gerber_export_gate_blocks_failing_and_unrouted_boards(tmp_path):
    """G03 Acceptance Test: export_gerbers fails truthfully without hidden force=True bypass."""
    controller = MendexEngineeringController(tmp_path)
    proj = controller.create_project("Gate Project", code="GATE", auto_enroll=True)
    studio = controller.service
    product = studio.get_product(proj["project_id"])
    rev = studio.get_revision(product.active_revision_id)
    ws_dir = studio.workspace_path(rev)
    pcb_dir = ws_dir / "pcb"
    pcb_dir.mkdir(parents=True, exist_ok=True)

    desktop = DesktopService(studio)

    # Case 1: Unrouted board (0 tracks)
    unrouted_pcb = """(kicad_pcb
  (version 20240108)
  (general (thickness 1.6))
  (gr_rect (start 0 0) (end 50 50) (layer "Edge.Cuts"))
  (footprint "Resistor_SMD:R_0805_2012Metric" (at 10 10) (pad "1" smd roundrect (at 0 0) (size 1 1)))
)"""
    (pcb_dir / "board.kicad_pcb").write_text(unrouted_pcb, encoding="utf-8")

    res = desktop.export_gerbers(GerberExportQuery(revision_id=rev.revision_id, auto_route=False))
    assert res["success"] is False
    assert "board has 0 routed copper tracks" in res["error"]

    # Case 2: DRC failure must block export when check_drc=True
    routed_pcb = """(kicad_pcb
  (version 20240108)
  (general (thickness 1.6))
  (gr_rect (start 0 0) (end 50 50) (layer "Edge.Cuts"))
  (segment (start 10 10) (end 20 20) (width 0.5) (layer "F.Cu") (net 0))
)"""
    (pcb_dir / "board.kicad_pcb").write_text(routed_pcb, encoding="utf-8")

    fake_drc_failure = {
        "passed": False,
        "parsed": {"total_issues": 3, "violation_count": 3},
    }
    with patch("mendex_core.lifecycle.kicad_service.KiCadLifecycleService.run_drc", return_value=fake_drc_failure):
        res_drc = desktop.export_gerbers(GerberExportQuery(revision_id=rev.revision_id, auto_route=False, check_drc=True))
        assert res_drc["success"] is False
        assert "DRC failed with 3 issues" in res_drc["error"]


def test_routing_failures_propagate_truthfully_to_desktop(tmp_path):
    """Milestone 1 Acceptance Test: Unrouted nets or DRC errors result in success=False."""
    controller = MendexEngineeringController(tmp_path)
    proj = controller.create_project("Route Truth", code="RTRU", auto_enroll=True)
    studio = controller.service
    product = studio.get_product(proj["project_id"])
    rev = studio.get_revision(product.active_revision_id)
    ws_dir = studio.workspace_path(rev)
    pcb_dir = ws_dir / "pcb"
    pcb_dir.mkdir(parents=True, exist_ok=True)
    (pcb_dir / "board.kicad_pcb").write_text("(kicad_pcb)", encoding="utf-8")

    desktop = DesktopService(studio)

    # Scenario A: router completed some tracks, but 2 nets remain unrouted
    partial_route_res = {
        "routing_completed": False,
        "tracks": 12,
        "vias": 2,
        "unrouted_after": 2,
        "pour_completed": True,
        "drc_errors": 0,
        "drc_warnings": 0,
        "messages": ["2 unrouted nets remain"],
        "netclasses": {},
    }
    with patch("integrations.adapters.copper_kicad_adapter.CopperKiCadAdapter.route_pcb", return_value=partial_route_res):
        res = desktop.auto_route_pcb(AutoRouteQuery(revision_id=rev.revision_id))
        assert res["success"] is False
        assert res["routing_completed"] is False
        assert res["unrouted_after"] == 2

    # Scenario B: router routed 100%, but DRC has 1 violation
    drc_fail_route_res = {
        "routing_completed": True,
        "tracks": 14,
        "vias": 2,
        "unrouted_after": 0,
        "pour_completed": True,
        "drc_errors": 1,
        "drc_warnings": 0,
        "messages": ["Clearance violation"],
        "netclasses": {},
    }
    with patch("integrations.adapters.copper_kicad_adapter.CopperKiCadAdapter.route_pcb", return_value=drc_fail_route_res):
        res = desktop.auto_route_pcb(AutoRouteQuery(revision_id=rev.revision_id))
        assert res["success"] is False
        assert res["drc_errors"] == 1
