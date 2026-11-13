# 10. Engineering Core Regression Analysis

**Target:** Automated Pytest Regression Suite  
**Status:** **99.06% PASS (317 Passed, 1 Skipped, 2 Failed out of 320)**

---

## 1. Full Test Suite Results

```text
collected 320 items
=========================== short test summary info ===========================
FAILED tests/core/test_v19_design_synthesis.py::test_cross_tool_sync_and_external_edits
FAILED tests/integration/test_v19_revised_acceptance.py::test_scenario_j_external_edit_and_stale_invalidation
============ 2 failed, 317 passed, 1 skipped in 203.89s (0:03:23) =============
```

---

## 2. Deep Root-Cause Analysis of the 2 Failures

### Failure 1: `test_cross_tool_sync_and_external_edits`
- **Location**: `tests/core/test_v19_design_synthesis.py:170`
- **Error**: `IndexError: list index out of range` on `[a for a in active_rev.artifacts if a.kind == ArtifactKind.KICAD_SCH][0]`
- **Root Cause**: In-memory design caching. `s.design.generate_native_artifacts()` updates the design object in the service's internal cache `_designs`, but does not mutate the caller's existing local `design` variable. When the test accesses `design.get_active_revision().artifacts`, it reads the stale local object with 0 artifacts. If the test re-fetches `s.design.get_design(design.id)`, all 4 artifacts are present.

### Failure 2: `test_scenario_j_external_edit_and_stale_invalidation`
- **Location**: `tests/integration/test_v19_revised_acceptance.py:238`
- **Error**: `assert len(mods) >= 1` failed (`len(mods) == 0`).
- **Root Cause**: `CrossToolSyncService.detect_modifications()` compares file paths relative to `service.root`. In this test, path resolution mismatch between WindowsPath and relative artifact strings caused the external modification to be missed by the change detector.

### Recommendation:
These 2 failures are localized to cross-tool external file watcher unit tests and do not affect core mathematical sizing or lifecycle persistence. They must be resolved before v3.1 production sign-off.
