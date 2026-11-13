# Final Engineering Documentation

Lifecycle stage: `documentation`. Generic instructions; no product-specific requirements.

## Purpose

Compile engineering records and evidence without claiming release or manufacturing readiness.

## Required inputs

Project/revision, actual artifacts, validation/effective status, review requests and unresolved issues.

## Questions for the engineer

Which records and exclusions belong in the handover? Are any sources stale, legacy-unverified or unavailable?

## Supported engineering tools

Existing core report generator and immutable report-package export.

## MCP/CLI operations

`mcp:generate_revision_report`, `mcp:list_revision_reports`, `mcp:get_report_metadata`, `mcp:export_report_package`, `mcp:get_lifecycle_history`, `mcp:apply_lifecycle_stage`. Use the actual discovered schema; corresponding structured operations use `mendex engineering OPERATION request.json`, lifecycle actions use `mendex lifecycle apply request.json`, and legacy operations use their existing CLI groups.

## Expected artifacts

Draft engineering report, frozen snapshot, artifact/evidence manifest and revision history.

## Structured records to persist

Use a fresh idempotency key per intended generation/export; preserve original report IDs/hashes and warnings.

## Validation rules

Do not insert default engineering values. INTACT hashes attest file consistency, not design validity; legacy reports remain UNVERIFIED_LEGACY.

## Evidence requirements

Actual report/snapshot bytes and available referenced evidence with explicit exclusions.

## Completion criteria

documentation_acceptance and required review are gates. A ZIP or report existing is not approval or manufacturing release.

## Human review requirements

Request engineering handover review; authorized decisions remain unavailable where backend authentication is absent.

## Error handling

Reject modified/missing reports as intact exports; preserve prior records and report exclusions instead of deleting them.

## Next-stage recommendations

Present actual stage states, remaining blockers and next human actions; do not force all stages to COMPLETED.

