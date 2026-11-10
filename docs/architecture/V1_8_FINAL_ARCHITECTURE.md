# Mendex Engineering Studio v1.8 — Final Architecture Specification

## 1. Executive Summary

Mendex Engineering Studio v1.8 represents the definitive transition of the Mendex desktop platform from a product-first engineering tool into a **modern, enterprise-grade, product-independent engineering workspace and intelligence foundation**.

The studio enables electrical, magnetic, thermal, and mechanical engineers to configure workspaces, perform calculations, run native multi-physics simulations, analyze waveforms, and generate formal engineering reports—completely independently of any product concept, while preserving optional downstream association with product records.

Furthermore, v1.8 introduces the proprietary **Mendex Engineering Intelligence Foundation**: a five-pillar subsystem delivering versioned physical knowledge, deterministic unit-aware calculations, model-independent orchestration, and regression-validated benchmark datasets.

---

## 2. Core Architectural Principles

1. **Product-Independent Engineering Workflow**:
   Engineering activities exist as first-class citizens. An engineer creates a workspace, adds activities (simulations, calculations, design files), invokes engineering tools, views interactive waveforms, and generates reports. Product linking is an optional post-analysis operation.
2. **Single Authority Core Service**:
   All UI panels and CLI entry points interact exclusively through StudioService and IntegrationService. No panel or CLI command talks directly to the database or solver executables.
3. **Deterministic Truth & Provenance**:
   Calculations and simulations are cryptographically hashed and tagged with clear origin metadata (calculated, simulated, unverified). Non-evaluated evidence remains strictly NOT_EVALUATED. No synthetic or hallucinated results are ever emitted.
4. **Resilient Local Multi-Solver Execution**:
   External native tools (LTspice, KiCad, FEMM, FreeCAD, Qucs-S/ngspice, OpenModelica) run out-of-process with strict process-tree isolation, cancellation tokens, timeout guards, and output manifest hashing.
5. **Zero-Network Intelligence Fallback**:
   The built-in engineering assistant functions deterministically offline using the LocalRuleEngineBackend and curated physical formulas. Pluggable API backends can be registered without coupling core logic to any single vendor.

---

## 3. High-Level System Architecture

`mermaid
graph TD
    subgraph UI_Layer [Presentation Layer - PySide6 / Qt6]
        Window[StudioWindow Shell]
        Header[Global Header: Switcher, Ctrl+K Palette, Theme, Health]
        Nav[Collapsible Sidebar Navigation]
        Panels[14 Enterprise Panels: Dashboard, Workspace Manager, Simulation Lab, AI Assistant, Results, Waveform Viewer]
    end

    subgraph Service_Layer [Core Service Layer - Python 3.13]
        Service[StudioService: Central Facade]
        IntService[IntegrationService: Workspaces, Activities, Solver Jobs]
        IntelService[EngineeringReasoningOrchestrator]
    end

    subgraph Intelligence_Subsystem [Mendex Engineering Intelligence]
        Knowledge[EngineeringKnowledgeService: Formulas, Materials, Standards]
        Calculations[DeterministicCalculationService: Unit-Aware Equations]
        Models[ModelRegistry: LocalRuleEngineBackend & Pluggable Adapters]
        Benchmarks[EngineeringBenchmarkRegistry: Ground-Truth Regression]
    end

    subgraph Solver_Layer [Multi-Tool Adapter Subsystem]
        Registry[AdapterRegistry: 18 Tool Catalog]
        LTspice[LTspice Adapter v26.1]
        KiCad[KiCad CLI Adapter v10.0]
        FEMM[FEMM 4.2 Lua Adapter]
        FreeCAD[FreeCAD 1.1 STEP Adapter]
        Ngspice[Qucs-S / ngspice 46 Adapter]
        OpenModelica[OpenModelica 1.26 OMC Adapter]
        Guards[5 Commercial Guards: PLECS, MATLAB, Maxwell, Icepak, SolidWorks]
    end

    subgraph Data_Layer [Data & Storage Layer]
        SQLite[(SQLite Database: Additive v5 Schema)]
        FS[Local Workspace Filesystem: Manifests, Raw Logs, Netlists]
        Prefs[UI Preferences: Theme, Window Geometry, Recent Searches]
    end

    UI_Layer --> Service_Layer
    Service_Layer --> Intelligence_Subsystem
    Service_Layer --> Solver_Layer
    Service_Layer --> Data_Layer
    IntelService --> Knowledge
    IntelService --> Calculations
    IntelService --> Models
    IntelService --> Benchmarks
`

---

## 4. Product-Independent Workflow Architecture

In v1.3–v1.6, activities were constrained under Product -> Specification -> Revision. In v1.8, the system decouples engineering activities entirely:

`mermaid
sequenceDiagram
    autonumber
    actor Engineer as Electrical Engineer
    participant UI as Studio UI (Workspace Manager)
    participant Core as IntegrationService
    participant Tool as Solver Adapter (e.g. LTspice / FEMM)
    participant Intel as Intelligence Engine
    participant Store as SQLite & Filesystem

    Engineer->>UI: Create Workspace ('High-Freq Planar Magnetics')
    UI->>Core: create_workspace(name, path)
    Core->>Store: INSERT INTO integration_workspaces (product_id=NULL)
    
    Engineer->>UI: Consult AI Assistant ('Skin depth at 250kHz?')
    UI->>Intel: advise_engineering(query)
    Intel-->>UI: Deterministic calculation (delta = 0.131 mm) + formula reference

    Engineer->>UI: Create Activity ('FEA Winding Loss Analysis')
    UI->>Core: create_activity(workspace_id, tool_id='femm', type='simulation')
    Core->>Store: INSERT INTO activities
    
    Engineer->>UI: Execute Simulation
    UI->>Core: submit_job(activity_id, tool_id, input_files)
    Core->>Tool: execute(job_dir, timeout=120)
    Tool-->>Core: Process output, manifest, status=SUCCESS
    Core->>Store: INSERT INTO integration_jobs, write manifest.json
    
    Engineer->>UI: Inspect Waveforms & Losses (QtCharts Canvas)
    UI->>Core: get_job_results(job_id)
    Core-->>UI: Parsed raw data points
    
    Engineer->>UI: Generate Report (HTML/JSON)
    UI->>Core: generate_activity_report(activity_id)
    Core-->>UI: Cryptographically sealed engineering report

    opt Optional Product Link
        Engineer->>UI: Associate Activity with Product ('EV Charger Gen 2')
        UI->>Core: associate_activity_with_product(activity_id, product_id)
        Core->>Store: UPDATE activities SET product_id = :pid
    end
`

---

## 5. Engineering Intelligence Architecture

The Engineering Intelligence subsystem (src/mendex_core/intelligence/) is structured into five isolated, testable modules:

### 5.1 Knowledge Service (knowledge.py)
- Maintains curated, versioned engineering formulas (Dowell factor, skin depth, flyback CCM inductances, Steinmetz core loss, LC resonance).
- Standard material profiles (e.g., TDK N87 ferrite, Cree/Wolfspeed C3M0065090D SiC MOSFET) with thermal coefficients and flux limits.
- Regulatory clearance and creepage tables (IEC 62368-1, IPC-2221B).

### 5.2 Deterministic Calculation Service (calculations.py)
- Evaluates formulas using exact physical constants ( = 4\pi 	imes 10^{-7}$, $ho_{Cu} = 1.68 	imes 10^{-8} \ \Omega\cdot m$).
- Performs temperature corrections (copper resistivity at operating temperature $).
- Emits reproducible records with origin='calculated', input hashes, and step-by-step intermediate terms.

### 5.3 Model-Independent Interface (models.py)
- Defines the ModelBackend protocol (generate_response, classify_intent, extract_parameters).
- Implements LocalRuleEngineBackend ensuring full offline operation with zero API tokens or cloud dependencies.
- Pluggable ModelRegistry allows optional registration of external providers (Claude, OpenAI, Gemini, local Ollama).

### 5.4 Reasoning Orchestration (
easoning.py)
- Interprets engineer questions, recognizes calculation intents, maps queries to recommended native solvers (LTspice for transient, FEMM for magnetics, KiCad for layout), and formats responses with explicit limitations.

### 5.5 Benchmarks & Ground Truth (enchmarks.py)
- Evaluates analytical models against benchmark references (e.g., Dowell $ curve, Steinmetz loss curves) verifying MAPE $\le 5.0\%$.

---

## 6. Enterprise UI Architecture

The desktop application (src/mendex_ui/) is implemented in PySide6 (Qt 6.8+):

- **Modern Design System (	heme.py)**: Catppuccin Mocha (Dark) and Latte (Light) palettes with high-contrast borders and accessible typography.
- **Interactive Waveform Viewer (waveform_viewer.py)**: Hardware-accelerated QtCharts canvas supporting box zoom, pan, hover tooltips, and multi-trace overlays (voltage, current, power).
- **Global Command Palette (window.py)**: Ctrl+K modal offering instantaneous auto-completion across workspaces, activities, tools, and actions.
- **Layout & Preference Persistence**: User theme and window geometry are saved across sessions in .mendex/ui_preferences.json.
- **14 Unified Panels**: Full backward compatibility with canonical page indices while surfacing the modern EnterpriseDashboardPanel as the root entry point.

---

## 7. Security, Integrity & Constraints

1. **No Fabricated Data**: Calculation and simulation outputs must originate from real executable runs or analytical equations.
2. **Process Sandboxing**: External solvers run in isolated per-job directories. No execution modifies global workspace paths.
3. **No CI/CD or Hardware Control**: As dictated by project governance rules, the software produces local artifacts only and does not initiate remote deployments or hardware programming.
4. **Database Safety**: Additive schema upgrades preserve historical tables; PRAGMA user_version is maintained at 4 for backwards compatibility.
