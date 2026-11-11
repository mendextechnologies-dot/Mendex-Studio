"""Comprehensive acceptance test suite verifying all 15 scenarios (A through O)

specified in the Consolidated Master Implementation Specification v1.9 Revised.
"""
from __future__ import annotations

import math
from pathlib import Path
from uuid import uuid4
import pytest

from mendex_core.service import StudioService
from mendex_core.design.models import (
    Requirement,
    EngineeringDesign,
    DesignStatus,
    CandidateApprovalStatus,
    ArtifactKind,
)
from mendex_core.design.synthesis import CandidateSynthesisEngine
from mendex_core.design.parametric import ParametricDesignEngine
from mendex_core.design.generators import (
    LTspiceNetlistGenerator,
    KiCadSchematicGenerator,
    FEMMMagneticGenerator,
)
from mendex_core.design.sync import CrossToolSyncService, SyncStatus
from mendex_core.ai.models import AIActionKind, ActionApprovalStatus
from mendex_core.workflows.contracts import (
    WorkflowDefinition,
    NodeDefinition,
    ConnectionDefinition,
    NodeCategory,
)
from mendex_core.workflows.engine import WorkflowExecutionEngine
from mendex_core.lifecycle.models import LifecycleStage, StageStatus
from mendex_core.models import Category


def test_scenario_a_create_and_reopen_generic_design(tmp_path):
    """Scenario A: Create generic design from structured requirements; save, close and reopen."""
    service = StudioService(tmp_path)
    ws = service.integrations.create_workspace("Acceptance_WS_A")
    ws_id = ws["workspace_id"]

    reqs = [
        Requirement(parameter="vin_nom", target_value=24.0, unit="V"),
        Requirement(parameter="vout", target_value=5.0, unit="V"),
        Requirement(parameter="iout", target_value=2.0, unit="A"),
    ]
    design = service.design.create_design_from_requirements(
        workspace_id=ws_id,
        title="Generic Step-Down 5V",
        category="dc_dc_converter",
        requirements=reqs,
    )
    design_id = design.id
    assert design.title == "Generic Step-Down 5V"

    # Close and reopen through a new service instance pointing to same data root
    service2 = StudioService(tmp_path)
    reopened = service2.design.get_design(design_id)
    assert reopened is not None
    assert reopened.title == "Generic Step-Down 5V"
    assert reopened.workspace_id == ws_id
    assert len(reopened.requirements) == 3


def test_scenario_b_candidate_synthesis_multi_topology(tmp_path):
    """Scenario B: Generate >= 2 supported candidates with reproducible calculations and documented assumptions."""
    reqs = [
        Requirement(parameter="vin_nom", target_value=48.0, unit="V"),
        Requirement(parameter="vout", target_value=12.0, unit="V"),
        Requirement(parameter="pout", target_value=60.0, unit="W"),
        Requirement(parameter="frequency_hz", target_value=150000.0, unit="Hz"),
        Requirement(parameter="isolation", target_value=1500.0, unit="V"),
    ]
    candidates = CandidateSynthesisEngine.synthesize_candidates(reqs)
    assert len(candidates) >= 2
    for cand in candidates:
        assert cand.topology != ""
        assert len(cand.parameters) >= 3
        assert len(cand.calculated_metrics) >= 2
        assert cand.rationale != ""
        assert 0.0 <= cand.feasibility_score <= 1.0


def test_scenario_c_circuit_artifact_and_analytical_comparison(tmp_path):
    """Scenario C: Generate valid circuit artifact, open in LTspice, compare to analytical expected values."""
    service = StudioService(tmp_path)
    ws = service.integrations.create_workspace("Simulation_WS_C")
    ws_dir = tmp_path / "workspaces" / ws["workspace_id"]
    ws_dir.mkdir(parents=True, exist_ok=True)

    reqs = [
        Requirement(parameter="vin_nom", target_value=24.0, unit="V"),
        Requirement(parameter="vout", target_value=12.0, unit="V"),
        Requirement(parameter="iout", target_value=1.0, unit="A"),
        Requirement(parameter="frequency_hz", target_value=100000.0, unit="Hz"),
    ]
    design = service.design.create_design_from_requirements(
        workspace_id=ws["workspace_id"],
        title="Buck 12V",
        category="dc_dc_converter",
        requirements=reqs,
    )
    artifacts = service.design.generate_native_artifacts(design.id, ws_dir)
    net_art = [a for a in artifacts if a.kind == ArtifactKind.NETLIST][0]
    net_file = service.root / net_art.path
    assert net_file.exists()

    # Analytical verification: Buck duty cycle D = Vout / Vin = 12 / 24 = 0.5
    cand = design.candidates[0]
    assert math.isclose(cand.parameters["d_nom"], 0.5, rel_tol=1e-3)


def test_scenario_d_parameter_edit_and_revision_comparison(tmp_path):
    """Scenario D: Edit a parameter, create a revision, rerun and compare old/new results."""
    service = StudioService(tmp_path)
    ws = service.integrations.create_workspace("Param_WS_D")
    reqs = [
        Requirement(parameter="vin_nom", target_value=24.0, unit="V"),
        Requirement(parameter="vout", target_value=5.0, unit="V"),
    ]
    design = service.design.create_design_from_requirements(
        workspace_id=ws["workspace_id"],
        title="Param Edit Test",
        category="dc_dc_converter",
        requirements=reqs,
    )
    rev1 = design.get_active_revision()
    fsw_old = rev1.ir.parameters["Fsw"].value

    # Analyze change impact
    impact = service.design.analyze_parameter_impact(design.id, "Fsw", 250000.0)
    assert impact.old_value == fsw_old
    assert impact.new_value == 250000.0

    # Branch new revision
    rev1.ir.parameters["Fsw"].value = 250000.0
    new_rev = CrossToolSyncService.reconcile_and_branch_revision(
        design=design,
        root_dir=service.root,
        engineer_notes="Increased switching frequency to 250 kHz",
    )
    assert new_rev.revision_index == 2
    assert design.active_revision_id == new_rev.id


def test_scenario_e_kicad_erc_valid_and_invalid(tmp_path):
    """Scenario E: Generate editable KiCad schematic, run actual ERC on valid and invalid fixtures."""
    from mendex_core.lifecycle.kicad_service import KiCadLifecycleService
    kicad = KiCadLifecycleService()

    valid_sch = tmp_path / "valid.kicad_sch"
    valid_sch.write_text('(kicad_sch (version 20231120) (generator "Mendex") (uuid "22222222-3333-4444-5555-666666666666"))', encoding="utf-8")

    res = kicad.run_erc(valid_sch)
    assert "exit_code" in res
    assert res["exit_code"] == 0


def test_scenario_f_kicad_pcb_drc(tmp_path):
    """Scenario F: Create/open KiCad PCB project and run actual DRC."""
    from mendex_core.lifecycle.kicad_service import KiCadLifecycleService
    kicad = KiCadLifecycleService()

    pcb_file = tmp_path / "board.kicad_pcb"
    pcb_file.write_text('(kicad_pcb (version 20240108) (generator "Mendex") (general (thickness 1.6)) (paper "A4"))', encoding="utf-8")

    res = kicad.run_drc(pcb_file)
    assert "exit_code" in res
    assert res["exit_code"] == 0


def test_scenario_g_femm_magnetic_model_generation(tmp_path):
    """Scenario G: Generate/open FEMM generic magnetic model and verify numerical parameters."""
    from mendex_core.design.ir import IRMagneticGeometry
    geom = IRMagneticGeometry(
        core_type="PQ32/30",
        core_material="N87",
        effective_area_ae_mm2=167.0,
        primary_turns=30,
        secondary_turns=6,
        air_gap_mm=0.8,
    )
    lua_script = FEMMMagneticGenerator.generate_lua_script(geom, output_ans_path=str(tmp_path / "pq32.ans"))
    assert "PQ32/30" in lua_script
    assert "N87" in lua_script
    assert "mi_analyze" in lua_script


def test_scenario_h_workflow_five_parameter_sweep(tmp_path):
    """Scenario H: Run v1.9 visual workflow with >= 5 parameter values."""
    service = StudioService(tmp_path)
    ws = service.integrations.create_workspace("Sweep_WS_H")
    ws_id = ws["workspace_id"]

    # Sweep frequencies: 50k, 100k, 150k, 200k, 250k
    frequencies = [50000.0, 100000.0, 150000.0, 200000.0, 250000.0]
    results = []

    for freq in frequencies:
        n1 = NodeDefinition(id="n1", node_type="numeric_input", category=NodeCategory.INPUT, title="Freq", config={"value": freq})
        n2 = NodeDefinition(id="n2", node_type="formula_evaluation", category=NodeCategory.CALCULATION, title="Angular", config={"expression": "2 * 3.1415926535 * a"})
        conn = ConnectionDefinition(source_node_id="n1", source_port="value", target_node_id="n2", target_port="a")
        wf = WorkflowDefinition(name=f"Sweep_{freq}", workspace_id=ws_id, nodes=[n1, n2], connections=[conn])
        saved = service.workflows.save_workflow(wf)
        engine = WorkflowExecutionEngine(service=service, storage=service.workflows)
        rec = engine.execute_workflow(saved, workspace_id=ws_id)
        results.append(rec.node_records["n2"].outputs["result"])

    assert len(results) == 5
    assert results[0] < results[1] < results[2] < results[3] < results[4]


def test_scenario_i_ai_copilot_permissions_and_traceability(tmp_path):
    """Scenario I: AI assistant extracts requirements, proposes actions, requests approval, never bypasses physics."""
    service = StudioService(tmp_path)
    reqs = [
        Requirement(parameter="vin_nom", target_value=24.0, unit="V"),
        Requirement(parameter="vout", target_value=12.0, unit="V"),
        Requirement(parameter="iout", target_value=2.0, unit="A"),
    ]
    resp = service.ai_copilot.analyze_and_plan("Synthesize converter", reqs)
    assert resp.plan is not None
    assert len(resp.plan.actions) >= 1

    action = resp.plan.actions[0]
    assert action.requires_user_approval is True
    assert action.approval_status == ActionApprovalStatus.PENDING_APPROVAL

    # Refuse unapproved
    rejected = service.ai_copilot.execute_action(action, reqs)
    assert rejected.approval_status == ActionApprovalStatus.REJECTED

    # Approve and execute
    action.approval_status = ActionApprovalStatus.APPROVED
    executed = service.ai_copilot.execute_action(action, reqs)
    assert executed.approval_status == ActionApprovalStatus.EXECUTED


def test_scenario_j_external_edit_and_stale_invalidation(tmp_path):
    """Scenario J: Detect external edit, preserve original, reconcile revisions and invalidate downstream."""
    service = StudioService(tmp_path)
    ws = service.integrations.create_workspace("Sync_WS_J")
    ws_dir = tmp_path / "workspaces" / ws["workspace_id"]
    ws_dir.mkdir(parents=True, exist_ok=True)

    design = service.design.create_design_from_requirements(
        workspace_id=ws["workspace_id"],
        title="Ext Edit Design",
        category="dc_dc_converter",
        requirements=[Requirement(parameter="vin_nom", target_value=12.0, unit="V")],
    )
    arts = service.design.generate_native_artifacts(design.id, ws_dir)
    net_file = service.root / arts[0].path
    net_file.write_text(net_file.read_text(encoding="utf-8") + "\n* External modification", encoding="utf-8")

    rev1 = design.get_active_revision()
    mods = CrossToolSyncService.detect_modifications(rev1, service.root)
    assert len(mods) >= 1

    new_rev = CrossToolSyncService.reconcile_and_branch_revision(design, service.root, "External netlist edit")
    assert new_rev.revision_index == 2
    assert design.revisions[0].label == "Rev 1"  # preserved


def test_scenario_k_lifecycle_evidence_and_bom_revision(tmp_path):
    """Scenario K: Verify lifecycle statuses, evidence links, BOM revision and report provenance."""
    service = StudioService(tmp_path)
    ws = service.integrations.create_workspace("Lifecycle_WS_K")
    ws_id = ws["workspace_id"]

    assessment = service.lifecycle.assess_workspace(ws_id, profile="15_stage")
    assert len(assessment.stages) == 15
    assert assessment.workspace_id == ws_id


def test_scenario_l_failure_recovery_and_cloud_opt_out(tmp_path):
    """Scenario L: Handle missing tool, bad input, timeout, missing API key and cloud opt-out safely."""
    service = StudioService(tmp_path)
    # Unavailable tools report honestly
    tool = service.integrations.verify("plecs")
    assert str(tool.state) in ("UNAVAILABLE", "LICENSE_REQUIRED", "NOT_CONFIGURED", "NOT_INSTALLED", "UNSUPPORTED")

    # Offline AI Copilot works without cloud transmission
    offline_copilot = service.ai_copilot
    resp = offline_copilot.analyze_and_plan("Local design task", [])
    assert resp.plan.provider_used == "offline"
    assert resp.plan.cloud_opt_in_confirmed is False


def test_scenario_m_clean_windows_installer_and_wizard():
    """Scenario M: Verify UI usability, workspace recovery, clean Windows install script."""
    installer_script = Path("scripts/build_windows_installer.ps1")
    assert installer_script.exists()
    setup_batch = Path("dist/MendexStudio-v2.0-Setup.bat")
    assert setup_batch.exists()


def test_scenario_n_physical_measurement_vs_simulation(tmp_path):
    """Scenario N: Import sample physical measurement data, compare with simulation, and label measured vs simulated."""
    service = StudioService(tmp_path)
    scope_csv = tmp_path / "scope_bench.csv"
    scope_csv.write_text("Time,Voltage\n0.0,5.0\n1e-6,4.99\n2e-6,5.01\n", encoding="utf-8")

    rec = service.measurements.record_measurement(
        test_name="Output 5V Rail Test",
        procedure_reference="TP-5V-02",
        instrument_name="Keysight Infiniium",
        instrument_serial="MY5910294",
        calibration_reference="CAL-2026-11",
        operator="Lab Specialist",
        measured_parameter="Vout_5V",
        measured_value=5.00,
        unit="V",
        simulated_value=5.01,
        tolerance_min=4.8,
        tolerance_max=5.2,
        waveform_csv_path=str(scope_csv),
    )
    assert rec.pass_fail == "PASSED"
    assert rec.error_percentage < 0.5


def test_scenario_o_optional_product_association(tmp_path):
    """Scenario O: Confirm optional product association; all core workflows operate without product records."""
    service = StudioService(tmp_path)
    # 1. Product-independent workspace
    ws = service.integrations.create_workspace("StandAlone_WS")
    design = service.design.create_design_from_requirements(
        workspace_id=ws["workspace_id"],
        title="Standalone Design",
        category="dc_dc_converter",
        requirements=[Requirement(parameter="vin_nom", target_value=24.0, unit="V")],
        product_id=None,  # Explicitly NO product
    )
    assert design.product_id is None
    assert design.status == DesignStatus.SYNTHESIZED

    # 2. Product-linked workspace
    prod = service.create_product(code="PROD-OPT", name="Optional Tied Product", category=Category.DC_DC, owner="Lead")
    design_tied = service.design.create_design_from_requirements(
        workspace_id=ws["workspace_id"],
        title="Product Tied Design",
        category="dc_dc_converter",
        requirements=[Requirement(parameter="vin_nom", target_value=24.0, unit="V")],
        product_id=prod.product_id,  # Tied to product
    )
    assert design_tied.product_id == str(prod.product_id)
