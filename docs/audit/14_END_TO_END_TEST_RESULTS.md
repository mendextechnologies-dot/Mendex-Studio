# 14 — End-to-End Test Results (isolated generic project)

Audit date: 2026-11-14.

* Data root: `%TEMP%\mendex-audit3\ui\e2e2` (disposable). This is not SV1000 and not the repo root.
* Project `AUDE2E` "Audit Generic Buck 12V-5V", project_id `112f57b6-1cef-4ba1-b6cd-4f1386c0fa12`, R001 `989533c1…`, R002 `14b71dd2…`.
* Drivers:
  * MCP: `MendexMCPServer.handle_request` in-process.
  * CLI: `python -m mendex_core.cli --root …` subprocesses.
  * Lifecycle enrol/start: called on the core service directly, as in the repo's own interface tests.
  * Desktop backend: `python -m mendex_core.desktop --root …` over stdio JSON-lines.
* Scripts: `e2e.py.txt`, `e2e2.py.txt`, `e2e3.py.txt`. Logs: `e2e_part1..3.log` in `docs/audit/evidence/ui_perf_e2e/`.

| # | Step | Result | Evidence |
|---|---|---|---|
| 1 | Create project (MCP `create_project`) | PASS | status CREATED, R001 created |
| 2 | Init lifecycle (enrol + start `project_initialization`; read back with CLI `lifecycle show`) | PASS | assignment `dbb6e6d6…`, engineering_status NOT_EVALUATED |
| 3 | Add specs (MCP `save_project_specification`) + requirements (CLI `engineering record_requirements`) | PASS (second attempt) | spec hash `fcef3cdc…`. First attempt found two problems, both recorded: (a) the MCP tool error body is not JSON and the docs give no field names (`input_voltage_*` rejected; real names are `vin_min_v`…); (b) saving specs *after* starting the stage made every later write fail with CONFLICT "Start/reopen a current stage attempt". The order must be specs before stage start. |
| 4 | Calculation (MCP `record_calculation_run`, `losses`) | PASS | status SUCCEEDED; formula and implementation sha256 recorded; inputs explicitly synthetic |
| 5 | Persist (read back from a separate CLI process) | PASS | `list_calculation_runs` returns the record |
| 6 | Register design artifact (CLI `register_engineering_artifact`, `sim/buck_rc.net`) | PASS | record `dcb38323…` |
| 7 | Revision (MCP `create_revision`, label R002) | PASS (with defect) | First call failed with `KeyError: 'label'` because `label` is required but was missing from the call. Creating R002 **froze R001**, so later writes to R001 fail with `IMMUTABLE`. |
| 8 | **Real LTspice** (CLI `simulation run --tool ltspice --netlist buck_rc.net`, LTspice 26.1.1 batch) | PASS | 1.2 s wall; exit 0; COMPLETED; `.raw` 303,363 B and log produced; log header "LTspice 26.1.1 for Windows"; summary_verdict NOT_EVALUATED. Defect: `execution_time_s: 0.0`. |
| 9 | Capture outputs (MCP `get_simulation_results` / `get_simulation_logs`) | PASS | raw present; log text returned |
| 10 | Register evidence (`record_validation_evidence`, raw file as SIMULATED evidence) | FAIL on R001 (IMMUTABLE, frozen by step 7) → PASS on R002 after enrolling R002 | record `4a8127a9…` |
| 11 | Project status (MCP `get_project_lifecycle`, `get_workspace_status`) | PASS (with caveat) | `workspace_status` for the project points at active R002 and reports 0 simulations; the job is attributed to R001 |
| 12 | Studio shows records (desktop stdio API) | PASS (API) / visual partially verified | `overview`, `projects`, `simulations` (job SUCCEEDED, attributed), and `project(revision_id=R001)` contain the calculation, requirement and artifact. **`project` without revision_id (what the UI sends) returned NOT_FOUND "Revision has not been enrolled"** until R002 was enrolled. A headless-Chrome render of the built UI (browser fallback path, not the Tauri window) after enrolment shows the dashboard, simulation job, report and project pages (`dash.png`, `simulations.png`, `reports.png`, `project.png`). The Tauri window is NOT VERIFIED. R001 records cannot be opened in the UI (no revision selector call). |
| 13 | Sync (CLI `update_project_metadata` rename → API) | PASS | the next `projects` call (4.0 ms) shows the new name; the UI picks it up on the next 4 s poll (`App.tsx:64`); the screenshot shows "RENAMED" |
| 14 | Report (CLI `generate_revision_report`) | FAIL on R001 (IMMUTABLE) → PASS on R002 | report `613454be…`, `included_check_ids: ["vout_sim"]` |
| 15 | Report accessible (desktop `reports` + `export_report`) | PASS | 1 row (34.5 ms); export ZIP `.mendex/engineering-records/exports/…/report-package.zip`, integrity INTACT. `open_report` was not run because it launches an OS viewer. |
| 16 | Restart backend | PASS | `shutdown` rc 0; restart to handshake 0.865 s. Kill-mid-request and restart: 1.457 s (doc 12). |
| 17 | Data intact | PASS | `project(R001)` payload identical before and after restart (timestamp excluded, 21,757 B) |

## Findings from the E2E

1. HIGH: The UI's default project load fails for every non-enrolled active revision, which includes every newly created revision. Studio has no enrol action.
2. HIGH: Ordering traps that are not surfaced to the agent or user:
   * Saving specs after the stage starts invalidates the attempt.
   * Creating a revision freezes the previous one before its evidence or report is recorded.
3. MEDIUM: `create_revision` requires an undocumented `label`; MCP error bodies are plain text, not JSON.
4. MEDIUM: Simulation records sit on R001 while the active revision is R002. The workspace status and UI views for the active revision show 0 simulations, and R001 is not viewable in the UI.
5. LOW: `execution_time_s` is 0.0 for a real 1.2 s LTspice run.
6. The netlist was an RC test circuit, not a buck converter. The returned metric names (`vout_mean_v`, `vout_ripple_pk_pk_v`) are generic labels, not engineering validation. The verdict correctly stayed NOT_EVALUATED.
