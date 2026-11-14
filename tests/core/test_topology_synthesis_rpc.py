"""Unit and integration tests for Topology Synthesizer and Candidate Switcher RPCs."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from mendex_core.controller import MendexEngineeringController
from mendex_core.desktop.service import DesktopService
from mendex_core.models import Specification


def _setup_test_project(tmp_path: Path):
    controller = MendexEngineeringController(tmp_path)
    proj = controller.create_project("Power Synthesis Project", code="PSP", auto_enroll=True)
    studio = controller.service
    product = studio.get_product(proj["project_id"])
    rev = studio.get_revision(product.active_revision_id)

    # Set up realistic electrical specification
    spec = Specification(
        vin_min_v=20.0,
        vin_nom_v=24.0,
        vin_max_v=28.0,
        vout_v=12.0,
        iout_a=10.0,  # 120W -> triggers high-power candidates (PSFB, LLC, etc.)
        switching_frequency_hz=100000.0,
        isolation_requirement="Reinforced 1500V",
    )
    studio.update_specification(rev.revision_id, spec)
    rev = studio.get_revision(rev.revision_id)

    return controller, studio, product, rev


def test_synthesize_topologies_rpc(tmp_path: Path):
    """Verifies that synthesize_topologies RPC synthesizes candidates and persists EngineeringDesign."""
    controller, studio, product, rev = _setup_test_project(tmp_path)
    desktop = DesktopService(studio)

    res = desktop.dispatch("synthesize_topologies", {
        "revision_id": str(rev.revision_id),
    })

    assert res["success"] is True
    assert res["revision_id"] == str(rev.revision_id)
    assert res["count"] >= 3
    candidates = res["candidates"]

    # Check topologies generated for 120W isolated spec
    topologies = [c["topology"] for c in candidates]
    assert any("Phase-Shifted Full-Bridge" in t for t in topologies)
    assert any("LLC Resonant" in t for t in topologies)
    assert any("Flyback" in t for t in topologies)

    # Check candidate metrics and ir_snapshot
    for cand in candidates:
        assert cand["feasibility_score"] > 0
        assert "estimated_efficiency" in cand["calculated_metrics"]
        assert cand["ir_snapshot"] is not None

    # Check that design was persisted in studio
    designs = studio.design.list_designs()
    assert len(designs) >= 1
    d = designs[0]
    assert d.product_id == str(product.product_id)
    assert len(d.candidates) == len(candidates)


def test_select_candidate_rpc(tmp_path: Path):
    """Verifies that select_candidate RPC selects candidate, creates revision, and exports KiCad."""
    controller, studio, product, rev = _setup_test_project(tmp_path)
    desktop = DesktopService(studio)

    # First synthesize
    synth_res = desktop.dispatch("synthesize_topologies", {
        "revision_id": str(rev.revision_id),
    })
    candidates = synth_res["candidates"]
    psfb_cand = next(c for c in candidates if "Phase-Shifted" in c["topology"])

    # Mock export_copper_project for fast unit test
    ws_dir = studio.workspace_path(rev)
    pcb_dir = ws_dir / "pcb"

    def fake_export(ir, target_dir, auto_place=True, layers=2):
        td = Path(target_dir)
        td.mkdir(parents=True, exist_ok=True)
        sch = td / "pcb.kicad_sch"
        pcb = td / "pcb.kicad_pcb"
        sch.write_text("(kicad_sch (version 20240108))", encoding="utf-8")
        pcb.write_text("(kicad_pcb (version 20240108))", encoding="utf-8")
        return {
            "project_dir": str(td),
            "schematic": str(sch),
            "pcb": str(pcb),
            "project": str(td / "pcb.kicad_pro"),
            "ops_applied": 10,
            "erc": {"violations": 0},
            "sync": True,
            "placed": True,
        }

    with patch("mendex_core.design.generators.kicad_generator.KiCadSchematicGenerator.export_copper_project", side_effect=fake_export):
        sel_res = desktop.dispatch("select_candidate", {
            "revision_id": str(rev.revision_id),
            "candidate_id": psfb_cand["id"],
            "auto_export_kicad": True,
        })

    assert sel_res["success"] is True
    assert "Phase-Shifted Full-Bridge" in sel_res["selected_topology"]
    assert sel_res["kicad_exported"] is True
    assert sel_res["kicad_details"]["placed"] is True

    # Verify that the candidate is marked SELECTED in design
    designs = studio.design.list_designs()
    target_d = [d for d in designs if d.product_id == str(product.product_id)][0]
    active_cand = next(c for c in target_d.candidates if c.id == psfb_cand["id"])
    assert active_cand.status.value == "SELECTED"

    # Verify other candidates are marked PROPOSED
    for c in target_d.candidates:
        if c.id != psfb_cand["id"]:
            assert c.status.value == "PROPOSED"

    # Verify new DesignRevision was added
    assert len(target_d.revisions) >= 1
    assert "Phase-Shifted Full-Bridge" in target_d.revisions[-1].label
