# Mendex Engineering Studio v2.1 — Step-by-Step Implementation Plan

**Target Version:** v2.1.0  
**Implementation Strategy:** Non-destructive, incremental refactoring with continuous test verification.  
**Baseline Test Gate:** 206 passed, 2 skipped (100% green).  

---

## Phase 1: Audit & Architecture Alignment (COMPLETED)
- [x] Comprehensive repository audit covering all 23 subsystems.
- [x] Authored `docs/V21_EXISTING_SYSTEM_AUDIT.md`.
- [x] Authored `docs/V21_TARGET_ARCHITECTURE.md`.
- [x] Checkpoint baseline commit created on `v2.0-engineering-qualification` branch (`2d74c87`).

---

## Phase 2: Mendex Engineering CLI (`mendex_core/cli.py`)
- [ ] Implement enhanced modular CLI supporting:
  - `workspace create`, `workspace list`, `workspace open`
  - `specification validate`, `specification show`
  - `design generate`, `design status`
  - `calculation run` (Dowell AC factor, Steinmetz loss, power dissipation)
  - `simulation run`, `simulation status`, `simulation results`
  - `tool list`, `tool check`, `tool open`
  - `revision list`, `revision compare`
  - `report generate`
- [ ] Ensure `--json` output flag is universally supported for automation by Codex and Claude Code.
- [ ] Implement CLI integration tests in `tests/core/test_v21_cli.py`.

---

## Phase 3: Standardized Agent-Independent MCP Server (`mendex_core/mcp/`)
- [ ] Implement robust local MCP server over JSON-RPC 2.0 stdio transport.
- [ ] Zero agent-specific dependencies in Core (protocol standard JSON-RPC).
- [ ] Implement typed MCP tools:
  - `list_workspaces`, `create_workspace`, `get_workspace_status`
  - `validate_specification`, `create_specification`
  - `generate_design`, `get_design`, `list_design_candidates`
  - `run_engineering_calculations`, `get_calculation_results`
  - `run_simulation`, `get_simulation_status`, `get_simulation_results`
  - `list_design_artifacts`, `open_artifact`
  - `list_design_revisions`, `create_design_revision`
  - `generate_engineering_report`, `get_validation_summary`
- [ ] Implement MCP server tests in `tests/core/test_v21_mcp.py` verifying protocol compliance, tool discovery, and execution.

---

## Phase 4: VS Code + Codex & Claude Code Configuration & Guides
- [ ] Author `docs/V21_CODEX_INTEGRATION_GUIDE.md` detailing setup for both OpenAI Codex and Anthropic Claude Code.
- [ ] Author `docs/V21_CLI_REFERENCE.md` and `docs/V21_MCP_TOOL_REFERENCE.md`.
- [ ] Provide ready-to-use client configuration files:
  - `.vscode/mcp.json` / `codex_config.json`
  - `claude_desktop_config.json` / Claude Code MCP registration command
  - Update `AGENTS.md` with standardized repository guidelines.

---

## Phase 5: Studio UI Simplification (7-Item Navigation)
- [ ] Refactor `src/mendex_ui/window.py` to establish clean 7-item navigation:
  1. `Dashboard`
  2. `Engineering Workspaces` (with 9 sub-views)
  3. `Simulation Center` (with embedded WaveformViewerWidget)
  4. `Component Library`
  5. `Engineering Tools`
  6. `Reports & Evidence`
  7. `Settings`
- [ ] Remove obsolete in-app AI chat panel, API key setup dialogs, and visual workflow canvas from primary navigation.
- [ ] Eliminate duplicate design creation dialogs and consolidate into unified workspace generation.
- [ ] Verify dark theme contrast and responsiveness.

---

## Phase 6: Live Synchronization & Native Tool Launching
- [ ] Ensure SQLite change detection and workspace filesystem polling updates Studio when Codex/Claude executes operations.
- [ ] Verify native application launching (`open_native`) strictly opens correct CAD tools (.step to FreeCAD, .kicad_sch to KiCad eeschema, .kicad_pcb to KiCad pcbnew, .asc to LTspice).

---

## Phase 7: End-to-End Verification & Milestone Reports
- [ ] Run full regression test suite (all existing + new CLI & MCP tests).
- [ ] Demonstrate end-to-end generic test flow (Workspace -> Spec -> Synthesis -> LTspice Simulation -> Waveform Viewing -> KiCad Launch -> Dossier Export).
- [ ] Author remaining v2.1 documentation suite:
  - `docs/V21_ENGINEERING_WORKSPACE_GUIDE.md`
  - `docs/V21_UI_SIMPLIFICATION_REPORT.md`
  - `docs/V21_END_TO_END_TEST_REPORT.md`
  - `docs/V21_FINAL_IMPLEMENTATION_SUMMARY.md`
- [ ] Update `docs/implementation-checklist.md`.
