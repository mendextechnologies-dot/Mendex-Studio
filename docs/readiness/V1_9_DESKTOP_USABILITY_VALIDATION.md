# v1.9 Readiness Gate — Test I: Professional Desktop Experience

**Result: FAIL** — the window launches on-screen and navigation, theme switching and preference persistence work. However, the v1.9 Workflow Studio canvas does not exist at the gate baseline, the Simulation Lab / waveform viewer / AI assistant panels are not mounted in the window, and the dashboard shows **hard-coded tool-readiness claims that contradict the core service**.

Evidence: `.mendex/qa/v19-readiness/pinned_dc21aa9/test_i/` (14 page captures + theme + relaunch) · harness `harness/test_i_desktop.py`.

Method: the real `StudioWindow` was launched against a disposable data root on the native Windows QPA (`qpa_platform: windows`, not offscreen). Pages were driven programmatically and captured with `QScreen.grabWindow` (real screen pixels). No human drag-and-drop was performed, and items that need it are marked NOT VERIFIED.

## Results

| Item | Result | Evidence / observation |
|---|---|---|
| Launch / window | PASS | Title "Mendex Engineering Studio v1.9 · Enterprise Edition" |
| Dashboard navigation | PASS | 14 sidebar pages; switch times 3–46 ms |
| Workspace creation | PASS (core) | Via service in Tests D/F; the UI "+ New Workspace" dialog was not clicked through (NOT VERIFIED interactively) |
| Workflow Studio canvas | **FAIL — absent** | No workflow page in the sidebar; no QGraphics code at `dc21aa9` |
| Drag-and-drop nodes | **FAIL — absent** | — |
| Node connection validation (UI) | FAIL — absent in UI | The backend validator works (Test D) |
| Properties editing | NOT VERIFIED | No workflow properties panel |
| Simulation progress display | FAIL | Simulations page: "No solver will run. Requests persist as NOT_SUPPORTED" (`page_06_Simulations.png`) |
| Waveform viewer | **FAIL** | `SimulationLabPanel` (which hosts the viewer) is defined in `v17_panels.py` but not instantiated by `StudioWindow`; when wired, it shows hard-coded benchmark curves rather than solver output (Test A) |
| Results Center ("Jobs & Results") | PARTIAL | Page renders; no numerical result display exists |
| Engineering Tool Center | PARTIAL | "Tools & Integrations" lists 18 entries with `installed ≠ verified` messaging (`page_11`) |
| Engineering Intelligence interface | FAIL | `AIAssistantPanel` is not mounted |
| Report export | PARTIAL | Reports page renders draft-only text; content is inadequate (Test E) |
| Theme switching | PASS | Dark → light (`theme_light.png`) |
| Layout persistence | PASS | `ui_preferences.json` written on close; light theme restored on relaunch (`relaunch.png`) |
| UI responsiveness | PASS for navigation | ≤ 46 ms page switches. Note: `SimulationLabPanel.run_simulation` calls `integrations.wait()` on the UI thread, which would block the UI for the full solver run if the panel were mounted |

## Misleading status displays (critical)

| UI element | Shows | Reality (core service / host) |
|---|---|---|
| Header badge (`window.py:105`) | "● 6 Solvers Operational · 12 Catalog" (string literal) | 1 executable connector (LTspice) |
| KPI card (`v17_panels.py:63`) | "CORE TOOLS READY 6 / 6 — LTspice, KiCad, FEMM, FreeCAD, Qucs-S, OMC" (literal) | Service: KiCad, FEMM, FreeCAD, Qucs-S, OpenModelica = `NOT_INSTALLED` |
| Tool health table (`v17_panels.py:170-181`) | 8 tools "READY" with versions and paths (hard-coded list) | Not detected; e.g. ngspice "READY 46 KLU" is not a Studio detection result |

These displays assert readiness without evidence, which conflicts with the project rule "Never fabricate calculations or evidence".

## Interaction limits of this gate

Interactive behaviour was driven by code (QTest / widget APIs), not by a human with a mouse. Because the canvas does not exist, drag-and-drop, node property editing and live workflow progress could not be exercised in any form.
