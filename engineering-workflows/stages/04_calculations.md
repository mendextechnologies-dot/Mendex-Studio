# Engineering Calculations

Lifecycle stage: `calculations`. Generic instructions; no product-specific requirements.

## Purpose

Execute existing deterministic calculations and preserve exact inputs, outputs and assumptions.

## Required inputs

Current stage attempt/hash, explicitly supplied parameters and units, material/device sources and model assumptions.

## Questions for the engineer

Which registered calculator is appropriate? Are all inputs and coefficient conventions supplied? Are the model limits acceptable?

## Supported engineering tools

Only calculators returned by list_supported_calculations; no equations reimplemented by the agent or frontend.

## MCP/CLI operations

`mcp:list_supported_calculations`, `mcp:record_calculation_run`, `mcp:list_calculation_runs`, `mcp:get_engineering_record`, `mcp:record_validation_evidence`, `mcp:apply_lifecycle_stage`. Use the actual discovered schema; corresponding structured operations use `mendex engineering OPERATION request.json`, lifecycle actions use `mendex lifecycle apply request.json`, and legacy operations use their existing CLI groups.

## Expected artifacts

Persisted calculation run and a calculation report using its actual returned values.

## Structured records to persist

Record calculator ID, inputs/result, implementation hash/version, assumptions, warnings and revision/stage association.

## Validation rules

No implicit electrical defaults, fractional layer truncation, unit conversion or unsupported coefficient reuse. SUCCEEDED means software execution.

## Evidence requirements

Actual calculation record plus explicit numerical validation criteria/evidence when supplied.

## Completion criteria

Use calculations_acceptance only through current intact validation evidence and review gates. FAILED execution has no invented output.

## Human review requirements

Request qualified review of assumptions/model applicability; a numerical rule is not product approval.

## Error handling

Invalid inputs require correction. For a timeout, inspect receipts with the same key before retrying; arithmetic failures stay FAILED.

## Next-stage recommendations

Recommend artifact development or further analysis with traceable references to the calculation run.

