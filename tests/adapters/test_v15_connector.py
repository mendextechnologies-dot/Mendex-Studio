from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
import pytest

from integrations.v15_connector import (
    LTspiceV15Connector,
    PythonV15Connector,
    GitV15Connector,
    V15ConnectorRegistry,
)


class MockExecutionContext:
    def __init__(self, workdir: Path):
        self.workdir = workdir
        self.cancel_event = None

    def checkpoint(self):
        pass


def test_v15_registry_contains_18_connectors():
    connectors = V15ConnectorRegistry.all()
    assert len(connectors) == 18

    tool_ids = {c.descriptor.tool_id for c in connectors}
    expected_ids = {
        "switchlossdb", "magnet-dataset", "magnet-ml-benchmarks", "kicad", "femm",
        "magnet-princeton", "ltspice", "plecs", "matlab-simulink", "ansys-maxwell",
        "ansys-icepak", "freecad", "qucs-s", "openmodelica", "python", "jupyter",
        "git", "solidworks",
    }
    assert tool_ids == expected_ids


def test_v15_ltspice_connector_lifecycle(tmp_path):
    connector = LTspiceV15Connector()
    if not connector._configured_path or not Path(connector._configured_path).exists():
        pytest.skip("LTspice is not installed on this machine")

    desc = connector.descriptor
    assert desc.tool_id == "ltspice"
    assert desc.version == "26.1.1.0"
    assert desc.schema_version == "1.5.0"

    health_detected = connector.detect(type("ToolConfig", (), {"executable_path": None})())
    assert health_detected.state == "DETECTED"
    assert health_detected.version == "26.1.1.0"

    health_ready = connector.verify(type("ToolConfig", (), {"executable_path": None})())
    assert health_ready.state == "READY"
    assert health_ready.verified_operations == ["batch_simulate"]

    netlist_text = (
        "* Mendex RC Filter Benchmark\n"
        "V1 in 0 10.0\n"
        "R1 in out 1k\n"
        "C1 out 0 1u\n"
        ".tran 100u 1m\n"
        ".end\n"
    )
    netlist_file = tmp_path / "circuit.net"
    netlist_file.write_text(netlist_text, encoding="utf-8")

    req = type(
        "JobRequest",
        (),
        {
            "job_id": uuid4(),
            "workspace_id": uuid4(),
            "tool_id": "ltspice",
            "operation": "batch_simulate",
            "input_paths": ["circuit.net"],
            "parameters": {},
            "timeout_s": 15,
            "provenance": "Mendex test",
        },
    )()

    context = MockExecutionContext(tmp_path)
    res = connector.execute(req, context)

    assert res.status == "SUCCEEDED"
    assert res.exit_code == 0
    assert "circuit.raw" in res.outputs
    assert "circuit.log" in res.outputs
    assert "circuit.net" in res.evidence_paths


def test_v15_python_connector_lifecycle(tmp_path):
    connector = PythonV15Connector()
    assert connector.descriptor.tool_id == "python"

    script = tmp_path / "calc.py"
    script.write_text("print('PYTHON_CONNECTOR_OK')\n", encoding="utf-8")

    req = type(
        "JobRequest",
        (),
        {
            "job_id": uuid4(),
            "workspace_id": uuid4(),
            "tool_id": "python",
            "operation": "run_script",
            "input_paths": ["calc.py"],
            "parameters": {},
            "timeout_s": 10,
            "provenance": "Python test",
        },
    )()

    context = MockExecutionContext(tmp_path)
    res = connector.execute(req, context)
    assert res.status == "SUCCEEDED"
    assert res.exit_code == 0
    assert "python_runner.log" in res.outputs


def test_v15_git_connector_lifecycle(tmp_path):
    connector = GitV15Connector()
    assert connector.descriptor.tool_id == "git"

    req = type(
        "JobRequest",
        (),
        {
            "job_id": uuid4(),
            "workspace_id": uuid4(),
            "tool_id": "git",
            "operation": "status",
            "input_paths": [],
            "parameters": {},
            "timeout_s": 10,
            "provenance": "Git test",
        },
    )()

    context = MockExecutionContext(tmp_path)
    res = connector.execute(req, context)
    assert res.status == "SUCCEEDED"
    assert res.exit_code == 0
