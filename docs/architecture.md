# Architecture v0.1

The final foundation addendum in the supplied master guide governs scope. The filename says v1.3 but internal document control ends at v1.2. Earlier enterprise scope and embedded agent task briefs are reference material; the user assigns the entire application to this implementation.

`mendex_core` owns typed contracts, SQLite persistence, migrations and application services. `mendex_ui` consumes those services in-process. CLI commands use the same services. No UI business rules or second database.

SQLite metadata lives in `.mendex/studio.sqlite3` beneath the selected data root. Products use UUID directories and revision UUID subdirectories, keeping user labels out of filesystem paths. Native CAD remains filesystem content. Specifications are typed, schema-versioned SI fields with provenance. Draft revisions are editable; creating a new revision archives the old draft as an immutable baseline. Approval and manufacturing release are unavailable.

Day 1 migration uses SQLite user_version=1. Day 2 migrates v1 to v2 transactionally, preserving existing products and adding executable configuration, append-only validation records (database update/delete triggers) and report indexes. A newer database version is rejected. Schema changes require a tested incremental migration. Product creation and initial workspace setup roll back on failure. Duplicate codes and revision labels are rejected. Each service call owns a short database connection.

Module shells expose implementation status separately from evaluation status. Day 2 implements a reviewed in-process adapter registry with discovery capabilities, immutable-by-API evidence directories and draft HTML/JSON reports. External solver execution is disabled until independently verified. No remote repository, signing identity or deployment is configured.

Manual check values, criteria and identities are supplied by the user. A numerical rule match plus an evidence file permits a historical PASS record; this is not engineering authorization. Effective status is computed centrally: missing/modified evidence or a different specification hash yields NOT_EVALUATED. Reports preserve frozen input snapshots and show all warnings; append-only records are never rewritten when inputs change. Direct filesystem/database access is not an OS security boundary; SHA-256 detects file changes on subsequent validation/report generation.

Day 3 adds shared launch and diagnostics services, used by both desktop and CLI. Windows code.cmd discovery resolves to Code.exe and launches a fixed argument list without a shell. Native document opening uses validated revision-relative paths and an extension allowlist; scripts/executables are excluded. Report opening is centralized in the same service. Diagnostics check the SQLite schema/integrity, Python/Qt dependencies, editor/developer tools and native discovery. Tool unqualification keeps workstation status PARTIAL independently of core framework readiness.

Source remote: https://github.com/mendextechnologies-dot/Mendex-Studio.git. Initial repository was empty; local foundation commits are integrated on main. No CI/CD or deployment automation is configured. Version 0.1.0.dev3 remains a development build pending interactive/second-engineer qualification.
