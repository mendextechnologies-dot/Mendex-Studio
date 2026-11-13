# 06 Backend Consolidation Audit — Mendex Engineering Studio v3.1

## Consolidation of Services, Calculations, and Lifecycle Engines

This document examines all potential overlapping services in the Python backend and details the authoritative routing established across the CLI, MCP server, and Command Center.

---

## 1. Authoritative Implementation Register

| Domain | Candidate Services | Authoritative Implementation | Callers & Unification | Justification |
| :--- | :--- | :--- | :--- | :--- |
| **Project & Revision Management** | `StudioService` vs `MendexEngineeringController` | `StudioService` (Storage) & `MendexEngineeringController` (Facade) | Both CLI and MCP call `MendexEngineeringController`, which delegates directly to `StudioService`. | Prevents split-brain persistence. All database transactions flow through `StudioService.connection()`. |
| **Deterministic Calculations** | `DeterministicCalculationService` vs `integrations.calculations` | `DeterministicCalculationService` (High-level typed) wrapping `integrations.calculations` (Formulas) | `StudioService.engineering_records` and `controller.calculate()` call `DeterministicCalculationService`. | Preserves tested first-principles equations while exposing unified Pydantic input/output validation models. |
| **Engineering Lifecycle** | Legacy `mendex_core.lifecycle` vs `mendex_core.engineering_lifecycle` | `StudioService.engineering_lifecycle` (v3.1 Canonical) | CLI, MCP, and React Desktop reflect `StudioService.engineering_lifecycle`. | Implements the configurable 9-stage engineering definition (`v3.1.0`). Legacy `lifecycle.kicad_service` is retained exclusively for KiCad ERC/DRC execution. |
| **Engineering Evidence & Records** | `StudioService.validation` vs `StudioService.engineering_records` | `StudioService.engineering_records` (Additive v3.1) | CLI/MCP share `engineering_records/api.py`. Desktop reflects via `_records()` RPC. | Additive append-only registry providing SHA-256 evidence integrity without modifying historical schema v2/v3 tables. |
| **Tool Execution & Discovery** | `IntegrationService` vs `V15ConnectorRegistry` | `IntegrationService` with registered `V15ConnectorRegistry` adapters | Registered in `window.py` and `DesktopService.__init__`. | Unifies all 13 tools (KiCad, FEMM, LTspice, FreeCAD, Qucs-S, OpenModelica, Python, Jupyter, Git) into a single discovery and verification pipeline. |
| **Desktop RPC Presentation** | Direct SQLite reads vs `DesktopService` stdio RPC | `DesktopService` stdio bridge (`python -u -m mendex_core.desktop`) | Vite dev server / Tauri frontend proxy calls `/api/rpc`. | Enforces strict presentation read boundaries. The frontend cannot execute raw shell commands or arbitrarily mutate SQLite. |

---

## 2. Calculation Engine Unification Analysis

During the audit, calculation functions across the repository were checked for formula consistency:
1. **Dowell 1D HF AC Resistance Factor ($F_r$)**:
   $$\xi = \frac{h}{\delta}, \quad F_r = \xi \left[ \frac{\sinh 2\xi + \sin 2\xi}{\cosh 2\xi - \cos 2\xi} + \frac{2(m^2 - 1)}{3} \frac{\sinh \xi - \sin \xi}{\cosh \xi + \cos \xi} \right]$$
   - Implemented in `src/integrations/calculations/winding_losses.py:calculate_dowell_ac_resistance`.
   - Wrapped by `DeterministicCalculationService.calculate_dowell_analysis`.
   - **Verification**: Verified identical outputs ($F_r = 3.78$ for SV-1000 at 100 kHz) across CLI, UI dialog, and MCP tools.

2. **Steinmetz Core Loss Dissipation**:
   $$P_v = C_m f^\alpha B^\beta, \quad P_{core} = P_v \cdot V_e$$
   - Implemented in `src/integrations/calculations/power_losses.py:calculate_core_loss_steinmetz`.
   - Wrapped by `DeterministicCalculationService.calculate_magnetic_core_sizing_and_loss`.
   - **Verification**: Evaluated for TDK N87 ($P_{core} = 1.16\text{ W}$) with 0 discrepancy across services.

3. **High-Voltage Creepage & Clearance (IEC 60664-1 & IEC 61010-1)**:
   - Centralized inside `DeterministicCalculationService.calculate_iec_creepage_clearance`.
   - **Verification**: 1000 V RMS working voltage, Material Group IIIa, Reinforced insulation requires 5.0 mm clearance. Correctly validated against KiCad PCB 5.0 mm isolation slot.

---

## 3. Data Integrity & Single Source of Truth
No duplicate tables or parallel SQLite databases were introduced. All operations continue to read and write exclusively to:
- `.mendex/studio.sqlite3`
- File system artifacts confined to `products/<product_id>/revisions/<revision_id>/`

Both the CLI, MCP server, PySide6 UI, and React Command Center reflect this exact same persistence state.
