# Mendex Engineering Studio v1.9 — Engineering Readiness Gate

Independent verification of real-world engineering capability. Verification only: no Studio code, algorithms, baselines or production data were modified. The final decision is in [V1_9_FINAL_READINESS_DECISION.md](V1_9_FINAL_READINESS_DECISION.md).

## 1. Baseline

| Item | Value |
|---|---|
| Repository / branch | `C:\Mendex studio` · `v1.9-visual-workflow-studio` |
| Gate baseline (frozen) | **`dc21aa92c1e51cae9d777ad730a61125fecc0906`** (2026-11-10 20:07:06 +0530), extracted read-only with `git archive` to `.mendex/qa/v19-readiness/snapshot_dc21aa9/` |
| Start state | `dd26af9` + uncommitted UI changes (first pass of Tests A–C, G, I) |
| Excluded | Uncommitted work in progress that appeared during the gate: `workflows/engine.py`, `tests/core/test_workflow_engine.py`, `mendex_ui/workflow_canvas/`, edits to `service.py`, `window.py` |
| Test window | 2026-11-10, 19:55–20:20 IST (14:25–14:50 UTC) |
| OS | Microsoft Windows 11 Home Single Language 10.0.26300 |
| Python | 3.13.7 (project `.venv`); PySide6 6.12.0; pydantic 2.14.3; pytest 9.2.0 |
| Studio version | Package `mendex-studio 0.1.0` (`pyproject.toml`); window title "v1.9 · Enterprise Edition" |
| Existing tests | 118 passed in 19.85 s (`baseline_pytest.txt`) |

### Installed engineering software (versions read from the binaries)

| Tool | Version | Path | Studio core-service state |
|---|---|---|---|
| LTspice | 26.1.1.0 | `C:\Program Files\ADI\LTspice\LTspice.exe` | READY (`batch_simulate`) |
| FEMM | 4.2 | `C:\femm42\bin\femm.exe` | NOT_INSTALLED (wrong) |
| KiCad CLI | 10.0.7 | `C:\Program Files\KiCad\10.0\bin\kicad-cli.exe` | NOT_INSTALLED (wrong) |
| FreeCAD | 1.1.4 | `C:\Program Files\FreeCAD 1.1\bin\FreeCADCmd.exe` | NOT_INSTALLED (wrong) |
| OpenModelica | 1.26.3 | `C:\Program Files\OpenModelica1.26.3-64bit\bin\omc.exe` | NOT_INSTALLED (wrong) |
| Qucs-S / ngspice | ngspice-46 (KLU) | `%LOCALAPPDATA%\Programs\qucs-s\bin\` | Qucs-S NOT_INSTALLED (wrong); ngspice has no connector |

Baseline correction: the initial inventory missed Qucs-S because it only searched Program Files. This was corrected after inspecting the dashboard screenshot, and ngspice was then tested.

### Adapters present

Two parallel adapter stacks exist. Only the first is reachable from the UI/CLI core service:
1. `integrations/v15_connector.py` → `V15ConnectorRegistry` → registered into `StudioService.integrations` by `StudioWindow`. **Executable connectors: LTspice, Python, Git.** KiCad, FEMM, FreeCAD, Qucs-S, OpenModelica and Jupyter are `UninstalledToolV15Connector` (always raise); datasets are metadata-only; commercial tools are license-guarded stubs.
2. `integrations/adapters/*` → `ToolRegistry` (LTspice, KiCad, FEMM, FreeCAD, ngspice, OpenModelica, …). **Not referenced by `StudioService` or the UI.**
3. v1.9 workflow nodes (`mendex_core/workflows/nodes/*`, new in `dc21aa9`), with no engine and no UI.

### Data safety

All Studio activity used disposable roots: `.mendex/qa/v19-readiness/studio_root/`, `pinned_dc21aa9/studio_root/`, `ui_root/` and a temp dir. The production `.mendex/studio.sqlite3` and existing audit evidence were not touched. Two orphaned LTspice processes created by the interrupted-execution test were identified by their command lines (pointing into the QA folder) and terminated. The user's own LTspice GUI instance (PID 24960, `-mcpserver`) was left untouched.

## 2. Method

- Real tools, real input files, real solver runs, results extracted by **independent QA parsers** (`harness/qa_common.py`), never by the code under test.
- Analytic references and tolerances were fixed in the harness before execution and are justified in each test document.
- Studio capability was judged separately from tool capability. A test passes only if the **Studio** performs the step.
- All automated tests were rerun against the frozen `dc21aa9` snapshot (`MENDEX_SRC`, `QA_RUN_TAG=pinned_dc21aa9`). Results were identical to the first pass.
- QA harness errors found along the way were corrected and disclosed (FEMM Lua API names, KiCad netlist regex, `FileReference.filename`, adapter `workspace_id`). None changed a Studio verdict.

## 3. Test documents

| Test | Document |
|---|---|
| A — LTspice | [V1_9_ELECTRICAL_SIMULATION_VALIDATION.md](V1_9_ELECTRICAL_SIMULATION_VALIDATION.md) |
| B — FEMM | [V1_9_MAGNETIC_SIMULATION_VALIDATION.md](V1_9_MAGNETIC_SIMULATION_VALIDATION.md) |
| C — KiCad | [V1_9_SCHEMATIC_VALIDATION.md](V1_9_SCHEMATIC_VALIDATION.md) |
| D — Sweep / workflow | [V1_9_WORKFLOW_AUTOMATION_VALIDATION.md](V1_9_WORKFLOW_AUTOMATION_VALIDATION.md) |
| G — Intelligence | [V1_9_ENGINEERING_INTELLIGENCE_VALIDATION.md](V1_9_ENGINEERING_INTELLIGENCE_VALIDATION.md) |
| I — Desktop | [V1_9_DESKTOP_USABILITY_VALIDATION.md](V1_9_DESKTOP_USABILITY_VALIDATION.md) |
| E, F, H, supplementary | Sections 4–7 below |

## 4. Test E — Engineering report generation: **FAIL**

Source: Studio `export_report()` for the pinned Test A job (`pinned_dc21aa9/studio_root/.mendex/ij/8c7e101d…/reports/f0b416fbad78/report.{json,html}`), plus the `report_export` / `evidence_aggregation` workflow nodes.

| Required content | Present? |
|---|---|
| Engineering objective | No |
| Test configuration / input parameters | Partial — request JSON with a staged-file path; netlist content not included |
| Assumptions | No |
| Software versions | Yes (`tool_version`, from a hard-coded constant) |
| Solver settings | No |
| Numerical results | **No** |
| Graphs / waveforms | **No** |
| Reference calculations / error % / validation outcome | **No** — `engineering_status: NOT_EVALUATED` |
| Limitations | Present but **wrong**: "Synthetic outputs are software test fixtures, not engineering simulation or measurement" for a real LTspice run |
| Execution timestamps | Yes |
| Source artifact references | Yes — paths + SHA-256, evidence integrity `True` |

The report does not invent values, because it contains none. Every engineering result in this gate therefore had to be traced by QA rather than by the Studio report. Workflow `evidence_aggregation` treats a check with no `passed` field as passed (`chk.get("passed", True)`) and reports `all_passed = True` when it is given no checks, so it can produce a pass with no evidence. When `workspace_path` is unset, `report_export` writes to a CWD-relative `reports/` folder.

## 5. Test F — Workspace persistence and reproducibility: **PASS (core-service scope)**

Evidence: `pinned_dc21aa9/test_dfh/result.json` (`F_*`).

| Step | Result |
|---|---|
| Product-independent workspace created | PASS (`product_id: null`) |
| Activity added (`RC reference rerun`, tool ltspice, R/C/Vs parameters) | PASS |
| Simulations executed, inputs/outputs saved with manifests | PASS (5 jobs) |
| Close → new OS process → reopen same root | PASS — workspace present, activity recovered, all 5 job statuses identical, `evidence_integrity` True for all 5 |
| Rerun reference simulation | PASS — job `fa581c10…`, max \|ΔV\| vs analytic 2.75 µV |
| Rerun vs original | max \|ΔV\| at check points = **0.0 V**; `.raw` not byte-identical (LTspice embeds the run date in the header). Tolerance: numerically identical within 1 µV — met. |
| Environment change | None (same host/session); not assessed |
| Desktop-level close/reopen | Theme/geometry persisted (Test I); the UI has no results view to show recovered numerical results |

## 6. Test H — Failure and safety handling: **FAIL**

Evidence: `pinned_dc21aa9/test_dfh/result.json` (`H`), workflow backend JSON.

| Scenario | Observed | Assessment |
|---|---|---|
| Missing tool executable | `configure("ltspice", {executable_path: C:\nonexistent\…})` rejected: "Configure an existing absolute path"; FEMM/KiCad report NOT_INSTALLED; submit → UNSUPPORTED | PASS (clear refusal) |
| Invalid input file (bad sub-circuit) | Status FAILED, exit 1. LTspice log says "This sub-circuit name is not defined", but **Studio diagnostics are empty** | PARTIAL — no useful diagnostic surfaced |
| Empty netlist | Accepted at submit (no validation); outcome masked because the harness shut down the session (CANCELLED) | Observation |
| Incorrect engineering units | Calculation service accepts kHz-as-Hz and µH-as-H with `verified: True` (Test G) | **FAIL** |
| Solver execution failure | The floating-node probe was resolved by LTspice (gmin) and SUCCEEDED, so it was not a genuine failure case. An unrecoverable-solver case was not reproduced. | NOT VERIFIED |
| Simulation timeout (3 s) | TIMED_OUT after 3.5 s; process tree killed (no orphan) | PASS |
| Workflow / job cancellation | CANCELLED in 0.35 s; process tree killed | PASS (jobs). Workflow-level cancellation: no engine |
| Missing dataset | MagNet submit → UNSUPPORTED (metadata-only) | PASS |
| Missing input file | INVALID_INPUT "Input is missing, outside workspace or exceeds 10 MiB" | PASS |
| Invalid workflow connection | Backend validator rejects type mismatch, missing port and cycle with clear messages | PASS (backend only; no UI) |
| Restart after interrupted execution | Studio process hard-killed mid-run: job stays **RUNNING permanently** after restart; `cancel()` in a new session → "INTERRUPTED … its runner must acknowledge cancellation"; **LTspice orphan kept running** (reproduced in both passes; PIDs 29152 and 8060 killed manually) | **FAIL** |
| No fabricated successful results | **Violated** by workflow nodes `ltspice_simulation` (no service), `kicad_check`, `femm_analysis`, by `KiCadAdapter` on invalid ERC, and by the dashboard tool-status literals | **FAIL** |
| Preservation of workspace data | Existing jobs and evidence intact after all failure cases (integrity True) | PASS |

## 7. Supplementary tools (reported separately; tool-level only)

None of these tools is executable through the Studio core service, so each result below shows the tool works, **not** that the Studio does.

| Tool | Test | Reference | Result | Evidence |
|---|---|---|---|---|
| OpenModelica 1.26.3 | `RCRef.mo` (C·dv/dt = (Vs−v)/R), compiled and simulated with DASSL, tol 1e-9, CSV output | 5(1−e^(−t/1 ms)) at 6 points, tol 1 mV | **PASS** — max \|Δ\| 1.8e-8 V | `supplementary/openmodelica/` |
| FreeCAD 1.1.4 | `Part::Box` 10×20×30 mm → STEP AP214 → re-import | V = 6000 mm³, A = 2200 mm² | **PASS** — 6000.0 / 2200.0, shape valid | `supplementary/freecad/` |
| ngspice-46 (Qucs-S bundle) | Same RC netlist, `.tran 1u 5m UIC`, `wrdata` | Analytic RC, tol 1 mV | **PASS** — max \|Δ\| 2.7e-6 V | `supplementary/ngspice/` |
| Qucs-S GUI | — | — | NOT VERIFIED (only its bundled ngspice was exercised) | — |

## 8. Evidence index

Root: `.mendex/qa/v19-readiness/` (551 MB; mostly partial `.raw` files from the deliberately long timeout/interrupt runs)

| Path | Content |
|---|---|
| `SHA256SUMS.txt` | SHA-256 of 322 evidence artifacts (inputs, raw outputs, logs, reports, manifests, screenshots, harness) |
| `SNAPSHOT_dc21aa9_SOURCE_SHA256.txt` | SHA-256 of every `.py` in the frozen baseline |
| `snapshot_dc21aa9/` | Frozen baseline source (`git archive`) |
| `harness/` | All QA scripts (`qa_common.py`, `rc_job.py`, `test_*.py`, `make_tables.py`) |
| `test_a/`, `test_b/`, `test_c/`, `test_dfh/`, `test_g/`, `test_i/` | First pass (`dd26af9` + WIP) |
| `pinned_dc21aa9/` | Rerun against the frozen baseline (authoritative for A, C, D, F, G, H, I) |
| `test_d/workflow_backend_dc21aa9.json` | Workflow node / validator / storage execution evidence |
| `supplementary/` | OpenModelica, FreeCAD, ngspice |
| `tables.md` | Tables rendered from JSON by `make_tables.py` (source of every table in these documents) |
| `baseline_pytest.txt` | Existing test-suite run |

Reproduce any test: `cd .mendex/qa/v19-readiness/harness`, set `MENDEX_SRC` to `..\snapshot_dc21aa9\src` and `QA_RUN_TAG` to a new folder name, then run `..\..\..\..\.venv\Scripts\python.exe test_<x>.py`. Test B needs no Studio code.
