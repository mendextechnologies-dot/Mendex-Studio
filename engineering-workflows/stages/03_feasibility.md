# Feasibility and Architecture

Lifecycle stage: `feasibility`. Generic instructions; no product-specific requirements.

## Purpose

Compare supported approaches and document decisions, assumptions and technical risks.

## Required inputs

Versioned requirements, alternatives, explicit constraints and known capability/tool limitations.

## Questions for the engineer

Which alternatives are viable? What tradeoffs matter? Which assumptions and unresolved risks need a qualified decision?

## Supported engineering tools

Existing core calculation/design capability discovery and native tool inspection; no new product implementation.

## MCP/CLI operations

`mcp:get_project_specifications`, `mcp:list_supported_calculations`, `mcp:list_tools`, `mcp:record_requirements`, `mcp:register_engineering_artifact`, `mcp:apply_lifecycle_stage`. Use the actual discovered schema; corresponding structured operations use `mendex engineering OPERATION request.json`, lifecycle actions use `mendex lifecycle apply request.json`, and legacy operations use their existing CLI groups.

## Expected artifacts

Feasibility report, alternatives table, decisions and risk register.

## Structured records to persist

Register actual revision-relative documents with expected hashes and stage/revision/source context.

## Validation rules

Separate analytical estimates, qualitative decisions and measured facts. Never invent efficiency, feasibility scores or vendor specifications.

## Evidence requirements

Source documents, calculations where supported and recorded rationale; file existence alone is not completion.

## Completion criteria

Inspect feasibility_acceptance and review blockers; request review, not self-approval.

## Human review requirements

Architecture choices needing engineering judgment require human review.

## Error handling

If an analysis is unsupported, document the limit and block the criterion; do not synthesize a fake result.

## Next-stage recommendations

Recommend calculation and design work only with the required inputs and an explicit scope.

