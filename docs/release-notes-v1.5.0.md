# Mendex Engineering Studio — Release Notes v1.5.0

**Release Date:** November 10, 2026  
**Baseline:** v1.3 Foundation, v1.4 18-Tool Inventory, v1.5 Two-Agent Execution Model  
**Platform Target:** Windows 10/11 (Local-First Desktop Application)  
**Branch:** `main`

---

## Executive Summary

Mendex Engineering Studio v1.5.0 delivers the full two-agent execution plan:
1. **Core Studio & Extensibility (Codex workstream):** Unified PySide6 desktop interface with 14 modular navigation views, additive SQLite v4 persistence, generic integration workspaces, non-blocking job execution engine with cooperative cancellation, artifact and evidence browser with hash verification, and truth-preserving catalog/settings.
2. **Tool Connectors & Loss Analytics (Antigravity workstream):** Universal V15 connector suite covering all 18 approved tools/resources, sandboxed `SafeSubprocessRunner`, native script generators (FEMM 4.2 Lua, FreeCADCmd bobbin, OpenModelica `.mos`), canonical research datasets (SwitchLossDB, MagNet Steinmetz loss benchmarks), and analytical calculations (Flyback transformer design, Dowell AC winding resistance, semiconductor switching/conduction losses).
3. **Interactive Engineering Workbenches:** Live GUI panels for high-frequency transformer sizing, power semiconductor selection with SwitchLossDB integration, and DC-DC converter simulation script export, fully linked to active revision specifications.

All work conforms strictly to engineering integrity guidelines: no fabricated solver outputs, unavailable tools remain truthfully labeled `NOT_INSTALLED` / `OPTIONAL_UNLICENSED`, and unverified checks remain `NOT_EVALUATED`.

---

## Key Capabilities & Enhancements

### 1. Interactive Engineering Modules
- **Transformer & Magnetics Panel:**
  - Analytical Flyback core sizing ($N_p, N_s, L_m, I_{pk}, I_{rms}, l_g$) based on $V_{in}, V_{out}, I_{out}, f_{sw}, B_{max}, A_e$.
  - Dowell high-frequency AC winding loss calculator computing temperature-dependent skin depth $\delta$ and AC-to-DC resistance factor $F_R = R_{ac}/R_{dc}$.
  - Direct export of native FEMM 4.2 Lua simulation scripts and FreeCAD STEP bobbin scripts.
- **Power Semiconductor Loss Panel:**
  - Integrated `SwitchLossDB` preset device picker (e.g., Wolfspeed SiC MOSFETs).
  - Analytical calculation of conduction loss ($P_{cond} = I_{rms}^2 \cdot R_{ds(on)} \cdot D$) and switching loss ($P_{sw} = (E_{on} + E_{off}) \cdot f_{sw}$).
- **DC–DC Converter Panel:**
  - Modelica transient simulation generator exporting headless `.mos` scripts for OpenModelica.
- **Revision Synchronization:**
  - All workspace panels automatically synchronize inputs ($V_{in}, V_{out}, I_{out}, f_{sw}$) from the active product revision specification.

### 2. Universal 18-Tool Integration & Safe Subprocess Runner
- **Verified Local Tools:**
  - **LTspice 26.1.1.0:** Headless simulation execution via safe CLI arguments (`-b -ascii`), netlist discovery, automated log and `.raw` output capture.
  - **Python 3.13.7:** Execution sandbox for mathematical modeling and script execution.
  - **Git 2.45.2:** Revision tracking, hash verification, and workspace integrity checks.
- **Research Datasets:**
  - `SwitchLossDB`: Ingestion of device parameters from structured CSV fixtures.
  - `MagNet Dataset`: Steinmetz core loss evaluation ($P_v = k f^\alpha B^\beta$) and ML benchmark fixtures.
- **Native Solvers (Generators & Connectors):**
  - FEMM 4.2, FreeCADCmd, OpenModelica, KiCad, Qucs-S, Jupyter, and commercial stubs (Ansys Maxwell, Ansys Icepak, SolidWorks, MATLAB/Simulink, PLECS).
- **Subprocess Safety:**
  - `SafeSubprocessRunner` with `shell=False`, argument list validation, process-tree termination (`taskkill /T /F`), isolated temporary working directories, and chunked SHA-256 artifact hashing.

### 3. Architecture & Persistence
- **Additive SQLite v4 Migration:**
  - Preserves 100% backward compatibility with v1-v3 tables.
  - Added `integration_jobs`, `job_artifacts`, `external_datasets`, and `tool_settings`.
- **Navigation Invariant Maintained:**
  - Preserved exactly 14 navigation screens in `StudioWindow`, wrapping module workspaces seamlessly without breaking existing UI tests.

---

## Verification & Test Results

| Test Category | Suite / File | Status | Duration |
|---|---|---|---|
| Calculation Engines | `tests/adapters/test_calculations.py` | 3 Passed | < 0.1s |
| Commercial Stubs | `tests/adapters/test_commercial_stubs.py` | 1 Passed | < 0.1s |
| Research Datasets | `tests/adapters/test_datasets.py` | 5 Passed | < 0.2s |
| Script Generators | `tests/adapters/test_generators.py` | 3 Passed | < 0.1s |
| LTspice Adapter | `tests/adapters/test_ltspice_adapter.py` | 3 Passed | 0.8s |
| Magnetics Solvers | `tests/adapters/test_magnetics.py` | 4 Passed | < 0.1s |
| Safe Subprocess Runner | `tests/adapters/test_safe_runner.py` | 5 Passed | 0.5s |
| Security & Bounds | `tests/adapters/test_security_and_limits.py` | 4 Passed | < 0.1s |
| Tool Detection & Registry | `tests/adapters/test_tool_detection.py` | 4 Passed | < 0.1s |
| Universal V15 Connectors | `tests/adapters/test_v15_connector.py` | 4 Passed | < 0.1s |
| Shared Contracts | `tests/contracts/test_v15_contracts.py` | 8 Passed | < 0.1s |
| Core Service & Persistence | `tests/core/` (completion, day2, service) | 22 Passed | 0.8s |
| Integration & Jobs | `tests/integration/` (day3, restore, jobs) | 18 Passed | 6.5s |
| UI & Workspace Panels | `tests/ui/` (window, v15_panels, workspace_panels) | 6 Passed | 1.8s |
| **Total Automated Tests** | `pytest` | **90 Passed** | **10.17s** |

### Smoke Test Evidence
- `scripts/desktop_smoke.py`: Seven desktop UI screenshots captured under `.mendex/qa`.
- `scripts/v15_codex_smoke.py`: Synthetic UI workflow verified; screenshots saved under `.mendex/qa/v15-codex`.

---

## Release Artifacts & Traceability
- [`docs/audits/MASTER_IMPLEMENTATION_AUDIT.md`](file:///c:/Mendex%20studio/docs/audits/MASTER_IMPLEMENTATION_AUDIT.md)
- [`docs/audits/REQUIREMENTS_TRACEABILITY_MATRIX.md`](file:///c:/Mendex%20studio/docs/audits/REQUIREMENTS_TRACEABILITY_MATRIX.md)
- [`docs/audits/TOOL_INTEGRATION_AUDIT.md`](file:///c:/Mendex%20studio/docs/audits/TOOL_INTEGRATION_AUDIT.md)
- [`docs/audits/IMPLEMENTATION_GAPS.md`](file:///c:/Mendex%20studio/docs/audits/IMPLEMENTATION_GAPS.md)
- [`docs/audits/NEXT_ACTION_PLAN.md`](file:///c:/Mendex%20studio/docs/audits/NEXT_ACTION_PLAN.md)
- [`docs/TOOL_COMPATIBILITY.md`](file:///c:/Mendex%20studio/docs/TOOL_COMPATIBILITY.md)
