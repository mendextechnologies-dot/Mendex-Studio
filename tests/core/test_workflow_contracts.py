"""Automated test suite for v1.9 visual workflow models, port contracts, and persistence."""
import pytest
from pathlib import Path
from uuid import uuid4

from mendex_core.workflows.types import (
    PortDataType,
    QuantityValue,
    check_type_compatibility,
    check_unit_compatibility,
    ValidationResultData,
)
from mendex_core.workflows.contracts import (
    NodeCategory,
    NodeExecutionState,
    WorkflowStatus,
    WorkflowDefinition,
    NodeDefinition,
    ConnectionDefinition,
    WorkflowExecutionRecord,
)
from mendex_core.workflows.registry import NodeRegistry, ExecutionContext
from mendex_core.workflows.validation import (
    detect_cycles_and_toposort,
    validate_workflow,
)
from mendex_core.workflows.storage import WorkflowStorageService
from mendex_core.workflows.nodes.calculations import safe_eval_expression


def test_node_registry_registration():
    """Verify all 7 node categories are registered with valid port catalogs."""
    nodes = NodeRegistry.list_nodes()
    assert len(nodes) >= 12

    catalog = NodeRegistry.get_port_catalog()
    assert "numeric_input" in catalog
    assert "formula_evaluation" in catalog
    assert "ltspice_simulation" in catalog
    assert "range_validation" in catalog
    assert "report_export" in catalog
    assert "knowledge_lookup" in catalog


def test_quantity_canonical_conversion():
    """Verify quantity conversion to canonical SI units."""
    q_khz = QuantityValue(value=250.0, unit="kHz")
    val, base = q_khz.to_canonical()
    assert val == 250000.0
    assert base == "hz"

    q_uh = QuantityValue(value=150.0, unit="uH")
    val_l, base_l = q_uh.to_canonical()
    assert pytest.approx(val_l, 1e-9) == 150e-6
    assert base_l == "h"


def test_type_and_unit_compatibility():
    """Verify typed port and unit compatibility checking."""
    # Type compatibility
    assert check_type_compatibility(PortDataType.SCALAR, PortDataType.SCALAR) is True
    assert check_type_compatibility(PortDataType.QUANTITY, PortDataType.SCALAR) is True
    assert check_type_compatibility(PortDataType.SIM_RESULT, PortDataType.TIME_SERIES) is True
    assert check_type_compatibility(PortDataType.STRING, PortDataType.SCALAR) is False

    # Unit compatibility
    assert check_unit_compatibility("kHz", "Hz") is True
    assert check_unit_compatibility("uH", "mH") is True
    assert check_unit_compatibility("V", "mV") is True
    assert check_unit_compatibility("kHz", "V") is False


def test_safe_math_expression_evaluation():
    """Verify safe AST evaluator computes valid math and rejects malicious payloads."""
    # Valid math
    res = safe_eval_expression("sqrt(a * b) + 2.0 * c", {"a": 4.0, "b": 9.0, "c": 3.0})
    assert res == 12.0  # sqrt(36) + 6.0 = 6 + 6 = 12

    res_pi = safe_eval_expression("2 * pi * f * l", {"f": 1000.0, "l": 0.001})
    assert pytest.approx(res_pi, 0.01) == 6.28318

    # Safe rejection of arbitrary code injection
    with pytest.raises(Exception):
        safe_eval_expression("__import__('os').system('echo pwned')", {})

    with pytest.raises(Exception):
        safe_eval_expression("eval('2+2')", {})


def test_cycle_detection_and_topological_sort():
    """Verify DAG topological ordering and directed cycle rejection."""
    n1 = NodeDefinition(id="N1", node_type="numeric_input", category=NodeCategory.INPUT, title="In")
    n2 = NodeDefinition(id="N2", node_type="formula_evaluation", category=NodeCategory.CALCULATION, title="Calc")
    n3 = NodeDefinition(id="N3", node_type="range_validation", category=NodeCategory.VALIDATION, title="Val")

    # Clean linear DAG: N1 -> N2 -> N3
    c1 = ConnectionDefinition(source_node_id="N1", source_port="value", target_node_id="N2", target_port="a")
    c2 = ConnectionDefinition(source_node_id="N2", source_port="result", target_node_id="N3", target_port="value_in")

    order, cycle = detect_cycles_and_toposort([n1, n2, n3], [c1, c2])
    assert cycle is None
    assert order == ["N1", "N2", "N3"]

    # Introduce cycle: N3 -> N1
    c_cycle = ConnectionDefinition(source_node_id="N3", source_port="passed", target_node_id="N1", target_port="in")
    order_cyc, cycle_nodes = detect_cycles_and_toposort([n1, n2, n3], [c1, c2, c_cycle])
    assert order_cyc == []
    assert cycle_nodes is not None
    assert set(cycle_nodes) == {"N1", "N2", "N3"}


def test_workflow_storage_crud_product_independent(tmp_path):
    """Verify workflow database CRUD operations without product association."""
    db_file = tmp_path / "studio.sqlite3"
    storage = WorkflowStorageService(db_file)

    # 1. Create Workflow
    wf = WorkflowDefinition(
        name="Flyback CCM Transformer Sizing",
        description="Calculates primary inductance and validates peak flux density",
        workspace_id=str(uuid4()),
        product_id=None,  # Strictly product-independent
    )
    n1 = NodeDefinition(node_type="numeric_input", category=NodeCategory.INPUT, title="Vin Min", config={"value": 100.0, "unit": "V"})
    n2 = NodeDefinition(node_type="deterministic_physics", category=NodeCategory.CALCULATION, title="CCM Sizing", config={"formula_id": "flyback_ccm"})
    wf.nodes = [n1, n2]
    wf.connections = [
        ConnectionDefinition(source_node_id=n1.id, source_port="value", target_node_id=n2.id, target_port="param1")
    ]

    saved = storage.save_workflow(wf)
    assert saved.id == wf.id
    assert saved.version == 1

    # 2. Get and List
    fetched = storage.get_workflow(saved.id)
    assert fetched is not None
    assert fetched.name == "Flyback CCM Transformer Sizing"
    assert len(fetched.nodes) == 2
    assert fetched.product_id is None

    all_wfs = storage.list_workflows()
    assert len(all_wfs) == 1

    # 3. Duplicate
    dup = storage.duplicate_workflow(saved.id, "Flyback Sizing Clone")
    assert dup is not None
    assert dup.id != saved.id
    assert dup.name == "Flyback Sizing Clone"
    assert dup.nodes[0].id != saved.nodes[0].id
    assert dup.connections[0].source_node_id == dup.nodes[0].id

    # 4. Record Run
    run_rec = WorkflowExecutionRecord(
        workflow_id=saved.id,
        workflow_name=saved.name,
        status=WorkflowStatus.COMPLETED,
        provenance="Test suite execution",
    )
    storage.record_run(run_rec)
    runs = storage.list_runs(saved.id)
    assert len(runs) == 1
    assert runs[0].status == WorkflowStatus.COMPLETED

    # 5. Export and Import JSON
    json_data = storage.export_workflow_json(saved.id)
    assert "Flyback CCM Transformer Sizing" in json_data
    imported = storage.import_workflow_json(json_data)
    assert imported.id != saved.id
    assert imported.name == saved.name

    # 6. Delete
    deleted = storage.delete_workflow(saved.id)
    assert deleted is True
    assert storage.get_workflow(saved.id) is None
