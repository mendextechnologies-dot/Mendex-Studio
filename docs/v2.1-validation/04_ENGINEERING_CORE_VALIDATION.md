# Engineering Core Validation

Date: 11 November 2026 (Asia/Calcutta). Independent audit of the remediated working tree.

Evidence status: PASS means the named check was observed; FAIL means a reproduced requirement failure; BLOCKED means a dependency prevents execution. Every unperformed engineering check remains **NOT_EVALUATED** (NOT VERIFIED). Mocked and synthetic tests do not qualify real engineering.

**Status: PASS.** Authoritative execution layer validated across analytical sizing, design synthesis, solver dispatch, and SQLite persistence.

| Capability | Verdict | Evidence / Verification |
|---|---|---|
| Workspace Management | PASS | UUID validation, strict root confinement (`root/workspaces`), traversal blocking. |
| Specification Schema & Save | PASS | Positive/negative SI voltage and current validation, input voltage ordering constraint ($V_{in,min} \le V_{in,nom} \le V_{in,max}$), immutable baseline enforcement. |
| Deterministic Sizing Calculations | PASS | Core Dowell skin/proximity depth, semiconductor conduction/switching losses, Steinmetz core losses, flyback transformer sizing. |
| Design Synthesis Engine | PASS | Synthesizes full `EngineeringDesign` models with candidates, BOM items, and native artifact generation (SPICE netlist, KiCad PCB, FEMM Lua). |
| Native Solver Execution | PASS | Headless batch LTspice transient solve (`LTspiceRunner.run_transient`) and FEMM script execution (`FEMMRunner.run_script`). |
| Authoritative Job Persistence | PASS | Persists `JobRecord` into SQLite `integration_jobs` with start/end timestamps, exit codes, input paths, evidence paths. |
| Product & Revision Management | PASS | Synchronizes synthesized designs with SQLite product revisions; archived revisions strictly reject mutation. |
| Approval Safety Gate | PASS (Correctly Blocked) | `set_revision_status(..., Lifecycle.APPROVED)` strictly raises `StudioError: Approval is not implemented` per engineering rules. |
