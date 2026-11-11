# Mendex MCP Tool Reference v2.1

Complete reference for all 20 Model Context Protocol (MCP) tools provided by `mendex-engineering-mcp` (protocol version `2024-11-05`).

---

## Tool Catalog

| # | Tool Name | Subsystem | Description |
|---|---|---|---|
| 1 | `list_workspaces` | Workspace | Lists all active engineering and product workspaces. |
| 2 | `create_workspace` | Workspace | Creates a new engineering workspace directory and database record. |
| 3 | `get_workspace_status` | Workspace | Returns workspace metadata, designs, CAD files, and simulation logs. |
| 4 | `validate_specification` | Specification | Validates electrical operating parameters against SI schema. |
| 5 | `save_specification` | Specification | Persists electrical specification on a product revision. |
| 6 | `generate_design` | Synthesis | Synthesizes candidate topologies & generates native CAD artifacts. |
| 7 | `get_design` | Synthesis | Retrieves design details, calculated components, and topology. |
| 8 | `list_design_candidates` | Synthesis | Lists synthesized topologies with feasibility ranking. |
| 9 | `run_engineering_calculations` | Calculation | Executes deterministic analytical calculations (Dowell, Steinmetz, Losses, Flyback). |
| 10 | `run_simulation` | Simulation | Executes batch headless LTspice transient or FEMM Lua solver. |
| 11 | `list_simulations` | Simulation | Lists simulation jobs and execution status. |
| 12 | `list_design_artifacts` | Artifacts | Discovers all native CAD, netlist, solid, and waveform files. |
| 13 | `open_artifact` | Artifacts | Opens a design file in KiCad, LTspice, or FreeCAD. |
| 14 | `list_tools` | Tools | Lists detected external engineering tools and versions. |
| 15 | `check_tool` | Tools | Performs live diagnostic health check on a specific host tool. |
| 16 | `open_tool_file` | Tools | Launches external tool directly with a file path. |
| 17 | `list_revisions` | Revisions | Lists immutable revision snapshots and specification hashes. |
| 18 | `create_revision` | Revisions | Freezes previous baseline and creates a new product revision. |
| 19 | `get_validation_summary` | Validation | Returns engineering check status and gate evaluation. |
| 20 | `generate_engineering_report` | Reporting | Generates immutable HTML + JSON engineering dossier. |

---

## Detailed Tool Specifications

### `generate_design`
- **Arguments**:
  - `workspace_id` (string, required): Destination workspace.
  - `title` (string, required): Human-readable design title.
  - `category` (string, default "dc_dc_converter"): Converter topology family.
  - `vin_nom` (number, required): Nominal input voltage (V).
  - `vin_min` (number, optional): Minimum input voltage (V).
  - `vin_max` (number, optional): Maximum input voltage (V).
  - `vout` (number, required): Regulated output voltage (V).
  - `iout` (number, required): Rated load current (A).
  - `fsw_hz` (number, default 100000.0): Switching frequency (Hz).
  - `ripple_v` (number, default 0.05): Maximum output voltage ripple (V).
  - `isolation_v` (number, optional): Galvanic isolation test voltage (V).
  - `generate_artifacts` (boolean, default true): Synthesize KiCad/LTspice/FreeCAD files.
  - `product_id` (string, optional): Associated product record.
- **Returns**:
  ```json
  {
    "status": "SYNTHESIZED",
    "design_id": "993f...",
    "title": "Synchronous Buck 20W",
    "active_revision": "Rev 1",
    "candidate_count": 3,
    "candidates": [...],
    "generated_artifacts": [
      {"kind": "kicad_sch", "path": "..."},
      {"kind": "kicad_pcb", "path": "..."},
      {"kind": "netlist", "path": "..."},
      {"kind": "step_solid", "path": "..."}
    ]
  }
  ```

### `run_engineering_calculations`
- **Arguments**:
  - `calc_type` (string, required): One of `"dowell"`, `"losses"`, `"steinmetz"`, `"flyback"`.
  - `params` (object, required): Parameter map for the calculation.
- **Returns**: Strict SI numerical calculation result with formulas and provenance.
