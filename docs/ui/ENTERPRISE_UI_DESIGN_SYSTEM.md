# MENDEX ENGINEERING STUDIO — ENTERPRISE UI DESIGN SYSTEM
## Design Guidelines, Styling Tokens, Typography, and Component Specifications

### 1. Design Philosophy

Mendex Engineering Studio is an engineering platform comparable in precision and information density to modern IDEs (VS Code, JetBrains), CAD platforms (FreeCAD, Altium), and simulation suites (COMSOL, Ansys).

**Core Principles:**
- **Information-Dense, Not Cluttered:** High signal-to-noise ratio; engineers must see simulation parameters, waveforms, and file structures without gratuitous padding or empty cards.
- **Dark & Light Mode Parity:** Restrained palettes with semantic color tokens. Dark mode is optimized for low-fatigue multi-hour engineering design sessions.
- **Keyboard & Mouse Efficiency:** Contextual menus, command palette, shortcut keys, and clear focus states.
- **Visual Truthfulness:** Real-time health badges reflect true executable status (`READY`, `DETECTED`, `NOT_INSTALLED`, `OPTIONAL_UNLICENSED`). Unrun tools never show false positive states.

---

### 2. Color Palette & Semantic Tokens

#### Dark Theme (Default Engineering Theme)
- **Background Primary:** `#1e1e2e` (Deep slate / navy)
- **Background Surface / Cards:** `#252538` (Elevated card background)
- **Background Header / Sidebar:** `#181825` (Ground layer)
- **Border Default:** `#313244` (Subtle 1px boundary)
- **Border Active / Focus:** `#89b4fa` (Soft accent blue)
- **Text Primary:** `#cdd6f4` (Crisp off-white)
- **Text Secondary / Muted:** `#a6adc8` (Medium contrast grey)
- **Accent Primary:** `#89b4fa` (Mendex Cyan / Blue)
- **Accent Success:** `#a6e3a1` (Muted emerald green for `READY` / `SUCCEEDED`)
- **Accent Warning:** `#f9e2af` (Warm amber for `DETECTED` / `UNLICENSED`)
- **Accent Danger:** `#f38ba8` (Soft rose red for `FAILED` / `NOT_INSTALLED`)

#### Light Theme
- **Background Primary:** `#f8f9fa`
- **Background Surface / Cards:** `#ffffff`
- **Border Default:** `#dee2e6`
- **Text Primary:** `#212529`
- **Text Secondary:** `#6c757d`
- **Accent Primary:** `#0066cc`

---

### 3. Typography & Spacing

- **Primary UI Font:** `Segoe UI`, `-apple-system`, `system-ui`, sans-serif (Clean Windows rendering)
- **Monospace Code & Log Font:** `Consolas`, `Cascadia Code`, `Courier New`, monospace
- **Scale:**
  - Header Title: 18px / Semi-bold (600)
  - Section Header: 14px / Semi-bold (600)
  - Body Text: 12px / Regular (400)
  - Caption / Badges: 10px / Medium (500)
  - Code / Terminal: 11px / Regular (400)
- **Base Spacing Grid:** 4px, 8px, 12px, 16px, 24px. Avoid oversized margins exceeding 24px.

---

### 4. Layout Architecture

```
+-----------------------------------------------------------------------------------------+
| [Mendex Studio Logo]   Workspace: [ Default Engineering v ]   [Search (Ctrl+K)]   [AI Badge] [?] |
+--------------+--------------------------------------------------------------------------+
|  Dashboard   |  [Breadcrumbs] Workspace > HF-Transformer-Study                          |
| >Workspaces  | +----------------------------------------------------------------------+ |
|  Eng Tools   | | Tab 1: Design | Tab 2: Simulation | Tab 3: FEA Mesh | Tab 4: Logs     | |
|  Sim Lab     | +----------------------------------------------------------------------+ |
|  AI Assist   | | [File Explorer]  | [Main Workbench Panel]      | [Inspector / AI Side] | |
|  Research    | | - core.fem       | Core Geometry: EFD20        | Inductance: 127.4 uH  | |
|  Results     | | - circuit.cir    | Primary Turns: 24           | Flux Peak: 0.18 T     | |
|  Knowledge   | | - bobbin.step    | Gap: 0.5 mm                 | Dowell Rac/Rdc: 1.42  | |
|  Products    | | - results.txt    | [ Run 2D FEA ] [ FreeCAD ]  | [ AI Diagnosis... ]   | |
|  Settings    | +----------------------------------------------------------------------+ |
|              | Bottom Drawer: [ Terminal & Execution Diagnostics                      ] |
+--------------+--------------------------------------------------------------------------+
| Status: All 6 Core Tools READY (LTspice, KiCad, FEMM, FreeCAD, Qucs-S, OpenModelica)    |
+-----------------------------------------------------------------------------------------+
```

---

### 5. Standard Component Styling Tokens

```css
/* Global Studio Widget Theme */
QWidget {
    font-family: 'Segoe UI', sans-serif;
    font-size: 12px;
    color: #cdd6f4;
    background-color: #1e1e2e;
}

QListWidget, QTreeWidget, QTableWidget {
    background-color: #252538;
    border: 1px solid #313244;
    border-radius: 6px;
    padding: 4px;
}

QPushButton {
    background-color: #313244;
    border: 1px solid #45475a;
    border-radius: 4px;
    padding: 6px 14px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #45475a;
    border-color: #89b4fa;
}

QPushButton:pressed {
    background-color: #585b70;
}

QTabBar::tab {
    background: #181825;
    border: 1px solid #313244;
    border-bottom: none;
    padding: 6px 14px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}

QTabBar::tab:selected {
    background: #252538;
    border-color: #89b4fa;
}
```
