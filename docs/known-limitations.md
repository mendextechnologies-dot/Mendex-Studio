# Known limitations

- v0.1 foundation: discovery, manual validation, draft HTML/JSON reports, real primary-workstation VS Code/native-file handoff, diagnostics, rules, plugin loading, AI interface and persisted simulation availability requests are implemented. A second machine/independent engineer remains unqualified.
- Module workspaces are explicitly NOT IMPLEMENTED; no numeric engineering outputs exist.
- Specification and manual-check editing use typed JSON; category-specific guided forms are future enhancements.
- No approvals, manufacturing release, users/permissions or cloud sharing.
- Previous revisions freeze specification metadata only; native CAD versioning remains pending. Validation evidence is copied and hashed, with original filename preserved in metadata. Approval cannot be granted by the service; draft/review stages are informational workflow states.
- Product metadata remains editable; deletion is intentionally unavailable to preserve revision history.
- Local desktop smoke tests cannot replace second-engineer clean-machine qualification.
- Tool discovery searches PATH and known Windows locations, with explicit executable-path configuration. A missing result can mean installation elsewhere. Available Windows file-version metadata is displayed; it is not runtime compatibility qualification. Licenses and benchmarks are not qualified. No native installers or solver processes run.
- Validation values, acceptance criteria, evidence classification and reviewer identity are manually declared. They are not authenticated or independently verified. Historical PASS records do not approve products or establish safety.
- HTML/JSON reports are drafts. PDF/Word generation, embedded plots and report signing are not implemented.
- Append-only storage is enforced through the service and SQLite validation triggers; a user with direct filesystem/database access can alter local data. Evidence changes are detected on recheck. Signed/tamper-proof storage is unavailable.
- JSON plugin manifests load discovery/rule definitions without executing Python or approving results. Arbitrary executable plugins are unavailable. Simulation requests persist as NOT_SUPPORTED; solver execution remains disabled. The AI provider is unavailable; only its read-only extension contract is implemented, as required by the foundation scope.
- Automated unit launch tests use mocks. A separate primary-workstation check actually opened VS Code, File Explorer and a native text document and observed their window titles. This does not qualify a CAD solver or an independent workstation.
- Source/wheel distributions are supported. A signed bundled desktop executable is optional future packaging; no signing identity is configured. Independent-engineer/clean-machine pilot qualification is not claimed by the foundation tag.

## Codex v1.5 review branch

- The full 18-entry inventory and Codex application workflow are present, but no unreviewed Agent 2 connector is imported or enabled automatically. The synthetic adapter is a software fixture, not an engineering solver.
- Queue cancellation/deadlines are cooperative. Native process isolation, executable allowlists, process-tree cancellation and actual installed-tool smoke tests belong to Agent 2 and remain unmerged. Cross-process cancellation and crash recovery are not claimed.
- Dataset registration stores metadata and optionally opaque local bytes/hashes; actual dataset schema parsing, licensing qualification and research model interpretation remain Agent 2 work. Every record stays NOT_REVIEWED.
- SQLite v4 is additive; back up matching database/files before upgrading. The original released app cannot open a v4 database. No shared dependency manifests or Agent 2-owned code were changed by Codex.
- This branch is provided for review/handoff, not a complete v1.5 release, owner sign-off, product-specific result or manufacturing approval.
