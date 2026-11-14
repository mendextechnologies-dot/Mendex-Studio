"""Unit tests for Milestone 4: Command Center 3D Raytraced Photo View & Interactive Render Trigger."""
from __future__ import annotations

import hashlib
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mendex_core.controller import MendexEngineeringController
from mendex_core.desktop.models import Render3DQuery
from mendex_core.desktop.service import DesktopService
from mendex_core.lifecycle.kicad_service import KiCadLifecycleService


def _setup_test_project(tmp_path: Path):
    controller = MendexEngineeringController(tmp_path)
    proj = controller.create_project("Raytrace Test Project", code="RTP", auto_enroll=True)
    studio = controller.service
    product = studio.get_product(proj["project_id"])
    rev = studio.get_revision(product.active_revision_id)
    ws_dir = studio.workspace_path(rev)
    pcb_dir = ws_dir / "pcb"
    pcb_dir.mkdir(parents=True, exist_ok=True)

    # Sample board file
    pcb_file = pcb_dir / "board.kicad_pcb"
    pcb_file.write_text("""(kicad_pcb (version 20240108) (general (thickness 1.6))
      (gr_rect (start 10 10) (end 60 40) (stroke (width 0.15) (type solid)) (layer "Edge.Cuts"))
      (segment (start 15 15) (end 25 25) (width 0.5) (layer "F.Cu") (net 1))
    )""", encoding="utf-8")

    return controller, studio, product, rev, pcb_dir, pcb_file


def test_render_3d_pcb_rpc_success(tmp_path):
    controller, studio, product, rev, pcb_dir, pcb_file = _setup_test_project(tmp_path)

    dummy_png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    expected_sha = hashlib.sha256(dummy_png_bytes).hexdigest()

    def fake_render_3d(pcb_path, output_png=None, view="iso", width=1200, height=900):
        out_png = output_png or (pcb_path.parent / f"board_3d_{view}.png")
        out_png.write_bytes(dummy_png_bytes)
        return out_png

    desktop = DesktopService(studio)

    with patch.object(KiCadLifecycleService, "is_available", return_value=True), \
         patch.object(KiCadLifecycleService, "render_3d", side_effect=fake_render_3d):
        res = desktop.dispatch("render_3d_pcb", {
            "revision_id": str(rev.revision_id),
            "view": "iso",
            "width": 1400,
            "height": 1050,
        })

    assert res["success"] is True
    assert res["available"] is True
    assert res["view"] == "iso"
    assert res["filename"] == "board.kicad_pcb"
    assert res["width"] == 1400
    assert res["height"] == 1050
    assert res["render_bytes"] == len(dummy_png_bytes)
    assert res["sha256"] == expected_sha
    assert res["render_image"].startswith("data:image/png;base64,")
    assert "Isometric Perspective" in res["title"]


def test_render_3d_pcb_all_angles(tmp_path):
    controller, studio, product, rev, pcb_dir, pcb_file = _setup_test_project(tmp_path)

    dummy_png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"

    def fake_render_3d(pcb_path, output_png=None, view="iso", width=1200, height=900):
        out_png = output_png or (pcb_path.parent / f"board_3d_{view}.png")
        out_png.write_bytes(dummy_png_bytes)
        return out_png

    desktop = DesktopService(studio)

    views = [
        ("top", "Top View (Component Placement)"),
        ("bottom", "Bottom View (Solder / Ground Plane)"),
        ("iso_bottom", "Isometric Underside View"),
    ]

    with patch.object(KiCadLifecycleService, "is_available", return_value=True), \
         patch.object(KiCadLifecycleService, "render_3d", side_effect=fake_render_3d):
        for v, expected_title_part in views:
            res = desktop.render_3d_pcb(Render3DQuery(
                revision_id=rev.revision_id,
                view=v,
                width=1600,
                height=1200,
            ))
            assert res["success"] is True
            assert res["view"] == v
            assert expected_title_part in res["title"]


def test_render_3d_pcb_no_pcb_file(tmp_path):
    controller = MendexEngineeringController(tmp_path)
    proj = controller.create_project("Empty Project", code="EMP", auto_enroll=True)
    studio = controller.service
    product = studio.get_product(proj["project_id"])
    rev = studio.get_revision(product.active_revision_id)

    desktop = DesktopService(studio)
    res = desktop.render_3d_pcb(Render3DQuery(revision_id=rev.revision_id))
    assert res["success"] is False
    assert res["available"] is False
    assert "No .kicad_pcb file found" in res["error"]


def test_render_3d_pcb_with_step_metadata(tmp_path):
    controller, studio, product, rev, pcb_dir, pcb_file = _setup_test_project(tmp_path)

    # Place dummy STEP solid file
    step_file = pcb_dir / "board.step"
    dummy_step_content = b"ISO-10303-21; HEADER; TEST SOLID; ENDSEC;"
    step_file.write_bytes(dummy_step_content)
    expected_step_sha = hashlib.sha256(dummy_step_content).hexdigest()

    dummy_png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"

    def fake_render_3d(pcb_path, output_png=None, view="iso", width=1200, height=900):
        out_png = output_png or (pcb_path.parent / f"board_3d_{view}.png")
        out_png.write_bytes(dummy_png_bytes)
        return out_png

    desktop = DesktopService(studio)

    with patch.object(KiCadLifecycleService, "is_available", return_value=True), \
         patch.object(KiCadLifecycleService, "render_3d", side_effect=fake_render_3d):
        res = desktop.render_3d_pcb(Render3DQuery(revision_id=rev.revision_id, view="iso"))

    assert res["success"] is True
    assert res["has_step"] is True
    assert res["step_filename"] == "board.step"
    assert res["step_bytes"] == len(dummy_step_content)
    assert res["step_sha256"] == expected_step_sha
