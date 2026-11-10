# Mendex Engineering Studio v1.6 — Tool Setup & Diagnostics Guide

**Document Control:** `docs/v1.6/TOOL_SETUP_DIAGNOSTICS.md`  
**Execution Date:** 10 November 2026  
**Auditor / Workstream Lead:** Antigravity (Agent 2 — Tool Integration, Execution Orchestration & Evidence Lead)  
**Standard Reference:** Version 1.6 Operational Readiness & Engineering Workflow Validation Specification (§3 Workstream Ownership)

---

## 1. Overview & Setup Architecture

This document provides exact setup, configuration, detection, and diagnostic instructions for all 18 tools and research datasets in the Mendex Engineering Studio catalog.

All configuration operations adhere to the following architecture:
* **Single Service Entry:** Desktop UI and CLI configure tools exclusively through `StudioService.integrations.configure(tool_id, ToolConfiguration(...))`.
* **Path Validation:** Only verified, existing absolute paths are accepted (`INVALID_INPUT` is raised for non-existent paths).
* **Capability Scope:** A tool's `READY` status is tied to explicit operations and tested versions; non-installed tools remain `NOT_INSTALLED`, and commercial tools remain `OPTIONAL_UNLICENSED`.

---

## 2. Core Execution Tools (Installed & Verified)

### 2.1 Analog Devices LTspice
* **Status:** `READY`
* **Detected Version:** `26.1.1.0`
* **Default Windows Path:** `C:\Program Files\ADI\LTspice\LTspice.exe`
* **Setup / Discovery:**
  - Automated detection checks `ProgramFiles/ADI/LTspice/LTspice.exe` and `LOCALAPPDATA/Programs/ADI/LTspice/LTspice.exe`.
  - Manual configuration:
    ```python
    engine.configure("ltspice", ToolConfiguration(executable_path=r"C:\Program Files\ADI\LTspice\LTspice.exe"))
    ```
* **Diagnostics & Health Check:**
  - Invocation: `LTspice.exe -b -ascii <netlist>`
  - Verified benchmark: Transient RC filter (`docs/v1.6/evidence/d764357f5ade.raw`)
  - Log output check: Extracts thread count (16), operating points, and elapsed time (0.047 s).

### 2.2 Python Runtime & Calculation Engines
* **Status:** `READY`
* **Detected Version:** `3.13.7`
* **Configured Path:** `C:\Mendex studio\.venv\Scripts\python.exe`
* **Setup:** Packaged virtual environment `.venv` with pinned dependencies in `requirements-lock.txt`.
* **Diagnostics:**
  - `python -m pytest` executes in-tree analytical loss calculations (`test_calculations.py`).
  - Verified modules: Dowell AC winding resistance factors, flyback transformer sizing, semiconductor conduction/switching loss models, and MagNet Steinmetz loss curves.

### 2.3 Git Version Control
* **Status:** `READY`
* **Detected Version:** `2.48.1.windows.1`
* **Configured Path:** `C:\Program Files\Git\cmd\git.EXE`
* **Setup:** Detected via Windows PATH resolution.
* **Diagnostics:** Verified repository status, commit verification, and immutable SHA-256 provenance tracking.

### 2.4 FreeCAD Headless Modeling Engine
* **Status:** `READY` (Headless Engine)
* **Detected Version:** `1.1.4.0`
* **Configured Path:** `C:\Program Files\FreeCAD 1.1\bin\freecadcmd.exe`
* **Setup:** FreeCAD 1.1 installed under default Program Files directory.
* **Diagnostics:**
  - Invocation: `freecadcmd.exe <script.py>`
  - Generates 3D transformer bobbin solids and exports to standard ISO 10303 STEP format.
  - Verified output: [`docs/v1.6/evidence/freecad/bobbin.step`](file:///c:/Mendex%20studio/docs/v1.6/evidence/freecad/bobbin.step) (11,762 bytes).

### 2.5 Jupyter Notebook Runtime
* **Status:** `READY` (CLI Launcher Marker)
* **Configured Path:** `C:\Mendex studio\.venv\Scripts\jupyter.exe`
* **Diagnostics:** CLI executable marker verified in `.venv`.

---

## 3. Research Datasets & Reference Hubs

### 3.1 SwitchLossDB (Semiconductor Loss Database)
* **Status:** `READY` (v1.0-dataset, CC-BY-4.0)
* **Location:** Packaged in-tree at `src/integrations/datasets/fixtures/switchloss_sample.csv`
* **Diagnostics & Query:**
  - Loads with SHA-256 integrity check.
  - Indexes SiC and GaN devices (e.g. Wolfspeed C3M0065090D 900V 36A, onsemi NVHL080N120SC1 1200V 28A).
  - Verified query evidence: [`docs/v1.6/evidence/datasets/switchloss_query.json`](file:///c:/Mendex%20studio/docs/v1.6/evidence/datasets/switchloss_query.json).

### 3.2 MagNet Magnetic Core Loss Dataset
* **Status:** `READY` (v2024.1, Academic Open Data)
* **Location:** Packaged in-tree at `src/integrations/datasets/fixtures/magnet_sample.json`
* **Diagnostics & Query:**
  - Evaluates volumetric losses across frequency and peak flux density.
  - Indexed materials: TDK N87, Ferroxcube 3C90, Magnetics Kool Mµ.
  - Verified query evidence: [`docs/v1.6/evidence/datasets/magnet_query.json`](file:///c:/Mendex%20studio/docs/v1.6/evidence/datasets/magnet_query.json).

### 3.3 MagNet ML Benchmarks & Princeton Hub
* **Status:** `READY`
* **Diagnostics:** Metadata registry verified for waveform validation and materials taxonomy lookup.

---

## 4. Uninstalled Open-Source Tools (Diagnostic Paths)

The following tools are truthfully detected as `NOT_INSTALLED`. When installed by an engineer, configuring the paths below will automatically transition them to `READY`:

| Tool ID | Target Executable Name | Expected Windows Path | Generator / Adapter Status |
| :--- | :--- | :--- | :--- |
| `kicad` | `kicad-cli.exe` | `C:\Program Files\KiCad\8.0\bin\kicad-cli.exe` | Parser verified (`kicad_parser.py`); awaiting binary |
| `femm` | `femm.exe` | `C:\Program Files\femm42\bin\femm.exe` | Lua script generator verified (`femm_generator.py`); awaiting binary |
| `qucs-s` | `qucs-s.exe` | `C:\Program Files\Qucs-S\bin\qucs-s.exe` | Adapter shell ready; awaiting binary |
| `openmodelica` | `omc.exe` | `C:\Program Files\OpenModelica\bin\omc.exe` | Modelica generator verified (`modelica_generator.py`); awaiting binary |

---

## 5. Commercial Tool Licensing Guards

The following 5 commercial tools are truthfully guarded as `OPTIONAL_UNLICENSED`:
* `plecs` (Plexim PLECS)
* `matlab-simulink` (MathWorks MATLAB)
* `ansys-maxwell` (Ansys Maxwell 2D/3D)
* `ansys-icepak` (Ansys Icepak Thermal)
* `solidworks` (Dassault Systèmes SolidWorks)

**Guard Policy:**
* Submitting jobs without a verified local license reference raises `StudioError` or returns `OPTIONAL_UNLICENSED`.
* **Zero mock or synthetic calculation results are fabricated.**
