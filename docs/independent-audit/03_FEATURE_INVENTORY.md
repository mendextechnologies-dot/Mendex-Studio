# 03 — Feature Inventory (independent audit, 2026-11-11)

Status legend: IV = Implemented+verified (command run in this audit); INV = Implemented, not verified; P = Partial; PM = Placeholder/mock; M = Missing; DEAD = code present but unreachable from any entry point.
Scratch runs used data root `%TEMP%\mendex-audit\arch`. The test suite was NOT run by this auditor.

| Feature | Location | Status | Evidence / notes |
|---|---|---|---|
| CLI entry `mendex` | `mendex_core/cli.py` | IV | `python -m mendex_core.cli --help` lists 28 subcommands |
| CLI `calculate dowell/losses/steinmetz/flyback` | `cli.py:139-178`, `controller.run_calculation` `controller.py:350` | IV with defect | `calculate dowell` with **no parameters** returned `r_ac_ohm=0.188955` from silent defaults (100 kHz, 2 layers, 0.5 mm, Rdc 0.05 ohm; `controller.py:356-361`). Same for losses (`GENERIC_MOSFET_650V`, rdson 0.025, i_rms 4.0; `controller.py:378-380`). **P1**: numbers not derived from user input |
| CLI `tool list` / MCP `list_tools` | `controller.list_tools :811`, `launch.py` | IV | Detected LTspice 26.1.1.0 and FEMM, state FOUND_UNVERIFIED |
| MCP stdio server | `mcp/server.py`, `mcp/__main__.py` | IV (tools/list only) | 23 tools returned; `tools/call` NOT VERIFIED |
| Workspaces list/create/status | `controller.py:95-170` | INV | merges integration workspaces and products |
| Product/revision CRUD | `service.py`, `controller.py:673-760` | INV | SQLite |
| Specification validate/save | `controller.py:172-218` | INV | |
| Design synthesis (candidates) | `design/synthesis.py`, `controller.generate_design :220` | INV | |
| Native artifact generation (LTspice .asc/.net, FEMM, KiCad, FreeCAD script) | `design/service.py:146-242`, `design/generators/*` | INV | |
| LTspice / FEMM simulation run | `design/ltspice_runner.py`, `femm_runner.py`, `controller.run_simulation :460` | INV | not executed in audit |
| Open artifact / launch tool | `launch.py`, `controller.py:656,844` | INV | |
| Validation summary / report | `controller.py:762,784`, `service.py` | INV | |
| Generic solver execution via `AdapterRegistry` | `mendex_core/adapters/registry.py:63,74` | PM | `raise NotImplementedError("Solver execution is not implemented or qualified")` |
| Integration job orchestration | `integration_service.py` | PM | only registered adapter is `SyntheticAdapter` "studio-demo" (`integration_service.py:54`); `demo_adapter.py` docstring: "deterministic test double, not an engineering connector" |
| integrations adapters (ltspice, femm, kicad, openmodelica, git, freecad, jupyter) | `src/integrations/adapters/*` | P | unsupported ops raise NotImplementedError (`base.py:141`, `kicad.py:80`, `openmodelica.py:96`); reached from UI only via `v15_connector` (`window.py:369`) |
| Workflow engine + nodes | `mendex_core/workflows/*` | INV (backend) | wired in `service.py:81-85`; UI canvas DEAD |
| Visual workflow canvas | `mendex_ui/workflow_canvas/*` | DEAD | imported only by `tests/ui/test_workflow_studio_ui.py` |
| Design Studio panel | `mendex_ui/design_studio_panel.py` (864 LOC) | DEAD | imported only by `tests/ui/test_design_studio_ui.py` |
| AI assistant chat panel | `v17_panels.AIAssistantPanel :927` | DEAD | only instantiated in `panels.KnowledgePanel :73`; `KnowledgePanel` has 0 references |
| AI key setup dialog | `ai_config_dialog.py` | DEAD | used only inside dead KnowledgePanel (`panels.py:82`) and AIAssistantPanel (`v17_panels.py:1273`) |
| Built-in AI copilot / LLM backends | `mendex_core/ai/*`, `intelligence/models.py` | INV (backend live) | instantiated on every `StudioService` (`service.py:79-99`); calls OpenAI/Gemini |
| Dashboard | `v17_panels.EnterpriseDashboardPanel` | INV | nav row 0 |
| Engineering Workspaces (Transformer, DC-DC, Semiconductor, PCB) | `workspace_panels.py`, `pcb_panel.py`, `product_lifecycle_panel.py` | INV | |
| Simulation Center | `simulation_center_panel.py` | INV | uses controller |
| Simulation Lab & waveforms | `v17_panels.SimulationLabPanel`, `waveform_viewer.py` | INV | via `panels.SimulationPanel :27` |
| Component Library | `component_library_panel.py`, `mendex_core/components` | INV | |
| Reports & Evidence | `reports_evidence_panel.py` | INV | |
| Settings | `settings_panel.py` | P | hardcoded "22 deterministic engineering tools" (`:64`) vs 23 actual |
| Command palette, notifications | `command_palette.py`, `notification_center.py` | INV | |
| First-run wizard | `first_run_wizard.py` | DEAD | no importers found |
| Unused v17 panels | `EngineeringWorkspaceManagerPanel :592`, `ResearchCenterPanel :1279`, `ResultsReportsPanel :1384` | DEAD | 0 references |
| Status bar | `window.py:367` | P | static "Approval and simulation execution unavailable" contradicts Simulation Center |
| Lifecycle / ECR / measurements | `mendex_core/lifecycle`, `measurements` | INV | |
| Hardware control / manufacturing approval | none | M (by policy) | per AGENTS.md |
