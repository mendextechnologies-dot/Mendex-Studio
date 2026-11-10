from pathlib import Path
from integrations.adapters.commercial_stubs import (
    PLECSAdapter,
    MATLABAdapter,
    AnsysMaxwellAdapter,
    AnsysIcepakAdapter,
    SolidWorksAdapter,
)
from integrations.contracts import JobRequest, JobState, ToolState


def test_commercial_adapters_graceful_missing_execution(tmp_path):
    adapters = [
        PLECSAdapter(),
        MATLABAdapter(),
        AnsysMaxwellAdapter(),
        AnsysIcepakAdapter(),
        SolidWorksAdapter(),
    ]

    for adapter in adapters:
        desc = adapter.descriptor
        assert desc.state in (ToolState.OPTIONAL_UNLICENSED, ToolState.DETECTED)
        assert desc.category == "optional"

        req = JobRequest(
            job_id=f"test_{adapter.tool_id}",
            workspace_id="ws_01",
            tool_id=adapter.tool_id,
            operation="test_op",
        )
        res = adapter.execute(req, workdir=tmp_path)
        assert res.status == JobState.FAILED
        assert res.exit_code != 0
