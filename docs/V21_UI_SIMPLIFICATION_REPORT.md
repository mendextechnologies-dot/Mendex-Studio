# Mendex Engineering Studio v2.1 — UI Simplification Report

**Date:** 11 November 2026  
**Status:** Completed & Qualified  
**Scope:** Streamlining desktop navigation to 7 core destinations and removing obsolete in-app tools.

---

## 1. Executive Summary of Changes

Prior to v2.1, the desktop user interface had accumulated 16 disparate navigation tabs, including built-in AI conversational dialogs, drag-and-drop workflow canvases, and custom circuit design screens.

In accordance with the v2.1 mandate:
- **VS Code + AI Agents (Codex & Claude Code)** now serve as the primary authoring environment.
- **Mendex Studio** is restructured into a clean 7-destination engineering command center.
- Redundant and duplicate UI elements have been permanently eliminated from the primary navigation.

---

## 2. Before vs. After Navigation Structure

| v2.0 Navigation (16 Tabs) | v2.1 Navigation (7 Clean Destinations) | Rationale & Status |
|---|---|---|
| Dashboard | **1. Dashboard** | Preserved enterprise overview with solver readiness. |
| Products | **2. Engineering Workspaces** | Consolidated workspace hub (catalog, 12-stage lifecycle, specs, revisions). |
| Transformer | Integrated into **3. Component Library** / Calculations | Dedicated math accessible via Core/CLI/Component Library. |
| DC–DC Converter | Integrated into **2. Engineering Workspaces** | Merged into unified parametric synthesis. |
| Switching Devices | Integrated into **3. Component Library** | Preserved in unified semiconductor browser. |
| PCB Workspace | Integrated into **2. Engineering Workspaces** | Accessible via Direct Result Access in 12-stage overview. |
| Simulations | **3. Simulation Center** | Combined simulation execution and interactive waveform viewer (`WaveformViewerWidget`). |
| Validation | Integrated into **6. Reports & Evidence** | Unified with formal reporting. |
| Reports | **6. Reports & Evidence** | Formal verification dossiers & append-only audit trail. |
| Tool Manager | Integrated into **5. Engineering Tools** | Consolidated host discovery. |
| Knowledge Center | Integrated into **4. Component Library** | Integrated research datasets & references. |
| Tools & Integrations | **5. Engineering Tools** | Host tools & solvers detection. |
| Jobs & Results | Integrated into **3. Simulation Center** | Consolidated simulation job queue. |
| Dataset Catalog | Integrated into **4. Component Library** | MagNet & SwitchLossDB catalog. |
| Workflow Studio | **Removed from Navigation** | Visual drag-and-drop canvas removed; VS Code handles automation. |
| Design Studio | **Removed from Navigation** | Duplicate creation interface removed; unified synthesis in Core/CLI. |
| *(None)* | **7. Settings** | New dedicated configuration & MCP connection center. |

---

## 3. Specific Visual Cleanups

1. **Sidebar Header Branding Cleaned**:
   - The duplicate "MENDEX TECHNOLOGIES" logo card previously located at the top of the sidebar has been removed, resolving user feedback.
   - The navigation items now cleanly align to the top of the sidebar.
2. **Simplified Specification-to-Design Generation**:
   - Filenames generated during parametric synthesis are fully sanitized via `sanitize_filename`, eliminating Windows `[Errno 22]` invalid argument errors.
3. **Consolidated Command Palette**:
   - Palette actions now cleanly navigate to the 7 core destinations.
