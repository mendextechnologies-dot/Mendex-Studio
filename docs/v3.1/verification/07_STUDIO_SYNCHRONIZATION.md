# 07. Studio Synchronization Audit

**Target:** Automatic UI Updates from External Codex / CLI Mutations  
**Status:** **FAIL (CRITICAL GAP)**

---

## 1. Audit Findings

The target v3.1 architecture specifies:
> *"The Studio must automatically reflect changes made through Codex or CLI without manual refresh."*

### Reality in Current Codebase:
1. **Desktop UI is PySide6 Qt**: The running desktop application is `src/mendex_ui/window.py`.
2. **No Active Polling in PySide6**: The PySide6 UI loads data when panels are constructed or navigated to. There is no `QTimer` polling SQLite or background thread listening for CLI mutations.
3. **Tauri IPC Bridge Not Built**: A sidecar service exists at `src/mendex_core/desktop/service.py` with private stdio JSON-lines protocol, but no desktop application is connected to it.
4. **Latency / Staleness**: If an engineer creates a project or adds a calculation via CLI, the PySide6 UI will NOT display it until the user manually switches tabs, navigates, or restarts the app.

---

## 2. Required Remediation

To achieve genuine automatic synchronization:
1. Implement the React frontend with TanStack Query polling (e.g. 2000 ms refetch interval).
2. Connect Tauri 2 IPC commands to `DesktopService` stdio stream.
3. Ensure backend design cache invalidation works across separate processes.
