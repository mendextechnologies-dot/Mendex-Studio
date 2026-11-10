# Mendex Engineering Studio v1.9 — Node Contracts & Port Specifications

## 1. Overview

This document specifies the typed data contracts, port definitions, and execution behaviors for all node categories in Mendex Engineering Studio v1.9 (`src/mendex_core/workflows/`).

---

## 2. Port Data Types & Compatibility

| Port Data Type | Description | Python Underlying Type | Compatible Target Types |
|---|---|---|---|
| `SCALAR` | Single numeric value | `float` or `int` | `SCALAR`, `QUANTITY`, `STRING`, `ANY` |
| `QUANTITY` | Value with physical unit | `QuantityValue(value, unit)` | `QUANTITY`, `SCALAR`, `STRING`, `ANY` |
| `BOOLEAN` | True / False condition | `bool` | `BOOLEAN`, `STRING`, `ANY` |
| `STRING` | Text string / netlist | `str` | `STRING`, `ANY` |
| `VECTOR` | Array of numbers | `list[float]` | `VECTOR`, `ANY` |
| `TIME_SERIES` | Waveform signals & timestamps | `TimeSeriesData(time, signals, units)` | `TIME_SERIES`, `ANY` |
| `FILE_REF` | Local file reference & SHA256 | `FileReference(path, filename, sha256)` | `FILE_REF`, `ARTIFACT`, `ANY` |
| `DATASET_REF` | Registered dataset reference | `DatasetReference(dataset_id, version)` | `DATASET_REF`, `ANY` |
| `SIM_RESULT` | Multi-solver execution output | `SimulationResultData(job_id, tool_id)` | `SIM_RESULT`, `TIME_SERIES`, `ARTIFACT`, `ANY` |
| `ARTIFACT` | Sealed output artifact | `ArtifactData(path, artifact_type, sha256)` | `ARTIFACT`, `ANY` |
| `VALIDATION_RESULT` | Formal engineering check outcome | `ValidationResultData(check_id, passed, ...)` | `VALIDATION_RESULT`, `ANY` |
| `ANY` | Open generic port | Any JSON-serializable structure | All types |

---

## 3. Engineering Unit Canonical Conversion

The `QuantityValue.to_canonical()` method normalizes units to standard SI base dimensions:

- **Frequency**: $\text{kHz} \to \times 10^3\text{ Hz}$, $\text{MHz} \to \times 10^6\text{ Hz}$, $\text{GHz} \to \times 10^9\text{ Hz}$.
- **Voltage**: $\text{mV} \to \times 10^{-3}\text{ V}$, $\text{kV} \to \times 10^3\text{ V}$, $\mu\text{V} \to \times 10^{-6}\text{ V}$.
- **Inductance**: $\mu\text{H} \to \times 10^{-6}\text{ H}$, $\text{mH} \to \times 10^{-3}\text{ H}$, $\text{nH} \to \times 10^{-9}\text{ H}$.
- **Capacitance**: $\mu\text{F} \to \times 10^{-6}\text{ F}$, $\text{nF} \to \times 10^{-9}\text{ F}$, $\text{pF} \to \times 10^{-12}\text{ F}$.
- **Resistance**: $\text{k}\Omega \to \times 10^3\ \Omega$, $\text{m}\Omega \to \times 10^{-3}\ \Omega$, $\text{M}\Omega \to \times 10^6\ \Omega$.
- **Length**: $\text{mm} \to \times 10^{-3}\text{ m}$, $\mu\text{m} \to \times 10^{-6}\text{ m}$, $\text{mil} \to \times 2.54 \times 10^{-5}\text{ m}$.
- **Temperature**: $^\circ\text{C} \to + 273.15\text{ K}$.

Port connection validation checks whether two quantities share identical canonical base dimensions before allowing connection.

---

## 4. Safe AST Expression Evaluation

To guarantee workspace security, expression evaluation in `FormulaEvaluationNode` uses strict Python AST parsing without `eval()`:

- **Allowed Operators**: `+`, `-`, `*`, `/`, `**`, `%`, unary `+`, `-`.
- **Allowed Math Functions**: `sqrt`, `abs`, `sin`, `cos`, `tan`, `exp`, `log`, `log10`, `min`, `max`, `pi`, `e`.
- **Security Rejections**: Attribute access (`.__class__`), import calls (`__import__`), system execution, and file I/O are rejected by AST node type checking and raise immediate `ValueError`.

---

## 5. Complete 7-Category Node Library Catalog

| Category | Node Type | Input Ports | Output Ports | Executable Behavior |
|---|---|---|---|---|
| **Inputs** | `numeric_input` | None | `value` (Scalar), `quantity` (Quantity) | Emits configured scalar or quantity |
| **Inputs** | `text_input` | None | `text` (String) | Emits configured text or netlist |
| **Inputs** | `parameter_input` | None | `name`, `value`, `quantity` | Emits named engineering parameter |
| **Inputs** | `file_input` | None | `file_ref` (FileRef), `text_content` | Reads and hashes local file |
| **Inputs** | `dataset_reference` | None | `dataset_ref` (DatasetRef) | Emits catalog dataset pointer |
| **Calculations** | `formula_evaluation` | `a`, `b`, `c`, `d` (Scalar) | `result` (Scalar), `quantity` | Evaluates safe AST formula |
| **Calculations** | `unit_conversion` | `input_quantity` (Quantity) | `output_quantity`, `output_value` | Converts between compatible units |
| **Calculations** | `deterministic_physics` | `param1`, `param2`, `param3`, `param4` | `result`, `quantity`, `record` | Evaluates Dowell, skin depth, CCM, Steinmetz, LC |
| **Calculations** | `numerical_summary` | `signal` (Any) | `rms`, `pk_pk`, `mean`, `min`, `max` | Computes signal statistics |
| **Tools** | `ltspice_simulation` | `netlist_text`, `netlist_file` | `sim_result`, `waveform`, `log_output` | Headless LTspice batch run |
| **Tools** | `femm_analysis` | `turns`, `current_a`, `script_lua` | `sim_result`, `inductance_h`, `flux_density_t` | Headless FEMM 2D magnetics FEA |
| **Tools** | `kicad_check` | `design_file` (FileRef) | `sim_result`, `violations_count`, `passed` | KiCad CLI schematic/layout check |
| **Tools** | `ngspice_simulation` | `netlist_text` (String) | `sim_result`, `waveform` (TimeSeries) | Qucs-S / ngspice batch simulation |
| **Tools** | `freecad_export` | `core_type` (String) | `sim_result`, `file_ref` (FileRef) | FreeCAD headless 3D STEP export |
| **Results** | `waveform_extract` | `waveform_in` (TimeSeries) | `signal_vector`, `time_vector`, `peak_value` | Extracts named signal trace |
| **Results** | `result_comparison` | `actual`, `reference` | `delta`, `percent_error`, `within_tolerance` | Compares values against baseline |
| **Validation** | `range_validation` | `value_in` (Scalar) | `validation_result`, `passed` | Verifies $min \le x \le max$ |
| **Validation** | `tolerance_comparison` | `actual`, `target` | `validation_result`, `passed` | Verifies relative error $\le \text{tol}\%$ |
| **Validation** | `regulatory_check` | `working_voltage_v`, `actual_clearance_mm` | `validation_result`, `required_clearance_mm` | IEC 62368-1 / IPC-2221B check |
| **Reporting** | `evidence_aggregation` | `check1`, `check2`, `sim_result`, `calculation` | `manifest`, `manifest_sha256`, `all_passed` | Compiles sealed evidence manifest |
| **Reporting** | `report_export` | `manifest` (Any) | `report_path`, `report_artifact` | Generates HTML engineering dossier |
| **Intelligence** | `knowledge_lookup` | None | `material_data`, `resistivity`, `saturation_flux` | TDK N87, SiC, Copper database |
| **Intelligence** | `reasoning_advisor` | `query_text` (String) | `recommended_tool`, `advice_text`, `confidence` | LocalRuleEngine recommendations |
