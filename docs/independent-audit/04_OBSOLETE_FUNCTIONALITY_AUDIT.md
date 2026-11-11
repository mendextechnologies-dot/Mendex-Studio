# 04 — Obsolete Functionality Audit (independent audit, 2026-11-11)

Reachability proved by grep of imports (`grep -rlnE "(import|from) ...<module>"` over `src/` and `tests/`) and class-name reference counts in `src/mendex_ui`.

| Item | Location | State | Still referenced by | Verdict |
|---|---|---|---|---|
| Built-in AI copilot | `mendex_core/ai/{gateway,models,config}.py` | Backend remains (live) | `service.py:14` (`UnavailableAIService`, `AIRequest`), `service.py:98-99` (`AICopilotGateway()` on every start); CLI `ai-availability` | Gateway removable after detaching `service.py:98`; keep/replace `UnavailableAIService` used by CLI |
| Internal chat UI | `v17_panels.AIAssistantPanel :927-1278`, `ai_interactive.py` (615 LOC) | Hidden only | only via `panels.KnowledgePanel :73`, which has zero references | Dead; safe to remove together with `KnowledgePanel` |
| Direct AI provider integrations | `intelligence/models.py:155-316` (OpenAI SDK, Gemini via `requests.post :256`), `ai/config.py:29-44` (`GEMINI_API_KEY`, `OPENAI_API_KEY`, `GOOGLE_API_KEY`) | Backend remains (live) | `service.py:79-80` (`EngineeringReasoningOrchestrator`), `service.py:390`, `workflows/nodes/intelligence.py`, `v17_panels.py:1155` | **P1 security**: `ai/config.py` save writes `api_key` in plaintext to `.mendex/ai_config.json` and exports it to `os.environ`. `openai`/`requests` are undeclared deps. Remove provider backends |
| AI key dialog | `mendex_ui/ai_config_dialog.py` | Hidden only | `panels.py:82`, `v17_panels.py:1273` (both inside dead classes) | Safe to remove with above |
| Visual workflow builder / drag-drop canvas | `mendex_ui/workflow_canvas/*` | Hidden only | only `tests/ui/test_workflow_studio_ui.py` | Safe to remove with its test |
| Redundant workflow orchestration | `mendex_core/workflows/*` | Backend remains | `service.py:81-85, 284, 603-609`; tests `test_workflow_*`, `test_v19_*`, `test_v20_acceptance.py` | Not dead; removal needs migration of `service.py:284` table cleanup and tests |
| Duplicate design-generation UI | `mendex_ui/design_studio_panel.py` (864 LOC) | Hidden only | only `tests/ui/test_design_studio_ui.py` | Safe to remove; do NOT remove `mendex_core/design/*` (live via controller) |
| Unnecessary design-studio / v17 screens | `EngineeringWorkspaceManagerPanel`, `ResearchCenterPanel`, `ResultsReportsPanel` (v17_panels.py), `first_run_wizard.py` | Hidden only | 0 references | Safe to remove |
| Duplicate circuit/schematic editors | none found as separate editor modules in `src/mendex_ui` | n/a | n/a | NOT VERIFIED beyond file listing |
| Commercial stubs | `src/integrations/adapters/commercial_stubs.py`, `tests/adapters/test_commercial_stubs.py` | Removed fully (git `D`) | no import remains in `src`; names appear in `tests/core/test_retired_integrations.py`, `tests/integration/test_v19_revised_acceptance.py`, `test_v20_acceptance.py` (retirement assertions; pass/fail NOT VERIFIED) | Removed; run those tests to confirm no broken refs |
| Synthetic demo adapter | `mendex_core/demo_adapter.py` | Backend remains | `integration_service.py:14,54` (sole registered adapter), `tests/contracts/test_v15_contracts.py` | Test double in production path; move to tests |
| v15 connector vs adapters | `src/integrations/v15_connector.py` (741 LOC) | Still referenced | `mendex_ui/window.py:369` (UI bypasses Core), several tests | Redundant with controller tool detection; route via Core |
| `mendex_core/adapters/registry.py` | | Placeholder | `service.py:11` | `NotImplementedError :63,:74` |
| Obsolete navigation | `window.py:155-163` | Simplified to 7 nav items | legacy panels still constructed (`window.py:340-344`: SimulationPanel, ToolPanel, JobsPanel); whether shown NOT VERIFIED | Review; status bar text `window.py:367` obsolete |
| Duplicate launcher | `main.py` vs `src/main.py` | Both present | n/a | Keep one |
| Obsolete dependencies | `requirements-lock.txt` | Out of sync | pins `PySide6_WebEngine`, `PySide6_Pdf` (usage NOT VERIFIED); missing `openai`, `requests` imported in code | Regenerate after AI removal |
| Dead services | `integration_cli.py`, `plugins.py`, `knowledge.py` | Mixed | `knowledge` used by `window.py:15`; `plugins` by `service.py`; `integration_cli` reachability NOT VERIFIED | Keep pending review |

Do not remove: `src/integrations/calculations/*`, `mendex_core/design/*` (synthesis, generators, runners), or `intelligence/calculations.py` until it is consolidated with `integrations/calculations` (workflow nodes depend on it, `workflows/nodes/calculations.py:12`).
