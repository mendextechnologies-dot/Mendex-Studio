# Mendex Engineering Studio — Complete 18-Resource Integration Audit & Ecosystem Inventory

**Document ID**: `AUD-18-RES-20261110-01`  
**Classification**: Enterprise Platform Engineering Audit  
**Audited Baseline**: Branch `v1.9-visual-workflow-studio`  
**Host Environment**: Windows 11 x64 · Python 3.13.7 · PySide6 6.8.2.1  
**Total Resources Audited**: 18 Approved Team Resources + 1 Discovered Native Solver = **19 Resources Total**

---

## 1. Executive Summary

This audit assesses the integration, discovery, host operational health, and dashboard presentation of the approved Mendex Engineering Studio ecosystem. 

Previously, the Engineering Operations Dashboard displayed only a subset of 10 entries due to a hardcoded UI filtering list in `src/mendex_ui/v17_panels.py`. This investigation verified that **all 18 approved resources plus native ngspice** are fully cataloged, tracked in backend contracts, and now correctly and truthfully presented on the modern Enterprise Dashboard.

### Summary Metrics
| Metric | Count | Details |
|---|---|---|
| **Approved Inventory Items** | **18** | Complete approved specification inventory |
| **Additional Discovered Tools** | **1** | Native `ngspice` (KLU sparse matrix solver) |
| **Total Ecosystem Resources** | **19** | Full registered engineering inventory |
| **Verified Operational** | **4** | LTspice, ngspice, Python Math Runtime, Git CLI |
| **Installed — Not Validated** | **6** | KiCad CLI, FEMM 4.2, FreeCAD, Qucs-S, OpenModelica, Jupyter |
| **Registered Only (Data/Benchmark)** | **4** | SwitchLossDB, MagNet Dataset, MagNet ML Benchmarks, MagNet Princeton |
| **License Required (Commercial)** | **5** | PLECS, MATLAB/Simulink, Ansys Maxwell, Ansys Icepak, SolidWorks |

---

## 2. Complete 19-Resource Traceability & Status Matrix

| # | Resource ID | Display Name | Category | Integration Status | Host Version | License Classification | Discovered Location / Provenance | Supported Automation & Capabilities |
|---|---|---|---|---|---|---|---|---|
| 1 | `switchlossdb` | SwitchLossDB | Research datasets | **REGISTERED ONLY** | 1.0-dataset | Open Research Data Terms | `https://github.com/switchloss/switchloss-db` | `query_device`, `import_csv`, `verify_checksum` |
| 2 | `magnet-dataset` | MagNet Dataset | Research datasets | **REGISTERED ONLY** | 1.0-dataset | Research License (Princeton) | `https://www.princeton.edu/~minjie/magnet.html` | `query_material`, `import_waveform_data`, `verify_checksum` |
| 3 | `magnet-ml-benchmarks` | MagNet ML Benchmarks | Benchmark resources | **REGISTERED ONLY** | 1.0-dataset | Research License (Princeton) | `https://github.com/minjiechen/MagNet` | `evaluate_benchmark`, `compare_error_metrics` |
| 4 | `kicad` | KiCad CLI | CAD and PCB tools | **INSTALLED — NOT VALIDATED** | 10.0.7 | GPLv3+ (Open Source) | `C:\Program Files\KiCad\10.0\bin\kicad-cli.exe` | `erc`, `drc`, `export_gerber`, `export_step`, `version` |
| 5 | `femm` | FEMM 4.2 | Simulation solvers | **INSTALLED — NOT VALIDATED** | 4.2 | Aladdin Free Public License | `C:\femm42\bin\femm.exe` | `solve_2d_magnetic`, `inductance_matrix`, `core_loss` |
| 6 | `magnet-princeton` | MagNet Princeton Research | Research datasets | **REGISTERED ONLY** | 1.0-dataset | Academic Research Terms | `https://www.princeton.edu/~minjie/magnet.html` | `browse_publications`, `fetch_material_constants` |
| 7 | `ltspice` | LTspice | Simulation solvers | **VERIFIED OPERATIONAL** | 26.1.1.0 | Freeware (Analog Devices) | `C:\Program Files\ADI\LTspice\LTspice.exe` | `batch_simulate`, `operating_point`, `transient` |
| 8 | `plecs` | PLECS Standalone | Commercial integrations | **LICENSE REQUIRED** | — | Commercial Proprietary (Plexim) | License review reference required | `simulate_converter`, `thermal_loss_calculation` |
| 9 | `matlab-simulink` | MATLAB / Simulink | Commercial integrations | **LICENSE REQUIRED** | — | Commercial Proprietary (MathWorks) | License review reference required | `run_m_script`, `simulate_simulink` |
| 10 | `ansys-maxwell` | Ansys Maxwell | Commercial integrations | **LICENSE REQUIRED** | — | Commercial Proprietary (Ansys) | License review reference required | `solve_3d_em_field`, `core_loss_extraction` |
| 11 | `ansys-icepak` | Ansys Icepak | Commercial integrations | **LICENSE REQUIRED** | — | Commercial Proprietary (Ansys) | License review reference required | `thermal_cfd_simulation`, `junction_temperature_solve` |
| 12 | `freecad` | FreeCAD | CAD and PCB tools | **INSTALLED — NOT VALIDATED** | 1.1.4 | LGPLv2+ (Open Source) | `C:\Program Files\FreeCAD 1.1\bin\freecadcmd.exe` | `export_step`, `generate_bobbin`, `export_stl` |
| 13 | `qucs-s` | Qucs-S | Simulation solvers | **INSTALLED — NOT VALIDATED** | 26.1.1 | GPLv2+ (Open Source) | `C:\Users\Sagar\AppData\Local\Programs\qucs-s\bin\qucs-s.exe` | `batch_simulate`, `netlist_export` |
| 14 | `openmodelica` | OpenModelica (OMC) | Simulation solvers | **INSTALLED — NOT VALIDATED** | 1.26.3 | OSMC-PL / GPLv3 | `C:\Program Files\OpenModelica1.26.3-64bit\bin\omc.exe` | `check_model`, `simulate_modelica`, `version` |
| 15 | `python` | Python Math Runtime | Engineering frameworks | **VERIFIED OPERATIONAL** | 3.13.7 | PSF License (Open Source) | `C:\Mendex studio\.venv\Scripts\python.exe` | `run_script`, `evaluate_formula`, `ast_math` |
| 16 | `jupyter` | Jupyter Notebook | Development tools | **INSTALLED — NOT VALIDATED** | 7.0.0 | Modified BSD (Open Source) | `C:\Mendex studio\.venv\Scripts\jupyter.exe` | `execute_notebook`, `export_html` |
| 17 | `git` | Git CLI | Development tools | **VERIFIED OPERATIONAL** | 2.45.2 | GPLv2 | `C:\Program Files\Git\cmd\git.EXE` | `status`, `rev_parse`, `hash_object` |
| 18 | `solidworks` | SolidWorks | Commercial integrations | **LICENSE REQUIRED** | — | Commercial Proprietary (Dassault) | License review reference required | `export_step`, `mechanical_clearance_check` |
| 19 | `ngspice` | ngspice (KLU Engine) | Simulation solvers | **VERIFIED OPERATIONAL** | 46 KLU | BSD 3-Clause (Open Source) | `C:\Users\Sagar\AppData\Local\Programs\qucs-s\bin\ngspice_con.exe` | `batch_simulate`, `operating_point`, `transient` |

---

## 3. Categorization & Rigorous Truthfulness

In compliance with project standards, the studio applies strict truthfulness rules:

1. **No False `READY` Claims**:
   - Merely detecting an executable does **not** grant `VERIFIED OPERATIONAL` status.
   - An executable tool is marked `VERIFIED OPERATIONAL` only when automated tests confirm reproducible execution, numerical accuracy, output artifact creation, and integrity verification through the core service (LTspice, ngspice, Python, Git).
   - Tools installed on the host but awaiting domain-level sign-off remain `INSTALLED — NOT VALIDATED` (KiCad, FEMM, FreeCAD, Qucs-S, OpenModelica, Jupyter).

2. **Distinct Resource Separation**:
   - Research datasets and benchmarks (`switchlossdb`, `magnet-*`) are classified separately from executable solvers and marked `REGISTERED ONLY`. They are never presented as executable applications.
   - Commercial tools (`plecs`, `matlab-simulink`, `ansys-maxwell`, `ansys-icepak`, `solidworks`) are classified as `Commercial integrations` and marked `LICENSE REQUIRED`. The studio never fabricates commercial execution and requires user license references before operation.

3. **Discovered Additions**:
   - `ngspice` is a verified native solver installed under `qucs-s/bin/ngspice_con.exe`. It is fully supported by `NgspiceAdapter` and verified operational in automated integration tests.
