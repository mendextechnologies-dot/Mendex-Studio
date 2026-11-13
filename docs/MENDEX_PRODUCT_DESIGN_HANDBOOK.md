# Mendex Engineering Studio v3.1
# The Complete End-to-End Product Design Handbook
### Autonomous Power Electronics Engineering with Codex, Open-Source Solvers & the React Command Center

**Document Version**: 3.1.0  
**Target Architecture**: Codex-First Engineering Architecture  
**Authoritative Core**: Python Mendex Engineering Core (`src/mendex_core/`)  
**Presentation Client**: React 18 + TypeScript + Vite Command Center (`http://localhost:5173`)  
**Audience**: Power Electronics Engineers, Hardware Designers, Technical Leads, and Autonomous AI Agents (OpenAI Codex, Claude Code, Antigravity)

---

## 1. Architectural Principles & Operating Rules

Mendex Engineering Studio v3.1 operates on a strict **Codex-First Architecture**. The system enforces absolute separation of responsibilities:

```text
Engineer / AI Designer
    │
VS Code + Codex / Antigravity / Claude Code
    │
Generic 9-Stage AI Workflow Prompts (engineering-workflows/stages/)
    │
Mendex MCP (58 Tools)  /  Mendex CLI (`mendex`)
    │
Python Mendex Engineering Core (`src/mendex_core/`)
    ├── Deterministic Calculations (Dowell, Steinmetz, IEC 61010-1)
    ├── Local Solver Runners (LTspice, FEMM, KiCad, FreeCAD)
    └── Immutable Storage (SQLite studio.sqlite3 + SHA-256 Evidence)
    │
Mendex Studio Command Center (`http://localhost:5173`)
(Real-Time Read-Only Engineering Dashboard & Solver Monitor)
```

### Core Engineering Rules (Never Violate)
1. **Zero Fabrication**: Calculations, simulation outputs, and validation metrics are strictly deterministic. Unperformed checks must remain `NOT_EVALUATED`. Never invent or hallucinate physical results.
2. **Immutable History**: Historical revisions, frozen baselines, and raw evidence (`.raw`, `.csv`, `.log`) are never altered or overwritten.
3. **Single Core Authority**: All user-facing clients (MCP, CLI, and Command Center) interact solely with the authoritative Python core services.
4. **Authoritative Local Solvers**: Physics simulations must be executed through real host binaries (LTspice XVII, FEMM 4.2, KiCad CLI, FreeCAD).

---

## 2. System Environment & Toolchain Qualification

### 2.1 Starting the Desktop Command Center
To launch the real-time visualization command center:
- **1-Click Launcher**: Double-click `start_desktop.bat` in the repository root.
- **Manual Launch**:
  ```bash
  cd desktop
  npm run dev
  ```
- Open your browser to `http://localhost:5173`.
- The dashboard automatically bridges to Python via unbuffered stdio RPC and updates every 4 seconds.

### 2.2 Verifying Local Engineering Solvers
Check solver readiness either via CLI or in the web UI:
- **In Command Center**: Navigate to **Engineering Tools** (`http://localhost:5173/?page=tools`). All 13 solver connectors must display a green `READY` badge with resolved host binary paths.
- **Via CLI**:
  ```bash
  python -m mendex_core.cli doctor
  ```

---

## 3. The Canonical 9-Stage Engineering Lifecycle

Every product revision progresses through nine canonical lifecycle stages:

| Stage # | Stage Name | Purpose | Primary Output Artifacts |
| :---: | :--- | :--- | :--- |
| **1** | `project_initialization` | Register identity, revision R001, workspace layout | `project_metadata.json`, workspace directories |
| **2** | `requirements` | Record electrical, isolation, thermal envelope | Authoritative specification (SHA-256 hash) |
| **3** | `feasibility` | Topology trade-off & switch stress estimation | `feasibility_report.md` |
| **4** | `calculations` | Deterministic turns ratio, Dowell $F_r$, Steinmetz losses | `calculations/sizing_analysis.json` |
| **5** | `design_development` | Native schematic, 2-layer PCB, 3D bobbin model | `.kicad_sch`, `.kicad_pcb`, `bobbin.step` |
| **6** | `simulation` | Headless SPICE transient and 2D FEA magnetics | `circuit.raw`, `femm_mesh.ans` |
| **7** | `verification` | KiCad ERC/DRC checks, IPC-9592B stress deratings | `erc_report.txt`, `drc_report.txt` |
| **8** | `prototype_testing` | Laboratory hi-pot, oscilloscope, thermal imaging | Lab waveforms, hipot test certificates |
| **9** | `documentation` | Production BOM and print-ready Engineering Dossier | `bom.csv`, `bom.json`, `report.html` |

---

## 4. Stage-by-Stage Implementation Manual

### Stage 1: Project Initialization

#### Objective
Create the authoritative product record in SQLite, establish revision `R001`, auto-enroll the canonical 9-stage lifecycle, and create the workspace folder.

#### Execution Methods
- **Via MCP**:
  ```json
  // Tool: create_project
  {
    "name": "SpectraVolt SV-1000",
    "code": "SV-1000",
    "category": "dc_dc_converter",
    "owner": "Lead Power Electronics Engineer",
    "description": "High-Voltage Isolated DC-DC Converter (24V to 1000V 100W)"
  }
  ```
- **Via CLI**:
  ```bash
  python -m mendex_core.cli create-project "SpectraVolt SV-1000" --code SV-1000 --category dc_dc_converter --owner "Lead Power Electronics Engineer"
  ```

#### Stage Lifecycle Progression
```bash
# Start stage 1
python -m mendex_core.cli lifecycle apply '{"project_id": "<PROJECT_UUID>", "stage_id": "project_initialization", "action": "start"}'

# Complete stage 1
python -m mendex_core.cli lifecycle apply '{"project_id": "<PROJECT_UUID>", "stage_id": "project_initialization", "action": "complete"}'
```

---

### Stage 2: Requirements & Electrical Specifications

#### Objective
Formulate the exact physical specification envelope. The Core computes an immutable SHA-256 specification digest that binds to all subsequent calculations and simulation runs.

#### Specification Envelope Schema
- Input Voltage Range ($V_{in}$): $20.0\text{ V}$ to $28.0\text{ V}$ ($24.0\text{ V}$ nominal)
- Output Voltage ($V_{out}$): $1000.0\text{ V DC} \pm 1.0\%$
- Output Current / Power ($I_{out}, P_{out}$): $0.1\text{ A}$ ($100.0\text{ W}$)
- Switching Frequency ($f_{sw}$): $100.0\text{ kHz}$
- Galvanic Isolation: $3000\text{ V RMS}$ (IEC 61010-1 basic/reinforced)
- Ambient Temperature ($T_{amb}$): $-20^\circ\text{C}$ to $+55^\circ\text{C}$

#### Execution Methods
- **Via MCP**:
  ```json
  // Tool: save_project_specification
  {
    "project_id": "<PROJECT_UUID>",
    "specification": {
      "vin_min": 20.0,
      "vin_nom": 24.0,
      "vin_max": 28.0,
      "vout_nom": 1000.0,
      "vout_tolerance_pct": 1.0,
      "iout_nom": 0.1,
      "pout_nom": 100.0,
      "fsw_hz": 100000.0,
      "isolation_voltage_vrms": 3000.0,
      "standards_profile": "IEC-61010-1",
      "target_efficiency": 0.90
    }
  }
  ```
- **Via CLI**:
  ```bash
  python -m mendex_core.cli project save-spec <PROJECT_UUID> '{"vin_min": 20.0, "vin_nom": 24.0, "vin_max": 28.0, "vout_nom": 1000.0, "vout_tolerance_pct": 1.0, "iout_nom": 0.1, "pout_nom": 100.0, "fsw_hz": 100000.0, "isolation_voltage_vrms": 3000.0, "standards_profile": "IEC-61010-1", "target_efficiency": 0.90}'
  ```

---

### Stage 3: Feasibility & Architecture Selection

#### Objective
Evaluate power conversion topologies and calculate primary switch and secondary rectifier voltage stresses to select optimal semiconductor technologies.

#### Power Converter Mathematics
1. **Topology Selection**: High-Voltage Isolated Flyback Converter with primary RCD snubber clamp. Chosen for single-switch simplicity, galvanic safety, and wide $V_{in}$ range.
2. **Primary Switch Voltage Stress**:
   $$V_{ds,pk} = V_{in,max} + \frac{V_{out} + V_F}{n} + V_{spike}$$
   - Given $V_{in,max} = 28\text{ V}$, $n = 30$, $V_{out} = 1000\text{ V}$, clamp spike allowance $V_{spike} = 150\text{ V}$:
   $$V_{ds,pk} \approx 28\text{ V} + \frac{1001\text{ V}}{30} + 150\text{ V} \approx 211.4\text{ V}$$
   - *Selection*: $650\text{ V}$ / $1200\text{ V}$ SiC MOSFET provides $>3\times$ safety margin.
3. **Secondary Rectifier Diode Stress**:
   $$V_{rr} \approx V_{out} + n \cdot V_{in,max} = 1000\text{ V} + (30 \times 28\text{ V}) = 1840\text{ V}$$
   - *Selection*: $2000\text{ V}$ SiC Schottky Diode (e.g. Wolfspeed C3D02060E or series SiC diodes) eliminating reverse recovery losses ($Q_{rr} \approx 0$).

#### Artifact
Save feasibility report to workspace using template [`engineering-workflows/templates/feasibility_report.md`](file:///c:/Mendex%20studio/engineering-workflows/templates/feasibility_report.md).

---

### Stage 4: Deterministic Calculations

#### Objective
Execute mathematical sizing, high-frequency magnetic losses, and safety spacing through Mendex Core's deterministic calculation service.

#### Formulas & Physical Calculations
1. **Primary Magnetizing Inductance ($L_p$)**:
   Operating in Discontinuous Conduction Mode (DCM) / Boundary Mode with maximum duty cycle $D_{max} = 0.45$:
   $$L_p = \frac{(V_{in,min} \cdot D_{max})^2}{2 \cdot (P_{out} / \eta) \cdot f_{sw}} = \frac{(20\text{ V} \times 0.45)^2}{2 \times (100\text{ W} / 0.90) \times 100\text{ kHz}} \approx 36.45\ \mu\text{H} \rightarrow \text{Budget } 48\ \mu\text{H}$$
2. **Turns Ratio ($n = N_s / N_p$)**:
   $$\frac{V_{out} + V_F}{V_{in,min}} \cdot \frac{1 - D_{max}}{D_{max}} = \frac{1001}{20} \cdot \frac{0.55}{0.45} \approx 61.1 \rightarrow \text{Optimal turns ratio } n = 30:1$$
   - Primary turns: $N_p = 4\text{ turns}$ (copper foil or multi-strand Litz)
   - Secondary turns: $N_s = 120\text{ turns}$
3. **Skin Depth & Dowell AC Winding Factor ($F_r$)**:
   $$\delta = \frac{1}{\sqrt{\pi f \mu_0 \sigma}} = \frac{66.1}{\sqrt{100000}} \approx 0.209\text{ mm at } 75^\circ\text{C}$$
   - Using 40-strand triple-insulated Litz wire ($d_{strand} = 0.1\text{ mm} < 2\delta$):
   $$F_r = \frac{R_{ac}}{R_{dc}} \approx 1.18 \quad (R_{dc} = 120\text{ m}\Omega \rightarrow R_{ac} = 141.6\text{ m}\Omega)$$
4. **Modified Steinmetz Volumetric Core Loss (TDK N87 Ferrite)**:
   $$P_v = C_m \cdot f^\alpha \cdot B_{pk}^\beta$$
   - For TDK N87: $C_m = 16.9$, $\alpha = 1.25$, $\beta = 2.35$.
   - Operating at $\Delta B = 0.28\text{ T}$ ($< B_{sat} = 0.39\text{ T}$):
   $$P_{core} = P_v \cdot V_e = 84.5\text{ kW/m}^3 \times 14.1\times 10^{-6}\text{ m}^3 \approx 1.19\text{ W}$$
5. **IEC 61010-1 High-Voltage Isolation Spacing**:
   - Working Voltage: $1000\text{ V DC}$ with $3000\text{ V RMS}$ dielectric withstand test.
   - Required Basic Clearance: $3.2\text{ mm}$.
   - Required Reinforced Creepage (Pollution Degree 2, Material Group IIIa): $4.8\text{ mm}$.
   - Engineered PCB Allocation: **$5.0\text{ mm}$ physical air milling slot** under the transformer isolation barrier.

#### Execution Methods
```json
// MCP Tool: record_calculation_run
{
  "calculator_id": "flyback_transformer_sizing",
  "inputs": {
    "vin_min": 20.0,
    "vin_max": 28.0,
    "vout": 1000.0,
    "pout": 100.0,
    "fsw": 100000.0,
    "efficiency": 0.90
  }
}
```

---

### Stage 5: Design Development (CAD Synthesis)

#### Objective
Synthesize production-grade native design files directly inside the revision workspace (`kicad/` and `cad/`).

#### Generated Artifacts
1. **KiCad Schematic (`kicad/sv1000.kicad_sch`)**:
   - Power Stage: Primary SiC MOSFET (C3M0075120K), ETD34 Flyback Transformer, RCD Snubber clamp, Secondary High-Voltage SiC Schottky Diode.
   - Feedback: TL431 + Optocoupler isolation loop providing 1000 V regulation with $3000\text{ V}$ isolation barrier.
2. **KiCad PCB Layout (`kicad/sv1000.kicad_pcb`)**:
   - 2-layer FR-4 PCB ($1.6\text{ mm}$ thickness, $2\text{ oz}$ copper).
   - High-voltage isolation slot cut on layer `Edge.Cuts` ($5.0\text{ mm}$ wide $\times 35.0\text{ mm}$ long) separating primary ground from secondary return.
3. **FreeCAD 3D Bobbin Model (`cad/etd34_bobbin.step`)**:
   - Parametric 3D solid model of the transformer bobbin featuring primary and secondary winding bays with physical creepage barriers.

---

### Stage 6: Solver Execution & Physical Simulation

#### Objective
Execute headless physical simulations using native tools installed on the host.

#### 1. Headless LTspice Transient Simulation
- **Circuit Netlist**: Synthesize `simulations/flyback_circuit.net` with $45\%$ PWM switching drive and $1000\text{ V}$ load resistor ($R_L = 10\text{ k}\Omega$).
- **Command / MCP Call**:
  ```json
  // MCP Tool: run_simulation
  {
    "tool_id": "ltspice",
    "operation": "transient",
    "circuit_file": "simulations/flyback_circuit.net",
    "parameters": { "stop_time": "2ms" }
  }
  ```
- **Output**: Produces binary waveform `flyback_circuit.raw`. Parses steady-state regulation: $V_{out} = 1000.4\text{ V}$ DC, ripple $= 7.2\text{ V}_{pk-pk}$ ($0.72\% \le 1.0\%$).

#### 2. Headless FEMM 4.2 2D Magnetics FEA
- **Script**: Lua script `simulations/etd34_core.lua` setting up the ETD34 ferrite geometry, air gap ($g = 0.45\text{ mm}$), and excitation current ($I_{pk} = 8.33\text{ A}$).
- **Command / MCP Call**:
  ```json
  // MCP Tool: run_simulation
  {
    "tool_id": "femm",
    "operation": "magnetics",
    "script_file": "simulations/etd34_core.lua"
  }
  ```
- **Output**: 2D magnetic solution `etd34_core.ans`. Evaluates peak flux density: $B_{pk} = 0.282\text{ T} < 0.35\text{ T}$, confirming magnetic headroom.

---

### Stage 7: Automated Verification & Stress Derating

#### Objective
Run automated Electrical and Design Rules checks and enforce component stress derating against standard reliability guidelines.

#### 1. KiCad CLI Automated Rules Check
- Headless ERC:
  ```bash
  kicad-cli sch erc --severity-error --output erc_report.txt kicad/sv1000.kicad_sch
  ```
  *Result*: 0 errors.
- Headless DRC:
  ```bash
  kicad-cli pcb drc --output drc_report.txt kicad/sv1000.kicad_pcb
  ```
  *Result*: 0 violations; confirmed $5.0\text{ mm}$ physical creepage slot clearance.

#### 2. IPC-9592B Component Stress Audit
Mendex Core evaluates peak electrical and thermal stress margins:

| Component | Designator | Parameter | Measured / Simulated | Absolute Rating | Stress Ratio | Limit | Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| SiC MOSFET | `Q1` | $V_{ds}$ | $211.4\text{ V}$ | $1200\text{ V}$ | $17.6\%$ | $\le 75\%$ | **PASS** |
| SiC MOSFET | `Q1` | $I_{d,rms}$ | $2.85\text{ A}$ | $30.0\text{ A}$ | $9.5\%$ | $\le 70\%$ | **PASS** |
| HV Rectifier | `D1` | $V_{rr}$ | $1840\text{ V}$ | $2000\text{ V}$ | $92.0\%$ | $\le 95\%$ | **PASS** |
| Filter Cap | `C_OUT` | $V_{dc}$ | $1000\text{ V}$ | $1500\text{ V}$ | $66.7\%$ | $\le 80\%$ | **PASS** |
| Transformer | `T1` | $T_{hotspot}$ | $78.5^\circ\text{C}$ | $125^\circ\text{C}$ | $62.8\%$ | $\le 80\%$ | **PASS** |

---

### Stage 8: Physical Prototype Lab Testing Evidence

#### Objective
Ingest physical bench test measurements into the immutable evidence registry with SHA-256 integrity verification.

#### Required Evidence Types
1. **Dielectric Hi-Pot Test Record**: $3000\text{ V RMS}$ applied across isolation barrier for 60 seconds. Measured leakage current $I_{leak} = 4.2\ \mu\text{A}$ ($< 10\ \mu\text{A}$ threshold). Attached as `evidence/hipot_test_certificate.pdf`.
2. **Oscilloscope Waveform Capture**: Drain-to-source voltage and secondary diode waveforms logged at $100\text{ W}$ continuous load (`evidence/switching_waveform_ch1_ch2.csv`).
3. **Thermal Radiometric Survey**: Thermal imaging showing maximum surface temperature $T_{max} = 68.4^\circ\text{C}$ at $25^\circ\text{C}$ ambient (`evidence/thermal_radiometric_map.png`).

---

### Stage 9: Production Documentation & Release Dossier

#### Objective
Compile the qualified Bill of Materials and generate the formal, print-ready Engineering Dossier.

#### 1. Qualified Bill of Materials (`bom/bom.csv`)
```csv
Reference,Part Number,Manufacturer,Description,Package,Quantity,Unit Cost (USD)
Q1,C3M0075120K,Wolfspeed,SiC Power MOSFET 1200V 75mOhm,TO-247-4,1,14.85
D1,C3D02060E,Wolfspeed,High-Voltage SiC Schottky Diode 2000V 2A,TO-220-2,1,8.40
T1,CUSTOM-ETD34-N87,TDK Electronics,Custom Flyback Transformer 48uH 30:1 3kV,ETD34,1,16.50
C1,C4AF3BW5100A3OK,KEMET,High-Voltage Polypropylene Film Cap 100nF 1500V,Radial,2,4.20
R_SNUB,RH050100R0FE02,Vishay Dale,Wirewound Aluminum Housed Resistor 100 Ohm 50W,Chassis,1,5.10
U1,FOD817D300,ON Semiconductor,High-Voltage Optocoupler 5000Vrms CTR 300%,DIP-4,1,0.65
```

#### 2. Generating the Executive Engineering Dossier
- **Command / MCP Call**:
  ```json
  // MCP Tool: generate_engineering_report
  {
    "project_id": "<PROJECT_UUID>",
    "title": "SpectraVolt SV-1000 Engineering Dossier"
  }
  ```
- Mendex Core produces `report.html`, embedding:
  - KPI summary and 9-stage lifecycle maturity matrix.
  - Sizing calculations with KaTeX equations.
  - Simulation waveform plots and FEMM flux density contours.
  - IPC-9592B derating compliance table.
  - Itemized Bill of Materials with unit pricing.
  - Cryptographic SHA-256 evidence digests.

---

## 5. Revision Management & Trade-Off Branching

When engineering trade-offs require exploration (e.g. comparing ETD34 vs PQ26 core, or comparing GaN vs SiC switches):
1. **Never mutate the frozen revision**: Existing records in `R001` remain immutable.
2. **Branch a new revision (`R002`)**:
   ```json
   // MCP Tool: create_revision
   {
     "project_id": "<PROJECT_UUID>",
     "source_revision_id": "<R001_UUID>",
     "label": "R002",
     "description": "Exploration of planar PQ26/20 core and 650V GaN switch"
   }
   ```
3. Run Stage 4 calculations and Stage 6 simulations under `R002`.
4. Inspect the delta in the Command Center under the **Revisions** tab.

---

## 6. Command Center Live Visibility Cheat Sheet

| Command Center Route / Tab | What to Inspect During Design |
| :--- | :--- |
| **Dashboard** (`/?page=dashboard`) | Total authoritative projects, completed simulations, active revision badge |
| **Engineering Tools** (`/?page=tools`) | All 13 solver runners status (`READY`), host paths for KiCad, FEMM, LTspice |
| **Project: Overview** (`tab=overview`) | Active revision label, input specification SHA-256 hash, operating limits |
| **Project: Lifecycle** (`tab=lifecycle`) | 9-stage progression timeline with blockers and review gates |
| **Project: Specifications** (`tab=specifications`) | Typed SI voltage, current, power, and frequency envelope |
| **Project: Calculations** (`tab=calculations`) | Sizing runs, Dowell $F_r$, Steinmetz losses, creepage formulas |
| **Project: Simulations** (`tab=simulations`) | Solver execution timestamps, exit codes, and raw waveforms |
| **Project: Designs** (`tab=designs`) | Registered KiCad schematic, PCB layout, and FreeCAD 3D models |
| **Project: Files** (`tab=files`) | Workspace file tree with 1-click **Open in native application** buttons |
| **Project: Validation** (`tab=validation`) | ERC/DRC check summaries and IPC-9592B derating safety audit |
| **Project: Reports** (`tab=reports`) | Print-ready Engineering Dossier with 1-click browser viewer |

---

## 7. Summary & Quick Reference

To start designing a new power electronics product from scratch:
1. Double-click `start_desktop.bat` to bring up the Command Center.
2. Direct Codex to read `engineering-workflows/MASTER_ENGINEERING_INSTRUCTIONS.md`.
3. Feed the Stage 1 prompt (`engineering-workflows/stages/01_project_initialization.md`).
4. Follow the step-by-step instructions in this handbook through Stage 9.
5. All calculations, simulations, rules checks, and evidence digests are permanently preserved in `.mendex/studio.sqlite3`.
