# MENDEX ENGINEERING STUDIO v1.7 — END-TO-END ACCEPTANCE TEST RESULTS

**Date:** 10 November 2026  
**Auditor:** Independent Systems Quality Auditor  
**Audit Standard:** Formal Verification & Regression Validation  
**Target Environment:** Clean disposable temp directories on Windows 11 Enterprise  

---

## 1. Scenario Execution Evidence Matrix

The 7 mandatory acceptance scenarios specified in Section 10 of the audit requirements were executed against real service instances and filesystem workspaces:

| Scenario ID | Test Scope | Execution Method | Expected Outcome | Observed Outcome | Status |
|---|---|---|---|---|---|
| **Scenario A** | General Engineering Workspace | `create_workspace()` & `create_activity()` persisted, closed, reopened | Workspace and activity metadata restored from SQLite without data loss | Name, description, owner, parameters preserved; 100% matched | **PASS** |
| **Scenario B** | Engineering Tool Execution | `KiCadAdapter.execute()` with operation `version` | Headless execution, zero exit code, version string in stdout | Exit code 0; version `10.0.7` parsed from stdout | **PASS** |
| **Scenario C** | Simulation Workflow | `IntegrationService.submit()`, `wait()`, `export_report()` | Job queued, completed, hashed manifest, and generated HTML/JSON dossier | Status `SUCCEEDED`, manifest SHA-256 generated, `report.html` intact | **PASS** |
| **Scenario D** | AI Engineering Assistant | `StudioService.ai.advise()` & `AIAssistantPanel.send_prompt()` | Formula guidance in UI; backend safety guard rejects unapproved network leaks | UI renders Dowell/Flyback formulas; backend returns `unavailable` | **BLOCKED** *(Cloud)* / **PASS** *(Local)* |
| **Scenario E** | Product Independence | Complete simulation & activity workflow with zero products | All operations succeed without product ID or product creation | 0 products in DB; workspace and activities execute normally | **PASS** |
| **Scenario F** | Existing Product Compatibility | Product with R001 revision & specification, then linked workspace | Product and revision intact; downstream association recorded cleanly | Code `PRD-01`, revision `R001`, and `product_id` link verified | **PASS** |
| **Scenario G** | Failure Recovery & Tamper Check | Missing input file, missing executable config, corrupted manifests | Errors caught gracefully; no unhandled exceptions or data corruption | `INVALID_INPUT` raised on missing file; invalid configs rejected | **PASS** |

---

## 2. Automated Regression Test Suite Evidence

Full local test suite executed with `pytest`:

```
============================= test session starts =============================
platform win32 -- Python 3.13.7, pytest-9.2.0, pluggy-1.7.0
rootdir: C:\Mendex studio
configfile: pyproject.toml
testpaths: tests
plugins: anyio-4.16.0, platformdirs-4.14.5
collected 113 items

tests\adapters\test_calculations.py ...                                  [  2%]
tests\adapters\test_commercial_stubs.py .                                [  3%]
tests\adapters\test_datasets.py .....                                    [  7%]
tests\adapters\test_femm_adapter.py ..                                   [  9%]
tests\adapters\test_generators.py ...                                    [ 12%]
tests\adapters\test_kicad_adapter.py ...                                 [ 15%]
tests\adapters\test_ltspice_adapter.py ....                              [ 18%]
tests\adapters\test_magnetics.py ....                                    [ 22%]
tests\adapters\test_ngspice_adapter.py ....                              [ 25%]
tests\adapters\test_openmodelica_adapter.py ...                          [ 28%]
tests\adapters\test_safe_runner.py .....                                 [ 32%]
tests\adapters\test_security_and_limits.py ....                          [ 36%]
tests\adapters\test_tool_detection.py ....                               [ 39%]
tests\adapters\test_v15_connector.py ....                                [ 43%]
tests\contracts\test_v15_contracts.py ........                           [ 50%]
tests\core\test_completion.py ......                                     [ 55%]
tests\core\test_day2.py .......                                          [ 61%]
tests\core\test_service.py .........                                     [ 69%]
tests\integration\test_day3.py ....                                      [ 73%]
tests\integration\test_restore.py .                                      [ 74%]
tests\integration\test_v15_integration_hook.py .                         [ 75%]
tests\integration\test_v15_jobs.py ............                          [ 85%]
tests\integration\test_v16_resilience.py ......                          [ 91%]
tests\integration\test_v16_workflow.py .                                 [ 92%]
tests\integration\test_v17_product_independent.py ...                    [ 94%]
tests\ui\test_v15_panels.py .                                            [ 95%]
tests\ui\test_window.py .                                                [ 96%]
tests\ui\test_workspace_panels.py ....                                   [100%]

============================ 113 passed in 18.47s =============================
```

---

## 3. Desktop UI Smoke Test Suite Evidence

### 3.1 `scripts/desktop_smoke.py`
- **Output:** `Desktop smoke passed: seven screens captured under .mendex/qa`
- **Captured Views:** `day3-products.png`, `day3-transformer.png`, `day3-validation.png`, `day3-reports.png`, `day3-tools.png`, `day3-knowledge.png`, `day3-doctor.png`.

### 3.2 `scripts/v15_codex_smoke.py`
- **Output:** `Codex v1.5 synthetic UI smoke passed; screenshots under .mendex/qa/v15-codex`
- **Captured Views:** `tool-center.png`, `jobs.png`, `datasets.png`, `logs.png`, `evidence.png`.

### 3.3 `scripts/v17_enterprise_smoke.py`
- **Output:** `Mendex Studio v1.7 Enterprise UI smoke passed; 5 screens captured under .mendex/qa/v17-enterprise`
- **Captured Views:** `dashboard-dark.png`, `dashboard-light.png`, `tool-center.png`, `jobs-workspaces.png`, `research-datasets.png`.

---

## 4. Final Verification Summary

- **Total Acceptance Scenarios:** 7
- **Passed Scenarios:** 6 (Scenarios A, B, C, E, F, G)
- **Partially Passed / Policy Blocked:** 1 (Scenario D: Local AI formula heuristics pass; Live external cloud connection blocked due to lack of configured API key)
- **Failed Scenarios:** 0
- **Overall Scenario Pass Rate:** 85.7% Full Pass / 14.3% Conditioned on Cloud Policy
