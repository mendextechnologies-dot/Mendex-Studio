# Lifecycle data model — opt-in component schema 1

Phase 2 extension: `engineering_records_schema` component version 1,
`engineering_records_entries` and `engineering_records_receipts` are now implemented
in the same database. They preserve attributed requirements, calculation runs,
artifact snapshots/associations, validation/report references and atomic retry receipts.
They have separate opt-in backed-up initialization and append-only triggers; the
lifecycle/global versions are unchanged. See `17_SHARED_AGENT_OPERATIONS.md`. The
original Phase 1 milestone description follows for historical context.

The lifecycle extension uses the **existing** `.mendex/studio.sqlite3`. It does not
replace products, revisions, validation records, native files, design JSON or evidence.
`StudioService` construction adds only the domain object; new schema creation occurs
on explicit definition registration or enrollment. Listing the packaged default and
ordinary legacy startup do not install this component or enroll old revisions.

| New table | Role |
|---|---|
| engineering_lifecycle_schema | Component version 1 and pre-migration backup path |
| engineering_lifecycle_definitions | Immutable definition ID/version, canonical digest, payload and attribution |
| engineering_lifecycle_assignments | Unique existing revision, selected definition, assignment UUID/timestamp |
| engineering_lifecycle_events | Append-only sequence/event IDs, assignment/stage, retry key/digest and event payload |

All four tables have UPDATE/DELETE rejection triggers. Foreign keys connect assignments
to existing revisions/definitions and events to assignments. A unique assignment/request
key serializes retry receipts; no separate duplicate project or evidence table is needed.
All mutations run under BEGIN IMMEDIATE. Definition/assignment/event changes in one
operation commit together. Failed stage checks append no success event. Missing or
future component schema is rejected rather than silently repaired or downgraded.

## Migration and recovery

Global SQLite user_version stays **4**, intentionally preserving the current guard
and pre-existing v5-style columns. This is an additive, separately versioned component
migration rather than an unsafe global bump. The old schema migrations are unchanged.

Before the first component DDL, SQLite's online backup API writes a unique directory
under `.mendex/backups/lifecycle-UUID/`, checks the copied database with quick_check,
and writes a manifest of the backup digest and existing authoritative artifact hashes.
The manifest scans products, workspaces, engineering_designs, reports and metadata
files (excluding database journals and backup directories). Directory links are not
traversed and escaping file/root paths are rejected. Originals are never modified.

Artifacts are hash-manifested, not copied: schema installation does not modify them.
The backup is therefore a database rollback safeguard, not a general full-project
disaster-recovery archive. External artifact edits during hashing are not an atomic
filesystem snapshot. Stop writers and take a separate full data-root backup when a
complete project backup is required. Incomplete/failed backup prevents DDL; a failed
migration rolls back DDL and leaves original metadata intact. A partial diagnostic
backup directory may remain after failure and is not automatically deleted.

Tests restore a backup into an isolated database and verify original revision payload
and integrity, inject DDL failure to verify rollback, and exercise immutable triggers
and concurrent retry behavior. No migration or restore was executed against live
engineering data in this implementation turn. Tests use temporary roots only.

Historical revisions remain readable; new mutations require draft status. Enrollment
does not copy stage completions to new revisions or promote old PASS flags. Changed
specifications/evidence invalidate effective results without editing history.

Generic artifact registry, durable calculation-run tables and structured additional
requirements remain later implementation phases; no empty tables for those were added.
