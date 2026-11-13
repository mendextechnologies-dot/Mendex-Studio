# Prototype and Physical Testing

Lifecycle stage: `prototype_testing`. Generic instructions; no product-specific requirements.

## Purpose

Track actual physical testing evidence without controlling hardware or manufacturing approval.

## Required inputs

Explicit prototype revision, human-authorized test plan, actual readings, instrument/serial/calibration/operator/procedure details.

## Questions for the engineer

Who performed the test? Which instrument/calibration and procedure apply? Are the raw measured files available? Is the stage genuinely not applicable?

## Supported engineering tools

Existing evidence ingestion and measurement records where exposed; human-operated laboratory equipment only.

## MCP/CLI operations

`mcp:get_project_specifications`, `mcp:record_validation_evidence`, `mcp:get_validation_results`, `mcp:register_engineering_artifact`, `mcp:apply_lifecycle_stage`. Use the actual discovered schema; corresponding structured operations use `mendex engineering OPERATION request.json`, lifecycle actions use `mendex lifecycle apply request.json`, and legacy operations use their existing CLI groups.

## Expected artifacts

Real test plan, measured source files, deviations and review findings.

## Structured records to persist

Persist actual MEASURED validation evidence with supplied bounds/units and instrument/operator/procedure provenance in notes; never describe an assertion as authenticated.

## Validation rules

Never infer laboratory values from simulation. No hardware control, HV test initiation or manufacturing authorization is permitted.

## Evidence requirements

Actual supplied laboratory files and traceable human attribution/calibration; preserve raw bytes.

## Completion criteria

The default physical stage is optional but review-gated even for exemption. Use prototype_testing_acceptance only with real evidence; without authorization/evidence leave blocked or awaiting review.

## Human review requirements

Separate qualified human authorization and review are required; the agent cannot approve its own work.

## Error handling

Missing physical evidence stays NOT_EVALUATED. Do not mark NOT_APPLICABLE merely to make a demonstration finish.

## Next-stage recommendations

Record corrective actions or proceed to documentation with every physical limitation clearly visible.

