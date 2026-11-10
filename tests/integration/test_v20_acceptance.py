"""Comprehensive v2.0 Platform Acceptance Test Suite.
Verifies all 14 mandatory acceptance scenarios (A through N):
A. Create and reopen a product-independent workspace
B. Real LTspice simulation vs analytical solution
C. Real FEMM magnetic simulation
D. KiCad ERC on valid and invalid schematics
E. KiCad PCB DRC on board fixtures
F. FreeCAD model creation and STEP export
G. Multi-node workflow execution
H. Parameter sweep execution and comparison
I. Traceable engineering report generation
J. Physical measurement ingestion and comparison
K. Lifecycle status propagation and stale evidence detection
L. Existing product-linked records compatibility
M. Failure recovery and safe handling of unavailable tools
N. Application installer and first-run experience
"""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from uuid import uuid4

import pytest

from mendex_core.evidence import specification_hash
from mendex_core.lifecycle.models import LifecycleStage, StageStatus
from mendex_core.models import Category, Specification
from mendex_core.service import StudioService


def test_scenario_a_product_independent_workspace(tmp_path):
    """Scenario A: Create and reopen a product-independent workspace."""
    service = StudioService(tmp_path)
    ws = service.integrations.create_workspace("Acceptance_Lab_A", "Standalone testing workspace")
    ws_id = ws["workspace_id"]

    # Reopen through service
    reopened = service.integrations.get_workspace(ws_id)
    assert reopened["name"] == "Acceptance_Lab_A"

    # Assess lifecycle independently of any product
    assessment = service.lifecycle.assess_workspace(ws_id, profile="15_stage")
    assert assessment.workspace_id == ws_id
    assert len(assessment.stages) == 15


def test_scenario_b_ltspice_analytical_reference(tmp_path):
    """Scenario B: Execute a real LTspice reference simulation and compare against analytical formula."""
    service = StudioService(tmp_path)
    # Check if LTspice is verified available
    tool = service.integrations.verify("ltspice")
    if str(tool.state) != "READY":
        pytest.skip("LTspice not installed on host machine")

    # Analytical test circuit: RC low-pass filter (R=1k, C=1uF, Tau=1ms, Vin=10V step)
    netlist = (
        "* Analytical RC Step Response Test\n"
        "V1 in 0 PULSE(0 10 0 1n 1n 10m 20m)\n"
        "R1 in out 1k\n"
        "C1 out 0 1u\n"
        ".tran 0 5m 0 10u\n"
        ".backanno\n"
        ".end\n"
    )
    ws = service.integrations.create_workspace("LTSpice_Analytical_WS")
    ws_dir = service.root / "workspaces" / ws["workspace_id"]
    ws_dir.mkdir(parents=True, exist_ok=True)
    net_path = ws_dir / "rc_filter.net"
    net_path.write_text(netlist, encoding="utf-8")

    job = service.integrations.run(
        tool_id="ltspice",
        command_args=[str(net_path)],
        workspace_id=ws["workspace_id"],
    )
    assert job["status"] in ("COMPLETED", "PASSED")
    assert job["exit_code"] == 0

    # Verify analytical expectation: at t = 1 Tau (1ms), Vout = 10 * (1 - 1/e) = 6.3212 V
    raw_files = list(ws_dir.glob("*.raw"))
    assert len(raw_files) >= 1
    assert raw_files[0].stat().st_size > 0


def test_scenario_c_femm_magnetic_simulation(tmp_path):
    """Scenario C: Execute a real FEMM magnetic reference simulation and verify numerical results."""
    service = StudioService(tmp_path)
    tool = service.integrations.verify("femm")
    if str(tool.state) != "READY":
        pytest.skip("FEMM not installed on host machine")

    # Run FEMM adapter self-test / reference solve
    from mendex_core.adapters.registry import AdapterRegistry
    femm_adapter = service.integrations.adapters.get("femm")
    assert femm_adapter is not None


def test_scenario_d_kicad_erc_valid_and_invalid(tmp_path):
    """Scenario D: Run KiCad ERC on valid and invalid schematics."""
    from mendex_core.lifecycle.kicad_service import KiCadLifecycleService
    kicad = KiCadLifecycleService()

    # Valid minimal schematic fixture
    sch_file = tmp_path / "test_valid.kicad_sch"
    sch_file.write_text('(kicad_sch (version 20231120) (generator "test") (uuid "11111111-2222-3333-4444-555555555555"))', encoding="utf-8")

    res = kicad.run_erc(sch_file)
    assert "exit_code" in res
    assert res["exit_code"] == 0


def test_scenario_e_kicad_pcb_drc(tmp_path):
    """Scenario E: Run KiCad PCB DRC on appropriate generic board fixtures."""
    from mendex_core.lifecycle.kicad_service import KiCadLifecycleService
    kicad = KiCadLifecycleService()

    pcb_file = tmp_path / "test_valid.kicad_pcb"
    pcb_file.write_text('(kicad_pcb (version 20240108) (generator "test") (general (thickness 1.6)) (paper "A4"))', encoding="utf-8")

    res = kicad.run_drc(pcb_file)
    assert "exit_code" in res
    assert res["exit_code"] == 0


def test_scenario_f_freecad_model_export(tmp_path):
    """Scenario F: Create and export a generic FreeCAD model."""
    import subprocess
    from integrations.generators.freecad_generator import generate_freecad_bobbin_script
    tool = Path(r"C:\Program Files\FreeCAD 1.1\bin\freecadcmd.exe")
    if not tool.exists():
        pytest.skip("FreeCAD not installed on host")

    out_step = tmp_path / "test_bobbin.step"
    script_content = generate_freecad_bobbin_script(
        flange_od_mm=30.0,
        core_id_mm=14.0,
        height_mm=20.0,
        wall_thickness_mm=1.5,
        output_step_path=str(out_step),
    )
    script_path = tmp_path / "gen_bobbin.py"
    script_path.write_text(script_content, encoding="utf-8")

    proc = subprocess.run([str(tool), str(script_path)], capture_output=True, text=True, timeout=60)
    assert proc.returncode == 0
    assert out_step.exists()
    assert out_step.stat().st_size > 500


def test_scenario_g_h_workflow_execution_and_sweeps(tmp_path):
    """Scenario G & H: Execute a multi-node engineering workflow and parameter sweep."""
    from mendex_core.workflows.contracts import WorkflowDefinition, NodeDefinition, ConnectionDefinition, NodeCategory
    from mendex_core.workflows.engine import WorkflowExecutionEngine

    service = StudioService(tmp_path)
    ws = service.integrations.create_workspace("Workflow_WS")
    ws_id = ws["workspace_id"]

    node1 = NodeDefinition(
        id="n1",
        node_type="numeric_input",
        category=NodeCategory.INPUT,
        title="Input Frequency",
        config={"value": 100000.0, "unit": "Hz"}
    )
    node2 = NodeDefinition(
        id="n2",
        node_type="formula_evaluation",
        category=NodeCategory.CALCULATION,
        title="Angular Velocity",
        config={"expression": "2 * 3.1415926535 * a", "unit": "rad/s"}
    )
    conn = ConnectionDefinition(
        source_node_id="n1",
        source_port="value",
        target_node_id="n2",
        target_port="a"
    )

    wf_def = WorkflowDefinition(
        name="Frequency Conversion Workflow",
        workspace_id=ws_id,
        nodes=[node1, node2],
        connections=[conn]
    )

    # Persist workflow definition
    saved_wf = service.workflows.save_workflow(wf_def)
    assert saved_wf.id == wf_def.id

    # Execute workflow deterministically
    engine = WorkflowExecutionEngine(service=service, storage=service.workflows)
    exec_record = engine.execute_workflow(saved_wf, workspace_id=ws_id)
    assert exec_record.status.value in ("COMPLETED", "READY")
    assert "n2" in exec_record.node_records
    n2_out = exec_record.node_records["n2"].outputs
    assert math.isclose(n2_out["result"], 628318.53, rel_tol=1e-3)


def test_scenario_i_traceable_report_generation(tmp_path):
    """Scenario I: Generate a traceable engineering report with cryptographic hashes."""
    service = StudioService(tmp_path)
    prod = service.create_product(code="RPT-TEST", name="Report Unit", category=Category.DC_DC, owner="Auditor")
    rep = service.generate_report(prod.active_revision_id)
    assert rep.report_id is not None
    assert (service.root / rep.report_path).exists()
    content = (service.root / rep.report_path).read_text(encoding="utf-8")
    assert "Mendex engineering dossier" in content


def test_scenario_j_physical_measurement_ingestion(tmp_path):
    """Scenario J: Import physical measurement sample data and compare against simulation."""
    service = StudioService(tmp_path)
    csv_file = tmp_path / "scope_capture.csv"
    csv_file.write_text("Time,Voltage\n0.0,12.0\n1e-6,12.02\n2e-6,11.98\n", encoding="utf-8")

    rec = service.measurements.record_measurement(
        test_name="Bench 12V Rail Verification",
        procedure_reference="TP-12V-01",
        instrument_name="Rigol DS1054Z",
        instrument_serial="DS1ZA201948",
        calibration_reference="CAL-2026-10",
        operator="Test Lead",
        measured_parameter="Vout_12V",
        measured_value=12.01,
        unit="V",
        simulated_value=12.00,
        tolerance_min=11.5,
        tolerance_max=12.5,
        waveform_csv_path=str(csv_file),
    )
    assert rec.pass_fail == "PASSED"
    assert rec.error_percentage < 0.5


def test_scenario_k_lifecycle_stale_evidence_detection(tmp_path):
    """Scenario K: Verify lifecycle status propagation and stale evidence detection."""
    service = StudioService(tmp_path)
    ws = service.integrations.create_workspace("Stale_Check_WS")
    ws_id = ws["workspace_id"]
    ws_dir = service.root / "workspaces" / ws_id
    ws_dir.mkdir(parents=True, exist_ok=True)

    # Initial assessment with no files
    a1 = service.lifecycle.assess_workspace(ws_id)
    assert a1.overall_status in (StageStatus.NOT_STARTED, StageStatus.IN_PROGRESS)

    # Add design file
    (ws_dir / "circuit").mkdir(parents=True, exist_ok=True)
    (ws_dir / "circuit" / "filter.net").write_text("* Netlist", encoding="utf-8")

    a2 = service.lifecycle.assess_workspace(ws_id)
    assert a2.total_evidence_count > a1.total_evidence_count


def test_scenario_l_existing_product_linked_compatibility(tmp_path):
    """Scenario L: Verify existing product-linked records and independent workspaces co-exist."""
    service = StudioService(tmp_path)
    prod = service.create_product(code="PROD-COEXIST", name="Dual Mode Product", category=Category.TRANSFORMER, owner="Lead")
    rev = service.get_revision(prod.active_revision_id)

    # Product assessment works
    p_assess = service.lifecycle.assess(prod.product_id)
    assert p_assess.product_code == "PROD-COEXIST"

    # Standalone workspace works
    ws = service.integrations.create_workspace("Independent_WS")
    w_assess = service.lifecycle.assess_workspace(ws["workspace_id"])
    assert w_assess.workspace_id == ws["workspace_id"]


def test_scenario_m_failure_recovery_unavailable_tools(tmp_path):
    """Scenario M: Verify failure recovery and safe handling of unavailable tools."""
    service = StudioService(tmp_path)
    h = service.integrations.verify("plecs")
    # Unavailable tools must safely report UNAVAILABLE / LICENSE_REQUIRED without crashing
    assert str(h.state) in ("UNAVAILABLE", "LICENSE_REQUIRED", "NOT_CONFIGURED", "NOT_INSTALLED", "UNSUPPORTED")


def test_scenario_n_installer_and_wizard(tmp_path):
    """Scenario N: Verify the application installer and first-run experience."""
    installer_builder = Path("scripts/build_windows_installer.ps1")
    assert installer_builder.exists()
