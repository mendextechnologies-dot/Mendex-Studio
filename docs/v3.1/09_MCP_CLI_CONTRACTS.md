# Shared lifecycle MCP/CLI contracts — initial coverage

Phase 2 adds 22 shared engineering-record operations, documented with request,
retry and capability limits in `17_SHARED_AGENT_OPERATIONS.md`. Their CLI entry point
is `mendex --root DATA_ROOT engineering OPERATION request.json`; canonical record/
calculator schemas are `contracts/v3.1/records.*.schema.json`. The lifecycle operations
below remain unchanged.

Implemented registry: `engineering_lifecycle/api.py`. It generates MCP input schemas
and dispatches both transports to `StudioService.engineering_lifecycle`; neither
transport implements criteria or state transitions. Existing MCP tools/CLI commands
retain their names and behavior. This milestone adds lifecycle coverage, not all
remaining operations in the audit gap matrix.

| MCP tool | CLI operation | Request |
|---|---|---|
| list_lifecycle_definitions | lifecycle definitions | Empty object |
| get_lifecycle_definition | lifecycle definition --id engineering --version 3.1.0 | DefinitionQuery |
| register_lifecycle_definition | lifecycle register request.json | RegisterDefinition |
| enroll_lifecycle | lifecycle enroll request.json | Enrollment |
| get_project_lifecycle | lifecycle show REVISION_UUID | LifecycleQuery |
| get_lifecycle_history | lifecycle history REVISION_UUID --stage STAGE --after 0 --limit 100 | HistoryQuery |
| apply_lifecycle_stage | lifecycle apply request.json | StageCommand |

Invocation prefix: `python -m mendex_core.cli --root DATA_ROOT`; run from an installed
environment or source checkout with the core on PYTHONPATH. CLI mutation files are
UTF-8 JSON (BOM accepted). Mutation requests have `schema_version: 3.1.0` (defaulted
when absent), revision_id, source, reason and idempotency_key. Enrollment additionally
selects definition_id/version (defaults engineering/3.1.0). StageCommand adds stage_id,
action, optional expected_sequence and, only for attach_evidence, evidence_record_id.

Supported actions: start, reopen, block, fail, request_review, complete,
not_applicable, attach_evidence. No approval action exists. Example start request:

```json
{
  "schema_version": "3.1.0",
  "revision_id": "REPLACE_WITH_EXISTING_DRAFT_REVISION_UUID",
  "stage_id": "project_initialization",
  "action": "start",
  "source": "Engineer through an external agent",
  "reason": "Establish recorded project context",
  "idempotency_key": "unique-key-for-this-operation"
}
```

Use an actual existing revision UUID; this template is not executable engineering
data. A source string is caller attribution, not an authenticated identity.

Same enrollment/stage request and idempotency key returns the originally committed
event, including sequence/event ID, even after later transitions. Reusing a key with
different normalized inputs returns CONFLICT. Keys are scoped to the immutable
assignment. `expected_sequence` optionally guards against stale client updates; a
retry of an already committed identical request is resolved before that guard.

History supports an exclusive after_sequence cursor and limit 1–500. Event responses
include schema version, project/revision/assignment/event IDs, timestamp, source,
reason, action, attempt, input hash and evidence links; stage events include recorded
state and a criteria snapshot. Read views re-evaluate integrity and dependencies.
History retains earlier states even when effective evaluation changes.

Unknown fields/actions and invalid UUID/version/schema values fail validation. CLI
returns exit 1 with structured JSON on stderr. New MCP lifecycle failures use existing
MCP `isError: true` with a JSON text object containing schema_version/error/message;
legacy tool error formatting is preserved. Public service error codes are reused:
INVALID_INPUT, NOT_FOUND, CONFLICT, IMMUTABLE, STORAGE_ERROR.

No subprocess is launched by lifecycle methods. Long-running simulation jobs and
their logs/cancellation remain the existing implementation and are not wrapped by
these new lifecycle operations yet. No automatic solver retries are introduced.
