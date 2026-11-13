# Master engineering instructions

Use this library when an engineer says: "Start a new engineering project using the Mendex engineering lifecycle", or asks to continue an existing project. It works with Codex, Claude Code, Antigravity or a human CLI user; the core contains no agent-specific provider.

1. Read AGENTS.md, docs/architecture.md, docs/engineering-rules.md and contracts/README.md. Discover actual MCP tools and schemas. Choose the explicit data root; preserve project, revision and workspace identifiers.
2. Find the existing project with `mcp:list_projects`/`mcp:get_project`. Only use `mcp:create_project` when a new project is intended and identity/context are supplied. Do not create duplicate records or delete data to resolve a conflict.
3. Retrieve `mcp:get_lifecycle_definition` and `mcp:get_project_lifecycle`. An unenrolled draft requires explicit `mcp:enroll_lifecycle`; this does not complete stages. Existing legacy PASS flags are not generic lifecycle completion.
4. Read the relevant stage prompt, current specifications, evidence and missing-input findings. Ask only necessary engineering questions. Missing electrical values, material properties, physical measurements and acceptance thresholds are never guessed.
5. Execute only supported existing operations through MCP/CLI. No duplicated calculations, direct SQL, cloud dependency, custom native-tool editor or built-in AI chat. Start/reopen a draft stage with `mcp:apply_lifecycle_stage`; use its current specification hash for attributed record writes.
6. Use stable idempotency keys per intended operation. After uncertain transport failures inspect persisted results and retry the same request/key. A changed request needs a new key and current context. Never automatically repeat a simulation because its caller timed out.
7. Persist real requirements, calculations, artifacts, validation and reports through their shared core APIs. Significant changes need `mcp:create_revision` before edits. Frozen history/raw evidence is never overwritten.
8. Inspect effective evidence integrity/staleness and dependency blockers. Request completion only with explicit supported criteria. File existence, model confidence and solver success are not engineering acceptance.
9. Request review using the stage request_review action. No approve operation exists; caller-supplied identities are not authenticated. Review-required stages remain awaiting review/blocked when authorization is unavailable.
10. Present actual findings, source IDs/hashes, warnings, unknowns and next actions. Hardware control, manufacturing approval, CI/CD, automatic deployment and development of a specific commercial product are outside this implementation task.

Read [engineering rules](validation/engineering_rules.md), [evidence requirements](validation/evidence_requirements.md) and [completion rules](validation/stage_completion_rules.md). Stage prompts are instructions, not executable approvals. The default numerical criterion names are conservative placeholders with no fabricated thresholds; use an engineer-supplied versioned policy for discipline-specific acceptance.

