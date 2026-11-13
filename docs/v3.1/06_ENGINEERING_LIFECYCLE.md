# Configurable engineering lifecycle — first implementation milestone

Implemented 12 November 2026 in `src/mendex_core/engineering_lifecycle/`, exposed as
`StudioService.engineering_lifecycle`. The existing `service.lifecycle` 12/15-stage
assessments and visual workflow engine remain available and unchanged. They are not
used as completion evidence for new stages.

The packaged `mendex_core/config/engineering-lifecycle.json` defines nine generic
stages: initialization, requirements, feasibility, calculations, design development,
simulation, verification, prototype testing and documentation. Engineering-specific
stages require review by default. Prototype testing is optional but its exemption also
requires review. No product-specific input values or acceptance thresholds are supplied.

Enrollment is explicit for an existing draft revision. It reuses the existing product
ID and revision ID, creates one immutable assignment and an enrollment event, and leaves
all stages NOT_STARTED. No files, legacy assessments or historical approval flags
automatically complete a stage. No project/workspace duplicates are created.

## State and evaluation

The recorded states are NOT_STARTED, IN_PROGRESS, BLOCKED, AWAITING_REVIEW, COMPLETED,
FAILED and NOT_APPLICABLE. Start/reopen creates a new attempt and clears that attempt's
evidence links. Previous attempts remain in history. Independent branches can run in
parallel; dependencies gate completion rather than forcing every stage to run linearly.

Completion requires an explicit request, a started/unblocked attempt, current
specification context, successful registered criteria, completed/applicably exempt
dependencies and any required review. BLOCKED stages must start/reopen before completion.
Optional-stage exemption requires justification and is rejected for mandatory stages
or review-gated exemptions. All mutations require a draft revision.

The current implementation has no authenticated human-review mechanism. A review
request records AWAITING_REVIEW/REQUESTED, not an approval. Review-required completion
and exemptions remain blocked. There is no approve action, identity authentication,
manufacturing approval or automatic product release. Legacy caller-supplied reviewer
strings do not satisfy this new gate.

`get` returns recorded `status` separately from `effective_status`, criteria outcomes,
blockers and staleness. Changed specification or damaged/missing validation evidence
can make a historically COMPLETED stage effectively BLOCKED, including dependent
stages, without rewriting its event. `acceptance_status` describes these process
criteria, not product compliance. Top-level `engineering_status` remains NOT_EVALUATED
and `approval_status` UNAVAILABLE. No completion percentage is invented.

## Evidence and current scope

Attachment references existing `ValidationRecord.record_id` values from the same
revision. The core's `validation_summary` checks current specification hash and copied
evidence SHA-256. Stale, missing or modified evidence is rejected on attachment and
re-evaluated on subsequent reads. The most recently attached matching check controls
the criterion; older PASS records cannot mask a newer attached FAIL. CALCULATED,
SIMULATED, MEASURED and MANUAL kinds must match the definition.

Definitions can also express recorded project context and required specification
fields. Those process checks are not engineering validation. A file existing or a
solver returning zero is not a criterion type. The packaged engineering-stage checks
are conservative named numerical-validation placeholders with no invented thresholds;
discipline-specific requirement coverage, durable calculation records and solver/job
criteria remain later work. Do not call the default policy a complete discipline
acceptance specification. Register a new definition version for an explicit policy;
an enrolled definition cannot be silently changed.

General artifact registration, physical measurement ingestion via MCP, authorized
human decisions, desktop presentation/synchronization and full stage-operation
orchestration are not implemented by this first milestone.
