"""Codex-owned deterministic test double, not an engineering connector or runner."""
import json
from time import sleep

from .integration_contracts import Capability, JobRequest, JobResult, JobStatus, ToolDescriptor, ToolHealth, ToolState, Diagnostic, ErrorCode
from .models import now


class SyntheticAdapter:
    descriptor = ToolDescriptor(tool_id="studio-demo", name="Studio synthetic workflow (software fixture)", category="demo", supported_os=["Windows"], version="1.5.0", license_status="NOT_REQUIRED", license_notes="Mendex-owned in-process software fixture. No engineering model or external executable.", capabilities=[Capability(operation="synthetic-echo", supported=True, tested_version="1.5.0", verification_evidence="tests/contracts/test_v15_contracts.py", diagnostic="Synthetic contract fixture only; not a simulator")])

    def detect(self, configuration):
        return ToolHealth(tool_id="studio-demo", state=ToolState.DETECTED, version="1.5.0", diagnostic="Built-in synthetic software adapter")

    def verify(self, configuration):
        return ToolHealth(tool_id="studio-demo", state=ToolState.READY, version="1.5.0", diagnostic="Only synthetic-echo software fixture is verified; engineering remains NOT_EVALUATED", verified_operations=["synthetic-echo"])

    def supported_operations(self):
        return self.descriptor.capabilities

    def execute(self, request: JobRequest, context):
        start = now()
        if request.operation != "synthetic-echo":
            return JobResult(job_id=request.job_id, tool_id=request.tool_id, status=JobStatus.FAILED, started_at=start, exit_code=2, diagnostics=[Diagnostic(code=ErrorCode.UNSUPPORTED, message="No such synthetic operation")])
        steps = request.parameters.get("steps", 10)
        delay = request.parameters.get("delay_s", 0.02)
        if type(steps) is not int or not 1 <= steps <= 1000 or type(delay) not in (int, float) or not 0 <= delay <= 1:
            return JobResult(job_id=request.job_id, tool_id=request.tool_id, status=JobStatus.FAILED, started_at=start, exit_code=2, diagnostics=[Diagnostic(code=ErrorCode.INVALID_INPUT, message="steps must be 1..1000 and delay_s 0..1")])
        context.log("SYNTHETIC SOFTWARE FIXTURE: no engineering calculation or simulation")
        for step in range(steps):
            context.checkpoint()
            context.cancel_event.wait(delay)
            context.checkpoint()
            context.progress((step + 1) / steps)
        if request.parameters.get("fail", False):
            return JobResult(job_id=request.job_id, tool_id=request.tool_id, tool_version="1.5.0", status=JobStatus.FAILED, started_at=start, exit_code=1, diagnostics=[Diagnostic(code=ErrorCode.EXECUTION_FAILED, message="Intentional synthetic failure fixture")])
        if request.parameters.get("malformed", False):
            return {"bad": "intentional malformed output fixture"}
        output = context.workdir / "synthetic.json"
        output.write_text(json.dumps({"label": "SYNTHETIC SOFTWARE FIXTURE", "engineering_status": "NOT_EVALUATED", "echo": request.parameters.get("echo", "demo"), "input_paths": request.input_paths}, indent=2), encoding="utf-8")
        context.log("Synthetic output written; engineering validity not evaluated")
        return JobResult(job_id=request.job_id, tool_id=request.tool_id, tool_version="1.5.0", status=JobStatus.SUCCEEDED, started_at=start, exit_code=0, outputs=["synthetic.json"])
