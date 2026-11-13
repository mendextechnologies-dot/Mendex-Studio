# Security and reliability — lifecycle milestone

Phase 2 adds strict engineering-record contracts, optimistic metadata/specification
guards, atomic core-operation/receipt composition, unique artifact/evidence/export
directories, digest checks, bounded file reads and rejection of foreign-session
cancellation. Missing report fields no longer receive invented example values or
fabrication-authority wording. Existing evidence/reports remain unchanged. See
`17_SHARED_AGENT_OPERATIONS.md` for implemented scope and remaining limits. The Phase 1
assessment below remains applicable.

Implemented and tested locally:

- Strict extra-field rejection and bounded definition/stage/criterion/text/key sizes;
  registered criterion types only, validated DAG, no executable configuration.
- Existing draft revision required for mutation; append-only lifecycle tables, versioned
  immutable assignments and retry/conflict handling under SQLite write transactions.
- Existing same-revision numerical validation evidence required for attachment;
  central hash/specification checks reused on attachment and subsequent reads.
- Review requests remain unapproved. No agent approval endpoint, hardware control,
  manufacturing approval, automatic deployment or new shell/network surface.
- Pre-DDL online SQLite backup, integrity check, unchanged artifact hash manifest and
  tested rollback/restoration. No live data migration was run for development/tests.

Limits requiring explicit interpretation:

- Caller source/reviewer strings are untrusted attribution. A passing numerical rule
  is not independent verification of the value, threshold, reviewer or physical origin.
- Configurable policy is not authorization. A custom process can disable its review
  requirement but cannot obtain product/standards/manufacturing approval from this API.
- Direct filesystem/database access is not an OS security boundary. Hashes detect
  subsequent changes; they do not prevent modification or make file reads atomic.
- Read views perform fresh core reads and file checks, but do not lock external files.
  Mutation-time database checks run under BEGIN IMMEDIATE. No cross-process filesystem
  snapshot guarantee is claimed.
- Existing legacy review/delete/tool execution interfaces remain compatible. This
  milestone does not certify them or remediate every audit finding.
- Tauri permissions/CSP, frozen Python distribution, dependency vulnerability scans,
  desktop responsiveness and clean-machine/offline acceptance are not evaluated by
  these backend tests. They remain later work.
