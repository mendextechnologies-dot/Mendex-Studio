# 09 — Frontend UI/UX Audit (React/Tauri desktop)

Audit date: 2026-11-14. Branch `v2.0-engineering-qualification` (dirty working tree, audited as-is). Audit only; no source changed.
Evidence: `docs/audit/evidence/ui_perf_e2e/` (logs, harness scripts saved as `*.py.txt`, screenshots).
All backend runs used disposable roots under `%TEMP%\mendex-audit3\ui\`.

## 1. Tech stack actually used

| Expected by brief | Actually present | Evidence |
|---|---|---|
| React 18 + Vite + TS | YES (react 18.3, vite 5.4, TS 5.6) | `desktop/package.json` |
| Tailwind | **NO** — hand-written CSS (`index.css`, 2.5 kB built) + heavy inline `style={{}}` | `desktop/src/index.css`, pages |
| shadcn/ui | **NO** | package.json |
| TanStack Query | **NO** — custom `usePolling` hook + `setInterval` in `App.tsx` | `desktop/src/usePolling.ts`, `App.tsx:64` |
| ECharts / Plotly | **NO** — no chart library and no chart rendering anywhere | grep for echarts/plotly/recharts/svg/chart: none |
| Icons | lucide-react | package.json |
| Router | none — `useState<RouteId>` + `?page=`/`?project=` query params | `App.tsx:16,52-60` |

`npx tsc --noEmit` passes (exit 0). `vite build` (output redirected to `%TEMP%`) succeeds: one JS bundle 254 kB (70 kB gzip).

## 2. How React talks to Python (corrected transport description)

The backend is **not an HTTP server**. `python -m mendex_core.desktop` reads newline-delimited JSON requests on stdin and writes responses on stdout (`src/mendex_core/desktop/__main__.py`), with a 256 KiB request cap, 8 MiB response cap, 16 pending-request cap and a 4-thread read pool.

* Production/Tauri: `desktop/src-tauri/src/main.rs` spawns the interpreter (`MENDEX_PYTHON` → bundled `backend/python.exe` → debug `.venv`) and exposes the `rpc_dispatch` command; `client.ts:24-27` uses `window.__TAURI__.core.invoke`.
* Browser/dev fallback: `client.ts:28-40` POSTs to `/api/rpc`, which exists only in the Vite dev-server plugin (`desktop/vite.config.ts`) that spawns the same stdio backend.
* Every response is checked for matching `id` and `protocol_version` 3.1.0 (`client.ts:44`).

**Data-root finding (HIGH):** neither the Tauri launcher (`main.rs:43-44`) nor the Vite plugin (`vite.config.ts` spawn args) passes `--root`; the backend falls back to `MENDEX_DATA_ROOT` or the repo root (`paths.py`). With cwd = repo root in debug/dev, the desktop app operates directly on the repo-root data store. There is no UI to choose the root (Settings only displays `data_root`).

**Dev-server exposure (MEDIUM):** `vite.config.ts` sets `server.host: '::'` (all interfaces). The `/api/rpc` middleware rejects non-`localhost:5173` Host/Origin headers, which blocks casual LAN access, but Host is client-controlled. A LAN client sending `Host: localhost:5173` reaches the bridge, including write methods (`complete_stage`, `submit_review`, `export_report`, `generate_bom`, `open_file`). Not exploited in this audit; found by reading the code only.

### Method parity: `client.ts` vs `desktop/service.py` ROUTES

| Method | client.ts | ROUTES | Called by UI | Live result (temp root) |
|---|---|---|---|---|
| handshake | yes | yes | Header/Settings | OK 31 ms |
| overview | yes | yes | App poll | OK |
| projects | yes | yes | App poll | OK |
| project | yes (`revision_id` optional) | yes | ProjectDetail poll — **always without revision_id** | OK; **NOT_FOUND "Revision has not been enrolled in a lifecycle" for non-enrolled revisions** |
| simulations | yes | yes | App poll | OK |
| components / tools / reports / settings | yes | yes | page polls | OK |
| waveform | yes | yes | **never called** | returns `{"samples": [], "traces": []}` for a valid ASCII .raw — **stub** (`service.py:262`) |
| open_file / reveal_file / open_evidence / open_report | yes | yes | buttons | not executed (would launch OS apps) |
| export_report | yes | yes | Reports tab button | OK, ZIP written, `integrity: INTACT` |
| generate_bom | yes | yes | buttons | INVALID_INPUT without `bom/bom.json` (correct refusal) |
| list_reviewers, review_package, request_review, submit_review, complete_stage | yes | yes | Lifecycle tab | review_package OK after enrolment |
| job, job_logs | **no** | yes | — | routes exist; UI cannot show job logs |
| shutdown | no (Tauri sends it) | yes | — | exits rc 0 |
| unknown method | — | — | — | METHOD_NOT_ALLOWED (correct) |

No method name mismatches. Gaps: unused `job`/`job_logs`, and a `waveform` endpoint that validates the file but never returns samples.

## 3. Screens (code review plus real headless-Chrome render)

The built bundle was served from `%TEMP%` by a throw-away adapter (`serve.py.txt`) that forwards `/api/rpc` to a stdio backend on the E2E temp root. Headless Chrome 1400×900 screenshots are in the evidence folder. This exercises the **browser fallback path, not the Tauri WebView**. Tauri-window behaviour is NOT VERIFIED. No clicks or interactions were automated, so button behaviour is from code only.

| Screen | Real backend data | Loading / error / empty | Notes and defects |
|---|---|---|---|
| Dashboard (`dash.png`) | YES (overview) | Errors from the App-level poll go to `syncError` and `console.error` | **Bug:** "N total recorded revisions" shows the project count (`service.py:67 "revisions": len(projs)`); the screenshot shows "1 total recorded revisions" while 2 revisions exist. `review_requests: 0` is hardcoded (`service.py:70`), so the "Pending Reviews" tile is always 0. |
| Engineering Projects (`projects.png`) | YES | search filter on code/name (`Projects.tsx:13`) | no sort or pagination; renders all rows |
| Simulation Center (`simulations.png`) | YES; the real LTspice job showed SUCCEEDED, exit 0, attributed to the project | **no empty state** (blank table); no error display (props only) | read-only; no run, cancel, log or waveform view; job id truncated without copy |
| Component Library | YES (static sourced catalog) | empty-state text present (`ComponentLibrary.tsx:111`) | 6 aria attributes, the only page with any |
| Engineering Tools (`tools.png`) | YES (live health probe) | usePolling error | `tools` costs 147–907 ms per poll (live executable probes every 4 s) |
| Reports & Evidence (`reports.png`) | YES; the E2E report was listed with `INTACT` | usePolling | — |
| Settings (`settings.png`) | YES (handshake + diagnostics) | usePolling | read-only; `mcp_status` hardcoded `NOT_EVALUATED`; data root not changeable |

### Project tabs (`ProjectDetail.tsx`, 1,656 lines)

The brief's 10 tabs are all present (`ProjectDetail.tsx:49-58`). "Engineering Files" is labelled **Revision Files**. At 1400 px the Revisions and Reports tabs are cut off (overflow; see `project.png`).

| Tab | Data source | Notes |
|---|---|---|
| Overview | `project` | Real counts. "Recorded inputs…: 0" on R002 is correct, because the calculation was recorded on R001. |
| Lifecycle | lifecycle in `project`, review_package/request/submit/complete | write actions; not clicked |
| Specifications | `revision.specification` | units are carried in field names (`vin_min_v`, `switching_frequency_hz`), not formatted units |
| Calculations / Designs / Simulations / Validation / Reports | engineering_records lists | real data |
| Revision Files | filesystem walk, capped at 1000 files | open/reveal buttons launch OS apps |
| Revisions | `revisions[]` list | **cannot open a historical revision**: `ProjectDetail.tsx:1653` always calls `api.project(projectId)` without `revision_id`, so records on earlier revisions (R001 calculations, simulation, artifact in the E2E) are not reachable from the UI |

**HIGH (functional):** after a new revision is created (MCP `create_revision`), the active revision is not lifecycle-enrolled and `project` returns `NOT_FOUND "Revision has not been enrolled in a lifecycle"`. The whole project page then shows "Project unavailable" until someone enrols the revision through CLI or MCP. This was reproduced in E2E part 2. The UI has no enrol action.

**Hardcoded or placeholder values** in the `project` payload: `availability_requests: []`, `pcb_checks: []`, `measurements: []` (`service.py:174-178`). The `projects` row falls back to `revision_label "R001"` and `"draft"` when no revision is found (`service.py:89-90`).

**Charts:** none. Waveforms cannot be displayed: the endpoint is a stub and the UI never calls it.

## 4. Auto-refresh and load

* `App.tsx:64`: `setInterval(syncData, 4000)` runs overview, projects and simulations concurrently (`Promise.all`), guarded against overlap.
* Each page's `usePolling` (4000 ms, serial setTimeout) adds one more call (components, tools, reports, settings or project).
* Even static data (component catalog) and expensive probes (`tools`) are re-polled every 4 s. Cost at scale: see `12_PERFORMANCE_RELIABILITY.md`.
* There is no visibility or backoff handling: polling continues while the window is hidden, and there is no exponential backoff on errors.

## 5. Accessibility and responsiveness (code plus one narrow render)

* Accessibility: 7 `aria-*` attributes in the whole UI (ComponentLibrary 6, ProjectDetail 1 `role="alert"`). Tables have no captions or `scope`. Icon-only affordances have no labels. No keyboard handlers beyond native buttons.
* Responsiveness: **0 `@media` rules**. A 420 px render (`dash_narrow.png`) keeps a fixed 240 px sidebar, so content is clipped and the header badges overlap. The layout is desktop-only.
* Colours are hardcoded inline hex in many places, with no theme tokens beyond a few CSS variables.

## 6. Severity summary

1. HIGH: Desktop/Tauri and Vite bridge do not pass `--root`, so the debug/dev app runs on the repo-root real data store.
2. HIGH: Project page fails ("Project unavailable") for any revision that is not lifecycle-enrolled, including every fresh revision. The UI has no enrol path.
3. HIGH: Historical revisions are not viewable (`revision_id` never sent).
4. MEDIUM: `waveform` is a stub and there are no charts at all, so simulation results cannot be inspected in Studio.
5. MEDIUM: Dashboard "revisions" metric is wrong (it shows the project count), and "Pending reviews" is hardcoded 0.
6. MEDIUM: Vite dev server binds `::`; the Host check is the only guard on write-capable RPC.
7. MEDIUM: Polling of expensive endpoints every 4 s (see doc 12).
8. LOW: no empty state in Simulation Center; tab overflow; no responsive layout; minimal accessibility; `job`/`job_logs` unused; stack differs from the brief (no Tailwind, shadcn, TanStack, ECharts or Plotly).
