# 07 - CLI and MCP Audit (independent)

Audit date: 2026-11-11. Branch `v2.0-engineering-qualification`. Read-only audit of the app.
Live runs used isolated data roots under `%TEMP%\mendex-audit\cli-mcp\{root,mcproot,mcproot2}` with cwd set to that folder. The interpreter was `C:\Mendex studio\.venv\Scripts\python.exe` with `PYTHONPATH=C:\Mendex studio\src`.
No solver (LTspice/FEMM/KiCad) was run. `run_simulation`, `simulation run`, `open_artifact`, `open_tool_file`, `tool open`, `artifact open`, and the `pcb-*`/`open-*` commands were NOT RUN. They are NOT VERIFIED live.

**Concurrency caveat:** `src/mendex_core/mcp/server.py` and `controller.py` are untracked, and another party changed them during this audit. server.py grew from 615 to 703 lines and gained `*_project` tools. The live results below come from the earlier 23-tool build. Line references marked "(now)" are for the file as it was at the end of the audit.

## A. CLI (`src/mendex_core/cli.py`)

### How the data root is chosen
- `--root` defaults to `Path.cwd()` (cli.py:30). The MCP entry point has the same default (mcp/__main__.py:15), and so does the controller (controller.py:38).
- Running `mendex` from the repo directory without `--root` writes into the repo. All runs here passed `--root <temp>`.
- `doctor` has its own `--root` (dest `DOCTOR_ROOT`) that shadows the global one.

### Commands
Top-level commands listed by `mendex --help`: products, delete-product, tools, plugins, rules, ai-availability, request-simulation, runs, export-specification, doctor, open-vscode, open-file, validation, report, pcb-files, pcb-checks, pcb-import, pcb-open, pcb-check, pcb-notes, create, workspace {list,create,status}, specification {validate,save}, design {generate,show,candidates}, calculate {dowell,losses,steinmetz,flyback}, simulation {run,list}, artifact {list,open}, tool {list,check,open}.

### Live results (cwd = temp, `--root <temp>\root`)
| Command | Exit | stdout JSON | Notes |
|---|---|---|---|
| `products` (empty) | 0 | valid `[]` | |
| `workspace create AuditWS --description x` | 0 | valid | id cf40d92c-... |
| `workspace list` (new process) | 0 | valid | workspace persisted across invocations |
| `create AUD-1 "Audit Product" --owner auditor --category dc_dc_converter` | 0 | valid | revision 7916a000-... created |
| `products` (new process) | 0 | valid | persisted |
| `workspace status <id>` | 0 | valid | |
| `workspace status bad-id` | 1 | stdout empty; stderr `{"error": "INVALID_INPUT", ...}` | structured error goes to stderr |
| `workspace status ../../etc` | 1 | stderr "Access denied: Traversal or path separators not allowed" | confinement works |
| `workspace status` (missing arg) | 2 | argparse usage text | not JSON |
| `nosuch` | 2 | argparse text | not JSON |
| `calculate dowell` | 0 | valid | F_r 3.7791, R_ac 0.188955 |
| `calculate flyback` | 0 | valid | turns ratio 1.0, Np=Ns=3. Engineering plausibility is not judged here |
| `calculate steinmetz --freq -5` | 1 | stderr INVALID_INPUT | input validated |
| `calculate losses --duty 7` | 1 | stderr INVALID_INPUT | input validated |
| `design generate --workspace <id> --title AuditBuck` | 0 | valid, 1.46 s | Wrote .net, .asc, KiCad sch/pcb/pro under `workspaces/<id>/generated_artifacts/rev_1`. FreeCAD was not invoked for the buck design |
| `design show <id>` / `design candidates <id>` | 0 | valid | |
| `design show 0000...` | 1 | stderr NOT_FOUND | |
| `artifact list --workspace <id>` | 0 | valid | includes sha256 |
| `simulation list` | 0 | `[]` | |
| `runs --revision <rev>` / `validation --revision <rev>` | 0 | `[]` | |
| `validation --revision notauuid` | 1 | stderr INVALID_INPUT | |
| `specification validate '{"vin_nom":24,"vout":5,"iout":4}'` | 1 | valid JSON `valid:false`, `extra_forbidden` | **Schema mismatch:** the spec model rejects the same field names that `design generate` and MCP `generate_design` use |
| `report --revision <rev>` | 0 | valid | HTML report written. Warning text: "DRAFT ONLY: no manuf..." |
| `rules` | 0 | valid | |
| `tool list` / `tool check ltspice` | 0 | valid | detection only. **Inconsistency:** `tool list` gives installed_path `C:\Program Files\ADI\LTspice\LTspice.exe`, while `tool check` gives `installed_path: null` |

Verdict: the CLI produces JSON on success, and persistence across invocations works. Errors are JSON on stderr with exit 1. Argparse errors exit 2 with plain text. **VERIFIED** for the commands listed above. Unrun commands are NOT VERIFIED.

## B. MCP server (`src/mendex_core/mcp/server.py`)
Live probe: the script `%TEMP%\mendex-audit\cli-mcp\scripts\mcp_probe.py` spawned `python -m mendex_core.mcp --root <temp>\mcproot` and spoke newline-delimited JSON-RPC over stdio.

- **initialize:** the client asked for `2025-06-18`. The server answered `"protocolVersion": "2024-11-05"` and `capabilities: {"tools": {}}`. The version is a fixed constant (server.py:27) with no negotiation. This is acceptable because clients fall back, but it is an old revision.
- **notifications/initialized:** no response, which is correct.
- **tools/list:** 23 tools. No tool has `annotations` (destructiveHint/readOnlyHint) and none has an `outputSchema`.
- **Schema drift (P2):** `generate_design` declares `required: [workspace_id, title, vin_nom, vout, iout]` (server.py:227 now). The dispatcher defaults all of these, and a call with only workspace_id and title succeeded. `run_engineering_calculations` requires `params` in its schema, but the dispatcher uses `args.get("params", {})`. Arguments are never validated against `inputSchema`.
- **tools/call success:** create_workspace, list_workspaces, run_engineering_calculations(dowell), generate_design, list_design_artifacts, create_product, list_products, check_tool, and ping all returned results with `isError:false`. The payload is pretty-printed JSON inside a text content block.
- **Errors:**
  - Unknown tool: `result.isError:true` "Unknown MCP tool 'unknown_tool'".
  - Missing required arg: `isError:true` with the bare text `'name'` (a KeyError message that is not useful to an agent).
  - Bad type `vout:"abc"`: `isError:true` "could not convert string to float".
  - `params:"bad"` and `arguments:[1]`: JSON-RPC -32602.
  - Malformed JSON: -32700.
  - `[]`: -32600.
  - `resources/list`: -32601.
  - A message without `"jsonrpc":"2.0"` is accepted (lenient).
- **stdout cleanliness:** after 28 requests, no non-JSON line appeared on stdout. Logs and tracebacks go to stderr through `logger.exception` (server.py:510 now). The tracebacks are large: about 11 KB of stderr for 14 errors.
- **Pipe deadlock (LIVE):** with stderr on an undrained PIPE, the server blocked on request 13 for more than 120 s, because the Windows pipe buffer filled with tracebacks. The same call in-process returned in 0.001 s. Real clients drain stderr, so this is P2.
- **Path traversal:**
  - `get_workspace_status "../../Windows"` and `list_design_artifacts "..\x"` were rejected (`_resolve_workspace_dir`, controller.py:44).
  - `open_artifact` with `../../../../Windows/win.ini` was rejected, and so was the absolute `C:/Windows/win.ini` (`_resolve_artifact_path`, controller.py:100 now).
  - `list_revisions "../x"` was rejected by the UUID parse.
  - **`open_tool_file` is NOT confined (P1):** absolute paths are accepted, and relative paths are resolved without a containment check (controller.py:1017-1023 now). LIVE: `../../../../../Windows/win.ini` resolved to `C:\Users\Sagar\AppData\Windows\win.ini`, outside the data root. It was stopped only by "does not exist" and, for `C:/Windows/win.ini`, by the extension allow-list in `launch_tool` (launch.py:213+).
- **Sensitive operations without approval (P1):**
  - `delete_product` (MCP, and CLI `delete-product`) has no confirmation and no immutability check. `delete_product` (service.py:242-293) deletes validations, reports, runs, lifecycle_approvals, and measurements rows, then runs `shutil.rmtree(products/<id>)`, which removes report and evidence files. This conflicts with AGENTS.md "Never change frozen baselines or raw evidence". It was exercised live only against a nonexistent id (NOT_FOUND). The destructive path was confirmed by code reading.
  - `open_artifact` and `open_tool_file` launch GUI executables (`subprocess.Popen`, and `os.startfile` for .html/.pdf/.json/etc., launch.py:32-170). `run_simulation` launches solvers. No tool approves a design for manufacturing. No tool runs arbitrary shell commands.
- **Long-running jobs:** `run_simulation` runs synchronously inside the request. It has no job id or polling, and no progress or cancellation notifications. The stdio loop is single-threaded, so the server cannot respond while a solver runs. NOT VERIFIED live (no solver runs).
- **Delegation:** `_dispatch_tool` forwards to `MendexEngineeringController`, which uses `ServiceStore` and the design service. The CLI uses the same controller (for example, cli.py:358). No calculation logic is duplicated in server.py. Only argument coercion (`float(...)` defaults) is duplicated between server.py and cli.py.
- **Repo writes:** none from my runs. The untracked `engineering_designs/1af250bd-...json` (title "Buck 24V to 5V", mtime 21:57 local) and `workspaces/4f7a9de8-...` in the repo were not created by me: my design ids were b331010f and 08659db1, both in temp. They likely came from another party running with the repo as root.

## Doc claims
`docs/V21_CLI_REFERENCE.md` and `docs/V21_MCP_TOOL_REFERENCE.md` were not relied on. Any claim there that goes beyond the tables above is NOT VERIFIED.
