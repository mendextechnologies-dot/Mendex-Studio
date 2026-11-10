import json
from time import sleep

import pytest

from mendex_core.integration_contracts import JobRequest, JobStatus, ToolConfiguration, ToolState
from mendex_core.service import StudioError, StudioService


def request(engine, workspace, **kwargs):
    return JobRequest(workspace_id=workspace["workspace_id"], tool_id="studio-demo", operation="synthetic-echo", parameters=kwargs.pop("parameters", {"steps": 1, "delay_s": 0}), provenance="SYNTHETIC SOFTWARE TEST; not engineering evidence", **kwargs)


def test_catalog_settings_and_no_false_ready(tmp_path):
    service = StudioService(tmp_path)
    engine = service.integrations
    catalog = engine.list_tools()
    assert len(catalog) == 18
    assert len({tool.tool_id for tool in catalog}) == 18
    assert sum(tool.optional_paid for tool in catalog) == 5
    assert all(engine.verify(tool.tool_id).state != ToolState.READY for tool in catalog)
    executable = tmp_path / "fixture.exe"
    executable.write_bytes(b"software fixture; never executed")
    engine.configure("plecs", ToolConfiguration(executable_path=str(executable), license_reference="manual review fixture"))
    restarted = StudioService(tmp_path)
    assert restarted.integrations.configuration("plecs").license_reference == "manual review fixture"
    assert restarted.integrations.detect("plecs").state == ToolState.DETECTED
    assert restarted.integrations.verify("plecs").state != ToolState.READY
    executable.unlink()
    assert restarted.integrations.detect("plecs").state == ToolState.NOT_INSTALLED
    with pytest.raises(StudioError, match="existing absolute"):
        engine.configure("plecs", ToolConfiguration(executable_path=str(executable)))


def test_generic_job_evidence_report_retry_and_restart(tmp_path):
    service = StudioService(tmp_path)
    engine = service.integrations
    workspace = engine.create_workspace("Generic software demonstration")
    source = tmp_path / "demo-input.txt"
    source.write_text("Synthetic input only; no product design")
    relative = engine.attach_input(workspace["workspace_id"], source)
    job = engine.submit(request(engine, workspace, input_paths=[relative]))
    complete = engine.wait(job.request.job_id)
    assert complete.status == JobStatus.SUCCEEDED
    assert engine.evidence_integrity(job.request.job_id)
    manifest = engine.evidence(job.request.job_id)
    assert relative in manifest.input_hashes
    assert manifest.engineering_status == "NOT_EVALUATED"
    assert any(a.source_label == "SYNTHETIC" for a in manifest.artifacts)
    report = engine.export_report(job.request.job_id)
    assert "NOT_EVALUATED" in report.read_text(encoding="utf-8")
    retry = engine.retry(job.request.job_id)
    assert retry.request.job_id != job.request.job_id and retry.retry_of == job.request.job_id
    engine.wait(retry.request.job_id)
    engine.shutdown()
    restarted = StudioService(tmp_path).integrations
    assert restarted.job(job.request.job_id).status == JobStatus.SUCCEEDED
    output = engine.job_path(job.request.job_id) / "synthetic.json"
    output.write_text("altered")
    assert not restarted.evidence_integrity(job.request.job_id)
    assert "EVIDENCE INTEGRITY FAILURE" in restarted.export_report(job.request.job_id).read_text(encoding="utf-8")


@pytest.mark.parametrize("parameters,status,code", [({"steps": 1, "delay_s": 0, "fail": True}, "FAILED", "EXECUTION_FAILED"), ({"steps": 1, "delay_s": 0, "malformed": True}, "FAILED", "MALFORMED_OUTPUT"), ({"steps": 100, "delay_s": .02}, "TIMED_OUT", "TIMED_OUT")])
def test_failure_malformed_output_and_timeout(tmp_path, parameters, status, code):
    engine = StudioService(tmp_path).integrations
    workspace = engine.create_workspace()
    job = engine.submit(request(engine, workspace, parameters=parameters, timeout_s=.05 if status == "TIMED_OUT" else 5))
    result = engine.wait(job.request.job_id)
    assert result.status.value == status
    assert result.result.diagnostics[0].code.value == code
    assert engine.evidence_integrity(job.request.job_id)
    assert "engineering NOT_EVALUATED" in engine.logs(job.request.job_id)
    engine.shutdown()


def test_cancel_queued_and_running_no_reuse(tmp_path):
    engine = StudioService(tmp_path).integrations
    workspace = engine.create_workspace()
    jobs = [engine.submit(request(engine, workspace, parameters={"steps": 1000, "delay_s": .02})) for _ in range(3)]
    engine.cancel(jobs[-1].request.job_id)
    assert engine.job(jobs[-1].request.job_id).status == JobStatus.CANCELLED
    assert engine.job(jobs[-1].request.job_id).started_at is None
    for job in jobs[:-1]:
        engine.cancel(job.request.job_id)
    assert all(engine.wait(job.request.job_id).status == JobStatus.CANCELLED for job in jobs)
    assert all(engine.evidence_integrity(job.request.job_id) for job in jobs)
    with pytest.raises(StudioError, match="already exists"):
        engine.submit(jobs[0].request)
    engine.shutdown()


def test_invalid_input_and_unsupported_native_job(tmp_path):
    engine = StudioService(tmp_path).integrations
    workspace = engine.create_workspace()
    with pytest.raises(StudioError, match="missing"):
        engine.submit(request(engine, workspace, input_paths=["missing.txt"]))
    native = JobRequest(workspace_id=workspace["workspace_id"], tool_id="ltspice", operation="simulate", provenance="Unavailable connector check")
    with pytest.raises(StudioError, match="verified"):
        engine.submit(native)
    assert not engine.list_jobs()


def test_manifest_and_staged_input_tampering_are_detected(tmp_path):
    engine = StudioService(tmp_path).integrations
    workspace = engine.create_workspace()
    file = tmp_path / "input.txt"
    file.write_text("synthetic input")
    relative = engine.attach_input(workspace["workspace_id"], file)
    job = engine.submit(request(engine, workspace, input_paths=[relative]))
    engine.wait(job.request.job_id)
    (engine.job_path(job.request.job_id) / relative).write_text("altered")
    assert not engine.evidence_integrity(job.request.job_id)
    retry = engine.retry(job.request.job_id)
    engine.wait(retry.request.job_id)
    (engine.job_path(retry.request.job_id) / "manifest.json").write_text('{"changed":true}')
    assert not engine.evidence_integrity(retry.request.job_id)
    with pytest.raises(StudioError, match="modified"):
        engine.export_report(retry.request.job_id)
    engine.shutdown()


def test_dataset_metadata_review_and_hash(tmp_path):
    engine = StudioService(tmp_path).integrations
    with pytest.raises(StudioError):
        engine.register_dataset("magnet-dataset", "https://example.org/", "demo", "", "software fixture")
    source = tmp_path / "demo.csv"
    source.write_text("fixture_id,label\n1,synthetic\n")
    imported = engine.register_dataset("magnet-dataset", "https://example.org/software-fixture", "synthetic-1", "fixture authorship; not MagNet data/license review", "SYNTHETIC SOFTWARE FIXTURE; no upstream dataset included", source)
    assert imported["sha256"]
    assert imported["review_state"] == "NOT_REVIEWED"
    assert imported["interpretation"].startswith("METADATA_ONLY")
    assert StudioService(tmp_path).integrations.list_datasets() == [imported]


def test_v3_to_v4_preserves_legacy_revisions(tmp_path):
    import sqlite3
    service = StudioService(tmp_path)
    product = service.create_product("REGRESSION", "Existing baseline fixture", "pcb", "Test engineer")
    with sqlite3.connect(service.database) as db:
        for table in ("integration_jobs", "integration_workspaces", "integration_settings", "integration_health", "integration_datasets"):
            db.execute(f"DROP TABLE {table}")
        db.execute("PRAGMA user_version=3")
    migrated = StudioService(tmp_path)
    assert migrated.get_product(product.product_id) == product
    assert migrated.integrations.list_workspaces() == []


def test_cli_generic_demo_and_reopen(tmp_path, capsys):
    from mendex_core.integration_cli import main
    assert main(["--root", str(tmp_path), "new-workspace"]) == 0
    workspace = json.loads(capsys.readouterr().out)
    assert main(["--root", str(tmp_path), "demo", "--workspace", workspace["workspace_id"], "--steps", "1", "--delay", "0"]) == 0
    job = json.loads(capsys.readouterr().out)
    assert job["status"] == "SUCCEEDED"
    assert main(["--root", str(tmp_path), "job", job["request"]["job_id"]]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "SUCCEEDED"


def test_reviewed_hook_rejects_unsubstantiated_ready(tmp_path):
    from types import SimpleNamespace
    from mendex_core.integration_contracts import Capability, ToolHealth
    engine = StudioService(tmp_path).integrations
    adapter = SimpleNamespace(
        descriptor=engine.descriptor("python"),
        detect=lambda configuration: ToolHealth(tool_id="python", state="READY", version="fictional", diagnostic="Bad detect fixture", verified_operations=["version"]),
        verify=lambda configuration: ToolHealth(tool_id="python", state="READY", version="fictional", diagnostic="Unsubstantiated fixture", verified_operations=["version"]),
        supported_operations=lambda: [Capability(operation="version", supported=True)],
    )
    engine.register_reviewed_adapter(adapter)
    assert engine.detect("python").state == ToolState.DETECTED
    assert engine.verify("python").state == ToolState.DETECTED
