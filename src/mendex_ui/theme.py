"""Mendex Engineering Studio Enterprise Design System Stylesheet."""

DARK_THEME_QSS = """
QMainWindow, QDialog {
    background-color: #11111b;
    color: #cdd6f4;
    font-family: 'Segoe UI', system-ui, sans-serif;
    font-size: 12px;
}

QWidget {
    color: #cdd6f4;
    font-family: 'Segoe UI', system-ui, sans-serif;
    font-size: 12px;
}

QWidget#work_area {
    background-color: #11111b;
}

QWidget#sidebar_container {
    background-color: #11111b;
    border-right: 1px solid #313244;
}

/* Sidebar Navigation */
QListWidget#nav_sidebar {
    background-color: #11111b;
    border: none;
    border-right: 1px solid #313244;
    font-size: 13px;
    font-weight: 500;
    padding: 8px 4px;
}

QListWidget#nav_sidebar::item {
    height: 40px;
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

QListWidget#nav_sidebar QScrollBar:vertical {
    border: 1px solid #313244;
    background-color: #11111b;
    width: 12px;
    margin: 0px;
    border-radius: 4px;
}

QListWidget#nav_sidebar QScrollBar::handle:vertical {
    background-color: #585b70;
    border: 1px solid #45475a;
    border-radius: 4px;
    min-height: 25px;
    margin: 2px;
}

QListWidget#nav_sidebar QScrollBar::handle:vertical:hover {
    background-color: #89b4fa;
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
QTableWidget, QTreeWidget, QListWidget {
    background-color: #181825;
    color: #cdd6f4;
    border: 1px solid #313244;
    border-radius: 6px;
    gridline-color: #272838;
}

QListWidget::item {
    background-color: #1e1e2e;
    color: #cdd6f4;
    border-radius: 5px;
    padding: 6px 10px;
    margin: 2px 2px;
}

QListWidget::item:hover {
    background-color: #313244;
    color: #ffffff;
}

QListWidget::item:selected {
    background-color: #24273a;
    border-left: 3px solid #89b4fa;
    color: #89b4fa;
}

QStackedWidget {
    background-color: #181825;
}

QScrollArea {
    background-color: transparent;
    border: none;
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

/* Group Boxes */
QGroupBox {
    background-color: #181825;
    border: 1px solid #313244;
    border-radius: 8px;
    margin-top: 14px;
    padding: 16px 12px 12px 12px;
    font-weight: 700;
    color: #cdd6f4;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 14px;
    padding: 0 6px;
    background-color: #181825;
    color: #89b4fa;
}

/* Splitters */
QSplitter {
    background-color: transparent;
}

QSplitter::handle {
    background-color: #313244;
}

QSplitter::handle:horizontal {
    width: 4px;
}

QSplitter::handle:vertical {
    height: 4px;
}

QSplitter::handle:hover {
    background-color: #89b4fa;
}

/* Scrollbars - High-contrast, clear visibility modern engineering styling */
QScrollBar:vertical {
    border: 1px solid #313244;
    background-color: #181825;
    width: 14px;
    margin: 0px 0px 0px 0px;
    border-radius: 4px;
}

QScrollBar::handle:vertical {
    background-color: #585b70;
    border: 1px solid #45475a;
    border-radius: 4px;
    min-height: 35px;
    margin: 2px;
}

QScrollBar::handle:vertical:hover {
    background-color: #89b4fa;
    border-color: #b4befe;
}

QScrollBar::handle:vertical:pressed {
    background-color: #b4befe;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    border: none;
    background: none;
    height: 0px;
    width: 0px;
}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
}

QScrollBar:horizontal {
    border: 1px solid #313244;
    background-color: #181825;
    height: 14px;
    margin: 0px 0px 0px 0px;
    border-radius: 4px;
}

QScrollBar::handle:horizontal {
    background-color: #585b70;
    border: 1px solid #45475a;
    border-radius: 4px;
    min-width: 35px;
    margin: 2px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #89b4fa;
    border-color: #b4befe;
}

QScrollBar::handle:horizontal:pressed {
    background-color: #b4befe;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    border: none;
    background: none;
    height: 0px;
    width: 0px;
}

QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
    background: none;
}

/* Engineering Workspaces & Product Catalog */
QWidget#products_container {
    background-color: #11111b;
}

QSplitter#products_splitter {
    background-color: #11111b;
}

QSplitter#products_splitter::handle {
    background-color: #313244;
    width: 4px;
}

QFrame#catalog_card {
    background-color: #181825;
    border: 1px solid #313244;
    border-radius: 8px;
}

QListWidget#products_list {
    background-color: #11111b;
    color: #cdd6f4;
    border: 1px solid #313244;
    border-radius: 6px;
    padding: 4px;
    outline: none;
}

QListWidget#products_list::item {
    background-color: #1e1e2e;
    color: #cdd6f4;
    border: 1px solid #313244;
    border-radius: 6px;
    margin: 3px 2px;
    padding: 10px;
}

QListWidget#products_list::item:hover {
    background-color: #313244;
    border-color: #89b4fa;
}

QListWidget#products_list::item:selected {
    background-color: #24273a;
    border: 1.5px solid #89b4fa;
    color: #ffffff;
}

QWidget#editor_container {
    background-color: #181825;
}

QTabWidget#product_main_tabs::pane {
    border: 1px solid #313244;
    background-color: #181825;
    top: -1px;
}

QTabWidget#product_main_tabs > QTabBar::tab {
    background-color: #11111b;
    color: #cdd6f4;
    font-size: 12px;
    font-weight: 600;
    padding: 10px 22px;
    border: 1px solid #313244;
    border-bottom: none;
    margin-right: 4px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
}

QTabWidget#product_main_tabs > QTabBar::tab:hover {
    background-color: #313244;
    color: #89b4fa;
    border-color: #89b4fa;
}

QTabWidget#product_main_tabs > QTabBar::tab:selected {
    background-color: #24273a;
    color: #89b4fa;
    border: 1.5px solid #89b4fa;
    border-bottom: 2px solid #24273a;
    font-weight: 700;
}
"""

LIGHT_THEME_QSS = """
QMainWindow, QDialog {
    background-color: #ffffff;
    color: #212529;
    font-family: 'Segoe UI', system-ui, sans-serif;
    font-size: 12px;
}

QWidget {
    color: #212529;
    font-family: 'Segoe UI', system-ui, sans-serif;
    font-size: 12px;
}

QWidget#work_area {
    background-color: #ffffff;
}

QWidget#sidebar_container {
    background-color: #ffffff;
    border-right: 1px solid #dee2e6;
}

/* Sidebar Navigation */
QListWidget#nav_sidebar {
    background-color: #ffffff;
    border: none;
    border-right: 1px solid #dee2e6;
    font-size: 13px;
    font-weight: 500;
    padding: 8px 4px;
}

QListWidget#nav_sidebar::item {
    height: 40px;
    border-radius: 6px;
    padding-left: 12px;
    margin: 2px 6px;
    color: #495057;
}

QListWidget#nav_sidebar::item:hover {
    background-color: #e9ecef;
    color: #212529;
}

QListWidget#nav_sidebar::item:selected {
    background-color: #e7f1ff;
    color: #0066cc;
    font-weight: 600;
    border-left: 3px solid #0066cc;
}

QListWidget#nav_sidebar QScrollBar:vertical {
    border: 1px solid #dee2e6;
    background-color: #ffffff;
    width: 12px;
    margin: 0px;
    border-radius: 4px;
}

QListWidget#nav_sidebar QScrollBar::handle:vertical {
    background-color: #adb5bd;
    border: 1px solid #ced4da;
    border-radius: 4px;
    min-height: 25px;
    margin: 2px;
}

QListWidget#nav_sidebar QScrollBar::handle:vertical:hover {
    background-color: #0066cc;
}

/* Header & Toolbars */
QFrame#top_header {
    background-color: #ffffff;
    border-bottom: 1px solid #dee2e6;
    padding: 6px 16px;
}

/* Cards & Surfaces */
QFrame.card_surface {
    background-color: #ffffff;
    border: 1px solid #dee2e6;
    border-radius: 8px;
    padding: 12px;
}

QFrame.card_surface:hover {
    border-color: #0066cc;
}

/* Buttons */
QPushButton {
    background-color: #ffffff;
    color: #212529;
    border: 1px solid #ced4da;
    border-radius: 5px;
    padding: 6px 14px;
    font-weight: 500;
    font-size: 12px;
}

QPushButton:hover {
    background-color: #e9ecef;
    border-color: #0066cc;
    color: #0066cc;
}

QPushButton:pressed {
    background-color: #dee2e6;
}

QPushButton.primary_btn {
    background-color: #0066cc;
    border: 1px solid #0052a3;
    color: #ffffff;
    font-weight: 600;
}

QPushButton.primary_btn:hover {
    background-color: #0052a3;
    color: #ffffff;
}

/* Inputs & Form Fields */
QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    background-color: #ffffff;
    color: #212529;
    border: 1px solid #ced4da;
    border-radius: 5px;
    padding: 6px 10px;
}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus {
    border: 1px solid #0066cc;
}

/* Tables & Lists */
QTableWidget, QTreeWidget, QListWidget {
    background-color: #ffffff;
    color: #212529;
    border: 1px solid #dee2e6;
    border-radius: 6px;
    gridline-color: #e9ecef;
}

QListWidget::item {
    background-color: #f8f9fa;
    color: #212529;
    border-radius: 5px;
    padding: 6px 10px;
    margin: 2px 2px;
}

QListWidget::item:hover {
    background-color: #e9ecef;
    color: #0066cc;
}

QListWidget::item:selected {
    background-color: #e7f1ff;
    border-left: 3px solid #0066cc;
    color: #0066cc;
    font-weight: 600;
}

QStackedWidget {
    background-color: #f8f9fa;
}

QScrollArea {
    background-color: transparent;
    border: none;
}

QHeaderView::section {
    background-color: #f1f3f5;
    color: #495057;
    padding: 6px;
    border: none;
    border-bottom: 1px solid #dee2e6;
    font-weight: 600;
    font-size: 11px;
}

/* Tab Bar */
QTabWidget::pane {
    border: 1px solid #dee2e6;
    background-color: #ffffff;
    border-radius: 6px;
}

QTabBar::tab {
    background-color: #e9ecef;
    color: #495057;
    padding: 8px 16px;
    border: 1px solid #dee2e6;
    border-bottom: none;
    margin-right: 2px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}

QTabBar::tab:selected {
    background-color: #ffffff;
    color: #0066cc;
    font-weight: 600;
}

/* Badges & Labels */
QLabel.metric_value {
    font-size: 24px;
    font-weight: 700;
    color: #0066cc;
}

QLabel.metric_label {
    font-size: 11px;
    color: #6c757d;
    text-transform: uppercase;
    font-weight: 600;
}

QLabel.badge_ready {
    background-color: #d1e7dd;
    color: #0f5132;
    border: 1px solid #badbcc;
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 10px;
    font-weight: 600;
}

/* Group Boxes */
QGroupBox {
    background-color: #ffffff;
    border: 1px solid #dee2e6;
    border-radius: 8px;
    margin-top: 14px;
    padding: 16px 12px 12px 12px;
    font-weight: 700;
    color: #212529;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 14px;
    padding: 0 6px;
    background-color: #ffffff;
    color: #0066cc;
}

/* Splitters */
QSplitter {
    background-color: transparent;
}

QSplitter::handle {
    background-color: #dee2e6;
}

QSplitter::handle:horizontal {
    width: 4px;
}

QSplitter::handle:vertical {
    height: 4px;
}

QSplitter::handle:hover {
    background-color: #0066cc;
}

/* Scrollbars */
QScrollBar:vertical {
    border: 1px solid #dee2e6;
    background-color: #f8f9fa;
    width: 14px;
    margin: 0px;
    border-radius: 4px;
}

QScrollBar::handle:vertical {
    background-color: #adb5bd;
    border: 1px solid #ced4da;
    border-radius: 4px;
    min-height: 35px;
    margin: 2px;
}

QScrollBar::handle:vertical:hover {
    background-color: #0066cc;
    border-color: #0052a3;
}

QScrollBar::handle:vertical:pressed {
    background-color: #0052a3;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    border: none;
    background: none;
    height: 0px;
    width: 0px;
}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
}

QScrollBar:horizontal {
    border: 1px solid #dee2e6;
    background-color: #f8f9fa;
    height: 14px;
    margin: 0px;
    border-radius: 4px;
}

QScrollBar::handle:horizontal {
    background-color: #adb5bd;
    border: 1px solid #ced4da;
    border-radius: 4px;
    min-width: 35px;
    margin: 2px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #0066cc;
    border-color: #0052a3;
}

QScrollBar::handle:horizontal:pressed {
    background-color: #0052a3;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    border: none;
    background: none;
    height: 0px;
    width: 0px;
}

QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
    background: none;
}

/* Engineering Workspaces & Product Catalog */
QWidget#products_container {
    background-color: #f8f9fa;
}

QSplitter#products_splitter {
    background-color: #f8f9fa;
}

QSplitter#products_splitter::handle {
    background-color: #dee2e6;
    width: 4px;
}

QFrame#catalog_card {
    background-color: #ffffff;
    border: 1px solid #dee2e6;
    border-radius: 8px;
}

QListWidget#products_list {
    background-color: #ffffff;
    color: #212529;
    border: 1px solid #dee2e6;
    border-radius: 6px;
    padding: 4px;
    outline: none;
}

QListWidget#products_list::item {
    background-color: #f8f9fa;
    color: #212529;
    border: 1px solid #dee2e6;
    border-radius: 6px;
    margin: 3px 2px;
    padding: 10px;
}

QListWidget#products_list::item:hover {
    background-color: #e9ecef;
    border-color: #0066cc;
}

QListWidget#products_list::item:selected {
    background-color: #e7f1ff;
    border: 1.5px solid #0066cc;
    color: #0066cc;
    font-weight: 700;
}

QWidget#editor_container {
    background-color: #ffffff;
}

QTabWidget#product_main_tabs::pane {
    border: 1px solid #dee2e6;
    background-color: #ffffff;
    top: -1px;
}

QTabWidget#product_main_tabs > QTabBar::tab {
    background-color: #e9ecef;
    color: #495057;
    font-size: 12px;
    font-weight: 600;
    padding: 10px 22px;
    border: 1px solid #dee2e6;
    border-bottom: none;
    margin-right: 4px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
}

QTabWidget#product_main_tabs > QTabBar::tab:hover {
    background-color: #dee2e6;
    color: #0066cc;
    border-color: #0066cc;
}

QTabWidget#product_main_tabs > QTabBar::tab:selected {
    background-color: #ffffff;
    color: #0066cc;
    border: 1.5px solid #0066cc;
    border-bottom: 2px solid #ffffff;
    font-weight: 700;
}
"""
