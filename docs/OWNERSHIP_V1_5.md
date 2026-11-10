# v1.5 ownership mapped to this repository

Baseline commit: 2055673, app release v0.1.0. The new document uses v1.3/v1.5 plan labels; the repository does not contain an independently verified app release numbered v1.3.

Codex worktree: `C:/Mendex studio codex-v1.5`; branch `codex/v1.5-integration`. During this session the original `C:/Mendex studio` was switched independently to `antigravity/v1.5-integrations` by Agent 2. Codex did not change that checkout or any of its edits. The shared main ref remains at the released baseline. Agent 2's code is not assumed reviewed or merged merely because its branch exists.

| Owner | Actual paths |
|---|---|
| Codex application/persistence | src/mendex_core/service.py, integration_service.py, catalog.py, integration_store.py; schema migrations here preserve legacy data |
| Codex UI/report UX | src/mendex_ui/**, integration_reports.py, tests/ui/**, tests/integration/** |
| Codex fake contract fixture | src/mendex_core/demo_adapter.py, tests/contracts/** |
| Codex catalog metadata | src/mendex_core/config/integration_catalog.json |
| Codex documentation | docs/IMPLEMENTATION_STATUS.md, docs/CONTRACTS.md, docs/DECISIONS.md and handoff/audit docs |
| Codex-owned shared freeze | integration_contracts.py, contracts/v1.5.0/**; scripts/export_v15_contracts.py |
| Agent 2 exclusive | actual src/integrations/** (adapters, runners, parsers, datasets, connector); existing src/mendex_core/adapters/** retained read-only by Codex; tests/adapters/**; docs/TOOL_COMPATIBILITY.md, docs/ADAPTER_TEST_EVIDENCE.md and docs/DEPENDENCY_REQUESTS.md |
| Shared, no simultaneous edits | AGENTS.md, pyproject.toml, requirements-lock.txt, legacy contracts; Codex handles agreed changes |

Codex will consume legacy discovery without editing its implementation. Catalog entries may display NOT_CONFIGURED/UNKNOWN/DETECTED, but unsupported operations stay disabled until Agent 2 supplies versioned verify evidence. Dataset UI stores metadata/import records through shared contracts; actual format parsing and license research belong to Agent 2.
