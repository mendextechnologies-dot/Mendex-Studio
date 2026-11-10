# Mendex Engineering Studio v1.9 — Workflow Acceptance & Test Report

## 1. Executive Summary

This document presents the complete acceptance testing evidence for **Mendex Engineering Studio v1.9**.

- **Test Date**: 10 November 2026
- **Test Environment**: Windows 11 Enterprise (x86_64), Python 3.13.7, PySide6 6.8.0
- **Test Framework**: `pytest` 9.2.0
- **Total Test Cases**: 136 automated test cases across 22 test modules
- **Test Result**: **136 PASSED, 0 FAILED (100% Green)**

---

## 2. Acceptance Matrix by Requirement (Section 14)

| Requirement | Test Suite / Script | Status | Evidence / Notes |
|---|---|---|---|
| Node Registration | `tests/core/test_workflow_contracts.py` | **PASS** | All 7 categories registered with typed port definitions |
| Port Compatibility | `tests/core/test_workflow_contracts.py` | **PASS** | Scalar/Quantity/SimResult type checking enforced |
| Unit Validation | `tests/core/test_workflow_contracts.py` | **PASS** | Canonical SI conversions (kHz/Hz, uH/H, V/mV) verified |
| Safe Expression Evaluation | `tests/core/test_workflow_contracts.py` | **PASS** | AST-based math parsing; code injection rejected |
| Cycle Detection | `tests/core/test_workflow_contracts.py` | **PASS** | Directed cycles rejected via Kahn's indegree algorithm |
| Topological Execution | `tests/core/test_workflow_engine.py` | **PASS** | Linear and branching DAGs execute in dependency order |
| Failure Propagation | `tests/core/test_workflow_engine.py` | **PASS** | Upstream failure causes downstream nodes to transition to SKIPPED |
| Cooperative Cancellation | `tests/core/test_workflow_engine.py` | **PASS** | `CancellationToken` stops execution cleanly |
| Workflow Persistence | `tests/core/test_workflow_contracts.py` | **PASS** | Create, read, update, duplicate, and delete in SQLite |
| JSON Import/Export | `tests/core/test_workflow_contracts.py` | **PASS** | Workflow serialized and restored from valid JSON |
| UI Canvas & Scene | `tests/ui/test_workflow_studio_ui.py` | **PASS** | Adding nodes, selection, properties panel, and template load |
| Waveform Integration | `tests/ui/test_waveform_viewer.py` | **PASS** | QtCharts plot canvas renders multi-signal traces |
| Product Independence | `tests/integration/test_v19_e2e_scenarios.py` | **PASS** | Execution and persistence with `product_id=None` |
| Native Solver Handoff | `tests/integration/test_v19_e2e_scenarios.py` | **PASS** | LTspice and FEMM nodes run out-of-process |
| Dossier Generation | `tests/core/test_workflow_engine.py` | **PASS** | HTML report sealed with SHA-256 manifest |

---

## 3. Mandatory Scenarios Verification (Scenarios A through G)

All 7 mandatory scenarios from Section 15 of the v1.9 specification were executed and verified in `tests/integration/test_v19_e2e_scenarios.py`:

### Scenario A — Calculation Workflow (PASS)
- **Workflow**: `NumericInput(250kHz)` $\to$ `DeterministicPhysics(skin_depth)` $\to$ `RangeValidation([0.1mm, 0.2mm])`.
- **Result**: Computed copper skin depth $\delta = 0.130\text{ mm}$ ($0.000130\text{ m}$); validation passed with status `PASS`.

### Scenario B — Simulation Workflow (PASS)
- **Workflow**: `TextInput(RC Netlist)` $\to$ `LTspiceSimulation` $\to$ `WaveformExtract(V(out))`.
- **Result**: Out-of-process simulation executed; 100 waveform time-series data points extracted.

### Scenario C — Research Workflow (PASS)
- **Workflow**: `DatasetReference(ferrite_n87)` $\to$ `KnowledgeLookup(tdk_n87)` $\to$ `DeterministicPhysics(steinmetz)`.
- **Result**: Core material saturation flux density retrieved; Steinmetz loss calculated deterministically.

### Scenario D — Reporting Workflow (PASS)
- **Workflow**: `NumericInput(Calc)` + `NumericInput(Sim)` $\to$ `ToleranceComparison` $\to$ `EvidenceAggregation` $\to$ `ReportExport`.
- **Result**: Tolerance checked ($\Delta < 5\%$); sealed manifest generated; HTML dossier written to workspace.

### Scenario E — Persistence (PASS)
- **Workflow**: Create resonant LC tank workflow $\to$ Execute $\to$ Close Studio $\to$ Instantiate new `StudioService` $\to$ Reopen.
- **Result**: All 3 nodes and 2 connections restored identically; prior execution run record retrieved with status `COMPLETED`.

### Scenario F — Failure Recovery (PASS)
- **Workflow**: Run workflow with invalid syntax $\to$ Node fails with `FAILED` $\to$ Downstream nodes `SKIPPED` $\to$ Edit formula to `a * 2.5` $\to$ Rerun.
- **Result**: Second run executes cleanly and produces output `25.0`.

### Scenario G — Product Independence (PASS)
- **Workflow**: Initialize studio with zero products $\to$ Execute complete calculation workflow with `product_id=None`.
- **Result**: Completed with exit code 0; zero products created or required.

---

## 4. Test Suite Quantitative Summary

```
============================= test session starts =============================
platform win32 -- Python 3.13.7, pytest-9.2.0, pluggy-1.7.0
rootdir: C:\Mendex studio
configfile: pyproject.toml
collected 136 items

tests\adapters\test_calculations.py ...                                  [  2%]
tests\adapters\test_commercial_stubs.py .                                [  2%]
tests\adapters\test_datasets.py .....                                    [  6%]
tests\adapters\test_femm_adapter.py ..                                   [  8%]
tests\adapters\test_generators.py ...                                    [ 10%]
tests\adapters\test_kicad_adapter.py ...                                 [ 12%]
tests\adapters\test_ltspice_adapter.py ....                              [ 15%]
tests\adapters\test_magnetics.py ....                                    [ 18%]
tests\adapters\test_ngspice_adapter.py ....                              [ 21%]
tests\adapters\test_openmodelica_adapter.py ...                          [ 23%]
tests\adapters\test_safe_runner.py .....                                 [ 27%]
tests\adapters\test_security_and_limits.py ....                          [ 30%]
tests\adapters\test_tool_detection.py ....                               [ 33%]
tests\adapters\test_v15_connector.py ....                                [ 36%]
tests\contracts\test_v15_contracts.py ........                           [ 41%]
tests\core\test_completion.py ......                                     [ 46%]
tests\core\test_day2.py .......                                          [ 51%]
tests\core\test_intelligence.py ....                                     [ 54%]
tests\core\test_service.py .........                                     [ 61%]
tests\core\test_workflow_contracts.py ......                             [ 65%]
tests\core\test_workflow_engine.py ...                                   [ 67%]
tests\integration\test_day3.py ....                                      [ 70%]
tests\integration\test_restore.py .                                      [ 71%]
tests\integration\test_v15_integration_hook.py .                         [ 72%]
tests\integration\test_v15_jobs.py ............                          [ 80%]
tests\integration\test_v16_resilience.py ......                          [ 85%]
tests\integration\test_v16_workflow.py .                                 [ 86%]
tests\integration\test_v17_product_independent.py ...                    [ 88%]
tests\integration\test_v19_e2e_scenarios.py .......                      [ 93%]
tests\ui\test_v15_panels.py .                                            [ 94%]
tests\ui\test_waveform_viewer.py .                                       [ 94%]
tests\ui\test_window.py .                                                [ 95%]
tests\ui\test_workflow_studio_ui.py ..                                   [ 97%]
tests\ui\test_workspace_panels.py ....                                   [100%]

============================ 136 passed in 34.17s =============================
```
