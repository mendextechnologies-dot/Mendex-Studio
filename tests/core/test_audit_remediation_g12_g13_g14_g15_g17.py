"""Tests for Audit Remediation G12 (Topology Qualification), G13 (Tool Truthfulness), G14 (Physical Intake), G15 (Dependencies/Decoupling), and G17 (Portability)."""
import math
import tomllib
from pathlib import Path
from uuid import uuid4
import pytest
import numpy as np

from mendex_core.design.models import Requirement
from mendex_core.design.synthesis import CandidateSynthesisEngine
from mendex_core.design.geometry import extract_pcb_geometry
from mendex_core.measurements.service import MeasurementService
from mendex_core.models import Category
from mendex_core.service import StudioService
from integrations.contracts import ToolState, ToolKind, JobRequest
from integrations.adapters.registry import ToolRegistry
from integrations.parsers.ltspice_parser import calculate_waveform_metrics
from mendex_core.bom_generator import to_safe_windows_path


def test_g12_non_buck_candidates_tagged_experimental_with_qualification_notice():
    """G12: Non-buck candidates are explicitly tagged EXPERIMENTAL with qualification notice."""
    reqs = [
        Requirement(parameter="vin_nom", target_value=48.0, unit="V"),
        Requirement(parameter="vout", target_value=12.0, unit="V"),
        Requirement(parameter="iout", target_value=3.0, unit="A"),
        Requirement(parameter="isolation", target_value=1500.0, unit="V"),
        Requirement(parameter="fsw", target_value=100000.0, unit="Hz"),
    ]
    candidates = CandidateSynthesisEngine.synthesize_candidates(reqs)
    assert len(candidates) >= 1
    flyback = next(c for c in candidates if "flyback" in c.topology.lower())
    assert flyback.readiness_status == "EXPERIMENTAL"
    assert "EXPERIMENTAL / DRAFT TOPOLOGY" in flyback.rationale
    assert any("NOT_EVALUATED" in note or "independent engineering review" in note for note in flyback.qualification_notes)


def test_g13_unsupported_execution_adapters_report_detected_not_ready():
    """G13: Adapters inheriting BaseToolAdapter without execute implementation (e.g. FreeCAD, Qucs-S) report DETECTED, not READY."""
    registry = ToolRegistry()
    for tool_id in ["freecad", "qucs-s"]:
        adapter = registry.get(tool_id)
        desc = adapter.descriptor
        if desc.executable_path and Path(desc.executable_path).exists():
            assert desc.state == ToolState.DETECTED
            assert "Automated execution is not implemented" in desc.diagnostic

        # Calling execute directly returns failed result with clear error taxonomy
        req = JobRequest(
            job_id=str(uuid4()),
            workspace_id="test_ws",
            tool_id=tool_id,
            operation="unsupported_op",
            input_paths=[],
            parameters={},
            timeout_s=10,
            workdir=".",
        )
        res = adapter.execute(req)
        assert res.status.value == "FAILED"
        assert "not implemented" in res.error_message.lower()


def test_g14_physical_measurement_intake_fails_closed(tmp_path):
    """G14: Physical measurement intake requires operator identification and finite values."""
    service = StudioService(tmp_path)
    meas = MeasurementService(service)

    # Missing operator must raise ValueError
    with pytest.raises(ValueError, match="operator"):
        meas.record_measurement(
            test_name="Bench Test",
            procedure_reference="TP-001",
            instrument_name="Rigol DSO",
            instrument_serial="DS1054Z",
            calibration_reference="CAL-01",
            operator="",
            measured_parameter="Vout",
            measured_value=5.0,
            unit="V",
        )

    # Non-finite value must raise ValueError
    with pytest.raises(ValueError, match="finite"):
        meas.record_measurement(
            test_name="Bench Test",
            procedure_reference="TP-001",
            instrument_name="Rigol DSO",
            instrument_serial="DS1054Z",
            calibration_reference="CAL-01",
            operator="Lab Tech",
            measured_parameter="Vout",
            measured_value=float("nan"),
            unit="V",
        )


def test_g15_numpy_declared_in_dependencies_and_geometry_in_core():
    """G15: NumPy is explicitly declared in pyproject.toml and geometry extraction is in mendex_core."""
    pyproject_path = Path("pyproject.toml")
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    deps = data["project"]["dependencies"]
    assert any("numpy" in d for d in deps)

    # Geometry extraction must be callable from mendex_core.design.geometry without desktop imports
    geo = extract_pcb_geometry(None)
    assert geo["has_pcb"] is False
    assert geo["footprints"] == []
    assert geo["bbox"]["width"] == 0.0


def test_g17_windows_portability_safe_path_and_waveform_metrics():
    """G17: Handles paths >= 240 chars with \\\\?\\ prefix, and 2-point waveform record does not crash parser."""
    # 1. Path length check
    long_path = "C:/" + "a" * 250 + "/file.docx"
    safe = to_safe_windows_path(long_path)
    assert safe.startswith("\\\\?\\")

    # 2. Waveform parser 2-point fallback (G17 fix)
    time_arr = np.array([0.0, 1e-6])
    val_arr = np.array([5.0, 5.01])
    wf = {"time": time_arr, "V(out)": val_arr}
    metrics = calculate_waveform_metrics(wf, steady_state_ratio=0.8)
    assert metrics["V(out)"]["mean"] == pytest.approx(5.005)
    assert metrics["V(out)"]["p2p"] == pytest.approx(0.01)
