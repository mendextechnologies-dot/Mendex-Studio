# Mendex Engineering Studio v2.1 — Engineering Workspace Guide

**Architecture Version:** v2.1.0  
**Scope:** Hybrid Workspace Operations via VS Code (Codex & Claude Code) and Mendex Studio GUI.

---

## 1. Unified Engineering Workspace Model

In Mendex Engineering Studio v2.1, an **Engineering Workspace** is a dedicated filesystem directory (`workspaces/<workspace_id>/`) paired with metadata in `.mendex/studio.sqlite3`.

Each workspace manages the end-to-end electrical, magnetic, and physical engineering lifecycle:
1. **Requirements & Specifications**: Electrical input/output ranges, frequency, ripple, isolation.
2. **Design Syntheses**: Multi-candidate topology generation (Synchronous Buck, Isolated Flyback, Push-Pull).
3. **Deterministic Calculations**: Dowell AC winding loss, Steinmetz core loss, semiconductor conduction & switching losses.
4. **Native EDA/CAD Artifacts**:
   - KiCad 9/10 S-expression schematics (`.kicad_sch`) & projects (`.kicad_pro`)
   - KiCad populated PCB layouts (`.kicad_pcb`)
   - LTspice graphical schematics (`.asc`) & simulation netlists (`.net`)
   - FreeCAD 3D ISO 10303 STEP solids (`.step`)
   - FEMM 2D axisymmetric magnetic models (`.lua`)
5. **Simulation Execution**: Headless batch execution via `LTspiceRunner` (generating `.raw` waveforms) and `FEMMRunner`.
6. **Validation & Evidence Dossier**: SHA-256 evidence tracking and frozen verification reports.

---

## 2. Directory Structure of an Engineering Workspace

```text
workspaces/<workspace_id>/
│
├── generated_artifacts/
│   └── rev_1/
│       ├── kicad/
│       │   ├── synchronous_buck_20w.kicad_sch   # Editable schematic
│       │   ├── synchronous_buck_20w.kicad_pro   # KiCad project
│       │   └── synchronous_buck_20w.kicad_pcb   # Populated PCB layout
│       │
│       ├── synchronous_buck_converter_schematic.asc  # LTspice schematic
│       ├── buck_circuit.net                          # SPICE netlist
│       ├── buck_circuit.raw                          # Binary simulation waveforms
│       ├── buck_circuit.log                          # Solver convergence log
│       │
│       ├── magnetic_simulation.lua                   # FEMM FEA script
│       └── bobbin.step                               # 3D mechanical STEP solid
│
└── validation/
    ├── manifests/
    └── evidence_dossier.html
```

---

## 3. Working from VS Code + AI Agents (Codex & Claude Code)

### Step 1: Workspace Creation
From VS Code terminal or via Claude Code:
```bash
python -m mendex_core.cli workspace create "SV-1000 Precision Converter" --description "High-voltage isolated DC-DC stage"
```
Or via MCP:
```json
{
  "name": "create_workspace",
  "arguments": {
    "name": "SV-1000 Precision Converter",
    "description": "High-voltage isolated DC-DC stage"
  }
}
```

### Step 2: Specification Validation & Sizing
Validate input constraints before synthesis:
```bash
python -m mendex_core.cli specification validate '{"vin_nom_v": 24.0, "vout_v": 1000.0, "iout_a": 0.1, "switching_frequency_hz": 100000.0}'
```

### Step 3: Design Generation
Synthesize topologies and compile native CAD files:
```bash
python -m mendex_core.cli design generate --workspace <workspace_id> --title "SV-1000 Flyback" --category "isolated_dc_dc" --vin-nom 24.0 --vout 1000.0 --iout 0.1 --isolation 3000.0
```

### Step 4: Analytical Calculations
Run first-principles calculations:
```bash
# Dowell AC loss factor
python -m mendex_core.cli calculate dowell --freq 100000 --layers 3 --wire-dia 0.35

# Semiconductor losses
python -m mendex_core.cli calculate losses --part "C3M0065090D" --rdson 0.065 --irms 1.5 --duty 0.45 --freq 100000

# Steinmetz core loss
python -m mendex_core.cli calculate steinmetz --material "N87" --freq 100000 --bmax 0.2 --volume 2e-5
```

---

## 4. Working from Mendex Engineering Studio GUI

1. **Dashboard**: Inspect system-wide status, solver readiness, recent jobs, and active projects.
2. **Engineering Workspaces**:
   - Inspect the 12-Stage Lifecycle Overview.
   - Click **Open Schematic in KiCad** to inspect `.kicad_sch` directly in Eeschema.
   - Click **Open PCB in KiCad** to inspect footprint placement and clearance in Pcbnew.
   - Click **Run KiCad ERC** to run live batch electrical rule checks.
   - Click **Specification & Revisions Editor** to edit parameters or freeze new revision baselines.
3. **Simulation Center**:
   - Execute LTspice transient simulations.
   - View interactive waveforms with voltage/current trace inspection.
4. **Component Library**:
   - Browse verified power MOSFETs, SiC devices, and ferrite core geometries.
5. **Engineering Tools**:
   - Verify tool installation paths (LTspice, KiCad, FEMM, FreeCAD).
6. **Reports & Evidence**:
   - Generate immutable engineering verification dossiers.
7. **Settings**:
   - Review MCP connection strings and database health.
