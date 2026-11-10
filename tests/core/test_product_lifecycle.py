"""Automated tests for Product Engineering Lifecycle and Verification Framework."""
from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import pytest

from mendex_core.lifecycle.models import (
    ArtifactType,
    LifecycleStage,
    StageStatus,
)
from mendex_core.models import Category, Specification
from mendex_core.service import StudioService


def test_product_lifecycle_12_stages_initialization(tmp_path):
    """Verifies that every product is evaluated across all 12 configurable engineering lifecycle stages."""
    service = StudioService(tmp_path)
    product = service.create_product(
        code="TEST-001",
        name="Precision Converter Test",
        category=Category.DC_DC,
        owner="Test Engineer",
    )

    assessment = service.lifecycle.assess(product.product_id)
    assert assessment.product_code == "TEST-001"
    assert assessment.overall_status in (StageStatus.NOT_STARTED, StageStatus.IN_PROGRESS)
    assert not assessment.prototype_ready
    assert len(assessment.stages) == 12
    assert len(assessment.readiness_gates) == 12

    # Verify all 12 stage names are present
    expected_stages = [
        LifecycleStage.REQUIREMENTS.value,
        LifecycleStage.ELECTRICAL_ARCHITECTURE.value,
        LifecycleStage.CIRCUIT_DESIGN.value,
        LifecycleStage.ELECTRICAL_SIMULATION.value,
        LifecycleStage.MAGNETIC_ANALYSIS.value,
        LifecycleStage.SCHEMATIC_VERIFICATION.value,
        LifecycleStage.PCB_LAYOUT.value,
        LifecycleStage.PCB_DRC.value,
        LifecycleStage.THERMAL_MECHANICAL.value,
        LifecycleStage.BOM_REVIEW.value,
        LifecycleStage.ENGINEERING_VALIDATION.value,
        LifecycleStage.PROTOTYPE_READINESS.value,
    ]
    for stg in expected_stages:
        assert stg in assessment.stages
        assert assessment.stages[stg].category_number >= 1


def test_product_lifecycle_blockers_and_readiness(tmp_path):
    """Verifies that prototype readiness is strictly blocked if mandatory engineering gates are incomplete."""
    service = StudioService(tmp_path)
    product = service.create_product(
        code="HV-PSU",
        name="High Voltage Test Unit",
        category=Category.DC_DC,
        owner="Systems Engineer",
    )

    assessment = service.lifecycle.assess(product.product_id)
    assert not assessment.prototype_ready
    assert assessment.stages[LifecycleStage.PROTOTYPE_READINESS.value].status == StageStatus.BLOCKED
    assert len(assessment.critical_blockers) > 0


def test_product_lifecycle_evidence_register(tmp_path):
    """Verifies unified evidence registration when artifacts are populated in workspace."""
    service = StudioService(tmp_path)
    product = service.create_product(
        code="REG-01",
        name="Evidence Test",
        category=Category.DC_DC,
        owner="Lead Developer",
    )
    rev = service.get_revision(product.active_revision_id)
    ws_path = service.workspace_path(rev)

    # Place a specification document and a circuit netlist
    (ws_path / "requirements").mkdir(parents=True, exist_ok=True)
    (ws_path / "requirements" / "SPEC_01.md").write_text("# Requirements", encoding="utf-8")

    (ws_path / "circuit").mkdir(parents=True, exist_ok=True)
    (ws_path / "circuit" / "circuit.cir").write_text("* SPICE Netlist", encoding="utf-8")

    assessment = service.lifecycle.assess(product.product_id)
    assert assessment.total_evidence_count >= 2

    ev_register = service.lifecycle.get_evidence_register(product.product_id)
    file_names = [e.source_file for e in ev_register]
    assert "SPEC_01.md" in file_names
    assert "circuit.cir" in file_names

    # Check that SHA-256 is populated for both
    for e in ev_register:
        assert len(e.sha256) == 64


def test_product_lifecycle_stage_approval_persistence(tmp_path):
    """Verifies that explicit reviewer approvals are recorded, persistent, and update stage status."""
    service = StudioService(tmp_path)
    product = service.create_product(
        code="APP-01",
        name="Approval Test",
        category=Category.DC_DC,
        owner="Lead Developer",
    )
    rev = service.get_revision(product.active_revision_id)
    ws_path = service.workspace_path(rev)
    (ws_path / "requirements" / "SPEC.md").write_text("# Requirements", encoding="utf-8")

    # Initial assessment: Requirements is PENDING_VERIFICATION or IN_PROGRESS
    initial = service.lifecycle.assess(product.product_id)
    assert initial.stages[LifecycleStage.REQUIREMENTS.value].status != StageStatus.PASSED

    # Record formal sign-off
    service.lifecycle.record_stage_approval(
        revision_id=rev.revision_id,
        stage_id=LifecycleStage.REQUIREMENTS,
        reviewer="Principal Architect",
        passed=True,
        notes="All 24V inputs and 1kV outputs verified against mission spec",
    )

    # Re-assess
    updated = service.lifecycle.assess(product.product_id)
    req_stage = updated.stages[LifecycleStage.REQUIREMENTS.value]
    assert req_stage.status == StageStatus.PASSED
    assert req_stage.reviewer == "Principal Architect"


def test_kicad_service_discovery_and_erc_parser(tmp_path):
    """Verifies KiCad workflow service discovers files and distinguishes missing vs failing ERC."""
    service = StudioService(tmp_path)
    product = service.create_product(
        code="PCB-01",
        name="PCB Verification Test",
        category=Category.PCB,
        owner="CAD Lead",
    )
    rev = service.get_revision(product.active_revision_id)
    ws_path = service.workspace_path(rev)

    # Initially no KiCad files
    files = service.lifecycle.kicad.discover_files(ws_path)
    assert len(files["schematics"]) == 0
    assert len(files["pcbs"]) == 0

    # Add dummy schematic and failing ERC report
    (ws_path / "pcb").mkdir(parents=True, exist_ok=True)
    dummy_sch = ws_path / "pcb" / "board.kicad_sch"
    dummy_sch.write_text("(kicad_sch ...)", encoding="utf-8")

    erc_report = ws_path / "pcb" / "board_erc.json"
    erc_report.write_text(json.dumps({
        "sheets": [
            {"name": "Root", "violations": [{"type": "unconnected_pin", "description": "Pin 1 floating"}]}
        ]
    }), encoding="utf-8")

    assessment = service.lifecycle.assess(product.product_id)
    sch_stage = assessment.stages[LifecycleStage.SCHEMATIC_VERIFICATION.value]
    assert sch_stage.status in (StageStatus.PENDING_VERIFICATION, StageStatus.IN_PROGRESS)
    assert len(sch_stage.evidence_records) >= 2


def test_product_independent_workflows_unaffected(tmp_path):
    """Verifies that standalone Simulation Lab and general workspaces continue working without products."""
    service = StudioService(tmp_path)
    # General workspace with no product_id
    ws = service.integrations.create_workspace("General_Lab", "Product-independent study")
    assert ws["name"] == "General_Lab"
    assert ws.get("product_id") is None

    # Workspace list works cleanly
    workspaces = service.integrations.list_workspaces()
    assert len(workspaces) >= 1
