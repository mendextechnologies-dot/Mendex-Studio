# Mendex Engineering Studio v1.8 — Release Readiness & Installation Guide

## 1. Release Overview

- **Release Version**: `0.1.0` (Mendex Engineering Studio v1.8)
- **Target OS**: Windows 10 / Windows 11 (64-bit)
- **Primary Runtime**: Python 3.11 – 3.13 (Verified on Python 3.13.7)
- **Packaging Format**: Standard Python Wheel (`.whl`), Source Archive (`.zip`), and SHA-256 Checksums (`SHA256SUMS.txt`).

---

## 2. Release Artifacts & Cryptographic Checksums

The release artifacts were built using `scripts/package.ps1` and are stored under `dist/`:

| Artifact File | Size (Bytes) | SHA-256 Checksum |
|---|---|---|
| `mendex_studio-0.1.0-py3-none-any.whl` | 129,735 | `b7ba1a4653e1b23717f8010be75a8b015f87a361a4508385c50145c8c7b92634` |
| `mendex-studio-0.1.0-source.zip` | 1,799,162 | `2297ea02c21c97b09b67b18357697b839c53b6d277cafe553849f40e4474ecc2` |
| `mendex-studio-0.1.0-SHA256SUMS.txt` | 202 | — |

---

## 3. System Requirements & External Solvers

### Minimum Hardware
- **Processor**: Intel Core i5 / AMD Ryzen 5 (4+ physical cores recommended for FEA/SPICE).
- **RAM**: 8 GB minimum (16 GB recommended for 2D/3D meshing).
- **Display**: $1920 \times 1080$ recommended (Qt High-DPI scaling fully supported for $4\text{K}$ monitors).
- **Storage**: 500 MB for Studio runtime + space for simulation cache.

### Supported External Engineering Solvers
For complete simulation and design capabilities, the following open-source tools should be installed on the host machine:

1. **ADI LTspice**: Default path `C:\Program Files\ADI\LTspice\LTspice.exe`
2. **KiCad EDA (v8+)**: Default path `C:\Program Files\KiCad\10.0\bin\kicad-cli.exe`
3. **FEMM 4.2**: Default path `C:\femm42\bin\femm.exe`
4. **FreeCAD (v0.21+)**: Default path `C:\Program Files\FreeCAD 1.1\bin\freecadcmd.exe`
5. **Qucs-S & ngspice (v42+)**: Default path `%LOCALAPPDATA%\Programs\qucs-s\bin\`
6. **OpenModelica (v1.20+)**: Default path `C:\Program Files\OpenModelica1.26.3-64bit\bin\omc.exe`

*(Note: In the absence of any solver, Mendex Studio safely marks that specific tool as `NOT_CONFIGURED` without crashing or disabling remaining features.)*

---

## 4. Clean Machine Installation Guide

### Step 1: Create an Isolated Python Environment
```powershell
python -m venv C:\MendexDeploy\venv
C:\MendexDeploy\venv\Scripts\Activate.ps1
```

### Step 2: Install the Wheel
```powershell
pip install --upgrade pip
pip install C:\Mendex studio\dist\mendex_studio-0.1.0-py3-none-any.whl
```

### Step 3: Verify Installation
```powershell
mendex-studio --version
# Expected: mendex-studio 0.1.0
```

### Step 4: Launch the Studio
```powershell
# Launch interactive desktop GUI
mendex-studio

# Or run diagnostic health check via CLI
mendex-studio doctor
```

---

## 5. Verification & Smoke Testing Procedures

To run automated smoke verification on a new installation:

```powershell
# Run headless desktop smoke test
python scripts/desktop_smoke.py

# Run v1.8 enterprise feature smoke test (produces screenshots under .mendex/qa/)
python scripts/v17_enterprise_smoke.py
```

---

## 6. Troubleshooting & Operational Failure Modes

| Issue / Symptom | Root Cause | Resolution |
|---|---|---|
| **Qt High-DPI Scaling Blur / Cutoff** | Windows display scaling set to 125% or 150% without Qt DPI awareness | Mendex Studio automatically sets `QT_ENABLE_HIGHDPI_SCALING=1` and `QT_SCALE_FACTOR_ROUNDING_POLICY=PassThrough` in `main.py`. |
| **Solver execution fails with `Executable not found`** | Custom installation directory not in standard paths | Open **Tool Center** (`Ctrl+K` -> "Tool Center"), click the tool, and enter the custom binary path. |
| **Simulation jobs time out** | Complex circuit or FEA mesh taking excessive CPU time | Increase the per-activity timeout in the Simulation Lab panel (default is 120 seconds). |
| **`Permission Denied` creating workspace** | Target folder requires administrative rights (e.g. `C:\Program Files`) | Choose an engineering workspace location under user directories (`C:\Users\<user>\Engineering` or `D:\EngineeringWorkspaces`). |
| **Commercial tools report `REFUSED_NO_LICENSE`** | Commercial tool (e.g. PLECS or MATLAB) selected without license | Commercial tools are guarded by design; use supported open-source solvers (LTspice/ngspice) or configure valid license server in settings. |
