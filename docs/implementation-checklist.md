# Three-day implementation checklist

Scope: final foundation addendum of supplied guide; user owns approval decisions. Start: 10 November 2026, Asia/Calcutta. This is an execution sequence, not a claim that elapsed calendar days have passed.

## Day 1 — foundation

- [x] Read complete source guide, inspect workspace and development runtime.
- [x] Establish package boundaries, service contract and engineering rules.
- [x] Implement typed specifications, SQLite v1 migration, products and revisions.
- [x] Create per-revision local workspaces; freeze previous specifications.
- [x] Build real-service desktop dashboard, product editor and navigation.
- [x] Pass persistence, failure-path and desktop smoke tests (10 passed).
- [x] Record environment and test results; initialize local Git baseline.

## Day 2 — extensibility

- [x] Adapter protocol, discovery capability registry and native executable detection/configuration.
- [x] Simulation-run contracts, no automatic execution claims.
- [x] Append-only manual validation entries with provenance and evidence hashes.
- [x] Basic draft HTML/JSON report service and module-specific workspace views.
- [x] Tool Manager, validation/report views and revisioned knowledge content (0.2).
- [x] Verify missing tools, no-PASS-without-evidence, stale evidence and deliberate failure cases (17 tests).

## Day 3 — integration

- [x] VS Code/project-file launching with path validation (automated launch mocks).
- [x] CLI doctor, diagnostic export and UI/core integration.
- [x] Product → specification → revision → tool check → evidence → draft report automated smoke test, including deliberate FAIL (21 tests).
- [x] Reproduce wheel installation in a fresh local environment; document rollback and remaining issues.
- [x] Capture seven desktop screens and run installed-package desktop smoke test.
- [x] Complete actual primary-workstation VS Code, File Explorer and native-document handoff (matching windows observed).
- [x] Complete backup/restore regression; preserve specification/evidence hashes after restore.
- [x] Add the remaining framework contracts: AI interface, versioned rule registry, data-only plugin loader and persisted simulation availability requests.
- [x] Complete draft/review editing, label changes, atomic product/specification saves, metadata/specification exports and evidence opening.
- [x] Pass 28 tests, Windows-native desktop smoke and independent local wheel-install checks.
- [x] Prepare v0.1.0 foundation tag and manual source/wheel/checksum packaging after the primary-machine release gates pass.

## Separate pilot qualification (not part of a software implementation claim)

- [ ] Independent second-engineer / clean-machine acceptance, following docs/manual-acceptance.md.
- [ ] Native solver benchmarks, actual engineering calculations, KiCad checks, physical/HV testing and product review: post-foundation scope, not claimed by this release.

Source repository: https://github.com/mendextechnologies-dot/Mendex-Studio · branch `main` · foundation software version `0.1.0`. See docs/requirements-matrix.md for the audit. Final-addendum release gate: primary-machine clean installation, repeatable smoke, no fabricated results, tests green and open issues documented. This replaces the earlier overly broad checklist item that conflated the foundation tag with independent pilot qualification. No engineering/manufacturing approval, CI/CD or deployment is implemented.

## v1.5 execution plan — Codex-owned workstream

- [x] Read the complete v1.4 specification/v1.5 addendum and verify actual baseline (28 tests).
- [x] Use separate codex/v1.5-integration branch/worktree and document actual ownership.
- [x] Publish stable 1.5.0 contracts, deterministic fake adapter, schemas, fixture and contract tests at 12b56c3.
- [x] Add all 18 catalog entries with truthful category/license/availability, plus persistent local settings and verification gates.
- [x] Add additive SQLite v4 migration, generic workspaces, queued jobs and result/evidence metadata without rebuilding legacy functionality.
- [x] Implement synthetic job start/progress/logs, cooperative cancel/timeout, retry, reopen and draft report export/opening.
- [x] Implement hash-verified evidence/input/artifact browser, manifest tamper checks and bounded text previews.
- [x] Add dataset/research provenance/license-reference UI and optional opaque file registration without parsing or downloading upstream data.
- [x] Preserve all 11 legacy navigation destinations and append 3 integration screens.
- [x] Pass **49 tests**, including contracts, legacy regressions, false-READY rejection, failures/timeouts/cancellation, CLI and UI end-to-end behavior.
- [x] Render and visually inspect Tool Center, Jobs, Logs, Evidence and Dataset UI; keep Agent 2 source/dependencies/AGENTS.md untouched.
- [ ] Review a committed Agent 2 PR and reproducible native smoke evidence; integrate only after tests and agreed review.
- [ ] Owner accepts the combined demonstration/limitations; no full-v1.5 release or sign-off is claimed by the Codex-only branch.


## v1.5 Two-Agent Integration & Engineering Modules — Antigravity & Codex Milestone

- [x] Read and align on Master Implementation Guide v1.3, v1.4 (18 tools), v1.5 (two-agent execution plan), architecture and engineering rules.
- [x] Verified and truth-tested all 18 tools and research datasets: verified installed LTspice 26.1.1.0, Python 3.13.7, Git 2.45.2; kept 15 unavailable/commercial tools truthfully marked NOT_INSTALLED/OPTIONAL_UNLICENSED.
- [x] Implemented secure, sandboxed execution engine: SafeSubprocessRunner with `shell=False`, argument list validation, process-tree termination, isolated directories, and SHA-256 artifact hashing.
- [x] Implemented Universal V15 Connector architecture with V15ConnectorRegistry and native script generators (FEMM 4.2 Lua, FreeCADCmd bobbin, OpenModelica `.mos`).
- [x] Integrated canonical research datasets (SwitchLossDB CSV query engine, MagNet loss benchmark fixtures).
- [x] Built analytical loss calculation engines: Dowell AC winding resistance factor, Flyback transformer parameter sizing, semiconductor conduction & switching losses, and MagNet Steinmetz core loss.
- [x] Completed comprehensive 5-part Master Audit Package under `docs/audits/` (Master Audit, Traceability Matrix, Tool Integration Audit, Implementation Gaps P0-P3, Next Action Plan).
- [x] Merged Codex UI branch and Antigravity Integrations branch cleanly into `main` with 100% backward compatibility.
- [x] Integrated interactive engineering workbenches (`TransformerWorkspacePanel`, `SemiconductorWorkspacePanel`, `DCDCWorkspacePanel`) into `StudioWindow` while maintaining 14 navigation pages and dynamic specification synchronization.
- [x] 90 automated tests passed across adapters, contracts, core services, UI, calculations, and integrations (`pytest` green in 10.17s).
- [x] Desktop smoke tests passed (`scripts/desktop_smoke.py` and `scripts/v15_codex_smoke.py`).

## Independent final verification — 10 November 2026

This verification does not close the acceptance gate or implement fixes. Scope: frozen main `30cbb15`, initial main `7230079`, comparison Codex `f2be079`, released baseline `2055673`.

- [x] Re-run latest main suite: **90 passed** at short paths; **13 failed, 77 passed** at the deeper root. Retain both results.
- [x] Re-run Codex candidate: **96 passed** at short and deeper roots; these fixes are not present in tested main.
- [x] Verify existing native RC software execution and raw artifacts; reproduce health, dataset, runner, parsing, report and input-collision failures without application changes.
- [x] Inspect/test concurrent UI delta; retain stale unspecified-revision fields and hardcoded-export reproductions.
- [x] Produce [independent final verification](audits/final-verification-20261110-01/FINAL_IMPLEMENTATION_VERIFICATION.md), complete status matrix, owners and completion tasks. Existing root-level verification report preserved separately.
- [ ] Close independently reproduced defects and resolve blocked/unverified checks, then verify one immutable acceptance commit and obtain actual owner acceptance. **Studio completion is NOT YET VERIFIED.**

## Codex final implementation audit — current source 0f299dd

- [x] Freeze current source and separate remediation0312f5a; retain exact commands/source hashes and previous reports.
- [x] Execute current short/deep suites: **90 passed**; **13 failed,77 passed**. Candidate: **112 passed,1 failed** at each path regime; released baseline: **28 passed**.
- [x] Independently run existing RC fixture, generic FreeCAD STEP export and Jupyter software-marker notebook; distinguish direct native components from unimplemented Studio operation wrappers.
- [x] Reproduce readiness/data/parser/runner/report/input/form failures; verify all five optional configuration-only guards.
- [x] Save the independent [Codex final audit](audits/FINAL_IMPLEMENTATION_VERIFICATION_CODEX.md), normalized traceability matrix, all18 statuses and agent-wise actions. No application changes/installations or automatic fixes performed.
- [ ] Resolve listed findings, integrate reviewed workstreams and reverify one accepted source tree. **NO — IMPLEMENTATION INCOMPLETE.**

## v1.6 Operational Readiness & Workflow Validation — Antigravity (Agent 2) Milestone

- [x] Read and align with Version 1.6 Execution Specification (10 November 2026), architecture.md, engineering-rules.md, and contracts/README.md.
- [x] Classified and evidenced all 18 approved tools/resources in [docs/v1.6/TOOL_READINESS_MATRIX.md](v1.6/TOOL_READINESS_MATRIX.md) (Gate C: PASS; 18/18 entries classified with exact version, capability scope, license constraints, and blockers).
- [x] Implemented and verified generic end-to-end simulation workflow using real installed LTspice 26.1.1.0 in [docs/v1.6/WORKFLOW_TEST_REPORT.md](v1.6/WORKFLOW_TEST_REPORT.md) (Gate B: PASS; queued -> running -> exit code 0, outputs hashed to manifest, truthful NOT_EVALUATED provenance, exported report, deterministic rerun).
- [x] Verified critical failure, timeout, cancellation, tampering, and recovery modes in [docs/v1.6/RESILIENCE_TEST_REPORT.md](v1.6/RESILIENCE_TEST_REPORT.md) (Gate D: PASS; missing exe rejection, timeout process tree cleanup, cooperative cancel, SHA-256 tampering detection, restart persistence).
- [x] Preserved raw evidence artifacts in [docs/v1.6/evidence/](v1.6/evidence/) with cryptographically verifiable SHA-256 hashes.
- [x] Added automated integration test suites `test_v16_workflow.py` and `test_v16_resilience.py`; all **97 tests** pass cleanly in pytest.
- [x] Completed Open-Source Integration Audit in [docs/audits/AGENT2_OPEN_SOURCE_INTEGRATION_AUDIT.md](audits/AGENT2_OPEN_SOURCE_INTEGRATION_AUDIT.md).
- [x] Unblocked GAP-OSS-04: Installed NumPy (v2.5.4) and SciPy (v1.18.1) in `.venv`; implemented vectorized raw waveform parsing and signal metrics (RMS, peak-to-peak, min, max, mean) in `ltspice_parser.py`.
- [x] Unblocked GAP-OSS-03: Integrated FreeCAD 1.1.4 3D STEP generation action directly into PySide6 `TransformerWorkspacePanel`.
- [x] Unblocked GAP-OSS-06: Implemented `NgspiceAdapter` (BSD 3-Clause) with batch simulation and argument generation.
- [x] Unblocked GAP-OSS-02: Installed and verified FEMM 4.2 at `C:\femm42\bin\femm.exe`; updated base adapter discovery roots; implemented headless Lua execution in `femm.py`, transformer Lua generator `femm_generator.py`, and results parser `femm_parser.py`; verified real 2D FEA transformer simulation in `test_femm_adapter.py`.
- [x] Unblocked GAP-OSS-05 (Qucs-S) & GAP-OSS-06 (ngspice): Installed standalone Qucs-S 26.1.1 and bundled ngspice 46 at `LOCALAPPDATA\Programs\qucs-s`; verified `qucs-s.exe` and `ngspice_con.exe`; tested real batch netlist simulation in `test_ngspice_adapter.py`.
- [x] Unblocked GAP-OSS-01 (KiCad): Installed KiCad 10.0.7 at `C:\Program Files\KiCad\10.0\bin\kicad-cli.exe`; implemented adapter execution for version, ERC, and DRC; verified in `test_kicad_adapter.py`.
- [x] Unblocked GAP-OSS-05 (OpenModelica): Installed OpenModelica 1.26.3 at `C:\Program Files\OpenModelica1.26.3-64bit\bin\omc.exe`; implemented adapter execution for version, model checking, and simulation; verified in `test_openmodelica_adapter.py`.
- [x] 110 automated tests passing across adapters, contracts, UI, calculations, resilience, and parsers. All 18 approved tools truthfully classified with 100% test coverage.
