from __future__ import annotations

from pathlib import Path
from uuid import uuid4
import pytest

from integrations.adapters.openmodelica import OpenModelicaAdapter
from integrations.contracts import JobRequest, JobState, ToolState


def test_openmodelica_descriptor_and_capabilities():
    adapter = OpenModelicaAdapter()
    desc = adapter.descriptor
    assert desc.tool_id == "openmodelica"
    assert "OpenModelica" in desc.name
    assert desc.category == "high"
    assert "OSMC-PL" in desc.license_name
    assert "check_model" in adapter.supported_operations()
    assert "simulate_modelica" in adapter.supported_operations()
    assert "version" in adapter.supported_operations()

    # Host check
    if adapter.descriptor.executable_path:
        assert desc.state in (ToolState.READY, ToolState.DETECTED)
        assert Path(desc.executable_path).exists()


def test_openmodelica_version_execution(tmp_path):
    adapter = OpenModelicaAdapter()
    if not adapter.descriptor.executable_path or not Path(adapter.descriptor.executable_path).exists():
        pytest.skip("OpenModelica omc compiler not installed on this host")

    job_id = str(uuid4())
    req = JobRequest(
        job_id=job_id,
        workspace_id=str(uuid4()),
        tool_id="openmodelica",
        operation="version",
        workdir=str(tmp_path),
    )

    res = adapter.execute(req, workdir=tmp_path)
    assert res.job_id == job_id
    assert res.status == JobState.SUCCEEDED
    assert res.exit_code == 0
    assert "OpenModelica" in res.stdout


def test_openmodelica_check_model_execution(tmp_path):
    adapter = OpenModelicaAdapter()
    if not adapter.descriptor.executable_path or not Path(adapter.descriptor.executable_path).exists():
        pytest.skip("OpenModelica omc compiler not installed on this host")

    job_id = str(uuid4())
    req = JobRequest(
        job_id=job_id,
        workspace_id=str(uuid4()),
        tool_id="openmodelica",
        operation="check_model",
        parameters={
            "model_name": "FlybackCircuit",
            "model_code": (
                "model FlybackCircuit\n"
                "  parameter Real Vin = 24.0;\n"
                "  Real v_out(start=0.0);\n"
                "equation\n"
                "  der(v_out) = (Vin * 10.0 - v_out) / 0.001;\n"
                "end FlybackCircuit;\n"
            ),
        },
        workdir=str(tmp_path),
    )

    res = adapter.execute(req, workdir=tmp_path)
    assert res.job_id == job_id
    assert res.status == JobState.SUCCEEDED
    assert res.exit_code == 0
    assert "completed successfully" in res.stdout
