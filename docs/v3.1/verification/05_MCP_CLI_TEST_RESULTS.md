# 05. MCP & CLI Test Results

**Target:** MCP Server (`src/mendex_core/mcp/server.py`) & CLI (`src/mendex_core/cli.py`)  
**Status:** **PASS**

---

## 1. MCP Server Audit

- **Protocol**: JSON-RPC 2.0 stdio, Anthropic MCP Specification (2024-11-05).
- **Tools Count**: **58 registered tools** (0 duplicated, all schema-validated).
- **Tool Categories**:
  - Lifecycle: `list_lifecycle_definitions`, `get_lifecycle_definition`, `enroll_lifecycle`, `get_project_lifecycle`, `apply_lifecycle_stage`, `get_lifecycle_history`.
  - Records: `record_requirements`, `list_requirements`, `get_requirement_coverage`, `list_supported_calculations`, `record_calculation_run`, `register_engineering_artifact`, `record_validation_evidence`.
  - Projects & Revisions: `list_projects`, `create_project`, `get_project`, `save_project_specification`, `list_revisions`, `create_revision`.
  - Simulation & Artifacts: `run_simulation`, `list_simulations`, `get_simulation_status`, `get_simulation_results`, `list_design_artifacts`.

---

## 2. CLI Execution Verification

Actual command invocations executed during audit:

```powershell
# 1. Lifecycle Definitions Discovery
.venv\Scripts\python.exe -m mendex_core.cli lifecycle definitions
# Exit Code: 0 | Output: Valid JSON with 9 stages

# 2. Engineering Operations Help
.venv\Scripts\python.exe -m mendex_core.cli engineering --help
# Exit Code: 0 | Output: 22 subcommands displayed

# 3. Doctor Diagnostics
.venv\Scripts\python.exe -m mendex_core.cli doctor
# Exit Code: 0 | Output: SQLite integrity OK, Python 3.13 OK, tool discovery OK
```

### Safety & Guardrails:
- Direct unauthorized SQLite mutations by CLI/MCP are prevented by pydantic model validation and foreign key constraints.
- Long-running simulation requests return structured job tokens without blocking the transport.
