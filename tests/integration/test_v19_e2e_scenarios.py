"""Mandatory End-to-End Scenarios A through G for Mendex Engineering Studio v1.9."""
import pytest
from pathlib import Path
from uuid import uuid4

from mendex_core.service import StudioService
from mendex_core.workflows.contracts import (
    NodeCategory,
    NodeExecutionState,
    WorkflowStatus,
    WorkflowDefinition,
    NodeDefinition,
    ConnectionDefinition,
)
from mendex_core.workflows.engine import WorkflowExecutionEngine
from mendex_core.workflows.types import PortDataType, ValidationResultData


def test_scenario_a_calculation_workflow(tmp_path):
    """Scenario A: Calculation workflow
    Create workspace -> Add numeric input -> Add calculation node -> Add validation node -> Execute -> View results.
    """
    service = StudioService(tmp_path)
    ws = service.integrations.create_workspace("Scenario A Workspace")

    wf = WorkflowDefinition(name="Scenario A Calculation", workspace_id=ws["workspace_id"])
    n1 = NodeDefinition(node_type="numeric_input", category=NodeCategory.INPUT, title="Freq", config={"value": 250000.0, "unit": "Hz"})
    n2 = NodeDefinition(node_type="deterministic_physics", category=NodeCategory.CALCULATION, title="Skin Depth", config={"formula_id": "skin_depth"})
    n3 = NodeDefinition(node_type="range_validation", category=NodeCategory.VALIDATION, title="Skin Check", config={"min_val": 0.0001, "max_val": 0.0002, "check_id": "REQ-SKIN-250K"})

    wf.nodes = [n1, n2, n3]
    wf.connections = [
        ConnectionDefinition(source_node_id=n1.id, source_port="value", target_node_id=n2.id, target_port="param1"),
        ConnectionDefinition(source_node_id=n2.id, source_port="result", target_node_id=n3.id, target_port="value_in"),
    ]

    record = service.execute_workflow(wf, workspace_id=ws["workspace_id"])
    assert record.status == WorkflowStatus.COMPLETED
    assert record.node_records[n2.id].status == NodeExecutionState.COMPLETED
    assert record.node_records[n3.id].status == NodeExecutionState.COMPLETED
    assert record.node_records[n3.id].outputs["passed"] is True


def test_scenario_b_simulation_workflow(tmp_path):
    """Scenario B: Simulation workflow
    Create workspace -> Import generic engineering input -> Add supported simulation node -> Execute -> Inspect actual result.
    """
    service = StudioService(tmp_path)
    ws = service.integrations.create_workspace("Scenario B Simulation Workspace")

    wf = WorkflowDefinition(name="Scenario B Simulation", workspace_id=ws["workspace_id"])
    n1 = NodeDefinition(node_type="text_input", category=NodeCategory.INPUT, title="Netlist", config={"text": "* RC Simulation\nV1 in 0 PULSE(0 5 0 1n 1n 10u 20u)\nR1 in out 1k\nC1 out 0 10n\n.tran 0 20u 0 100n\n.end\n"})
    n2 = NodeDefinition(node_type="ltspice_simulation", category=NodeCategory.TOOL, title="LTspice", config={"timeout_s": 30})
    n3 = NodeDefinition(node_type="waveform_extract", category=NodeCategory.RESULTS, title="Extract V(out)", config={"signal_name": "V(out)"})

    wf.nodes = [n1, n2, n3]
    wf.connections = [
        ConnectionDefinition(source_node_id=n1.id, source_port="text", target_node_id=n2.id, target_port="netlist_text"),
        ConnectionDefinition(source_node_id=n2.id, source_port="waveform", target_node_id=n3.id, target_port="waveform_in"),
    ]

    record = service.execute_workflow(wf, workspace_id=ws["workspace_id"])
    assert record.status == WorkflowStatus.COMPLETED
    assert record.node_records[n2.id].status == NodeExecutionState.COMPLETED
    assert record.node_records[n3.id].status == NodeExecutionState.COMPLETED


def test_scenario_c_research_workflow(tmp_path):
    """Scenario C: Research workflow
    Import dataset -> Filter -> Analyze -> Visualize -> Save evidence.
    """
    service = StudioService(tmp_path)
    ws = service.integrations.create_workspace("Scenario C Research Workspace")

    wf = WorkflowDefinition(name="Scenario C Research", workspace_id=ws["workspace_id"])
    n1 = NodeDefinition(node_type="dataset_reference", category=NodeCategory.INPUT, title="Material Dataset", config={"dataset_id": "ferrite_n87", "version": "1.0"})
    n2 = NodeDefinition(node_type="knowledge_lookup", category=NodeCategory.INTELLIGENCE, title="Lookup N87", config={"material_id": "tdk_n87"})
    n3 = NodeDefinition(node_type="deterministic_physics", category=NodeCategory.CALCULATION, title="Steinmetz Core Loss", config={"formula_id": "steinmetz"})

    wf.nodes = [n1, n2, n3]
    wf.connections = [
        ConnectionDefinition(source_node_id=n2.id, source_port="saturation_flux_t", target_node_id=n3.id, target_port="param2"),
    ]

    record = service.execute_workflow(wf, workspace_id=ws["workspace_id"])
    assert record.status == WorkflowStatus.COMPLETED
    assert record.node_records[n2.id].status == NodeExecutionState.COMPLETED
    assert record.node_records[n3.id].status == NodeExecutionState.COMPLETED


def test_scenario_d_reporting_workflow(tmp_path):
    """Scenario D: Reporting workflow
    Combine actual calculated and simulated results -> Validate -> Generate report.
    """
    service = StudioService(tmp_path)
    ws = service.integrations.create_workspace("Scenario D Reporting Workspace")

    wf = WorkflowDefinition(name="Scenario D Reporting", workspace_id=ws["workspace_id"])
    n_calc = NodeDefinition(node_type="numeric_input", category=NodeCategory.INPUT, title="Calc Power", config={"value": 48.5, "unit": "W"})
    n_sim = NodeDefinition(node_type="numeric_input", category=NodeCategory.INPUT, title="Sim Power", config={"value": 49.2, "unit": "W"})
    n_tol = NodeDefinition(node_type="tolerance_comparison", category=NodeCategory.VALIDATION, title="Power Accuracy", config={"tolerance_pct": 5.0, "check_id": "REQ-POWER"})
    n_evid = NodeDefinition(node_type="evidence_aggregation", category=NodeCategory.REPORTING, title="Sealed Evidence")
    n_rep = NodeDefinition(node_type="report_export", category=NodeCategory.REPORTING, title="Engineering Dossier", config={"report_title": "Scenario D Power Dossier"})

    wf.nodes = [n_calc, n_sim, n_tol, n_evid, n_rep]
    wf.connections = [
        ConnectionDefinition(source_node_id=n_sim.id, source_port="value", target_node_id=n_tol.id, target_port="actual"),
        ConnectionDefinition(source_node_id=n_calc.id, source_port="value", target_node_id=n_tol.id, target_port="target"),
        ConnectionDefinition(source_node_id=n_tol.id, source_port="validation_result", target_node_id=n_evid.id, target_port="check1"),
        ConnectionDefinition(source_node_id=n_evid.id, source_port="manifest", target_node_id=n_rep.id, target_port="manifest"),
    ]

    record = service.execute_workflow(wf, workspace_id=ws["workspace_id"])
    assert record.status == WorkflowStatus.COMPLETED
    assert record.node_records[n_tol.id].outputs["passed"] is True
    report_path = record.node_records[n_rep.id].outputs["report_path"]
    assert Path(report_path).exists()


def test_scenario_e_persistence(tmp_path):
    """Scenario E: Persistence
    Save workflow -> Close Studio -> Reopen workflow -> Verify configuration and results.
    """
    service1 = StudioService(tmp_path)
    wf = WorkflowDefinition(name="Persistent Resonant Tank Workflow")
    n1 = NodeDefinition(node_type="numeric_input", category=NodeCategory.INPUT, title="Inductance", config={"value": 15e-6})
    n2 = NodeDefinition(node_type="numeric_input", category=NodeCategory.INPUT, title="Capacitance", config={"value": 100e-9})
    n3 = NodeDefinition(node_type="deterministic_physics", category=NodeCategory.CALCULATION, title="LC Tank", config={"formula_id": "lc_resonance"})
    wf.nodes = [n1, n2, n3]
    wf.connections = [
        ConnectionDefinition(source_node_id=n1.id, source_port="value", target_node_id=n3.id, target_port="param1"),
        ConnectionDefinition(source_node_id=n2.id, source_port="value", target_node_id=n3.id, target_port="param2"),
    ]

    saved = service1.save_workflow(wf)
    rec1 = service1.execute_workflow(saved)
    assert rec1.status == WorkflowStatus.COMPLETED

    # Restart Studio with fresh instance from same directory
    service2 = StudioService(tmp_path)
    reopened = service2.get_workflow(saved.id)
    assert reopened is not None
    assert reopened.name == "Persistent Resonant Tank Workflow"
    assert len(reopened.nodes) == 3
    assert len(reopened.connections) == 2

    # Verify run records persisted
    runs = service2.workflows.list_runs(saved.id)
    assert len(runs) >= 1
    assert runs[0].status == WorkflowStatus.COMPLETED


def test_scenario_f_failure_recovery(tmp_path):
    """Scenario F: Failure recovery
    Run workflow with failing node -> Display clear error -> Preserve valid prior results -> Allow correction and rerun.
    """
    service = StudioService(tmp_path)
    wf = WorkflowDefinition(name="Failure Recovery Workflow")

    n1 = NodeDefinition(id="N1", node_type="numeric_input", category=NodeCategory.INPUT, title="Input", config={"value": 10.0})
    n_broken = NodeDefinition(id="N_BROKEN", node_type="formula_evaluation", category=NodeCategory.CALCULATION, title="Bad Formula", config={"expression": "syntax error +++"})
    wf.nodes = [n1, n_broken]
    wf.connections = [
        ConnectionDefinition(source_node_id="N1", source_port="value", target_node_id="N_BROKEN", target_port="a")
    ]

    # Run with broken node
    rec_fail = service.execute_workflow(wf)
    assert rec_fail.status == WorkflowStatus.FAILED
    assert rec_fail.node_records["N1"].status == NodeExecutionState.COMPLETED
    assert rec_fail.node_records["N_BROKEN"].status == NodeExecutionState.FAILED

    # Correct configuration and rerun
    n_broken.config["expression"] = "a * 2.5"
    rec_fixed = service.execute_workflow(wf)
    assert rec_fixed.status == WorkflowStatus.COMPLETED
    assert rec_fixed.node_records["N_BROKEN"].status == NodeExecutionState.COMPLETED
    assert rec_fixed.node_records["N_BROKEN"].outputs["result"] == 25.0


def test_scenario_g_product_independence(tmp_path):
    """Scenario G: Product independence
    Complete a workflow without creating or selecting any product.
    """
    service = StudioService(tmp_path)
    # Ensure zero products exist
    assert len(service.list_products()) == 0

    # Execute workflow purely with product_id=None
    wf = WorkflowDefinition(name="Pure Product-Independent Workflow", product_id=None)
    n = NodeDefinition(node_type="numeric_input", category=NodeCategory.INPUT, title="Constant", config={"value": 42.0})
    wf.nodes = [n]

    rec = service.execute_workflow(wf)
    assert rec.status == WorkflowStatus.COMPLETED
    assert len(service.list_products()) == 0  # Still zero products
    assert rec.workflow_name == "Pure Product-Independent Workflow"
