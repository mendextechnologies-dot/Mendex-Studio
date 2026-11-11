# Mendex Engineering CLI v2.1 — Command Reference

The Mendex CLI (`python -m mendex_core.cli`) provides direct terminal access to all Mendex Engineering Core operations. All commands output structured JSON.

---

## 1. Global Options

```bash
# Set custom data root
python -m mendex_core.cli --root C:\Mendex studio <command>

# Ensure JSON output
python -m mendex_core.cli --json <command>
```

---

## 2. Workspace Management

### List Workspaces
```bash
python -m mendex_core.cli workspace list
```

### Create Workspace
```bash
python -m mendex_core.cli workspace create "Buck 20W DC-DC" --description "Industrial Step-Down Converter"
```

### Workspace Status
```bash
python -m mendex_core.cli workspace status <workspace_uuid>
```

---

## 3. Specification Validation

### Validate Operating Parameters
```bash
python -m mendex_core.cli specification validate '{"vin_min_v": 18.0, "vin_nom_v": 24.0, "vin_max_v": 32.0, "vout_v": 5.0, "iout_a": 4.0, "switching_frequency_hz": 100000.0}'
```

### Save Specification to Revision
```bash
python -m mendex_core.cli specification save <revision_uuid> '{"vin_nom_v": 24.0, "vout_v": 5.0, "iout_a": 4.0}'
```

---

## 4. Design Synthesis

### Synthesize Candidate Topologies & Native Artifacts
```bash
python -m mendex_core.cli design generate \
  --workspace <workspace_uuid> \
  --title "Synchronous Buck Converter 20W" \
  --category "dc_dc_converter" \
  --vin-nom 24.0 \
  --vin-min 18.0 \
  --vin-max 32.0 \
  --vout 5.0 \
  --iout 4.0 \
  --fsw 100000.0 \
  --ripple 0.05
```

### Show Design Details
```bash
python -m mendex_core.cli design show <design_uuid>
```

### List Synthesized Candidates
```bash
python -m mendex_core.cli design candidates <design_uuid>
```

---

## 5. Engineering Calculations

### Dowell AC Winding Factor
```bash
python -m mendex_core.cli calculate dowell \
  --freq 100000 \
  --layers 2 \
  --wire-dia 0.5 \
  --porosity 0.85 \
  --rdc 0.05 \
  --temp 100.0
```

### Semiconductor Losses (Conduction & Switching)
```bash
python -m mendex_core.cli calculate losses \
  --part "BSC010NE2LS" \
  --rdson 0.015 \
  --irms 4.0 \
  --duty 0.45 \
  --eon 12e-6 \
  --eoff 8e-6 \
  --freq 100000
```

### Steinmetz Core Loss
```bash
python -m mendex_core.cli calculate steinmetz \
  --material "N87" \
  --freq 100000 \
  --bmax 0.15 \
  --volume 1.5e-5 \
  --k 1.5 \
  --alpha 1.3 \
  --beta 2.5
```

### Flyback Transformer Sizing
```bash
python -m mendex_core.cli calculate flyback \
  --vin-min 18.0 \
  --vin-nom 24.0 \
  --vout 12.0 \
  --iout 3.0 \
  --freq 100000 \
  --dmax 0.45 \
  --eff 0.88 \
  --bmax 0.25 \
  --ae 125.0
```

---

## 6. Simulation Dispatch

### Run Headless LTspice Simulation
```bash
python -m mendex_core.cli simulation run \
  --workspace <workspace_uuid> \
  --tool ltspice \
  --duration 0.002
```

### Run Headless FEMM Magnetics
```bash
python -m mendex_core.cli simulation run \
  --workspace <workspace_uuid> \
  --tool femm
```

### List Simulation Runs
```bash
python -m mendex_core.cli simulation list --workspace <workspace_uuid>
```

---

## 7. Artifact Management

### List Native Artifacts in Workspace
```bash
python -m mendex_core.cli artifact list --workspace <workspace_uuid>
```

### Open Artifact in External CAD
```bash
python -m mendex_core.cli artifact open \
  --workspace <workspace_uuid> \
  --file "generated_artifacts/rev_1/kicad/buck.kicad_sch"
```

---

## 8. Tool Management & Diagnostics

### List Installed Engineering Tools
```bash
python -m mendex_core.cli tool list
```

### Live Diagnostic Check
```bash
python -m mendex_core.cli tool check ltspice
```

### System Doctor & Diagnostics Export
```bash
python -m mendex_core.cli doctor --export
```
