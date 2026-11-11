# Mendex Engineering Studio v2.1 — Target Architecture Specification

**Version:** 2.1.0  
**Status:** Approved Architecture Blueprint  
**Primary Integration Agents:** OpenAI Codex & Anthropic Claude Code (via VS Code)  
**Execution Core:** Mendex Engineering Core  
**Visualization & Governance:** Mendex Engineering Studio Desktop  

---

## 1. System Overview & Philosophy

Mendex Engineering Studio v2.1 adopts a **hybrid, agent-orchestrated power electronics engineering architecture**.

Instead of attempting to recreate interactive AI chat windows, visual node-graph workflow editors, and circuit CAD editors inside a single monolithic desktop GUI, v2.1 cleanly separates responsibilities:

1. **AI Interaction & Orchestration (VS Code + Codex / Claude Code):** Engineers interact with AI assistants inside their natural code editor. The AI interprets specifications, queries calculation tools, requests design generation, schedules batch simulations, and analyzes waveforms.
2. **Standardized Integration Layer (CLI & MCP Server):** A protocol-standard Model Context Protocol (MCP) server running over JSON-RPC 2.0 stdio, paired with a Unix/Windows CLI (`python -m mendex_core.cli`). Both Codex and Claude Code connect to the exact same endpoints.
3. **Deterministic Engineering Core (Mendex Core):** The authoritative execution layer for physical equations (Dowell, Steinmetz, loss budgets), topology synthesis, component databases, and artifact generation.
4. **Native Specialized Solvers (LTspice, FEMM, KiCad, FreeCAD):** Headless, batch execution of industrial-grade solvers without mock data or simulated approvals.
5. **Engineering Command Center (Mendex Studio GUI):** A lean, responsive 7-item navigation desktop application for workspace monitoring, simulation inspection, waveform viewing, design rule verification, and formal reporting.

---

## 2. Logical Block Diagram

```text
                                 ENGINEER
                                    |
                                    v
                     +-----------------------------+
                     |       VS CODE EDITOR        |
                     |  +-----------------------+  |
                     |  |  OpenAI Codex Agent   |  |
                     |  |  Anthropic Claude     |  |
                     |  +-----------------------+  |
                     +-----------------------------+
                                    |
                JSON-RPC 2.0 stdio / CLI Subprocess
                                    |
                                    v
              +-------------------------------------------+
              |          MENDEX INTEGRATION LAYER         |
              |   +-------------------+  +------------+   |
              |   |  Mendex MCP Server|  | Mendex CLI |   |
              |   +-------------------+  +------------+   |
              +-------------------------------------------+
                                    |
                     In-Process Python Core API
                                    |
                                    v
              +-------------------------------------------+
              |          MENDEX ENGINEERING CORE          |
              |  - StudioService (SQLite Persistence)     |
              |  - CandidateSynthesisEngine (Topologies)  |
              |  - AnalyticalCalculators (Dowell, Losses) |
              |  - ComponentDatabase (MOSFET, Magnetics)  |
              |  - ArtifactGenerators (LTspice, KiCad)    |
              |  - SafeSubprocessRunner (Sandboxing)      |
              |  - ProductLifecycleEngine (12 Stages)     |
              +-------------------------------------------+
                     |              |              |
                     v              v              v
              +-----------+   +-----------+  +------------+
              |  LTspice  |   | FEMM 4.2  |  |  KiCad 10  |
              |  26.1     |   | (Magnetics|  |  (eeschema/|
              |  (SPICE)  |   |   FEA)    |  |   pcbnew)  |
              +-----------+   +-----------+  +------------+
                     \              |              /
                      v             v             v
              +-------------------------------------------+
              |           ENGINEERING WORKSPACE           |
              |  - .mendex/studio.sqlite3 (Metadata)      |
              |  - workspaces/<id>/ (Generated Artifacts) |
              |  - Raw Simulation Waveforms (.raw)        |
              |  - Solver Logs & Manifests (.log, .sha)   |
              +-------------------------------------------+
                                    ^
                                    | Local Filesystem & DB Watcher
                                    v
              +-------------------------------------------+
              |        MENDEX ENGINEERING STUDIO          |
              |  1. Dashboard                             |
              |  2. Engineering Workspaces                |
              |  3. Simulation Center & Waveform Viewer   |
              |  4. Component Library                     |
              |  5. Engineering Tools                     |
              |  6. Reports & Evidence                    |
              |  7. Settings                              |
              +-------------------------------------------+
```

---

## 3. Subsystem Responsibilities

### 3.1 VS Code + Codex & Claude Code
- **Natural Language Parsing:** Converts engineer prompts ("Design a 24V to 5V 4A buck converter with < 50mV ripple") into structured SI requirements.
- **Tool Calling:** Invokes typed MCP tools (`validate_specification`, `generate_design`, `run_simulation`).
- **Design Review:** Reads extracted simulation metrics from Mendex Core and suggests component optimizations.
- **Workflow Orchestration:** Sequences engineering steps automatically without GUI drag-and-drop canvas complexity.
- **Agent Independence:** Uses standard MCP protocol tools. Neither Codex nor Claude requires customized backend code.

### 3.2 Mendex CLI (`python -m mendex_core.cli` or `mendex`)
Provides automated scriptability and fallback execution for CI/local shell:
```bash
# Workspaces
mendex workspace list
mendex workspace create --name "DC-DC Study" --description "Buck analysis"
mendex workspace open --workspace <id>

# Specifications & Design
mendex specification validate --file spec.json
mendex design generate --workspace <id> --title "Buck 20W" --category "dc_dc_converter" --vin 24 --vout 5 --iout 4 --fsw 100000 --ripple 0.05
mendex design status --design <id>

# Deterministic Calculations
mendex calculation run --type dowell --frequency 100000 --layer-count 2 --conductor-height 0.00035
mendex calculation run --type losses --mosfet "Infineon OptiMOS" --current 4.0 --freq 100000

# Simulations
mendex simulation run --workspace <id> --tool ltspice --netlist circuit.net
mendex simulation status --job <job_id>
mendex simulation results --job <job_id>

# Tools & Revisions
mendex tool list
mendex tool open --tool kicad_sch --file circuit.kicad_sch
mendex revision list --product <product_id>
mendex report generate --product <product_id>
```

### 3.3 Mendex MCP Server (`python -m mendex_core.mcp`)
Exposes standardized Model Context Protocol tools over JSON-RPC 2.0 stdio:
- **`list_workspaces`**, **`create_workspace`**, **`get_workspace_status`**
- **`validate_specification`**, **`create_specification`**
- **`generate_design`**, **`get_design`**, **`list_design_candidates`**
- **`run_engineering_calculations`**, **`get_calculation_results`**
- **`run_simulation`**, **`get_simulation_status`**, **`get_simulation_results`**
- **`list_design_artifacts`**, **`open_artifact`**
- **`list_design_revisions`**, **`create_design_revision`**
- **`generate_engineering_report`**, **`get_validation_summary`**

### 3.4 Mendex Engineering Core
- Single authoritative Python library for calculations, database persistence, and artifact generation.
- **Deterministic:** Calculations are reproducible and unit-tested; no probabilistic AI hallucinations in core physics.
- **Offline-First:** All records live in local SQLite `.mendex/studio.sqlite3` and filesystem folders.

### 3.5 Specialized Solvers
- **LTspice 26.1:** Executes transient, AC, and DC operating point batch runs (`-b -ascii`), outputting `.raw` and `.log`.
- **FEMM 4.2:** Executes magnetic finite-element solving via filelink IPC (`create(0)`), producing $B_{\max}$ and core losses.
- **KiCad 10.0:** Runs electrical rules checking (`kicad-cli sch erc`) and design rules checking (`kicad-cli pcb drc`).
- **FreeCAD 1.1:** Runs headless Python geometry generation (`freecadcmd.exe`), producing standard STEP 3D CAD models.

### 3.6 Mendex Engineering Studio (Desktop GUI)
Simplified to a high-contrast, clean 7-item navigation sidebar:
1. **Dashboard:** High-level status, operational tool counts, active workspace cards, recent runs.
2. **Engineering Workspaces:** Centralized workspace browser containing 9 focused sub-views:
   - *Overview*, *Specifications*, *Designs*, *Calculations*, *Simulations*, *Engineering Files*, *Validation*, *Revisions*, *Reports*.
3. **Simulation Center:** Active queue, batch monitoring, solver output logs, and interactive waveform viewer (`WaveformViewerWidget`).
4. **Component Library:** Discrete component catalog, semiconductor ratings, and MagNet/SwitchLossDB fixtures.
5. **Engineering Tools:** Host tool discovery, versions, paths, and launch shortcuts.
6. **Reports & Evidence:** Dossier viewer, SHA-256 evidence register, and formal audit summaries.
7. **Settings:** Executable paths, default workspace locations, MCP server configuration, and UI theme.

---

## 4. End-to-End Operation Flow

```text
Step 1: Engineer instructs Codex in VS Code:
        "Synthesize a 24V to 5V 4A buck converter in workspace 'Buck_Study' and simulate in LTspice"
        
Step 2: Codex calls MCP tool:
        -> create_workspace(name="Buck_Study")
        -> generate_design(workspace_id=..., vin_nom=24, vout=5, iout=4, fsw=100000, ripple=0.05)
        
Step 3: Mendex Core calculates L1, C1, duty cycle, peak switch current, and generates:
        - workspaces/Buck_Study/generated_artifacts/rev_1/buck_circuit.net
        - workspaces/Buck_Study/generated_artifacts/rev_1/buck_schematic.asc
        - workspaces/Buck_Study/generated_artifacts/rev_1/kicad/buck.kicad_sch
        - workspaces/Buck_Study/generated_artifacts/rev_1/kicad/buck.kicad_pcb
        
Step 4: Codex calls MCP tool:
        -> run_simulation(workspace_id=..., tool="ltspice", netlist="buck_circuit.net")
        
Step 5: Mendex Core launches LTspice batch runner:
        LTspice.exe -b -ascii buck_circuit.net
        Captures exit code 0, extracts Vout, ripple, and generates circuit.raw.
        
Step 6: Studio Desktop displays:
        - Engineering Workspaces shows 'Buck_Study' with Rev 1.
        - Simulation Center shows job SUCCEEDED, duration 0.8s.
        - Waveform Viewer renders 5.0V regulated transient waveform.
        
Step 7: Engineer reviews results in Studio, clicks "🔌 Open Schematic in KiCad" to inspect EDA layout,
        or instructs Codex to iterate design parameters.
```
