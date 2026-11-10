from pathlib import Path
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
