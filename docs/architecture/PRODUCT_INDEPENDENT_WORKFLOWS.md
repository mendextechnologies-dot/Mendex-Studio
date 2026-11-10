# PRODUCT-INDEPENDENT ENGINEERING WORKFLOWS
## Functional Verification & Acceptance Paths for General-Purpose Engineering

### 1. Mandatory Acceptance Scenario (v1.7 Specification Section 4)

An engineer must be able to perform the following complete engineering loop without ever creating or selecting a product:

1. **Launch Studio:** Open Mendex Engineering Studio without any required product prompts.
2. **Create Workspace:** Create a generic engineering workspace named `HighFrequency-Magnetic-Study` with local storage directory.
3. **Execute Simulation / CAD / FEA:**
   - Launch **LTspice / ngspice** on a circuit netlist; obtain real transient `.raw` waveform data.
   - Run **FEMM 4.2** 2D finite-element magnetic simulation; calculate inductance and flux density.
   - Run **FreeCAD 1.1.4** to parametrically generate a 3D STEP bobbin model.
   - Run **KiCad 10.0.7** CLI to perform ERC / DRC schematic & PCB checks.
   - Run **OpenModelica 1.26.3** to perform Modelica model checks and behavioral simulation.
4. **Inspect Results:** View generated logs, cryptographic SHA-256 manifests, extracted numeric metrics, and visual artifacts.
5. **Consult AI Assistant:** Ask the AI Engineering Assistant to explain simulation results or optimize winding wire gauge within the active workspace.
6. **Generate Report:** Export a verified engineering report detailing tool executions, input parameters, and output metrics.
7. **Save and Reopen:** Close and reopen the workspace, verifying full state persistence.
8. **Optional Product Link:** Downstream, optionally link this completed engineering activity or workspace to an existing or new Product record without loss of history or recalculation.

---

### 2. Verification Flow Matrix

| Engineering Action | Tool Used | Product Required? | Verified Output Artifact | Test Reference |
| :--- | :--- | :--- | :--- | :--- |
| **Circuit Simulation** | LTspice / ngspice | **NO** | `circuit.raw`, `circuit.log`, RMS/Vpeak metrics | `test_ltspice_adapter.py`, `test_ngspice_adapter.py` |
| **Magnetic FEA** | FEMM 4.2 | **NO** | `temp_transformer.ans`, `results.txt`, inductance | `test_femm_adapter.py` |
| **3D CAD Bobbin** | FreeCAD 1.1.4 | **NO** | `bobbin.step`, SHA-256 hash | `test_workspace_panels.py` |
| **PCB & Schematic Check** | KiCad 10.0.7 | **NO** | `drc_report.json`, violation counts | `test_kicad_adapter.py` |
| **System Modelica Sim** | OpenModelica 1.26.3 | **NO** | `check.mos`, equation balance output | `test_openmodelica_adapter.py` |
| **Semiconductor Losses** | SwitchLossDB | **NO** | Eon/Eoff curve interpolation, Conduction loss | `test_datasets.py`, `test_calculations.py` |
| **Core Loss Lookup** | MagNet Dataset | **NO** | Steinmetz $k, \alpha, \beta$ multi-material loss | `test_magnetics.py` |
| **Standalone Reporting** | Studio Report Engine | **NO** | `report.json`, `report.html` with SHA-256 manifest | `test_v16_workflow.py` |
