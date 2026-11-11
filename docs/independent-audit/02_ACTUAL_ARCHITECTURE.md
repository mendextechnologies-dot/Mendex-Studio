# 02 — Actual Architecture (independent audit, 2026-11-11)

Scope: read-only inspection of working tree on branch `v2.0-engineering-qualification` (34 files modified, `git diff --stat`: 1913+/808-, plus many untracked v2.1 files). Docs were not trusted; all claims below are from code or command output.

## Languages / frameworks
- Python 3.13 (`pyproject.toml`: `requires-python = ">=3.13,<3.14"`), Pydantic 2, PySide6 6.x. Declared deps only `pydantic`, `PySide6` (+ `pytest` dev).
- Undeclared runtime imports: `requests` and `openai` in `src/mendex_core/intelligence/models.py:175,243` (lazy). Present in `.venv` (`openai-2.54.0`, `requests-2.34.2`) but absent from `pyproject.toml` and `requirements-lock.txt`.

## Entry points
| Entry | File | Target |
|---|---|---|
| Desktop | `main.py` (repo root) and `src/main.py` (near-duplicate files) | `mendex_ui.__main__.main` |
| Desktop module | `src/mendex_ui/__main__.py` | `StudioWindow(StudioService(--root, default cwd))` |
| CLI console script | `pyproject.toml [project.scripts] mendex = "mendex_core.cli:main"` | `src/mendex_core/cli.py` — verified `--help` lists 28 subcommands (legacy `products/tools/plugins/rules/ai-availability/...` plus v2.1 `workspace/specification/design/calculate/simulation/artifact/tool`) |
| MCP stdio | `python -m mendex_core.mcp --root` → `src/mendex_core/mcp/__main__.py` → `MendexMCPServer` (`mcp/server.py`) | verified `tools/list` returns JSON-RPC result; 23 tool names in `_build_tools_schema` (server.py:39–333). Settings UI claims "22" (`mendex_ui/settings_panel.py:64`) — mismatch. |
| Legacy integration CLI | `src/mendex_core/integration_cli.py` | NOT VERIFIED whether wired into `cli.py` |

All entry points default `--root` to the current working directory. Consequence observed: repo root already contains runtime data (`engineering_designs/39f88be3-...json`, `femm_in.tmp`) — runtime output is leaking into the source tree.

## Persistence
- SQLite: `<root>/.mendex/studio.sqlite3` (`service.py:30`). Tables: products, revisions, tool_settings, validations, reports, runs (`service.py:47–65`); integration_* and activities (`integration_store.py:6–37`); workflows (`workflows/storage.py` via `service.py:81–84`); engineering_change_requests (`lifecycle/ecr.py:58`); lifecycle_approvals (`lifecycle/engine.py:80`); measurements (`measurements/service.py:35`).
- JSON files: designs at `<root>/engineering_designs/<id>.json` (`design/service.py:41,63`); AI config incl. **plaintext API key** at `<root>/.mendex/ai_config.json` (`ai/config.py` save function writes `"api_key"`); generated CAD files (.net/.asc/.fem/FreeCAD scripts) written by `design/service.py:146,164,216,242`.
- Two stores for one domain: products/revisions in SQLite, designs in loose JSON; "workspaces" are a merge of integration workspaces and products (`controller.py:95–122`).

## Data models
- `mendex_core/models.py` (Category, Specification, Product, Revision, Lifecycle)
- `mendex_core/evidence.py` (ValidationRecord, Report, SimulationRun, ManualCheck)
- `mendex_core/integration_contracts.py` (JobRequest/JobRecord/ToolHealth...) AND `src/integrations/contracts.py` (separate contract set for `integrations.adapters`)
- `mendex_core/design/models.py`, `design/ir.py` (Requirement, EngineeringDesign, DesignCandidate...)
- `mendex_core/workflows/types.py|contracts.py`, `ai/models.py`, `intelligence/*`

## Actual dependency graph
```
 Codex/Claude ──stdio──> mcp/server.py ─┐
 shell ──────────────> cli.py ──────────┼──> controller.py (MendexEngineeringController, 857 LOC)
                         cli.py ────────┘        │  (legacy cmds call StudioService directly)
 Desktop UI (window.py) ─┬─> StudioService (service.py) <── controller wraps it
                         ├─> controller.py   (simulation_center_panel.py, window.py)
                         └─> integrations.v15_connector (window.py:369, direct import, bypasses Core)
 StudioService ──> integration_service.py ──> demo_adapter.SyntheticAdapter (only adapter registered, :54)
              ──> adapters/registry.py (solver exec raises NotImplementedError :63,:74)
              ──> workflows/ (engine, nodes) ──> intelligence/calculations.py
              ──> intelligence/ (reasoning, models -> OpenAI/Gemini HTTP)
              ──> ai/ (AICopilotGateway, service.py:98)
              ──> lifecycle/, measurements/, components/, plugins, rules, knowledge
 controller ──> design/service.py (EngineeringDesignService) ──> design/synthesis, generators,
                                                                   ltspice_runner, femm_runner
            ──> integrations/calculations/* (run_calculation, controller.py:355–425)
            ──> launch.py (open_native, launch_tool)
 integrations/adapters/* (ltspice, femm, kicad, openmodelica, git...) <── v15_connector
```

## Authoritative source of engineering data
No single authority. Products/revisions/validations: SQLite via `StudioService`. Designs/candidates: JSON via `design/service.py`. Calculations: `integrations/calculations/*` for CLI/MCP, but `intelligence/calculations.py` (DeterministicCalculationService) for workflows/AI. Tool health: `controller.list_tools` (launch.py detection) vs `integrations/v15_connector` (UI) vs `integration_service` catalog.

## Duplicate logic
| Concern | Implementations |
|---|---|
| Core façade | `service.py` (StudioService), `controller.py` (wraps it), `integration_service.py`, `design/service.py` |
| Dowell / Steinmetz / flyback / semiconductor losses | `src/integrations/calculations/{winding_losses,power_losses,transformer_design}.py` AND `src/mendex_core/intelligence/calculations.py:66,97,156,184` |
| Tool adapters | `src/integrations/adapters/*` + `v15_connector.py`; `src/mendex_core/adapters/registry.py`; `design/ltspice_runner.py`/`femm_runner.py`; `integration_service` + `demo_adapter.py` |
| Contracts | `integration_contracts.py` vs `integrations/contracts.py` |
| AI | `mendex_core/ai/*` vs `mendex_core/intelligence/models.py` |
| Launchers | `main.py` vs `src/main.py` |

## Intended vs actual
Intended: Agents → MCP/CLI → Core → calc/design/validation → tool adapters → evidence → Studio.
Actual deviations:
1. UI bypasses Core for tool listing (`window.py:369` imports `integrations.v15_connector`).
2. UI uses both `StudioService` and `controller` — no single Core service (violates AGENTS.md "single core service").
3. Simulations in controller go through `design/ltspice_runner`/`femm_runner`, not through `integrations/adapters` or `integration_service` job/evidence pipeline (`controller.py:460+`).
4. Two calculation libraries can diverge.
5. Built-in AI/LLM path (ai/, intelligence/models.py) still instantiated in Core (`service.py:79–99`) despite agent-driven model.
