# Application service contract v0.1

Desktop review update (13 November 2026): `submit_review` now takes reviewer_name,
required comments and the displayed expected_document_hashes / expected_evidence_hashes,
along with existing revision/stage/attempt/digest/decision fields. It calls the shared
core's local manual-decision path. Result metadata explicitly states MANUALLY_DECLARED,
identity_authenticated=false and CONTENT_DIGEST_NOT_IDENTITY_PROOF. Credential-based
MCP/CLI review contracts are retained; manual payloads are rejected by their strict
schema. Existing historical records are unchanged. See `docs/MANUAL_ENGINEERING_REVIEW.md`.

Phase 2 engineering-record contracts are additive `contracts/v3.1/records.*.schema.json`.
`StudioService.engineering_records` delegates to existing domain implementations;
CLI/MCP share `engineering_records/api.py`. See `docs/v3.1/17_SHARED_AGENT_OPERATIONS.md`
for strict request/retry/context rules and truthful cancellation/report-integrity limits.

Additive v3.1 lifecycle contracts are in `contracts/v3.1/`. The shared domain object is
`StudioService.engineering_lifecycle`; CLI and MCP use one strict operation registry.
Enrollment/definition registration explicitly installs the backed-up component schema;
ordinary startup does not enroll revisions. Review requests are not approvals.
See `docs/v3.1/09_MCP_CLI_CONTRACTS.md` for the implemented lifecycle subset.

Integration scope update (11 November 2026): PLECS, MATLAB/Simulink, Ansys Maxwell,
Ansys Icepak and SolidWorks are no longer registered. Shared catalog/discovery APIs
exclude these five tools; configuring/verifying a retired ID returns NOT_FOUND.
Historical persisted records are retained, with no destructive database migration.

Canonical Pydantic models: `src/mendex_core/models.py`, `src/mendex_core/evidence.py` and `src/mendex_core/adapters/registry.py`. Generated JSON schemas and an illustrative payload live here. UI and CLI use `StudioService(root)`.

Day 1 operations: create_product(code, name, category, owner, description), list_products(), get_product(id), get_revision(id), list_revisions(product_id), update_specification(revision_id, Specification), create_revision(product_id, label), create_workspace(revision_id), update_product(id, name, owner, description).

Day 2 operations: configure_tool(tool_id, path=None), list_tools(), check_tool(tool_id), list_runs(revision_id), record_validation(revision_id, ManualCheck, evidence_path=None), list_validation(revision_id), validation_summary(revision_id), validation_integrity(record), generate_report(revision_id), list_reports(revision_id).

Validation records are append-only. PASS/FAIL requires an evidence file and an evaluated inclusive numerical min/max rule. The reviewer supplies the value, criterion, evidence type and identity; Mendex does not authenticate them or authorize the threshold. Evidence is copied with SHA-256 and a frozen specification. `validation_summary` returns effective_status, stale and evidence_integrity separately from the original record; both desktop and CLI use this operation. Stale or damaged evidence is NOT_EVALUATED. Records are historical; no overall product approval is inferred. New revisions do not inherit validation.

Tools expose discovery only; detected executables remain FOUND_UNVERIFIED. Windows file-version metadata is read without starting the tool; absent version metadata remains unknown and runtime compatibility remains unqualified. Full adapter protocol and capabilities are defined in adapters/contracts.py, including validation, preparation, run, parse and self-test boundaries. Unimplemented execution/preparation raises NotImplementedError and parsers return no metrics.

The JSON-only plugin loader reads `<data-root>/.mendex/plugins/*.json`. PluginManifest and AdapterDefinition reject unknown fields, traversal and duplicate IDs; incompatible manifests are rejected atomically and reported to the UI. Plugins can extend discovery and engineering rules without editing the service, but cannot execute Python or grant approval. Packaged default rules carry versioned evidence requirements and report missing inputs/physical verification; they do not invent numerical acceptance thresholds.

SimulationRun is now persisted by request_simulation(revision_id, tool_id). These availability requests snapshot the specification/hash and available tool version, remain NOT_SUPPORTED and never claim a solver started or produced artifacts. list_runs returns the actual history. AIRequest, AIResponse and AIService are **retired** (2026-11-11): Mendex Core contains no AI provider or copilot. AI coding agents operate Mendex only through the CLI and MCP server. The AIRequest/AIResponse schema files are kept as historical records and are no longer generated. Reports include rule assessments, plugin inventory and simulation request history and remain draft HTML + frozen JSON, never RELEASED.

Day 3 operations: open_in_vscode(revision_id), open_project_file(revision_id, relative_path="."), open_report(report_id), diagnostics(), export_diagnostics(). Launching validates paths and uses a shell-free VS Code executable or Windows document associations. No model scripts or executable project files are launched. Doctor reads runtime/package/SQLite state and tool discovery without running solvers. framework_ready and workstation status are separate; exit 0 means core framework usable, not qualified engineering tools. Diagnostic exports contain environment paths but no product specifications or credentials.

Completion operations: save_product_revision(...) atomically saves metadata and specifications; rename_revision(revision_id,label), set_revision_status(revision_id,status), export_specification(revision_id), open_evidence(record_id), request_simulation(revision_id,tool_id), list_rules(revision_id=None), list_plugins(), ai_advice(revision_id,question). Draft/review transitions are supported; approved is a reserved model state and cannot be granted by the service. New revisions archive previous baselines. Evidence opening rechecks hashes and file types; copied files use compact internal filenames while preserving their original filename in metadata.

Errors: `StudioError.code` is INVALID_INPUT, NOT_FOUND, CONFLICT, IMMUTABLE, STORAGE_ERROR or LAUNCH_ERROR. Pydantic rejects unknown fields and non-finite quantities. Registry misuse raises ValueError and disabled adapter execution raises NotImplementedError. CLI emits JSON errors to stderr and returns a nonzero exit code.

PCB workspace contract (11 November 2026): `StudioService.pcb.overview(revision_id)`, `import_file(revision_id, source)`, `open_file(revision_id, relative_path)`, `review_notes(revision_id)`, `save_review_notes(revision_id, notes)`, `run_check(revision_id, relative_path, operation)`, `list_checks(revision_id)`, `read_check(revision_id, run_id)` and `open_check_evidence(revision_id, run_id)` are shared by presentation clients. Import/open-for-editing/notes require draft revisions; imports never overwrite. Checks accept only erc/schematic or drc/board pairs inside that revision's pcb directory, execute against copies, and preserve unique hash-covered artifacts outside the revision. Native report status and effective status are separate: current status may be CLEAR/ISSUES_FOUND/ERROR/NOT_EVALUATED; stale or integrity-failed reads are effectively NOT_EVALUATED. Product evaluation is always NOT_EVALUATED by this module. Notes/checks do not write lifecycle approvals or numerical validation PASS records. See docs/PCB_WORKSPACE.md.


Component reference contract update (13 November 2026): desktop `components` returns the shared core catalog with `categories`, `components`, `materials`, `cores` and `provenance_note`. Canonical Pydantic fields are used directly by the typed React client. Missing ratings, core dimensions, loss coefficients and model associations are nullable. Records carry source/conditions and qualification NOT_EVALUATED; FAMILY references require an exact variant. Source dates and lifecycle labels do not qualify a component. No project/schema migration. See docs/COMPONENT_LIBRARY.md.
