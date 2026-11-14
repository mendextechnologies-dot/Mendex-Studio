# 07 Engineering Prompts Audit (2026-11-14)

## Files reviewed
- `engineering-workflows/MASTER_ENGINEERING_INSTRUCTIONS.md`
- `stages/01..09_*.md`
- `templates/{calculation_report,engineering_review,feasibility_report,project_specification,simulation_report,verification_report}.md`
- `validation/{engineering_rules,evidence_requirements,stage_completion_rules}.md`

## Findings
- **Tool names:** every `get_/list_/record_/register_/apply_/enroll_/generate_/run_/request_/create_/save_/update_/export_/cancel_/validate_` identifier in the folder was compared with the live list of 64 tools. The only name that does not match a tool is `request_review`. It is a lifecycle *action*, not a tool: acceptable, but it could confuse agents.
- **Anti-fabrication rules:** explicit in:
  - MASTER:16 ("no fabricated thresholds"; "Stage prompts are instructions, not executable approvals")
  - 03_feasibility:35
  - 04_calculations:43
  - 06_simulation:35
  - validation/engineering_rules.md:3 (no invented vendor data, NOT_EVALUATED for unsupported checks, no automatic approval)
- **Generic and reusable:** stage files map 1:1 to lifecycle stage ids, and numerical criteria are explicitly labelled as placeholders.
- **Deprecated references:** a grep for `copilot|ai assistant|v2.` found nothing.

## Gaps
- "Prompts are not approvals" is enforced only by the prompt text. The tool surface lets an agent register a reviewer (see 06 and 11).
- NOT VERIFIED line-by-line:
  - Per-stage wording on output persistence, failure reporting and restoring context from records.
  - Whether the templates are bound to `generate_revision_report` output.
