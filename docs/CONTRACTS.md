# Agent integration contract freeze — 1.5.0

Canonical module: `src/mendex_core/integration_contracts.py`. Exported schemas and stable example: `contracts/v1.5.0/`. This new boundary preserves the legacy v0.1 contracts and adapters; it does not relabel them as fully executable v1.5 integrations.

`ToolAdapter` provides descriptor, detect(configuration), verify(configuration), supported_operations(), execute(request, context). Optional launch may be supplied by Agent 2. Detection cannot assert operation readiness. READY requires verified operation names, a specific tested version and repeatable smoke evidence. Commercial connectors also need a local license-review reference; no license keys are stored here.

`JobRequest` is immutable-by-convention after submission: 1.5.0 schema, UUID job/workspace IDs, registered tool/operation, relative input paths, JSON parameters, bounded timeout and provenance. `ExecutionContext` supplies a dedicated workdir, cancellation Event, monotonic deadline, bounded log/progress callbacks and checkpoint(). Agent 2 must implement real subprocess isolation, resource bounds, executable allowlists and process-tree termination; the Codex synthetic adapter is cooperative and starts no processes.

Job lifecycle: QUEUED → RUNNING → SUCCEEDED/FAILED/CANCELLED/TIMED_OUT. Queued jobs can cancel directly. Retry always creates a new job ID and preserves the original evidence. Result output/evidence paths must remain relative to the job workdir. Success means software operation completed, never an engineering pass. Artifacts retain source labels, timestamps, SHA-256, raw/derived distinction, units and NOT_REVIEWED status. EvidenceManifest identity must agree with request/result/artifact IDs; engineering status remains NOT_EVALUATED.

Fake adapter: `src/mendex_core/demo_adapter.py`, operation synthetic-echo. Supports deterministic success, deliberate failure/malformed-result fixtures and cooperative timeout/cancel checks. Contract tests: tests/contracts/test_v15_contracts.py. No hardware, engineering model or native integration is provided by this fixture.

Freeze protocol: commit this boundary before Agent 2 implementation. Agent 2 targets the freeze commit, submits isolated PRs and records supported versions, test logs and smoke artifacts. Change requests are Codex-owned, versioned and accompanied by regenerated schemas/fixtures. No unreviewed cross-boundary merges or shared-worktree edits. Owner sign-off is not fabricated by automated tests.
