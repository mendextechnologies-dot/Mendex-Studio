# Tool Compatibility & Integration Audit • Mendex Studio v1.5

**Date:** 10 November 2026  
**Auditor:** Agent 2 (Antigravity), Engineering Integration Lead  
**Scope:** Complete inventory and technical evaluation of the 18 team-approved engineering tools, datasets, and commercial platforms.  
**Reference Machine:** Windows 11 x64 (AMD64), Python 3.13.7, Git 2.45.2.

---

## 1. Executive Summary

This audit establishes the baseline compatibility matrix, licensing boundaries, automation capabilities, and adapter strategies for Mendex Engineering Studio v1.5. 

### Operational Integrity Principles
1. **Truthful Status Reporting:** A tool is never marked `READY` unless its executable has been detected, its version confirmed within supported ranges, and a verified non-destructive smoke test has executed successfully.
2. **Subprocess Isolation:** All external tools run headlessly in isolated working directories with argument lists (`shell=False`), explicit timeouts, and full process-tree cancellation.
3. **No Fabricated Evidence:** Solvers that are not installed remain `NOT_INSTALLED`. Unexecuted benchmarks remain `NOT_EVALUATED`.
4. **Commercial Tool Safeguards:** Commercial platforms (PLECS, MATLAB, Ansys, SolidWorks) are license-gated stubs. They never block application startup and never attempt unauthorized licensing bypasses.

---

## 2. Comprehensive Inventory of Approved Entries (18 Tools & Resources)

| # | Tool / Resource | Category | Proposed Role | Detected on Host | Verified Version | Host State | License Model | Automation Mechanism |
|---|---|---|---|---|---|---|---|---|
| 1 | **LTspice** | Application | Core | **YES** (`C:\Program Files\ADI\LTspice\LTspice.exe`) | **26.1.1.0** | **READY** | Proprietary Freeware (Analog Devices) | Headless batch mode: `LTspice.exe -b -ascii <netlist>` |
| 2 | **Python** | Runtime | Core | **YES** (`.venv\Scripts\python.exe`) | **3.13.7** | **READY** | PSF License (Open Source) | Direct interpreter / subshell subprocess execution |
| 3 | **Git** | Tool | Core | **YES** (`C:\Program Files\Git\cmd\git.EXE`) | **2.45.2.windows.1** | **READY** | GPLv2 (Open Source) | CLI execution: `git rev-parse`, `git status`, `git hash-object` |
| 4 | **KiCad CLI** | Application | Core | NO | N/A | `NOT_INSTALLED` | GPLv3+ (Open Source) | CLI: `kicad-cli pcb drc`, `kicad-cli sch erc`, `kicad-cli pcb export` |
| 5 | **FEMM** | Application | Core | NO | N/A | `NOT_INSTALLED` | Aladdin Free Public License | Headless Lua scripting: `femm.exe -lua=<script.lua>` or ActiveX |
| 6 | **FreeCAD** | Application | Core | NO | N/A | `NOT_INSTALLED` | LGPLv2+ (Open Source) | Headless console: `FreeCADCmd.exe <script.py>` |
| 7 | **Qucs-S** | Application | High | NO | N/A | `NOT_INSTALLED` | GPLv2+ (Open Source) | Batch CLI: `qucs-s.exe -b <schematic>` with ngspice/SPICE backend |
| 8 | **OpenModelica**| Application | High | NO | N/A | `NOT_INSTALLED` | OSMC-PL (Open Source) | Compiler CLI: `omc.exe <script.mos>` |
| 9 | **Jupyter** | Tool | High | NO | N/A | `NOT_INSTALLED` | Modified BSD (Open Source) | CLI: `jupyter nbconvert --to script --execute <nb.ipynb>` |
| 10 | **SwitchLossDB**| Dataset | High | NO (Schema Ready) | N/A | `READY_FOR_IMPORT` | Open Access / CC-BY | Tabular CSV/JSON parser with SHA-256 provenance manifest |
| 11 | **MagNet Dataset** | Research Dataset | High | NO (Schema Ready) | N/A | `READY_FOR_IMPORT` | Academic (Princeton) / CC-BY | HDF5/CSV waveform dataset reader with excitation metadata |
| 12 | **MagNet ML Benchmarks** | Benchmark | High | NO (Schema Ready) | N/A | `READY_FOR_IMPORT` | Open Research | Neural network surrogate benchmark verification metrics |
| 13 | **MagNet (Princeton)** | Research Resource | High | Clarified: Research Hub | N/A | `REFERENCE_ONLY` | Academic | Knowledge center references, publications, and material models |
| 14 | **PLECS** | Application | Optional | NO | N/A | `OPTIONAL_UNLICENSED` | Commercial Proprietary (Plexim) | Headless CLI / XML RPC / MATLAB toolbox integration |
| 15 | **MATLAB / Simulink** | Application | Optional | NO | N/A | `OPTIONAL_UNLICENSED` | Commercial Proprietary (MathWorks) | Batch engine: `matlab.exe -batch <command>` |
| 16 | **Ansys Maxwell** | Application | Optional | NO | N/A | `OPTIONAL_UNLICENSED` | Commercial Proprietary (Ansys) | Batch COM / IronPython: `ansysedt.exe -ng -BatchSolve` |
| 17 | **Ansys Icepak** | Application | Optional | NO | N/A | `OPTIONAL_UNLICENSED` | Commercial Proprietary (Ansys) | Batch solver: `icepak.exe -batch` |
| 18 | **SolidWorks** | Application | Optional | NO | N/A | `OPTIONAL_UNLICENSED` | Commercial Proprietary (Dassault) | COM API automation / headless export |

---

## 3. Detailed Tool Profiles & Automation Specifications

### 3.1 LTspice (Analog Devices)
- **Host Location:** `C:\Program Files\ADI\LTspice\LTspice.exe`
- **File Version:** `26.1.1.0`
- **Automation Method:** 
  ```powershell
  & "C:\Program Files\ADI\LTspice\LTspice.exe" -b -ascii <netlist-path>
  ```
- **Generated Artifacts:**
  - `<netlist-basename>.log`: ASCII simulation log containing operating point iterations, matrix statistics, transient steps, warnings, and elapsed execution time.
  - `<netlist-basename>.raw`: Raw waveform dataset (ASCII format when `-ascii` flag is passed).
- **Execution Characteristics:**
  - Fast, fully headless execution confirmed on host.
  - Subprocess terminates with exit code 0 on successful convergence.
  - Non-convergence produces non-zero exit code or explicit fatal messages in the `.log` file.
- **Adapter Status:** Core batch runner and `.log`/`.raw` parser implemented and verified.

### 3.2 KiCad CLI
- **Expected Locations:** `C:\Program Files\KiCad\<version>\bin\kicad-cli.exe`
- **Supported Operations:**
  - `kicad-cli sch erc --format json --output <report.json> <schematic.kicad_sch>`
  - `kicad-cli pcb drc --format json --output <report.json> <board.kicad_pcb>`
  - `kicad-cli pcb export gerbers --output <dir> <board.kicad_pcb>`
- **Host State:** Not installed. The adapter performs non-destructive path detection and returns `NOT_INSTALLED`.

### 3.3 FEMM (Finite Element Method Magnetics)
- **Expected Locations:** `C:\femm42\bin\femm.exe`
- **Automation Method:**
  - Headless Lua script execution: `femm.exe -lua=<script.lua>` or Windows ActiveX/COM via `pyfemm`.
  - Solves 2D magnetic fields, calculating core flux density $B$, inductances, leakage, and winding losses.
- **Host State:** Not installed. The adapter correctly reports `NOT_INSTALLED` and provides official installation links (`https://www.femm.info`).

### 3.4 FreeCAD
- **Expected Locations:** `C:\Program Files\FreeCAD <version>\bin\FreeCADCmd.exe`
- **Automation Method:**
  - Headless console: `FreeCADCmd.exe <python-script.py>`
  - Automated generation of 3D transformer bobbin/core models and STEP/IGES exports.
- **Host State:** Not installed. Reports `NOT_INSTALLED`.

### 3.5 Qucs-S & OpenModelica
- **Qucs-S:** Circuit simulator supporting multiple simulation backends (ngspice, Qucsator). Executed via CLI batch mode.
- **OpenModelica:** Equation-based multi-domain modeling tool. Executed via `omc.exe` running `.mos` automation scripts.
- **Host State:** Both report `NOT_INSTALLED` with structured diagnostics.

### 3.6 Python & Jupyter
- **Python:** System and virtual environment runtime (`Python 3.13.7`). Fully functional for engineering scripts, parameter sweeps, and analytical calculations.
- **Jupyter:** Headless execution via `jupyter nbconvert --execute`. When uninstalled, notebook execution operations report `NOT_INSTALLED`.

### 3.7 Research Datasets (SwitchLossDB, MagNet Dataset, MagNet Benchmarks)
- **Clarification:** These are research data repositories and machine learning benchmarks, not desktop CAD software.
- **SwitchLossDB:** Tabular database of wide-bandgap (SiC, GaN) and Si MOSFET/IGBT switching losses under varied $V_{ds}, I_d, T_j$.
- **MagNet Dataset:** High-frequency magnetic core loss measurements across sinusoidal, triangular, and trapezoidal excitations.
- **Provenance Requirement:** Any imported dataset must register its source URL, publication citation, SHA-256 checksum, record count, and license type (`CC-BY 4.0` / academic).

### 3.8 Commercial Stubs (PLECS, MATLAB, Ansys Maxwell/Icepak, SolidWorks)
- **Role:** Stubs provide configuration fields (executable path, license server address) and detection logic.
- **Guardrail:** No mock approvals or synthetic passes are issued. If no valid license or executable is detected, the status remains `OPTIONAL_UNLICENSED`. Application startup is never blocked.

---

## 4. Proposed Sprint Plan for Agent 2 (Antigravity)

1. **Sprint 1 — Execution Engine & Detection Baseline (Done):**
   - Safe subprocess runner with process-tree cancellation (`taskkill /PID <pid> /T /F`), timeout enforcement, and stdout/stderr logging.
   - Unified `ToolRegistry` and detection logic for all 18 entries.
   - Standardized artifact hashing and manifest generation.

2. **Sprint 2 — Core Tool Connectors & Parsers (Done):**
   - Dedicated LTspice batch adapter with verified log and ASCII raw parsing.
   - Stubs and detection for KiCad, FEMM, and FreeCAD with fixture test coverage.

3. **Sprint 3 — Extended Tools & Dataset Provenance (Done):**
   - Dataset manifest reader and validator for SwitchLossDB and MagNet.
   - Qucs-S, OpenModelica, and Python/Jupyter adapters.

4. **Sprint 4 — Commercial Stubs & Acceptance Verification (Done):**
   - License-gated adapters for PLECS, MATLAB, Ansys Maxwell/Icepak, and SolidWorks.
   - Comprehensive test suite under `tests/adapters/` guaranteeing 0 regressions and truthful reporting.
