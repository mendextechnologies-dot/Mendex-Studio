# 01 — Executive Summary

**Audit date:** 2026-11-14.

**Baseline:** commit `d555d97` plus 71 uncommitted working-tree entries, frozen by SHA-256 over 365 files at 11:19:13. The hash list is in `%TEMP%\mendex-audit3\baseline\`.

**Method:** read-only code inspection, live runs against disposable data roots under `%TEMP%\mendex-audit3\`, real LTspice/FEMM/KiCad executions, and the full pytest suite. No application code, configuration or git state was changed by this audit.

**Final verdict: PARTIALLY READY — FIXES REQUIRED** (see 17).

## What Mendex Studio is today
A Python 3.13 engineering core is exposed through three front doors:
- an MCP stdio server (64 tools);
- the `mendex` CLI;
- a JSON-over-stdio desktop backend.

The desktop backend is consumed by a React 18 + Vite + TypeScript UI in a Tauri 2 shell. Nine engineering-stage prompts live in `engineering-workflows/`. Data is stored in SQLite (`.mendex/studio.sqlite3`) with file artifacts. A legacy PySide6 UI is still shipped by the only Windows installer.

## What works (verified)
- Real LTspice batch simulation:
  - the RC reference matches the analytical 6.3212 V to 5 digits, and results are byte-reproducible (08);
  - a buck through the app path gives 11.71 V against a 12 V target, matching hand calculations.
- The full 17-step end-to-end workflow on an isolated project reached PASS, including a real LTspice run and a backend restart with data intact. Two steps passed only on retry against a second revision (14).
- MCP protocol handling, the shared v3.1 MCP/CLI dispatch, path confinement, salted reviewer secrets and append-only validations (05, 10, 11).
- Python tests: **415 passed, 3 failed, 1 skipped**. The failures are stale headless-browser text assertions; the skip is an honest FEMM `NOT_EVALUATED`.
- Backend starts in 0.7–1.3 s, uses about 60–75 MB, shuts down cleanly and recovers after a kill (12).

## What does not
1. **AI agents can register a reviewer and record a "human" review through MCP.** The only barrier is a word blocklist on the reviewer id, and identity is never authenticated (06, 11). This defeats the core rule that humans approve.
2. **Approval records can be overwritten or deleted, and stay valid after a spec edit or demotion to draft** (10).
3. **Engineering correctness:**
   - The flyback inductance formula is wrong (1490 µH vs a correct 670.6 µH).
   - There are four inconsistent calculation libraries.
   - Silent defaults have returned on the workflow path.
   - The flyback transformer exceeds its own flux limit (04).
4. **Tools:**
   - The KiCad output has no wires or tracks yet produces Gerbers.
   - The FEMM model is unexcited, so magnetics are never verified.
   - Simulation numbers and ERC/DRC results are not shown in the Studio (08).
5. **Desktop:**
   - Newly created revisions make the project page "unavailable", and older revisions cannot be viewed.
   - There are no charts.
   - The expected stack is absent: Tailwind, shadcn/ui, TanStack Query, ECharts and Plotly.
   - The UI slows to 1.3–2.1 s per refresh at 200 projects (09, 12).
6. **Safety of real data:**
   - The Tauri dev/debug launcher, the Vite bridge and the browser tests run against the real repo data root.
   - The Vite dev server listens on all network interfaces.
   - During this audit, a test run refreshed the real `integration_health` table; no engineering records changed (verified read-only).
7. **Agents:** a fresh Claude Code session cannot discover Mendex (no `.mcp.json`, not registered). Codex and Antigravity are NOT VERIFIED.
8. **Packaging:** a release Tauri build bundles no Python backend and has no icon. The only installer launches the legacy PySide6 UI.

## First priorities
Remove reviewer provisioning and human-review recording from MCP. Make approvals immutable and invalidate them on change. Fix the flyback formulas and consolidate the calculation libraries. Isolate all tests and dev tooling from the real data root. See 16 for the ordered plan.
