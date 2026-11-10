from pathlib import Path
import pytest

from integrations.adapters.ltspice import LTspiceAdapter
from integrations.contracts import JobRequest, JobState, ToolState
from integrations.parsers.ltspice_parser import parse_ltspice_log, parse_ascii_raw_header


def test_ltspice_smoke_run(tmp_path):
    adapter = LTspiceAdapter()
    if adapter.descriptor.state not in (ToolState.READY, ToolState.DETECTED):
        pytest.skip("LTspice is not installed on this machine")

    # Simple RC circuit with a transient analysis
    netlist_text = (
        "* Mendex RC Filter Benchmark\n"
        "V1 in 0 10.0\n"
        "R1 in out 1k\n"
        "C1 out 0 1u\n"
        ".tran 100u 1m\n"
        ".end\n"
    )

    req = JobRequest(
        job_id="ltspice_smoke_01",
        workspace_id="ws_01",
        tool_id="ltspice",
        operation="batch_simulate",
        parameters={"netlist_text": netlist_text},
        timeout_s=15,
    )

    res = adapter.execute(req, workdir=tmp_path)
    assert res.status == JobState.SUCCEEDED
    assert res.exit_code == 0
    assert res.log_path is not None
    assert Path(res.log_path).exists()

    # Check generated files
    assert (tmp_path / "circuit.log").exists()
    assert (tmp_path / "circuit.raw").exists()

    # Check metrics extracted
    assert "elapsed_time_s" in res.metrics
    assert "thread_count" in res.metrics
    assert res.metrics.get("error_count", 0) == 0

    # Check artifact manifests
    assert len(res.artifacts) >= 2
    raw_manifest = next((a for a in res.artifacts if a.file_type == "raw"), None)
    assert raw_manifest is not None
    assert len(raw_manifest.sha256) == 64


def test_ltspice_missing_input_error(tmp_path):
    adapter = LTspiceAdapter()
    req = JobRequest(
        job_id="ltspice_fail_01",
        workspace_id="ws_01",
        tool_id="ltspice",
        operation="batch_simulate",
        parameters={},
    )
    res = adapter.execute(req, workdir=tmp_path)
    assert res.status == JobState.FAILED
    assert "No valid netlist" in res.error_message


def test_ltspice_parser_with_sample_log(tmp_path):
    sample_log = (
        "LTspice 26.1.1 for Windows\n"
        "Circuit: C:\\test\\circuit.net\n"
        "solver = Normal\n"
        "Maximum thread count: 16\n"
        "Direct Newton iteration succeeded in finding operating point.\n"
        "V(out): 9.999 voltage\n"
        "V(in): 10.0 voltage\n"
        "Total elapsed time: 0.042 seconds.\n"
        "WARNING: Time step too small on step 12\n"
    )
    log_file = tmp_path / "sample.log"
    log_file.write_text(sample_log, encoding="utf-8")

    parsed = parse_ltspice_log(log_file)
    assert parsed.metrics["elapsed_time_s"] == 0.042
    assert parsed.metrics["thread_count"] == 16.0
    assert parsed.metrics["warning_count"] == 1.0
    assert parsed.metrics["error_count"] == 0.0
    assert parsed.operating_points["V(out)"] == 9.999
    assert parsed.operating_points["V(in)"] == 10.0
