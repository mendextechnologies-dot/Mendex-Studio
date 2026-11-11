# 08 - AI Agent Compatibility (independent)

## Config files
- `mcp_config.json`: `"command": ".venv\\Scripts\\python.exe"`, args `-m mendex_core.mcp --root .`, env `PYTHONPATH=src`, with no `cwd`. The command, PYTHONPATH, and root are all relative, so they resolve against whatever cwd the client launches from. In most clients (for example, Claude Desktop) that is not the repo, so the server fails to start. When it is the repo, `--root .` makes the **repository itself the data root**, and agent actions write products/, workspaces/, and engineering_designs/ into the source tree. **P1.**
- `.vscode/mcp.json`: uses `${workspaceFolder}/.venv/Scripts/python.exe` and `--root ${workspaceFolder}`, which is valid VS Code syntax. However, `PYTHONPATH: "src"` is relative and depends on cwd. The data root is again the repo (same P1). It was not tested inside VS Code.
- `.venv\Scripts\python.exe -m mendex_core.mcp` starts correctly with an absolute PYTHONPATH (demonstrated live).

## Installed agents
| Agent | Detection | Connection to Mendex MCP | Status |
|---|---|---|---|
| Claude Code | `where claude` -> `C:\Users\Sagar\AppData\Roaming\npm\claude(.cmd)` and `.npm-global\claude`. `claude --version` -> `2.1.284 (Claude Code)` | `claude mcp list` shows only `notion` (HTTP) and `ltspice` (ltspice-mcp-bridge.exe). **mendex-engineering is not registered.** No config was changed | **NOT VERIFIED** (not configured, no connection demonstrated) |
| Codex | `where codex` -> "Could not find" | n/a | **NOT VERIFIED** (not installed) |
| Antigravity | `where antigravity` -> not found. PATH entry `...\Programs\Antigravity\bin` does not exist on disk | n/a | **NOT VERIFIED** (not found) |
| VS Code MCP | `.vscode/mcp.json` present | not exercised | **NOT VERIFIED** |

## Protocol-level result
**Protocol verified (not agent verified):** a self-driven stdio JSON-RPC session completed initialize, notifications/initialized, tools/list (23 tools), tools/call (success and error paths), and ping, with clean stdout. Details are in 07.

## Compatibility risks
- The server answers protocol `2024-11-05` whatever the client requests (server.py:27).
- Schemas list required fields that the server actually defaults (generate_design, server.py:227).
- There are no tool annotations, so clients cannot auto-gate destructive tools (`delete_product`, `delete_project`) or process-launching tools (`open_tool_file`, `open_artifact`, `run_simulation`).
- Missing-argument errors come back as bare KeyError text (`'name'`).
- A synchronous solver run blocks the single stdio loop, so client timeouts can abort long simulations.
- `validate_specification` (strict model, `extra_forbidden`) and `generate_design` (vin_nom/vout/iout) use different field vocabularies.
