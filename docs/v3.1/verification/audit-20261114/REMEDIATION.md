# Audit repairs and remaining acceptance ? 14 November 2026

The [baseline audit](AUDIT.md) inspected commit d555d97 and independently recognized the other agent's startup, artifact-preservation, explicit-input, specification-conflict, native-RPC and manual-review improvements. Existing native snapshot/manifest regression also passed; current report source aggregates attributed native jobs. Historical assertions that all these features were missing are superseded.

## Completed first repair pass

| Finding | Result |
|---|---|
| A01: destructive CAD launch cleanup | Removed automatic lock/recovery deletion. A two-case regression failed before the fix and passes afterward. Actual desktop creation is mocked in tests, including the newer Win32 boundary. |
| A02: fixed SV1000 screen values / effective-status errors | Specifications, requirement snapshots, calculations, revision jobs and designs now use shared-core data. No fixed project electrical values, solver metrics, CAD paths or qualification badges. Completion counts and coloring use effective status. Validation displays effective verdicts and opens evidence through the integrity-checked evidence operation. Existing review actions, file browsing and report functions remain. |
| A03: cross-project job leakage / wire mismatch | Normalized desktop jobs expose the fields expected by React while retaining stored request/result. Revision attribution requires consistent explicit project/revision/workspace IDs. Project panels exclude other projects/revisions and legacy unattributed jobs; the global job list can still show them without claiming revision evidence. |
| A04: missing designs | Project API returns designs explicitly linked to that project and core revision. Native CAD files are also listed independently; unassigned historical designs are not guessed into a revision. |
| A05: regression fixtures | Updated structured ambiguity-error expectation, artifact snapshot locations and required frequency/ripple input fixtures. Editor/native routing tests mock the actual spawn boundary; real native windows are not opened by routing checks. |
| A06: lifecycle schema drift | Regenerated the four affected schema files from the canonical human_review-capable models. Nine lifecycle and twenty engineering-record schema checks pass. |
| A11: example/overwriting/approved BOM exports | Requires explicit nonempty revision bom.json rows with positive quantities. Draft-only guard and transaction serialize against revision freezing. Source and export paths stay confined. Each export uses a new UUID directory and retains exact source bytes/hash. Removed the default example parts, fixed safety/procurement/approval language and qualified-item claims. PDF availability is reported honestly. Existing BOM documents are not rewritten. |

BOM buttons now discover existing revision files instead of fixed SV1000 filenames. UI polling text matches the four-second configuration. Changing project resets the project view and review state.

## Validation and preserved evidence

- Baseline: 349 passed, 5 failed, 1 skipped, 1 deselected; excluded live-data/browser modules.
- First focused repair regression: 49 passed. Integrity/BOM tests: 10 passed.
- An intermediate full run completed 364 passing assertions but exited with native status 0xc0000409 during shutdown. It was **not** accepted as a clean run. Raw XML/log and exit-status record remain available.
- After closing the test launch-isolation gap, separate UI/native-routing checks passed 33 tests and exited 0.
- **Final regression: 365 passed, 1 skipped in 174.65 seconds, process exit 0.** The native launch-routing test is now included. Two modules remain excluded: localhost/browser tests coupled to the live app and the safety/BOM UI module hardcoded to the real production data root.
- The skip is the excited FEMM acceptance reference (winding current and boundary conditions), which remains NOT_EVALUATED. Passing an unexcited software fixture does not qualify magnetic physics.
- Real React server rendering covered all ten project tabs on two dissimilar disposable core payloads, plus stale lifecycle, failed/stale validation, and empty/unknown states. The component-library render checks also passed. This is not browser interaction or visual acceptance.
- Latest TypeScript/Vite production build passed (1584 modules). All 29 checked contracts match; git diff whitespace check passed.
- Fresh disposable before/after probes show zero overwritten registered artifacts, rejection of omitted inputs and conflicting specifications, zero project-B jobs in project A, two linked designs visible instead of zero, and four concurrent initializations exiting 0. The after-probe command emitted the expected omitted-input validation trace to stderr; its shell returned nonzero. Focused tests and the final regression provide clean-process evidence for these fixes.
- The updated local development service is listening on **127.0.0.1:5173**. Read-only HTTP handshake/projects/project/simulation calls passed against the real selected data root. The live project has zero integration job records and zero explicitly linked design records, alongside 56 revision files. That is a record-attribution distinction, not deletion of its manually produced engineering outputs.
- Preservation check: **82 of 82 live product/design/artifact files have unchanged bytes/sizes**; SQLite table row counts and project/revision metadata are unchanged. No review decision, stage transition, product simulation or product BOM export was performed by this repair pass.

## Remaining work, in order

1. **Legacy safety-calculation qualification (A12).** Pollution-degree applicability is not selected by the current heuristic calculation. Establish qualified source/applicability handling or return NOT_EVALUATED for unsupported cases. Arithmetic regression assertions are not standards evidence.
2. **Waveform viewer (A10).** The present endpoint validates the ASCII header but returns an empty sample array. Implement bounded real-data parsing, trace selection, truthful errors and native/interactive acceptance. Preserve existing solver bytes.
3. **Qualified excited FEMM reference and existing-file attribution.** The actual saved CAD/solver outputs remain accessible in Revision Files and registered artifact records. Add structured associations only from trustworthy saved context; never invent historical executions or approvals.
4. **Windows packaging (A07).** Repair the native toolchain, supply/install the actual Python backend and dependencies, build the current Tauri app and test a clean installation, shutdown/restart and recovery. Native installed behavior remains NOT_EVALUATED; no deployment was attempted.
5. **Interactive acceptance and remaining test isolation (A08).** Supported browser discovery is empty. Verify navigation, polling, native opening and waveform interactions when available. Replace live-data assumptions in the two excluded modules with disposable fixtures before including them in an unrestricted suite.
6. **Catalog coverage (A09).** Continue manufacturer-backed exact-part/model/core characterization. Zero-count categories and Unknown/NOT_EVALUATED properties are intentional until sourced.

The live read-only lifecycle view independently confirms stages 1?7 effectively COMPLETED, prototype_testing NOT_STARTED and documentation effectively BLOCKED by a stale review. No approval or physical-test record was fabricated or altered to clear these conditions.

## Evidence locations

`final-pytest.xml`, `final-pytest.log`, `final-exit-code.txt`; `repairs-core-v2.xml`, `repairs-integrity.xml`, `ui-isolated.xml`; `project-view-fixtures.json`; `live-http-readonly.json`; `live-lifecycle-readonly.json`; `live-preservation-check.json`; before/after gap probes. The running development server writes `dev-server.log`; it is a runtime log and may continue growing.
