# MENDEX ENGINEERING STUDIO v2.0
## IMPLEMENTATION & QUALIFICATION PLAN

**Plan Date**: 11 November 2026  
**Target Version**: v2.0 — Real Engineering Workflow Qualification & Design Automation

---

## 1. Execution Phases & Milestones

```mermaid
flowchart TD
    P1["Phase 1: Baseline Audit & Gap Analysis (Done)"] --> P2["Phase 2: Real LTspice Simulation & Waveform Extraction"]
    P2 --> P3["Phase 3: Real FEMM Magnetics Solve & Result Parsing"]
    P3 --> P4["Phase 4: KiCad Populated PCB & DRC Verification"]
    P4 --> P5["Phase 5: AI-Assisted Closed-Loop Design Iteration"]
    P5 --> P6["Phase 6 & 7: Coherent Design Workspace UI & Stage Actions"]
    P6 --> P8["Phase 8: Parametric Change & Cross-Tool Sync"]
    P8 --> P9["Phase 9: End-to-End Generic Design Qualification (Refs A & B)"]
    P9 --> P10["Phase 10: Final Engineering Readiness Dashboard & Reports"]
```

---

## 2. Technical Deliverables Specification

1. **LTspice Simulation Engine (`src/mendex_core/design/ltspice_runner.py`)**:
   - Executes `LTspice.exe -b <file.net>` in process-isolated workspace.
   - Ingests generated `.raw` file via `numpy` parser.
   - Calculates real metrics: $V_{out,\text{mean}}$, $\Delta V_{out}$ (peak-to-peak ripple), $I_{pk}$, efficiency $\eta$.
   - Generates both `.net` netlist and graphical `.asc` schematic file.
2. **FEMM Magnetic FEA Engine (`src/mendex_core/design/femm_runner.py`)**:
   - Executes `C:\femm42\bin\femm.exe -windowhide -lua=<script.lua>`.
   - Parses output file (`.ans` / log) extracting maximum magnetic flux density $B_{\max}$ and inductance $L$.
3. **Populated KiCad PCB Generator (`src/mendex_core/design/generators/kicad_pcb_generator.py`)**:
   - Generates `.kicad_pcb` with standard board outline (`Edge.Cuts`), mounting holes, placed footprints, and net connections.
   - Ready for manual trace completion or DRC verification via `kicad-cli pcb drc`.
4. **AI Iteration Orchestrator (`src/mendex_core/design/iteration.py`)**:
   - Compares simulation metrics against requirements.
   - If requirement failed (e.g. ripple > 1%), formulates parameter adjustment recommendation.
   - Dispatches approved change $\to$ creates new revision $\to$ re-runs solver $\to$ generates before/after comparison table.
5. **End-to-End Acceptance Suites**:
   - `Reference A`: Circuit design, simulation, parameter change, re-simulation, and report.
   - `Reference B`: CAD, magnetics, KiCad schematic ERC, populated PCB DRC, and BOM export.
