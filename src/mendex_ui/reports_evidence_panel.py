"""Reports and Verification Evidence Panel for Mendex Engineering Studio v2.1."""
from __future__ import annotations

from PySide6.QtWidgets import QTabWidget, QVBoxLayout, QWidget

from .panels import ReportsPanel, ValidationPanel


class ReportsEvidencePanel(QWidget):
    """Unified reports and verification evidence panel."""

    def __init__(self, service, guarded_callback=None, parent=None):
        super().__init__(parent)
        self.service = service
        self.guarded = guarded_callback or (lambda fn: fn())
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        self.tabs = QTabWidget()

        # Tab 1: Engineering Dossiers & Reports
        self.reports_panel = ReportsPanel(self.service, self.guarded)
        self.tabs.addTab(self.reports_panel, "📄 Verification Dossiers & Reports")

        # Tab 2: Verification Criteria & Audit Trail
        self.validation_panel = ValidationPanel(self.service, self.guarded)
        self.tabs.addTab(self.validation_panel, "🛡️ Verification Records & Audit Trail")

        layout.addWidget(self.tabs)

    def refresh(self):
        if hasattr(self.reports_panel, "refresh"):
            self.reports_panel.refresh()
        if hasattr(self.validation_panel, "refresh"):
            self.validation_panel.refresh()
