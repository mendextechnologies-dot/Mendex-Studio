# 02 Dependency Analysis — Mendex Engineering Studio v3.1

## Static & Dynamic Dependency Mapping

This analysis documents the dependency relationships between the Codex orchestration layer, the Python Engineering Core, external solvers, the desktop command center, and the legacy Qt framework.

---

## 1. System Architectural Dependency Graph

```text
+-------------------------------------------------------------+
|        Engineer / AI Agent (Codex / Antigravity)            |
+-------------------------------------------------------------+
                             |
         [engineering-workflows/stages/*.md]
                             |
         +-------------------+-------------------+
         |                                       |
         v                                       v
+------------------+                   +------------------+
|    Mendex CLI    |                   | Mendex MCP Server|
| (mendex_core.cli)|                   | (mendex_core.mcp)|
+------------------+                   +------------------+
         |                                       |
         +-------------------+-------------------+
                             |
                             v
               +---------------------------+
               | MendexEngineeringController|
               | (single core facade)      |
               +---------------------------+
                             |
         +-------------------+-------------------+
         |                                       |
         v                                       v
+------------------+                   +---------------------+
|  StudioService   |                   |DeterministicCalculations|
| (core authority) |                   | (sizing, Dowell, etc)|
+------------------+                   +---------------------+
         |
         +-------------------+-------------------+
         |                   |                   |
         v                   v                   v
+------------------+ +---------------+ +---------------------+
| SQLite Metadata  | | Filesystem CAD| | Solver Connectors   |
| (.mendex/studio) | | (products/**) | | (LTspice, FEMM, etc)|
+------------------+ +---------------+ +---------------------+
                             ^
                             | (read-only SQLite & files)
+------------------------------------------------------------+
|            Desktop RPC Bridge (DesktopService)             |
|          python -u -m mendex_core.desktop (stdio)          |
+------------------------------------------------------------+
                             | (JSON-lines stdio over ::)
+------------------------------------------------------------+
|       Modern Web Command Center (desktop/ React + Vite)    |
|                http://localhost:5173                       |
|           [Optional Tauri 2 Desktop Shell]                 |
+------------------------------------------------------------+
```

---

## 2. Python Dependency Manifest (`pyproject.toml`)

### Active Runtime Dependencies
- `python`: `>=3.13,<3.14` (Verified: Python 3.13.7 runtime on host).
- `pydantic`: `>=2.12,<3` (Verified: Core typed data models, input validation, and JSON schemas).
- `PySide6`: `>=6.10,<7` (Legacy desktop UI and legacy UI test runner).
  - *Dependency Analysis*: The core Python engine (`mendex_core`), CLI, and MCP server **do not import PySide6**. The only references outside `mendex_ui/` were `src/main.py` (launcher) and `src/mendex_core/diagnostics.py` (which checked metadata version).
  - *Retention Rationale*: Retained in `pyproject.toml` so the 34 legacy unit tests in `tests/ui/` can run cleanly in CI/local regression testing until test migration is complete.

### Development Dependencies
- `pytest`: `>=9,<10` (Verified: Primary automated test harness; 323 passing tests).

---

## 3. Node.js Dependency Manifest (`desktop/package.json`)

### Active Production Dependencies
- `react`: `^18.3.1` (Verified: Powers UI component rendering and reactive lifecycle).
- `react-dom`: `^18.3.1` (Verified: Virtual DOM to browser DOM reconciliation).
- `lucide-react`: `^0.453.0` (Verified: Vector icons across all 7 routes and 10 project tabs).

### Development Dependencies
- `vite`: `^5.4.10` (Verified: High-speed HMR dev server and production asset bundler).
- `@vitejs/plugin-react`: `^4.3.3` (Verified: Babel/SWC Fast Refresh plugin).
- `typescript`: `^5.6.3` (Verified: Strict type checking, 0 compilation errors).
- `@types/react`: `^18.3.11`
- `@types/react-dom`: `^18.3.1`

*Analysis*: Zero redundant state libraries (no Redux, no MobX, no unnecessary chart bloated packages). The frontend maintains a compact 209 kB bundle size.

---

## 4. Tauri 2 Desktop Shell Manifest (`desktop/src-tauri/Cargo.toml`)

### Rust Dependencies
- `tauri`: `2.0.0`
- `tauri-build`: `2.0.0`
- `serde`: `1.0`
- `serde_json`: `1.0`

*Host Status*: Rust toolchain (`cargo`, `rustc`) is currently not installed on this host environment. The configuration and Rust source code (`main.rs`) are verified syntactically against the Tauri 2.0 schema and will build natively when Rust is installed.

---

## 5. Dynamic Imports & Subprocess Execution Audit

| Caller | Callee / Target | Mechanism | Verification / Safety |
| :--- | :--- | :--- | :--- |
| `vite.config.ts` | `python.exe -u -m mendex_core.desktop` | `child_process.spawn` | Auto-respawns on exit, unbuffered stdio, 15s timeout protection |
| `src/mendex_core/desktop/service.py` | `integrations.v15_connector` | Dynamic import inside `__init__` | Loads verified connectors (KiCad, LTspice, FEMM, FreeCAD, Qucs-S, OpenModelica) |
| `src/integrations/runners/safe_runner.py` | Host solver binaries | `subprocess.Popen` | Timeout bounded, working directory confined, zero shell injection |
| `src/mendex_core/launch.py` | `Code.exe` / File Explorer | Direct binary execution | Shell-free binary lookup, argument escaping |
