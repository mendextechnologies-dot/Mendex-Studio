"""Dedicated modal dialog and widget for configuring AI providers and API keys."""
from __future__ import annotations

import json
from pathlib import Path
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QCheckBox, QMessageBox, QGroupBox, QWidget
)
from PySide6.QtCore import Qt

from mendex_core.ai.config import load_ai_config, save_ai_config, AIProviderConfig


class AIKeySetupWidget(QWidget):
    """Embeddable or standalone widget for setting up AI API keys and models."""

    def __init__(self, data_root: Path, parent=None):
        super().__init__(parent)
        self.data_root = data_root

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        box = QGroupBox("AI Copilot & Cloud Provider Configuration")
        box.setStyleSheet("font-size: 13px; font-weight: 600;")
        form = QFormLayout(box)
        form.setSpacing(12)

        # Provider Selector
        self.combo_provider = QComboBox()
        self.combo_provider.addItems([
            "Offline Deterministic Engine (Zero Cost / Local)",
            "Google Gemini API (Cloud)",
            "OpenAI API (Cloud)",
        ])
        self.combo_provider.currentIndexChanged.connect(self._on_provider_changed)
        form.addRow("AI Provider:", self.combo_provider)

        # API Key Input
        self.txt_api_key = QLineEdit()
        self.txt_api_key.setEchoMode(QLineEdit.Password)
        self.txt_api_key.setPlaceholderText("Enter API Key (e.g. AIzaSy... for Gemini, sk-... for OpenAI)")

        key_row = QHBoxLayout()
        key_row.addWidget(self.txt_api_key)
        self.btn_toggle = QPushButton("👁️ Show")
        self.btn_toggle.setFixedWidth(75)
        self.btn_toggle.clicked.connect(self._toggle_key)
        key_row.addWidget(self.btn_toggle)
        form.addRow("API Key:", key_row)

        # Model Name
        self.txt_model = QLineEdit()
        self.txt_model.setPlaceholderText("e.g. gemini-2.0-flash, gemini-1.5-pro, gpt-4o")
        form.addRow("Model Name:", self.txt_model)

        # Cloud Opt-In
        self.chk_opt_in = QCheckBox("Explicit Cloud Opt-In (allow technical requirements to be processed by cloud provider)")
        form.addRow("", self.chk_opt_in)

        # Save Button
        self.btn_save = QPushButton("💾 Save API Key & Provider Settings")
        self.btn_save.setStyleSheet(
            "background-color: #89b4fa; color: #11111b; font-weight: 700; font-size: 13px; padding: 8px 16px; border-radius: 4px;"
        )
        self.btn_save.clicked.connect(self.save_settings)
        form.addRow("", self.btn_save)

        # Status Label
        self.lbl_status = QLabel("● Active Backend: Local Deterministic Engine (Offline)")
        self.lbl_status.setStyleSheet("color: #a6e3a1; font-weight: 600; font-size: 12px; margin-top: 6px;")
        form.addRow("Active Status:", self.lbl_status)

        layout.addWidget(box)
        layout.addStretch()

        self.load_settings()

    def _toggle_key(self):
        if self.txt_api_key.echoMode() == QLineEdit.Password:
            self.txt_api_key.setEchoMode(QLineEdit.Normal)
            self.btn_toggle.setText("🔒 Hide")
        else:
            self.txt_api_key.setEchoMode(QLineEdit.Password)
            self.btn_toggle.setText("👁️ Show")

    def _on_provider_changed(self, idx: int):
        if idx == 1:  # Gemini
            if not self.txt_model.text() or self.txt_model.text() == "gpt-4o":
                self.txt_model.setText("gemini-2.0-flash")
            self.txt_api_key.setPlaceholderText("Enter Google Gemini API Key (AIzaSy...)")
        elif idx == 2:  # OpenAI
            if not self.txt_model.text() or self.txt_model.text() == "gemini-2.0-flash":
                self.txt_model.setText("gpt-4o")
            self.txt_api_key.setPlaceholderText("Enter OpenAI API Key (sk-...)")
        else:
            self.txt_model.setText("local_engineering_rules")
            self.txt_api_key.setPlaceholderText("No API Key required for offline engine")

    def load_settings(self):
        cfg = load_ai_config(self.data_root)
        if cfg.provider == "gemini":
            self.combo_provider.setCurrentIndex(1)
        elif cfg.provider == "openai":
            self.combo_provider.setCurrentIndex(2)
        else:
            self.combo_provider.setCurrentIndex(0)

        self.txt_api_key.setText(cfg.api_key)
        self.txt_model.setText(cfg.model)
        self.chk_opt_in.setChecked(cfg.cloud_opt_in)

        if cfg.api_key and cfg.provider in ("gemini", "openai"):
            masked = cfg.api_key[:6] + "..." + cfg.api_key[-4:] if len(cfg.api_key) > 10 else "***"
            self.lbl_status.setText(f"● Connected to {cfg.provider.upper()} ({cfg.model}) [{masked}]")
            self.lbl_status.setStyleSheet("color: #89b4fa; font-weight: 600;")
        else:
            self.lbl_status.setText("● Active Backend: Local Deterministic Engine (Offline / Zero Cost)")
            self.lbl_status.setStyleSheet("color: #a6e3a1; font-weight: 600;")

    def save_settings(self):
        idx = self.combo_provider.currentIndex()
        prov = "gemini" if idx == 1 else "openai" if idx == 2 else "offline"
        api_k = self.txt_api_key.text().strip()

        if prov in ("gemini", "openai") and not api_k:
            QMessageBox.warning(self, "API Key Required", f"Please enter a valid API key for {prov.upper()}.")
            return

        cfg = AIProviderConfig(
            provider=prov,
            model=self.txt_model.text().strip() or ("gemini-2.0-flash" if prov == "gemini" else "gpt-4o" if prov == "openai" else "local_engineering_rules"),
            api_key=api_k,
            cloud_opt_in=self.chk_opt_in.isChecked(),
        )
        save_ai_config(cfg, self.data_root)
        self.load_settings()
        QMessageBox.information(
            self,
            "AI Configuration Saved",
            f"Successfully saved {prov.upper()} configuration to .mendex/ai_config.json.\n\n"
            f"• Provider: {prov.upper()}\n"
            f"• Model: {cfg.model}\n"
            f"• Cloud Opt-In: {'Enabled' if cfg.cloud_opt_in else 'Disabled'}",
        )


class AIKeySetupDialog(QDialog):
    """Modal popup dialog for configuring AI keys from any panel or toolbar."""

    def __init__(self, data_root: Path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AI Copilot & API Key Configuration")
        self.resize(580, 360)
        self.setStyleSheet("background-color: #1e1e2e; color: #cdd6f4;")

        layout = QVBoxLayout(self)
        self.widget = AIKeySetupWidget(data_root, self)
        layout.addWidget(self.widget)

        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close, alignment=Qt.AlignRight)
