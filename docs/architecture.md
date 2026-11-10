# Architecture v0.1

The final foundation addendum in the supplied master guide governs scope. The filename says v1.3 but internal document control ends at v1.2. Earlier enterprise scope and embedded agent task briefs are reference material; the user assigns the entire application to this implementation.

`mendex_core` owns typed contracts, SQLite persistence, migrations and application services. `mendex_ui` consumes those services in-process. CLI commands use the same services. No UI business rules or second database.

SQLite metadata lives in `.mendex/studio.sqlite3` beneath the selected data root. Products use UUID directories and revision UUID subdirectories, keeping user labels out of filesystem paths. Native CAD remains filesystem content. Specifications are typed, schema-versioned SI fields with provenance. Draft revisions are editable; creating a new revision archives the old draft as an immutable baseline. Approval and manufacturing release are unavailable.

Day 1 migration uses SQLite user_version=1. A newer database version is rejected. Schema changes require a tested incremental migration. Product creation and initial workspace setup roll back on failure. Duplicate codes and revision labels are rejected. Each service call owns a short database connection.

Module shells expose implementation status separately from evaluation status. Day 2 adds tool adapters, append-only validation/evidence and reports. External solver execution is disabled until independently verified. No remote repository, signing identity or deployment is configured.
