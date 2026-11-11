"""Engineering Product Design Guide and Copy-Paste AI Prompts Dialog."""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QGuiApplication
from PySide6.QtWidgets import (
    QDialog, QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QTabWidget, QTextEdit, QVBoxLayout, QWidget,
)


MASTER_CODEX_PROMPT = """You are an expert power electronics engineering AI agent connected to Mendex Engineering Studio.
Design an authoritative, production-grade engineering baseline for the following product:

Product Name: SpectraVolt SV-1000 Precision HV DC-DC Converter
Product Code: SV-1000
Topology: High-Voltage Isolated Flyback Converter
Operating Envelope:
- Input Voltage: 20 V to 28 V DC (24 V nominal)
- Output Voltage: 1000 V DC regulated
- Output Current: 0.1 A (100 W output power)
- Switching Frequency: 100 kHz
- Isolation Voltage: 3000 V RMS (IEC-61010-1 compliance)

Execute the following 10 design activities through Mendex Core:
1. Define the authoritative specification envelope in the project workspace.
2. Execute deterministic sizing calculations: Dowell AC winding loss factor (Fr), Steinmetz core loss (N87 Ferrite), and semiconductor switching/conduction losses (Wolfspeed C2M0080120D SiC MOSFET). Save to calculations/sv1000_sizing_analysis.json.
3. Synthesize the SPICE circuit netlist (flyback_circuit.net) and schematic (flyback_schematic.asc) with a 45% PWM gate drive pulse and primary clamp snubber.
4. Run headless LTspice simulation to verify 1000 V output voltage regulation and ripple; save raw waveform (flyback_circuit.raw) and solver.log.
5. Generate a 2D FEMM 4.2 magnetic model (temp_mag.fem) and verify peak flux density remains below 0.35 T saturation.
6. Generate native KiCad 10 schematic (.kicad_sch) and 2-layer PCB layout (.kicad_pcb) featuring a 5.0 mm isolation milling slot on Edge.Cuts between primary and secondary circuits.
7. Execute kicad-cli sch erc (0 violations) and kicad-cli pcb drc, exporting drc/drc_report.json.
8. Generate FreeCAD parametric 3D bobbin solid model (bobbin.step) in ISO 10303 STEP format.
9. Generate structured BOM (bom.json and bom.csv) with qualified industry part numbers (Wolfspeed SiC FET, SiC diode, TDK film caps).
10. Generate formal immutable Engineering Dossier (report.html) with SHA-256 evidence hashes.

Ensure all calculations are mathematically deterministic and truthful. Unperformed checks must remain NOT_EVALUATED."""

CALCULATIONS_PROMPT = """Please perform deterministic mathematical sizing calculations for SV-1000 HV DC-DC Converter:
- Input: 24 V nom, Output: 1000 V, 0.1 A, 100 kHz.
1. Flyback Transformer Turns: Calculate primary turns Np, secondary turns Ns, turns ratio (Ns/Np), and magnetizing inductance Lp for 45% maximum duty cycle.
2. Dowell AC Winding Factor: Compute copper skin depth (delta) at 100 kHz, Dowell ratio Fr = Rac/Rdc, and AC resistance.
3. Steinmetz Core Loss: Calculate volumetric loss Pv and total loss for TDK N87 power ferrite at Bmax = 0.22 T and 100 kHz.
4. Semiconductor Losses: Compute conduction loss (Irms^2 * Rds_on) and switching loss (fsw * (Eon + Eoff)) for Wolfspeed C2M0080120D SiC MOSFET.
Save the complete structured result in JSON format to:
products/<project_id>/revisions/<rev_id>/calculations/sv1000_sizing_analysis.json"""

SIMULATION_PROMPT = """Generate an LTspice transient simulation for the SV-1000 High-Voltage Isolated Flyback Converter:
1. Synthesize SPICE netlist: Include primary switch (NMOS with C2M0080120D parameters), coupled transformer inductors (Lp and Ls with K=0.995), RCD clamp snubber, secondary ultrafast diode, and capacitive output filter with 10k resistive load.
2. Configure gate drive: V_G1 GATE 0 PULSE(0 10 0 10n 10n 4.5u 10u) for 45% duty cycle at 100 kHz.
3. Add transient simulation directive: .tran 0 2m 1.5m 10n
4. Run headless LTspice simulation using Mendex LTspice runner.
5. Save the output to circuit/flyback_circuit.net and simulations/flyback_circuit.raw."""

KICAD_PROMPT = """Generate native KiCad 10 schematic and PCB layout for the SV-1000 High-Voltage Converter:
1. Schematic (.kicad_sch): Connect primary input filter, PWM gate drive, Wolfspeed SiC MOSFET, high-voltage transformer, secondary diode bridge, and 1000 V output terminals.
2. PCB Layout (.kicad_pcb): 2-layer board layout with 0.8 mm primary power tracks, 0.35 mm secondary tracks.
3. High-Voltage Isolation Slot: Route a 5.0 mm wide isolation slot on the Edge.Cuts layer between the primary (low voltage) and secondary (1000 V HV) zones to meet IEC-61010-1 creepage requirements.
4. Run native KiCad CLI:
   kicad-cli sch erc --output erc/erc_report.json <schematic_path>
   kicad-cli pcb drc --output drc/drc_report.json <pcb_path>
Verify 0 unconnected nets and 0 DRC violations."""

FREECAD_PROMPT = """Generate a 3D CAD solid model for the SV-1000 transformer bobbin using FreeCAD:
1. Create a parametric Python script utilizing the FreeCAD Part module:
   - Outer bobbin body: E22/6/16 geometry with raised 5.0 mm isolation barrier.
   - Primary and secondary separated winding bays.
   - Center through-hole for ferrite core center post.
2. Invoke freecadcmd.exe headlessly to execute the script and export the model to ISO 10303 STEP format:
   products/<project_id>/revisions/<rev_id>/mechanical/bobbin.step
3. Verify that bobbin.step exists and contains valid STEP boundary-representation geometry."""

BOM_PROMPT = """Generate a qualified Bill of Materials for the SV-1000 Precision HV DC-DC Converter:
Include qualified, commercially purchasable power electronic components:
- Primary Switch: Wolfspeed C2M0080120D 1200V SiC MOSFET (TO-247-3)
- Secondary Rectifier: Wolfspeed C4D02120A 1200V SiC Schottky Diode (TO-220-2)
- Output Capacitor: TDK / EPCOS High-Voltage Metallized Film Capacitor 1200V 2.2uF
- Transformer Core: TDK / Epcos Planar E22/6/16 N87 Ferrite Core + Custom Bobbin
- Clamp Diode: STMicroelectronics STTH112 1200V Ultrafast Diode
- Bleeder Resistor: Ohmite Slim-MOX Precision High-Voltage Resistor 10M 1500V
Export the BOM to bom/bom.json and bom/bom.csv with part numbers, ratings, quantities, and unit pricing."""


class PromptCard(QFrame):
    """Visual card displaying an AI prompt template with 1-click clipboard copy."""

    def __init__(self, title: str, description: str, prompt_text: str, is_dark: bool = True, parent=None):
        super().__init__(parent)
        self.title = title
        self.prompt_text = prompt_text
        self.is_dark = is_dark
        self.init_ui(description)

    def init_ui(self, description: str):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        hdr_row = QHBoxLayout()
        title_lbl = QLabel(f"🤖 {self.title}")
        title_lbl.setStyleSheet("font-weight: 700; font-size: 13px; color: #89b4fa;")
        hdr_row.addWidget(title_lbl)
        hdr_row.addStretch()

        self.lbl_copied = QLabel("")
        self.lbl_copied.setStyleSheet("color: #a6e3a1; font-weight: 600; font-size: 11px;")
        hdr_row.addWidget(self.lbl_copied)

        self.btn_copy = QPushButton("📋 Copy Prompt")
        self.btn_copy.setFixedHeight(26)
        self.btn_copy.setStyleSheet(
            "background-color: #1b4332; color: #a6e3a1; font-weight: 700; font-size: 11px; "
            "border: 1px solid #2d6a4f; border-radius: 4px; padding: 2px 10px;"
        )
        self.btn_copy.clicked.connect(self._copy_to_clipboard)
        hdr_row.addWidget(self.btn_copy)
        layout.addLayout(hdr_row)

        desc_lbl = QLabel(description)
        desc_lbl.setStyleSheet("color: #a6adc8; font-size: 11px;")
        desc_lbl.setWordWrap(True)
        layout.addWidget(desc_lbl)

        txt_preview = QTextEdit()
        txt_preview.setReadOnly(True)
        txt_preview.setFont(QFont("Consolas", 9))
        txt_preview.setPlainText(self.prompt_text)
        txt_preview.setMaximumHeight(110)
        txt_preview.setStyleSheet(
            "background: #11111b; color: #cdd6f4; border: 1px solid #313244; border-radius: 4px; padding: 6px;"
        )
        layout.addWidget(txt_preview)

        self.setStyleSheet(
            "QFrame { background-color: #181825; border: 1px solid #313244; border-radius: 8px; }"
        )

    def _copy_to_clipboard(self):
        clipboard = QGuiApplication.clipboard()
        clipboard.setText(self.prompt_text)
        self.lbl_copied.setText("✓ Copied!")
        self.btn_copy.setText("✓ Copied")
        QTimer.singleShot(2500, self._reset_copy_label)

    def _reset_copy_label(self):
        self.lbl_copied.setText("")
        self.btn_copy.setText("📋 Copy Prompt")


class EngineeringGuideDialog(QDialog):
    """Complete product engineering workflow guide and copy-paste prompt library for AI agents."""

    def __init__(self, is_dark: bool = True, parent=None):
        super().__init__(parent)
        self.is_dark = is_dark
        self.setWindowTitle("📘 Mendex Studio — Product Design Guide & AI Engineering Prompts")
        self.resize(1000, 720)
        self.init_ui()

    def init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(16, 16, 16, 16)
        root_layout.setSpacing(12)

        # Header Title
        hdr_row = QHBoxLayout()
        title_lbl = QLabel("📘 Complete Product Engineering Guide")
        title_lbl.setStyleSheet("font-size: 18px; font-weight: 700; color: #89b4fa;")
        hdr_row.addWidget(title_lbl)
        hdr_row.addStretch()

        btn_close = QPushButton("✕ Close")
        btn_close.setFixedHeight(28)
        btn_close.setStyleSheet("background: #24273a; color: #cdd6f4; font-weight: 600; border: 1px solid #45475a; border-radius: 4px; padding: 2px 14px;")
        btn_close.clicked.connect(self.accept)
        hdr_row.addWidget(btn_close)
        root_layout.addLayout(hdr_row)

        subtitle = QLabel(
            "Learn how to design power electronics products end-to-end using AI engineering agents (Codex, Antigravity, Claude Code) "
            "and review real simulation waveforms, KiCad CAD files, and validation evidence in Mendex Studio."
        )
        subtitle.setStyleSheet("color: #a6adc8; font-size: 12px; line-height: 1.4;")
        subtitle.setWordWrap(True)
        root_layout.addWidget(subtitle)

        # Tabbed Guide
        tabs = QTabWidget()
        tabs.setDocumentMode(True)

        # Tab 1: Operational Playbook (When & How to use LTspice, KiCad, FreeCAD, Review)
        tab_playbook = QWidget()
        self._init_playbook_tab(tab_playbook)
        tabs.addTab(tab_playbook, "📖 Tool Playbook: When & How to Use Solvers & Review")

        # Tab 2: 12-Stage Step-by-Step Workflow
        tab_flow = QWidget()
        self._init_workflow_tab(tab_flow)
        tabs.addTab(tab_flow, "🚀 12-Stage Product Design Workflow")

        # Tab 3: AI Engineering Prompts
        tab_prompts = QWidget()
        self._init_prompts_tab(tab_prompts)
        tabs.addTab(tab_prompts, "🤖 Copy-Paste AI Prompts (Codex / Claude)")

        # Tab 3: Connecting AI via MCP & CLI
        tab_connect = QWidget()
        self._init_connect_tab(tab_connect)
        tabs.addTab(tab_connect, "🛠️ Connecting Codex / Claude via MCP")

        # Tab 4: Review & Approvals Guide
        tab_review = QWidget()
        self._init_review_tab(tab_review)
        tabs.addTab(tab_review, "✍️ Review & Sign-Off Checklist")

        root_layout.addWidget(tabs, 1)

    def _init_workflow_tab(self, parent_widget: QWidget):
        layout = QVBoxLayout(parent_widget)
        layout.setContentsMargins(10, 10, 10, 10)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        content = QWidget()
        c_layout = QVBoxLayout(content)
        c_layout.setSpacing(12)

        steps = [
            ("Stage 1: Requirements & Specifications",
             "Define the electrical envelope: input voltage range (Vin_min, Vin_nom), target output (Vout, Iout), switching frequency (fsw), and safety isolation voltage (Viso). "
             "In Studio: Click '📝 Specifications Revisions' or '+ New Project' to define or update specifications.",
             "#89b4fa"),
            ("Stage 2: Deterministic Sizing Calculations",
             "Calculate transformer turns ratio (Np, Ns), primary magnetizing inductance (Lp), Dowell high-frequency AC winding factor (Fr = Rac / Rdc), Steinmetz magnetic core dissipation, and semiconductor losses using SwitchLossDB or vendor datasheet parameters. "
             "In Studio: View results on the '🔬 Calculations' tab or click '🔬 Browse SwitchLossDB Research Catalog' to compare alternative SiC/GaN devices.",
             "#a6e3a1"),
            ("Stage 3: Circuit Topology Synthesis",
             "Generate standard SPICE circuit netlist (flyback_circuit.net) and schematic (flyback_schematic.asc) with power switch, RCD snubber, resonant tank, and secondary diode rectifier.",
             "#89b4fa"),
            ("Stage 4: Electrical Simulation & Waveforms",
             "Execute headless LTspice solver (LTspice.exe -b -ascii). Extract transient output voltage, peak voltage stress, and ripple. "
             "In Studio: Click '⚡ Simulations' to inspect interactive raw waveforms (.raw) in the built-in waveform viewer.",
             "#f9e2af"),
            ("Stage 5: 2D Finite-Element Magnetic Analysis (FEA)",
             "Emit Lua script and run FEMM 4.2 headlessly (-windowhide). Compute peak flux density (Bmax) across core cross-section to guarantee it operates well below 0.35 T saturation.",
             "#a6e3a1"),
            ("Stage 6, 7 & 8: KiCad 10 Schematic, PCB Layout & DRC/ERC",
             "Synthesize native KiCad 10 schematic (.kicad_sch) and PCB (.kicad_pcb). Route a 5.0 mm isolation milling slot on Edge.Cuts between primary (low voltage) and secondary (1000 V) domains. "
             "Run native kicad-cli sch erc (0 violations) and kicad-cli pcb drc (drc_report.json).",
             "#89b4fa"),
            ("Stage 9: Thermal & 3D Mechanical Modeling",
             "Execute FreeCAD Python generator (freecadcmd.exe) to produce an ISO 10303 STEP solid model (bobbin.step) of the custom transformer bobbin and isolation barrier.",
             "#cba6f7"),
            ("Stage 10: Bill of Materials (BOM) & Component Selection",
             "Compile structured BOM (bom.json, bom.csv) with real, purchasable components (Wolfspeed C2M0080120D SiC MOSFET, C4D02120A SiC diode, TDK film caps). Total estimated BOM cost calculated.",
             "#f9e2af"),
            ("Stage 11: Validation Benchmarks Register",
             "Record numerical benchmark claims comparing measured simulation waveforms vs design specifications (output voltage, ripple, efficiency, thermal headroom).",
             "#a6e3a1"),
            ("Stage 12: Prototype Readiness Gate Review & Sign-Off",
             "Review all 12 mandatory engineering readiness gates. Use Tab 0 ('✍️ Review & Approvals') to sign off gates with reviewer identity and justification notes. Once all gates pass, status turns to 'PROTOTYPE READY'.",
             "#a6e3a1"),
        ]

        for num, (title, desc, color) in enumerate(steps, start=1):
            box = QFrame()
            box.setStyleSheet("background: #181825; border: 1px solid #313244; border-radius: 6px; padding: 10px;")
            b_layout = QVBoxLayout(box)
            b_layout.setSpacing(4)

            t_lbl = QLabel(f"#{num} — {title}")
            t_lbl.setStyleSheet(f"font-weight: 700; font-size: 12px; color: {color};")
            b_layout.addWidget(t_lbl)

            d_lbl = QLabel(desc)
            d_lbl.setStyleSheet("color: #cdd6f4; font-size: 11px; line-height: 1.4;")
            d_lbl.setWordWrap(True)
            b_layout.addWidget(d_lbl)

            c_layout.addWidget(box)

        scroll.setWidget(content)
        layout.addWidget(scroll)

    def _init_prompts_tab(self, parent_widget: QWidget):
        layout = QVBoxLayout(parent_widget)
        layout.setContentsMargins(10, 10, 10, 10)

        info_lbl = QLabel("Click '📋 Copy Prompt' and paste directly into OpenAI Codex, Anthropic Claude Code, or Antigravity:")
        info_lbl.setStyleSheet("color: #89b4fa; font-weight: 600; font-size: 11px;")
        layout.addWidget(info_lbl)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        content = QWidget()
        c_layout = QVBoxLayout(content)
        c_layout.setSpacing(12)

        c_layout.addWidget(PromptCard(
            "Master Prompt: Full Product Build From Scratch",
            "Use this master prompt to have Codex / Claude build an entire authoritative engineering baseline from scratch with all 10 stages.",
            MASTER_CODEX_PROMPT,
            self.is_dark,
        ))

        c_layout.addWidget(PromptCard(
            "Stage 2: Deterministic Sizing Calculations Prompt",
            "Prompt Codex to calculate Dowell AC winding loss, Steinmetz core loss, and semiconductor dissipation.",
            CALCULATIONS_PROMPT,
            self.is_dark,
        ))

        c_layout.addWidget(PromptCard(
            "Stage 3 & 4: SPICE Circuit & LTspice Transient Simulation Prompt",
            "Prompt Codex to synthesize the flyback circuit netlist and execute headless LTspice transient analysis.",
            SIMULATION_PROMPT,
            self.is_dark,
        ))

        c_layout.addWidget(PromptCard(
            "Stage 6-8: KiCad 10 Schematic, PCB Routing & DRC Prompt",
            "Prompt Codex to generate schematic, PCB layout with 5.0 mm isolation milling slot, and run native ERC/DRC.",
            KICAD_PROMPT,
            self.is_dark,
        ))

        c_layout.addWidget(PromptCard(
            "Stage 9: FreeCAD 3D Bobbin Solid Model Prompt",
            "Prompt Codex to invoke FreeCAD headlessly and generate the verified ISO 10303 STEP solid model.",
            FREECAD_PROMPT,
            self.is_dark,
        ))

        c_layout.addWidget(PromptCard(
            "Stage 10: Bill of Materials & Component Derating Prompt",
            "Prompt Codex to select qualified commercial components and compile structured bom.json and bom.csv.",
            BOM_PROMPT,
            self.is_dark,
        ))

        scroll.setWidget(content)
        layout.addWidget(scroll)

    def _init_connect_tab(self, parent_widget: QWidget):
        layout = QVBoxLayout(parent_widget)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        title = QLabel("Connecting AI Engineering Agents (Codex & Claude Code) via MCP")
        title.setStyleSheet("font-size: 14px; font-weight: 700; color: #89b4fa;")
        layout.addWidget(title)

        desc = QLabel(
            "Mendex Engineering Studio provides a standard Model Context Protocol (MCP) server that exposes 20+ deterministic engineering tools.\n"
            "This enables Codex, Claude Code, and Antigravity to create projects, run simulations, execute CAD checks, and synthesize designs through the same core service."
        )
        desc.setStyleSheet("color: #cdd6f4; font-size: 11px; line-height: 1.5;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        txt_mcp = QTextEdit()
        txt_mcp.setReadOnly(True)
        txt_mcp.setFont(QFont("Consolas", 10))
        mcp_instructions = """1. CONNECT FROM OPENAI CODEX / VS CODE:
Add to your .vscode/settings.json or mcp.json:
{
  "mcpServers": {
    "mendex-engineering": {
      "command": "${workspaceFolder}/.venv/Scripts/python.exe",
      "args": ["-m", "mendex_core.mcp", "--root", "${workspaceFolder}"]
    }
  }
}

2. CONNECT FROM ANTHROPIC CLAUDE CODE CLI:
Run the following in PowerShell:
claude mcp add mendex-engineering -- python -m mendex_core.mcp

3. MENDEX CORE CLI COMMANDS (Agent-Independent):
- List projects:             python -m mendex_core.cli projects
- Create project:            python -m mendex_core.cli create-project --code SV-1000 --name "High Voltage Converter"
- Run LTspice simulation:    python -m mendex_core.cli run-simulation --project <ID> --tool ltspice
- Run KiCad DRC check:       python -m mendex_core.cli run-simulation --project <ID> --tool kicad
- Generate Dossier Report:   python -m mendex_core.cli report generate <REVISION_ID>"""
        txt_mcp.setPlainText(mcp_instructions)
        txt_mcp.setStyleSheet("background: #11111b; color: #a6e3a1; border: 1px solid #313244; border-radius: 6px; padding: 10px;")
        layout.addWidget(txt_mcp, 1)

    def _init_review_tab(self, parent_widget: QWidget):
        layout = QVBoxLayout(parent_widget)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        title = QLabel("How to Review and Formally Sign Off Engineering Stages")
        title.setStyleSheet("font-size: 14px; font-weight: 700; color: #89b4fa;")
        layout.addWidget(title)

        txt_review = QTextEdit()
        txt_review.setReadOnly(True)
        txt_review.setFont(QFont("Segoe UI", 10))
        review_guide = """STEP-BY-STEP REVIEW PROCESS:

1. SELECT STAGE TO REVIEW:
   - On the '12-Stage Project Lifecycle Overview', click any stage card (e.g. Card #2 'Electrical Architecture & Sizing' or Card #4 'Electrical Simulation').
   - Tab 0 ('✍️ Review & Approvals') will immediately update with that stage's details, required evidence, actual evidence on disk, and recorded blockers.

2. INSPECT TECHNICAL RESULTS:
   - Click '🔍 Inspect Technical Data Tab' to view the full calculations, simulation waveforms, PCB layout, or 3D bobbin.
   - On the '🔬 Calculations' tab, you can view the exact turns ratio, Dowell winding factor, and semiconductor loss breakdown.
   - On the '⚡ Simulations' tab, you can view the live LTspice waveform in the built-in waveform viewer.
   - On the '📐 KiCad PCB' tab, you can inspect the KiCad ERC and DRC violation counts (0 violations = PASSED).

3. RECORD FORMAL ENGINEERING GATE SIGN-OFF:
   - In Tab 0 on the right panel ('Formal Engineering Gate Sign-Off'):
     a) Reviewer Identity: Enter your name (e.g. 'sagar jamage').
     b) Gate Decision: Select PASS or FAIL.
     c) Review Notes: Add verification justification (or keep pre-filled technical notes).
     d) Click '✅ Record Stage Sign-Off'.
   - The stage card status badge immediately turns GREEN ('PASSED').

4. QUICK SIGN-OFF ON TECHNICAL TABS:
   - While on the '🔬 Calculations' tab, you can also sign off Stage #2 directly using the quick sign-off bar at the top!
   - Similarly, quick buttons exist on '⚡ Simulations', '📐 KiCad PCB', '📋 BOM', and '🧊 3D Mechanical'.

5. WHAT 'NOT_EVALUATED' MEANS:
   - Mendex Studio enforces strict scientific truthfulness. If physical hardware measurements (e.g. Hi-Pot breakdown, thermal chamber testing) have not been physically executed, they remain NOT_EVALUATED.
   - Studio NEVER fabricates test results or approvals."""
        txt_review.setPlainText(review_guide)
        txt_review.setStyleSheet("background: #11111b; color: #cdd6f4; border: 1px solid #313244; border-radius: 6px; padding: 12px; line-height: 1.5;")
        layout.addWidget(txt_review, 1)

    def _init_playbook_tab(self, parent_widget: QWidget):
        layout = QVBoxLayout(parent_widget)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        c_widget = QWidget()
        c_layout = QVBoxLayout(c_widget)
        c_layout.setSpacing(14)

        sections = [
            ("⚡ 1. When and How to Use LTspice",
             "• WHEN TO USE: In Stage 4 (Electrical Simulation) after circuit synthesis.\n"
             "• IN STUDIO VIEW: Click the '⚡ Simulations' tab. The bottom half contains an interactive Waveform Viewer showing the 1000 V transient output waveform.\n"
             "• WHEN TO LAUNCH NATIVE LTSPICE: Click '📈 Open Raw Waveform in LTspice'. Studio launches LTspice directly with 'flyback_circuit.raw'.\n"
             "• WHAT TO INSPECT IN LTSPICE:\n"
             "  1. Drain Voltage V(drain): Check that peak switch spike does not exceed 1000 V (safe for 1200 V SiC MOSFET).\n"
             "  2. Output Voltage V(out): Verify that the output reaches 1000 V regulated DC.\n"
             "  3. Ripple: Measure peak-to-peak ripple at steady state (< 2% target).\n"
             "• WHEN TO RE-RUN SIMULATION: If you modified circuit components, duty cycle, or frequencies, click '⚡ Open Simulation Lab' or ask Codex to re-simulate.",
             "#89b4fa"),

            ("📐 2. When and How to Use KiCad 10 (Schematic & PCB)",
             "• WHEN TO USE: In Stages 6, 7 & 8 after electrical operating points are proven.\n"
             "• IN STUDIO VIEW: Click the '📐 KiCad PCB' tab to view DRC/ERC verification reports and manufacturing artifacts.\n"
             "• WHEN TO LAUNCH KICAD SCHEMATIC: Click '🚀 Open Schematic in KiCad'. Inspect symbols, net connections, and component values.\n"
             "• WHEN TO LAUNCH KICAD PCB LAYOUT: Click '🚀 Open PCB in KiCad'. Studio launches KiCad PCB Editor loading 'sv-1000.kicad_pcb'.\n"
             "• WHAT TO INSPECT IN KICAD PCB:\n"
             "  1. High-Voltage Isolation Slot: Crucial! Inspect the 5.0 mm wide isolation cut-out routed on the 'Edge.Cuts' layer separating primary (24V) and secondary (1000V) domains.\n"
             "  2. Track Widths: 0.8 mm power traces on primary pulsed path; 0.35 mm on high-voltage secondary.\n"
             "  3. Creepage & Clearance: Ensure clearance complies with IEC-61010-1 (3000 V RMS).\n"
             "• HOW TO RUN CHECKS: Click '⚡ Run KiCad ERC' and '🛡️ Run KiCad DRC' in Studio. Both should report 0 violations.",
             "#a6e3a1"),

            ("🧊 3. When and How to Use FreeCAD (3D Mechanical Bobbin)",
             "• WHEN TO USE: In Stage 9 (Thermal & Mechanical Evaluation).\n"
             "• IN STUDIO VIEW: Click the '🧊 3D Mechanical' tab to view enclosure parameters and bobbin dimensions.\n"
             "• WHEN TO LAUNCH FREECAD: Click '📐 Open 3D STEP Model in CAD Viewer / FreeCAD'.\n"
             "• WHAT TO INSPECT IN FREECAD:\n"
             "  1. Bobbin Barrier: Inspect the 5.0 mm raised physical barrier separating the primary and secondary winding bays.\n"
             "  2. Core Fitment: Verify center core post diameter matches E22/6/16 ferrite core dimensions.\n"
             "  3. Pin Retention: Check clearance for through-hole transformer termination pins.",
             "#cba6f7"),

            ("🔬 4. When and How to Review Mathematical Sizing",
             "• WHEN TO USE: In Stage 2 right after project creation.\n"
             "• IN STUDIO VIEW: Click the '🔬 Calculations' tab.\n"
             "• WHAT TO INSPECT:\n"
             "  1. Turns Ratio: 5 primary turns, 306 secondary turns (61.2:1 ratio).\n"
             "  2. Dowell AC Loss: Fr = 3.78 (effective Rac = 0.170 ohm at 100 kHz).\n"
             "  3. Core Dissipation: Steinmetz loss of 1.16 W in TDK N87 ferrite.\n"
             "  4. MOSFET Dissipation: 5.63 W total dissipation in Wolfspeed C2M0080120D.\n"
             "• HOW TO SIGN OFF: Use the Quick Sign-Off bar right above the equations: Reviewer: 'sagar jamage', Decision: 'PASS', click '✅ Sign-Off Stage #2'.",
             "#f9e2af"),

            ("✍️ 5. Step-by-Step Formal Review & Approval (Clearing Blockers)",
             "• HOW TO CLEAR BLOCKERS & REACH 'PROTOTYPE READY':\n"
             "  1. Click Tab 0 ('✍️ Review & Approvals') — it is always the first tab.\n"
             "  2. Click any pending stage card above (e.g. Card #2, Card #4, Card #8, Card #10).\n"
             "  3. The left panel shows the required evidence vs actual evidence files on disk.\n"
             "  4. The right panel displays the 'Formal Engineering Gate Sign-Off' form:\n"
             "     - Reviewer Identity: 'sagar jamage'\n"
             "     - Gate Decision: 'PASS'\n"
             "     - Review Notes: Pre-filled technical justification\n"
             "     - Click '✅ Record Stage Sign-Off'.\n"
             "  5. As each stage is approved, its card turns GREEN ('PASSED').\n"
             "  6. When all mandatory stages are passed, the header badge updates from 'PROTOTYPE BLOCKED' to 'PROTOTYPE READY'!",
             "#a6e3a1"),

            ("🔬 6. When and How to Use SwitchLossDB (Research Benchmark Catalog)",
             "• WHAT IS SWITCHLOSSDB: An open-source research dataset (CC-BY-4.0, IEEE PELS inventory) containing laboratory-measured switching energies (Eon, Eoff) and on-state resistance (Rds(on)) for SiC, GaN, and Silicon power semiconductors under verified test conditions (Vtest, Itest, Tj).\n"
             "• PRODUCT DEPENDENCY — WHY & WHEN TO USE IT:\n"
             "  1. Custom / Vendor-Specified Hardware: If your product is built around a specific commercial part with an official manufacturer datasheet (like SV-1000's Wolfspeed C2M0080120D 1200V SiC MOSFET), you use the manufacturer's exact switching curves in sizing calculations.\n"
             "  2. Topology Exploration & Device Selection: When evaluating candidate switches (e.g. comparing OnSemi NVHL080N120SC1 vs Cree C3M0065090D vs GaN Systems GS66508T), SwitchLossDB provides independent empirical loss data without relying solely on marketing datasheets.\n"
             "• IN STUDIO VIEW: Go to 'Component Library' -> '🔬 SwitchLossDB Research Catalog' (or click '🔬 Browse SwitchLossDB Research Catalog' directly from the Calculations tab).\n"
             "• HOW TO USE IN DESIGN:\n"
             "  1. Filter by technology (SiC, GaN, MOSFET) or rated voltage (>= 900V, >= 1200V).\n"
             "  2. Select any transistor to inspect its dynamic energy parameters (Eon, Eoff) and conduction resistance.\n"
             "  3. Use the built-in Loss Estimator to calculate conduction loss (P_cond) and switching loss (P_sw) for your operating current and frequency.\n"
             "  4. Click '📋 Copy Sizing JSON Block' to paste the verified parameters directly into your project's sizing analysis!",
             "#f9e2af")
        ]

        for title, body, color in sections:
            box = QFrame()
            box.setStyleSheet("background: #181825; border: 1px solid #313244; border-radius: 8px; padding: 12px;")
            b_layout = QVBoxLayout(box)
            b_layout.setSpacing(6)

            t_lbl = QLabel(title)
            t_lbl.setStyleSheet(f"font-weight: 700; font-size: 13px; color: {color};")
            b_layout.addWidget(t_lbl)

            body_txt = QTextEdit()
            body_txt.setReadOnly(True)
            body_txt.setFont(QFont("Segoe UI", 10))
            body_txt.setPlainText(body.replace("\\n", "\n"))
            body_txt.setStyleSheet("background: #11111b; color: #cdd6f4; border: 1px solid #272838; border-radius: 4px; padding: 8px;")
            body_txt.setMinimumHeight(130)
            b_layout.addWidget(body_txt)

            c_layout.addWidget(box)

        scroll.setWidget(c_widget)
        layout.addWidget(scroll)
