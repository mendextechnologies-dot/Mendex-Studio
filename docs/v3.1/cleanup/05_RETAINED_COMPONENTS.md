# 05 Retained Components Log — Mendex Engineering Studio v3.1

This document specifies the core architecture components retained in Mendex Engineering Studio v3.1, along with the technical justification and test evidence for their retention.

---

## Retained Core Subsystems

### 1. Authoritative Python Engineering Core (`src/mendex_core/`)
- **Components**: `StudioService`, `MendexEngineeringController`, `models.py`, `evidence.py`, `paths.py`, `integration_service.py`, `pcb.py`, `launch.py`, `diagnostics.py`.
- **Architectural Role**: The single authoritative engineering service managing SQLite persistence (`.mendex/studio.sqlite3`), immutable revision archiving, specification hashing, and tool execution orchestration.
- **Why Retained**: Mandatory foundational core. Neither the CLI, MCP server, nor desktop clients maintain business logic or database access independently of this core service.
- **Test Evidence**: 159 tests in `tests/core/` and 76 tests in `tests/integration/` passing.

---

### 2. Canonical 9-Stage Engineering Lifecycle (`src/mendex_core/engineering_lifecycle/`)
- **Components**: `EngineeringLifecycleService`, `api.py`, `models.py`, `service.py`, `storage.py`.
- **Architectural Role**: Implements the v3.1 generic 9-stage engineering definition (`engineering`, v3.1.0) with explicit revision enrollment, append-only review stage transitions, and human gate sign-off tracking.
- **Why Retained**: Provides the authoritative lifecycle progression backing both the CLI/MCP tools and the React Command Center Lifecycle timeline.
- **Test Evidence**: `tests/core/test_engineering_lifecycle.py` and `tests/integration/test_engineering_lifecycle_interfaces.py` passing.

---

### 3. Append-Only Engineering Records & Evidence (`src/mendex_core/engineering_records/`)
- **Components**: `EngineeringRecordService`, `calculations.py`, `models.py`, `service.py`, `storage.py`.
- **Architectural Role**: Cryptographic registry for requirement snapshots, deterministic calculations, registered CAD artifacts, and formal verification dossiers.
- **Why Retained**: Guarantees zero fabrication and immutable auditability under Section 8 of the engineering guidelines.
- **Test Evidence**: `tests/core/test_engineering_records.py` and `tests/integration/test_engineering_record_interfaces.py` passing.

---

### 4. Deterministic Physical Calculation Services (`src/mendex_core/intelligence/` & `src/integrations/calculations/`)
- **Components**:
  - `DeterministicCalculationService`: Sizing calculations, Dowell $F_r$, Steinmetz core losses, IEC 60664-1 / IEC 61010-1 creepage/clearance, IPC-9592B derating.
  - `power_losses.py`: Conduction, switching, and Steinmetz volumetric dissipation equations.
  - `winding_losses.py`: Temperature-corrected skin depth and Dowell 1D AC resistance factors.
  - `transformer_design.py`: Closed-form flyback and forward magnetic turns sizing.
- **Why Retained**: Authoritative mathematical formulas that cannot be modified or replaced without explicit engineering re-qualification.
- **Test Evidence**: `tests/adapters/test_calculations.py` and `tests/adapters/test_magnetics.py` passing.

---

### 5. Local Solver Connectors (`src/integrations/v15_connector.py`)
- **Components**: `V15ConnectorRegistry`, `LTspiceV15Connector`, `FEMMV15Connector`, `KiCadCLIConnector`, `FreeCADConnector`, `QucsSConnector`, `OpenModelicaConnector`, `PythonConnector`, `GitConnector`, `SafeRunner`.
- **Architectural Role**: Safe, sandboxed headless runners that discover local host binaries, stage execution inputs in revision-relative folders, invoke solvers without shell expansion, and parse execution outputs.
- **Why Retained**: Provides real physical simulation execution for LTspice XVII, FEMM 4.2 Lua, KiCad ERC/DRC, and FreeCAD STEP generation.
- **Test Evidence**: `tests/adapters/test_v15_connector.py`, `tests/adapters/test_ltspice_adapter.py`, `tests/adapters/test_femm_adapter.py` passing.

---

### 6. Modern Web Command Center (`desktop/`)
- **Components**: React 18, TypeScript, Vite 5, Lucide icons, Dark CSS tokens (`desktop/src/`), Tauri 2 config (`desktop/src-tauri/`).
- **Architectural Role**: Read-only engineering visualization command center running on `http://localhost:5173`. Reflects SQLite and workspace filesystem state in real time via dual-stack stdio RPC bridge to `python.exe -u -m mendex_core.desktop`.
- **Why Retained**: Official v3.1 command center replacing legacy UI interfaces.
- **Test Evidence**: `npm run build` compiling in 1.78s with 0 errors; live headless browser DOM verification.

---

### 7. Generic 9-Stage AI Workflow Prompts (`engineering-workflows/stages/`)
- **Components**: Stage 1 through Stage 9 Markdown prompts and validation templates.
- **Architectural Role**: Standardized, copy-paste prompts for OpenAI Codex, Claude Code, and Antigravity to guide autonomous power electronics engineering workflows.
- **Why Retained**: Primary orchestration layer driving the entire v3.1 architecture.
- **Test Evidence**: `tests/core/test_engineering_prompt_library.py` passing.

---

### 8. PySide6 Legacy UI Panels (`src/mendex_ui/` — Transitional Preservation)
- **Components**: `ProductEngineeringOverviewPanel`, `ComponentLibraryPanel`, `SimulationCenterPanel`, `SettingsPanel`, `PCBPanel`, `Window.py`.
- **Architectural Role**: Preserved as a transitional secondary interface and test target while native Tauri 2 desktop compilation is awaiting host Rust toolchain installation.
- **Why Retained**: Prevents breaking the 34 automated UI unit tests in `tests/ui/` and provides a guaranteed desktop fallback on hosts without a web browser.
- **Test Evidence**: 34 unit tests in `tests/ui/` passing.
