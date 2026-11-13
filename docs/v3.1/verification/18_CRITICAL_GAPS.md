# 18. Critical Gaps & Required Remediation

**Target:** Comprehensive List of Blockers, Bugs, and Architectural Divergences  
**Status:** **3 CRITICAL GAPS IDENTIFIED**

---

## 1. Gap 1: Desktop Shell Migration (Tauri 2 + React) Not Implemented
- **Severity**: High (Architectural Divergence)
- **Description**: The project continues to run on PySide6 Qt. The requested modern Tauri 2 + React + TypeScript frontend has 0% implementation in the repository.
- **Impact**: While the PySide6 UI is rich and fully functional, it does not match the requested lightweight read-only command center architecture.
- **Remediation**: Initialize `desktop/` with Tauri 2, Vite, React, TypeScript, and TanStack Query, connecting to `DesktopService` via stdio.

## 2. Gap 2: Automatic Background UI Synchronization
- **Severity**: High (Core Workflow Requirement)
- **Description**: The UI does not automatically update when projects, calculations, or revisions are created via Codex / CLI.
- **Impact**: Requires manual navigation or restarting the desktop app to observe external writes.
- **Remediation**: Implement active background polling (e.g. 2000 ms interval) in the desktop shell.

## 3. Gap 3: Design Cache Stale Object Regression
- **Severity**: Medium (Unit Test Regression)
- **Description**: 2 tests in `tests/core/test_v19_design_synthesis.py` and `tests/integration/test_v19_revised_acceptance.py` fail because `generate_native_artifacts` updates the internal service cache but leaves caller local references stale.
- **Impact**: External file modification detection fails when calling on cached objects.
- **Remediation**: Update `CrossToolSyncService` and `design.service.py` to refresh local design objects on artifact generation.
