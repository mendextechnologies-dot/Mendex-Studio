# v1.5 execution status — Codex

## Gate A: baseline and freeze

Completed: read the complete v1.4 specification/v1.5 addendum; inspected real architecture, UI, SQLite, contracts and extensions; baseline **28 tests passed**. Working features are preserved rather than rebuilt. Separate Codex worktree/branch created; exclusive ownership mapped in docs/OWNERSHIP_V1_5.md.

| Plan area | Baseline evidence | Gap / Codex response |
|---|---|---|
| Products, specs, revisions, evidence, reports | Shared StudioService, SQLite v3, PySide6, regression tests | Preserve and regression-test |
| Registry | 3 native discovery entries plus data-only extension loader | Add separate 18-entry integration catalog without changing Agent 2 discovery |
| Adapters | Legacy discovery with execution unavailable | Publish 1.5.0 contracts and deterministic fake adapter; real connectors remain Agent 2-owned |
| Jobs | Persisted NOT_SUPPORTED availability requests | Add generic workspace queue/history, cancel/retry, progress/logs and evidence |
| Research datasets | No catalog/import UX | Add catalog/provenance/license-review workflow; no proprietary datasets or format-parser claims |
| Commercial tools | None | Optional configuration/status only, never a required dependency |
| Acceptance | Primary v0.1 tests and release | New contract/UI/DB/integration tests; owner demonstration acceptance remains external |

## Codex implementation milestone

Completed:

- Contract freeze **12b56c3**, published on codex/v1.5-integration; 8 contract tests pass. Frozen source/fixtures remain unchanged after that commit.
- All 18 approved names are represented with resource/application/benchmark/runtime/developer categories, references, license-review notes, paid/optional flags and truthful availability. Only the synthetic operation is runnable in this branch.
- Additive SQLite v4 migration preserves legacy v3 products/revisions/evidence and adds tool settings/health, generic workspaces, jobs and dataset-provenance records.
- Tools & Integrations UI, local settings/detect/verify, generic Jobs & Results, cooperative cancel/retry/deadlines, progress, logs, manifest/artifact previews and draft HTML/JSON report export/opening.
- Dataset Catalog registers source/version/license-reference/provenance and optional opaque local files with hashes. It neither downloads nor interprets real upstream datasets and never grants license approval.
- SHA-256 for staged inputs, request snapshots, outputs, logs and the evidence manifest; tampering prevents trusted preview/report use. Every engineering status remains NOT_EVALUATED.
- Original 11 navigation destinations preserved, with 3 appended integration destinations. UI and CLI consume the same application service. No product is created by the integration demo.

Tests: **49 passed** (28 baseline plus new contract, queue, migration, catalog, path/readiness, unsubstantiated-READY rejection, synthetic failure/timeout/cancellation, tamper, dataset metadata, CLI and UI integration tests). `scripts/v15_codex_smoke.py` passed; Tool Center, Jobs, Logs, Evidence and Dataset screenshots were rendered and visually inspected. No native tool was executed for these Codex tests.

Codex implementation is complete for review; branch publication/draft PR provides the handoff. No full-v1.5 release, self-merge or owner acceptance is claimed. Native execution remains disabled until Agent 2's committed operations and smoke evidence are reviewed.

Blocked/external handoff: Agent 2 is actively working on antigravity/v1.5-integrations (observed commit 7ed71de plus uncommitted connector/evidence changes). No completed, reviewed adapter PR has been merged. Native execution, version-specific verification, subprocess runner/process-tree cancellation and dataset parsing cannot be marked complete by Codex. No owner baseline signature, cross-agent review or consolidated human sign-off has been supplied. See docs/AGENT2_HANDOFF.md.

Changed files: integration_contracts.py, demo_adapter.py, catalog.py, integration_service.py, integration_store.py, integration_cli.py, packaged integration catalog JSON, additive StudioService/UI wiring, integration_panels.py, Codex scripts/docs and tests. No Agent 2 source, AGENTS.md or dependency manifest was edited. Next handoff: Agent 2 consumes the freeze and submits committed connectors plus actual logs/manifests for review; Codex reviews/tests before an integration merge.
