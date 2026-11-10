# Mendex Engineering Studio v1.9 — Final Readiness Decision

**Verdict: NOT READY**

Gate baseline: commit `dc21aa9` (frozen) · Date: 2026-11-10 · Details: [V1_9_ENGINEERING_READINESS_GATE.md](V1_9_ENGINEERING_READINESS_GATE.md)

## Summary

| Test | Area | Result | One-line reason |
|---|---|---|---|
| A | Electrical simulation (LTspice) | **FAIL** | Real solve executed and archived by the Studio (QA-measured accuracy: 2.75 µV max error), but the Studio extracts no waveforms or values, and its viewer plots hard-coded benchmark curves |
| B | Magnetic analysis (FEMM) | **FAIL** | Studio reports FEMM NOT_INSTALLED and rejects jobs; the tool alone gives ≤ 0.5 % B error, but the pre-declared mesh-convergence criterion failed (0.87 %) |
| C | Schematic / ERC (KiCad) | **FAIL** | Studio cannot run KiCad; its adapter and workflow node report **0 violations / passed** for a schematic with 2 real ERC errors |
| D | Parameter sweep / Workflow Studio | **FAIL** | No canvas, engine or sweep node at baseline; LTspice workflow node crashes with the service and fabricates results without it |
| E | Engineering report | **FAIL** | Report has no objective, settings, numerical results, graphs or references, and labels a real run "synthetic" |
| F | Persistence & reproducibility | **PASS** (core-service scope) | Workspace, activity, jobs and evidence integrity survive a process restart; the rerun is numerically identical |
| G | Engineering Intelligence | **FAIL** | Deterministic maths correct and reproducible (3/3 benchmarks independently confirmed); not unit-aware, reasoning does not calculate, unsubstantiated MagNet claim; rule engine only, **no trained model** |
| H | Failure & safety handling | **FAIL** | Timeout and cancel are sound; an interrupted job stays RUNNING forever with an orphaned solver, and several paths fabricate success |
| I | Desktop experience | **FAIL** | Navigation, theme and persistence work; no workflow canvas, Simulation Lab/viewer/AI panels not mounted, dashboard shows hard-coded "6/6 READY" |

Supplementary (tool-level only, not Studio capability): OpenModelica PASS, FreeCAD PASS, ngspice PASS, Qucs-S GUI NOT VERIFIED.

## Why NOT READY rather than CONDITIONALLY READY

CONDITIONALLY READY requires the core calculations and simulations to pass. Here:
- Only one simulator (LTspice) can run through the Studio at all, and the Studio cannot read a single number from its output.
- Magnetic (FEMM) and schematic-validation (KiCad) capability are absent from the Studio service.
- **Data-integrity violations exist**: code paths report successful engineering outcomes that did not happen (KiCad pass on a failing schematic, synthetic LTspice waveform labelled "executed successfully", heuristic FEMM values labelled COMPLETED, hard-coded READY statuses). These directly contravene the project rule "Never fabricate calculations or evidence".

## Critical findings (must fix before re-gating)

1. **Fabricated results**: `workflows/nodes/tools.py` — `KiCadCheckNode` returns `passed=True` with no execution; `LTspiceSimulationNode` returns a synthetic waveform with status COMPLETED when there is no service; `FEMMAnalysisNode` returns heuristic/default values. Each should fail or return NOT_EVALUATED instead.
2. **False clean ERC**: `integrations/parsers/kicad_parser.py` ignores `sheets[].violations`, so `KiCadAdapter` reports 0 violations for an invalid schematic.
3. **Hard-coded readiness claims** in the UI: `window.py:105` badge, `v17_panels.py:63` KPI card, `v17_panels.py:170-181` tool table.
4. **No result extraction**: no Studio code reads `.raw` sample data, and `SimulationLabPanel` displays `load_benchmark_data()` instead of solver output.
5. **Interrupted-job recovery**: a job stays RUNNING indefinitely after a crash, cannot be cancelled from a new session, and leaves an orphan solver process.

## Major findings

6. Installed FEMM, KiCad, FreeCAD, OpenModelica and Qucs-S are reported NOT_INSTALLED; the working adapter stack (`integrations/adapters`) is not wired to `StudioService`.
7. `LTspiceSimulationNode` calls the non-existent `integrations.get_job` and passes `netlist_text`, which the connector ignores.
8. Studio report: no engineering content; the "Synthetic outputs…" limitation is applied to real solver runs; `evidence_aggregation` defaults missing checks to passed.
9. Calculation service is not unit-aware and marks every result `verified=True`; the reasoning layer does not invoke calculations, misroutes queries, and uses hard-coded confidence values.
10. Simulation Lab, waveform viewer and AI assistant panels are not mounted in `StudioWindow`; `run_simulation` would block the UI thread.
11. Invalid-netlist failures surface no diagnostic text in the Studio job.
12. v1.8 documentation claims ("unit-aware dimensional evaluation", "6 active solvers verified", waveform viewer "embedded in Simulation Lab", Steinmetz/CCM benchmarks) are not supported by this gate's evidence.

## What is genuinely working

- Real LTspice batch execution through the core service with SHA-256 evidence manifests, job persistence, integrity checking, timeout and cancellation with process-tree termination.
- Workspace / activity / job persistence across restarts, with numerically reproducible reruns.
- Deterministic closed-form calculations that match independent recomputation exactly.
- v1.9 workflow contracts: connection-type, missing-port and cycle validation, and workflow storage round-trip.
- Installed tools (LTspice, FEMM, KiCad, OpenModelica, FreeCAD, ngspice) are each individually capable of producing results that agree with analytic references. The capability gap is in Studio integration, not in the host toolchain.

## Scope notes

- The gate was frozen to committed `dc21aa9`. Uncommitted v1.9 work that appeared during testing (`workflows/engine.py`, `mendex_ui/workflow_canvas/`) was not assessed and may change Tests D and I once committed. A re-gate on the next committed baseline is required.
- No product (SV-1000, MC-100 or other) was developed; only generic reference models were used.
- Material/standard constants in the knowledge base were not checked against source datasheets/standards and remain NOT_EVALUATED.
