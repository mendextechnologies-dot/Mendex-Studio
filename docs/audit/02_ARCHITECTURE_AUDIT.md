# 02 Architecture Audit
Auditor: independent (read-only). Date 2026-11-14. Baseline d555d97 + uncommitted tree (37 `git status --short` entries, unchanged during audit). No live runs performed; all findings are static (file:line / command output).

## 1. Repository structure and languages
- Python core: `src/mendex_core` (~16.8k LOC incl. subpackages), `src/integrations` (3,278 LOC), legacy PySide6 UI `src/mendex_ui` (12,327 LOC). Counts via `find <dir> -name '*.py' | xargs cat | wc -l`.
- Desktop: React 18 + Vite 5 + TypeScript 5 (`desktop/package.json`), Tauri 2 shell `desktop/src-tauri/src/main.rs`.
- Other: `contracts/` (JSON Schema incl. v3.1), `engineering-workflows/` (MASTER_ENGINEERING_INSTRUCTIONS.md, stages/, templates/, validation/), `scripts/` (25 Python/PS1 scripts), `tests/` (72 test files: core, integration, ui, adapters, contracts, command_center).
- `pyproject.toml`: mendex-studio 0.1.0, deps `pydantic`, `PySide6>=6.10` (pyproject.toml:9); single console script `mendex = mendex_core.cli:main` (pyproject.toml:15).

## 2. Entry points
| Entry | Target | Evidence |
|---|---|---|
| `mendex` console script | `mendex_core.cli:main` | pyproject.toml:15, cli.py:526 |
| `python -m mendex_core.mcp` | MCP stdio server -> `MendexMCPServer` | mcp/__main__.py:26; server.py:19,32 |
| `python -m mendex_core.desktop` | JSON stdio RPC -> `DesktopService(StudioService)` | desktop/__main__.py:10-13,78 |
| `python -m mendex_core.integration_cli` | integration CLI | integration_cli.py:63 |
| `python -m mendex_core.doctor` | diagnostics | doctor.py:7 |
| `python -m mendex_ui`, `main.py`, `src/main.py` | legacy PySide6 window | mendex_ui/__main__.py:27; main.py:10 |
| `start_desktop.bat` | release Tauri exe if built, else `npm run dev` (Vite) | start_desktop.bat |
| `build_desktop.bat` | `npm run build` + `npm run tauri build` | build_desktop.bat |
| Tauri `main.rs` | spawns `python -u -m mendex_core.desktop` over piped stdio | main.rs:35-56 |
| Vite dev plugin | spawns `.venv/Scripts/python.exe -u -m mendex_core.desktop`, proxies HTTP `/api/rpc` to stdio | desktop/vite.config.ts:6-21,79 |

**Correction to brief:** the desktop backend is NOT a local HTTP server. `mendex_core.desktop` is a stdio JSON RPC process. HTTP exists only in the Vite dev-server middleware (`/api/rpc`); `desktop/src/api/client.ts:24-31` uses Tauri `invoke` when present, else `fetch('/api/rpc')` restricted to localhost.

Python resolution in Tauri (main.rs:35-39): `MENDEX_PYTHON` env -> `resources/backend/python.exe` -> (debug only) `<repo>/.venv`. `tauri.conf.json` declares no `bundle.resources`/`externalBin` and `"icon": []`, so a release bundle ships no backend; release builds require `MENDEX_PYTHON` (P1). In debug, Tauri sets cwd to the repo root (main.rs:46-47); whether the data root then defaults into the repo is NOT VERIFIED live.

## 3. CI/CD and packaging
- CI/CD: none. No `.github/` (`ls .github` -> not found); no other CI config observed. Consistent with AGENTS.md.
- `dist/`: `MendexStudio-v2.0-Setup.bat`, v0.1.0 wheel + source zip + SHA256 files: stale relative to app version 3.1.0 (tauri.conf.json:4). `build/` holds setuptools leftovers.
- `scripts/build_windows_installer.ps1:51` creates a desktop shortcut running `pythonw -m mendex_ui` ("v2.0"): the only installer targets the legacy PySide6 UI, not Tauri.
- `packaging/` contains only README.md.

## 4. Actual dependency / data flow (derived from imports)
```
 VS Code agent (Codex/Claude)             Engineer (desktop)
   | stdio MCP                              | Tauri invoke  |  Vite fetch /api/rpc (dev)
   v                                        v
 mcp/server.py ---.              desktop/__main__.py (stdio JSON RPC)
                  |                          |
 cli.py ----------+--> controller.py         v
   |                 (MendexEngineering   desktop/service.py (DesktopService)
   |                  Controller)            |  + integrations.v15_connector (line 15)
   |                  | design/*, launch.py, |  + bom_generator (line 316)
   |                  | ltspice/femm runners |
   |                  v                      |
   +------------> service.py (StudioService) <+
                    | sqlite_schema, rules, adapters, evidence, plugins,
                    | lifecycle/*, workflows/*, measurements, pcb,
                    | engineering_lifecycle / records / reviews, integration_service
                    v
           SQLite + artifacts + evidence (data root)

 legacy: main.py / mendex_ui (PySide6) --> StudioService, intelligence/*, workflows/*, pcb
 workflows/nodes/* --> intelligence/*
```

## 5. One authoritative core?
Partially. All front-ends converge on `StudioService` (service.py), but:
- MCP uses only `MendexEngineeringController` (server.py:19,32).
- CLI uses both `StudioService` and the controller (cli.py:22-23).
- Desktop uses `StudioService` directly and bypasses the controller (desktop/service.py:2-8 imports; `self.studio.*` at 17-97). Controller-owned design/simulation orchestration (controller.py:24-31) is not reachable from the desktop; desktop RPC is mostly read/open/export/review (dispatch at desktop/service.py:264+).
- BOM generation (`bom_generator`) is imported only by desktop/service.py:316: business logic available on one front-end only (P2).
- desktop/service.py:15-18 imports `integrations.v15_connector` and registers adapters into the core registry at construction: a front-end mutating core state (P2).
- Two orchestration layers (controller.py 1,186 LOC, service.py 823 LOC) form duplicated facades (P2).

## 6. Deviations from intended architecture
1. P1 Release Tauri build has no bundled Python backend (tauri.conf.json bundle; main.rs:36-39).
2. P1 The only Windows installer launches legacy PySide6 UI (scripts/build_windows_installer.ps1:51); PySide6 still a hard runtime dependency (pyproject.toml:9).
3. P2 Desktop bypasses controller; MCP never calls StudioService directly: no single facade.
4. P2 "Desktop HTTP API" is in fact stdio RPC plus a dev-only Vite HTTP proxy.
5. P2 Four calculation libraries and three lifecycle subsystems (see 03).
6. P3 Two conflicting MCP configs (see 13).
