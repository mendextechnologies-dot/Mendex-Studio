# Phase 2 — shared engineering record operations

Implemented 12 November 2026. Source: `mendex_core/engineering_records/`, exposed as
`StudioService.engineering_records`. Existing calculation, project, validation, report
and integration services remain authoritative. CLI/MCP use the same strict operation
registry, not separate transport business rules. Existing commands/tools remain valid.

## Scope and entry points

| Area | New operations |
|---|---|
| Project metadata | get_project_metadata, update_project_metadata |
| Requirements | record_requirements, list_requirements, get_requirement_coverage |
| Calculations | list_supported_calculations, record_calculation_run, list_calculation_runs |
| Record retrieval | get_engineering_record |
| Artifact registration | register_engineering_artifact, list_registered_artifacts |
| Validation | record_validation_evidence, get_validation_results |
| Simulation inspection | get_simulation_status, get_simulation_logs, get_simulation_results, get_simulation_artifact |
| Supported cancellation | cancel_simulation_job |
| Reports | generate_revision_report, get_report_metadata, list_revision_reports, export_report_package |

All 22 operation names are both MCP tools and choices for:

```text
python -m mendex_core.cli --root DATA_ROOT engineering OPERATION request.json
```

Omit the request file only for empty-input discovery, such as
`engineering list_supported_calculations`. Strict canonical request models live in
`engineering_records/models.py`; calculator inputs in `calculations.py`. Twenty new
`contracts/v3.1/records.*.schema.json` files can be regenerated/checked with
`scripts/export_engineering_record_contracts.py [--check]`. Phase 1 schemas are unchanged.

## Context, concurrency and retries

New writes require schema version 3.1.0 (defaulted), source, reason and idempotency_key.
Stage-associated writes additionally require an existing draft revision, enrolled
stage, current IN_PROGRESS attempt and matching expected_input_hash. They do not
complete a stage or grant review/approval. Retrieve the hash through existing project
specification or lifecycle read operations; reopen an attempt after changing inputs.

Metadata edits use existing project IDs and optimistic expected_updated_at, obtained
from get_project_metadata. Names, owners and descriptions are updated through the
existing core method; project codes/IDs and frozen revision specifications are not
changed. Metadata attribution is separate from engineering approval.

Receipts are scoped by project/revision/job/report and key. The same parsed request
returns its original committed response. A changed request/operation with the same
key conflicts. Reads re-evaluate current integrity/staleness; a frozen retry receipt
is not a promise that an external file has remained unchanged or still exists.

`StudioService.atomic()` composes existing service calls and the receipt in one SQLite
transaction, using a task-local connection context. This avoids a core write committing
without its retry receipt. Failed outer transactions remove only unique directories
created by that failed operation, never original artifacts/evidence. Tests inject a
receipt failure to prove metadata/validation rollback and original-file preservation.
Controller construction can reuse an existing StudioService and its design service;
CLI no longer creates a second service graph for its legacy controller operations.

## Requirements and calculations

Requirements are immutable versioned snapshots with IDs, discipline, sourced text,
explicit criterion descriptions, optional existing specification-field references,
optional numeric target/unit, mandatory flag and assumptions. Referencing specification
fields avoids requiring duplicate numerical entry. Missing-input coverage checks the
latest snapshot, missing criteria/fields, differing explicit targets, unit mismatch
and specification staleness. It never claims requirement completeness, validated
standards coverage or engineering approval merely because that list is empty.

Four existing calculators are exposed with strict discoverable input schemas: Dowell,
semiconductor losses, Steinmetz and flyback. The record service calls the existing
controller/functions and stores exact validated inputs, returned outputs, assumptions,
formula reference, implementation-file SHA-256, Python version and warnings. It does
not implement alternative formulas. SUCCEEDED is numerical execution, not validation.
Arithmetic/model failures after valid input acceptance are recorded FAILED with no
invented result. Invalid/unknown inputs are rejected before execution.

The new path rejects fractional layer counts, booleans as numbers, nonfinite inputs
and porosity outside the implementation's unclamped range; it never silently truncates
or clamps them. Flyback diode drop must be explicitly supplied on this path. Legacy
calculation defaults remain compatible on old paths, while the new record warns about
the underlying model's existing ripple-factor constant/turn rounding. Existing mm/mm2/
degrees-C and output-labelled unit conventions are retained explicitly; coefficients
and device/material applicability are caller supplied, not manufacturer verification.

## Artifacts and validation evidence

Artifact registration accepts an existing revision-relative file, explicit expected
digest and classification. Paths are confined through the core relative-path validator
and resolved-root checks. Optional design/design-revision IDs must belong to the project
and identify an existing design revision. A unique non-overwriting copy is stored
outside frozen revisions under `.mendex/engineering-records/artifacts/UUID/`.

Both original and snapshot hashes are checked on later reads. Missing/changed source
files or snapshots are visible separately; effective status becomes NOT_EVALUATED.
Registering a script as an artifact never runs it. General imports from arbitrary
external directories and native authoring workflows are not added by this operation.

Validation recording wraps existing ManualCheck/record_validation behavior. The caller
supplies numerical value/bounds/units, evidence kind and reviewer attribution. Evidence
files use the existing 50 MiB bound and need an explicit expected digest, verified
before and after the core copy. The original ValidationRecord ID is returned inside
the attributed stage record and can be attached through the Phase 1 lifecycle operation.
Reads reuse validation_summary, including stale/damaged => NOT_EVALUATED. No reviewer
authentication, laboratory-origin verification or agent self-approval is introduced.

## Job inspection and cancellation

Status/results use existing persisted JobRecord/JobResult and manifest integrity.
Logs use existing bounded log access; manifest-declared text artifacts can be previewed
through the existing safe preview API. Unsupported binary previews remain explicit;
no waveform interpolation, invented samples or new solver parser is added. Controller
jobs without a verified manifest can have an execution status but unverified/unavailable
evidence/log previews. This interface does not equate execution success, extracted
results, engineering validation and review.

New IntegrationService submissions record the actual worker PID. A new observer session
therefore does not mark a live worker interrupted solely because its local future map
is empty. Existing interruption recovery remains in place for dead/unknown owners.

Cancellation is exposed only through `cancel_owned`: a current service session must
own a live cooperative cancellation event. Foreign-session jobs return UNSUPPORTED
without relabelling them CANCELLED. Terminal jobs are returned unchanged. A receipt
acknowledges a cooperative request, not confirmed termination; inspect later status
for acknowledgement. A one-shot CLI cannot cancel work owned by a separate MCP/native
runner session. Existing synchronous controller runners do not gain a new cancellation
capability. The new record API adds no native process-termination or simulation-replay
behavior; it delegates the existing supported cooperative cancellation.

## Reports and export

Generation uses the existing core generator with idempotency/stage attribution and
stored hashes of report.html/snapshot.json. Missing-input report fallbacks were fixed:
no example voltages, frequency, isolation rating, turns, losses, prices, vendor or
qualification is substituted. Workspace sizing/BOM sections display actual bounded,
confined source content with provenance caveats. Legacy readiness no longer claims
fabrication authorization. Already generated reports/baselines were not rewritten.

Metadata checks availability, specification staleness, snapshot identity and known
file hashes. Reports generated through this new path can be INTACT/FAILED; older reports
without original hashes are explicitly UNVERIFIED_LEGACY, never retroactively trusted.
Exports create unique ZIPs under `.mendex/engineering-records/exports/UUID/` containing
the original report bytes, frozen snapshot and a current manifest/digests. They do not
modify original reports or raw evidence, or claim to be complete manufacturing/release
packages. Missing or known modified reports cannot be exported as intact evidence.

## Storage and remaining work

Three opt-in tables in the same SQLite database: engineering_records_schema (component
version 1), engineering_records_entries and engineering_records_receipts. Entries and
receipts are append-only, with UPDATE/DELETE triggers and unique scoped keys. Entries
reference existing revisions and store canonical payload digests. First mutation
backs up SQLite and manifests existing artifact hashes before transactional additive
DDL; global user_version and lifecycle component version remain unchanged. Discovery/
ordinary startup do not install the record tables. No live database migration was
performed in this development turn; tests use disposable data roots.

This completes the six Phase 2 priority areas agreed in conversation. Broader master
scope still includes measurement-agent ingestion, richer discipline-specific coverage,
asynchronous orchestration and compatible numerical simulation comparisons where
supported. Generic prompt library, automatic Studio synchronization and Tauri/React
remain subsequent phases. Qt remains available; no UI workflows have been retired.

## Verification

Full confirmation: 318 passed, 1 skipped in 83.45 seconds, with explicit pytest return
0 and process exit 0. The initial full run had the same assertion totals but returned
nonzero after its summary; both XML reports are retained. After the final rollback
cleanup guard, all 26 new record/interface tests passed again in 9.07 seconds. The
missing excited FEMM reference remains NOT_EVALUATED. See document 15 for commands,
evidence paths and the distinction between these software tests and final desktop/
physical engineering acceptance. No production or manufacturing readiness is implied.
