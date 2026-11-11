# 12 Desktop UI and UX Audit (independent)

Method: StudioWindow (window.py:53) was instantiated offscreen through .venv (system Python has no PySide6) against %TEMP%\mendex-audit\core. Screenshots are in %TEMP%\mendex-audit\ui\nav_0..6.png. Script: ui.py. No buttons were clicked.

| # | Actual nav | Expected | Page class | Observations |
|---|---|---|---|---|
|0|Dashboard|Dashboard|QWidget|Shows a tool/resource catalog ("All Resources (14)", "Research Datasets & Benchmarks (4)", "Frameworks & Dev (3)"), not engineering project status. Its value is questionable.|
|1|Engineering Workspaces|Engineering Projects|QWidget|Name does not match. The page is overloaded with 25+ buttons: workspace, product, revision, spec, lifecycle, 3D Bobbin, Benchmarks, Gates, Evidence. It duplicates the Reports page (Export Dossier) and the Simulations page.|
|2|Simulation Center|same|SimulationCenterPanel|Execute Simulation, Open .RAW, plot controls. Not exercised.|
|3|Component Library|same|ComponentLibraryPanel|Only registers a local file or metadata and shows history. There is no searchable parts database. Partial.|
|4|Engineering Tools|same|ToolCenter|Browse, Detect and Verify. Tool detection works.|
|5|Reports & Evidence|same|ReportsEvidencePanel|Record manual validation, open evidence, generate draft dossier, open report.|
|6|Settings|same|SettingsPanel|The only visible button is the theme toggle. The "AI Copilot & Cloud Provider Configuration" group is at panels.py:103.|

## Findings
- **P1: the UI goes stale after CLI/MCP changes.** There is no QFileSystemWatcher anywhere in src (grep). The only timers are job polling (integration_panels.py:147, v17_panels.py:881), plus a manual "Refresh Status" button on the Dashboard.
- **AI leftovers:** ai_interactive.py, ai_config_dialog.py and design_studio_panel.py still exist. v17_panels.py:1035 and 1153-1175 still wire up an "AI Copilot" query worker. None of these is a top-level nav item; whether they can be reached from inside a page is NOT VERIFIED.
- **Contradictory message:** the status bar says "Approval and simulation execution unavailable" (window.py:367), but Simulation Center offers "Execute Simulation".
- **Error visibility:** NOT VERIFIED (actions were not clicked).
