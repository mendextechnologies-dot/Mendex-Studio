from threading import Event
from time import monotonic
from uuid import uuid4

import pytest
from pydantic import ValidationError

from mendex_core.demo_adapter import SyntheticAdapter
from mendex_core.integration_contracts import ExecutionContext, JobRequest, JobResult, JobStatus, EvidenceManifest, ToolConfiguration


def test_fake_adapter_frozen_boundary(tmp_path):
    adapter = SyntheticAdapter()
    assert adapter.verify(ToolConfiguration()).verified_operations == ["synthetic-echo"]
    request = JobRequest(tool_id="studio-demo", operation="synthetic-echo", parameters={"steps": 1, "delay_s": 0}, provenance="Synthetic contract test")
    messages = []
    context = ExecutionContext(tmp_path, Event(), monotonic() + 5, messages.append, lambda value: None)
    result = adapter.execute(request, context)
    assert result.status == JobStatus.SUCCEEDED
    assert result.outputs == ["synthetic.json"]
    assert "SYNTHETIC" in (tmp_path / result.outputs[0]).read_text()
    manifest = EvidenceManifest(job_id=request.job_id, request=request, result=result, artifacts=[])
    assert manifest.engineering_status == "NOT_EVALUATED"
    with pytest.raises(ValidationError):
        EvidenceManifest(job_id=uuid4(), request=request, result=result, artifacts=[])


@pytest.mark.parametrize("path", ["../secret", "C:/secret", "C:secret", "\\\\server\\share", "part/../../secret", "/tmp/secret"])
def test_contract_rejects_input_traversal(path):
    with pytest.raises(ValidationError):
        JobRequest(tool_id="studio-demo", operation="synthetic-echo", input_paths=[path], provenance="test")


def test_schema_version_and_false_success():
    with pytest.raises(ValidationError):
        JobRequest(schema_version="9.0", tool_id="test", operation="test", provenance="test")
    with pytest.raises(ValidationError):
        JobResult(job_id=uuid4(), tool_id="test", status="SUCCEEDED", exit_code=None)
