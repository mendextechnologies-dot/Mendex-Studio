"""Milestone 3 — Wider Engineering Coverage Verification Test Suite.

Verifies:
- G11: FEMM excitation, discrete inductor generator, and analytical reluctance benchmark.
- G12: Converter control transfer function, line/load regulation, and fault response.
- G13: Topology applicability matrix and readiness status stamping on candidates.
- G15: 3D model coverage tracking and mechanical PCB envelope constraint validation.
- G16 / G17 / G23: Disciplined physical test evidence validation and draft release protection.
"""
from __future__ import annotations

import csv
import hashlib
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from mendex_core.controller import MendexEngineeringController
from mendex_core.design.femm_runner import FEMMRunner
from mendex_core.design.ltspice_runner import LTspiceRunner
from mendex_core.design.models import Requirement as CandidateRequirement
from mendex_core.design.synthesis import CandidateSynthesisEngine, TOPOLOGY_APPLICABILITY_MATRIX
from mendex_core.desktop.service import DesktopService, _inspect_pcb_mechanical_and_3d
from mendex_core.engineering_records.models import ValidationWrite
from mendex_core.evidence import ManualCheck, ValidationStatus
from mendex_core.lifecycle.engine import LifecycleStage, StageStatus
from mendex_core.models import Specification
from mendex_core.service import StudioService
from integrations.generators.femm_generator import generate_femm_inductor_script


# ---------------------------------------------------------------------------
# G11: FEMM Inductor FEA & Analytical Reluctance Benchmark
# ---------------------------------------------------------------------------

def test_g11_femm_inductor_script_generation():
    """Verifies discrete inductor script generates valid Lua commands with explicit excitation."""
    script = generate_femm_inductor_script(
        core_type="ER28",
        turns=18,
        current_a=1.5,
        air_gap_mm=0.5,
        frequency_hz=100000.0,
    )
    assert "newdocument(0)" in script
    assert "mi_probdef(100000.0" in script
    assert "mi_addmaterial(\"Air\"" in script
    assert "mi_addmaterial(\"Ferrite_N87\"" in script
    assert "mi_addcircprop(\"Winding\", 1.5, 1)" in script
    assert "mi_saveas" in script
    assert "mi_analyze(" in script


def test_g11_analytical_reluctance_benchmark():
    """Verifies 1D reluctance analytical formula compares truthfully against FEA flux density."""
    runner = FEMMRunner()
    
    # Test case: N=20 turns, I=2A, l_gap=1mm (0.001m), l_e=50mm (0.05m), mu_r=2000
    # Reluctance is dominated by gap: mu0 * N * I / l_gap = (4pi*1e-7 * 20 * 2) / 0.001 = 0.050265 T
    benchmark = runner.compare_analytical_vs_fea(
        turns=20,
        current_a=2.0,
        air_gap_mm=1.0,
        core_le_mm=50.0,
        mu_r=2000.0,
        fea_b_max=0.0495,  # FEA result close to analytical
    )
    assert benchmark["status"] == "CONVERGED_ORDER_OF_MAGNITUDE"
    assert benchmark["analytical_b_t"] == pytest.approx(0.04904, rel=1e-3)
    assert benchmark["fea_b_max_t"] == 0.0495
    assert benchmark["ratio"] == pytest.approx(1.009, abs=0.02)

    # Negative test: Unexcited case (zero current)
    zero_bench = runner.compare_analytical_vs_fea(
        turns=20,
        current_a=0.0,
        air_gap_mm=1.0,
        fea_b_max=0.0,
    )
    assert "NOT_EVALUATED" in zero_bench["status"]


# ---------------------------------------------------------------------------
# G12: Converter Control & Line/Load/Fault Analysis
# ---------------------------------------------------------------------------

def test_g12_buck_small_signal_bode_analysis():
    """Verifies LC double pole and ESR zero computation with explicit open-loop qualification."""
    runner = LTspiceRunner()
    
    # 12V -> 5V Buck with L=47uH, C=47uF, ESR=50mOhm, 1A load (R_load = 5 Ohm)
    bode = runner.calculate_buck_small_signal_bode(
        vin_nom=12.0,
        vout=5.0,
        iout=1.0,
        l_h=47e-6,
        c_f=47e-6,
        esr_ohm=0.05,
    )
    
    # Theoretical f0 = 1 / (2 * pi * sqrt(47u * 47u)) = 1 / (2 * pi * 47u) = 3386.28 Hz
    assert bode["f_double_pole_hz"] == pytest.approx(3386.3, rel=1e-2)
    # Theoretical fz = 1 / (2 * pi * C * ESR) = 1 / (2 * pi * 47u * 0.05) = 67725.5 Hz
    assert bode["f_esr_zero_hz"] == pytest.approx(67725.5, rel=1e-2)
    # Q = R * sqrt(C / L) = 5 * sqrt(47u / 47u) = 5.0
    assert bode["q_factor"] == pytest.approx(5.0, rel=1e-2)
    
    # Enforce truthfulness: loop compensation status must be NOT_EVALUATED
    assert "NOT_EVALUATED" in bode["loop_compensation_status"]
    assert bode["control_mode"] == "OPEN_LOOP_PWM"
    assert bode["is_closed_loop"] is False


def test_g12_line_and_load_regulation_evaluation():
    """Verifies line and load regulation calculation and tolerance compliance."""
    runner = LTspiceRunner()
    
    # 5V output with 10mV line variation across 10-14V and 20mV load variation
    reg = runner.evaluate_line_load_regulation(
        vout_nom=5.0,
        vout_line_min=4.995,
        vout_line_max=5.005,
        vout_load_light=5.010,
        vout_load_full=4.990,
        vin_min=10.0,
        vin_max=14.0,
    )
    assert reg["line_regulation_pct"] == pytest.approx(0.2, abs=0.01)
    assert reg["load_regulation_pct"] == pytest.approx(0.4, abs=0.01)
    assert reg["status"] == "PASS"

    # Failing case: Excessive line variation (> 10%)
    failing_reg = runner.evaluate_line_load_regulation(
        vout_nom=5.0,
        vout_line_min=4.2,
        vout_line_max=5.8,
        vout_load_light=5.01,
        vout_load_full=4.99,
        vin_min=10.0,
        vin_max=14.0,
    )
    assert failing_reg["status"] == "MARGINAL"
    assert failing_reg["line_regulation_pct"] > 10.0


def test_g12_fault_response_evaluation():
    """Verifies peak fault current vs switch rating evaluation."""
    runner = LTspiceRunner()
    
    # Safe condition: peak fault current 15A < 30A rating
    safe_fault = runner.evaluate_fault_response(
        i_peak_fault_a=15.0,
        switch_i_max_a=30.0,
    )
    assert safe_fault["fault_status"] == "WITHIN_RATING"
    assert safe_fault["stress_ratio"] == 0.5
    assert safe_fault["active_current_limiting"] == "PASS_MARGIN"

    # Violation condition: peak fault current 35A > 30A rating
    viol_fault = runner.evaluate_fault_response(
        i_peak_fault_a=35.0,
        switch_i_max_a=30.0,
    )
    assert viol_fault["fault_status"] == "TRIPPED_OVERCURRENT"
    assert "NOT_IMPLEMENTED" in viol_fault["active_current_limiting"]


# ---------------------------------------------------------------------------
# G13: Topology Readiness & Applicability Matrix
# ---------------------------------------------------------------------------

def test_g13_topology_applicability_matrix_and_candidate_stamping():
    """Verifies candidate synthesis stamps QUALIFIED_REFERENCE for Buck and EXPERIMENTAL for others."""
    # Check global applicability matrix
    assert "buck" in TOPOLOGY_APPLICABILITY_MATRIX
    assert TOPOLOGY_APPLICABILITY_MATRIX["buck"]["readiness"] == "QUALIFIED_REFERENCE"
    assert TOPOLOGY_APPLICABILITY_MATRIX["flyback"]["readiness"] == "EXPERIMENTAL"
    assert TOPOLOGY_APPLICABILITY_MATRIX["llc"]["readiness"] == "EXPERIMENTAL"

    # Synthesize candidates for a non-isolated 12V -> 5V, 1A spec
    engine = CandidateSynthesisEngine()
    reqs = [
        CandidateRequirement(parameter="vin_nom", target_value=12.0, min_value=10.0, max_value=14.0, unit="V"),
        CandidateRequirement(parameter="vout", target_value=5.0, unit="V"),
        CandidateRequirement(parameter="iout", target_value=1.0, unit="A"),
        CandidateRequirement(parameter="fsw", target_value=100000.0, unit="Hz"),
    ]
    candidates = engine.synthesize_candidates(reqs)
    assert len(candidates) > 0

    buck_candidate = next((c for c in candidates if "buck" in c.topology_name.lower()), None)
    assert buck_candidate is not None
    assert buck_candidate.readiness_status == "QUALIFIED_REFERENCE"

    # Non-buck candidates must be EXPERIMENTAL
    for cand in candidates:
        if "buck" not in cand.topology_name.lower():
            assert cand.readiness_status == "EXPERIMENTAL"
            assert len(cand.qualification_notes) > 0


# ---------------------------------------------------------------------------
# G15: 3D Model Coverage & Mechanical PCB Envelope
# ---------------------------------------------------------------------------

def test_g15_mechanical_pcb_envelope_and_3d_model_coverage(tmp_path: Path):
    """Verifies PCB envelope violation detection and 3D model coverage accounting."""
    # Create test PCB file with 2 footprints: R1 (with 3D model) and L1 (without 3D model)
    # Board dimensions: (10, 10) to (60, 40) => Width = 50.0 mm, Height = 30.0 mm
    pcb_file = tmp_path / "test_board.kicad_pcb"
    pcb_file.write_text("""(kicad_pcb (version 20240108) (general (thickness 1.6))
      (gr_rect (start 10 10) (end 60 40) (stroke (width 0.15) (type solid)) (layer "Edge.Cuts"))
      (footprint "Resistor_SMD:R_0805_2012Metric" (layer "F.Cu")
        (property "Reference" "R1")
        (model "${KICAD8_3DMODEL_DIR}/Resistor_SMD.3dshapes/R_0805_2012Metric.wrl")
      )
      (footprint "Inductor_SMD:L_12x12mm" (layer "F.Cu")
        (property "Reference" "L1")
      )
    )""", encoding="utf-8")

    # 1. Evaluate without dimension constraint
    metrics = _inspect_pcb_mechanical_and_3d(pcb_file, specification=None)
    assert metrics["board_width_mm"] == 50.0
    assert metrics["board_height_mm"] == 30.0
    assert metrics["total_components"] == 2
    assert metrics["components_with_3d"] == 1
    assert metrics["model_coverage_pct"] == 50.0
    assert metrics["model_coverage_status"] == "PARTIAL"
    assert len(metrics["missing_3d_models"]) == 1
    assert metrics["missing_3d_models"][0]["ref"] == "L1"
    assert metrics["envelope_compliance"] == "NOT_EVALUATED"
    assert "Collision detection with chassis" in metrics["mechanical_disclaimer"]

    # 2. Evaluate with compliant specification (max_w=60, max_h=50)
    spec_ok = Specification(max_pcb_width_mm=60.0, max_pcb_height_mm=50.0)
    metrics_ok = _inspect_pcb_mechanical_and_3d(pcb_file, specification=spec_ok)
    assert metrics_ok["envelope_compliance"] == "COMPLIANT"

    # 3. Evaluate with envelope violation (board width 50mm > max allowed 40mm)
    spec_viol = Specification(max_pcb_width_mm=40.0, max_pcb_height_mm=50.0)
    metrics_viol = _inspect_pcb_mechanical_and_3d(pcb_file, specification=spec_viol)
    assert metrics_viol["envelope_compliance"] == "VIOLATION"
    assert "Board width (50.0mm) exceeds max allowed (40.0mm)" in metrics_viol["envelope_details"]


# ---------------------------------------------------------------------------
# G16 / G17 / G23: Disciplined Physical Testing & Draft Release Gate
# ---------------------------------------------------------------------------

def test_g16_g17_validation_write_evidence_source_enforcement(tmp_path: Path):
    """Verifies ValidationWrite strictly rejects physical test claims without MEASURED evidence."""
    controller = MendexEngineeringController(tmp_path)
    proj = controller.create_project("Validation Test Project", code="VTP", auto_enroll=True)
    studio = controller.service
    product = studio.get_product(proj["project_id"])
    rev = studio.get_revision(product.active_revision_id)

    dummy_csv = tmp_path / "waveform.csv"
    dummy_csv.write_text("0.0, 5.0\n1e-6, 5.01\n", encoding="utf-8")
    csv_sha = hashlib.sha256(dummy_csv.read_bytes()).hexdigest()

    # Valid physical test check
    check_measured = ManualCheck(
        check_id="VAL-PHYS-01",
        reviewer="Lead Test Engineer",
        notes="Physical bench ripple measurement",
        evidence_kind="MEASURED",
        measured_value=5.01,
        unit="V",
        minimum=4.9,
        maximum=5.1,
        status=ValidationStatus.PASS,
    )

    valid_write = ValidationWrite(
        revision_id=rev.revision_id,
        stage_id="validation",
        expected_input_hash=csv_sha,  # dummy stage hash
        source="desktop",
        reason="Record physical bench test",
        idempotency_key="rec_phys_01",
        check=check_measured,
        evidence_path=str(dummy_csv),
        expected_evidence_sha256=csv_sha,
        evidence_source="physical_test",
    )
    assert valid_write.evidence_source == "physical_test"

    # Violation: Claiming physical_test with SIMULATED evidence_kind
    check_sim = ManualCheck(
        check_id="VAL-SIM-01",
        reviewer="Simulator",
        notes="LTspice ripple check",
        evidence_kind="SIMULATED",
        measured_value=5.01,
        unit="V",
        minimum=4.9,
        maximum=5.1,
        status=ValidationStatus.PASS,
    )
    with pytest.raises(ValueError, match="Physical test evidence records must declare MEASURED evidence_kind"):
        ValidationWrite(
            revision_id=rev.revision_id,
            stage_id="validation",
            expected_input_hash=csv_sha,
            source="desktop",
            reason="Attempt to spoof physical test",
            idempotency_key="rec_spoof_01",
            check=check_sim,
            evidence_path=str(dummy_csv),
            expected_evidence_sha256=csv_sha,
            evidence_source="physical_test",
        )


def test_g23_physical_testing_gate_blocks_unverified_engineering_release(tmp_path: Path):
    """Verifies that Engineering Release package remains DRAFT and IN_PROGRESS until physical testing passes."""
    service = StudioService(tmp_path)
    ws = service.integrations.create_workspace("Release_Gate_WS")
    ws_id = ws["workspace_id"]
    ws_dir = service.root / "workspaces" / ws_id
    ws_dir.mkdir(parents=True, exist_ok=True)

    # 1. Add requirements, architecture, schematic, pcb, simulations, and release dossier files
    (ws_dir / "requirements").mkdir(parents=True, exist_ok=True)
    (ws_dir / "requirements" / "spec.md").write_text("# Spec", encoding="utf-8")
    (ws_dir / "architecture.md").write_text("# Buck Architecture", encoding="utf-8")
    (ws_dir / "circuit").mkdir(parents=True, exist_ok=True)
    (ws_dir / "circuit" / "buck.net").write_text("* SPICE netlist", encoding="utf-8")
    (ws_dir / "calculations").mkdir(parents=True, exist_ok=True)
    (ws_dir / "calculations" / "sizing.json").write_text("{}", encoding="utf-8")
    (ws_dir / "simulations").mkdir(parents=True, exist_ok=True)
    (ws_dir / "simulations" / "tran.raw").write_text("raw", encoding="utf-8")
    (ws_dir / "pcb").mkdir(parents=True, exist_ok=True)
    (ws_dir / "pcb" / "board.kicad_sch").write_text("(kicad_sch)", encoding="utf-8")
    (ws_dir / "pcb" / "board.kicad_pcb").write_text("(kicad_pcb)", encoding="utf-8")
    (ws_dir / "pcb" / "erc.json").write_text("{}", encoding="utf-8")
    (ws_dir / "pcb" / "drc.json").write_text("{}", encoding="utf-8")
    (ws_dir / "bom.csv").write_text("Reference,MPN\nR1,RC0805", encoding="utf-8")
    (ws_dir / "validation_report.json").write_text("{}", encoding="utf-8")

    # Add release dossier file (e.g. release/dossier.pdf)
    (ws_dir / "release").mkdir(parents=True, exist_ok=True)
    (ws_dir / "release" / "engineering_dossier.pdf").write_bytes(b"%PDF-1.4 dummy draft dossier")

    # 2. Assess workspace WITHOUT physical measurements
    assess1 = service.lifecycle.assess_workspace(ws_id, profile="15_stage")
    
    # PHYSICAL_TESTING must be NOT_STARTED
    assert assess1.stages[LifecycleStage.PHYSICAL_TESTING.value].status == StageStatus.NOT_STARTED
    # ENGINEERING_RELEASE must NOT be PASSED; it must remain IN_PROGRESS with a draft disclosure blocker
    release_stage1 = assess1.stages[LifecycleStage.ENGINEERING_RELEASE.value]
    assert release_stage1.status == StageStatus.IN_PROGRESS
    assert any("restricted to DRAFT design data" in b for b in release_stage1.blockers)
    # Overall workspace status cannot claim PASSED
    assert assess1.overall_status == StageStatus.IN_PROGRESS

    # 3. Add a simulated measurement (attempting to bypass physical testing)
    csv_file = ws_dir / "dso_trace.csv"
    csv_file.write_text("0.0, 5.0\n1e-6, 5.0\n", encoding="utf-8")
    
    service.measurements.record_measurement(
        test_name="Simulated Output Ripple",
        procedure_reference="SPICE-SIM-01",
        instrument_name="LTspice Simulator",
        instrument_serial="LT-2026",
        calibration_reference="N/A",
        operator="Automated Runner",
        measured_parameter="Vout",
        measured_value=5.0,
        unit="V",
        tolerance_min=4.9,
        tolerance_max=5.1,
        waveform_csv_path=str(csv_file),
        workspace_id=ws_id,
    )
    assess_sim = service.lifecycle.assess_workspace(ws_id, profile="15_stage")
    assert assess_sim.stages[LifecycleStage.PHYSICAL_TESTING.value].status == StageStatus.NOT_STARTED
    assert assess_sim.stages[LifecycleStage.ENGINEERING_RELEASE.value].status == StageStatus.IN_PROGRESS

    # 4. Now add an authentic physical measurement from a real laboratory instrument
    service.measurements.record_measurement(
        test_name="Bench Oscilloscope Vout Ripple",
        procedure_reference="TP-ELEC-001",
        instrument_name="Keysight DSOX3024T Oscilloscope",
        instrument_serial="MY58492014",
        calibration_reference="CAL-2026-9921",
        operator="Senior Verification Engineer",
        measured_parameter="Vout_ripple",
        measured_value=5.01,
        unit="V",
        tolerance_min=4.9,
        tolerance_max=5.1,
        waveform_csv_path=str(csv_file),
        workspace_id=ws_id,
    )

    assess2 = service.lifecycle.assess_workspace(ws_id, profile="15_stage")
    assert assess2.stages[LifecycleStage.PHYSICAL_TESTING.value].status == StageStatus.PASSED
    assert assess2.stages[LifecycleStage.ENGINEERING_RELEASE.value].status == StageStatus.PASSED
    assert assess2.overall_status == StageStatus.PASSED
