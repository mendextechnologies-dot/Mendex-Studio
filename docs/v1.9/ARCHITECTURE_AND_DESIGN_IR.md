# MENDEX ENGINEERING STUDIO v1.9 — ARCHITECTURE & DESIGN INTERMEDIATE REPRESENTATION (IR)

## 1. System Architecture Overview

Mendex Engineering Studio v1.9 is architected around a unified **Single Core Authority** model. A central service facade (`StudioService`) manages design synthesis, parametric dependencies, visual workflows, native tool generation, and lifecycle records.

```mermaid
flowchart TD
    subgraph UI ["Studio Interface (PySide6 Desktop & CLI)"]
        WIZARD["New Design Wizard"]
        CANVAS["Visual Design Canvas"]
        COPILOT["AI Engineering Copilot"]
        EXPLORER["Stage & Artifact Explorer"]
    end

    subgraph Core ["Core Domain Services (mendex_core)"]
        DESIGN["EngineeringDesignService"]
        SYNTH["CandidateSynthesisEngine"]
        PARAM["ParametricDesignEngine"]
        SYNC["CrossToolSyncService"]
        COMP["ComponentLibraryService"]
        AI["AICopilotGateway"]
        WF["WorkflowExecutionEngine"]
        LIFE["ProductLifecycleEngine"]
    end

    subgraph IR ["Canonical Design Intermediate Representation"]
        COMPONENTS["IRComponent (Designators, Pins, Values, Models)"]
        NETS["IRNet (Interconnecting Pins & Signals)"]
        PORTS["IRPort (Boundary Power & Signals)"]
        PARAMS["IRParameter (Named Formulas & Expressions)"]
        GEOM["IRMagneticGeometry (Core & Bobbin Dimensions)"]
    end

    subgraph Generators ["Native Artifact Exporters"]
        LTSPICE["LTspiceNetlistGenerator (.net/.cir)"]
        KICAD["KiCadSchematicGenerator (.kicad_sch/.kicad_pro)"]
        FEMM["FEMMMagneticGenerator (.lua)"]
        FREECAD["FreeCadGenerator (.step)"]
    end

    UI --> DESIGN
    UI --> COPILOT
    DESIGN --> SYNTH
    DESIGN --> PARAM
    DESIGN --> SYNC
    DESIGN --> IR
    IR --> Generators
```

---

## 2. Design Intermediate Representation (Design IR) Specification

The Design Intermediate Representation (IR) is a syntax-independent mathematical container representing circuits, magnetics, and hardware topology without tying to any specific simulator or CAD syntax.

### Key Constructs
1. **`IRComponent`**:
   - `designator`: Unique identifier (e.g. `Q1`, `L1`, `T1`, `C1`, `R1`).
   - `type`: Classified component (`resistor`, `capacitor`, `inductor`, `transformer`, `mosfet`, `diode`, `voltage_source`).
   - `value`: Numerical SI scalar value.
   - `pins`: Terminal identifiers (e.g. `['d', 'g', 's']` for MOSFET, `['1', '2']` for passive).
   - `parameters`: Key-value properties (`rds_on`, `v_ds_max`, `esr`, `isat`).
   - `footprint`: Standard KiCad footprint reference.
   - `spice_model`: Subcircuit model identifier.
2. **`IRNet`**:
   - `name`: Signal or power net (e.g. `VIN`, `VOUT`, `SW`, `DRAIN`, `GND`).
   - `connections`: List of `(component_id, pin_id)` bindings.
3. **`IRParameter`**:
   - Named variable, formula expression, SI unit, and tolerance.
4. **`IRMagneticGeometry`**:
   - Physical dimensions ($A_e$, $l_e$, $V_e$, air gap, turns ratio, core type, and bobbin geometry).
