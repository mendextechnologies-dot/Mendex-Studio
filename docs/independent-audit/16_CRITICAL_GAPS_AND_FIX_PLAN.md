# 16 — Critical Gaps and Fix Plan

Status key: **FIXED** = changed and covered by tests in this session; **OPEN** = not yet addressed.
Regression guards: `tests/core/test_engineering_integrity_guards.py` (22 tests). Full suite after AI removal: 250 passed, 1 skipped (3 copilot tests removed with the feature).

## P0 — engineering integrity (fabricated or destroyable evidence)
| # | Issue | Status | Fix |
|---|---|---|---|
| P0-1 | `delete_product` / `delete_project` (MCP, CLI, UI) erased revisions, runs, validations, reports, approvals and measurements with no frozen-baseline check | **FIXED** | `StudioService.delete_product` raises `DELETE_BLOCKED` unless every revision is draft and no evidence exists. The check runs inside the same `BEGIN IMMEDIATE` transaction (`src/mendex_core/service.py`). |
| P0-2 | FEMM substituted a hard-coded 0.285 T when the solved field was zero and reported `SOLVED_CONVERGED`/`PASSED` | **FIXED** | Fallback removed; a zero or unparseable field gives `NOT_EVALUATED` with the reason. A Lua-script exit 0 is now `SCRIPT_COMPLETED`/`NOT_EVALUATED`. Result defaults changed from `PASSED` to `NOT_EVALUATED` (`design/femm_runner.py`). |
| P0-3 | LTspice runs with no requirements were `PASSED`. The log was never read and convergence was hard-coded `CONVERGED`. | **FIXED** | `.log` parsed (UTF-16/8-bit); errors fail the run and floating nodes count as errors. No requirements gives `NOT_EVALUATED`. Empty `.raw` gives `success=False` (`design/ltspice_runner.py`). |
| P0-4 | Flyback netlist left the MOSFET gate floating (0 V output, still `PASSED`) and injected the buck freewheel diode | **FIXED** | Gate connected in IR, and an open-loop CCM duty parameter added (`design/synthesis.py`). The generator drives each switch gate relative to its own source, and `D_FW` is emitted only if an `SW` node exists. Real LTspice: 12.51 V vs 12 V. |
| P0-5 | KiCad ERC/DRC on documents with no symbols/footprints reported `passed` | **FIXED** | `KiCadLifecycleService.run_erc/run_drc` add `structure` and `evaluation`; unpopulated gives `NOT_EVALUATED` and `passed=False`. |
| P0-6 | Synthesis accepted Vout<0 (negative L/C) and crashed on fsw=0/Iout=0. It also silently defaulted Vin/Vout/Iout/fsw. | **FIXED** | Critical requirements are required, finite and positive, and the input range is checked. Iout may be derived from an explicit Pout. |
| P0-7 | Test suite launched real LTspice/KiCad/FreeCAD GUIs on the engineer's desktop | **FIXED** | `tests/conftest.py` autouse fixture records launches instead of spawning processes. |

## P1 — trustworthiness
| # | Issue | Status | Fix / plan |
|---|---|---|---|
| P1-1 | Calculations ran on silent defaults (`calculate dowell` with no args returned a value; "N87" Steinmetz constants unsourced) | **FIXED** | All numeric inputs required in the controller and CLI; results echo `inputs`. |
| P1-2 | User Vin range and ripple were silently replaced by ±20 % and 1 %, because synthesis read the wrong keys | **FIXED** | Range read from the requirement's `min_value`/`max_value`, and the ripple requirement used for C. The controller no longer invents ±20 % and returns `assumptions`. |
| P1-3 | `open_tool_file` accepted any absolute path | **FIXED** | Confined to the data root. |
| P1-4 | Simulation picked the first `.net`/`.lua` found | **FIXED** | Ambiguity raises an error listing the candidates. Job records hold netlist/raw SHA-256, verdict, log errors/warnings, and a note that the requested duration was not applied. |
| P1-5 | Peak current reported start-up inrush | **FIXED** | Steady-state window only. |
| P1-6 | Acceptance tests skipped real LTspice/FEMM ("not installed") and asserted nothing analytical | **FIXED** | Real RC analytical check (1 %). The FEMM skip now states the true reason. |
| P1-7 | Data root defaulted to the current working directory; `mcp_config.json` used `--root .` | **FIXED** | Owner decision: data lives in the project root. `mendex_core/paths.py::default_data_root()` returns `MENDEX_DATA_ROOT`, else the project root. It never falls back to the current directory. Used by the CLI, integration CLI, MCP, UI and controller. `mcp_config.json` now uses absolute paths. |
| P1-8 | Evidence hashes recorded but never re-verified; external edits undetected | OPEN | Add a `verify_evidence(revision)` core service that recomputes SHA-256 and marks results stale. |
| P1-9 | Non-atomic writes (`write_text`) | OPEN | Write to a temp file, then `os.replace`. |
| P1-10 | Approval has no actor or role check | OPEN | Require a human reviewer identity on lifecycle approval; keep approval out of MCP. |
| P1-11 | `generate_report` without a revision used the first product's revision | OPEN | Require `revision_id`. |
| P1-12 | AI provider code (`mendex_core/ai`, `intelligence/models.py`) wired into Core; API key stored in plaintext; `openai`/`requests` undeclared | **FIXED (removed)** | Owner decision: removed `mendex_core/ai/`, `intelligence/models.py` and `reasoning.py`, `mendex_ui/ai_config_dialog.py` and `ai_interactive.py`, `KnowledgePanel`, `AIAssistantPanel`, the `ReasoningAdvisorNode` workflow node, `StudioService.ai/ai_copilot/intelligence/ai_advice/advise_engineering`, and the `ai-availability` CLI command. Deterministic `intelligence/calculations`, `knowledge` and `benchmarks` were retained. **Action for owner:** `.mendex/ai_config.json` still holds a plaintext OpenAI key (git-ignored, now unused). Delete it and rotate the key. |
| P1-13 | UI uses "Engineering Workspaces", not "Engineering Projects"; no refresh after CLI/MCP changes | OPEN | Rename the navigation label; add a `QFileSystemWatcher` on `.mendex/studio.sqlite3` and the workspaces root. |
| P1-14 | KiCad schematic generator emits no symbols; PCB is a placeholder | OPEN | Either generate real `lib_symbols` + placed symbols + wires, or stop presenting these as generated designs (mark as "board outline / BOM only"). |
| P1-15 | FEMM model has no excitation or boundary | OPEN | Add a coil region with N·I, an air region and an A=0 boundary, and validate against an analytical gapped-core inductance. |
| P1-16 | Flyback turns sizing can exceed Bmax by up to 12.5 %; Lm mismatch (41 µH vs 27.4 µH) | OPEN | See 10 for the corrected equations. |

## P2
MCP schemas vs code (`generate_design` "required" fields), protocol-version negotiation, `run_simulation` blocking the MCP server, the unused `SafeRunner` allowlist, shared FEMM temp files (parallel-run collisions), dead UI modules (`design_studio_panel.py`, `workflow_canvas/*`, `first_run_wizard.py`), and duplicate calculation libraries. See 04, 07 and 13.
