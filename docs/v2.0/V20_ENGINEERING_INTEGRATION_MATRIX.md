# MENDEX ENGINEERING STUDIO v2.0 — ENGINEERING INTEGRATION MATRIX

## 1. Complete Approved 18-Resource Tool Ecosystem + ngspice

| # | Resource Name | Category | Classification | Host Status | Supported Operations | Verification Mode |
|---|---------------|----------|----------------|-------------|----------------------|-------------------|
| 1 | **SwitchLossDB** | Dataset | Open Dataset | INSTALLED / READY | Query, Ingestion, Loss Extrapolation | Hash & Metadata Check |
| 2 | **MagNet Dataset** | Dataset | Open Dataset | INSTALLED / READY | Core Material Query, BH Curve Lookup | Hash & Range Check |
| 3 | **MagNet ML Benchmarks** | Dataset / ML | Benchmark Suite | READY | Model Benchmark Ingestion | SHA-256 Manifest |
| 4 | **KiCad** | EDA Application | Open Source (GPLv3) | READY (v9.0.7) | Schematic ERC, PCB DRC, Netlist, BOM, Gerbers | Subprocess CLI (`kicad-cli`) |
| 5 | **FEMM** | FEA Application | Open Source | READY | 2D Magnetics FEA, Inductance, Core Loss | Subprocess CLI / Lua Script |
| 6 | **MagNet Princeton Resources** | Research / Models | Research Spec | READY | Loss Model Parameter Verification | Analytical Formulas |
| 7 | **LTspice** | SPICE Simulator | Freeware | READY (when installed) | Transient, AC, Operating Point Simulation | Subprocess CLI (`-b -ascii`) |
| 8 | **PLECS** | System Simulator | Commercial | UNLICENSED STUB | Model Export, External Netlist Prep | Honest License Warning |
| 9 | **MATLAB / Simulink** | Numerical / System | Commercial | UNLICENSED STUB | Script Export, Simulink Bridge Prep | Honest License Warning |
| 10 | **Ansys Maxwell** | Electromagnetic FEA | Commercial | UNLICENSED STUB | Geometry Prep, Boundary Export | Honest License Warning |
| 11 | **Ansys Icepak** | Thermal CFD | Commercial | UNLICENSED STUB | Thermal Mesh Prep, Boundary Export | Honest License Warning |
| 12 | **FreeCAD** | 3D Mechanical CAD | Open Source (LGPLv2+) | READY (v1.1.4) | Headless 3D Bobbin Solid Gen, STEP Export | FreeCADCmd Subprocess |
| 13 | **Qucs-S** | Circuit Simulator | Open Source (GPLv2) | READY (when installed) | Schematic Netlist, RF & AC Analysis | Subprocess CLI |
| 14 | **OpenModelica** | Multidomain Modeling | Open Source (OSMC-PL) | READY (when installed) | Modelica Syntax Check, Flattening, Transient | Subprocess CLI (`omc`) |
| 15 | **Python** | Runtime / Scripting | Open Source (PSF) | READY (v3.13.7) | Scientific Calculations, Data Analysis, AST | Native Python In-Process |
| 16 | **Jupyter Notebook** | Interactive R&D | Open Source (BSD) | READY (when installed) | Notebook Launch, Headless Execution | Subprocess CLI |
| 17 | **Git** | Version Control | Open Source (GPLv2) | READY (v2.46.0) | Repository Tracking, Revisions, SHA History | Subprocess CLI (`git`) |
| 18 | **SolidWorks** | Mechanical CAD | Commercial | UNLICENSED STUB | Parasolid/STEP Assembly Prep | Honest License Warning |
| + | **ngspice** | SPICE Simulator | Open Source (BSD) | READY (when installed) | Transient, Fourier, Noise Analysis | Subprocess CLI (`-b -r`) |

---

## 2. Integration Verification Lifecycle

Every integration in Mendex Studio v2.0 complies with strict operational contracts:

1. **Discovery & Version Detection**: Probes candidate binary paths and environment variables truthfully. If missing, status is explicitly marked `NOT_INSTALLED`.
2. **Commercial Licensing Integrity**: Commercial solvers (PLECS, MATLAB, Maxwell, Icepak, SolidWorks) are never spoofed or bypassed. When licenses are unavailable, they gracefully report `LICENSE_REQUIRED` or `UNAVAILABLE` without application crash.
3. **Execution Sandboxing**: All tool invocations run within isolated working directories with strict execution timeouts, stdout/stderr logging, and returncode verification.
4. **Result Parsing vs. Engineering Validation**: A successful exit code ($0$) only confirms that the solver did not crash. The result parser extracts physical quantities (voltages, currents, temperatures, flux density) and passes them to the validation service to check against engineering requirements.
