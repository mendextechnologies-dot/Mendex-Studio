# Engineering Design Development

Lifecycle stage: `design_development`. Generic instructions; no product-specific requirements.

## Purpose

Manage supported design generation and native artifacts through core/native tools.

## Required inputs

Current requirements/revision, explicit supported topology/tool scope, component provenance and significant-change policy.

## Questions for the engineer

Is a new revision needed before editing? Are all generator inputs explicit? Which native tool will own authoring?

## Supported engineering tools

Existing generate_design service and LTspice/FEMM/KiCad native editors where supported; Studio is a viewer.

## MCP/CLI operations

`mcp:get_project_specifications`, `mcp:create_revision`, `mcp:generate_design`, `mcp:get_design`, `mcp:list_design_candidates`, `mcp:list_design_artifacts`, `mcp:register_engineering_artifact`, `mcp:apply_lifecycle_stage`. Use the actual discovered schema; corresponding structured operations use `mendex engineering OPERATION request.json`, lifecycle actions use `mendex lifecycle apply request.json`, and legacy operations use their existing CLI groups.

## Expected artifacts

Native design files, design revision, component references and source documentation.

## Structured records to persist

Register actual confined revision files with classification and expected SHA-256; preserve design/product revision identities separately.

## Validation rules

Do not rely on generator default values for engineering inputs. Never overwrite a frozen baseline or duplicate a native editor in Studio.

## Evidence requirements

Exact native inputs, generator provenance, artifact hashes and supported validation records.

## Completion criteria

The design_development_acceptance criterion and required review must be satisfied; a generated file is not validated design.

## Human review requirements

Ask for engineering review of generated artifacts; no automatic approval.

## Error handling

If generation is unsupported or an input is missing, block and report it; do not create placeholder evidence.

## Next-stage recommendations

Prepare supported simulation configurations in native files and retain their revision/hash association.

