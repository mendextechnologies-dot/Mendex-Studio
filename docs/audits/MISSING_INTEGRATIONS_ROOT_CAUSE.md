# Root Cause Analysis: Missing Integrations on the Engineering Dashboard

**Document ID**: `RCA-DASH-18-20261110-01`  
**Severity**: High (Inventory Visibility Discrepancy)  
**Status**: Resolved in Baseline `v1.9-visual-workflow-studio`  
**Affected Component**: `src/mendex_ui/v17_panels.py` (`EnterpriseDashboardPanel`)

---

## 1. Problem Statement

The approved Mendex Engineering Studio specification defines an ecosystem of **18 engineering tools, platforms, datasets, and research benchmarks**. However, the modern executive Engineering Operations Dashboard (`EnterpriseDashboardPanel`) previously displayed only **10 entries** in its "Native Engineering Solvers & Frameworks" table.

This created a discrepancy where 8 approved items appeared absent from the platform dashboard, and additional native integrations (such as `ngspice`) were not surfaced.

---

## 2. Root Cause Analysis & Code References

Our investigation revealed that the discrepancy was **not** caused by missing backend contracts or dropped repository adapters, but rather by **hardcoded UI presentation lists and architectural compartmentalization**:

### A. Hardcoded UI Array in `EnterpriseDashboardPanel`
- **Location**: [`src/mendex_ui/v17_panels.py:169-180`](file:///c:/Mendex%20studio/src/mendex_ui/v17_panels.py)
- **Defect**: The `refresh_metrics()` method contained an explicit hardcoded list named `core_tools` with exactly 10 tuples:
  ```python
  core_tools = [
      ("ltspice", "LTspice"),
      ("kicad", "KiCad CLI"),
      ("femm", "FEMM 4.2"),
      ("freecad", "FreeCAD"),
      ("qucs-s", "Qucs-S"),
      ("openmodelica", "OpenModelica"),
      ("python", "Python Math"),
      ("git", "Git"),
      ("plecs", "PLECS"),
      ("matlab-simulink", "MATLAB"),
  ]
  ```
- **Consequence**: The dashboard iterated solely over these 10 entries, completely ignoring the remaining 8 registered tools and datasets.

### B. Compartmentalization of Datasets and Commercial Tools
1. **Research Datasets & Benchmarks**:
   - `switchlossdb`, `magnet-dataset`, `magnet-ml-benchmarks`, `magnet-princeton` were fully cataloged in [`src/mendex_core/config/integration_catalog.json`](file:///c:/Mendex%20studio/src/mendex_core/config/integration_catalog.json) and rendered in `DatasetPanel` (Page 13). However, they were omitted from the primary dashboard because the author of `EnterpriseDashboardPanel` originally intended the table to show only "native solvers".
2. **Commercial Tool Stubs**:
   - `ansys-maxwell`, `ansys-icepak`, and `solidworks` were defined in `integration_catalog.json` and `commercial_stubs.py`, but were omitted from the dashboard's `core_tools` list while `plecs` and `matlab-simulink` were included arbitrarily.
3. **Interactive Developer Tools**:
   - `jupyter` was registered in `ToolRegistry` and detected in `.venv\Scripts\jupyter.exe`, but omitted from the 10-item list.
4. **Discovered Solvers**:
   - `ngspice` had a full adapter in `src/integrations/adapters/ngspice.py` and was installed on the machine, but was absent from `integration_catalog.json` (frozen at 18 entries) and not listed on the dashboard.

---

## 3. Discrepancy Resolution Breakdown

| Missing Item | Original Reason | Remediation |
|---|---|---|
| `switchlossdb` | Omitted from UI `core_tools` array; isolated to `DatasetPanel`. | Added to `INVENTORY_DEFINITIONS` with category `Research datasets` and status `REGISTERED ONLY`. |
| `magnet-dataset` | Omitted from UI `core_tools` array; isolated to `DatasetPanel`. | Added to `INVENTORY_DEFINITIONS` with category `Research datasets` and status `REGISTERED ONLY`. |
| `magnet-ml-benchmarks` | Omitted from UI `core_tools` array; isolated to `DatasetPanel`. | Added to `INVENTORY_DEFINITIONS` with category `Benchmark resources` and status `REGISTERED ONLY`. |
| `magnet-princeton` | Omitted from UI `core_tools` array; isolated to `DatasetPanel`. | Added to `INVENTORY_DEFINITIONS` with category `Research datasets` and status `REGISTERED ONLY`. |
| `jupyter` | Omitted from UI `core_tools` array. | Added to `INVENTORY_DEFINITIONS` with category `Development tools` and status `INSTALLED — NOT VALIDATED`. |
| `ansys-maxwell` | Omitted from UI `core_tools` array. | Added to `INVENTORY_DEFINITIONS` with category `Commercial integrations` and status `LICENSE REQUIRED`. |
| `ansys-icepak` | Omitted from UI `core_tools` array. | Added to `INVENTORY_DEFINITIONS` with category `Commercial integrations` and status `LICENSE REQUIRED`. |
| `solidworks` | Omitted from UI `core_tools` array. | Added to `INVENTORY_DEFINITIONS` with category `Commercial integrations` and status `LICENSE REQUIRED`. |
| `ngspice` | Native solver omitted from catalog & dashboard. | Added to `INVENTORY_DEFINITIONS` with category `Simulation solvers` and status `VERIFIED OPERATIONAL`. |

---

## 4. Architectural Corrective Actions Implemented

1. **Ecosystem Inventory Definition**:
   Created `INVENTORY_DEFINITIONS` in [`src/mendex_ui/v17_panels.py`](file:///c:/Mendex%20studio/src/mendex_ui/v17_panels.py) containing all 18 approved items plus `ngspice` (19 total entries), with complete metadata: identifier, display name, category, license model, supported operations, and host/remote locations.

2. **Dashboard Table Redesign**:
   - Expanded table from 4 to 7 columns (`Resource Name`, `Category`, `Status`, `Version`, `License`, `Capabilities`, `Discovered Location / Source`).
   - Integrated real-time search filtering (`search_filter`) and category/status combo boxes.
   - Wired double-click row actions to navigate seamlessly to Simulation Lab, Tool Center, or Dataset Catalog.

3. **Truthful KPI Metrics**:
   - Replaced misleading static claims with live counts:
     - `ACTIVE WORKSPACES`: Live count from database
     - `VERIFIED OPERATIONAL`: `4 / 19` (Automated verification passing)
     - `INSTALLED ON HOST`: `10 / 19` (Discovered native binaries)
     - `ECOSYSTEM INVENTORY`: `19 Resources` (18 Approved + ngspice)

4. **Global Command Palette Synchronization**:
   Updated `_init_search_completer()` in [`src/mendex_ui/window.py`](file:///c:/Mendex%20studio/src/mendex_ui/window.py) to index all 19 resources in the `Ctrl+K` palette.
