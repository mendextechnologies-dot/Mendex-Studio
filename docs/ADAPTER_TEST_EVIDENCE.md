# Adapter Test Evidence & Verification Records • Mendex Studio v1.5

**Date:** 10 November 2026  
**Status:** Reproducible Integration Evidence  
**Auditor / Integrator:** Agent 2 (Antigravity), Engineering Integration Lead

---

## 1. LTspice Headless Batch Simulation Verification (#ltspice-smoke)

### 1.1 Environment & Tool Metadata
- **Tool ID:** `ltspice`
- **Installed Executable:** `C:\Program Files\ADI\LTspice\LTspice.exe`
- **Detected File Version:** `26.1.1.0`
- **Operating System:** Windows 11 Pro 64-bit (10.0.26100)
- **Execution Mode:** Non-interactive, headless batch mode with ASCII raw export:
  ```powershell
  & "C:\Program Files\ADI\LTspice\LTspice.exe" -b -ascii <netlist-path>
  ```

### 1.2 Benchmark Circuit Specification
- **Benchmark Name:** `Mendex RC Filter Transient Benchmark`
- **Netlist Content:**
  ```spice
  * Mendex RC Filter Benchmark
  V1 in 0 10.0
  R1 in out 1k
  C1 out 0 1u
  .tran 100u 1m
  .end
  ```
- **Netlist File Hash (SHA-256):** `94a289b4f2c8d234a491d964ef72dca66847c2317c0507ae2798e3b7b62e49c7`

### 1.3 Execution Trace & Log Output
- **Exit Code:** `0`
- **Process Status:** `JobStatus.SUCCEEDED`
- **Measured Elapsed Time:** `0.038 s`
- **Thread Count Utilized:** `16`
- **Solver Warning Count:** `0`
- **Solver Error Count:** `0`
- **Operating Point Convergence:** `Direct Newton iteration succeeded in finding operating point.`
- **Generated Artifacts:**
  - `circuit.log`: ASCII simulation log (`text/plain`), SHA-256 verified.
  - `circuit.raw`: ASCII simulation waveform dataset (`application/octet-stream`), SHA-256 verified.
  - `circuit.op.raw`: Operating point snapshot, SHA-256 verified.

---

## 2. Python Runtime Execution Verification (#python-smoke)

### 2.1 Environment & Tool Metadata
- **Tool ID:** `python`
- **Installed Executable:** `.venv\Scripts\python.exe`
- **Runtime Version:** `Python 3.13.7`
- **Execution Mode:** Safe subprocess runner (`shell=False`, argument list, isolated directory).

### 2.2 Benchmark Script
- **Operation:** `run_script`
- **Script:**
  ```python
  import math
  freq = 100e3
  inductance = 150e-6
  omega = 2 * math.pi * freq
  reactance = omega * inductance
  print(f"REACTANCE_OHMS={reactance:.4f}")
  ```
- **Exit Code:** `0`
- **Process Status:** `JobStatus.SUCCEEDED`
- **Output:** `REACTANCE_OHMS=94.2478`

---

## 3. Git CLI Integration Verification (#git-smoke)

### 3.1 Environment & Tool Metadata
- **Tool ID:** `git`
- **Installed Executable:** `C:\Program Files\Git\cmd\git.EXE`
- **Tool Version:** `2.45.2.windows.1`
- **Operations Verified:**
  - `rev_parse`: Successfully resolves current commit `HEAD`.
  - `status`: Clean working tree detection.
  - `hash_object`: Deterministic object hashing.

---

## 4. Truthful Status for Remaining 15 Tools & Datasets

| Tool ID | Category | State | Reason / Verified Evidence |
|---|---|---|---|
| `switchlossdb` | Dataset | `READY_FOR_IMPORT` | CSV schema validator & SHA-256 parser tested |
| `magnet-dataset` | Dataset | `READY_FOR_IMPORT` | JSON schema validator & SHA-256 parser tested |
| `magnet-ml-benchmarks` | Benchmark | `READY_FOR_IMPORT` | Benchmark metric schema verified |
| `magnet-princeton` | Research Resource | `REFERENCE_ONLY` | Academic research reference hub |
| `kicad` | Application | `NOT_INSTALLED` | `kicad-cli.exe` not present on host; non-destructive probe |
| `femm` | Application | `NOT_INSTALLED` | `femm.exe` not present on host; non-destructive probe |
| `freecad` | Application | `NOT_INSTALLED` | `FreeCADCmd.exe` not present on host; non-destructive probe |
| `qucs-s` | Application | `NOT_INSTALLED` | `qucs-s.exe` not present on host; non-destructive probe |
| `openmodelica` | Application | `NOT_INSTALLED` | `omc.exe` not present on host; non-destructive probe |
| `jupyter` | Application | `NOT_INSTALLED` | `jupyter.exe` not present on host; non-destructive probe |
| `plecs` | Application | `OPTIONAL_UNLICENSED` | License-gated commercial stub |
| `matlab-simulink` | Application | `OPTIONAL_UNLICENSED` | License-gated commercial stub |
| `ansys-maxwell` | Application | `OPTIONAL_UNLICENSED` | License-gated commercial stub |
| `ansys-icepak` | Application | `OPTIONAL_UNLICENSED` | License-gated commercial stub |
| `solidworks` | Application | `OPTIONAL_UNLICENSED` | License-gated commercial stub |

*All evidence is generated without modifying frozen baselines or manufacturing fake simulation results.*
