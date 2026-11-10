# v1.9 Readiness Gate — Test D: Parameter Sweep & Workflow Automation

**Result: FAIL** — at the gate baseline (commit `dc21aa9`) there is no Workflow Studio UI, no workflow execution engine and no parameter-sweep node. The committed workflow tool nodes either crash against the real service or return fabricated results. A five-point sweep run as a QA script against the core service shows that the solver path itself works, but that is not Workflow Studio capability.

Evidence: `.mendex/qa/v19-readiness/pinned_dc21aa9/test_dfh/result.json`, `.mendex/qa/v19-readiness/test_d/workflow_backend_dc21aa9.json` · harness `test_dfh.py`, `test_d_workflow_backend.py`.

## 1. Baseline drift during the gate

| Time (IST) | State |
|---|---|
| 19:55 | Gate started at `dd26af9` (+ uncommitted UI changes). No workflow code in `src/` (`git grep` for QGraphicsScene/QGraphicsView/WorkflowNode/NodeEditor/sweep: no hits). |
| 20:07:06 | Developer commit `dc21aa9` "feat(v1.9): implement Phase 2 workflow models, node contracts, validation, and storage service" landed during testing. |
| ~20:10 | Uncommitted `src/mendex_core/workflows/engine.py`, `tests/core/test_workflow_engine.py`, later `src/mendex_ui/workflow_canvas/` appeared (work in progress). |

The gate was frozen to **committed HEAD `dc21aa9`**: extracted with `git archive` to `.mendex/qa/v19-readiness/snapshot_dc21aa9/` (source hashes in `SNAPSHOT_dc21aa9_SOURCE_SHA256.txt`), and all automated tests were rerun against it. Uncommitted work in progress was **not assessed**.

## 2. Workflow backend at `dc21aa9`

| Capability | Present? | Evidence |
|---|---|---|
| Node registry | Yes — 23 node types (`ltspice_simulation`, `femm_analysis`, `kicad_check`, `parameter_input`, `tolerance_comparison`, `report_export`, …) | `registered_node_types` |
| Execution engine | **No** (`engine.py` absent at HEAD) | `has_engine_module: false` |
| Parameter sweep node / iteration | **No** | `sweep_node_present: false` |
| Visual canvas / drag-and-drop UI | **No** — no workflow page in the sidebar; no QGraphics code in `mendex_ui` | Test I |
| Connection validation | Yes — type mismatch, missing port and cycle are all rejected with clear messages | `validate_type_mismatch`, `validate_missing_port`, `validate_cycle` |
| Workflow storage | Yes — save and reload round-trip equal | `storage_roundtrip_equal: true` |

### Workflow tool nodes executed directly

| Node | Context | Observed | Assessment |
|---|---|---|---|
| `ltspice_simulation` | No service | Returns `status "COMPLETED"`, `metrics {"sample_count": 500, "status": "simulated"}`, a 100-point synthetic waveform `10·(1−2.718^(−i/20))`, and log text **"LTspice simulation executed successfully."** No solver ran. | **Fabricated result** |
| `ltspice_simulation` | Real `StudioService` | Submits a job with `parameters.netlist_text`, which the LTspice connector ignores (it requires `input_paths`), so the job FAILS ("No netlist file found"). The node then crashes: `AttributeError: 'IntegrationService' object has no attribute 'get_job'`. | Defect |
| `femm_analysis` | No service / service | Heuristic values reported as `COMPLETED` / `UNSUPPORTED` (see Test B) | Fabricated / blocked |
| `kicad_check` | Invalid schematic | `passed: True`, 0 violations, no tool executed (see Test C) | **Fabricated pass** |

## 3. Supporting evidence only: QA-scripted sweep through the core service

Five distinct R values with C = 1 µF and Vs = 5 V. Each point is a separate real LTspice job submitted by the QA script through `StudioService.integrations` (no manual editing). Netlists were generated from parameters; acceptance per point was |ΔV| ≤ 1 mV at t = 0.1–5 τ.

| R (Ω) | τ (ms) | Job ID | Status | Points | max abs ΔV (µV) | Verdict | raw SHA-256 (first 16) |
|---|---|---|---|---|---|---|---|
| 500 | 0.50 | `aebdcb2e` | SUCCEEDED | 5023 | 5.01 | PASS | `24b974c2cdfa14c5` |
| 1000 | 1.00 | `6e7512ff` | SUCCEEDED | 5024 | 2.75 | PASS | `606c7869c8a9b59f` |
| 2000 | 2.00 | `bb695e75` | SUCCEEDED | 5025 | 1.62 | PASS | `6a1ddf8b5fe42e2c` |
| 4700 | 4.70 | `b1887d93` | SUCCEEDED | 5026 | 0.82 | PASS | `37ee20be300c146a` |
| 10000 | 10.00 | `d93bdf25` | SUCCEEDED | 5026 | 0.25 | PASS | `1268f6edd6121e1b` |

This shows that repeated, parameterised real-solver execution through the core service is feasible. It does **not** satisfy Test D, because the parameterisation, extraction, comparison and aggregation were all done by the QA harness.

## 4. Requirement verdicts

| # | Requirement | Result |
|---|---|---|
| 1 | Creation of workflow nodes | PARTIAL — programmatic `NodeDefinition` only; no UI |
| 2 | Parameter definition | PARTIAL — `parameter_input` node exists; not executable end to end |
| 3 | Parameter variation | FAIL — no sweep construct |
| 4 | Automated simulation execution | FAIL — no engine; LTspice node crashes with service |
| 5 | Result extraction per run | FAIL — node returns empty `TimeSeriesData()` with service |
| 6 | Comparison with analytical expectation | FAIL (no executable workflow) |
| 7 | Aggregation | FAIL |
| 8 | Interactive visualisation | FAIL |
| 9 | Workflow execution logs | FAIL — `record_run` storage exists, no runs possible |
| 10 | Export of comparison report | FAIL |
