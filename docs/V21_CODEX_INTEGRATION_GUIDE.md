# Mendex Engineering Studio v2.1 — AI Agent Integration Guide
## VS Code + OpenAI Codex & Anthropic Claude Code

**Target Version:** v2.1.0  
**Transport:** Standard JSON-RPC 2.0 stdio (Model Context Protocol) & CLI (`mendex_core.cli`)  
**Core Authority:** Single Authoritative Mendex Engineering Core (`src/mendex_core/`)

---

## 1. Executive Summary

In Mendex Engineering Studio v2.1, **VS Code + AI Agents (OpenAI Codex and Anthropic Claude Code)** serve as the primary interactive engineering authoring environments. Engineers interact with the agents using natural language, specifications, and instructions.

The AI agents interact with the underlying deterministic engineering capabilities exclusively through:
1. **The Mendex Model Context Protocol (MCP) Server** (`python -m mendex_core.mcp`)
2. **The Mendex Engineering CLI** (`python -m mendex_core.cli`)

Both interfaces connect to the exact same **`MendexEngineeringController`**, which invokes deterministic analytical calculations, synthesis engines, native EDA/CAD generators (KiCad, LTspice, FEMM, FreeCAD), and local SQLite persistence.

**Zero agent-specific logic exists in Mendex Core.** Both Codex and Claude Code have identical capabilities and execute the exact same operations.

```
       +--------------------+      +-----------------------+
       |   VS Code + Codex  |      |  Claude Code / Desktop |
       +---------+----------+      +-----------+-----------+
                 |                             |
                 +--------------+--------------+
                                |
                   JSON-RPC 2.0 stdio / CLI
                                |
                                v
             +-------------------------------------+
             |    Mendex MCP Server & Unified CLI  |
             +------------------+------------------+
                                |
                                v
             +-------------------------------------+
             |    MendexEngineeringController      |
             +------------------+------------------+
                                |
      +-------------------------+-------------------------+
      |                         |                         |
      v                         v                         v
Pure Calculations         Design Synthesis         Simulation Dispatch
(Dowell, Steinmetz,     (Buck, Flyback, Push-     (LTspice batch .raw,
Semiconductor Losses)     Pull, KiCad, FreeCAD)     FEMM Lua, KiCad ERC)
```

---

## 2. Setting Up Anthropic Claude Code

### Registration via Command Line
Run the following command in terminal to register Mendex MCP with Claude Code:

```bash
claude mcp add mendex-engineering -- python -m mendex_core.mcp
```

Or when launching Claude Code within the repository workspace:
```bash
claude --mcp-config mcp_config.json
```

### Claude Desktop Configuration
Add the server entry to `%APPDATA%\Claude\claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "mendex-engineering": {
      "command": "C:\\Mendex studio\\.venv\\Scripts\\python.exe",
      "args": ["-m", "mendex_core.mcp", "--root", "C:\\Mendex studio"]
    }
  }
}
```

---

## 3. Setting Up OpenAI Codex & VS Code

### VS Code MCP Configuration
Create or update `.vscode/mcp.json` in your repository root:

```json
{
  "servers": {
    "mendex-engineering": {
      "command": "${workspaceFolder}/.venv/Scripts/python.exe",
      "args": ["-m", "mendex_core.mcp", "--root", "${workspaceFolder}"],
      "env": {
        "PYTHONPATH": "src"
      }
    }
  }
}
```

### CLI Automation via VS Code Tasks
VS Code tasks in `.vscode/tasks.json` provide quick shortcuts:
```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Mendex: List Workspaces",
      "type": "shell",
      "command": "${workspaceFolder}/.venv/Scripts/python.exe",
      "args": ["-m", "mendex_core.cli", "workspace", "list"],
      "problemMatcher": []
    },
    {
      "label": "Mendex: Run LTspice Simulation",
      "type": "shell",
      "command": "${workspaceFolder}/.venv/Scripts/python.exe",
      "args": ["-m", "mendex_core.cli", "simulation", "run", "--workspace", "default"],
      "problemMatcher": []
    }
  ]
}
```

---

## 4. End-to-End Workflow Example (Codex or Claude Code)

An AI agent executes the full engineering workflow in sequence:

### Step 1: Create an Engineering Workspace
Prompt to Agent:
> *"Create a new engineering workspace for a 20W Synchronous Buck Converter."*

Tool Invocation:
```json
{
  "name": "create_workspace",
  "arguments": {
    "name": "Buck 20W DC-DC",
    "description": "24V to 5V 4A industrial synchronous buck converter"
  }
}
```

### Step 2: Validate the Electrical Specification
Prompt to Agent:
> *"Validate the operating parameters: Vin 18V-32V (nom 24V), Vout 5V, Iout 4A, fsw 100 kHz."*

Tool Invocation:
```json
{
  "name": "validate_specification",
  "arguments": {
    "spec_data": {
      "vin_min_v": 18.0,
      "vin_nom_v": 24.0,
      "vin_max_v": 32.0,
      "vout_v": 5.0,
      "iout_a": 4.0,
      "switching_frequency_hz": 100000.0
    }
  }
}
```

### Step 3: Synthesize Design & Generate Native CAD Artifacts
Prompt to Agent:
> *"Synthesize the candidate topologies and generate native KiCad schematics and LTspice netlists."*

Tool Invocation:
```json
{
  "name": "generate_design",
  "arguments": {
    "workspace_id": "<workspace_uuid>",
    "title": "Synchronous Buck 20W",
    "category": "dc_dc_converter",
    "vin_nom": 24.0,
    "vin_min": 18.0,
    "vin_max": 32.0,
    "vout": 5.0,
    "iout": 4.0,
    "fsw_hz": 100000.0,
    "ripple_v": 0.05
  }
}
```
*Artifacts automatically generated on filesystem:*
- `workspaces/<id>/generated_artifacts/rev_1/kicad/synchronous_buck_20w.kicad_sch` (KiCad S-expression)
- `workspaces/<id>/generated_artifacts/rev_1/kicad/synchronous_buck_20w.kicad_pcb` (KiCad Layout)
- `workspaces/<id>/generated_artifacts/rev_1/synchronous_buck_converter_schematic.asc` (LTspice Schematic)
- `workspaces/<id>/generated_artifacts/rev_1/buck_circuit.net` (SPICE Netlist)

### Step 4: Run Deterministic Loss & Magnetic Calculations
Prompt to Agent:
> *"Calculate the Dowell AC resistance factor for 2 layers of 0.5mm wire at 100 kHz."*

Tool Invocation:
```json
{
  "name": "run_engineering_calculations",
  "arguments": {
    "calc_type": "dowell",
    "params": {
      "frequency_hz": 100000.0,
      "layers": 2,
      "conductor_diameter_mm": 0.5,
      "r_dc_ohm": 0.05,
      "temperature_c": 100.0
    }
  }
}
```

### Step 5: Execute Simulation
Prompt to Agent:
> *"Execute a 2 ms transient simulation in LTspice and extract output voltage steady-state metrics."*

Tool Invocation:
```json
{
  "name": "run_simulation",
  "arguments": {
    "workspace_id": "<workspace_uuid>",
    "tool": "ltspice",
    "duration_s": 0.002
  }
}
```

### Step 6: Generate Formal Evidence Dossier
Prompt to Agent:
> *"Generate an engineering dossier with SHA-256 evidence manifest."*

Tool Invocation:
```json
{
  "name": "generate_engineering_report",
  "arguments": {}
}
```

---

## 5. Live Synchronization with Mendex Studio Desktop

When an agent (Codex or Claude Code) executes these actions:
1. The SQLite database `.mendex/studio.sqlite3` and the filesystem `workspaces/<id>/` are immediately updated.
2. Mendex Engineering Studio's UI displays the new workspaces, synthesized designs, simulation runs, and waveforms without manual data entry.
3. The human engineer in Mendex Studio can click **Open in KiCad** or inspect waveforms in the **Simulation Center** with full traceability.
