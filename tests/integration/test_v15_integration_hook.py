from pathlib import Path
from uuid import uuid4
import pytest

from mendex_core.integration_contracts import JobRequest, JobStatus, ToolState
from mendex_core.service import StudioService
from integrations.v15_connector import LTspiceV15Connector, PythonV15Connector


def test_real_ltspice_connector_through_codex_orchestrator(tmp_path):
    service = StudioService(tmp_path)
    engine = service.integrations

    connector = LTspiceV15Connector()
    if not connector._configured_path or not Path(connector._configured_path).exists():
        pytest.skip("LTspice executable not installed on this machine")

    # 1. Register reviewed adapter hook
    engine.register_reviewed_adapter(connector)
    assert "ltspice" in engine.adapters

    # 2. Verify health transitions to READY
    health = engine.verify("ltspice")
    assert health.state == ToolState.READY
    assert health.version == "26.1.1.0"
    assert "batch_simulate" in health.verified_operations

    # 3. Create workspace and stage netlist input
    ws = engine.create_workspace("LTspice Verified Integration WS")
    workspace_id = ws["workspace_id"]

    netlist_text = (
        "* Mendex RC Filter Integration Benchmark\n"
        "V1 in 0 10.0\n"
        "R1 in out 1k\n"
        "C1 out 0 1u\n"
        ".tran 100u 1m\n"
        ".end\n"
    )
    staged_src = tmp_path / "staged_circuit.net"
    staged_src.write_text(netlist_text, encoding="utf-8")
    rel_netlist = engine.attach_input(workspace_id, staged_src)

    # 4. Submit Job to Codex queue
    job_id = uuid4()
    req = JobRequest(
        job_id=job_id,
        workspace_id=workspace_id,
        tool_id="ltspice",
        operation="batch_simulate",
        input_paths=[rel_netlist],
        parameters={},
        timeout_s=20,
        provenance="Mendex Studio v1.5 Verified Smoke",
    )

    record = engine.submit(req)
    assert record.status in (JobStatus.QUEUED, JobStatus.RUNNING, JobStatus.SUCCEEDED)

    # 5. Wait for execution and verify results
    final_record = engine.wait(job_id, timeout=15)
    assert final_record.status == JobStatus.SUCCEEDED
    assert final_record.result is not None
    assert final_record.result.exit_code == 0
    assert any(p.endswith(".raw") for p in final_record.result.outputs)
    assert any(p.endswith(".log") for p in final_record.result.outputs)

    # 6. Check evidence integrity and export draft report
    assert engine.evidence_integrity(job_id) is True
    report_file = engine.export_report(job_id)
    assert report_file.exists()
    assert "DRAFT SOFTWARE FRAMEWORK REPORT" in (report_file.parent / "report.json").read_text(encoding="utf-8")

    engine.shutdown()
