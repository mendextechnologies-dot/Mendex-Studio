"""Codex-owned interface export; run before any agreed contract version change."""
import json
from pathlib import Path

from mendex_core.integration_contracts import ToolDescriptor, ToolConfiguration, ToolHealth, Capability, JobRequest, JobResult, JobRecord, ArtifactManifest, EvidenceManifest

root = Path(__file__).resolve().parents[1]
target = root / "contracts" / "v1.5.0"
target.mkdir(parents=True, exist_ok=True)
for model in (ToolDescriptor, ToolConfiguration, ToolHealth, Capability, JobRequest, JobResult, JobRecord, ArtifactManifest, EvidenceManifest):
    (target / f"{model.__name__}.schema.json").write_text(json.dumps(model.model_json_schema(), indent=2) + "\n", encoding="utf-8")
fixture = JobRequest(job_id="15000000-0000-0000-0000-000000000001", workspace_id="15000000-0000-0000-0000-000000000002", tool_id="studio-demo", operation="synthetic-echo", parameters={"steps": 1, "delay_s": 0, "echo": "synthetic contract fixture"}, provenance="SYNTHETIC SOFTWARE FIXTURE; no engineering evidence")
(target / "job-request.example.json").write_text(fixture.model_dump_json(indent=2) + "\n", encoding="utf-8")
print("Exported v1.5.0 contracts and deterministic request fixture")
