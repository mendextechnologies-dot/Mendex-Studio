# Mendex Engineering Studio v3.1 — independent implementation audit

Audit date: 13 November 2026 (Asia/Calcutta). Assignment: verification only.

## 1. Executive summary

**Final architecture acceptance: PARTIALLY IMPLEMENTED.** The local Python core,
CLI, MCP, nine-stage record engine and generic prompt library exist and support
useful operations. A disposable reference executed through the actual MCP stdio
process and was observed through a separately running desktop Python bridge.
This is meaningful backend integration evidence, not completed desktop acceptance.

Do not accept v3.1 for unrestricted real engineering use yet. Confirmed blockers
include overwritten registered design files, invented/default engineering inputs
on legacy MCP design calls, hardcoded engineering results and verification claims
in React, and a Tauri/frontend transport mismatch. Native simulation execution is
not consistently connected to revision-specific evidence inspection and reports.
Authenticated engineering review is unavailable, so the default review-gated
lifecycle cannot be completed. No manufacturing authorization is supported.

Application source was not changed. Existing working-tree modifications and live
engineering data were preserved. Only audit documentation, disposable harnesses,
test/build output and evidence copies were added. The first harness request error
and a subsequent real startup race are retained separately from the successful run.

## 2. Evidence and scope

Evidence directory: [audit-20261113](audit-20261113/).

| Evidence | Meaning |
|---|---|
| `working-tree-status.txt`, `environment.json`, `source-manifest.json` | Current checkout identity, pre-existing changes and inspected source/test/prompt hashes |
| `pytest.log`, `pytest.xml`, `selected-test-results.json` | Fresh full local regression: 323 passed, 1 skipped, process exit 0; selected named tests and durations |
| `transcript.json`, `summary.json` | First attempt: unsupported `ripple_voltage_v` rejected; harness error, not a demonstrated application defect |
| `attempt2/mcp-stderr.log`, `attempt2/summary.json` | Concurrent first launch: `table products already exists`; MCP process exits, harness times out |
| `attempt3/transcript.json`, `attempt3/summary.json`, `attempt3/cli-lifecycle.json` | Successful serially initialized disposable MCP/CLI/desktop-backend reference |
| `disposable-reference-snapshot/`, `reference-manifest.json` | Preserved reference SQLite backup and native inputs, outputs, snapshots and report; 20 files |
| `gap-probes.json`, `probe_gaps.py` | Repeat generation overwrites, omitted MCP inputs, specification synchronization and safety-calculator probes |
| `cargo-check.log` | Native offline compilation blocked: `serde` unavailable, exit 101 |
| `kicad-version.json` | Native CLI reports KiCad 10.0.7, exit 0 |

Harness commands:

```powershell
.\.venv\Scripts\python.exe -m pytest -q --junitxml=docs/v3.1/verification/audit-20261113/pytest.xml
npm.cmd run build # working directory: desktop
.\.venv\Scripts\python.exe scripts/export_lifecycle_contracts.py --check
.\.venv\Scripts\python.exe scripts/export_engineering_record_contracts.py --check
.\.venv\Scripts\python.exe docs/v3.1/verification/audit-20261113/run_audit.py
.\.venv\Scripts\python.exe docs/v3.1/verification/audit-20261113/probe_gaps.py
& "$env:USERPROFILE\.cargo\bin\cargo.exe" check --offline --manifest-path desktop/src-tauri/Cargo.toml
```

Frontend production assets compiled successfully: TypeScript plus Vite 5.4.21,
1,582 transformed modules; build exit 0. This does not compile/package Tauri.
Nine lifecycle schemas and twenty record/calculator schemas matched canonical
models. Cargo 1.99.1 is installed under the user profile but not on this shell's
PATH; offline resolution failed for `serde`. No dependencies were installed.

Browser bootstrap succeeded but `iab` was unavailable; browser discovery returned
`[]`. Visual interaction, screenshots, native installed-window behavior and actual
screen-update latency are **NOT VERIFIED**. Existing screenshots and historical
PASS documents are not fresh acceptance evidence. Unavailable engineering checks
remain **NOT_EVALUATED**, including physical tests and the excited FEMM reference.

## 3. Architecture assessment

Actual shared backend: `StudioService` with controller, lifecycle and engineering
record services; CLI and MCP route to these services. DesktopService reads the
same project/revision/record/database state. The disposable observer started before
project creation and subsequently saw one project, one calculation, one design,
six files, then two revisions, the simulation and generated report.

There is no mandatory cloud or embedded AI provider on this exercised path.
Generic prompts describe Codex, Claude Code, Antigravity and human CLI operation.
This audit used Codex to invoke actual MCP subprocess calls and CLI commands.
Native host registration of Mendex as a directly selectable Codex MCP connector
was not available in this session and is **NOT VERIFIED**; `mcp_config.json` alone
does not prove registration in every agent.

Two desktop paths coexist: the extensive PySide6 application and an unfinished
React/TypeScript frontend plus Tauri 2 shell. Qt still contains specification
authoring, calculations, simulations and workflow editing. The intended final
viewer-centered standalone architecture is not complete.

`desktop/src/api/client.ts` uses `fetch('/api/rpc')`. That endpoint is installed
only by Vite's `configureServer` development plugin. The Rust shell instead exposes
`rpc_dispatch`, which the frontend never invokes. A production bundle has no
implemented matching HTTP service. The Rust launcher also depends on relative
`.venv/Scripts/python.exe`, has no packaged Python sidecar, and lacks explicit
child shutdown/restart handling. `start_desktop.bat` launches Vite development mode.

## 4. Component verification scorecard

Statuses refer to the complete requested capability. A successful subset does not
make the whole component PASS.

| Component | Status | Evidence | Remaining Work |
|---|---|---|---|
| Codex-first architecture | PARTIAL | Actual Codex-driven MCP subprocess + CLI calls; shared core | Finish native viewer transport, lifecycle review and complete agent workflows |
| Engineering Core | PARTIAL | Reference calculations, designs, revisions, reports and persistence executed | Address startup race, native file collisions and inconsistent provenance |
| Nine lifecycle stages | PARTIAL | Nine definitions, guarded attempts/history/evidence/retries; regression coverage | Discipline criteria and authenticated review; eight default stages cannot complete |
| Generic Codex prompts | PASS | Master, nine generic stage prompts, validation guides and six templates; registered-tool/section contract test | Continue updating prompts as capabilities change; full unattended completion not claimed |
| MCP Server | PARTIAL | Real stdio initialization, 58 advertised tools, executed calls and error responses | Enforce legacy schemas/defaults and align simulation inspection |
| CLI | PARTIAL | Actual isolated lifecycle read exits 0; shared interface regression | Complete broad workflow parity and remaining agent operations |
| Project management | PASS | Reference project creation, stable UUID, cross-process read, no duplicate project on calculation retry | PASS is limited to exercised creation/retrieval path |
| Specifications | PARTIAL | Strict save/read and unknown-field rejection | Fix design-to-specification sync; extend missing engineering fields/provenance |
| Calculations | PARTIAL | Attributed losses run persisted, identical retry returns same record; four discoverable calculators | Render actual runs; address legacy safety verdicts and broaden qualified models |
| Design development | FAIL | Two designs overwrite four earlier registered files; omitted-input MCP call succeeds | Collision-free immutable paths, explicit inputs and revision/spec linkage |
| LTspice | PARTIAL | Installed 26.1.1.0; real RC execution exits 0; 526 samples parsed | Manifest/revision/version linkage, log retrieval and UI waveform presentation |
| FEMM | PARTIAL | Installed binary; existing native runner/reference tests assessed separately below | Excited, bounded numerical reference; trustworthy nonzero-result acceptance |
| KiCad | PARTIAL | CLI 10.0.7 executes; generated native files, fresh ERC/DRC tests pass | Populated valid/invalid engineering acceptance and viewer integration; empty-fixture success is insufficient |
| Automatic synchronization | PARTIAL | Separate desktop backend observes committed records; 4-second project/dashboard polling in source | Measure rendered latency, update all routes, prevent stale/out-of-order reads |
| Tauri + React UI | FAIL | Web build succeeds; native transport mismatch and hardcoded engineering claims | Wire native RPC, remove fabricated values, complete required viewer stack/features |
| Studio simplification | PARTIAL | React is largely a viewer; core has no built-in AI provider | Retire duplicate Qt authoring/workflow paths after capability parity; preserve human review |
| Engineering files | PARTIAL | Confined snapshot registration succeeds; hashes retained | Prevent native generation collisions; expose integrity and native opening in React |
| Revision management | PARTIAL | Two UUID revisions preserved; new draft/enrollment observed | Connect design/job revision IDs consistently; fix silent specification-sync failures |
| Validation and approvals | PARTIAL | Invalid self-approval rejected; conservative evidence/stale/dependency guards | Authenticated human decisions and laboratory-origin trust; no release authority |
| Reports | PARTIAL | Draft HTML/snapshot/hash record generated and separately observed | Include current job evidence truthfully; remove unconditional VERIFIED labels and wire access/export |
| SQLite data integrity | PARTIAL | Disposable `integrity_check=ok`, no FK violations; append-only/migration tests | Fix concurrent initial database creation and native-file evidence risks |
| Windows packaging | BLOCKED | Offline cargo check exits 101; no current Tauri installer demonstrated | Resolve native dependencies, package Python, clean-machine install/recovery/update tests |
| Complete end-to-end test | BLOCKED | Backend reference executed, screen stage unavailable and safety gates incomplete | Complete native UI, approved review workflow and fresh visible end-to-end acceptance |

## 5. Nine-stage verification

All nine prompts define purpose, inputs, questions, tools, operations, outputs,
structured records, validation, evidence, completion, review, errors and next steps.
The master prompt instructs the agent to discover tools and read the current stage;
an engineer need not manually paste all nine prompts. This is prompt guidance,
not an executable autonomous planner or a substitute for missing backend features.

Shared lifecycle operations support enrollment, start/reopen, block, fail,
request_review, attach_evidence, complete and guarded exemption. Attempts/events
persist in SQLite. The full regression exercises transitions, retries, conflicts,
revision isolation, damaged/stale/wrong-kind evidence and dependencies. Stage
definitions and record payloads are structured; arbitrary registered documents
remain files rather than fully typed discipline-specific analyses.

| Stage | Implemented operation/record path | Completion/review gap | Studio evidence |
|---|---|---|---|
| Project Initialization | Project, revision, enrollment and attempt history | Metadata criterion can complete; no engineering authorization | Backend shows stage; actual rendering NOT VERIFIED |
| Requirements and Specifications | Specification saves, sourced requirement snapshots, coverage | Numerical placeholder criterion; authenticated review unavailable | Backend data available; detailed coverage display incomplete |
| Feasibility and Architecture | Document/artifact registration, requirements and supported calculations | No complete typed alternatives/decision workflow; review unavailable | Files/design views only partially cover outputs |
| Engineering Calculations | Four existing calculators with exact inputs/results/provenance | Model applicability/acceptance criteria supplied by engineer; review unavailable | React calculation panel contains constants instead of runs |
| Engineering Design Development | Native generators, design records and artifact registration | Overwrites/default inputs and independent design/core revision identities | Hardcoded file names and metrics in CAD tab |
| Simulation and Analysis | Real LTspice/FEMM controller paths, jobs and inspection | Revision/manifests inconsistent; excited FEMM reference unavailable; review unavailable | Job list present; no rendered waveform viewer |
| Engineering Verification | Numerical validation records and integrity-aware evidence links | Human identity/laboratory origin not authenticated; review unavailable | Hardcoded standards claims; effective blockers not shown |
| Prototype and Physical Testing | Evidence-file ingestion and legacy measurement service | No dedicated instrument-rich MCP measurement workflow; actual lab tests NOT_EVALUATED; exemption review-gated | Backend can list measurements; complete review UX absent |
| Final Engineering Documentation | Draft report generation, snapshots, integrity metadata and export | Incomplete aggregation of newer engineering/job records; review unavailable | Lists reports but claims verification without checking integrity |

All eight post-initialization default stages require review. The backend explicitly
reports `approval_status=UNAVAILABLE`; it has no authenticated approve action.
Keeping these stages blocked is correct safety behavior, but does not satisfy the
requirement for working human approval gates. Criteria placeholders are not full
discipline acceptance definitions.

## 6. Disposable reference workflow and connectivity between clients

Successful attempt root:
`C:\Users\Sagar\AppData\Local\Temp\mendex-v31-audit-_qq0k30e`.
Retained copy: `audit-20261113/disposable-reference-snapshot/`.

1. Start actual `mendex_core.mcp` and `mendex_core.desktop` subprocesses using
   `--root`; initialize MCP and discover 58 tools. Desktop initially reads no projects.
2. Create `AUDIT-REF`, a synthetic software reference, through MCP; save explicit
   18/24/30 V input, 5 V/2 A output and 100 kHz specification.
3. Enroll lifecycle, start initialization and execute attributed losses calculation.
   Repeating the identical request returns the same persisted response.
4. Generate a generic buck design with explicit inputs. Desktop observer sees one
   project, one calculation, one design and six files.
5. Create `AUDIT-R002`; old revision is archived and new revision is draft.
   The native design is not automatically copied into the new revision.
6. Create an explicit disposable RC input in the new draft (R=1 kOhm, C=1 uF,
   10 V step, 5 ms transient). Register its expected SHA-256 through MCP.
   This is a software reference circuit, independent of the earlier buck design;
   it does not validate the buck or establish design-to-simulation linkage.
7. Execute the actual LTspice runner through MCP. Native exit 0, no log errors,
   `.raw` and `.log` produced. Desktop waveform endpoint returns ten requested
   original V(out) samples from 526 available points, with units and digest.
8. Inspect job through MCP: execution SUCCEEDED, but `manifest_path=null`,
   `tool_version=null`, `evidence_integrity=false`, `results_validated=false`.
   Log API says `Log unavailable; check evidence integrity`. Desktop job has
   `revision_id=null`, `evidence_available=false`.
9. Generate a new attributed draft report; independent desktop read sees it and
   two revisions. Its warning still says no automated simulations were executed,
   despite the separately persisted job: report aggregation is incomplete.
10. Reject invalid self-approval and completion before starting verification.
    Missing/stale evidence guards are additionally exercised by lifecycle tests.
    Actual physical test evidence was never asserted by this reference.
11. Actual CLI lifecycle read exits 0. SQLite integrity is `ok`; FK check is empty.
    Backend processes close at EOF. This does not verify Tauri child shutdown.

The observer proves cross-process backend visibility without restarting it.
Recorded `elapsed_ms` values measure request duration only. They are not rendered
synchronization latency. The required open-Studio 14-step visible synchronization
test remains **NOT VERIFIED**, and the complete engineering acceptance chain is
**BLOCKED**. No measured human/laboratory evidence or approval was fabricated.

## 7. Native tool assessment

| Check | LTspice | FEMM | KiCad |
|---|---|---|---|
| Installation | `C:\Program Files\ADI\LTspice\LTspice.exe` | `C:\femm42\bin\femm.exe` | `C:\Program Files\KiCad\10.0\bin\kicad-cli.exe` |
| Version | File metadata 26.1.1.0 | File metadata `1,0,0,1`; authoritative solver version NOT VERIFIED | Actual `--version`: 10.0.7 |
| Configuration | Existing runner discovers installed executable | Existing native runner finds installed binary | CLI resolver finds installed executable |
| Generated input | Buck `.net`/`.asc` and explicit RC fixture | Generic magnetic generator exists; regression reference assessed below | Native `.kicad_sch` and populated `.kicad_pcb` generated |
| Native execution | Actual RC succeeded, exit 0 | Unexcited-core execution is not qualified magnetic acceptance | Fresh regression includes ERC/DRC; results below |
| Results extraction | 526-point RC waveform parsed; native metrics returned | Excited numerical reference unavailable, NOT_EVALUATED | Native JSON parser exists; empty boards cannot establish design acceptance |
| Persistence | Job and raw/log files exist; revision/manifest/version gaps | Controller job path exists; equivalent provenance limitations | PCB check snapshots/history supported; fresh test outcome governs execution claim |
| Studio display | Backend returns samples; actual chart rendering absent | Actual result rendering NOT VERIFIED | File/check backend exists; actual visible result acceptance NOT VERIFIED |

Historical `verification/11_LTSPICE_FEMM_KICAD.md` claims a 198 mT FEMM PASS and
`verification/19_FINAL_ACCEPTANCE_SIGNOFF.md` must not override this audit.
The current excited-reference acceptance test explicitly skips. A passing test
that checks correct NOT_EVALUATED behavior for an unexcited zero-field model does
not qualify an excited transformer model. Native solver execution, parser success,
engineering validation and review are separate statuses.

## 8. UI issues and synchronization gaps

- **Fabricated results (P0):** `desktop/src/pages/ProjectDetail.tsx` renders constant
  turns ratio 61.2:1, Np=5/Ns=306, 4.46 uH, Dowell factor 3.78, core loss 1.16 W,
  core selection and switch stress values, irrespective of calculation records.
  It states 5 mm isolation/3000 V verification and zero violations without backend
  evidence. CAD cards hardcode commercial-product file names; missing candidate
  metrics become 88% efficiency, 94.4 V stress and ten components. Missing frequency
  becomes 100 kHz. Reports always show `VERIFIED DOSSIER`; unknown job exit becomes 0.
- **Lifecycle contract mismatch (P1):** React expects `definition.title` and
  `description`; backend definitions provide `name` and `purpose`. UI tests `PASSED`
  while canonical completion is `COMPLETED`, and displays recorded status without
  effective status, staleness, criteria or blockers. This can conceal invalidation.
- **Incomplete required stack (P1):** React/TypeScript and a Tauri 2 manifest exist.
  No Tailwind, shadcn/ui, TanStack Query, ECharts or Plotly dependency is declared.
  Screens use inline/custom CSS. No complete light/dark switch or waveform chart
  is implemented in the inspected React source.
- **Polling (P1):** Dashboard/projects/simulations and project detail have 4-second
  polling. Reports, components, tools and settings fetch once on mount. Details
  use an in-flight overlap guard but do not cancel/version old-project responses;
  other routes mostly send errors to console.
  Normal refresh behavior, latency, duplicates and cross-route consistency remain
  unverified in a running window.
- **Incomplete actions (P1):** Report/file rows are largely text, despite backend
  open/export operations; native opening and report accessibility are not verified
  through this UI. TypeScript payload declarations differ from record-list wrappers.
- **Duplicate workflows (P1):** PySide6 retains editable specification forms,
  design/simulation panels, visual workflow canvas and manual status controls.
  Backend reuse exists, but product simplification and UI retirement are unfinished.
  Engineering review controls must be preserved and authenticated separately.

## 9. Data integrity and security findings

| ID / Priority | Finding and evidence | Required resolution / acceptance |
|---|---|---|
| G01 / P0 | `gap-probes.json`: creating a second design in the same revision changes all four files registered to the first design. `design/service.py:generate_native_artifacts` namespaces by design revision index only, then uses `write_text`/exports. | Unique design/revision artifact directories, no overwrite, historical-file digest regression and explicit regeneration policy |
| G02 / P0 | MCP `generate_design` accepts omitted required electrical inputs; dispatcher supplies 24 V, 5 V, 4 A, 100 kHz and 0.05 V. Probe succeeds even without advertised required fields. | Enforce schema at invocation and explicit engineer inputs throughout legacy and new paths |
| G03 / P0 | Hardcoded engineering/standards/verification assertions appear in viewer independent of actual evidence (section 8). | Show actual values and effective integrity status; missing values remain unavailable/NOT_EVALUATED; test empty/unrelated/stale projects |
| G04 / P0 | Simultaneous first-start MCP/DesktopService initialization fails `CREATE TABLE products` with `table products already exists`; captured attempt 2 traceback. | Serialize schema bootstrap/transactional migrations; fresh-root concurrent startup regression; retain backups |
| G05 / P1 | Frontend production RPC is incompatible with Tauri command; relative development Python launcher; no native backend lifecycle. | Implement reviewed native bridge and packaged backend; clean install/startup/shutdown/crash recovery/update preservation tests |
| G06 / P1 | MCP simulation job lacks core revision ID, version, metrics outputs and manifest. Result/log inspection cannot validate evidence; project detail lists all project jobs without selected-revision filtering. | Persist exact design/revision/input/tool context, unique run snapshots and manifests; integrity-aware result/log/chart APIs |
| G07 / P1 | All eight default engineering stages require an authorization mechanism that does not exist. Caller reviewer/operator strings are attribution only. | Authenticated independent engineering-review decisions and suitable discipline criteria; agent self-approval must remain rejected |
| G08 / P1 | `generate_design` attempts `Specification(ripple_voltage_v=...)`, a field absent from the strict model; broad `except` hides failure and still returns SYNTHESIZED with apparent revision linkage. | Use correct canonical schema, preserve source/assumptions, fail visibly and atomically on synchronization failure |
| G09 / P1 | KiCad/FEMM qualification remains incomplete; excited FEMM reference is explicitly skipped. | Qualified safe excited/bounded FEMM reference and populated valid/invalid KiCad references with raw logs and results |
| G10 / P1 | Report generated after a successful native job still warns no simulations executed; React labels arbitrary report VERIFIED. | Aggregate appropriate attributed records/job evidence and distinguish intact, stale, legacy, failed and unavailable states |
| G11 / P1 | Legacy IEC calculator reports `compliant=1` for 5 mm slot while its own computed creepage requirement is 20 mm; changing pollution degree 1/2/3 leaves outputs unchanged. Legacy UI invokes it as a standards audit. | Qualified model review; restrict unsupported profiles, eliminate unsupported compliance conclusions and preserve uncertainty. External standards correctness was not established by this audit. |
| G12 / P1 | Vite binds `::`; `/api/rpc` has no authentication/origin validation or bounded HTTP body, and forwards native-open/export methods. | Keep local development surface confined, bound requests and define reviewed local authorization/origin policy; do not expose it as an internal service |
| G13 / P1 | Legacy `run_simulation(netlist_name)` joins caller paths without the confined validator used by new artifact operations; FEMM adapter can append quit() to input scripts and filelink uses shared installation files. Source finding; exploit not executed. | Constrain inputs to explicit current draft, execute unique copies, preserve originals and isolate concurrent native sessions |
| G14 / P1 | React synchronization, lifecycle fields, error states, charts, report/native actions and specified UI stack are incomplete (section 8). | Complete viewer and verify all 14 visible sync steps with latency/stale/duplicate evidence |
| G15 / P1 | Seed library constructs new UUIDs on every service startup and uses default 'Verified' provenance labels without independently checked datasheets. UI repeats verified-catalog language. | Stable identities, explicit sourced/seeded/unverified provenance and qualified component/material records |
| G16 / P1 | Legacy Qt authoring/workflow functionality remains; full measurement ingestion is not exposed through typed agent operations. | Agree supported agent workflow parity, preserve human-operated laboratory boundary, then retire duplicate UI functions |
| G17 / P2 | Historical v3.1 PASS documents and checkbox claims conflict with source and fresh evidence; Python package version remains 0.1.0 while desktop is 3.1.0. | Reconcile release documentation/versioning after fixes; retain historical evidence rather than rewrite raw records |
| G18 / P2 | Component/file/record lists have presentation limits and no complete paging UX; several views swallow errors or leave loading text. | Explicit truncation/paging and accessible loading/error/empty states |
| G19 / P3 | Optional richer native previews and numerical comparison views remain unqualified. | Add only after required integrity, native packaging and acceptance gates |

The new lifecycle/record APIs do provide confined paths, expected hashes, frozen
snapshots, append-only triggers, idempotency and optimistic guards. Those strengths
do not cover every legacy generator/runner path. An agent can submit self-attributed
MEASURED records if a file and numerical bounds are supplied; this is not proof of
laboratory origin. The generic lifecycle refuses to turn it into authenticated
approval. The system must not claim provenance authentication it does not implement.

No secret values were requested or displayed. This audit did not perform a
comprehensive dependency vulnerability scan, credential-store audit or penetration
test; overall security certification is **NOT VERIFIED**. The local transport and
path findings above are source-reviewed risks, not claims of observed remote access.

## 10. Windows readiness

The web bundle builds. The native offline check cannot resolve `serde`; no Tauri
production installer was built or installed in this audit. Rust source has no
portable packaged-Python fallback, explicit child termination/wait on window close,
request timeout or robust child-crash response. The stdio backend uses concurrent
workers, whereas Rust reads the next response line without correlation validation.
These require native integration tests, not only Python tests.

Existing `dist/` wheel/source archive and `MendexStudio-v2.0-Setup.bat` do not
establish a working v3.1 Tauri Windows installation. `packaging/README.md` describes
manual Python foundation distributions; `start_desktop.bat` starts a dev server.
Clean-machine/offline installation, normal shutdown, crash recovery and preservation
of user data across updates are **NOT VERIFIED** for the intended standalone UI.
No CI/CD or deployment work was performed or is proposed as an audit prerequisite.

## 11. Test execution results

**323 passed, 1 skipped in 394.46 seconds; pytest process exit 0.** There were no
regression failures. Evidence: `audit-20261113/pytest.log`, `pytest.xml` and
`selected-test-results.json`. This supersedes earlier 318-test totals for this
working-tree audit; historical results were not rewritten.

| Fresh check | Result | Interpretation |
|---|---|---|
| Generic stage prompts match real lifecycle/tool contracts | PASS, 0.198 s | Nine prompts, required sections and registered operation references |
| CLI/MCP lifecycle and record interface tests | PASS in full suite | Shared records, errors, retries, no self-approval and existing-service delegation |
| Lifecycle/record core integrity tests | PASS in full suite | Stale/damaged/wrong-kind evidence, rollback, backups/restore, append-only and concurrency guards |
| Real LTspice connector via orchestrator | PASS, 1.347 s | Native connector path executes |
| Analytical RC reference | PASS, 0.801 s | Native waveform compared against first-order analytical response within 1% |
| Real buck simulation | PASS, 3.216 s | Native solver and bounded converter outputs; not physical validation |
| FEMM unexcited-core run | PASS, 1.315 s | Correctly reports zero field and NOT_EVALUATED; this test's PASS is a software-safety result |
| Excited FEMM numerical reference | SKIPPED / NOT_EVALUATED | No winding-current/boundary-condition reference exists |
| Revised acceptance KiCad ERC | PASS, 19.200 s | Native call exits 0; inspected fixture is an empty sheet despite the broad test name |
| Revised acceptance KiCad DRC | PASS, 194.042 s | Native call completed, no timeout; inspected fixture is an empty board |
| v2 acceptance ERC / DRC | PASS, 8.141 / 10.786 s | Explicitly preserves NOT_EVALUATED for empty designs |
| Qt tests | PASS in full suite | Existing UI regression, not native React/Tauri acceptance |
| Frontend production asset build | PASS, exit 0 | TypeScript/Vite compilation only |
| Generated schema checks | PASS | 9 lifecycle + 20 record/calculator contracts |
| Offline native cargo check | BLOCKED, exit 101 | Missing cached `serde`; production native build not established |

The entire regression can pass while the independent probes expose defects because
existing assertions do not cover those cases. Each native test must be interpreted
by its assertions: synthetic fixtures, mocked native file opening, unexcited models
and installer-script existence checks do not qualify physical engineering or a
Windows installation. The new harnesses are retained audit reproductions, not
new application regression tests or fixes. The successful harness's `completed=true`
means the scripted sequence returned, not that every engineering capability passed.

## 12. Acceptance answers and prioritized remaining work

1. **Entire engineering work through Codex? No.** Supported project/specification/
   calculation/design/simulation/record/report operations work; authenticated human
   review, complete physical evidence trust, complete tool qualification and final
   visible handover do not.
2. **Every stage functional? Partially.** Nine stages and prompt/record/state APIs
   exist, but full discipline workflows and review-gated completion are incomplete.
3. **Automatic Studio display? Partially at the backend; visible test NOT VERIFIED.**
   Polling is incomplete and native production transport is incompatible.
4. **All supported tools integrated? No.** Real LTspice executes; FEMM and KiCad
   capabilities need the qualifications and remaining work identified above.
5. **Standalone Studio complete? No.** Web assets compile; native application and
   required visualization/truthfulness features fail acceptance.
6. **Duplicate functionality? Yes.** Qt still contains engineering authoring,
   calculation, simulation and workflow controls.
7. **Records/revisions reliable? Mixed.** SQLite/record protections work on exercised
   paths; confirmed artifact overwrites, initial-start race and missing job revision
   linkage prevent an overall reliability PASS.
8. **Windows installable/operational? NOT VERIFIED for v3.1 Tauri.** Dev build and
   foundation packaging are not installed-native acceptance.
9. **Incomplete work?** G01–G19 above, led by P0 integrity/input/display/bootstrap
   blockers, then native UI/packaging, traceable solver evidence and human review.
10. **Start real engineering projects?** Limit use to supervised exploratory work
    with independently checked inputs/results and explicit evidence retention.
    Do not use the present UI as authoritative verification or accept v3.1 as a
    completed engineering platform until P0 issues and required acceptance tests close.

Fix order: preserve evidence and explicit inputs (G01–G04), restore trustworthy
revision/job/spec/report linkage (G06/G08/G10/G13), finish native viewer and safe
local transport (G05/G12/G14), then qualified models/tool references, independent
review and remaining workflow parity. Repeat relevant tests and the complete
visible disposable workflow after approved fixes. **No fixes were implemented.**
