from __future__ import annotations

from pathlib import Path
from uuid import uuid4
import pytest

from integrations.adapters.femm import FEMMAdapter
from integrations.contracts import JobRequest, JobState, ToolState


def test_femm_adapter_descriptor_and_capabilities():
    adapter = FEMMAdapter()
    desc = adapter.descriptor
    assert desc.tool_id == "femm"
    assert desc.name == "FEMM"
    assert desc.category == "core"
    assert desc.license_name == "Aladdin Free Public License"
    assert "solve_2d_magnetic" in adapter.supported_operations()
    assert "inductance_matrix" in adapter.supported_operations()
    assert "core_loss" in adapter.supported_operations()

    # If FEMM is installed on host, state should be READY
    if adapter.descriptor.executable_path:
        assert desc.state in (ToolState.READY, ToolState.DETECTED)
        assert Path(desc.executable_path).exists()


def test_femm_adapter_execution_lifecycle(tmp_path):
    adapter = FEMMAdapter()
    if not adapter.descriptor.executable_path or not Path(adapter.descriptor.executable_path).exists():
        pytest.skip("FEMM 4.2 executable not found on host")

    job_id = str(uuid4())
    req = JobRequest(
        job_id=job_id,
        workspace_id=str(uuid4()),
        tool_id="femm",
        operation="solve_2d_magnetic",
        parameters={
            "core_type": "EE",
            "primary_turns": 24,
            "primary_current_a": 2.5,
            "air_gap_mm": 0.5,
            "frequency_hz": 100000.0,
        },
        timeout_s=30,
        workdir=str(tmp_path),
    )

    result = adapter.execute(req, workdir=tmp_path)

    assert result.job_id == job_id
    assert result.tool_id == "femm"
    assert result.status == JobState.SUCCEEDED
    assert result.exit_code == 0

    # Verify generated artifacts
    artifact_paths = [a.relative_path for a in result.artifacts]
    assert any("temp_transformer.fem" in p for p in artifact_paths)
    assert any("temp_transformer.ans" in p for p in artifact_paths)
    assert any("transformer.ans.bmp" in p for p in artifact_paths)
    assert any("results.txt" in p for p in artifact_paths)

    # Verify extracted metrics from real FEA solution
    assert "primary_current" in result.metrics
    assert result.metrics["primary_current"] == pytest.approx(2.5, rel=1e-3)
    assert "primary_flux_linkage" in result.metrics
    assert result.metrics["primary_flux_linkage"] > 0
    assert "primary_inductance_h" in result.metrics
    assert result.metrics["primary_inductance_h"] > 0
