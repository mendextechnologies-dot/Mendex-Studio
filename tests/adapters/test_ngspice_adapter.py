from pathlib import Path
from uuid import uuid4
import pytest

from integrations.adapters.ngspice import NgspiceAdapter
from integrations.adapters.registry import ToolRegistry
from integrations.contracts import JobRequest, JobState, ToolState


def test_ngspice_descriptor_and_detection():
    adapter = NgspiceAdapter()
    desc = adapter.descriptor
    assert desc.tool_id == "ngspice"
    assert desc.name == "ngspice"
    assert "BSD" in desc.license_name
    assert "batch_simulate" in adapter.supported_operations()

    # Truthful detection on host
    det = adapter.detect()
    assert det.state in (ToolState.READY, ToolState.NOT_INSTALLED, ToolState.DETECTED)


def test_ngspice_missing_input_error(tmp_path):
    adapter = NgspiceAdapter()
    fake_exe = tmp_path / "fake_ngspice.exe"
    fake_exe.write_text("binary", encoding="utf-8")
    adapter._descriptor = adapter._descriptor.model_copy(
        update={"state": ToolState.READY, "executable_path": str(fake_exe)}
    )

    req = JobRequest(
        job_id="ngspice_err_01",
        workspace_id="ws_ng",
        tool_id="ngspice",
        operation="batch_simulate",
        parameters={},
    )
    res = adapter.execute(req, workdir=tmp_path)
    assert res.status == JobState.FAILED
    assert "No valid netlist" in res.error_message


def test_ngspice_registry_inclusion():
    reg = ToolRegistry()
    adapter = NgspiceAdapter()
    reg.register(adapter)
    assert reg.get("ngspice") is not None
    assert reg.get("ngspice").descriptor.name == "ngspice"


def test_ngspice_real_execution(tmp_path):
    adapter = NgspiceAdapter()
    if adapter.descriptor.state != ToolState.READY or not adapter.descriptor.executable_path:
        pytest.skip("ngspice is not installed on this host")

    netlist = (
        "* Mendex RC Benchmark\n"
        "V1 in 0 10.0\n"
        "R1 in out 1k\n"
        "C1 out 0 1u\n"
        ".tran 100u 1m\n"
        ".end\n"
    )

    req = JobRequest(
        job_id=str(uuid4()),
        workspace_id=str(uuid4()),
        tool_id="ngspice",
        operation="batch_simulate",
        parameters={"netlist_text": netlist},
        workdir=str(tmp_path),
    )

    res = adapter.execute(req, workdir=tmp_path)
    assert res.status == JobState.SUCCEEDED
    assert res.exit_code == 0
    artifact_names = [Path(a.relative_path).name for a in res.artifacts]
    assert "circuit.raw" in artifact_names or "circuit.cir" in artifact_names
