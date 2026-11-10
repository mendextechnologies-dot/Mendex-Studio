# v1.5 ownership mapped to this repository

Baseline commit: 2055673, app release v0.1.0. The new document uses v1.3/v1.5 plan labels; the repository does not contain an independently verified app release numbered v1.3.

Codex worktree: `C:/Mendex studio codex-v1.5`; branch `codex/v1.5-integration`. Original `C:/Mendex studio` / main remains unchanged. Agent 2 must use a separate worktree/branch from the contract-freeze commit; none is assumed active and no Agent 2 work is fabricated.

| Owner | Actual paths |
|---|---|
| Codex application/persistence | src/mendex_core/service.py, integration_service.py, catalog.py, integration_store.py; schema migrations here preserve legacy data |
| Codex UI/report UX | src/mendex_ui/**, integration_reports.py, tests/ui/**, tests/integration/** |
| Codex fake contract fixture | src/mendex_core/demo_adapter.py, tests/contracts/** |
| Codex catalog metadata | src/mendex_core/config/integration_catalog.json |
| Codex documentation | docs/IMPLEMENTATION_STATUS.md, docs/CONTRACTS.md, docs/DECISIONS.md and handoff/audit docs |
| Codex-owned shared freeze | integration_contracts.py, contracts/v1.5.0/**; scripts/export_v15_contracts.py |
| Agent 2 exclusive | existing src/mendex_core/adapters/**; future runners/**, parsers/**, datasets/**; tests/adapters/**; docs/TOOL_COMPATIBILITY.md and docs/DEPENDENCY_REQUESTS.md |
| Shared, no simultaneous edits | AGENTS.md, pyproject.toml, requirements-lock.txt, legacy contracts; Codex handles agreed changes |

Codex will consume legacy discovery without editing its implementation. Catalog entries may display NOT_CONFIGURED/UNKNOWN/DETECTED, but unsupported operations stay disabled until Agent 2 supplies versioned verify evidence. Dataset UI stores metadata/import records through shared contracts; actual format parsing and license research belong to Agent 2.
