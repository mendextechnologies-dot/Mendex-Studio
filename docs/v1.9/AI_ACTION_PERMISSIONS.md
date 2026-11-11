# MENDEX ENGINEERING STUDIO v1.9 — AI ACTION PERMISSIONS & SANDBOX

## 1. Registered Typed Actions

The AI Copilot operates solely through registered typed actions:

1. `analyze_requirements`: Checks range, units, and consistency; identifies missing inputs.
2. `generate_candidates`: Invokes `CandidateSynthesisEngine` to produce candidate topologies.
3. `calculate`: Executes deterministic equations through `ParametricDesignEngine`.
4. `generate_artifact`: Emits native LTspice, KiCad, or FEMM files.
5. `open_native_tool`: Requests OS execution of external verified software.
6. `run_solver`: Dispatches batch simulation job.
7. `parse_results`: Extracts numerical waveforms and metrics.
8. `compare`: Computes error differences (e.g. RMSE vs simulation).
9. `propose_revision`: Formulates proposed parameter modifications.
10. `generate_report`: Compiles traceable engineering dossier.

---

## 2. Permission Guard Contract

- Every proposed action is created in `PENDING_APPROVAL` status.
- The execution engine rejects execution unless `action.approval_status == ActionApprovalStatus.APPROVED`.
- No silent disk modifications, tool invocations, or data uploads are permitted.
