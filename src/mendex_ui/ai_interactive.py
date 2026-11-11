"""Interactive AI Engineering Copilot — Rich Formatter, Sandbox & Async Execution.

Provides:
- Rich Markdown and LaTeX equation formatter for power electronics formulas.
- Interactive Parameter Sandbox for real-time CCM/DCM Flyback, Buck, and Dowell analysis.
- Asynchronous AI Query Worker (QThread) for smooth, non-blocking UI.
- Contextual action detection and follow-up suggestion generator.
"""
from __future__ import annotations

import html
import math
import re
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QObject, Qt, QThread, Signal
from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QSplitter,
    QTabWidget,
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


def format_engineering_markdown(raw_text: str) -> str:
    """Converts Markdown, LaTeX math blocks, lists, and code blocks into styled HTML."""
    if not raw_text:
        return ""

    text = raw_text

    # 1. Protect and format fenced code blocks
    code_blocks = []
    def save_code_block(match):
        code_content = match.group(2)
        escaped = html.escape(code_content)
        idx = len(code_blocks)
        html_code = (
            f'<div style="background:#11111b; border:1px solid #313244; border-radius:6px; '
            f'padding:10px 14px; margin:8px 0; font-family:Consolas,monospace; color:#a6e3a1; font-size:12px; white-space:pre-wrap;">'
            f'{escaped}</div>'
        )
        code_blocks.append(html_code)
        return f"__CODE_BLOCK_{idx}__"

    text = re.sub(r'```([a-zA-Z0-9_]*)\n?(.*?)```', save_code_block, text, flags=re.DOTALL)

    # 2. LaTeX Display Math: \[ ... \] and $$ ... $$
    def render_display_math(match):
        eq = match.group(1).strip()
        # Common power electronics math cleanups
        eq = re.sub(r'\\frac\{([^}]+)\}\{([^}]+)\}', r'(\1) / (\2)', eq)
        eq = eq.replace(r'\cdot', ' · ').replace(r'\times', ' × ')
        eq = eq.replace(r'\le', ' ≤ ').replace(r'\ge', ' ≥ ')
        eq = eq.replace(r'\Delta', 'Δ').replace(r'\delta', 'δ')
        eq = eq.replace(r'\xi', 'ξ').replace(r'\mu', 'µ')
        eq = eq.replace(r'\Omega', 'Ω').replace(r'\pi', 'π')
        eq = eq.replace(r'\eta', 'η').replace(r'\approx', ' ≈ ')
        eq = eq.replace(r'\sqrt', '√')
        eq = re.sub(r'\\text\{([^}]+)\}', r'\1', eq)
        eq = eq.replace(r'\left', '').replace(r'\right', '')
        eq = re.sub(r'_\{([^}]+)\}', r'<sub>\1</sub>', eq)
        eq = re.sub(r'_([A-Za-z0-9])', r'<sub>\1</sub>', eq)
        eq = re.sub(r'\^\{([^}]+)\}', r'<sup>\1</sup>', eq)
        eq = re.sub(r'\^([A-Za-z0-9])', r'<sup>\1</sup>', eq)

        return (
            f'<div style="background:#11111b; border:1px solid #45475a; border-left:4px solid #89b4fa; '
            f'border-radius:6px; padding:10px 14px; margin:10px 0; font-family:\'Cambria Math\',Consolas,monospace; '
            f'color:#f9e2af; font-size:13.5px; font-weight:bold;">'
            f'<span style="font-size:10px; color:#89b4fa; text-transform:uppercase; letter-spacing:0.5px; display:block; margin-bottom:4px;">📐 Governing Formula</span>'
            f'{eq}</div>'
        )

    text = re.sub(r'\\\[(.*?)\\\]', render_display_math, text, flags=re.DOTALL)
    text = re.sub(r'\$\$(.*?)\$\$', render_display_math, text, flags=re.DOTALL)

    # 3. LaTeX Inline Math: \( ... \) and $ ... $
    def render_inline_math(match):
        eq = match.group(1).strip()
        eq = re.sub(r'\\frac\{([^}]+)\}\{([^}]+)\}', r'(\1)/(\2)', eq)
        eq = eq.replace(r'\cdot', ' · ').replace(r'\times', ' × ')
        eq = eq.replace(r'\le', ' ≤ ').replace(r'\ge', ' ≥ ')
        eq = eq.replace(r'\Delta', 'Δ').replace(r'\delta', 'δ')
        eq = eq.replace(r'\xi', 'ξ').replace(r'\mu', 'µ')
        eq = eq.replace(r'\Omega', 'Ω').replace(r'\pi', 'π')
        eq = eq.replace(r'\eta', 'η').replace(r'\approx', ' ≈ ')
        eq = re.sub(r'\\text\{([^}]+)\}', r'\1', eq)
        eq = re.sub(r'_\{([^}]+)\}', r'<sub>\1</sub>', eq)
        eq = re.sub(r'_([A-Za-z0-9])', r'<sub>\1</sub>', eq)
        eq = re.sub(r'\^\{([^}]+)\}', r'<sup>\1</sup>', eq)
        return f'<span style="font-family:\'Cambria Math\',Consolas,serif; color:#f9e2af; font-weight:bold;">{eq}</span>'

    text = re.sub(r'\\\((.*?)\\\)', render_inline_math, text)
    text = re.sub(r'(?<!\$)\$(?!\$)([^\n$]+)\$(?!\$)', render_inline_math, text)

    # 4. Headers
    text = re.sub(r'^###\s+(.*)$', r'<div style="font-size:13.5px; font-weight:bold; color:#89b4fa; margin:12px 0 4px 0; border-bottom:1px solid #313244; padding-bottom:3px;">⚡ \1</div>', text, flags=re.MULTILINE)
    text = re.sub(r'^##\s+(.*)$', r'<div style="font-size:14.5px; font-weight:bold; color:#cdd6f4; margin:14px 0 6px 0; border-bottom:1px solid #45475a; padding-bottom:4px;">📌 \1</div>', text, flags=re.MULTILINE)
    text = re.sub(r'^#\s+(.*)$', r'<div style="font-size:16px; font-weight:bold; color:#89b4fa; margin:16px 0 8px 0;">\1</div>', text, flags=re.MULTILINE)

    # 5. Bold & Italics
    text = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'(?<!\*)\*([^*\n]+)\*(?!\*)', r'<i>\1</i>', text)

    # 6. Inline code `code`
    text = re.sub(r'`([^`]+)`', r'<code style="background:#313244; color:#a6e3a1; padding:2px 6px; border-radius:3px; font-family:Consolas,monospace; font-size:12px;">\1</code>', text)

    # 7. Bullet Lists & Numbered Lists
    text = re.sub(r'^[-\*]\s+(.*)$', r'<div style="margin:3px 0 3px 12px; line-height:1.4;"><span style="color:#89b4fa;">•</span> \1</div>', text, flags=re.MULTILINE)
    text = re.sub(r'^(\d+)\.\s+(.*)$', r'<div style="margin:3px 0 3px 12px; line-height:1.4;"><span style="color:#a6e3a1; font-weight:bold;">\1.</span> \2</div>', text, flags=re.MULTILINE)

    # 8. Restore Code Blocks
    for i, c_html in enumerate(code_blocks):
        text = text.replace(f"__CODE_BLOCK_{i}__", c_html)

    # 9. Format paragraph breaks
    text = text.replace("\n\n", "<br><br>").replace("\n", "<br>")

    return text


def build_interactive_actions_html(text: str) -> str:
    """Scans text for engineering keywords and builds clickable action pills."""
    lower = text.lower()
    pills = []

    if any(k in lower for k in ("flyback", "dcm", "ccm", "boundary", "duty cycle", "l_crit")):
        pills.append('<a href="action:sandbox_flyback" style="background:#2b223c; color:#cba6f7; text-decoration:none; padding:4px 10px; border-radius:4px; font-size:11px; font-weight:bold; border:1px solid #cba6f7; margin-right:6px;">📐 Live Flyback Sandbox</a>')

    if any(k in lower for k in ("buck", "step-down", "lc filter")):
        pills.append('<a href="action:sandbox_buck" style="background:#2b223c; color:#cba6f7; text-decoration:none; padding:4px 10px; border-radius:4px; font-size:11px; font-weight:bold; border:1px solid #cba6f7; margin-right:6px;">📐 Live Buck Sandbox</a>')

    if any(k in lower for k in ("dowell", "winding loss", "skin depth", "proximity")):
        pills.append('<a href="action:sandbox_dowell" style="background:#2b223c; color:#cba6f7; text-decoration:none; padding:4px 10px; border-radius:4px; font-size:11px; font-weight:bold; border:1px solid #cba6f7; margin-right:6px;">📐 Dowell Loss Sandbox</a>')

    if any(k in lower for k in ("spice", "ltspice", "simulation", "waveform", "transient")):
        pills.append('<a href="action:launch_ltspice" style="background:#1e3a5f; color:#89b4fa; text-decoration:none; padding:4px 10px; border-radius:4px; font-size:11px; font-weight:bold; border:1px solid #3b82f6; margin-right:6px;">⚡ Run LTspice Simulation</a>')

    if any(k in lower for k in ("design", "candidate", "converter", "sizing")):
        pills.append('<a href="action:open_design_studio" style="background:#1e3a2f; color:#a6e3a1; text-decoration:none; padding:4px 10px; border-radius:4px; font-size:11px; font-weight:bold; border:1px solid #a6e3a1; margin-right:6px;">➕ Create Design Candidate</a>')

    if any(k in lower for k in ("kicad", "pcb", "footprint", "schematic")):
        pills.append('<a href="action:open_kicad" style="background:#313244; color:#f9e2af; text-decoration:none; padding:4px 10px; border-radius:4px; font-size:11px; font-weight:bold; border:1px solid #fab387; margin-right:6px;">🖥️ KiCad PCB Workspace</a>')

    if any(k in lower for k in ("femm", "magnetic", "core", "saturation", "b_max")):
        pills.append('<a href="action:open_femm" style="background:#3e1f3a; color:#f38ba8; text-decoration:none; padding:4px 10px; border-radius:4px; font-size:11px; font-weight:bold; border:1px solid #f38ba8; margin-right:6px;">🧲 FEMM Magnetics Lab</a>')

    if any(k in lower for k in ("sic", "gan", "mosfet", "switchloss", "switching loss")):
        pills.append('<a href="action:open_datasets" style="background:#2d354b; color:#89dceb; text-decoration:none; padding:4px 10px; border-radius:4px; font-size:11px; font-weight:bold; border:1px solid #89dceb; margin-right:6px;">🔬 Query SwitchLossDB</a>')

    if not pills:
        pills.append('<a href="action:sandbox_flyback" style="background:#2b223c; color:#cba6f7; text-decoration:none; padding:4px 10px; border-radius:4px; font-size:11px; font-weight:bold; border:1px solid #cba6f7; margin-right:6px;">📐 Open Parameter Sandbox</a>')
        pills.append('<a href="action:open_design_studio" style="background:#1e3a2f; color:#a6e3a1; text-decoration:none; padding:4px 10px; border-radius:4px; font-size:11px; font-weight:bold; border:1px solid #a6e3a1; margin-right:6px;">➕ Design Studio</a>')

    return (
        '<div style="margin-top:12px; padding-top:8px; border-top:1px solid #313244; display:flex; flex-wrap:wrap; gap:6px;">'
        '<span style="font-size:10px; font-weight:bold; color:#a6adc8; text-transform:uppercase; letter-spacing:0.5px; display:inline-block; margin-right:8px; vertical-align:middle;">⚡ Direct Studio Actions:</span>'
        + " ".join(pills)
        + '</div>'
    )


class AIQueryWorker(QThread):
    """Asynchronous worker for executing AI reasoning queries without freezing the UI."""
    response_ready = Signal(dict)
    error_occurred = Signal(str)

    def __init__(self, service: Any, question: str, workspace_context: Optional[dict] = None):
        super().__init__()
        self.service = service
        self.question = question
        self.workspace_context = workspace_context or {}

    def run(self):
        try:
            if hasattr(self.service, "advise_engineering"):
                res = self.service.advise_engineering(self.question, self.workspace_context)
                self.response_ready.emit(res)
            else:
                self.response_ready.emit({
                    "provider": "Mendex Studio",
                    "model": "local",
                    "reply": f"Recorded query: {self.question}",
                    "recommendations": [],
                    "limitations": [],
                })
        except Exception as exc:
            self.error_occurred.emit(str(exc))


class InteractiveParameterSandboxWidget(QWidget):
    """Interactive Engineering Parameter Sandbox.
    
    Provides live sliders and calculation for Flyback CCM/DCM boundary, Buck sizing, and Dowell AC loss.
    """
    ask_ai_requested = Signal(str)
    simulate_requested = Signal(dict)
    create_design_requested = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # Header Title
        title_box = QHBoxLayout()
        icon_lbl = QLabel("⚡")
        icon_lbl.setStyleSheet("font-size: 16px;")
        title_box.addWidget(icon_lbl)
        title = QLabel("Live Parameter Sandbox & Solver Bridge")
        title.setStyleSheet("font-size: 13px; font-weight: 700; color: #89b4fa;")
        title_box.addWidget(title)
        title_box.addStretch()
        layout.addLayout(title_box)

        # Tabs for different topologies
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #313244; background: #181825; border-radius: 6px; }
            QTabBar::tab { background: #11111b; color: #a6adc8; padding: 6px 12px; font-size: 11px; font-weight: bold; border-top-left-radius: 4px; border-top-right-radius: 4px; }
            QTabBar::tab:selected { background: #181825; color: #89b4fa; border-bottom: 2px solid #89b4fa; }
        """)

        # Tab 1: Flyback CCM / DCM Boundary
        self.tab_flyback = self._create_flyback_tab()
        self.tabs.addTab(self.tab_flyback, "Flyback (CCM/DCM)")

        # Tab 2: Buck Converter Filter
        self.tab_buck = self._create_buck_tab()
        self.tabs.addTab(self.tab_buck, "Buck Converter")

        # Tab 3: Dowell AC Loss
        self.tab_dowell = self._create_dowell_tab()
        self.tabs.addTab(self.tab_dowell, "Dowell AC Loss")

        layout.addWidget(self.tabs)

        # Action Buttons at Bottom of Sandbox
        btn_box = QVBoxLayout()
        btn_box.setSpacing(6)

        self.btn_ask_ai = QPushButton("💬 Ask AI Copilot to Optimize These Parameters")
        self.btn_ask_ai.setStyleSheet("background-color: #313244; color: #89b4fa; font-weight: 700; padding: 7px; border-radius: 4px; border: 1px solid #45475a;")
        self.btn_ask_ai.clicked.connect(self._on_ask_ai_clicked)
        btn_box.addWidget(self.btn_ask_ai)

        h_actions = QHBoxLayout()
        h_actions.setSpacing(6)

        self.btn_sim = QPushButton("⚡ Simulate in LTspice")
        self.btn_sim.setStyleSheet("background-color: #1e3a5f; color: #89b4fa; font-weight: 700; padding: 6px; border-radius: 4px; border: 1px solid #3b82f6;")
        self.btn_sim.clicked.connect(self._on_sim_clicked)
        h_actions.addWidget(self.btn_sim)

        self.btn_cand = QPushButton("➕ Push Design Candidate")
        self.btn_cand.setStyleSheet("background-color: #1e3a2f; color: #a6e3a1; font-weight: 700; padding: 6px; border-radius: 4px; border: 1px solid #a6e3a1;")
        self.btn_cand.clicked.connect(self._on_cand_clicked)
        h_actions.addWidget(self.btn_cand)

        btn_box.addLayout(h_actions)
        layout.addLayout(btn_box)

        # Run initial calculations
        self.calculate_flyback()
        self.calculate_buck()
        self.calculate_dowell()

    def _create_flyback_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Live Mode Banner
        self.lbl_flyback_mode = QLabel("MODE: CONTINUOUS CONDUCTION (CCM)")
        self.lbl_flyback_mode.setAlignment(Qt.AlignCenter)
        self.lbl_flyback_mode.setStyleSheet("background: #1e3a2f; color: #a6e3a1; font-weight: 800; font-size: 11px; padding: 6px; border-radius: 4px; border: 1px solid #a6e3a1;")
        layout.addWidget(self.lbl_flyback_mode)

        # Controls Grid
        grid = QGridLayout()
        grid.setSpacing(6)

        # Vin
        grid.addWidget(QLabel("Input Voltage (Vin):"), 0, 0)
        self.spin_flyback_vin = QDoubleSpinBox()
        self.spin_flyback_vin.setRange(5.0, 600.0)
        self.spin_flyback_vin.setValue(24.0)
        self.spin_flyback_vin.setSuffix(" V")
        self.spin_flyback_vin.valueChanged.connect(self.calculate_flyback)
        grid.addWidget(self.spin_flyback_vin, 0, 1)

        # Vout
        grid.addWidget(QLabel("Output Voltage (Vout):"), 1, 0)
        self.spin_flyback_vout = QDoubleSpinBox()
        self.spin_flyback_vout.setRange(1.0, 200.0)
        self.spin_flyback_vout.setValue(12.0)
        self.spin_flyback_vout.setSuffix(" V")
        self.spin_flyback_vout.valueChanged.connect(self.calculate_flyback)
        grid.addWidget(self.spin_flyback_vout, 1, 1)

        # Pout
        grid.addWidget(QLabel("Output Power (Pout):"), 2, 0)
        self.spin_flyback_pout = QDoubleSpinBox()
        self.spin_flyback_pout.setRange(1.0, 1000.0)
        self.spin_flyback_pout.setValue(60.0)
        self.spin_flyback_pout.setSuffix(" W")
        self.spin_flyback_pout.valueChanged.connect(self.calculate_flyback)
        grid.addWidget(self.spin_flyback_pout, 2, 1)

        # Fsw
        grid.addWidget(QLabel("Switching Freq (fsw):"), 3, 0)
        self.spin_flyback_fsw = QDoubleSpinBox()
        self.spin_flyback_fsw.setRange(10.0, 1000.0)
        self.spin_flyback_fsw.setValue(100.0)
        self.spin_flyback_fsw.setSuffix(" kHz")
        self.spin_flyback_fsw.valueChanged.connect(self.calculate_flyback)
        grid.addWidget(self.spin_flyback_fsw, 3, 1)

        # Primary Inductance Lp
        grid.addWidget(QLabel("Primary Inductance (Lp):"), 4, 0)
        self.spin_flyback_lp = QDoubleSpinBox()
        self.spin_flyback_lp.setRange(1.0, 5000.0)
        self.spin_flyback_lp.setValue(120.0)
        self.spin_flyback_lp.setSuffix(" µH")
        self.spin_flyback_lp.valueChanged.connect(self.calculate_flyback)
        grid.addWidget(self.spin_flyback_lp, 4, 1)

        layout.addLayout(grid)

        # Live Results Box
        self.lbl_flyback_telemetry = QLabel()
        self.lbl_flyback_telemetry.setStyleSheet("background: #11111b; border: 1px solid #313244; border-radius: 4px; padding: 8px; font-family: Consolas, monospace; font-size: 11px; color: #cdd6f4;")
        layout.addWidget(self.lbl_flyback_telemetry)
        layout.addStretch()

        return widget

    def calculate_flyback(self):
        vin = self.spin_flyback_vin.value()
        vout = self.spin_flyback_vout.value()
        pout = self.spin_flyback_pout.value()
        fsw = self.spin_flyback_fsw.value() * 1000.0
        lp = self.spin_flyback_lp.value() * 1e-6

        # Sizing calculations
        d = vout / (vout + vin)
        r_load = (vout ** 2) / max(0.01, pout)
        # Critical boundary inductance
        l_crit = ((1.0 - d) ** 2 * r_load) / (2.0 * fsw)
        l_crit_uh = l_crit * 1e6

        is_ccm = lp >= l_crit

        if is_ccm:
            self.lbl_flyback_mode.setText("🟢 CONTINUOUS CONDUCTION MODE (CCM)")
            self.lbl_flyback_mode.setStyleSheet("background: #1e3a2f; color: #a6e3a1; font-weight: 800; font-size: 11px; padding: 6px; border-radius: 4px; border: 1px solid #a6e3a1;")
            i_in_avg = pout / max(0.1, vin)
            delta_il = (vin * d) / max(1e-9, lp * fsw)
            i_peak = (pout / (vin * d)) + (delta_il / 2.0)
            krf = delta_il / max(0.1, (pout / (vin * d)))
        else:
            self.lbl_flyback_mode.setText("🟠 DISCONTINUOUS CONDUCTION MODE (DCM)")
            self.lbl_flyback_mode.setStyleSheet("background: #3e2819; color: #fab387; font-weight: 800; font-size: 11px; padding: 6px; border-radius: 4px; border: 1px solid #fab387;")
            i_peak = math.sqrt((2.0 * pout) / max(1e-9, lp * fsw))
            delta_il = i_peak
            krf = 2.0

        i_rms = i_peak * math.sqrt(d / 3.0)
        energy_uj = 0.5 * lp * (i_peak ** 2) * 1e6

        txt = (
            f"<b>Operating Duty Cycle (D):</b> {d:.3f} ({d*100:.1f}%)\n"
            f"<b>Boundary Inductance (L_crit):</b> {l_crit_uh:.1f} µH\n"
            f"<b>Selected Inductance (Lp):</b> {lp*1e6:.1f} µH ({'Above L_crit' if is_ccm else 'Below L_crit'})\n"
            f"<b>Peak Primary Current (I_pk):</b> {i_peak:.2f} A\n"
            f"<b>Primary RMS Current (I_rms):</b> {i_rms:.2f} A\n"
            f"<b>Inductor Ripple (ΔI_L):</b> {delta_il:.2f} A\n"
            f"<b>Stored Energy per Cycle:</b> {energy_uj:.1f} µJ"
        )
        self.lbl_flyback_telemetry.setText(txt.replace("\n", "<br>"))

    def _create_buck_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        grid = QGridLayout()
        grid.setSpacing(6)

        grid.addWidget(QLabel("Input Voltage (Vin):"), 0, 0)
        self.spin_buck_vin = QDoubleSpinBox()
        self.spin_buck_vin.setRange(2.0, 200.0)
        self.spin_buck_vin.setValue(24.0)
        self.spin_buck_vin.setSuffix(" V")
        self.spin_buck_vin.valueChanged.connect(self.calculate_buck)
        grid.addWidget(self.spin_buck_vin, 0, 1)

        grid.addWidget(QLabel("Output Voltage (Vout):"), 1, 0)
        self.spin_buck_vout = QDoubleSpinBox()
        self.spin_buck_vout.setRange(1.0, 100.0)
        self.spin_buck_vout.setValue(5.0)
        self.spin_buck_vout.setSuffix(" V")
        self.spin_buck_vout.valueChanged.connect(self.calculate_buck)
        grid.addWidget(self.spin_buck_vout, 1, 1)

        grid.addWidget(QLabel("Load Current (Iout):"), 2, 0)
        self.spin_buck_iout = QDoubleSpinBox()
        self.spin_buck_iout.setRange(0.1, 100.0)
        self.spin_buck_iout.setValue(5.0)
        self.spin_buck_iout.setSuffix(" A")
        self.spin_buck_iout.valueChanged.connect(self.calculate_buck)
        grid.addWidget(self.spin_buck_iout, 2, 1)

        grid.addWidget(QLabel("Switching Freq (fsw):"), 3, 0)
        self.spin_buck_fsw = QDoubleSpinBox()
        self.spin_buck_fsw.setRange(10.0, 1000.0)
        self.spin_buck_fsw.setValue(200.0)
        self.spin_buck_fsw.setSuffix(" kHz")
        self.spin_buck_fsw.valueChanged.connect(self.calculate_buck)
        grid.addWidget(self.spin_buck_fsw, 3, 1)

        grid.addWidget(QLabel("Filter Inductor (L):"), 4, 0)
        self.spin_buck_l = QDoubleSpinBox()
        self.spin_buck_l.setRange(0.5, 500.0)
        self.spin_buck_l.setValue(15.0)
        self.spin_buck_l.setSuffix(" µH")
        self.spin_buck_l.valueChanged.connect(self.calculate_buck)
        grid.addWidget(self.spin_buck_l, 4, 1)

        layout.addLayout(grid)

        self.lbl_buck_telemetry = QLabel()
        self.lbl_buck_telemetry.setStyleSheet("background: #11111b; border: 1px solid #313244; border-radius: 4px; padding: 8px; font-family: Consolas, monospace; font-size: 11px; color: #cdd6f4;")
        layout.addWidget(self.lbl_buck_telemetry)
        layout.addStretch()

        return widget

    def calculate_buck(self):
        vin = self.spin_buck_vin.value()
        vout = min(self.spin_buck_vout.value(), vin * 0.98)
        iout = self.spin_buck_iout.value()
        fsw = self.spin_buck_fsw.value() * 1000.0
        l_h = self.spin_buck_l.value() * 1e-6

        d = vout / max(0.1, vin)
        delta_il = ((vin - vout) * d) / max(1e-9, fsw * l_h)
        ripple_ratio = delta_il / max(0.01, iout)
        i_peak = iout + (delta_il / 2.0)
        # Min C for 1% output ripple
        c_min_uf = (delta_il / (8.0 * fsw * (0.01 * vout))) * 1e6

        txt = (
            f"<b>Duty Cycle (D):</b> {d:.3f} ({d*100:.1f}%)\n"
            f"<b>Inductor Ripple (ΔI_L):</b> {delta_il:.2f} A (r = {ripple_ratio*100:.1f}%)\n"
            f"<b>Peak Switch Current (I_pk):</b> {i_peak:.2f} A\n"
            f"<b>Min Output Capacitor (1% ripple):</b> {c_min_uf:.1f} µF"
        )
        self.lbl_buck_telemetry.setText(txt.replace("\n", "<br>"))

    def _create_dowell_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        grid = QGridLayout()
        grid.setSpacing(6)

        grid.addWidget(QLabel("Conductor Thickness (h):"), 0, 0)
        self.spin_dowell_h = QDoubleSpinBox()
        self.spin_dowell_h.setRange(0.05, 5.0)
        self.spin_dowell_h.setValue(0.5)
        self.spin_dowell_h.setSuffix(" mm")
        self.spin_dowell_h.valueChanged.connect(self.calculate_dowell)
        grid.addWidget(self.spin_dowell_h, 0, 1)

        grid.addWidget(QLabel("Frequency (f):"), 1, 0)
        self.spin_dowell_f = QDoubleSpinBox()
        self.spin_dowell_f.setRange(1.0, 1000.0)
        self.spin_dowell_f.setValue(100.0)
        self.spin_dowell_f.setSuffix(" kHz")
        self.spin_dowell_f.valueChanged.connect(self.calculate_dowell)
        grid.addWidget(self.spin_dowell_f, 1, 1)

        grid.addWidget(QLabel("Winding Layers (m):"), 2, 0)
        self.spin_dowell_m = QSpinBox()
        self.spin_dowell_m.setRange(1, 12)
        self.spin_dowell_m.setValue(2)
        self.spin_dowell_m.valueChanged.connect(self.calculate_dowell)
        grid.addWidget(self.spin_dowell_m, 2, 1)

        layout.addLayout(grid)

        self.lbl_dowell_telemetry = QLabel()
        self.lbl_dowell_telemetry.setStyleSheet("background: #11111b; border: 1px solid #313244; border-radius: 4px; padding: 8px; font-family: Consolas, monospace; font-size: 11px; color: #cdd6f4;")
        layout.addWidget(self.lbl_dowell_telemetry)
        layout.addStretch()

        return widget

    def calculate_dowell(self):
        h_m = self.spin_dowell_h.value() * 1e-3
        f_hz = self.spin_dowell_f.value() * 1000.0
        m = self.spin_dowell_m.value()

        # Copper skin depth delta = sqrt(rho / (pi * f * mu0))
        rho_cu = 1.72e-8  # Ohm*m
        mu0 = 4.0 * math.pi * 1e-7
        delta_m = math.sqrt(rho_cu / (math.pi * f_hz * mu0))
        delta_mm = delta_m * 1e3
        xi = h_m / delta_m

        # Dowell factor approximation
        # F_R = xi * [ (sinh 2xi + sin 2xi)/(cosh 2xi - cos 2xi) + 2(m^2 - 1)/3 * (sinh xi - sin xi)/(cosh xi + cos xi) ]
        try:
            t1 = (math.sinh(2 * xi) + math.sin(2 * xi)) / max(1e-6, (math.cosh(2 * xi) - math.cos(2 * xi)))
            t2 = (2.0 * (m ** 2 - 1) / 3.0) * ((math.sinh(xi) - math.sin(xi)) / max(1e-6, (math.cosh(xi) + math.cos(xi))))
            fr = xi * (t1 + t2)
        except OverflowError:
            fr = 10.0

        txt = (
            f"<b>Copper Skin Depth (δ):</b> {delta_mm:.3f} mm\n"
            f"<b>Thickness Ratio (ξ = h/δ):</b> {xi:.2f}\n"
            f"<b>Dowell Factor (F_R = R_AC / R_DC):</b> {fr:.2f}\n"
            f"<b>High-Freq AC Loss Penalty:</b> {(fr - 1.0)*100:.1f}% higher"
        )
        self.lbl_dowell_telemetry.setText(txt.replace("\n", "<br>"))

    def _on_ask_ai_clicked(self):
        idx = self.tabs.currentIndex()
        if idx == 0:
            prompt = (
                f"Analyze this Flyback converter operating point: Vin={self.spin_flyback_vin.value()}V, "
                f"Vout={self.spin_flyback_vout.value()}V, Pout={self.spin_flyback_pout.value()}W, "
                f"fsw={self.spin_flyback_fsw.value()}kHz, Lp={self.spin_flyback_lp.value()}uH. "
                f"How can I optimize efficiency and reduce primary switching stress?"
            )
        elif idx == 1:
            prompt = (
                f"Analyze this Buck converter design: Vin={self.spin_buck_vin.value()}V, "
                f"Vout={self.spin_buck_vout.value()}V, Iout={self.spin_buck_iout.value()}A, "
                f"fsw={self.spin_buck_fsw.value()}kHz, L={self.spin_buck_l.value()}uH. "
                f"Suggest recommendations to reduce output voltage ripple below 10mV."
            )
        else:
            prompt = (
                f"Analyze Dowell AC winding loss for transformer: Conductor thickness h={self.spin_dowell_h.value()}mm, "
                f"frequency={self.spin_dowell_f.value()}kHz, layers m={self.spin_dowell_m.value()}. "
                f"What interleaving or litz wire structure reduces high-frequency proximity losses?"
            )
        self.ask_ai_requested.emit(prompt)

    def _on_sim_clicked(self):
        idx = self.tabs.currentIndex()
        if idx == 0:
            params = {
                "topology": "flyback",
                "vin_v": self.spin_flyback_vin.value(),
                "vout_v": self.spin_flyback_vout.value(),
                "pout_w": self.spin_flyback_pout.value(),
                "fsw_hz": self.spin_flyback_fsw.value() * 1000.0,
                "lp_h": self.spin_flyback_lp.value() * 1e-6,
            }
        else:
            params = {
                "topology": "buck",
                "vin_v": self.spin_buck_vin.value(),
                "vout_v": self.spin_buck_vout.value(),
                "iout_a": self.spin_buck_iout.value(),
                "fsw_hz": self.spin_buck_fsw.value() * 1000.0,
                "l_h": self.spin_buck_l.value() * 1e-6,
            }
        self.simulate_requested.emit(params)

    def _on_cand_clicked(self):
        idx = self.tabs.currentIndex()
        top = "flyback" if idx == 0 else "buck"
        params = {
            "topology": top,
            "vin_nom_v": self.spin_flyback_vin.value() if top == "flyback" else self.spin_buck_vin.value(),
            "vout_nom_v": self.spin_flyback_vout.value() if top == "flyback" else self.spin_buck_vout.value(),
            "iout_nom_a": (self.spin_flyback_pout.value() / self.spin_flyback_vout.value()) if top == "flyback" else self.spin_buck_iout.value(),
        }
        self.create_design_requested.emit(params)

    def select_mode(self, mode_name: str):
        if "flyback" in mode_name.lower():
            self.tabs.setCurrentIndex(0)
        elif "buck" in mode_name.lower():
            self.tabs.setCurrentIndex(1)
        elif "dowell" in mode_name.lower():
            self.tabs.setCurrentIndex(2)
