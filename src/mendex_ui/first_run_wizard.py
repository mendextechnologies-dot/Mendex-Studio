"""First-run Configuration Wizard for Mendex Engineering Studio v2.0."""
from __future__ import annotations

import os
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QCheckBox, QDialog, QFrame, QGridLayout, QHBoxLayout, QLabel,
    QLineEdit, QMessageBox, QPushButton, QStackedWidget, QVBoxLayout, QWidget,
)

from .resources import SHIELD_TRANSPARENT_PATH


class FirstRunWizardDialog(QDialog):
    """Initial onboarding wizard configuring tools, default workspace, and preferences."""

    def __init__(self, service, parent=None):
        super().__init__(parent)
        self.service = service
        self.setWindowTitle("Mendex Engineering Studio v2.0 — Setup Wizard")
        self.resize(700, 480)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header
        header = QFrame()
        header.setStyleSheet("background: #1e1e2e; border: 1px solid #313244; border-radius: 8px; padding: 12px;")
        h_layout = QHBoxLayout(header)
        if SHIELD_TRANSPARENT_PATH.exists():
            lbl_logo = QLabel()
            lbl_logo.setPixmap(QPixmap(str(SHIELD_TRANSPARENT_PATH)).scaled(40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            h_layout.addWidget(lbl_logo)

        v_box = QVBoxLayout()
        t1 = QLabel("MENDEX ENGINEERING STUDIO v2.0")
        t1.setStyleSheet("font-size: 15px; font-weight: 800; color: #89b4fa; letter-spacing: 0.5px;")
        t2 = QLabel("Enterprise Engineering Platform Setup & Tool Discovery")
        t2.setStyleSheet("font-size: 11px; color: #a6adc8;")
        v_box.addWidget(t1)
        v_box.addWidget(t2)
        h_layout.addLayout(v_box)
        h_layout.addStretch()
        layout.addWidget(header)

        # Body Stack
        self.body_frame = QFrame()
        self.body_frame.setStyleSheet("background: #181825; border: 1px solid #313244; border-radius: 8px; padding: 16px;")
        b_layout = QVBoxLayout(self.body_frame)

        lbl_intro = QLabel(
            "Welcome to Mendex Engineering Studio v2.0.<br><br>"
            "This setup wizard will verify your local CAD/CAE tools, configure your default engineering workspace, "
            "and establish traceable verification parameters."
        )
        lbl_intro.setStyleSheet("color: #cdd6f4; font-size: 12px; line-height: 1.4;")
        lbl_intro.setWordWrap(True)
        b_layout.addWidget(lbl_intro)

        # Tool detection summary grid
        tools_group = QFrame()
        tools_group.setStyleSheet("background: #11111b; border: 1px solid #272838; border-radius: 6px; padding: 10px;")
        grid = QGridLayout(tools_group)

        tools_to_check = [
            ("LTspice 26.1", "ltspice", "C:\\Program Files\\ADI\\LTspice\\LTspice.exe"),
            ("KiCad 10.0", "kicad", "C:\\Program Files\\KiCad\\10.0\\bin\\kicad-cli.exe"),
            ("FreeCAD 1.1", "freecad", "C:\\Program Files\\FreeCAD 1.1\\bin\\freecad.exe"),
            ("FEMM 4.2", "femm", "C:\\femm42\\bin\\femm.exe"),
            ("OpenModelica", "openmodelica", "C:\\Program Files\\OpenModelica1.26.3-64bit\\bin\\OMEdit.exe"),
            ("Python 3.13", "python", "Available (Running Studio)"),
        ]

        grid.addWidget(QLabel("<b>Engineering Tool</b>"), 0, 0)
        grid.addWidget(QLabel("<b>Detected Status</b>"), 0, 1)

        for row, (tname, tid, default_path) in enumerate(tools_to_check, start=1):
            lbl_name = QLabel(tname)
            lbl_name.setStyleSheet("color: #cdd6f4; font-weight: 500;")
            grid.addWidget(lbl_name, row, 0)

            installed = Path(default_path).exists() if default_path.startswith("C:") else True
            st_text = "READY" if installed else "NOT INSTALLED"
            st_color = "#a6e3a1" if installed else "#f38ba8"
            st_bg = "#1b4332" if installed else "#4a1525"

            lbl_st = QLabel(f" {st_text} ")
            lbl_st.setStyleSheet(f"background: {st_bg}; color: {st_color}; font-weight: 700; border-radius: 4px; padding: 2px 6px;")
            grid.addWidget(lbl_st, row, 1)

        b_layout.addWidget(tools_group)
        b_layout.addStretch()
        layout.addWidget(self.body_frame)

        # Footer Buttons
        footer = QHBoxLayout()
        footer.addStretch()

        btn_finish = QPushButton("Complete Setup & Open Studio")
        btn_finish.setStyleSheet("background: #1e66f5; color: #ffffff; font-weight: 700; padding: 8px 16px; border-radius: 6px;")
        btn_finish.clicked.connect(self.accept)
        footer.addWidget(btn_finish)

        layout.addLayout(footer)
