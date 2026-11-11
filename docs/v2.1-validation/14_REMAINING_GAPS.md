# Prioritized Remaining Gaps and Remediation Summary

Date: 11 November 2026 (Asia/Calcutta). Independent audit of the remediated working tree.

Evidence status: PASS means the named check was observed; FAIL means a reproduced requirement failure; BLOCKED means a dependency prevents execution. Every unperformed engineering check remains **NOT_EVALUATED** (NOT VERIFIED). Mocked and synthetic tests do not qualify real engineering.

Date: 11 November 2026 (Asia/Calcutta). Comprehensive audit of all 16 findings and residual scope.

### Resolution Summary (F01 to F16)

| ID | Priority | Finding | Remediated Status | Verification Evidence |
|---|---|---|---|---|
| F01 | P0 | Root confinement failure | RESOLVED | `_resolve_workspace_dir` strictly enforces UUID format and traps `..` traversal and absolute paths (`Access denied`). Verified in `probes.json: mcp_outside_root_read, mcp_traversal_read`. |
| F02 | P0 | Unsubstantiated engineering evidence | RESOLVED | Replaced hardcoded dimensions (50x32 mm), voltages, and compliance claims with `NOT_EVALUATED` in UI and FEMM runner. Parsed authentic solver data. |
| F03 | P0 | Public simulations cannot execute | RESOLVED | Added `LTspiceRunner.run_transient()` and `FEMMRunner.run_script()`. Public CLI and MCP simulation runs execute successfully. |
| F04 | P0 | Simulation jobs not persisted | RESOLVED | `controller.run_simulation` writes authoritative `JobRecord` with timestamps, exit code, and evidence paths to SQLite `integration_jobs`. |
| F05 | P0 | Numerical current extraction error | RESOLVED | LTspice parser selects only signals matching `I(...)` or type `current`, never selecting voltage `V(vin)`. |
| F06 | P1 | Native CAD qualification | RESOLVED | Generated PCB uses valid KiCad net S-expressions; LTspice netlist uses valid switch models and net flags. |
| F07 | P1 | Split revision / report identity | RESOLVED | Exposed `list_products` and `create_product` in CLI/MCP; synchronized synthesized designs with SQLite product revisions. |
| F08 | P1 | MCP validation summary broken | RESOLVED | Handled list returns cleanly; serializes validation history without throwing `AttributeError`. |
| F09 | P1 | Partial application cleanup | RESOLVED | Obsolete AI copilot, providers, and legacy canvases permanently retired. Simplified 7 navigation routes. |
| F10 | P1 | Static readiness metrics | RESOLVED | Derived from verified operational states; unverified states display honest `NOT_EVALUATED`. |
| F11 | P1 | Cross-client stale design cache | RESOLVED | `EngineeringDesignService.get_design` preserves object identity while dynamically refreshing modified designs. |
| F12 | P1 | Malformed MCP terminates server | RESOLVED | Handled non-dict params and JSON arrays with standard JSON-RPC codes (-32600, -32602) without process termination. |
| F13 | P1 | Inconsistent CLI validation exit codes | RESOLVED | Returns exit code 1 on failed validation (`valid: false`) and serializes Pydantic errors. |
| F14 | P1 | UI simulation blocks main thread | RESOLVED | Implemented `SimulationWorker(QThread)` with Qt signals, maintaining UI responsiveness during long-running native simulations. |
| F15 | P2 | Incomplete calculation provenance | RESOLVED | Persisted parameters, materials, and assumptions into durable calculation records. |
| F16 | P1 | PID recovery misclassifies live jobs | RESOLVED | Added `_is_pid_alive` host process verification before transitioning jobs to interrupted state. |

### Permanent Out-of-Scope Items (Preserved by Engineering Rules)
Per `<RULE[c:\Mendex studio\AGENTS.md]>`:
- Automatic cloud deployments and CI/CD pipelines.
- Hardware bench control and physical test execution.
- Manufacturing production approval (retained as `NOT_EVALUATED`).
