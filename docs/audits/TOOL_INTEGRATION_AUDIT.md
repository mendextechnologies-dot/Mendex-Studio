# Tool Integration Audit • Individual Readiness Assessments

**Audit Scope:** Deep-dive verification of all 18 approved tools, datasets, and commercial platforms.  
**Auditor:** Senior Software Architect & Platform Auditor  
**Date:** 10 November 2026

---

## 1. Executive Matrix of 18 Approved Entries

| No. | Tool / Resource | Category | Role | Host Status | Version | Adapter Compliance | Automation Interface | Operational Status |
|---|---|---|---|---|---|---|---|---|
| 1 | **LTspice** | Application | Core | Found | 26.1.1.0 | Full (`LTspiceV15Connector`) | Headless CLI (`-b -ascii`) | **FULLY OPERATIONAL** |
| 2 | **Python** | Runtime | Core | Found | 3.13.7 | Full (`PythonV15Connector`) | Subprocess runtime | **FULLY OPERATIONAL** |
| 3 | **Git** | Developer Tool | Core | Found | 2.45.2.windows.1 | Full (`GitV15Connector`) | CLI (`rev_parse`, `status`) | **FULLY OPERATIONAL** |
| 4 | **SwitchLossDB** | Dataset | High | Schema/Data | 1.0-dataset | Full (`DatasetV15Connector`) | CSV/JSON Ingestion | **DATA READY** |
| 5 | **MagNet Dataset** | Dataset | High | Schema/Data | 2024.1 | Full (`DatasetV15Connector`) | JSON Waveform Ingestion | **DATA READY** |
| 6 | **MagNet ML Benchmarks** | Benchmark | High | Schema | 1.2-benchmarks| Full (`DatasetV15Connector`) | Benchmark Metric Schema | **DATA READY** |
| 7 | **MagNet (Princeton)** | Research Resource| High | Reference | Reference-Hub | Full (`DatasetV15Connector`) | Knowledge Hub Reference | **REFERENCE READY** |
| 8 | **KiCad** | Application | Core | Not Found | None | Stub/Adapter Ready | CLI (`kicad-cli`) | **UNINSTALLED** |
| 9 | **FEMM** | Application | Core | Not Found | None | Stub/Adapter Ready | Lua Script / ActiveX | **UNINSTALLED** |
| 10 | **FreeCAD** | Application | Core | Not Found | None | Stub/Adapter Ready | Console (`FreeCADCmd`) | **UNINSTALLED** |
| 11 | **Qucs-S** | Application | High | Not Found | None | Stub/Adapter Ready | Batch CLI (`qucs-s -b`) | **UNINSTALLED** |
| 12 | **OpenModelica** | Application | High | Not Found | None | Stub/Adapter Ready | Compiler (`omc.exe`) | **UNINSTALLED** |
| 13 | **Jupyter Notebook** | Application | High | Not Found | None | Stub/Adapter Ready | CLI (`nbconvert`) | **UNINSTALLED** |
| 14 | **PLECS** | Application | Optional | Not Found | None | Commercial Stub | CLI / RPC / Simulink | **OPTIONAL UNLICENSED**|
| 15 | **MATLAB / Simulink** | Application | Optional | Not Found | None | Commercial Stub | Batch CLI (`matlab -batch`) | **OPTIONAL UNLICENSED**|
| 16 | **Ansys Maxwell** | Application | Optional | Not Found | None | Commercial Stub | Batch COM (`ansysedt -ng`) | **OPTIONAL UNLICENSED**|
| 17 | **Ansys Icepak** | Application | Optional | Not Found | None | Commercial Stub | Batch solver (`icepak -batch`)| **OPTIONAL UNLICENSED**|
| 18 | **SolidWorks** | Application | Optional | Not Found | None | Commercial Stub | COM API / Batch | **OPTIONAL UNLICENSED**|

---

## 2. Detailed Tool-by-Tool Assessments

### 2.1 LTspice (Analog Devices)
1. **Registry & Classification:** Cataloged under `tool_id="ltspice"`, category `application`, role `core`.
2. **Detection & Version:** Detected at `C:\Program Files\ADI\LTspice\LTspice.exe`. Windows PE version resource confirmed: `26.1.1.0`.
3. **Licensing:** Proprietary freeware (Analog Devices). Redistribution prohibited; local use compliant.
4. **Adapter Compliance:** Implements `ToolAdapter` protocol via `LTspiceV15Connector` and `LTspiceAdapter`.
5. **Configuration:** Supports user-configured absolute path or automatic fallback to standard installation directory.
6. **Launching Capability:** Verified shell-free headless invocation via `SafeRunner`.
7. **Automation Mechanism:** `LTspice.exe -b -ascii <netlist-path>`.
8. **File Handling:** Ingests `.net` SPICE netlist; generates ASCII `.raw` waveforms and `.log` execution traces.
9. **Simulation Execution:** Verified on host with a synthetic RC filter benchmark. Elapsed execution time: `0.038 s`, 16 threads.
10. **Result Parsing:** Operating points ($V_{out}, V_{in}$), transient steps, thread count, and error/warning counts parsed via `parse_ltspice_log`.
11. **Diagnostics:** Captures warnings (e.g. time step too small) and fatal convergence errors without crashing.
12. **Test Coverage:** Automated unit tests in `tests/adapters/test_ltspice_adapter.py` and `tests/adapters/test_v15_connector.py`.
- **Verdict:** **FULLY OPERATIONAL (Verified with Real Executable).**

### 2.2 Python Runtime
1. **Registry & Classification:** Cataloged under `tool_id="python"`, category `runtime`, role `core`.
2. **Detection & Version:** Active runtime at `.venv\Scripts\python.exe`. Version: `3.13.7`.
3. **Licensing:** PSF License (Open Source).
4. **Adapter Compliance:** `PythonV15Connector` and `PythonRuntimeAdapter`.
5. **Configuration:** Resolves to current interpreter virtual environment.
6. **Automation:** Subprocess execution of standalone calculation scripts and parameter sweeps.
7. **Test Coverage:** Automated in `tests/adapters/test_v15_connector.py`.
- **Verdict:** **FULLY OPERATIONAL.**

### 2.3 Git Version Control
1. **Registry & Classification:** Cataloged under `tool_id="git"`, category `developer_tool`, role `core`.
2. **Detection & Version:** Detected at `C:\Program Files\Git\cmd\git.EXE`. Version: `2.45.2.windows.1`.
3. **Licensing:** GPLv2.
4. **Adapter Compliance:** `GitV15Connector` and `GitAdapter`.
5. **Automation:** Subprocess queries (`git status`, `git rev-parse HEAD`, `git hash-object`).
6. **Test Coverage:** Automated in `tests/adapters/test_v15_connector.py`.
- **Verdict:** **FULLY OPERATIONAL.**

### 2.4 SwitchLossDB (Semiconductor Switching Loss Dataset)
1. **Classification:** Category `dataset`, role `high`. Explicitly distinguished from executable software.
2. **Provenance & Source:** Upstream: `https://github.com/switchloss/switchloss-db`. License: `CC-BY-4.0`.
3. **Implementation:** Tabular CSV parser in `src/integrations/datasets/switchloss_db.py`.
4. **Verification:** Shipped canonical fixture `switchloss_sample.csv` verified with SHA-256 chunked digest.
5. **Capabilities:** Filter devices by rated $V_{ds}$ and $I_d$; extracts $E_{on}, E_{off}, R_{ds(on)}$.
6. **Test Coverage:** Automated in `tests/adapters/test_datasets.py`.
- **Verdict:** **DATA READY.**

### 2.5 MagNet Dataset (Princeton University)
1. **Classification:** Category `dataset`, role `high`.
2. **Provenance & Source:** Upstream: `https://www.princeton.edu/~minjie/magnet.html`. License: `CC-BY-4.0 / Academic`.
3. **Implementation:** JSON parser in `src/integrations/datasets/magnet_dataset.py`.
4. **Verification:** Shipped canonical fixture `magnet_sample.json` verified with SHA-256 chunked digest.
5. **Capabilities:** Query volumetric loss $P_v$ across frequency ($50\,\text{kHz}-500\,\text{kHz}$), temperature ($25^\circ\text{C}-100^\circ\text{C}$), and material (N87, 3C90, 3F3).
6. **Test Coverage:** Automated in `tests/adapters/test_datasets.py`.
- **Verdict:** **DATA READY.**

### 2.6 MagNet ML Benchmarks & MagNet Princeton
1. **Classification:** Category `benchmark` and `research_resource`.
2. **Implementation:** Reference adapters in `src/integrations/adapters/research_adapters.py`.
3. **Capabilities:** Provides benchmark loss metrics and knowledge center documentation references.
- **Verdict:** **DATA & REFERENCE READY.**

### 2.7 KiCad CLI
1. **Classification:** Category `application`, role `core`.
2. **Host Detection:** Executable `kicad-cli.exe` not detected on host.
3. **Truthful State:** Accurately reported as `NOT_INSTALLED`.
4. **Adapter Readiness:** Complete `KiCadAdapter` in `src/integrations/adapters/kicad.py` supporting `erc`, `drc`, `export_gerber`, and `export_step`.
5. **Parsing Readiness:** `parse_kicad_drc_json` implemented in `src/integrations/parsers/kicad_parser.py`.
- **Verdict:** **ADAPTER READY; BLOCKED ON SOFTWARE INSTALLATION.**

### 2.8 FEMM (Finite Element Method Magnetics)
1. **Classification:** Category `application`, role `core`.
2. **Host Detection:** `femm.exe` not detected on host.
3. **Truthful State:** Accurately reported as `NOT_INSTALLED`.
4. **Adapter Readiness:** Complete `FEMMAdapter` in `src/integrations/adapters/femm.py`.
5. **Script Generator:** `generate_femm_transformer_script` generates headless Lua simulation scripts modeling core geometry, materials, air gaps, and axi-symmetric fields.
- **Verdict:** **ADAPTER READY; BLOCKED ON SOFTWARE INSTALLATION.**

### 2.9 FreeCAD
1. **Classification:** Category `application`, role `core`.
2. **Host Detection:** `FreeCADCmd.exe` not detected on host.
3. **Truthful State:** Accurately reported as `NOT_INSTALLED`.
4. **Adapter Readiness:** Complete `FreeCADAdapter` in `src/integrations/adapters/freecad.py`.
5. **Script Generator:** `generate_freecad_bobbin_script` generates Python scripts for parametric 3D bobbin generation and STEP exports.
- **Verdict:** **ADAPTER READY; BLOCKED ON SOFTWARE INSTALLATION.**

### 2.10 Qucs-S & OpenModelica
1. **Classification:** Category `application`, role `high`.
2. **Host Detection:** Neither `qucs-s.exe` nor `omc.exe` detected on host.
3. **Truthful State:** Both reported as `NOT_INSTALLED`.
4. **Adapter Readiness:** `QucsSAdapter` and `OpenModelicaAdapter` implemented; `generate_openmodelica_flyback_script` implemented for transient simulation models.
- **Verdict:** **ADAPTER READY; BLOCKED ON SOFTWARE INSTALLATION.**

### 2.11 Jupyter Notebook
1. **Classification:** Category `application`, role `high`.
2. **Host Detection:** `jupyter.exe` not installed in virtual environment or PATH.
3. **Truthful State:** Accurately reported as `NOT_INSTALLED`.
4. **Adapter Readiness:** `JupyterAdapter` implemented targeting `nbconvert`.
- **Verdict:** **ADAPTER READY; BLOCKED ON SOFTWARE INSTALLATION.**

### 2.12 Optional Commercial Stubs (PLECS, MATLAB, Ansys Maxwell, Ansys Icepak, SolidWorks)
1. **Classification:** Category `application`, role `optional`, `optional_paid=True`.
2. **Host Detection:** No commercial binaries or license servers found.
3. **Truthful State:** Strictly reported as `OPTIONAL_UNLICENSED`.
4. **Safety Boundaries:**
   - Adapters inherit from `CommercialStubAdapter` and `CommercialStubV15Connector`.
   - Never attempt unauthorized license validation or network activation.
   - Non-blocking: presence of unconfigured commercial tools does not impede Studio launch or execution of other tools.
- **Verdict:** **SAFE CONFIGURATION STUBS IMPLEMENTED; LICENSE GATED.**
