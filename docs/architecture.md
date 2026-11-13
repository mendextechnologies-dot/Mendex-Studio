# Architecture v0.1

Local manual review update (13 November 2026): at the user's direction, desktop
engineering review uses a supplied reviewer name and required comments, without
profiles or passphrases. `StudioService.reviews.record_manual_decision` applies the
shared context/evidence/safety checks and records append-only MANUALLY_DECLARED
decisions with identity_authenticated=false. This is local attribution, not proof
of human identity or qualifications. Legacy credential APIs and history remain;
manual decisions are not advertised as MCP/CLI approval tools. No schema or live
review history was rewritten. See `docs/MANUAL_ENGINEERING_REVIEW.md`.

v3.1 Phase 2 (12 November 2026): `StudioService.engineering_records` adds a shared
agent registry for project metadata, requirement snapshots, existing-calculator run
history, artifact snapshots, validation evidence, job inspection/owned cancellation
and report metadata/export. New record/receipt tables are opt-in, backed up and
append-only in the existing database. `StudioService.atomic()` provides task-local
transaction composition so existing core writes and retry receipts commit together.
Missing report data is displayed as unavailable, not substituted with examples.
See `docs/v3.1/17_SHARED_AGENT_OPERATIONS.md` for actual coverage and capability limits.

v3.1 incremental implementation (12 November 2026): the optional
`StudioService.engineering_lifecycle` service adds validated configurable definitions,
explicit draft-revision enrollment, append-only stage attempts/evidence links and
integrity-aware effective views. CLI and MCP share its operation registry. New tables
are installed only on explicit registration/enrollment after an online SQLite backup;
global user_version remains 4 for existing compatibility, with component schema 1.
Legacy lifecycle assessments, Qt UI and evidence remain unchanged. Authorized review,
automatic desktop synchronization and Tauri/React are not implemented at this milestone.
See `docs/v3.1/06_ENGINEERING_LIFECYCLE.md` and `10_ENGINEERING_DATA_MODEL.md`.

Current integration scope (11 November 2026): commercial license-gated PLECS,
MATLAB/Simulink, Ansys Maxwell, Ansys Icepak and SolidWorks integrations are retired.
Their adapters, registry entries and desktop inventory/filter controls are removed.
The shared catalog contains 13 retained tools/research resources; the dashboard also
includes the existing optional ngspice adapter (14 rows). Existing settings, jobs,
reports and evidence are preserved for historical traceability. Retired tool IDs
cannot be configured or executed through the current service. Reintroduction needs
an explicit implementation change; old saved settings do not reactivate a connector.

The final foundation addendum in the supplied master guide governs scope. The filename says v1.3 but internal document control ends at v1.2. Earlier enterprise scope and embedded agent task briefs are reference material; the user assigns the entire application to this implementation.

`mendex_core` owns typed contracts, SQLite persistence, migrations and application services. `mendex_ui` consumes those services in-process. CLI commands use the same services. No UI business rules or second database.

SQLite metadata lives in `.mendex/studio.sqlite3` beneath the selected data root. Products use UUID directories and revision UUID subdirectories, keeping user labels out of filesystem paths. Native CAD remains filesystem content. Specifications are typed, schema-versioned SI fields with provenance. Draft revisions are editable; creating a new revision archives the old draft as an immutable baseline. Approval and manufacturing release are unavailable.

Day 1 migration uses SQLite user_version=1. Day 2 migrates v1 to v2 transactionally, preserving existing products and adding executable configuration, append-only validation records (database update/delete triggers) and report indexes. A newer database version is rejected. Schema changes require a tested incremental migration. Product creation and initial workspace setup roll back on failure. Duplicate codes and revision labels are rejected. Each service call owns a short database connection.

Module shells expose implementation status separately from evaluation status. The adapter registry exposes discovery capabilities, immutable-by-API evidence directories and draft HTML/JSON reports. External solver execution is disabled until independently verified. No signing identity or deployment is configured.

Manual check values, criteria and identities are supplied by the user. A numerical rule match plus an evidence file permits a historical PASS record; this is not engineering authorization. Effective status is computed centrally: missing/modified evidence or a different specification hash yields NOT_EVALUATED. Reports preserve frozen input snapshots and show all warnings; append-only records are never rewritten when inputs change. Direct filesystem/database access is not an OS security boundary; SHA-256 detects file changes on subsequent validation/report generation.

Day 3 adds shared launch and diagnostics services, used by both desktop and CLI. Windows code.cmd discovery resolves to Code.exe and launches a fixed argument list without a shell. Native document opening uses validated revision-relative paths and an extension allowlist; scripts/executables are excluded. Report opening is centralized in the same service. Diagnostics check the SQLite schema/integrity, Python/Qt dependencies, editor/developer tools and native discovery. Tool unqualification keeps workstation status PARTIAL independently of core framework readiness.

Completion migration moves schema v2 to v3 and adds append-only simulation availability requests. Each request retains its specification snapshot and hash but remains NOT_SUPPORTED; no execution, results or raw artifacts are manufactured. Versioned JSON tool/rule configuration ships in the wheel. Data-only JSON plugins add discovery/rules atomically; no plugin code is imported or executed. The AI boundary is a typed read-only interface with an explicitly unavailable default provider. Product/specification saves share one transaction and draft/review metadata is separate from approval.

Source remote: https://github.com/mendextechnologies-dot/Mendex-Studio.git; branch main. v0.1.0 is a foundation software release against the final addendum's primary-machine installation, repeatable smoke test, green tests and documented-issues gate. Real editor, File Explorer and native-document windows have been observed on this workstation. Independent-engineer pilot qualification remains separate and unperformed; no engineering or manufacturing release is implied. Packaging is manual source/wheel creation, with no CI/CD or automated deployment.

PCB workspace implementation (11 November 2026): `StudioService.pcb` provides shared desktop/CLI file import, draft notes, native design opening, ERC/DRC snapshots and persisted check history. The desktop runs checks in a worker thread. Unique check directories under `.mendex/pcb-checks/` hold input copies, native reports/logs/version and checksum manifests, outside frozen product revisions. Re-reading compares context/specification and artifact hashes; stale/missing/damaged evidence remains NOT_EVALUATED. Empty CAD cannot clear a check, and malformed reports cannot imply zero violations. CLEAR is a configured-rule result, never product/HV/manufacturing approval. No new database schema is introduced. See docs/PCB_WORKSPACE.md for interfaces and limits.
