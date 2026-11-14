# 17 — Final Audit Scorecard

Scores reflect verified behaviour, not code presence. Evidence references point to reports 02–14.

| Area | Score /10 | Status | Critical gaps |
|---|---|---|---|
| Architecture | 5 | PARTIAL | Three service layers and three lifecycle systems; desktop bypasses the controller (02) |
| Engineering Core | 4 | PARTIAL | Wrong flyback formulas; four inconsistent calculation libraries; mutable approvals (04) |
| MCP Server | 4 | PARTIAL | Agents can self-provision reviewers and record reviews; 29 legacy tools have no validation (05, 11) |
| CLI | 6 | PARTIAL | Shares the v3.1 dispatch; same review-write exposure (05) |
| Nine Engineering Stages | 4 | PARTIAL | Stages exist and are persisted. Human gate bypassable via MCP; spec-save ordering trap (06, 14) |
| Generic Prompts | 7 | PASS | Generic; reference only existing tools; forbid fabrication (07) |
| LTspice | 7 | PARTIAL | Real reproducible runs. Intermittent timeouts, `.meas` not parsed, failure errors lost (08) |
| FEMM | 2 | FAIL | Unexcited model, so never evaluated; process leak (08) |
| KiCad | 3 | FAIL | No wires or tracks, yet Gerbers are produced; header-only BOM (08) |
| React/Tauri UI | 4 | PARTIAL | No charts; new-revision page breaks; old revisions unviewable; expected stack absent; Tauri window NOT VERIFIED (09) |
| Studio Synchronization | 6 | PARTIAL | CLI change visible on the next 4 s poll; heavy polling cost (09, 12) |
| Database | 5 | PARTIAL | Migrations and concurrency OK. Approvals, reports and measurements are mutable; no WAL or backup (10) |
| Security | 3 | FAIL | Approval authorization bypass; network-exposed dev proxy; real data root used by dev tooling (11) |
| Performance | 5 | PARTIAL | Startup 0.7–1.3 s and 60–75 MB. 1.3–2.1 s per call at 200 projects (12) |
| Code Quality | 4 | PARTIAL | 98 broad excepts; duplication; legacy PySide6 still present (03, 13) |
| Windows Packaging | 2 | FAIL | Release build has no backend and no icon; installer launches the legacy UI (02) |
| End-to-End Workflow | 6 | PARTIAL | All 17 steps passed with a real LTspice run; two needed a retry on a new revision (14) |
| Product Development Readiness | 3 | PARTIAL | Not ready for magnetics, PCB, approval integrity or manufacturing (15) |

## Final verdict (Phase 18)
1. **Architecturally sound?** Partly. The layering is right, but there are three overlapping service and lifecycle systems.
2. **Python core reliable?** Not yet: wrong flyback math, divergent libraries and mutable approvals.
3. **Can Claude Code / Codex run workflows through MCP/CLI?**
   - The protocol is verified by direct stdio sessions.
   - A fresh Claude Code session cannot discover Mendex (not registered, no `.mcp.json`).
   - Codex and Antigravity are NOT VERIFIED (not installed or not connected).
4. **All nine stages operational?** They are implemented and persisted, but human approval gates can be bypassed by an agent.
5. **Tools genuinely integrated?** LTspice yes. FEMM no (unexcited). KiCad only superficially (unconnected output).
6. **UI shows real engineering data?** Partially: project, lifecycle and records yes; simulation numbers, waveforms and ERC/DRC no.
7. **Automatic sync?** Yes, by 4 s polling (works, but costly).
8. **Database reliable?** Consistent under concurrency and migration; not tamper-resistant for approvals, reports or measurements.
9. **Secure enough for local use?** Not until P0-1, P0-3 and P0-4 are fixed.
10. **Clean and maintainable?** Moderate: heavy duplication and swallowed exceptions.
11. **Installable on Windows?** Not as the v3.1 desktop; only the legacy installer exists.
12. **Ready for product development?** No. Requirements capture, buck/flyback first-pass work and LTspice simulation are usable with care.
13. **Top 10 issues:** P0-1, P0-2, P0-5, P0-3, P0-4, P0-6, P1-1, P1-3, P1-4, P1-8 (see 16).
14. **Fix first:** approval integrity (P0-1, P0-2), then data-root isolation (P0-3/4), then calculation correctness (P0-5, P1-1/2).

## **VERDICT: PARTIALLY READY — FIXES REQUIRED**

## Audit integrity notes
- **Mid-audit edits:** `src/mendex_core/desktop/service.py` (11:32:58) and `desktop/src/components/RevisionEngineeringPanel.tsx` (11:34:42) were modified by a process outside this audit, after the 11:19 baseline. Desktop findings in 09, 12 and 14 may straddle that change. All other 363 baseline files were unchanged at the end of the audit.
- **Pre-existing processes on real data:** two desktop backends with no `--root` (PIDs 18964, 19836) were running against the real data root. They were not started by this audit and were left untouched.
- **Real database touched by the suite:** the full test run refreshed the real `integration_health` table (tool-detection cache) through the browser tests. A read-only check found no product, revision, validation, record, review or lifecycle row changed.
- **Not verified:** the Tauri window itself (only the browser-fallback UI was screenshotted) and Codex/Antigravity connectivity.
