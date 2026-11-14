"""Tests for LTspice solver robustness, .meas parsing, execution duration, and error diagnostics."""
from pathlib import Path
import pytest

from integrations.adapters.ltspice import LTspiceAdapter
from integrations.contracts import JobRequest, JobState
from mendex_core.design.ltspice_runner import LTspiceRunner
from mendex_core.design.models import Requirement


def test_ltspice_execution_time_and_netlist_hash(tmp_path):
    """Verifies execution_time_s is non-zero and input netlist SHA-256 is recorded."""
    runner = LTspiceRunner()
    if not runner.is_available:
        pytest.skip("LTspice is not installed on host machine.")

    net = tmp_path / "test_run.net"
    net.write_text(
        "* Test Netlist with .meas\n"
        "V1 in 0 12.0\n"
        "R1 in out 100\n"
        "C1 out 0 100n\n"
        ".tran 0 100u 0 1u\n"
        ".meas TRAN vout_avg AVG V(out) FROM 50u TO 100u\n"
        ".end\n",
        encoding="utf-8",
    )

    req = [Requirement(parameter="vout", target_value=12.0, unit="V", tolerance_pct=5.0)]
    res = runner.run_simulation(net, requirements=req)

    assert res.success is True
    assert res.execution_time_s > 0.0
    assert "vout_avg" in res.measurements
    assert abs(res.measurements["vout_avg"] - 12.0) < 0.5
    assert res.vout_mean_v == res.measurements["vout_avg"]

    # Test through adapter as well
    adapter = LTspiceAdapter()
    job_req = JobRequest(
        job_id="job_ltspice_01",
        workspace_id="ws_01",
        tool_id="ltspice",
        operation="batch_simulate",
        input_paths=[str(net)],
    )
    job_res = adapter.execute(job_req, workdir=tmp_path / "adapter_run")
    assert job_res.status == JobState.SUCCEEDED
    assert job_res.metrics.get("execution_time_s", 0.0) > 0.0
    assert any(d.startswith("netlist_sha256=") for d in job_res.diagnostics)
    net_manifest = next((a for a in job_res.artifacts if a.file_type == "net"), None)
    assert net_manifest is not None
    assert len(net_manifest.sha256) == 64


def test_ltspice_broken_netlist_captures_errors(tmp_path):
    """Verifies that a netlist with missing subcircuits or syntax errors exposes error diagnostics."""
    adapter = LTspiceAdapter()
    if not adapter.verify():
        pytest.skip("LTspice is not installed on host machine.")

    bad_net = tmp_path / "bad.net"
    bad_net.write_text(
        "* Broken Netlist referencing non-existent subcircuit\n"
        "X1 in out NonExistentModel_XYZ\n"
        ".tran 100u\n"
        ".end\n",
        encoding="utf-8",
    )

    job_req = JobRequest(
        job_id="job_ltspice_fail",
        workspace_id="ws_fail",
        tool_id="ltspice",
        operation="batch_simulate",
        input_paths=[str(bad_net)],
    )
    job_res = adapter.execute(job_req, workdir=tmp_path / "fail_run")
    assert job_res.status == JobState.FAILED
    assert job_res.error_message is not None
    assert len(job_res.error_message) > 0
    # Diagnostics must capture the error
    assert any("not defined" in d.lower() or "error" in d.lower() or "can't find" in d.lower() for d in job_res.diagnostics)
