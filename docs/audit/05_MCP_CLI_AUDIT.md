# 05 MCP / CLI Audit (2026-11-14, audit-only)

Data root for all live runs: `%TEMP%\mendex-audit3\mcp`. Python: `.venv\Scripts\python.exe` with `PYTHONPATH=src`.

## Inventory
- MCP: `python -m mendex_core.mcp --root <tmp>`. A live `tools/list` returned **64 tools** (server `mendex-engineering-mcp` 2.1.0, protocol 2024-11-05):
  - 7 lifecycle tools (`engineering_lifecycle/api.py` OPERATIONS)
  - 22 record tools (`engineering_records/api.py`)
  - 6 review tools (`engineering_reviews/api.py:5-12`)
  - 29 older hand-written tools (`mcp/server.py:42-405`). These are dispatched by the if/elif chain at `server.py:549-650`.
- CLI (`cli.py:34-256`):
  - Older commands: products, delete-product, tools, plugins, rules, request-simulation, runs, export-specification, doctor, launch*, validation, report, pcb*, create, projects, create-project, delete-project, plus the project, workspace, specification, design, calculate, simulation, artifact and tool subcommand groups.
  - v3.1 commands: `lifecycle {definitions,definition,register,enroll,apply,show,history}`, `engineering <op> <json>`, `review <op> <json>`.

| Group | Registration | Input schema | Backend | Persistence | Permission boundary |
|---|---|---|---|---|---|
| lifecycle/records/reviews | Shared OPERATIONS registries feed `tool_schemas()` (pydantic, `additionalProperties:false`) | Strict | `StudioService` (.lifecycle/.records/.reviews) | SQLite `studio.sqlite3` plus engineering-records | **None.** Every operation is exposed to MCP, including `register_authorized_reviewer`, `record_human_review` and `apply_lifecycle_stage complete`. |
| Older tools (create_project, run_simulation, open_tool_file, delete_project, ...) | Hand-written JSON in server.py | Loose: a missing key raises a raw `KeyError` | `MendexEngineeringController` (controller.py) | SQLite and workspace files | None. `delete_project`, `delete_product`, `open_tool_file`, `open_artifact` and `run_simulation` can all be called. |

## Live MCP session (stdio)
- `initialize` succeeded; `tools/list` returned 64 tools.
- Unknown tool: returns `isError:true "Unknown MCP tool 'no_such_tool'"`, which is correct.
- `get_project {}`: returns `isError:true "'project_id'"`. This is raw KeyError text because the older tools have no schema validation.
- A non-JSON line returns JSON-RPC error `-32700` with `id:null`, which is correct.
- `create_project` with name `<script>...` is rejected by the Product.code pattern. The full pydantic traceback goes to stderr.
- `register_authorized_reviewer` with `{id:"jdoe", roles:[lead_engineer, requirements_reviewer], secret:<agent-chosen>}` **succeeded** (see 11_SECURITY_AUDIT).

## Live CLI runs (same root)
- Ran: create-project (returned CREATED with revision R001), lifecycle enroll/apply, `engineering record_requirements`, and `review request_stage_review` / `get_review_package` / `record_human_review`.
- Errors come back as JSON `{"error":...}` on stderr with exit code 1 (`cli.py:258-262`).
- Not run: `simulation run` and MCP `run_simulation`. These are **not dispatch-only**: they call `ltspice_runner.run_simulation` synchronously (`controller.py:735-760`), so they would run the real LTspice solver.
- NOT VERIFIED live: calculations, design generate, results, reports, status.

## Shared core and duplicate logic
- For the v3.1 operations, MCP and CLI call the same `dispatch(service, name, args)`, so the core is genuinely shared.
- The older surface is duplicated:
  - MCP goes through `controller.py`, while the CLI's older commands parse arguments separately (`cli.py:84-230`).
  - There are two simulation entry points: `request-simulation` (agent-requests queue) and `simulation run` (runs directly).
  - Older MCP tools overlap the v3.1 ones: `get_validation_summary` vs `get_validation_results`, and `generate_engineering_report` vs `generate_revision_report`.

## Agent discoverability
- `claude mcp list` (read-only) shows only `notion` and `ltspice`. **Mendex is not registered.**
- The repo root has no `.mcp.json` and no `CLAUDE.md`.
- `mcp_config.json` uses an absolute path and passes **no `--root`**, so the server defaults to the repo root, which holds real data. `.vscode/mcp.json` passes `--root ${workspaceFolder}`, which is also the real data root.
- Conclusion: a fresh Claude Code session cannot find the Mendex tools without manual setup.
- Codex / Antigravity: NOT VERIFIED.
