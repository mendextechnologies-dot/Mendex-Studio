# 13 Legacy Code Inventory
Static evidence only (file:line / grep). Verdicts: KEEP / REFACTOR / MIGRATE / REMOVE / INVESTIGATE.

| Component | Path | Verdict | Reason / evidence |
|---|---|---|---|
| PySide6 UI | src/mendex_ui (12,327 LOC) | MIGRATE then REMOVE | Still launched by main.py:10, src/main.py, `python -m mendex_ui` (__main__.py:27), installer shortcut scripts/build_windows_installer.ps1:51, scripts/desktop_smoke.py:13, scripts/pcb_workspace_smoke.py:15; 32 test files reference it |
| PySide6 dependency | pyproject.toml:9; requirements-lock.txt:9-13 (incl. WebEngine, Pdf) | REFACTOR | Hard runtime dep of core although Tauri is the target UI; move to optional extra |
| Root launchers | main.py, src/main.py | REMOVE (after migration) | Duplicate PySide6 launchers |
| Old lifecycle | src/mendex_core/lifecycle/ | INVESTIGATE | Parallel to engineering_lifecycle/; used by service.py, pcb.py, mendex_ui |
| Workflow engine | src/mendex_core/workflows/ | INVESTIGATE | Consumers: service.py and mendex_ui/workflow_canvas only |
| Intelligence calcs | src/mendex_core/intelligence/ | REFACTOR | One of 4 calc libraries; used by workflows + legacy UI |
| Integration calcs | src/integrations/calculations/ | REFACTOR | Duplicate calculation domain |
| Facades | controller.py, service.py, desktop/service.py | REFACTOR | Three facades; desktop bypasses controller |
| integration_cli.py | src/mendex_core/integration_cli.py | INVESTIGATE | No importer, no console script |
| demo_adapter.py | src/mendex_core/demo_adapter.py | INVESTIGATE | Demo adapter imported by integration_service.py |
| v15 connector | src/integrations/v15_connector.py | INVESTIGATE | Version-named legacy module registered from desktop/service.py:15 |
| Root MCP config | mcp_config.json | REMOVE or align | Hard-coded `C:\Mendex studio\...`, no `--root` (falls back to default root); conflicts with .vscode/mcp.json which passes `--root ${workspaceFolder}` |
| VS Code MCP config | .vscode/mcp.json | KEEP | Workspace-relative |
| Installer script | scripts/build_windows_installer.ps1 | REFACTOR | Targets v2.0 PySide6 UI |
| dist artefacts | dist/ (v0.1.0 wheel/zip, MendexStudio-v2.0-Setup.bat) | REMOVE | Stale vs app 3.1.0 |
| build/ | build/bdist.win-amd64, build/lib | REMOVE | setuptools leftovers |
| Tauri bundle config | desktop/src-tauri/tauri.conf.json | REFACTOR | No backend resource, empty icon list |
| Version-specific scripts | scripts/v15_*, v17_*, v19_*, v21_capture_screens.py, unblock_sv1000.py, remove_existing_products.py, execute_last_operation.py | INVESTIGATE | One-off; some destructive by name |
| Root scratch | check_windows.py, list_*windows.py, root test_*.py, drc_test.json, erc_test.json, edge_snap.png, temp_femm_test/, sv1000.pdf | REMOVE or move to fixtures | Not collected by pytest; binaries tracked in git |
| Office lock file | docs/~$ndex_Developer_Prompt_Handbook.docx | REMOVE | Word lock artefact |
| Obsolete docs | docs/V1_8_*, V1_9_*, V20_*, V21_*, IMPLEMENTATION_STATUS_V1_7.md, OWNERSHIP_V1_5.md, V15_INTEGRATION_HANDOFF.md, AGENT2_HANDOFF.md, docs/chats/ | MIGRATE to archive | Superseded; claims unverified |
| Deprecated MCP tools | src/mendex_core/mcp/server.py | NOT VERIFIED | No "deprecated" marker found by grep; tool list not enumerated |
| Unused deps | pyproject/package.json | NOT VERIFIED beyond PySide6 | JS deps (react, lucide-react) appear used; not exhaustively checked |
| Stage prompts | engineering-workflows/ | KEEP | Matches intended architecture |
| React/Tauri app | desktop/ | KEEP | Target UI |
