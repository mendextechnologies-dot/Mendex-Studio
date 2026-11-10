"""Notification Center and System Activity Log Dialog."""
from __future__ import annotations

from datetime import datetime
from typing import List
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QFrame, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QVBoxLayout, QWidget,
)


class NotificationRecord:
    def __init__(self, title: str, message: str, level: str = "INFO", timestamp: datetime = None):
        self.title = title
        self.message = message
        self.level = level  # INFO, SUCCESS, WARNING, ERROR
        self.timestamp = timestamp or datetime.now()


class NotificationCenterDialog(QDialog):
    """Notification Center dialog displaying system alerts, simulation completions, and gate updates."""

    LEVEL_COLORS = {
        "INFO": ("#1e3a5f", "#89b4fa"),
        "SUCCESS": ("#1b4332", "#a6e3a1"),
        "WARNING": ("#45381f", "#f9e2af"),
        "ERROR": ("#4a1525", "#f38ba8"),
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Notification Center & Activity History")
        self.resize(550, 400)
        self.notifications: List[NotificationRecord] = []
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        header_row = QHBoxLayout()
        title = QLabel("🔔 Notification Center")
        title.setStyleSheet("font-size: 15px; font-weight: 700; color: #cdd6f4;")
        header_row.addWidget(title)
        header_row.addStretch()

        btn_clear = QPushButton("Clear All")
        btn_clear.clicked.connect(self.clear_notifications)
        header_row.addWidget(btn_clear)
        layout.addLayout(header_row)

        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet(
            "QListWidget { background: #181825; border: 1px solid #313244; border-radius: 6px; } "
            "QListWidget::item { padding: 8px; border-bottom: 1px solid #272838; }"
        )
        layout.addWidget(self.list_widget)

    def add_notification(self, title: str, message: str, level: str = "INFO"):
        record = NotificationRecord(title, message, level)
        self.notifications.insert(0, record)
        self._refresh_list()

    def _refresh_list(self):
        self.list_widget.clear()
        for rec in self.notifications:
            bg, fg = self.LEVEL_COLORS.get(rec.level, ("#313244", "#cdd6f4"))
            time_str = rec.timestamp.strftime("%H:%M:%S")
            item_text = f"[{rec.level}] {rec.title} ({time_str})\n{rec.message}"
            item = QListWidgetItem(item_text)
            self.list_widget.addItem(item)

    def clear_notifications(self):
        self.notifications.clear()
        self.list_widget.clear()
