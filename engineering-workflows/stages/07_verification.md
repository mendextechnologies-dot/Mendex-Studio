# Engineering Verification

Lifecycle stage: `verification`. Generic instructions; no product-specific requirements.

## Purpose

Evaluate recorded outputs against explicit requirements without approving AI-generated work.

## Required inputs

Current requirements, calculations, native evidence, acceptance criteria and known open issues.

## Questions for the engineer

Which requirements have valid evidence? Are any checks stale, missing, failed or physical-only? Who must review them?

## Supported engineering tools

Existing core numerical validation and integrity-aware summaries; supported native checks through existing services.

## MCP/CLI operations

`mcp:get_requirement_coverage`, `mcp:get_validation_results`, `mcp:record_validation_evidence`, `mcp:get_engineering_record`, `mcp:get_simulation_results`, `mcp:get_project_lifecycle`, `mcp:apply_lifecycle_stage`. Use the actual discovered schema; corresponding structured operations use `mendex engineering OPERATION request.json`, lifecycle actions use `mendex lifecycle apply request.json`, and legacy operations use their existing CLI groups.

## Expected artifacts

Verification report, requirement/evidence coverage, failures, unresolved issues and review request.

## Structured records to persist

Record exact validation check IDs, values, units, supplied bounds, evidence kind/source and reviewer attribution; link the ValidationRecord ID through attach_evidence.

## Validation rules

Use effective status, not historical PASS. Keep calculated, simulated and measured evidence distinct. Do not claim regulatory compliance from simulation or DRC.

## Evidence requirements

Intact actual files and matching specification snapshots; document any unverified identities/thresholds.

## Completion criteria

verification_acceptance and human-review gate remain required. No approve action exists; an empty issue list is not authorization.

## Human review requirements

Request human review. If authorization is unavailable, leave AWAITING_REVIEW/BLOCKED and explain the actual gate.

## Error handling

Stale/damaged evidence remains NOT_EVALUATED; reopen/re-run only through supported core operations on a draft revision.

## Next-stage recommendations

Recommend physical testing only with a real test plan and separate human authorization, or further corrective iterations.

