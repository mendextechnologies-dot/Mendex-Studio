# MENDEX ENGINEERING STUDIO v1.9 — VISUAL WORKFLOW CONTRACTS

## 1. Graph Data Model & Port Types

Mendex Visual Workflow Studio operates on typed directed acyclic graphs (DAGs):

- **Node Types**:
  - `Input`: `numeric_input`, `text_input`, `parameter_input`, `dataset_reference`.
  - `Calculation`: `formula_evaluation`, `unit_conversion`, `area_product_sizing`, `steinmetz_core_loss`, `dowell_ac_resistance`.
  - `Tool`: `ltspice_simulation`, `femm_magnetics`, `kicad_erc`, `kicad_drc`, `freecad_solid`.
  - `Validation`: `threshold_comparator`, `range_check`, `ripple_check`.
  - `Reporting`: `report_generator`, `dossier_generator`.
- **Port Data Types**:
  - `SCALAR`: Dimensionless or raw numeric value.
  - `QUANTITY`: Magnitude coupled with explicit SI unit (e.g. `24.0 V`, `100.0 kHz`).
  - `NETLIST`: SPICE circuit netlist text.
  - `WAVEFORM`: Array of time-series voltage/current points.
  - `FILE_REF`: Cryptographically verified filesystem path.
  - `VERDICT`: Boolean PASS/FAIL decision with reason.
