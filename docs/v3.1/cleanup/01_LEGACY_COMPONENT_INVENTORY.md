# 01 Legacy Component Inventory — Mendex Engineering Studio v3.1

## Executive Summary
This document provides a static and dynamic audit of all software components in the Mendex Engineering Studio repository as part of the transition to the **Codex-First Engineering Architecture**.

### Target Architecture Boundary
- **Orchestration**: VS Code + Codex / Claude Code / Antigravity with Generic Engineering Workflow Prompts (`engineering-workflows/`).
- **Control Interface**: Mendex CLI (`mendex_core.cli`) and MCP Server (`mendex_core.mcp.server`).
- **Engineering Core**: Authoritative Python backend (`mendex_core`), SQLite persistence (`studio.sqlite3`), and deterministic calculations.
- **External Solvers**: Local headless runners for LTspice XVII, FEMM 4.2, KiCad 10, FreeCAD, Qucs-S, and OpenModelica.
- **Presentation & Monitoring**: Modern React + TypeScript + Vite desktop command center (`desktop/`) with Tauri 2 shell support.

---

## Component Classification Matrix

| File Path | Component Name | Current Responsibility | Dependencies | Target Architecture Role / Replacement | Classification | Proposed Action | Risk Level | Test Evidence |
| :--- | :--- | :--- | :--- | :--- | :---: | :--- | :---: | :--- |
| `src/mendex_core/service.py` | `StudioService` | Authoritative application service & persistence root | SQLite, `models`, `paths` | Core authoritative service | **KEEP** | Maintain as single source of truth | None | `tests/core/test_service.py` |
| `src/mendex_core/controller.py` | `MendexEngineeringController` | High-level engineering facade & lifecycle coordinator | `StudioService`, calculations | Primary Python engineering facade | **KEEP** | Maintain single core service | None | `tests/core/test_v21_controller.py` |
| `src/mendex_core/cli.py` | CLI Entrypoint | Command-line interface for human & agent commands | `MendexEngineeringController` | Authoritative CLI | **KEEP** | Maintain CLI consistency | Low | `tests/core/test_v21_cli.py` |
| `src/mendex_core/mcp/server.py` | MCP Server | Model Context Protocol agent tool execution server | `MendexEngineeringController` | Authoritative Agent MCP | **KEEP** | Maintain MCP tool schema parity | Low | `tests/core/test_v21_mcp.py` |
| `src/mendex_core/desktop/service.py` | `DesktopService` | Stdio RPC presentation bridge for React command center | `StudioService`, `v15_connector` | Web/Tauri stdio RPC gateway | **KEEP** | Maintain dual-stack RPC bridge | Low | Headless Edge verification & RPC tests |
| `src/mendex_core/desktop/__main__.py` | Desktop Transport Main | Standalone JSON-lines stdio process runner | `DesktopService` | Stdio subprocess entry | **KEEP** | Maintain `-u` unbuffered bridge | Low | Vite bridge live connection |
| `src/mendex_core/engineering_lifecycle/` | `EngineeringLifecycleService` | Canonical 9-stage engineering lifecycle engine | `storage.py`, `models.py` | Canonical 9-stage lifecycle | **KEEP** | Authoritative lifecycle engine | Low | `tests/core/test_engineering_lifecycle.py` |
| `src/mendex_core/engineering_records/` | `EngineeringRecordService` | Append-only engineering artifact & calculation store | `storage.py`, `models.py` | Cryptographic evidence registry | **KEEP** | Authoritative evidence log | Low | `tests/core/test_engineering_records.py` |
| `src/mendex_core/intelligence/calculations.py`| `DeterministicCalculationService` | Sizing, Dowell $F_r$, Steinmetz, IEC creepage | `math`, `numpy` | Deterministic sizing math | **KEEP** | Single core math engine | None | `tests/adapters/test_calculations.py` |
| `src/integrations/calculations/` | Math modules (`power_losses`, etc.) | First-principles analytical formulas | `math` | Core calculation algorithms | **KEEP** | Shared formula library | None | `tests/adapters/test_calculations.py` |
| `src/integrations/v15_connector.py` | `V15ConnectorRegistry` | Host solver execution adapters (LTspice, FEMM, KiCad) | `SafeRunner`, host binaries | Host solver adapter registry | **KEEP** | Local solver runners | Low | `tests/adapters/test_v15_connector.py` |
| `desktop/src/` | React Web Command Center | Modern read-only engineering monitoring center | React 18, Vite 5, Lucide | Official Command Center | **KEEP** | Primary desktop UI | Low | `npm run build` (0 errors) |
| `desktop/src-tauri/` | Tauri 2 Desktop Shell | Native Windows packaging and webview container | Rust, Cargo, Tauri 2 | Native desktop distribution | **KEEP** | Build when Rust toolchain present | Low | Config verified against v2 schema |
| `engineering-workflows/` | Generic 9-Stage Prompts | Autonomous Codex engineering execution playbooks | Markdown templates | Codex workflow playbooks | **KEEP** | Primary engineering instructions | Low | Handbook & prompt tests |
| `src/mendex_ui/workflow_canvas/` | `WorkflowStudioPanel` & canvas | Abandoned drag-and-drop node graph canvas | PySide6 GraphicsScene | Removed in v3.1 Codex architecture | **REMOVE** | Safe deprecation/removal | Low | Not imported by any core or main window |
| `src/mendex_ui/first_run_wizard.py` | `FirstRunWizardDialog` | Legacy v2.0 onboarding dialog | PySide6 | Replaced by React / Settings | **REMOVE** | Verified unreferenced | None | 0 imports across codebase |
| `src/mendex_ui/design_studio_panel.py` | `EngineeringDesignStudioPanel` | Legacy manual CAD creation form | PySide6 | Replaced by Codex CAD prompts | **REMOVE** | Deprecate manual CAD UI | Low | Replaced by KiCad/FreeCAD generators |
| `src/mendex_ui/window.py` & core panels | PySide6 Desktop GUI | Legacy Qt desktop application | PySide6 | Temporary fallback desktop | **MIGRATE** | Preserve as test/fallback until Tauri | Medium | 34 `tests/ui/` unit tests |
| `src/main.py` | Qt Desktop Launcher | Legacy `python src/main.py` entrypoint | `mendex_ui.__main__` | `start_desktop.bat` (React) | **REFACTOR** | Route to modern desktop or fallback | Low | Launcher script verification |
| Root temporary files (`dump.html`, etc.) | Debug artifacts | Ad-hoc headless DOM dumps & test snapshots | None | Brain artifact directory | **REMOVE** | Safe cleanup | None | Git status cleanliness |

---

## Summary of Actions
- **KEEP**: All `mendex_core` services, `controller`, `cli`, `mcp`, `desktop` bridge, `integrations`, calculation math, and React command center.
- **REFACTOR**: `src/main.py` and documentation links to point primarily to the modern Command Center while maintaining transparent fallback.
- **REMOVE**: Unreferenced legacy drag-and-drop workflow canvases (`src/mendex_ui/workflow_canvas/`), dead onboarding wizard (`first_run_wizard.py`), and transient debug files.
- **MIGRATE / PRESERVE**: Retain `src/mendex_ui/` core panels exclusively to preserve the 34 legacy unit tests until full test migration to React/Playwright is scheduled, adhering to the mandatory rule: *"Do not blindly delete files. Preserve all functional engineering capabilities."*
