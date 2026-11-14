# 06 Workflow Stage Audit (2026-11-14)

## Scope
- Stages (definition `engineering` 3.1.0; prompts in `engineering-workflows/stages/01..09`): project_initialization, requirements, feasibility, calculations, design_development, simulation, verification, prototype_testing, documentation.
- Backend: `engineering_lifecycle/service.py`.
- Actions: `start|block|fail|request_review|complete|not_applicable|reopen|attach_evidence` (`models.py:137-139`). They are exposed identically through MCP `apply_lifecycle_stage` and CLI `lifecycle apply`.
- Desktop: the stdio RPC `complete_stage` method (`desktop/service.py:318`) and `submit_review` method (`desktop/service.py:313`, which calls `record_manual_decision`).

## Live tests (temp root, revision 728e563c...)
| Test | Result |
|---|---|
| Enroll, then start and complete project_initialization with source "mcp-agent" | COMPLETED. The automatic criterion `project_identity` was PASS. **Stage 1 has no human gate.** |
| Complete requirements without starting it | CONFLICT: "Start/reopen the stage before this operation" |
| `not_applicable` on calculations | INVALID_INPUT: "Mandatory stage cannot be marked not applicable" |
| Unknown stage `bogus` | NOT_FOUND |
| Complete requirements after start, with no review | Blocked: "Authorized human review is required ... review requests are not approvals" (`service.py:167-216`) |
| `record_human_review` on an empty requirements package | INVALID_INPUT: "empty requirements package" |
| `record_requirements` while a review is requested | CONFLICT. After `reopen` (attempt 2) it was accepted. |
| APPROVED decision with an incomplete spec | Blocked by mandatory safety items (vin/vout and isolation not specified) |
| REJECTED decision by the agent-registered reviewer `jdoe` | **Recorded** with `identity_authenticated:false` |

Not tested (NOT VERIFIED): failed execution, revisions invalidating completed stages, and resume after process restart. State is stored in SQLite, so resume is plausible but was not run. UI visibility was also not checked.

## CRITICAL: can an AI agent mark a stage complete or record a human approval?
- **Stage completion:** yes, for stages without a review gate. The agent completed stage 1 itself.
- **Human review:** an MCP agent can record a "human" review decision.
  - `register_authorized_reviewer` is an MCP tool (`engineering_reviews/api.py:10`). The agent picks both the reviewer and the secret, then calls `record_human_review` with them.
  - The only guard is a substring blacklist on the reviewer id: "agent", "mcp", "bot", "auto", "claude", "codex" (`engineering_reviews/service.py:45,283`).
  - Live, an agent-registered reviewer recorded a REJECTED decision. The full APPROVED path was NOT VERIFIED end-to-end; in this test it was blocked only by spec data, which the agent can also write.
- **Approver identity:** not verified. It is a self-provisioned id and passphrase, explicitly stored as `identity_authenticated: False` (`service.py:359`).
  - The self-review check compares the reviewer id with the free-text `submitter` field (`service.py:306`), so different strings bypass it.
  - The desktop `submit_review` path uses a free-text reviewer_name only (`service.py:233-242`).
