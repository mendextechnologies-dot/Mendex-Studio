# Requirements and Specifications

Lifecycle stage: `requirements`. Generic instructions; no product-specific requirements.

## Purpose

Collect sourced electrical, mechanical, environmental, safety and performance requirements without duplicate entry.

## Required inputs

Existing revision, current specifications, source documents, standards profile and engineer-supplied acceptance criteria.

## Questions for the engineer

What ranges, tolerances, environments and constraints apply? Which inputs/criteria are missing? Which standards edition is supplied?

## Supported engineering tools

Existing typed SI specification service and structured requirement records.

## MCP/CLI operations

`mcp:get_project_specifications`, `mcp:validate_specification`, `mcp:save_project_specification`, `mcp:get_project_lifecycle`, `mcp:apply_lifecycle_stage`, `mcp:record_requirements`, `mcp:get_requirement_coverage`, `mcp:list_requirements`. Use the actual discovered schema; corresponding structured operations use `mendex engineering OPERATION request.json`, lifecycle actions use `mendex lifecycle apply request.json`, and legacy operations use their existing CLI groups.

## Expected artifacts

Structured specification, source references, missing-input findings and requirements snapshot.

## Structured records to persist

Save specifications through core; reopen the stage after specification changes; use specification_field references rather than repeating values.

## Validation rules

A schema-valid specification is not complete requirements or standards compliance. Keep UNASSIGNED/missing inputs visible.

## Evidence requirements

Sources, assumptions and explicit criteria; quantitative validation records only with supplied bounds and intact evidence.

## Completion criteria

Empty coverage findings are not approval. The default requirements_acceptance numerical placeholder and authorized review remain explicit gates.

## Human review requirements

Request independent review; never assert a reviewer identity is authenticated.

## Error handling

Reject unknown fields or conflicting units; ask for missing constraints and leave unavailable checks NOT_EVALUATED.

## Next-stage recommendations

Proceed to feasibility and/or supported calculations when inputs permit; record blockers instead of guessing.

