# Mendex Engineering Studio v1.9 — Workflow Studio UI/UX Design

## 1. Overview

The **Workflow Studio** (`src/mendex_ui/workflow_canvas/`) provides a modern, responsive, hardware-accelerated visual graph programming interface integrated into Mendex Engineering Studio.

Designed in alignment with enterprise CAD, IDE, and simulation environments, the Studio adheres to the **Catppuccin Mocha (Dark)** and **Catppuccin Latte (Light)** design systems.

---

## 2. Workspace Layout

The Workflow Studio interface is structured into three primary functional zones:

```
+----------------------------------------------------------------------------------------------------+
| [Logo] Workflow: [Dowell Calculation v] [+ New] [Save] [Duplicate] [Templates v] [Fit] [+] [-] [▶ Run] [■ Stop] |
+----------------------------------------------------------------------------------------------------+
|  [Filter nodes...]   |                                              |  [Properties] [Log] [Waveforms] |
|                      |                                              | ------------------------------- |
|  > 1. Inputs         |           (Node A) --------\                 |  Title: Dowell Factor           |
|    - Numeric Input   |                             \                |  Category: Calculation         |
|    - Parameter       |                              +-> (Node C)    |  Formula ID: [dowell_factor]   |
|  > 2. Calculations   |           (Node B) ---------/                |  Status: COMPLETED             |
|    - Formula Eval    |                                              |  Outputs: { "result": 1.406 }   |
|    - Deterministic   |                                              | ------------------------------- |
|  > 3. Tools          |           (16px Snap-to-Grid Canvas)         |  [Live Progress Bar]            |
|  > 4. Results        |                                              |  [Run Log / Terminal Output]    |
|  > 5. Validation     |                                              |                                 |
+----------------------------------------------------------------------------------------------------+
```

### 2.1 Zone 1: Control & Action Header
- **Workflow Switcher & Metadata**: Seamlessly loads, creates, saves, and duplicates workflows.
- **Interactive Templates Dropdown**: One-click generation of validated engineering pipelines (Calculation & Validation, Simulation & Analysis, Evidence & Reporting).
- **Execution Bar**: High-contrast `▶ Run Workflow` (Emerald green) and `■ Cancel` (Ruby red) with live indeterminate progress tracking.
- **Viewport Controls**: Instant `Fit All`, `Zoom In`, `Zoom Out`, and zoom reset.

### 2.2 Zone 2: Node Library Palette (Left Pane)
- Full-text search and category filter.
- Grouped accordion hierarchy containing all 7 node categories.
- Double-click or drag to instantiate directly into the center of the active canvas viewport.

### 2.3 Zone 3: Interactive Canvas (Center Viewport)
- Subpixel antialiased grid background with 16px snap-to-grid alignment.
- Smooth cubic bezier wires connecting output to input sockets.
- Interactive wire dragging with real-time target port highlighting.
- Rubberband box selection, multi-node dragging, and keyboard shortcuts (`Delete`, `Backspace`).
- Pan via mouse wheel click or Alt+Drag; zoom via scroll wheel.

### 2.4 Zone 4: Multi-Tab Inspector (Right Pane)
- **Tab 1: Properties**: Form-based configuration editor tailored dynamically to the selected node type (expressions, values, units, tolerances) and real-time execution outputs.
- **Tab 2: Run Log**: Live, timestamped diagnostic execution console.
- **Tab 3: Waveforms**: Embedded interactive `WaveformViewerWidget` (QtCharts) with pan/zoom and multi-trace overlays.

---

## 3. Visual Styling Tokens & Theme Integration

| Element | Dark Theme (Mocha) | Light Theme (Latte) | Visual Role |
|---|---|---|---|
| **Canvas Background** | `#11111b` (Crust) | `#eff1f5` (Base) | Primary viewport background |
| **Grid Dots** | `#313244` (Surface0) | `#bcc0cc` (Overlay0) | 16px snap coordinate grid |
| **Node Card Body** | `#181825` (Mantle) | `#e6e9ef` (Mantle) | Rounded rect card ($r=8\text{px}$) |
| **Node Selection Glow** | `#89b4fa` (Blue, 2.5px) | `#1e66f5` (Blue, 2.5px) | Selected node focus border |
| **Status Glow: PENDING** | `#45475a` (Surface1) | `#9ca0b0` (Overlay0) | Inactive / unrun node |
| **Status Glow: RUNNING** | `#f9e2af` (Yellow) | `#df8e1d` (Yellow) | Active execution |
| **Status Glow: COMPLETED** | `#a6e3a1` (Green) | `#40a02b` (Green) | Successful completion |
| **Status Glow: FAILED** | `#f38ba8` (Red) | `#d20f39` (Red) | Failure / error state |
| **Status Glow: SKIPPED** | `#585b70` (Surface2) | `#acb0be` (Surface2) | Upstream dependency skipped |
| **Connection Wire** | `#89dceb` (Sky, 2.5px) | `#04a5e5` (Sky, 2.5px) | Directional signal path |

---

## 4. Smoke Verification Screenshots

High-DPI offscreen screenshots captured during automated test execution:
- **Dark Theme Workflow Studio**: `.mendex/qa/v19-workflow/workflow-studio-dark.png`
- **Light Theme Workflow Studio**: `.mendex/qa/v19-workflow/workflow-studio-light.png`
