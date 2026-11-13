# Project Initialization

Lifecycle stage: `project_initialization`. Generic instructions; no product-specific requirements.

## Purpose

Establish an existing or new engineering project, its context and revision identity.

## Required inputs

Project name/code/category/owner, data root and engineering discipline.

## Questions for the engineer

Is this a new project or an existing UUID/code? Who owns it? Which data root is authoritative?

## Supported engineering tools

Core project/specification services; native tools are not needed.

## MCP/CLI operations

`mcp:list_projects`, `mcp:create_project`, `mcp:get_project`, `mcp:get_project_metadata`, `mcp:get_lifecycle_definition`, `mcp:enroll_lifecycle`, `mcp:get_project_lifecycle`, `mcp:apply_lifecycle_stage`. Use the actual discovered schema; corresponding structured operations use `mendex engineering OPERATION request.json`, lifecycle actions use `mendex lifecycle apply request.json`, and legacy operations use their existing CLI groups.

## Expected artifacts

Project metadata, directory and revision IDs; explicit lifecycle enrollment.

## Structured records to persist

Existing project/product and initial revision; lifecycle enrollment and start event.

## Validation rules

Find existing IDs first. Never create a duplicate workspace/project to make Studio see it.

## Evidence requirements

Persisted project/revision context and attributable lifecycle events.

## Completion criteria

Request start, inspect blockers, then request complete only when the project_context criterion is satisfied. Enrollment alone does not complete the stage.

## Human review requirements

Initialization process completion does not authorize engineering work or hardware.

## Error handling

On CONFLICT reread existing project/receipt before retrying; do not delete a project to repair a duplicate code.

## Next-stage recommendations

Collect requirements next; retain the same project/revision IDs.

