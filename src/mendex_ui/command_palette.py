"""Global Command Palette and Action Dispatcher for Mendex Engineering Studio."""
from __future__ import annotations

from typing import Callable, List, Tuple
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QDialog, QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QVBoxLayout, QWidget,
)


class CommandItem:
    def __init__(self, title: str, category: str, shortcut: str, callback: Callable[[], None], icon: str = "⚡"):
        self.title = title
        self.category = category
        self.shortcut = shortcut
        self.callback = callback
        self.icon = icon


class CommandPaletteDialog(QDialog):
    """Modern modal command palette (Ctrl+K / Ctrl+P) for keyboard-driven navigation and tool actions."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(650, 420)
        self.commands: List[CommandItem] = []
        self.filtered_commands: List[CommandItem] = []
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # Container Frame with rounded corners and drop shadow style
        container = QFrame()
        container.setStyleSheet(
            "QFrame { background-color: #1e1e2e; border: 1.5px solid #89b4fa; border-radius: 10px; }"
        )
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(12, 12, 12, 12)
        container_layout.setSpacing(10)

        # Search Bar
        search_row = QHBoxLayout()
        search_icon = QLabel("🔍")
        search_icon.setStyleSheet("font-size: 16px; color: #89b4fa;")
        search_row.addWidget(search_icon)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Type a command or search action (e.g., 'simulation', 'kicad', 'dossier', 'theme')...")
        self.search_input.setStyleSheet(
            "QLineEdit { background: #181825; color: #cdd6f4; font-size: 13px; font-weight: 500; "
            "border: 1px solid #313244; border-radius: 6px; padding: 8px 12px; }"
        )
        self.search_input.textChanged.connect(self._filter_commands)
        self.search_input.returnPressed.connect(self._execute_selected)
        search_row.addWidget(self.search_input)
        container_layout.addLayout(search_row)

        # Commands List
        self.command_list = QListWidget()
        self.command_list.setStyleSheet(
            "QListWidget { background: #181825; border: 1px solid #313244; border-radius: 6px; padding: 4px; } "
            "QListWidget::item { padding: 8px 10px; border-radius: 4px; color: #cdd6f4; font-size: 12px; } "
            "QListWidget::item:selected { background: #24273a; color: #89b4fa; font-weight: 600; border-left: 3px solid #89b4fa; } "
            "QListWidget::item:hover { background: #313244; }"
        )
        self.command_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        container_layout.addWidget(self.command_list)

        # Footer Hint
        footer_layout = QHBoxLayout()
        lbl_hint = QLabel("↑↓ Navigate   ↵ Execute   Esc Close")
        lbl_hint.setStyleSheet("color: #6c7086; font-size: 11px;")
        footer_layout.addWidget(lbl_hint)
        footer_layout.addStretch()
        container_layout.addLayout(footer_layout)

        main_layout.addWidget(container)

    def register_command(self, title: str, category: str, shortcut: str, callback: Callable[[], None], icon: str = "⚡"):
        self.commands.append(CommandItem(title, category, shortcut, callback, icon))

    def show_palette(self):
        self.search_input.clear()
        self._filter_commands("")
        self.search_input.setFocus()
        self.exec()

    def _filter_commands(self, text: str):
        query = text.lower().strip()
        self.command_list.clear()
        self.filtered_commands = []

        for cmd in self.commands:
            if not query or query in cmd.title.lower() or query in cmd.category.lower() or query in cmd.shortcut.lower():
                self.filtered_commands.append(cmd)
                display_text = f"{cmd.icon}  [{cmd.category.upper()}]  {cmd.title}"
                if cmd.shortcut:
                    display_text = f"{display_text:<60} {cmd.shortcut}"
                item = QListWidgetItem(display_text)
                self.command_list.addItem(item)

        if self.command_list.count() > 0:
            self.command_list.setCurrentRow(0)

    def _execute_selected(self):
        row = self.command_list.currentRow()
        if 0 <= row < len(self.filtered_commands):
            cmd = self.filtered_commands[row]
            self.accept()
            cmd.callback()

    def _on_item_double_clicked(self, item):
        self._execute_selected()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.reject()
        elif event.key() == Qt.Key_Down:
            curr = self.command_list.currentRow()
            if curr < self.command_list.count() - 1:
                self.command_list.setCurrentRow(curr + 1)
        elif event.key() == Qt.Key_Up:
            curr = self.command_list.currentRow()
            if curr > 0:
                self.command_list.setCurrentRow(curr - 1)
        else:
            super().keyPressEvent(event)
