# 11 Security Audit (2026-11-14, non-destructive)

## Critical
1. **Approval authorization bypass via MCP.**
   - `register_authorized_reviewer` and `record_human_review` are both MCP tools (`engineering_reviews/api.py:5-12`, merged into the server at `mcp/server.py:36-39,560-562`).
   - Live test: an MCP call registered `jdoe` with roles lead_engineer/requirements_reviewer and a secret the agent chose. A CLI call then recorded a REJECTED decision as "J Doe" (`identity_authenticated:false`).
   - The only defense is a substring blacklist on the reviewer id (`engineering_reviews/service.py:45,283`).
   - Fix: remove reviewer provisioning from agent surfaces.

## High
2. **Vite dev proxy is exposed on all interfaces.**
   - `desktop/vite.config.ts:155` sets `host: '::'` with port 5173 and strictPort.
   - The `/api/rpc` guard (`vite.config.ts:80-83`) compares the client-supplied `Host`/`Origin` headers against `localhost:5173`. Any non-browser client, on this machine or on the LAN, can set `Host: localhost:5173`, and a request with no Origin passes.
   - The proxy spawns `python -m mendex_core.desktop` with no `--root` (`vite.config.ts:21`), so it works on the real data root.
   - Through it a caller can reach `complete_stage`, `submit_review` (free-text reviewer name), `request_review`, `generate_bom`, `export_report`, and `open_file`/`reveal_file`/`open_report`/`open_evidence`, which launch native apps (`desktop/service.py:273-325`).
   - This is dev-only. Not exploited live: NOT VERIFIED at runtime.
3. **The default data root is the repo, which holds real data.** `mcp_config.json` passes no `--root`; `.vscode/mcp.json` passes the workspace folder. The MCP tools `delete_project` and `delete_product` have no confirmation step.
4. **Agents can trigger process execution.**
   - `run_simulation` (MCP/CLI) runs LTspice synchronously (`controller.py:735-760`).
   - `open_tool_file` and `open_artifact` launch native apps.
   - Paths are confined: `controller.py:1175-1178` checks the target against the root; `service.py:205-216` confines `open_project_file` to the revision folder.
5. **Shell command string on non-Windows.** `launch.py:182` runs `subprocess.Popen(cmd_line, shell=True)` with a single command string, so shell metacharacters in path components could inject commands. The Windows command construction was not reviewed: NOT VERIFIED.

## Medium / Low
6. **Older MCP tools lack schema validation.** They return raw `KeyError` messages, and pydantic tracebacks go to stderr.
7. **Tauri.**
   - The desktop backend is a Python child process over stdin/stdout (`main.rs:27-115`), with a single invoke command, `rpc_dispatch`. There is no network listener in production.
   - `withGlobalTauri: true`.
   - The CSP `connect-src` allows `http://localhost:* ws://localhost:*`, which is broader than needed.
   - There is no `src-tauri/capabilities/` directory.
8. **Report HTML escaping.** Product code, name and revision label are escaped (`service.py:630,661`, `integration_service.py:587-588`). Full template coverage: NOT VERIFIED.
9. **Secrets.**
   - `.mendex/` holds `ui_preferences.json` and the SQLite database; no `.mendex/*.json` file matched `api_key|sk-`.
   - Reviewer secrets are stored salted and hashed (`engineering_reviews/storage.py`).
   - Secrets in logs: NOT VERIFIED.

Not tested: parsing of untrusted engineering files.
