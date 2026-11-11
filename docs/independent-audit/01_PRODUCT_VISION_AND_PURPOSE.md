# 01 — Product Vision and Purpose

Audit date: 2026-11-11. Branch `v2.0-engineering-qualification` at `2d74c87`, plus the uncommitted v2.1 working-tree changes (34 modified/deleted files and the untracked `controller.py`, `mcp/` and new panels).

## Why Mendex Engineering Studio exists
Mendex Electronics needs a systematic way to develop power-electronics products without rebuilding specialised tools (LTspice, FEMM, KiCad, VS Code). An earlier "all-in-one" approach added an internal AI copilot, a workflow canvas, design-studio editors and duplicate generators. The current vision drops that approach in favour of a **command center**:

| Layer | Responsibility |
|---|---|
| AI coding agents (Codex, Claude Code, Antigravity) | Interactive engineering work, via standard interfaces only |
| Mendex MCP server / CLI | Agent-neutral access to Core |
| Mendex Engineering Core | Authoritative, deterministic services: projects, specs, calculations, supported synthesis, simulation orchestration, validation, revisions, evidence, reports |
| Tool adapters → LTspice / FEMM / KiCad | Real solving and CAD |
| Mendex Studio (desktop) | Visibility, traceability, navigation, validation status. Not an editor and not a chat client |

## Non-negotiable product principles used as audit criteria
1. Core is independent of any AI model or agent, and of the UI.
2. Missing critical requirements are never invented. Calculations never run on silent defaults.
3. Generating a file is not a simulation. A passing simulation is not a physical, regulatory or production validation.
4. Unavailable checks stay `NOT_EVALUATED` (AGENTS.md).
5. Frozen baselines and raw evidence are immutable (AGENTS.md).
6. Agents never approve designs. Approval is a human engineering act.
7. The platform works offline (local-first). Supabase is not required.
8. One Core service is used by both the UI and the CLI (AGENTS.md).

## Where the implementation actually stands (summary; see 02–17)
The repo partly realises the vision:
- A CLI and an MCP stdio server front a new `MendexEngineeringController` ([controller.py](../../src/mendex_core/controller.py)).
- The desktop UI has the expected seven navigation slots.
- The test suite is green: **226 passed, 2 skipped** (`.venv` pytest, 2026-11-11). The two skips are the LTspice and FEMM real-solver acceptance tests (`tests/integration/test_v20_acceptance.py:56,93`, "not installed on host machine").

The implementation diverges from the principles above in several places:
- Calculations run on silent defaults (principle 2).
- MCP and the CLI expose an unguarded `delete_product` that destroys evidence (principle 5).
- AI provider code is still wired into Core (principle 1).
- There are two calculation libraries and two service facades (principle 8).
- "Workspaces" are shown to users instead of "Engineering Projects".

The details are in reports 04, 06, 10, 11 and 16.
