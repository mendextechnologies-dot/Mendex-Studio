# v3.1 architecture gap analysis

Status: audit/proposal, 12 November 2026. Existing behavior was inspected; proposed
interfaces and records below are not implemented features.

## Responsibility gaps

| Target | Current state | Required change |
|---|---|---|
| Agent-led engineering | Working CLI/MCP facade, but manual Qt workflows remain | Put supported orchestration behind shared core APIs and expose both agent interfaces |
| One configurable lifecycle | Hardcoded 12/15-stage assessments plus separate graph execution | Versioned data-only nine-stage definition and append-only stage executions; retain legacy assessments as historical projections |
| Traceable stage completion | File/record heuristics and reviewer name/pass flag | Explicit criteria assessments and integrity-checked evidence tied to specification/revision; review requests distinct from approval |
| Durable calculation history | Pure calculation responses and ad hoc files/design values | Add attributed calculation-run storage around existing functions, preserving inputs, assumptions, formula/service version and warnings |
| Automatic external updates | Qt refresh flows; JSON design cache loaded at initialization | Backend fresh reads/reload policy plus controlled UI polling, focus refresh, reconnect/backoff; no direct frontend SQLite |
| Lightweight Studio | Authoring, execution, reviews, editors and monitor screens intermixed | New frontend exposes viewing, searching, comparing, safe opens/exports/preferences; no design/specification/execution forms |
| Desktop runtime | Qt only; copy/setup script assumes Python | Add Tauri-managed Python transport, package proof and clean-machine acceptance before any legacy retirement |

## MCP/CLI operation coverage

Present means source entry points exist, not that native engineering capability has
been qualified. New MCP/CLI methods must validate strict versioned inputs, delegate
to the same service and return stable structured errors.

| Required operation family | Existing reuse | Missing or incomplete |
|---|---|---|
| Create/list/get project | MCP/controller and CLI project groups | Metadata update via MCP/CLI; lifecycle initialization/retrieval and retry idempotency |
| Specification revision/get/validate | Existing revision/create/save and validation methods | Complete typed agent coverage, structured non-electrical requirements, explicit missing-input/coverage API; never equate valid schema with complete engineering requirements |
| Lifecycle definitions/stages/start/status/history | Legacy assessment methods | Versioned definition retrieval/registration/selection, stage executions/transitions, blockers, evidence links, criteria evaluation, review request/history |
| Complete stage | No generic completion gate | Backend evaluates explicit criteria/evidence/current revision/dependencies/review policy; agents cannot supply completion as proof |
| Calculations | MCP `run_engineering_calculations`, CLI four calculation types | Discover supported inputs/units/limits, persist/retrieve runs/assumptions/warnings/stage associations; generic wrappers for newer supported functions |
| Designs | Generate/read/candidates; core revision and artifact services | Capability discovery, imported file registration, explicit design revision API/metadata, stage links and safe conflict handling for external changes |
| Simulation tools/config/start | Controller tools and synchronous run; separate IntegrationService submit | Strict configuration validation, coherent asynchronous adapter ownership and job IDs, no replay after timeout/crash |
| Simulation status/logs/results/cancel | Core job/list/logs/cancel functions, partial facade list | MCP/CLI detail/log/result/evidence/capability endpoints; accurate cancellation only for supported job ownership; reject unsupported cancellation |
| Simulation comparison | Existing output models | Compatible domain/units/revision comparison and exact provenance; do not interpolate automatically |
| Validation/rules/evidence | Core manual checks, rule registry, PCB checks and summaries; CLI exposes more than MCP | Strict attributed attach/record/read methods, effective integrity/stale status and explicit missing checks; no client-provided PASS bypass |
| Review request/status | Existing unauthenticated stage approval and ECR functions | Agent-safe request-only operation and recorded status; authorized human decisions remain unavailable until backend authorization is established |
| Prototype/laboratory records | MeasurementService | Expose supported measured records and real attachments with calibration/operator/procedure; no hardware execution or invented readings |
| Reports | Core generate/list/open; job export; controller generation | Consistent agent listing/metadata/export package, stage/revision evidence manifest and warnings |
| Safe artifact opening | Core path checks and launch helpers | Register/read missing/tampered status and versioned artifact associations; consolidate UI paths behind core |

Existing deletion commands remain compatibility operations. The new master prompt
does not authorize invoking them on existing projects or including deletion in generic
agent prompts. No manufacturing approval/release operation will be added.

## Proposed minimal data additions

Reuse `products` as project identity, `revisions` as specification context,
`integration_jobs` as execution records, `validations`, `measurements`, `reports` and
existing design JSON as authoritative records. Do not duplicate them in new tables.

Candidate additions to the same SQLite database, to validate during phase 1 design:

| Record | Minimal purpose |
|---|---|
| Lifecycle definition versions | Immutable validated JSON definition and digest, schema version, lifecycle identifier/version |
| Project/revision lifecycle assignment | Existing project and revision IDs, selected definition version/digest; no automatic migration of historical PASS states |
| Stage execution/events | Append-only transitions, iteration/attempt identifier, source, input/specification hash, timestamps, blockers, acceptance outcomes, review requests and references to existing records |
| Registered artifacts/evidence links | Existing artifact/validation/job/report/measurement references or confined relative file/hash metadata; explicit project/revision/stage context |
| Calculation runs | Existing calculator identifier/version, exact inputs/results, units/assumptions/provenance/warnings, stage/revision context and status |
| Retry receipts | Scoped idempotency key, request digest and committed result reference for new retryable mutations; differing payload on reused key is CONFLICT |

Do not add a second authoritative approval table merely to replicate legacy flags.
Review requests can be stage events. Additional requirement text/acceptance criteria
should use typed versioned records associated with the existing revision, without
rewriting its frozen specification schema or previous evidence. Final table/index
names and transaction boundaries belong in implementation contracts and migration
tests; this document is not a schema migration.

## Migration safeguards

1. Produce a consistent SQLite online backup and a manifest of authoritative JSON,
   native artifacts and evidence before any schema change; test restoration on copies.
   A raw copy of an open database may miss WAL contents. Do not mutate frozen content.
2. Test fresh schema, current version 4 with existing v5-style columns, older supported
   schemas and future-version rejection. Coordinate constructor version checks with
   the migration; do not blindly set user_version to 5.
3. Add only necessary tables/indexes, constraints and append-only triggers in a tested
   transactional migration. Failed migration must leave the original usable.
4. Existing projects remain existing projects. Explicitly enroll a revision in the new
   lifecycle; legacy assessment/approval records remain historical and are not promoted.
5. Evidence copy/registration stages bytes under unique internal names, verifies
   digest/context and commits metadata atomically as far as practical. Clean up only
   newly staged unreferenced bytes on failure; never overwrite original evidence.
6. Run compatibility checks against isolated restored copies and unchanged CLI/MCP
   callers. Downgrades use a verified backup; do not promise lossless reverse migration
   once new history exists.

## Critical semantic/security gaps

- Lifecycle state (COMPLETED) and engineering evaluation (NOT_EVALUATED/PASS/FAIL)
  are distinct. Configuration may define evidence-backed process completion; it must
  never grant product, safety, standards or manufacturing approval.
- A filename, file existence, zero exit code, model confidence or caller claim cannot
  satisfy a completion criterion alone. Changed/missing evidence or specification
  invalidates the effective evaluation while preserving historical events.
- Existing reviewer names are assertions, not authentication. Do not add an agent
  approval tool or a desktop approval button that bypasses this missing boundary.
- Configuration permits strict JSON data and registered criterion types only; no
  scripts, Python imports, shell, eval, SQL or arbitrary executable paths. Dependencies
  are validated; iteration is recorded as new attempts, not dependency cycles.
- Integration cancellation from a different process currently has separate semantics;
  test ownership before exposing it as solver termination. Desktop must not cancel
  independent CLI/MCP work during its own shutdown.
- Long-lived JSON design caches and direct write_text persistence need explicit refresh
  and atomic/conflict-safe writes. Polling a stale cache will not satisfy synchronization.
- Fixed status/readiness text and unsupported metrics must be replaced with actual
  backend records or explicit unavailability. Library seed records require provenance.
