"""Mendex Engineering Studio Enterprise Design System Stylesheet."""

DARK_THEME_QSS = """
QMainWindow, QDialog {
    background-color: #181825;
    color: #cdd6f4;
    font-family: 'Segoe UI', system-ui, sans-serif;
    font-size: 12px;
}

QWidget {
    color: #cdd6f4;
    font-family: 'Segoe UI', system-ui, sans-serif;
    font-size: 12px;
}

/* Sidebar Navigation */
QListWidget#nav_sidebar {
    background-color: #11111b;
    border: none;
    border-right: 1px solid #313244;
    font-size: 12px;
    font-weight: 500;
    padding: 8px 4px;
}

QListWidget#nav_sidebar::item {
    height: 38px;
    border-radius: 6px;
    padding-left: 12px;
    margin: 2px 6px;
    color: #a6adc8;
}

QListWidget#nav_sidebar::item:hover {
    background-color: #1e1e2e;
    color: #cdd6f4;
}

QListWidget#nav_sidebar::item:selected {
    background-color: #313244;
    color: #89b4fa;
    font-weight: 600;
    border-left: 3px solid #89b4fa;
}

/* Header & Toolbars */
QFrame#top_header {
    background-color: #11111b;
    border-bottom: 1px solid #313244;
    padding: 6px 16px;
}

/* Cards & Surfaces */
QFrame.card_surface {
    background-color: #1e1e2e;
    border: 1px solid #313244;
    border-radius: 8px;
    padding: 12px;
}

QFrame.card_surface:hover {
    border-color: #45475a;
}

/* Buttons */
QPushButton {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 5px;
    padding: 6px 14px;
    font-weight: 500;
    font-size: 12px;
}

QPushButton:hover {
    background-color: #45475a;
    border-color: #89b4fa;
    color: #ffffff;
}

QPushButton:pressed {
    background-color: #585b70;
}

QPushButton.primary_btn {
    background-color: #1e66f5;
    border: 1px solid #7287fd;
    color: #ffffff;
    font-weight: 600;
}

QPushButton.primary_btn:hover {
    background-color: #04a5e5;
}

/* Inputs & Form Fields */
QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    background-color: #181825;
    color: #cdd6f4;
    border: 1px solid #313244;
    border-radius: 5px;
    padding: 6px 10px;
}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus {
    border: 1px solid #89b4fa;
}

/* Tables & Lists */
QTableWidget, QTreeWidget {
    background-color: #181825;
    border: 1px solid #313244;
    border-radius: 6px;
    gridline-color: #272838;
}

QHeaderView::section {
    background-color: #11111b;
    color: #a6adc8;
    padding: 6px;
    border: none;
    border-bottom: 1px solid #313244;
    font-weight: 600;
    font-size: 11px;
}

/* Tab Bar */
QTabWidget::pane {
    border: 1px solid #313244;
    background-color: #1e1e2e;
    border-radius: 6px;
}

QTabBar::tab {
    background-color: #11111b;
    color: #a6adc8;
    padding: 8px 16px;
    border: 1px solid #313244;
    border-bottom: none;
    margin-right: 2px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}

QTabBar::tab:selected {
    background-color: #1e1e2e;
    color: #89b4fa;
    font-weight: 600;
}

/* Badges & Labels */
QLabel.metric_value {
    font-size: 24px;
    font-weight: 700;
    color: #89b4fa;
}

QLabel.metric_label {
    font-size: 11px;
    color: #a6adc8;
    text-transform: uppercase;
    font-weight: 600;
}

QLabel.badge_ready {
    background-color: #1c3b2b;
    color: #a6e3a1;
    border: 1px solid #2d5a3f;
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 10px;
    font-weight: 600;
}

QScrollBar:vertical {
    border: none;
    background: #11111b;
    width: 10px;
    border-radius: 5px;
}

QScrollBar::handle:vertical {
    background: #45475a;
    border-radius: 5px;
    min-height: 25px;
}

QScrollBar::handle:vertical:hover {
    background: #585b70;
}

QScrollBar:horizontal {
    border: none;
    background: #11111b;
    height: 10px;
    border-radius: 5px;
}

QScrollBar::handle:horizontal {
    background: #45475a;
    border-radius: 5px;
    min-width: 25px;
}

QScrollBar::handle:horizontal:hover {
    background: #585b70;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal,
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    border: none;
    background: none;
    width: 0px;
    height: 0px;
}
"""

LIGHT_THEME_QSS = """
QMainWindow, QDialog, QWidget {
    background-color: #f8f9fa;
    color: #212529;
    font-family: 'Segoe UI', system-ui, sans-serif;
    font-size: 12px;
}

QListWidget#nav_sidebar {
    background-color: #ffffff;
    border-right: 1px solid #dee2e6;
    padding: 8px 4px;
}

QListWidget#nav_sidebar::item {
    height: 38px;
    border-radius: 6px;
    padding-left: 12px;
    margin: 2px 6px;
    color: #495057;
}

QListWidget#nav_sidebar::item:selected {
    background-color: #e9ecef;
    color: #0066cc;
    font-weight: 600;
    border-left: 3px solid #0066cc;
}

QFrame#top_header {
    background-color: #ffffff;
    border-bottom: 1px solid #dee2e6;
    padding: 6px 16px;
}

QPushButton {
    background-color: #ffffff;
    color: #212529;
    border: 1px solid #ced4da;
    border-radius: 5px;
    padding: 6px 14px;
}

QPushButton:hover {
    background-color: #e9ecef;
    border-color: #0066cc;
}

QLineEdit, QTextEdit, QPlainTextEdit, QComboBox {
    background-color: #ffffff;
    color: #212529;
    border: 1px solid #ced4da;
    border-radius: 5px;
    padding: 6px 10px;
}
"""
