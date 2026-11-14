# 16 — Prioritized Remediation Plan

Ordered by dependency and engineering impact. **Effort:** S = up to 1 day, M = 2–4 days, L = 1–2 weeks. Evidence references point to reports 02–14.

## P0 — Critical

### P0-1 — AI agents can provision reviewers and record "human" reviews through MCP
- **Root cause:** `engineering_reviews/api.py` `OPERATIONS` is shared by MCP and CLI and includes `register_authorized_reviewer` and `record_human_review`. The only agent guard is a word blocklist on the reviewer id (`engineering_reviews/service.py:44,283`). Identity is never authenticated (`identity_authenticated:false`).
- **Affected files:** `engineering_reviews/api.py`, `engineering_reviews/service.py`, `mcp/server.py:38,560`.
- **Evidence:** 06, 11. Live MCP session registered `jdoe` and recorded a REJECTED review.
- **Fix:** Expose read-only review tools on MCP. Restrict reviewer provisioning and decisions to an interactive human channel (desktop UI or a CLI with a TTY prompt and OS-user binding). Drop the blocklist.
- **Dependencies:** none.
- **Effort:** M.
- **Regression tests:** the MCP tool list contains no write-review tools; a CLI without a TTY is refused.

### P0-2 — Approvals are mutable and stay valid after changes
- **Root cause:** the `lifecycle_approvals` table has no triggers. The API accepts an empty reviewer, a later row overrides an earlier one, and there is no invalidation on spec edit or on IN_REVIEW→DRAFT.
- **Affected files:** `lifecycle/`, `sqlite_schema.py`.
- **Evidence:** 10.
- **Fix:** Append-only triggers. Require a reviewer. Approvals bind to a spec/artifact hash and become stale when it changes.
- **Dependencies:** P0-1.
- **Effort:** M.
- **Regression tests:** UPDATE/DELETE raise; a spec edit marks the approval stale.

### P0-3 — Tests and dev tooling write to the real data root
- **Root cause:** `tests/command_center/test_react_command_center.py:47-62` uses the default root and can create and delete a project. Tauri `main.rs:43` and `vite.config.ts:21` start the backend with no `--root`.
- **Evidence:** 09, 10. The real `integration_health` table was refreshed during this audit; engineering records were unchanged.
- **Fix:** A `conftest` that sets `MENDEX_DATA_ROOT` to `tmp_path` for every test. Dev tooling uses an explicit sandbox root.
- **Dependencies:** none.
- **Effort:** S.
- **Regression tests:** the suite fails if the repo `.mendex` modification time changes.

### P0-4 — Vite dev server reachable from the network, with backend write methods
- **Root cause:** `vite.config.ts:155` `host: '::'`; the Host/Origin check (`:80-83`) is spoofable, and a request without Origin passes.
- **Evidence:** 11 (code; not exploited live).
- **Fix:** Bind to `127.0.0.1`, use a per-session token, and disable write methods in dev.
- **Effort:** S.
- **Regression tests:** a config test asserts the host is loopback.

### P0-5 — Wrong flyback engineering results
- **Root cause:** `intelligence/calculations.py:301-306` derives ripple from average input current. `integrations/calculations/transformer_design.py:62-70` applies `b_max_t` to the flux swing instead of peak.
- **Evidence:** 04. 85→12 V, 2 A, 100 kHz: code gives 1490 µH vs the correct 670.6 µH; peak flux 0.276 T vs a 0.25 T limit.
- **Fix:** Correct the equations and keep a single source of truth (see P1-1).
- **Effort:** S.
- **Regression tests:** hand-reference cases with tolerances.

### P0-6 — KiCad produces manufacturing outputs from an unconnected design
- **Root cause:** the generated `.kicad_sch` has no wires and no `lib_symbols`; the `.kicad_pcb` has no tracks; Gerber export is not gated.
- **Evidence:** 08 (ERC 6 violations, DRC 10 violations plus 8 unconnected, 13 Gerbers).
- **Fix:** Block Gerber/drill export unless DRC is clean and the routing is complete. Label generated boards "placement only".
- **Effort:** S (gate) to L (real generation).
- **Regression tests:** export is refused on an unrouted board.

## P1 — High

### P1-1 — Four inconsistent calculation libraries
- **Libraries:** `intelligence/calculations.py`, `workflows/nodes/calculations.py`, `engineering_records/calculations.py`, `integrations/calculations/`.
- **Evidence:** losses 1.25 vs 2.5 W; Steinmetz 3162 vs 1e5 W/m³; diode drop 0.7 vs 1.0 V (04).
- **Fix:** One validated library; delete the others.
- **Effort:** M.
- **Regression tests:** cross-library golden values.

### P1-2 — Silent defaults on the workflow path and weak input validation
- **Defaults:** `workflows/nodes/calculations.py:201-238` (Vin 100 V, Vout 24 V, ×1.2 range), `v_diode_drop_v` = 1.0 V.
- **Validation gaps:** NaN, η=2 and negative current are accepted; layers 2.7 is truncated.
- **Fix:** Require inputs; validate as finite, within range and integer where needed.
- **Effort:** S.

### P1-3 — Simulation results not visible in the Studio
- **Root cause:** `desktop/service.py:176-178` returns `pcb_checks` and `measurements` as `[]`. Metrics are written only to `metrics.json`. The waveform endpoint is empty, and there are no charts.
- **Evidence:** 08, 09.
- **Fix:** Persist metrics in records, expose them, and add a waveform chart.
- **Effort:** M.

### P1-4 — Project page breaks on new revisions; old revisions unviewable
- **Root cause:** the `project` RPC returns NOT_FOUND for revisions not enrolled in a lifecycle; `ProjectDetail.tsx:1653` never sends `revision_id`.
- **Evidence:** 09, 14.
- **Fix:** Auto-enrol revisions into the project lifecycle and add a revision selector.
- **Effort:** S–M.

### P1-5 — FEMM magnetics never verified
- **Root cause:** no coil, current or boundary in `femm_runner.py:107-125`; B is one point at (0,0); the `femm.exe` process leaks; ifile/ofile are written into `C:\femm42`.
- **Evidence:** 04, 08.
- **Fix:** Excited model with an air region and A=0 boundary; maximum B over the core region; per-run working directory; guaranteed process kill.
- **Effort:** L.
- **Regression tests:** analytical gapped-inductor reference.

### P1-6 — LTspice robustness
- **Gaps:** app-path timeouts (2 of 3 runs), errors lost on failure (`log_errors` empty), `.meas` not parsed, ripple requirement not evaluated, `execution_time_s` = 0, design-service path writes no hashes or job record.
- **Evidence:** 08, 14.
- **Fix:** Investigate the timeout (concurrent GUI instance?); parse the log on failure and `.meas`; record a job and hashes on every path.
- **Effort:** M.

### P1-7 — Agents cannot discover Mendex; MCP tool quality
- **Gaps:** no `.mcp.json`; 29 legacy MCP tools have no schema validation (`get_project {}` → KeyError); `create_revision` needs an undocumented `label`; delete tools have no confirmation.
- **Evidence:** 05.
- **Fix:** Add project `.mcp.json`; retire legacy tools in favour of the v3.1 dispatch; validate all inputs.
- **Effort:** M.

### P1-8 — Packaging
- **Gaps:** release Tauri bundles no Python backend and has no icon; the installer launches the legacy PySide6 UI (`scripts/build_windows_installer.ps1:51`).
- **Evidence:** 02.
- **Fix:** Bundle the backend (sidecar or embedded Python), add icons, replace the installer.
- **Effort:** M–L.

### P1-9 — Reports, measurements and change requests not append-only
- **Evidence:** 10.
- **Fix:** Triggers and versioned rows.
- **Effort:** S.

## P2 — Medium
| ID | Issue | Evidence | Fix | Effort |
|---|---|---|---|---|
| P2-1 | Performance at scale: 401 SQLite connections per `projects` call; 1.3–2.1 s at 200 projects; 4 s polling uses about 68 % of one core | 12 | Single connection, batched queries, adaptive polling | M |
| P2-2 | Three service layers (StudioService, controller, DesktopService); desktop bypasses the controller; BOM only reachable from desktop | 02 | One application-service facade | L |
| P2-3 | Three lifecycle systems (`lifecycle/`, `engineering_lifecycle/`, `workflows/`) | 02, 03 | Converge on `engineering_lifecycle` | L |
| P2-4 | 98 broad `except` handlers, 77 swallowed; misleading "already exists" for every integrity error (`service.py:119`) | 03, 04 | Specific exceptions and logging | M |
| P2-5 | Orphan workspace folders after crash; no WAL; FKs only via `connection()`; no backup command; `migrate_v5` re-runs every start | 10 | WAL, consistent connections, backup CLI, version bump | M |
| P2-6 | Engineering Tools page probes executables on every 4 s refresh | 12 | Cache detection | S |
| P2-7 | Dashboard shows the project count as "revisions"; "Pending reviews" hard-coded to 0 | 09 | Real queries | S |
| P2-8 | Headless browser tests assert stale UI text (3 failures) | pytest log | Update the tests and isolate their data (P0-3) | S |

## P3 — Low
| ID | Issue | Fix |
|---|---|---|
| P3-1 | Legacy PySide6 UI, `main.py`/`src/main.py`, stale `dist/` and `build/`, scratch files in the repo root, committed `drc_test.json`/`edge_snap.png`/`sv1000.pdf`, Office lock file | Clean-up per 13 (needs separate approval) |
| P3-2 | Accessibility (7 attributes in total), no responsive rules, project tabs clipped at 1400 px, no Simulation Center empty state | UI pass |
| P3-3 | Conflicting `mcp_config.json` / `.vscode/mcp.json`; no CI; about 43 % return-type coverage | Consolidate config, add CI and a type checker |
| P3-4 | Tech stack named in the brief (Tailwind, shadcn/ui, TanStack Query, ECharts/Plotly) is absent | Decide whether it is still required; at minimum add a charting library for P1-3 |
