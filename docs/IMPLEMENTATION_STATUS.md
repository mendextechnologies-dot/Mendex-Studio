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

In progress: contract tests/schema fixtures and a stable freeze commit, followed by registry/job/evidence UI.

Blocked/external handoff: no Agent 2 adapter PR has been supplied. Native execution, version-specific verification, subprocess runner/process-tree cancellation and dataset parsing cannot be marked complete by Codex. No owner baseline signature, cross-agent review or consolidated human sign-off has been supplied.

Changed files: canonical integration contracts, fake adapter, exported v1.5.0 schemas/fixture and Codex ownership/audit documents. Tests and exact freeze commit are recorded in milestone updates. Next handoff: Agent 2 consumes docs/CONTRACTS.md at freeze and submits isolated, tested connectors.
