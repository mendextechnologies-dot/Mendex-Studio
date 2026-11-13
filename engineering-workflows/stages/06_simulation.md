# Simulation and Analysis

Lifecycle stage: `simulation`. Generic instructions; no product-specific requirements.

## Purpose

Run supported real native tools and inspect execution separately from engineering validation.

## Required inputs

Explicit native input file, current revision/hash, configured tool/version, solver parameters and acceptance criteria.

## Questions for the engineer

Is this exact operation available and qualified? Which file governs duration/analysis? What results and units are expected?

## Supported engineering tools

Existing LTspice/FEMM runners and supported KiCad checks; discovered tools are not automatically operational.

## MCP/CLI operations

`mcp:list_tools`, `mcp:check_tool`, `mcp:list_simulations`, `mcp:run_simulation`, `mcp:get_simulation_status`, `mcp:get_simulation_logs`, `mcp:get_simulation_results`, `mcp:get_simulation_artifact`, `mcp:cancel_simulation_job`, `mcp:register_engineering_artifact`, `mcp:record_validation_evidence`, `mcp:apply_lifecycle_stage`. Use the actual discovered schema; corresponding structured operations use `mendex engineering OPERATION request.json`, lifecycle actions use `mendex lifecycle apply request.json`, and legacy operations use their existing CLI groups.

## Expected artifacts

Actual job record, native inputs, logs, raw waveforms and available numerical outputs.

## Structured records to persist

Use existing persisted job IDs and record source/tool/version/inputs/output references; retain original evidence.

## Validation rules

Configured, started, solver-completed, extracted, validated and reviewed are separate. Never interpolate or invent waveforms; never claim requested duration overrides a native directive when it does not.

## Evidence requirements

Actual solver outputs with checksums and native metadata; no synthetic benchmark as engineering evidence.

## Completion criteria

simulation_acceptance requires explicit current SIMULATED validation evidence and review. A zero exit code does not complete the stage.

## Human review requirements

Request independent engineering interpretation and validation of solver/model assumptions.

## Error handling

Unsupported/missing tools remain NOT_EVALUATED/BLOCKED. Inspect existing runs after a timeout before retrying. Cancellation is supported only for the owning service session; do not claim foreign-process termination.

## Next-stage recommendations

Compare actual available outputs against supplied criteria and carry unresolved failures into verification.

