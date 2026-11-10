# Mendex Engineering Studio v1.8 — Engineering Tools Readiness Audit

## 1. Executive Summary

This document presents the definitive operational readiness audit of all **18 engineering tools and resources** approved in the Mendex Engineering Studio catalog (`src/mendex_core/catalog.py`).

Every open-source native solver has been physically detected on the host workstation, wrapped with a dedicated subprocess execution adapter (`src/integrations/adapters/`), and verified through automated end-to-end regression tests.

Commercial tools remain strictly guarded under `OPTIONAL_UNLICENSED` status, ensuring safe runtime behavior without false claims of execution availability.

---

## 2. Complete 18-Tool Inventory Audit Matrix

| # | Tool ID | Tool Name | Category | License / Type | Detected Host Path | Version | Readiness Status | Automated Operations | Verification Evidence |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `ltspice` | ADI LTspice | Native Solver | Proprietary (Freeware) | `C:\Program Files\ADI\LTspice\LTspice.exe` | 26.1.1.0 | **READY** | Netlist batch run, `.raw` parsing, waveform export | `tests/test_v16_workflow.py`, `tests/test_ltspice_adapter.py` |
| 2 | `kicad` | KiCad EDA | Native EDA | GPL-3.0-or-later | `C:\Program Files\KiCad\10.0\bin\kicad-cli.exe` | 10.0.7 | **READY** | Schematic ERC, PCB DRC, 3D STEP export | `tests/test_kicad_adapter.py` |
| 3 | `femm` | Finite Element Method Magnetics | Native Solver | Free / Open Source | `C:\femm42\bin\femm.exe` | 4.2 | **READY** | Headless Lua magnetics FEA, inductance, flux density | `tests/test_femm_adapter.py` |
| 4 | `freecad` | FreeCAD | Native CAD | LGPL-2.0-or-later | `C:\Program Files\FreeCAD 1.1\bin\freecadcmd.exe` | 1.1.4 | **READY** | Headless Python CAD, 3D STEP transformer export | `tests/test_freecad_adapter.py` |
| 5 | `qucs_s` | Qucs-S & ngspice | Native Solver | GPL-2.0 / BSD 3-Clause | `C:\Users\Sagar\AppData\Local\Programs\qucs-s\bin\qucs-s.exe` (`ngspice_con.exe`) | 26.1.1 (ngspice 46) | **READY** | Batch SPICE simulation, AC/DC/Transient sweep | `tests/test_ngspice_adapter.py` |
| 6 | `openmodelica` | OpenModelica | Native Multi-Domain | OSMC-1.8 | `C:\Program Files\OpenModelica1.26.3-64bit\bin\omc.exe` | 1.26.3 | **READY** | OMC model syntax check, dynamic system simulation | `tests/test_openmodelica_adapter.py` |
| 7 | `plecs` | Plexim PLECS | Commercial Solver | Commercial Guard | — | — | **OPTIONAL_UNLICENSED** | Guarded execution refusal, schema validation | `tests/test_commercial_guards.py` |
| 8 | `matlab` | MathWorks MATLAB | Commercial Math | Commercial Guard | — | — | **OPTIONAL_UNLICENSED** | Guarded execution refusal | `tests/test_commercial_guards.py` |
| 9 | `ansys_maxwell` | Ansys Maxwell | Commercial EM | Commercial Guard | — | — | **OPTIONAL_UNLICENSED** | Guarded execution refusal | `tests/test_commercial_guards.py` |
| 10 | `ansys_icepak` | Ansys Icepak | Commercial Thermal | Commercial Guard | — | — | **OPTIONAL_UNLICENSED** | Guarded execution refusal | `tests/test_commercial_guards.py` |
| 11 | `solidworks` | Dassault SolidWorks | Commercial CAD | Commercial Guard | — | — | **OPTIONAL_UNLICENSED** | Guarded execution refusal | `tests/test_commercial_guards.py` |
| 12 | `python` | Python Runtime | Runtime Environment | PSF License | `C:\Mendex studio\.venv\Scripts\python.exe` | 3.13.7 | **READY** | Core calculations, NumPy/SciPy analytics, scripts | `tests/test_deterministic_calculations.py` |
| 13 | `numpy_scipy` | NumPy & SciPy | Numerical Library | BSD-compatible | In `.venv` | 2.5.4 / 1.18.1 | **READY** | Vectorized waveform parsing, signal statistics | `tests/test_ltspice_parser.py` |
| 14 | `pyside6` | PySide6 (Qt) | Desktop UI Framework | LGPLv3 | In `.venv` | 6.8.0 | **READY** | Native desktop UI, QtCharts waveform plotting | `tests/test_window.py`, `tests/test_waveform_viewer.py` |
| 15 | `sqlite` | SQLite Database | Relational Storage | Public Domain | Integrated in Python standard library | 3.x | **READY** | Additive v5 schema, transactional persistence | `tests/test_integration_service.py` |
| 16 | `git` | Git Version Control | VCS | GPL-2.0 | `git` on PATH | 2.x | **READY** | Branch management, workspace file versioning | Manual verification |
| 17 | `markdown_report` | Engineering Report Engine | Documentation | Internal Mendex | Native Core Service | 1.8.0 | **READY** | HTML/JSON report synthesis, cryptographic sealing | `tests/test_v16_workflow.py` |
| 18 | `intelligence_foundation` | Mendex Engineering Intelligence | AI / Knowledge Engine | Proprietary Internal | Native Core Service | 1.8.0 | **READY** | Unit-aware math, Dowell, skin depth, offline reasoning | `tests/test_engineering_intelligence.py` |

---

## 3. Native Solver Deep-Dive & Test Evidence

### 3.1 ADI LTspice (v26.1.1.0)
- **Path**: `C:\Program Files\ADI\LTspice\LTspice.exe`
- **Execution Mode**: Headless CLI (`-b -ascii -Run <netlist.net>`).
- **Output Artifacts**: ASCII/Binary `.raw` files, operating point logs (`.log`).
- **Resilience**: Verified timeout termination, abnormal exit handling, corrupted netlist detection.
- **Evidence**: `docs/v1.6/WORKFLOW_TEST_REPORT.md`, `tests/test_ltspice_adapter.py`.

### 3.2 KiCad CLI (v10.0.7)
- **Path**: `C:\Program Files\KiCad\10.0\bin\kicad-cli.exe`
- **Execution Mode**: Subcommand CLI (`sch erc`, `pcb drc`).
- **Output Artifacts**: JSON-formatted DRC violation reports, STEP mechanical models.
- **Evidence**: `tests/test_kicad_adapter.py`.

### 3.3 FEMM (v4.2)
- **Path**: `C:\femm42\bin\femm.exe`
- **Execution Mode**: Headless batch execution driven by generated Lua script (`-luafile <script.lua>`).
- **Output Artifacts**: Magnetic vector potential, core flux density ($B$), AC winding resistance, and leakage inductance.
- **Evidence**: `tests/test_femm_adapter.py`.

### 3.4 FreeCAD (v1.1.4)
- **Path**: `C:\Program Files\FreeCAD 1.1\bin\freecadcmd.exe`
- **Execution Mode**: Non-interactive command-line Python interpreter.
- **Output Artifacts**: Standard 3D CAD exchange models (`.step`, `.iges`) of custom transformer bobbins and cores.
- **Evidence**: `tests/test_freecad_adapter.py`.

### 3.5 Qucs-S & ngspice (v26.1.1 / ngspice 46)
- **Path**: `C:\Users\Sagar\AppData\Local\Programs\qucs-s\bin\qucs-s.exe` and `ngspice_con.exe`
- **Execution Mode**: Batch SPICE simulation via `ngspice_con -b -r <out.raw> <input.cir>`.
- **Output Artifacts**: Frequency response data, operating points, transient waveforms.
- **Evidence**: `tests/test_ngspice_adapter.py`.

### 3.6 OpenModelica (v1.26.3)
- **Path**: `C:\Program Files\OpenModelica1.26.3-64bit\bin\omc.exe`
- **Execution Mode**: Headless Modelica compiler commands (`omc <script.mos>`).
- **Output Artifacts**: Model check diagnostics, compilation binaries, dynamic simulation results.
- **Evidence**: `tests/test_openmodelica_adapter.py`.

---

## 4. Commercial Guard Verification

All 5 commercial tools (`plecs`, `matlab`, `ansys_maxwell`, `ansys_icepak`, `solidworks`) are strictly configured with guard wrappers in `src/integrations/adapters/guards.py`.

When an execution request targets any of these tools:
1. The adapter checks for valid workstation license configuration.
2. In the absence of confirmed enterprise licenses, the tool transitions to `OPTIONAL_UNLICENSED`.
3. Execution requests are cleanly rejected with code `REFUSED_NO_LICENSE` rather than crashing or throwing unhandled exceptions.
4. Generated engineering reports truthfully indicate `NOT_EVALUATED` rather than fabricating synthetic compliance.

---

## 5. Audit Conclusion

All 6 target open-source native engineering tools are **fully operational, physically installed, and automated**. All 5 commercial tools are **safely guarded**. The Mendex Studio tool integration subsystem meets 100% of the v1.8 enterprise readiness criteria.
