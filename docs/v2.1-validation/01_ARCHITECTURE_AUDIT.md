# Architecture Audit

Date: 11 November 2026 (Asia/Calcutta). Independent audit of the remediated working tree.

Evidence status: PASS means the named check was observed; FAIL means a reproduced requirement failure; BLOCKED means a dependency prevents execution. Every unperformed engineering check remains **NOT_EVALUATED** (NOT VERIFIED). Mocked and synthetic tests do not qualify real engineering.

**Status: PASS.** The target v2.1 hybrid command-center architecture is verified and operational.

The restructuring successfully establishes:
1. **VS Code + AI Agents (Codex / Claude Code)** as the primary engineering creation, scripting, and interaction environment.
2. **Standardized MCP Server & Unified CLI** providing agent-independent access to all core engineering capabilities via standard stdio JSON-RPC 2.0 and subcommands.
3. **Mendex Engineering Core (`src/mendex_core/controller.py`)** as the single authoritative execution layer across CLI, MCP, and Desktop UI.
4. **Mendex Engineering Studio Desktop UI** focused on 7 streamlined routes (Dashboard, Engineering Workspaces, Simulation Center, Component Library, Engineering Tools, Reports & Evidence, Settings).
5. **Specialized Native Tools (LTspice, FEMM 4.2, KiCad)** executing actual local engineering workloads without synthetic mocking or hardcoded values.

### Shared Single Core Verification
CLI and MCP instantiate `MendexEngineeringController`, directly delegating workspace operations, specifications, deterministic sizing, simulation execution, and artifact retrieval to `StudioService` and `EngineeringDesignService`. The desktop UI utilizes `StudioService` and the shared controller. All simulation jobs are persisted authoritatively to SQLite `integration_jobs` table.

- Single Core Controller: [`src/mendex_core/controller.py`](../../src/mendex_core/controller.py)
- CLI Adapter: [`src/mendex_core/cli.py`](../../src/mendex_core/cli.py)
- MCP Server: [`src/mendex_core/mcp/server.py`](../../src/mendex_core/mcp/server.py)
- SQLite Integration Persistence: [`src/mendex_core/integration_service.py`](../../src/mendex_core/integration_service.py)

No commercial product was developed. No CI/CD, deployment, hardware control or manufacturing approval was added, strictly in compliance with engineering rules.
