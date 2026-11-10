import pytest
from pathlib import Path
from mendex_core.service import StudioService
from mendex_core.integration_contracts import JobRequest, ToolConfiguration, JobStatus
from integrations.v15_connector import LTspiceV15Connector


def test_v16_generic_end_to_end_ltspice_workflow(tmp_path):
    """Phase B (Gate B): Full generic end-to-end simulation workflow using real installed LTspice."""
    service = StudioService(tmp_path)
    engine = service.integrations

    # 1. Register and verify LTspice connector
    connector = LTspiceV15Connector()
    engine.register_reviewed_adapter(connector)
    cfg = ToolConfiguration(executable_path=connector._configured_path)
    engine.configure("ltspice", cfg)
    health = engine.verify("ltspice")

    if health.state != "READY":
        pytest.skip(f"LTspice not READY on this workstation: {health.diagnostic}")

    assert health.version == "26.1.1.0"
    assert "batch_simulate" in health.verified_operations

    # 2. Create synthetic workspace
    ws = engine.create_workspace("Phase B Generic E2E Workflow")
    ws_id = ws["workspace_id"]
    assert ws_id is not None

    # 3. Create versioned synthetic netlist (RC low-pass filter)
    netlist = (
        "* Mendex v1.6 Synthetic Benchmark - RC Filter\n"
        "V1 in 0 5.0\n"
        "R1 in out 10k\n"
        "C1 out 0 100n\n"
        ".tran 10u 2m\n"
        ".end\n"
    )
    src_net = tmp_path / "rc_benchmark.net"
    src_net.write_text(netlist, encoding="utf-8")
    rel_input = engine.attach_input(ws_id, src_net)
    assert rel_input is not None

    # 4. Submit simulation job
    provenance_note = "SYNTHETIC SOFTWARE VERIFICATION; not physical product engineering evidence"
    req = JobRequest(
        workspace_id=ws_id,
        tool_id="ltspice",
        operation="batch_simulate",
        parameters={},
        input_paths=[rel_input],
        provenance=provenance_note,
    )
    job = engine.submit(req)
    assert job.status in (JobStatus.QUEUED, JobStatus.RUNNING)

    # 5. Wait for completion and verify terminal status
    completed = engine.wait(job.request.job_id, timeout=30)
    assert completed.status == JobStatus.SUCCEEDED
    assert completed.result is not None
    assert completed.result.exit_code == 0
    assert completed.result.started_at <= completed.result.ended_at

    # 6. Verify preserved raw files, manifests, and hashes
    manifest = engine.evidence(job.request.job_id)
    assert manifest.job_id == job.request.job_id
    assert manifest.engineering_status == "NOT_EVALUATED"
    assert rel_input in manifest.input_hashes
    assert len(completed.result.outputs) >= 2  # .raw and .log

    # 7. Check evidence integrity
    assert engine.evidence_integrity(job.request.job_id) is True

    # 8. Export report and verify truthful labeling
    report_file = engine.export_report(job.request.job_id)
    assert report_file.exists()
    report_html = report_file.read_text(encoding="utf-8")
    assert "NOT_EVALUATED" in report_html
    assert "ltspice" in report_html
    assert "26.1.1.0" in report_html

    # 9. Reproduce the run in same workspace with new request ID
    req2 = JobRequest(
        workspace_id=ws_id,
        tool_id="ltspice",
        operation="batch_simulate",
        parameters={},
        input_paths=[rel_input],
        provenance=provenance_note,
    )
    job2 = engine.submit(req2)
    completed2 = engine.wait(job2.request.job_id, timeout=30)
    assert completed2.status == JobStatus.SUCCEEDED
    assert completed2.result.exit_code == 0
    assert engine.evidence_integrity(job2.request.job_id) is True

    engine.shutdown()
