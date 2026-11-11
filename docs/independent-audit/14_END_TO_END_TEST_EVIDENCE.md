# 14 — End-to-End Test Evidence

All runs on 2026-11-11, Windows 11, Python 3.13.7 (`.venv`), with isolated data roots under `%TEMP%\mendex-audit\`. No production data in `workspaces/`, `products/` or `engineering_designs/` was used or modified.

## Installed engineering tools (detected on host)
| Tool | Version | Path | Source |
|---|---|---|---|
| LTspice | 26.1.1 | ADI install | report 09 |
| FEMM | 4.2 (2019) | `C:\femm42\bin\femm.exe` | report 09 (app mis-reports version as `1.0.0.1`) |
| KiCad CLI | 10.0.7 | kicad-cli | report 09 |

## Automated test suite
| Point in time | Result |
|---|---|
| Audit baseline (before any fix) | **226 passed, 2 skipped, 0 failed** (87.96 s). The skips were the LTspice/FEMM acceptance tests, wrongly reported "not installed" (`integrations.verify()` only returns `DETECTED`, never `READY`). |
| Baseline side effect | `tests/integration/test_v20_qualification.py::test_tool_launch_and_routing` opened **real** FreeCAD/LTspice/KiCad GUI windows on the engineer's desktop (user-observed: KiCad "test.kicad_sch does not exist" dialog). |
| After remediation (this session) | **253 passed, 1 skipped, 0 failed**. The single skip is an honest `NOT_EVALUATED` (no excited FEMM reference model exists). |

## Workflow steps (brief §17)
| # | Step | Result | Evidence |
|---|---|---|---|
| 1 | Create Engineering Project | PASS (CLI/MCP/controller) | 07 §A, 05 |
| 2–3 | Add / validate specifications | PARTIAL: `specification validate` rejects the field names design generation uses | 07 P2 |
| 4 | Generate supported design | PASS for buck and flyback only. Before the fix, invalid inputs produced negative L/C or crashed. | 09, 10 |
| 5 | Deterministic calculations | Numerically correct (buck, flyback CCM, Dowell, losses). Before the fix they ran on silent defaults. | 10 |
| 6 | Generate artifacts | PASS for `.net/.asc`. The KiCad schematic has **no components**. The PCB is a placeholder (identical 0805 footprints, no tracks). | 09 |
| 7–8 | Real LTspice run + extraction | **PASS (buck 12→5 V, 2 A, 500 kHz)**: Vout 4.75 V (open-loop, −5 %), ripple 47.5 mV vs 50 mV, IL ripple 0.598 A vs 0.600 A | 09, `evidence/tools_and_calcs_log.md` |
| 7b | Real LTspice flyback | Before the fix: **0 V, verdict PASSED** (floating gate). After: **12.51 V vs 12 V target (+4.2 %), no log errors**. Probe: `%TEMP%\mendex-audit\scripts\flyback_probe.py` | this session |
| 7c | Real LTspice RC analytical reference | After the fix: V(1 ms) within 1 % of 10·(1−1/e) = 6.321 V (`test_v20_acceptance::test_scenario_b`) | this session |
| 7d | Real FEMM | Solver runs, but the model has no excitation, so the field is 0. Before the fix a **hard-coded 0.285 T was reported as SOLVED/PASSED**; it is now `NOT_EVALUATED`. | 09, this session |
| 9–13 | Studio shows project/design/calcs/sims | PARTIAL: navigation exists; no refresh after CLI/MCP changes (manual Refresh only) | 12 |
| 14 | Open in LTspice | Routing PASS (not launched during the audit) | 07, 13 |
| 15–18 | Modify parameter, new revision, re-simulate, compare | PASS for the buck closed-loop iteration (real LTspice, rev 2 created) | `test_v20_qualification::test_closed_loop_ai_design_iteration` |
| 19 | Engineering report | PASS (HTML with hash). Before the fix, a report with no revision silently used the first product. **Still open (P1)** | 06 |
| 20 | Evidence / validation status | PARTIAL: hashes recorded but never re-verified; external edits undetected (P1, still open) | 11 |
| — | Run via Claude Code over MCP | **NOT VERIFIED**: Mendex is not registered in `claude mcp list` | 08 |
