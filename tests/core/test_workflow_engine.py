"""Automated test suite for v1.9 workflow DAG execution engine."""
import pytest
from pathlib import Path
from uuid import uuid4

from mendex_core.workflows.contracts import (
    NodeCategory,
    NodeExecutionState,
    WorkflowStatus,
    WorkflowDefinition,
    NodeDefinition,
    ConnectionDefinition,
)
from mendex_core.workflows.engine import WorkflowExecutionEngine, CancellationToken
from mendex_core.workflows.storage import WorkflowStorageService


def test_linear_calculation_and_validation_workflow(tmp_path):
    """Test full execution of Calculation -> Validation -> Evidence -> Report DAG."""
    db_file = tmp_path / "studio.sqlite3"
    storage = WorkflowStorageService(db_file)
    engine = WorkflowExecutionEngine(storage=storage)

    wf = WorkflowDefinition(
        name="Skin Depth Calculation and Validation",
        workspace_id=str(uuid4()),
    )

    # 1. Frequency Input Node (100 kHz)
    n_freq = NodeDefinition(
        node_type="numeric_input",
        category=NodeCategory.INPUT,
        title="Frequency",
        config={"value": 100000.0, "unit": "Hz"},
    )

    # 2. Temperature Input Node (20°C)
    n_temp = NodeDefinition(
        node_type="numeric_input",
        category=NodeCategory.INPUT,
        title="Temperature",
        config={"value": 20.0, "unit": "C"},
    )

    # 3. Deterministic Physics Node (Skin Depth)
    n_skin = NodeDefinition(
        node_type="deterministic_physics",
        category=NodeCategory.CALCULATION,
        title="Skin Depth",
        config={"formula_id": "skin_depth"},
    )

    # 4. Range Validation Node (Expecting between 0.1 mm and 0.3 mm, in meters: 0.0001 to 0.0003)
    n_val = NodeDefinition(
        node_type="range_validation",
        category=NodeCategory.VALIDATION,
        title="Skin Depth Check",
        config={"min_val": 0.0001, "max_val": 0.0003, "check_id": "REQ-SKIN-DEPTH"},
    )

    # 5. Evidence Aggregation Node
    n_evid = NodeDefinition(
        node_type="evidence_aggregation",
        category=NodeCategory.REPORTING,
        title="Aggregator",
    )

    # 6. Report Export Node
    n_rep = NodeDefinition(
        node_type="report_export",
        category=NodeCategory.REPORTING,
        title="Dossier Exporter",
        config={"report_title": "Skin Depth Engineering Dossier"},
    )

    wf.nodes = [n_freq, n_temp, n_skin, n_val, n_evid, n_rep]
    wf.connections = [
        # freq -> skin_depth.param1
        ConnectionDefinition(source_node_id=n_freq.id, source_port="value", target_node_id=n_skin.id, target_port="param1"),
        # temp -> skin_depth.param2
        ConnectionDefinition(source_node_id=n_temp.id, source_port="value", target_node_id=n_skin.id, target_port="param2"),
        # skin.result -> val.value_in
        ConnectionDefinition(source_node_id=n_skin.id, source_port="result", target_node_id=n_val.id, target_port="value_in"),
        # val.validation_result -> evid.check1
        ConnectionDefinition(source_node_id=n_val.id, source_port="validation_result", target_node_id=n_evid.id, target_port="check1"),
        # skin.record -> evid.calculation
        ConnectionDefinition(source_node_id=n_skin.id, source_port="record", target_node_id=n_evid.id, target_port="calculation"),
        # evid.manifest -> rep.manifest
        ConnectionDefinition(source_node_id=n_evid.id, source_port="manifest", target_node_id=n_rep.id, target_port="manifest"),
    ]

    record = engine.execute_workflow(wf, workspace_id=wf.workspace_id)

    assert record.status == WorkflowStatus.COMPLETED
    assert len(record.node_records) == 6

    # Verify skin depth result (~0.206 mm = 0.000206 m)
    skin_rec = record.node_records[n_skin.id]
    assert skin_rec.status == NodeExecutionState.COMPLETED
    assert pytest.approx(float(skin_rec.outputs["result"]), abs=1e-6) == 0.000206

    # Verify validation node passed
    val_rec = record.node_records[n_val.id]
    assert val_rec.status == NodeExecutionState.COMPLETED
    assert val_rec.outputs["passed"] is True

    # Verify report export generated HTML file
    rep_rec = record.node_records[n_rep.id]
    assert rep_rec.status == NodeExecutionState.COMPLETED
    report_path = rep_rec.outputs["report_path"]
    assert Path(report_path).exists()
    assert "Skin Depth Engineering Dossier" in Path(report_path).read_text(encoding="utf-8")


def test_failure_propagation_and_skip(tmp_path):
    """Verify that failure in an upstream node causes downstream dependents to be SKIPPED."""
    engine = WorkflowExecutionEngine()

    wf = WorkflowDefinition(name="Failure Propagation Workflow")

    # Node A: Evaluates invalid expression -> FAILS
    n_fail = NodeDefinition(
        id="N_FAIL",
        node_type="formula_evaluation",
        category=NodeCategory.CALCULATION,
        title="Failing Node",
        config={"expression": "1 / 0"},  # Div by zero
    )

    # Node B: Downstream dependent on A -> Should be SKIPPED
    n_downstream = NodeDefinition(
        id="N_DOWNSTREAM",
        node_type="range_validation",
        category=NodeCategory.VALIDATION,
        title="Dependent Node",
    )

    wf.nodes = [n_fail, n_downstream]
    wf.connections = [
        ConnectionDefinition(source_node_id="N_FAIL", source_port="result", target_node_id="N_DOWNSTREAM", target_port="value_in")
    ]

    # In safe_eval_expression, div by zero returns inf, so let's use an expression with an undefined variable to trigger ValueError
    n_fail.config["expression"] = "undefined_var * 2"

    record = engine.execute_workflow(wf)
    assert record.status == WorkflowStatus.FAILED
    assert record.node_records["N_FAIL"].status == NodeExecutionState.FAILED
    assert record.node_records["N_DOWNSTREAM"].status == NodeExecutionState.SKIPPED


def test_cancellation_token(tmp_path):
    """Verify cooperative cancellation stops workflow execution."""
    engine = WorkflowExecutionEngine()

    wf = WorkflowDefinition(name="Cancellable Workflow")
    n1 = NodeDefinition(id="N1", node_type="numeric_input", category=NodeCategory.INPUT, title="N1", config={"value": 1.0})
    n2 = NodeDefinition(id="N2", node_type="numeric_input", category=NodeCategory.INPUT, title="N2", config={"value": 2.0})
    wf.nodes = [n1, n2]

    cancel_token = CancellationToken()
    cancel_token.cancel()  # Cancel upfront

    record = engine.execute_workflow(wf, cancel_token=cancel_token)
    assert record.status == WorkflowStatus.CANCELLED
    assert record.node_records["N1"].status == NodeExecutionState.CANCELLED
