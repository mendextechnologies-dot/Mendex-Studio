"""Automated tests for Mendex Engineering Studio v2.0 Platform Capabilities.
Verifies:
- Product-independent standalone workspace lifecycle assessment (15 stages)
- Engineering Change Request (ECR) management and impact analysis
- Physical laboratory test and measurement ingestion and simulated vs measured comparison
"""
from __future__ import annotations

import csv
from pathlib import Path
from uuid import uuid4

import pytest

from mendex_core.lifecycle.ecr import ECRStatus
from mendex_core.lifecycle.models import (
    LifecycleStage,
    StageStatus,
)
from mendex_core.service import StudioService


def test_v20_standalone_workspace_lifecycle_15_stages(tmp_path):
    """Verifies that engineering lifecycle can be assessed on a standalone workspace without products."""
    service = StudioService(tmp_path)

    # 1. Create a standalone engineering workspace
    ws = service.integrations.create_workspace(
        name="Standalone_Inverter_Lab",
        description="General power electronics prototyping workspace without administrative product",
    )
    ws_id = ws["workspace_id"]
    ws_path = service.root / "workspaces" / ws_id
    ws_path.mkdir(parents=True, exist_ok=True)

    # 2. Add engineering files into workspace
    (ws_path / "requirements").mkdir(parents=True, exist_ok=True)
    (ws_path / "requirements" / "system_specs.md").write_text("# Requirements Spec", encoding="utf-8")

    (ws_path / "circuit").mkdir(parents=True, exist_ok=True)
    (ws_path / "circuit" / "inverter.net").write_text("* Resonant Inverter SPICE netlist", encoding="utf-8")

    (ws_path / "calculations").mkdir(parents=True, exist_ok=True)
    (ws_path / "calculations" / "sizing_calculations.json").write_text('{"tank_l_uh": 120, "tank_c_nf": 22}', encoding="utf-8")

    # 3. Assess standalone workspace lifecycle across 15 stages
    assessment = service.lifecycle.assess_workspace(ws_id, profile="15_stage")

    assert assessment.workspace_id == ws_id
    assert assessment.workspace_name == "Standalone_Inverter_Lab"
    assert len(assessment.stages) == 15
    assert len(assessment.readiness_gates) == 15

    # Check key 15 stages
    assert LifecycleStage.REQUIREMENTS.value in assessment.stages
    assert LifecycleStage.ARCHITECTURE.value in assessment.stages
    assert LifecycleStage.ELECTRICAL_DESIGN.value in assessment.stages
    assert LifecycleStage.ENGINEERING_CALCULATIONS.value in assessment.stages
    assert LifecycleStage.PHYSICAL_TESTING.value in assessment.stages
    assert LifecycleStage.ENGINEERING_RELEASE.value in assessment.stages

    # Verify requirements and design evaluated as passed
    assert assessment.stages[LifecycleStage.REQUIREMENTS.value].status == StageStatus.PASSED
    assert assessment.stages[LifecycleStage.ELECTRICAL_DESIGN.value].status == StageStatus.PASSED
    assert assessment.stages[LifecycleStage.ENGINEERING_CALCULATIONS.value].status == StageStatus.PASSED


def test_v20_ecr_lifecycle_and_impact_analysis(tmp_path):
    """Verifies Engineering Change Request (ECR) creation, impact analysis, and review sign-off."""
    service = StudioService(tmp_path)

    # 1. Create ECR
    ecr = service.ecr.create_ecr(
        title="Upgrade Resonant Switch to GaN FET",
        description="Replace standard silicon MOSFET with EPC2019 GaN FET for 200 kHz operation",
        reason="Reduce conduction and switching losses by 42% to fit thermal budget",
        impact_analysis="Affects gate driver circuit, PCB creepage/clearances, and thermal calculations",
        requested_by="Principal Power Architect",
        affected_stages=[
            LifecycleStage.CIRCUIT_DESIGN.value,
            LifecycleStage.PCB_DESIGN.value,
            LifecycleStage.THERMAL_MECHANICAL.value,
        ],
        workspace_id="test_ws_001",
    )

    assert ecr.ecr_number.startswith("ECR-")
    assert ecr.status == ECRStatus.DRAFT
    assert len(ecr.affected_stages) == 3

    # 2. List ECRs
    ecrs = service.ecr.list_ecrs(workspace_id="test_ws_001")
    assert len(ecrs) == 1
    assert ecrs[0].ecr_id == ecr.ecr_id

    # 3. Review ECR
    reviewed = service.ecr.review_ecr(
        ecr_id=ecr.ecr_id,
        reviewer="Engineering Director",
        status=ECRStatus.APPROVED,
        review_notes="Approved for prototype revision V2. Requires thermal bench re-verification.",
    )
    assert reviewed.status == ECRStatus.APPROVED
    assert reviewed.approved_by == "Engineering Director"
    assert reviewed.approval_date is not None


def test_v20_physical_measurement_ingestion_and_comparison(tmp_path):
    """Verifies laboratory oscilloscope CSV trace ingestion and simulation comparison."""
    service = StudioService(tmp_path)

    # 1. Create a dummy oscilloscope CSV trace
    csv_file = tmp_path / "dso_ch1_vout.csv"
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["# Keysight DSOX3024T Laboratory Capture"])
        writer.writerow(["Time (s)", "Channel 1 (V)"])
        for i in range(100):
            t = i * 1e-6
            v = 1000.0 + 0.5 * (i % 2)  # 1000V DC with 0.5V ripple
            writer.writerow([f"{t:.8e}", f"{v:.4f}"])

    # 2. Record physical measurement
    rec = service.measurements.record_measurement(
        test_name="Output Steady-State Voltage & Ripple Test",
        procedure_reference="TP-HV-004",
        instrument_name="Keysight InfiniiVision DSOX3024T",
        instrument_serial="MY58492014",
        calibration_reference="CAL-2026-9921",
        operator="Senior Test Engineer",
        measured_parameter="Vout_steady_state",
        measured_value=1000.25,
        unit="V",
        simulated_value=1000.00,
        tolerance_min=990.0,
        tolerance_max=1010.0,
        waveform_csv_path=str(csv_file),
        notes="Measured at 24.0V input, full rated 1mA load across 1M precision load bank",
        workspace_id="lab_bench_1",
    )

    assert rec.pass_fail == "PASSED"
    assert rec.waveform_sha256 is not None
    assert rec.error_percentage is not None
    assert rec.error_percentage < 0.1  # Error < 0.1%

    # 3. Verify comparison engine
    sim_t = [i * 1e-6 for i in range(100)]
    sim_v = [1000.0 for _ in range(100)]
    comparison = service.measurements.compare_waveforms(csv_file, sim_t, sim_v)

    assert comparison["status"] == "COMPUTED"
    assert comparison["measured_points"] == 100
    assert abs(comparison["measured_mean"] - 1000.25) < 0.5
    assert comparison["mean_error_percent"] < 0.1
