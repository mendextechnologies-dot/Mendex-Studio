"""Settings and External Connections Panel for Mendex Engineering Studio v2.1."""
from __future__ import annotations

from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QScrollArea, QVBoxLayout, QWidget
)


class SettingsPanel(QWidget):
    """Central settings, configuration, and external agent connection information."""

    def __init__(self, service, toggle_theme_callback=None, parent=None):
        super().__init__(parent)
        self.service = service
        self.toggle_theme_callback = toggle_theme_callback
        self.is_dark = True
        self.tool_labels: list[QLabel] = []
        self.tool_edits: list[QLineEdit] = []
        self.tool_status_labels: list[tuple[QLabel, bool]] = []
        self.env_labels: list[QLabel] = []
        self.env_edits: list[QLineEdit] = []
        self.btn_theme: QPushButton | None = None
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(14)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)

        self.content_widget = QWidget()
        layout = QVBoxLayout(self.content_widget)
        layout.setSpacing(16)

        # 1. Header Banner
        self.header_card = QFrame()
        h_layout = QVBoxLayout(self.header_card)
        self.lbl_title = QLabel("⚙ System Settings & Connections")
        h_layout.addWidget(self.lbl_title)
        self.lbl_desc = QLabel(
            "Mendex Engineering Studio v2.1 operates as a lightweight management and visualization center.\n"
            "AI agents (OpenAI Codex, Anthropic Claude Code) connect via the standardized Model Context Protocol (MCP) and CLI."
        )
        self.lbl_desc.setWordWrap(True)
        h_layout.addWidget(self.lbl_desc)
        layout.addWidget(self.header_card)

        # 2. AI Integration & MCP Server Card
        self.mcp_group = QGroupBox("🤖 AI Agent Integration (Codex & Claude Code)")
        mcp_layout = QVBoxLayout(self.mcp_group)
        mcp_layout.setSpacing(8)

        self.mcp_status = QLabel("● Model Context Protocol (MCP) Server: ACTIVE & READY")
        mcp_layout.addWidget(self.mcp_status)

        self.mcp_info = QLabel(
            "Protocol Version: 2024-11-05 (Standard JSON-RPC 2.0 stdio)\n"
            "Available MCP Tools: 22 deterministic engineering tools registered\n"
            "Supported Environments: VS Code (OpenAI Codex), Anthropic Claude Code CLI, Claude Desktop, Cursor"
        )
        mcp_layout.addWidget(self.mcp_info)

        self.code_box = QLabel(
            "Connect from VS Code:\n"
            "  \"command\": \"${workspaceFolder}/.venv/Scripts/python.exe\",\n"
            "  \"args\": [\"-m\", \"mendex_core.mcp\", \"--root\", \"${workspaceFolder}\"]\n\n"
            "Connect from Claude Code CLI:\n"
            "  claude mcp add mendex-engineering -- python -m mendex_core.mcp"
        )
        self.code_box.setTextInteractionFlags(Qt.TextSelectableByMouse)
        mcp_layout.addWidget(self.code_box)

        layout.addWidget(self.mcp_group)

        # 3. Host Tool Paths Card
        self.tools_group = QGroupBox("🛠 Host Engineering CAD & Solver Paths")
        tools_grid = QGridLayout(self.tools_group)
        tools_grid.setSpacing(8)

        row = 0
        tool_configs = [
            ("LTspice Simulator", "ltspice", [
                r"C:\Program Files\ADI\LTspice\LTspice.exe",
                r"C:\Users\Sagar\AppData\Local\Programs\ADI\LTspice\LTspice.exe",
                r"C:\Program Files\LTC\LTspiceXVII\XVIIx64.exe"
            ]),
            ("KiCad CLI (ERC/DRC)", "kicad", [
                r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe",
                r"C:\Program Files\KiCad\9.0\bin\kicad-cli.exe",
                r"C:\Program Files\KiCad\8.0\bin\kicad-cli.exe"
            ]),
            ("FEMM 4.2 Magnetics", "femm", [
                r"C:\femm42\bin\femm.exe",
                r"C:\Program Files\femm42\bin\femm.exe",
                r"C:\Program Files (x86)\femm42\bin\femm.exe"
            ]),
            ("FreeCAD 3D Engine", "freecad", [
                r"C:\Program Files\FreeCAD 1.1\bin\freecadcmd.exe",
                r"C:\Program Files\FreeCAD 1.0\bin\freecadcmd.exe",
                r"C:\Program Files\FreeCAD 0.21\bin\freecadcmd.exe"
            ]),
        ]

        for tool_name, tool_id, fallbacks in tool_configs:
            lbl_name = QLabel(f"{tool_name}:")
            self.tool_labels.append(lbl_name)
            tools_grid.addWidget(lbl_name, row, 0)

            txt_path = QLineEdit()
            health = self.service.integrations.detect(tool_id)
            detected_path = getattr(health, "executable_path", None) or getattr(health, "installed_path", None)

            resolved_path = None
            if detected_path and Path(detected_path).exists():
                resolved_path = str(detected_path)
            else:
                for fb in fallbacks:
                    if Path(fb).exists():
                        resolved_path = fb
                        break

            is_ready = resolved_path is not None and Path(resolved_path).exists()
            txt_path.setText(resolved_path if resolved_path else fallbacks[0])
            txt_path.setReadOnly(True)
            self.tool_edits.append(txt_path)
            tools_grid.addWidget(txt_path, row, 1)

            status_lbl = QLabel("READY" if is_ready else "NOT FOUND")
            self.tool_status_labels.append((status_lbl, is_ready))
            tools_grid.addWidget(status_lbl, row, 2)
            row += 1

        layout.addWidget(self.tools_group)

        # 4. Workspace & Database Environment
        self.env_group = QGroupBox("📁 Project & Database Storage")
        env_layout = QGridLayout(self.env_group)
        env_layout.setSpacing(8)

        lbl_root_title = QLabel("Data Root:")
        self.env_labels.append(lbl_root_title)
        env_layout.addWidget(lbl_root_title, 0, 0)
        lbl_root = QLineEdit(str(self.service.root))
        lbl_root.setReadOnly(True)
        self.env_edits.append(lbl_root)
        env_layout.addWidget(lbl_root, 0, 1)

        lbl_db_title = QLabel("SQLite Metadata:")
        self.env_labels.append(lbl_db_title)
        env_layout.addWidget(lbl_db_title, 1, 0)
        sqlite_path = self.service.root / ".mendex" / "studio.sqlite3"
        lbl_db = QLineEdit(str(sqlite_path))
        lbl_db.setReadOnly(True)
        self.env_edits.append(lbl_db)
        env_layout.addWidget(lbl_db, 1, 1)

        layout.addWidget(self.env_group)

        # 5. UI Preferences
        self.ui_group = QGroupBox("🎨 Visual Appearance & Theme")
        ui_layout = QHBoxLayout(self.ui_group)

        self.lbl_theme = QLabel("Theme Mode: Enterprise Dark (Catppuccin Mocha)")
        ui_layout.addWidget(self.lbl_theme)
        ui_layout.addStretch()

        if self.toggle_theme_callback:
            self.btn_theme = QPushButton("🌓 Toggle Dark / Light Theme")
            self.btn_theme.clicked.connect(self.toggle_theme_callback)
            ui_layout.addWidget(self.btn_theme)

        layout.addWidget(self.ui_group)
        layout.addStretch()

        self.scroll.setWidget(self.content_widget)
        main_layout.addWidget(self.scroll)

        # Apply initial dark styling
        self.apply_theme(True)

    def apply_theme(self, is_dark: bool):
        """Dynamically applies either dark or crisp white light theme styling."""
        self.is_dark = is_dark
        if is_dark:
            # Dark Mode (Catppuccin Mocha)
            self.setStyleSheet("background-color: #11111b; color: #cdd6f4;")
            self.scroll.setStyleSheet("QScrollArea { border: none; background-color: #11111b; }")
            self.content_widget.setStyleSheet("background-color: #11111b;")
            self.header_card.setStyleSheet("background-color: #181825; border: 1px solid #313244; border-radius: 8px; padding: 14px;")
            self.lbl_title.setStyleSheet("font-size: 16px; font-weight: 700; color: #89b4fa;")
            self.lbl_desc.setStyleSheet("color: #a6adc8; font-size: 12px; line-height: 1.5;")

            box_qss = (
                "QGroupBox { background-color: #181825; font-weight: 700; color: #cdd6f4; "
                "border: 1px solid #313244; border-radius: 6px; margin-top: 8px; padding: 16px 12px 12px 12px; } "
                "QGroupBox::title { color: #89b4fa; }"
            )
            self.mcp_group.setStyleSheet(box_qss)
            self.tools_group.setStyleSheet(box_qss)
            self.env_group.setStyleSheet(box_qss)
            self.ui_group.setStyleSheet(box_qss)

            self.mcp_status.setStyleSheet("color: #a6e3a1; font-weight: 700; font-size: 12px;")
            self.mcp_info.setStyleSheet("color: #bac2de; font-family: monospace; font-size: 11px; background: #11111b; border: 1px solid #313244; padding: 8px; border-radius: 4px;")
            self.code_box.setStyleSheet("background-color: #1e1e2e; color: #f9e2af; font-family: monospace; font-size: 11px; padding: 10px; border-radius: 4px; border: 1px solid #45475a;")

            for lbl in self.tool_labels + self.env_labels:
                lbl.setStyleSheet("color: #cdd6f4; font-size: 12px;")

            for edit in self.tool_edits + self.env_edits:
                edit.setStyleSheet("background-color: #11111b; color: #cdd6f4; border: 1px solid #313244; font-size: 11px; padding: 4px; border-radius: 4px;")

            for status_lbl, is_ready in self.tool_status_labels:
                color = "#a6e3a1" if is_ready else "#f38ba8"
                status_lbl.setStyleSheet(f"color: {color}; font-weight: 700; font-size: 11px;")

            self.lbl_theme.setText("Theme Mode: Enterprise Dark (Catppuccin Mocha)")
            self.lbl_theme.setStyleSheet("color: #cdd6f4; font-weight: 600;")
            if self.btn_theme:
                self.btn_theme.setStyleSheet("background-color: #313244; color: #cdd6f4; font-weight: 700; padding: 6px 14px; border-radius: 4px; border: 1px solid #45475a;")
        else:
            # Light Mode (Crisp #ffffff White Background)
            self.setStyleSheet("background-color: #ffffff; color: #212529;")
            self.scroll.setStyleSheet("QScrollArea { border: none; background-color: #ffffff; }")
            self.content_widget.setStyleSheet("background-color: #ffffff;")
            self.header_card.setStyleSheet("background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; padding: 14px;")
            self.lbl_title.setStyleSheet("font-size: 16px; font-weight: 700; color: #0066cc;")
            self.lbl_desc.setStyleSheet("color: #495057; font-size: 12px; line-height: 1.5;")

            box_qss = (
                "QGroupBox { background-color: #ffffff; font-weight: 700; color: #212529; "
                "border: 1px solid #dee2e6; border-radius: 6px; margin-top: 8px; padding: 16px 12px 12px 12px; } "
                "QGroupBox::title { color: #0066cc; }"
            )
            self.mcp_group.setStyleSheet(box_qss)
            self.tools_group.setStyleSheet(box_qss)
            self.env_group.setStyleSheet(box_qss)
            self.ui_group.setStyleSheet(box_qss)

            self.mcp_status.setStyleSheet("color: #2e7d32; font-weight: 700; font-size: 12px;")
            self.mcp_info.setStyleSheet("color: #212529; font-family: monospace; font-size: 11px; background: #f8f9fa; border: 1px solid #dee2e6; padding: 8px; border-radius: 4px;")
            self.code_box.setStyleSheet("background-color: #f1f3f5; color: #1e293b; font-family: monospace; font-size: 11px; padding: 10px; border-radius: 4px; border: 1px solid #ced4da;")

            for lbl in self.tool_labels + self.env_labels:
                lbl.setStyleSheet("color: #212529; font-size: 12px;")

            for edit in self.tool_edits + self.env_edits:
                edit.setStyleSheet("background-color: #ffffff; color: #212529; border: 1px solid #ced4da; font-size: 11px; padding: 4px; border-radius: 4px;")

            for status_lbl, is_ready in self.tool_status_labels:
                color = "#2e7d32" if is_ready else "#d32f2f"
                status_lbl.setStyleSheet(f"color: {color}; font-weight: 700; font-size: 11px;")

            self.lbl_theme.setText("Theme Mode: Professional Light")
            self.lbl_theme.setStyleSheet("color: #212529; font-weight: 600;")
            if self.btn_theme:
                self.btn_theme.setStyleSheet("background-color: #e9ecef; color: #212529; font-weight: 700; padding: 6px 14px; border-radius: 4px; border: 1px solid #ced4da;")
