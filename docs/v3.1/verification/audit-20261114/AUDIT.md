# Current application audit ? 14 November 2026

Baseline commit: `d555d97efe6386b92c7bffefff167944072e0d99` (final commit). The only pre-existing untracked file was the Word editor lock file. This report supersedes historical missing-feature claims where current code/probes differ. Audit completed before remediation; subsequent fixes are recorded separately.

## Result

The application has advanced substantially. Developer handover is possible with known issues; complete software acceptance has not been demonstrated. A product lifecycle milestone is separate from application acceptance.

Fresh regression on an isolated default root: **349 passed, 5 failed, 1 skipped, 1 deselected**, 243.65 seconds. Excluded the localhost/live-project command-center module, the UI module hardcoded to the actual C:\Mendex studio root, and the explicit native-window launch test. These exclusions are NOT_EVALUATED, not passes. One legacy editor-handoff test still bypassed its subprocess mock through the newer Win32 launcher and opened an editor against its disposable root; its isolation needs updating. No full-suite green claim.

TypeScript/Vite production build passed (1583 modules). All 20 engineering-record schemas match. Lifecycle schema check fails because the checked-in definition omits the now-supported `human_review` criterion. Actual CLI, desktop stdio and MCP stdio processes each exited 0 on one disposable shared root; MCP advertises 64 tools. Browser bootstrap reports `iab` unavailable and discovery returns []; interactive UI behavior is NOT_EVALUATED. Offline native Cargo check cannot start: cargo component is not applicable to the configured stable MSVC toolchain. No installer or clean-machine test performed.

## Improvements independently confirmed

- Four simultaneous first-start processes exited 0 against the same new root: the earlier startup race was not reproduced.
- Repeated design generation preserved every earlier registered file/hash: the overwrite defect was not reproduced.
- Omitted MCP electrical inputs are rejected, not defaulted.
- A design conflicting with a saved specification is rejected before generation.
- Native Tauri `rpc_dispatch` is used by the client; restart/shutdown handling exists in Rust. This supersedes the earlier missing-transport diagnosis, but is not a native runtime acceptance result.
- Manual reviewer attribution and stale-document/evidence guards are implemented. Credential-based identity is not required by the user's chosen manual-review workflow.
- Light styling and the corrected 20-reference / 30-category component catalog are present.

## Confirmed findings before changes

| ID | Priority | Finding and evidence | Required activity |
|---|---|---|---|
| A01 | P0 | `_spawn_gui` automatically deletes adjacent lock files and FreeCAD recovery caches, without proving they are stale or obtaining a recovery decision. Those files can protect active edits or recover unsaved work. | Preserve locks and recovery data; leave recovery handling to the native application. Mock launch in regression tests. |
| A02 | P0 | `ProjectDetail.tsx` renders fixed SV1000 requirements, calculations, solver qualification/results and CAD paths for arbitrary projects. Completion counts use recorded OR effective completion, so a stale blocked stage can look completed. Validation count is labeled gates verified. | Render saved revision records and effective status; make absent data explicit. Retain review and file-opening functions. |
| A03 | P1 | Disposable project A's desktop response contains project B's queued fixture job. `project()` returns all integration jobs; the raw nested JobRecord payload also differs from the flattened React job interface. | Scope by authoritative workspace/revision context and normalize the shared desktop projection. Unattributed jobs must never become revision evidence. |
| A04 | P1 | The disposable core has two designs, while desktop `project().designs` is always empty. | Read linked designs through the shared core; never assign a legacy design to a revision by guessing. |
| A05 | P1 | Five regression failures: ambiguous simulation input exception contract, outdated artifact-location fixture, CLI/MCP generation fixtures missing newly required inputs, and editor-handoff mock bypass. | Inspect each failure and preserve stricter input semantics while updating stale tests or fixing implementation defects as warranted. |
| A06 | P1 | Lifecycle definition schema lacks `human_review`, although the model supports it. | Regenerate canonical schema and recheck all contracts. |
| A07 | P1 | Rust toolchain cannot run offline check; bundle configuration does not supply a Python backend. Runtime expects an installed interpreter/backend or a bundled path. | Repair/build native packaging and validate clean install, backend dependencies, shutdown and recovery in a separate acceptance phase. |
| A08 | P2 | Real browser UI navigation, polling latency, waveform interactions and native installed behavior are unavailable for observation. | Execute interactive acceptance when a supported browser/native session is available. |
| A11 | P0 | BOM generation falls back to a fixed SV1000 list, overwrites fixed output paths without a draft guard, and prints qualified/approved language. Source confirmed during the first repair pass; pre-change SHA-256 retained. | Require explicit revision BOM data, preserve frozen/history files, write unique draft exports and remove invented qualification claims. |
| A12 | P1 | Legacy clearance/creepage calculator logs pollution_degree but does not use it to select the calculation path, while emitting a compliance scalar. Source inspection confirmed; no standards qualification asserted by this audit. | Qualify applicability and source tables, or return NOT_EVALUATED for unsupported contexts. Treat legacy safety verdicts separately from arithmetic tests. |
| A10 | P1 | The current waveform endpoint validates the ASCII header but returns an empty samples array without parsing the file. | Implement bounded real sample parsing and waveform interaction acceptance; do not show fixed solver metrics. |
| A09 | P2 | Component catalog is sourced reference data, not all parts in all categories; geometry-only cores and loss fits intentionally remain uncharacterized. | Continue exact-part/source/model qualification; do not fill unknowns with invented numbers. |

## Current project data observed without live writes

Read-only SQLite integrity_check is `ok`, with zero foreign-key violations. There is one project, SV-1000. A consistent SQLite backup and copies of relevant product/artifact files were evaluated only in a disposable root. Effective stages 1?7 are COMPLETED, prototype_testing is NOT_STARTED, and documentation is recorded COMPLETED but effectively BLOCKED because its approved review is stale after document/specification/requirements modification. This describes the stored process state; it does not independently qualify solver physics, human identity or hardware safety. Do not rewrite these historical decisions to make an audit green.

The disposable snapshot's results were saved successfully; its cleanup initially reported a retained SQLite handle. No live file was removed by that cleanup. The snapshot is a software verification aid, not new project evidence.

## Evidence

- `pytest.xml`, `pytest.log`: full baseline regression and five failure traces.
- `live-readonly-summary.json`: SQLite integrity, counts, project/revision metadata and recent lifecycle events.
- `live-files-before.json`: SHA-256 and size of 82 live product/design/artifact files.
- `lifecycle-snapshot-view.json`: effective lifecycle evaluation on disposable copied data.
- `probe_current.py`, `probe-results.json`: startup/integrity/input fixes and current cross-project jobs / omitted-design reproduction.
- `protocol-smoke.json`: actual independent CLI/MCP/desktop process responses.
- `source-before.json`: hashes of inspected application files before remediation.
- `lifecycle-contract-drift.diff`: exact schema mismatch.

## Activity order

1. Preserve recovery/lock files; scope revision data; correct schema drift and failing tests.
2. Replace fixed project-screen results with authoritative records and effective statuses; validate on dissimilar disposable projects.
3. Native installer and interactive acceptance, followed by remaining solver/report evidence qualification. Do not run physical hardware or manufacturing approval.

Remediation results will be documented in `REMEDIATION.md`; this baseline report and raw failure evidence remain unchanged.
