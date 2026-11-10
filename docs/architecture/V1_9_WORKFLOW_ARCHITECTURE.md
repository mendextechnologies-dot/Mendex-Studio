# Mendex Engineering Studio v1.9 — Visual Workflow Architecture

## 1. Executive Overview

Mendex Engineering Studio v1.9 introduces a native, node-based **Visual Engineering Workflow Studio**. This system enables electrical, magnetic, and systems engineers to construct, configure, execute, monitor, and persist multi-stage engineering calculation and simulation pipelines without writing code.

The workflow system operates strictly **independent of product definitions**, allowing general-purpose engineering pipelines (`Workflow -> Node Graph -> Execution -> Results & Evidence -> Optional Product Link`).

---

## 2. Architectural Principles

1. **Strict DAG Execution**: Workflows are directed acyclic graphs. Directed cycles are detected and rejected prior to execution via Kahn's algorithm.
2. **Explicit Port Contracts**: Nodes communicate exclusively through typed, unit-aware ports. Direct memory sharing or uncontrolled global mutation is forbidden.
3. **Deterministic & Unit-Aware**: Unit conversions and algebraic calculations are performed deterministically. All mathematical expressions use safe AST traversal without Python `eval()`.
4. **Process Tree & Adapter Safety**: Native solver execution is orchestrated out-of-process via verified adapters with timeout protection and process-tree cleanup.
5. **Non-Blocking Asynchronous UI**: Canvas rendering and user interaction remain responsive at 60 FPS while background execution workers process long-running solver jobs.

---

## 3. High-Level System Architecture

```mermaid
graph TD
    subgraph UI_Layer [Presentation Layer - PySide6 / Qt6]
        Window[StudioWindow]
        StudioPanel[WorkflowStudioPanel]
        Canvas[WorkflowGraphicsView & Scene]
        Inspector[NodePropertiesPanel & Log Monitor]
        Waveforms[WaveformViewerWidget QtCharts]
    end

    subgraph Workflow_Core [Workflow Core Engine - src/mendex_core/workflows/]
        Storage[WorkflowStorageService: SQLite Additive Schema]
        Registry[NodeRegistry: 7 Categories]
        Validation[Topology & Type Validator]
        Engine[WorkflowExecutionEngine: DAG Scheduler]
    end

    subgraph Native_Adapters [Multi-Solver Execution Subsystem]
        LTspice[LTspice 26.1 Batch Adapter]
        FEMM[FEMM 4.2 Lua FEA Adapter]
        KiCad[KiCad 10.0 CLI Adapter]
        FreeCAD[FreeCAD 1.1 STEP Adapter]
        Ngspice[ngspice 46 Batch Adapter]
        OpenModelica[OpenModelica 1.26 OMC Adapter]
    end

    subgraph Intelligence [Mendex Engineering Intelligence Foundation]
        Knowledge[Knowledge Service: Formulas & Materials]
        Calculations[Deterministic Calculation Service]
        Reasoning[Reasoning Orchestrator: LocalRuleEngine]
    end

    StudioPanel --> Canvas
    StudioPanel --> Inspector
    StudioPanel --> Waveforms
    StudioPanel --> Engine
    Engine --> Validation
    Engine --> Registry
    Engine --> Storage
    Engine --> Native_Adapters
    Engine --> Intelligence
```

---

## 4. Workflow Lifecycle & Execution Sequence

```mermaid
sequenceDiagram
    autonumber
    actor Engineer as Electrical Engineer
    participant UI as WorkflowStudioPanel
    participant Scene as WorkflowScene (Qt Graphics View)
    participant Validator as Topology Validator
    participant Engine as WorkflowExecutionEngine
    participant Solver as Tool Adapter (LTspice / FEMM)
    participant Store as WorkflowStorageService (SQLite)

    Engineer->>Scene: Drag & drop nodes (Inputs -> Calculation -> Tool -> Validation -> Report)
    Engineer->>Scene: Connect ports with bezier wires
    Scene->>Validator: Validate port type & unit compatibility
    Validator-->>Scene: Connection Accepted
    
    Engineer->>UI: Click "Run Workflow"
    UI->>Engine: execute_workflow(workflow, cancel_token)
    Engine->>Validator: detect_cycles_and_toposort(nodes, connections)
    Validator-->>Engine: topological_order: [N1, N2, N3, N4, N5]
    
    loop For each Node in Topological Order
        Engine->>Engine: Resolve inputs from connected source ports
        alt Node is Calculation
            Engine->>Engine: Execute deterministic AST expression or physical formula
        else Node is Native Solver
            Engine->>Solver: Submit out-of-process simulation job
            Solver-->>Engine: Return simulation artifacts & raw waveforms
        else Node is Validation
            Engine->>Engine: Check tolerance / limits -> PASS/FAIL record
        end
        Engine-->>UI: progress_callback(current, total, node_id, status)
        UI->>Scene: Update node border glow & progress bar in real-time
    end

    Engine->>Store: record_run(WorkflowExecutionRecord)
    Engine-->>UI: Workflow Finished (COMPLETED, duration, manifest_sha256)
    UI->>Engineer: Display Waveforms in QtCharts & Render HTML Dossier
```

---

## 5. Persistence & Schema Model

Workflows are persisted in the central SQLite database via additive tables without altering `PRAGMA user_version`:

- **`workflows` table**:
  - `id`: UUID primary key.
  - `workspace_id`: Foreign key to `integration_workspaces` (optional).
  - `product_id`: Foreign key to `products` (optional, product-independent).
  - `name`, `description`, `version`: Metadata.
  - `payload`: Full JSON-serialized `WorkflowDefinition` (nodes, connections, canvas viewport).
  - `created_at`, `updated_at`: ISO-8601 timestamps.
- **`workflow_runs` table**:
  - `id`: Execution run UUID.
  - `workflow_id`: Parent workflow reference.
  - `status`: `COMPLETED`, `FAILED`, or `CANCELLED`.
  - `duration_s`: Execution duration in seconds.
  - `manifest_sha256`: Cryptographic digest of run summary.
  - `payload`: Serialized `WorkflowExecutionRecord` containing per-node execution records.
