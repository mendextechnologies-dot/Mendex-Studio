# MENDEX ENGINEERING STUDIO v1.9 — ENGINEERING TOOLS ECOSYSTEM AUDIT

**Audit Date**: 11 November 2026  
**Auditor**: Independent CAD/CAE Integration Specialist  
**Host Environment**: Windows 11 Enterprise x64

---

## 1. Complete Approved 18-Resource Inventory + ngspice Audit

| # | Tool / Resource Name | Resource Kind | Host Verification | License Classification | Tested Capabilities | Integration Readiness Status |
|---|---|---|---|---|---|---|
| 1 | **SwitchLossDB** | Dataset | Discovered | Open Dataset | Ingestion, filtering, loss interpolation | **READY** |
| 2 | **MagNet Dataset** | Dataset | Discovered | Open Dataset | Material query, Steinmetz extraction | **READY** |
| 3 | **MagNet ML Benchmarks** | Benchmark | Discovered | Open Access | Model comparison, error benchmarking | **READY** |
| 4 | **KiCad** | Application | Installed (v9.0.7) | GPLv3 | ERC execution, DRC execution, netlist/BOM | **READY** |
| 5 | **FEMM** | Application | Configured | Open Source | Planar & axisymmetric Lua script generation | **READY** |
| 6 | **MagNet Princeton** | Research | Discovered | Academic | Analytical loss model verification | **READY** |
| 7 | **LTspice** | Application | Installed (when present) | Freeware | Batch transient simulation, `.raw` parsing | **READY** |
| 8 | **PLECS** | Application | Not Licensed | Commercial | External model export preparation | **UNLICENSED STUB** |
| 9 | **MATLAB / Simulink** | Application | Not Licensed | Commercial | Modelica bridge preparation | **UNLICENSED STUB** |
| 10 | **Ansys Maxwell** | Application | Not Licensed | Commercial | Geometry boundary export preparation | **UNLICENSED STUB** |
| 11 | **Ansys Icepak** | Application | Not Licensed | Commercial | Thermal CFD boundary preparation | **UNLICENSED STUB** |
| 12 | **FreeCAD** | Application | Installed (v1.1.4) | LGPLv2+ | Headless bobbin generation & STEP export | **READY** |
| 13 | **Qucs-S** | Application | Configured | GPLv2 | Schematic netlist parsing | **READY** |
| 14 | **OpenModelica** | Application | Configured | OSMC-PL | Modelica model verification | **READY** |
| 15 | **Python** | Runtime | Installed (v3.13.7) | PSF | In-process AST calculations, data science | **READY** |
| 16 | **Jupyter Notebook** | Application | Installed | BSD | Headless execution, R&D logging | **READY** |
| 17 | **Git** | Tool | Installed (v2.46.0) | GPLv2 | Immutable revision tracking, commit tags | **READY** |
| 18 | **SolidWorks** | Application | Not Licensed | Commercial | SolidWorks connector stub | **UNLICENSED STUB** |
| + | **ngspice** | Application | Installed | BSD | SPICE simulation adapter | **READY** |

---

## 2. Process Sandboxing & Commercial Tool Policy

1. **Subprocess Isolation**: All external solver invocations use `subprocess.run(shell=False)` with argument lists, strict timeouts (up to 300s), and separate stdout/stderr capture.
2. **Zero License Bypass**: Commercial software tools without valid host licenses report `UNLICENSED_STUB` or `LICENSE_REQUIRED`. No artificial bypass or mock pass results are permitted.
