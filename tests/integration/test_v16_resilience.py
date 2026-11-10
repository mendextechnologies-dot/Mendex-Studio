import pytest
from pathlib import Path
from mendex_core.service import StudioService, StudioError
from mendex_core.integration_contracts import JobRequest, ToolConfiguration, JobStatus
from integrations.v15_connector import LTspiceV15Connector


def test_v16_missing_executable_rejection(tmp_path):
    """Gate D: Truthful rejection of missing executable paths without false claims."""
    service = StudioService(tmp_path)
    engine = service.integrations

    # Attempting to configure a non-existent executable path must fail validation
    with pytest.raises(StudioError) as exc_info:
        engine.configure("ltspice", ToolConfiguration(executable_path="C:/NonExistentPath/LTspice.exe"))
    assert exc_info.value.code == "INVALID_INPUT"

    engine.shutdown()


def test_v16_invalid_input_failure_handling(tmp_path):
    """Gate D: Submitting missing/empty netlist fails safely with diagnostics and retained logs."""
    service = StudioService(tmp_path)
    engine = service.integrations
    ws = engine.create_workspace("Invalid Input Test")

    connector = LTspiceV15Connector()
    engine.register_reviewed_adapter(connector)
    cfg = ToolConfiguration(executable_path=connector._configured_path)
    engine.configure("ltspice", cfg)

    req = JobRequest(
        workspace_id=ws["workspace_id"],
        tool_id="ltspice",
        operation="batch_simulate",
        parameters={},
        input_paths=[],  # Deliberately missing netlist
        provenance="SYNTHETIC FAILURE TEST",
    )
    job = engine.submit(req)
    completed = engine.wait(job.request.job_id, timeout=10)
    assert completed.status == JobStatus.FAILED
    assert completed.result is not None
    assert any("No netlist file found" in d.message for d in completed.result.diagnostics)
    assert "FAILED" in engine.logs(job.request.job_id)

    engine.shutdown()


def test_v16_timeout_and_process_cleanup(tmp_path):
    """Gate D: Long running jobs hitting timeout are terminated cleanly with diagnostics."""
    service = StudioService(tmp_path)
    engine = service.integrations
    ws = engine.create_workspace("Timeout Test")

    req = JobRequest(
        workspace_id=ws["workspace_id"],
        tool_id="studio-demo",
        operation="synthetic-echo",
        parameters={"steps": 5, "delay_s": 0.5},
        timeout_s=1,
        provenance="SYNTHETIC TIMEOUT TEST",
    )
    job = engine.submit(req)
    completed = engine.wait(job.request.job_id, timeout=10)
    assert completed.status == JobStatus.TIMED_OUT
    assert completed.result is not None
    assert any("TIMED_OUT" in str(d.code) or "TIMEOUT" in str(d.code) for d in completed.result.diagnostics)

    engine.shutdown()


def test_v16_cancellation_queued_and_running(tmp_path):
    """Gate D: Cancellation stops job execution and marks record CANCELLED."""
    service = StudioService(tmp_path)
    engine = service.integrations
    ws = engine.create_workspace("Cancellation Test")

    jobs = [
        engine.submit(
            JobRequest(
                workspace_id=ws["workspace_id"],
                tool_id="studio-demo",
                operation="synthetic-echo",
                parameters={"steps": 50, "delay_s": 0.05},
                timeout_s=30,
                provenance="SYNTHETIC CANCELLATION TEST",
            )
        )
        for _ in range(3)
    ]
    for job in jobs:
        engine.cancel(job.request.job_id)

    for job in jobs:
        record = engine.wait(job.request.job_id, timeout=10)
        assert record.status == JobStatus.CANCELLED

    engine.shutdown()


def test_v16_tampering_detection_and_integrity(tmp_path):
    """Gate D: Modifying raw simulation artifacts triggers integrity failure."""
    service = StudioService(tmp_path)
    engine = service.integrations
    ws = engine.create_workspace("Tampering Test")

    req = JobRequest(
        workspace_id=ws["workspace_id"],
        tool_id="studio-demo",
        operation="synthetic-echo",
        parameters={"steps": 1, "delay_s": 0},
        provenance="SYNTHETIC INTEGRITY TEST",
    )
    job = engine.submit(req)
    completed = engine.wait(job.request.job_id, timeout=10)
    assert completed.status == JobStatus.SUCCEEDED
    assert engine.evidence_integrity(job.request.job_id) is True

    # Tamper with generated output file
    output_file = engine.job_path(job.request.job_id) / "synthetic.json"
    assert output_file.exists()
    output_file.write_text("TAMPERED RAW OUTPUT CONTENT", encoding="utf-8")

    # Verify integrity detection
    assert engine.evidence_integrity(job.request.job_id) is False
    report_html = engine.export_report(job.request.job_id).read_text(encoding="utf-8")
    assert "EVIDENCE INTEGRITY FAILURE" in report_html

    engine.shutdown()


def test_v16_workspace_recovery_after_restart(tmp_path):
    """Gate D: Database and workspace job history persist and recover seamlessly across restart."""
    service1 = StudioService(tmp_path)
    engine1 = service1.integrations
    ws = engine1.create_workspace("Persistence Test")
    ws_id = ws["workspace_id"]

    req = JobRequest(
        workspace_id=ws_id,
        tool_id="studio-demo",
        operation="synthetic-echo",
        parameters={"steps": 1, "delay_s": 0},
        provenance="SYNTHETIC RECOVERY TEST",
    )
    job = engine1.submit(req)
    engine1.wait(job.request.job_id, timeout=10)
    job_id = job.request.job_id

    engine1.shutdown()

    # Re-open studio on same root directory
    service2 = StudioService(tmp_path)
    engine2 = service2.integrations
    recovered_job = engine2.job(job_id)
    assert recovered_job is not None
    assert recovered_job.status == JobStatus.SUCCEEDED
    assert str(recovered_job.request.workspace_id) == str(ws_id)

    # Verify workspace listing
    workspaces = engine2.list_workspaces()
    assert any(str(w["workspace_id"]) == str(ws_id) for w in workspaces)

    engine2.shutdown()
