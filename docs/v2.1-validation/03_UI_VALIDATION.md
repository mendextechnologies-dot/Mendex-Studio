# Desktop UI Validation

Date: 11 November 2026 (Asia/Calcutta). Independent audit of the remediated working tree.

Evidence status: PASS means the named check was observed; FAIL means a reproduced requirement failure; BLOCKED means a dependency prevents execution. Every unperformed engineering check remains **NOT_EVALUATED** (NOT VERIFIED). Mocked and synthetic tests do not qualify real engineering.

**Status: PASS.** Windows Qt desktop UI (`windows`, native window ID `11668978`) validated across both Dark Mode (`#11111b`) and Light Mode (`#ffffff` white background).

### Navigation & Information Architecture
The desktop UI contains exactly 7 primary navigation routes:
1. **Dashboard** (`index 0`): System KPI metrics, solver readiness, workspace status.
2. **Engineering Workspaces** (`index 1`): Product catalog, 12-stage lifecycle panel, specification editor.
3. **Simulation Center** (`index 2`): Asynchronous non-blocking solver runs, waveform viewer.
4. **Component Library** (`index 3`): Core and winding component catalogs, search, property inspector.
5. **Engineering Tools** (`index 4`): Tool detection, path configuration, launch native tools.
6. **Reports & Evidence** (`index 5`): Engineering dossier generation, evidence manifests, PDF/HTML reports.
7. **Settings** (`index 6`): MCP connection status, theme toggling (Dark/Light), workspace root settings.

### Truth in UI & Honest Evidence States
- **Honest Evidence Display (F02 Remediated)**: Removed all fabricated dimensions (50.0 x 32.0 mm), 5.0 mm creepage, and IPC-2221B compliance claims. Unverified parameters explicitly show `NOT_EVALUATED` until authentic CAD/DRC files exist.
- **ERC / DRC Badges**: Display `NOT_EVALUATED` instead of prematurely claiming `PASSED` when reports are absent.
- **Waveform Simulation Values**: Removed hardcoded 1000 V / 0.85 mVpp claims; parameters display `NOT_EVALUATED` until authentic `.raw` output is parsed.
- **Truncation Resolution**: 9 Direct Result Access pill buttons (`[Spec]`, `[KiCad PCB]`, `[Simulations]`, `[BOM]`, `[Sizing]`, `[3D Bobbin]`, `[Benchmarks]`, `[Gates]`, `[Evidence]`) streamlined and verified readable without truncation.
- **Sidebar Brand Cleanup**: Duplicate sidebar brand block permanently removed; brand shield exists solely once in global top bar.
- **Non-blocking Simulations (F14 Remediated)**: Executed via background `SimulationWorker(QThread)` with Qt signals, preserving full desktop responsiveness during long-running native simulations.
