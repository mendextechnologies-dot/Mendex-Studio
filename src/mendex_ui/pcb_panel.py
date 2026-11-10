"""PCB workspace presentation; all file/check operations belong to the core."""
import json
from datetime import datetime

from PySide6.QtCore import QThread, Signal, Qt
from PySide6.QtWidgets import (
    QAbstractItemView, QFileDialog, QHBoxLayout, QHeaderView, QLabel,
    QPushButton, QSplitter, QTableWidget, QTableWidgetItem, QTabWidget,
    QTextEdit, QVBoxLayout, QWidget,
)


class _CheckWorker(QThread):
    completed = Signal(dict)
    failed = Signal(str)

    def __init__(self, service, revision_id, path, operation, parent):
        super().__init__(parent)
        self.service, self.revision_id = service, revision_id
        self.path, self.operation = path, operation

    def run(self):
        try:
            self.completed.emit(self.service.pcb.run_check(self.revision_id, self.path, self.operation))
        except Exception as exc:
            self.failed.emit(str(exc))


class PCBWorkspacePanel(QWidget):
    def __init__(self, service, guarded):
        super().__init__()
        self.service, self.guarded = service, guarded
        self.revision = None
        self.worker = None
        self.snapshot = {}
        layout = QVBoxLayout(self)
        self.title = QLabel("PCB Workspace · select a product and revision")
        self.title.setStyleSheet("font-size: 20px; font-weight: 600;")
        layout.addWidget(self.title)
        self.summary = QLabel("Product evaluation: NOT_EVALUATED")
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)
        actions = QHBoxLayout()
        self.import_button = QPushButton("Import KiCad file")
        self.open_button = QPushButton("Open selected design")
        self.refresh_button = QPushButton("Refresh")
        self.erc_button = QPushButton("Run ERC")
        self.drc_button = QPushButton("Run DRC")
        for button, callback in [(self.import_button,self.import_file), (self.open_button,self.open_selected),
                                 (self.refresh_button,self.refresh), (self.erc_button,lambda:self.start_check("erc")),
                                 (self.drc_button,lambda:self.start_check("drc"))]:
            button.clicked.connect(lambda checked=False, cb=callback:self.guarded(cb))
            actions.addWidget(button)
        actions.addStretch()
        layout.addLayout(actions)
        self.files = QTableWidget(0, 4)
        self.files.setHorizontalHeaderLabels(["Native design file", "Type", "Size (bytes)", "Content check"])
        self.files.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.files.setSelectionMode(QAbstractItemView.SingleSelection)
        self.files.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.files.horizontalHeader().setSectionResizeMode(0,QHeaderView.Stretch)
        self.files.horizontalHeader().setSectionResizeMode(3,QHeaderView.Stretch)
        self.files.itemSelectionChanged.connect(self.update_actions)
        split = QSplitter(Qt.Vertical)
        split.addWidget(self.files)
        tabs = QTabWidget()
        self.tabs = tabs
        history = QWidget()
        history_layout = QVBoxLayout(history)
        self.history = QTableWidget(0, 5)
        self.history.setHorizontalHeaderLabels(["Started", "Check", "Design", "Effective result", "Evidence"])
        self.history.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.history.setSelectionMode(QAbstractItemView.SingleSelection)
        self.history.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.history.horizontalHeader().setSectionResizeMode(2,QHeaderView.Stretch)
        for column in (0,1,3,4):
            self.history.horizontalHeader().setSectionResizeMode(column,QHeaderView.ResizeToContents)
        self.history.itemSelectionChanged.connect(self.show_check)
        history_layout.addWidget(self.history)
        self.evidence_button = QPushButton("Open selected check evidence")
        self.evidence_button.setEnabled(False)
        self.evidence_button.clicked.connect(lambda:self.guarded(self.open_check_evidence))
        history_layout.addWidget(self.evidence_button)
        self.details = QTextEdit()
        self.details.setReadOnly(True)
        history_layout.addWidget(self.details)
        tabs.addTab(history,"Check history and evidence")
        notes_tab = QWidget()
        notes_layout = QVBoxLayout(notes_tab)
        notes_help = QLabel("Record board size, clearance assumptions, sources and outstanding HV review. Notes do not approve the design.")
        notes_help.setWordWrap(True)
        notes_layout.addWidget(notes_help)
        self.notes = QTextEdit()
        self.notes.setAcceptRichText(False)
        self.notes.setPlaceholderText("Board envelope and stackup; isolation requirements; assumptions and source references; review still needed…")
        notes_layout.addWidget(self.notes)
        self.save_notes_button = QPushButton("Save draft notes")
        self.save_notes_button.clicked.connect(lambda:self.guarded(self.save_notes))
        notes_layout.addWidget(self.save_notes_button)
        tabs.addTab(notes_tab,"Design and isolation notes")
        split.addWidget(tabs)
        layout.addWidget(split,1)
        self.message = QLabel("Import the circuit schematic and board, select a file, then run the matching check.")
        self.message.setWordWrap(True)
        layout.addWidget(self.message)
        notice = QLabel("Rule checks do not establish HV isolation, product safety or prototype approval. Missing or changed evidence remains NOT_EVALUATED.")
        notice.setWordWrap(True)
        layout.addWidget(notice)
        self.update_actions()

    def is_running(self):
        return self.worker is not None

    def set_revision(self, revision):
        self.revision = revision
        self.details.clear()
        self.message.setText("A check is finishing in the background; its results stay with the original revision." if self.is_running()
                             else "Select a schematic for ERC or a board for DRC. Empty files remain NOT_EVALUATED.")
        self.notes.setPlainText(self.service.pcb.review_notes(revision.revision_id) if revision else "")
        self.refresh()

    def refresh(self):
        selected = self.selected_path()
        self.snapshot = self.service.pcb.overview(self.revision.revision_id) if self.revision else {}
        self.files.setRowCount(0)
        self.history.setRowCount(0)
        if not self.revision:
            self.title.setText("PCB Workspace · select a product and revision")
            self.summary.setText("Product evaluation: NOT_EVALUATED")
            self.update_actions()
            return
        product = self.service.get_product(self.revision.product_id)
        self.title.setText(f"PCB Workspace · {product.code} · {self.revision.revision_label}")
        state = "available" if self.snapshot["tool_available"] else "unavailable"
        self.summary.setText(f"KiCad CLI: {state} · Product evaluation: NOT_EVALUATED\n{self.snapshot['workspace']}")
        for i, entry in enumerate(self.snapshot["files"]):
            self.files.insertRow(i)
            structure = entry.get("structure")
            content = "Project/rules context" if not structure else (
                "Content present · not verified" if structure["populated"] else "NOT_EVALUATED · " + structure["reason"])
            for col,value in enumerate([entry["path"],entry["kind"],str(entry["bytes"]),content]):
                item = QTableWidgetItem(value)
                item.setToolTip(value)
                self.files.setItem(i,col,item)
            if entry["path"] == selected:
                self.files.selectRow(i)
        checks = sorted(self.snapshot["checks"],key=lambda x:x.get("started_at",""),reverse=True)
        for i, check in enumerate(checks):
            self.history.insertRow(i)
            timestamp = check.get("started_at")
            started = datetime.fromisoformat(timestamp).astimezone().strftime("%d %b %Y %H:%M:%S %z") if timestamp else "Unknown"
            values = [started, check.get("operation",""),check.get("source",""),
                      check["effective_status"], "Changed/missing" if not check["integrity"] else ("Stale inputs" if check["stale"] else "Hash verified")]
            for col,value in enumerate(values):
                item=QTableWidgetItem(value)
                item.setData(Qt.UserRole,check["run_id"])
                self.history.setItem(i,col,item)
        if self.history.rowCount():
            self.history.selectRow(0)
        self.update_actions()

    def selected_path(self):
        row=self.files.currentRow()
        item=self.files.item(row,0) if row>=0 else None
        return item.text() if item else None

    def update_actions(self):
        selected = self.selected_path() or ""
        idle = not self.is_running()
        editable = bool(self.snapshot.get("editable"))
        self.import_button.setEnabled(editable and idle)
        self.open_button.setEnabled(editable and bool(selected) and not selected.endswith(".kicad_dru") and idle)
        self.refresh_button.setEnabled(idle)
        self.save_notes_button.setEnabled(editable and idle)
        self.notes.setReadOnly(not editable or not idle)
        self.erc_button.setEnabled(bool(self.revision) and idle and selected.endswith(".kicad_sch"))
        self.drc_button.setEnabled(bool(self.revision) and idle and selected.endswith(".kicad_pcb"))

    def import_file(self):
        source,_ = QFileDialog.getOpenFileName(self,"Import into draft PCB workspace","",
                                              "KiCad files (*.kicad_sch *.kicad_pcb *.kicad_pro *.kicad_dru)")
        if source:
            saved=self.service.pcb.import_file(self.revision.revision_id,source)
            self.refresh()
            self.message.setText(f"Imported {saved}. Existing files were preserved. Import companion sheets/project/rules as needed.")

    def open_selected(self):
        path=self.selected_path()
        if path:
            self.service.pcb.open_file(self.revision.revision_id,path)

    def save_notes(self):
        path=self.service.pcb.save_review_notes(self.revision.revision_id,self.notes.toPlainText())
        self.refresh()
        self.message.setText(f"Saved {path}. Notes remain unreviewed; earlier check snapshots are retained.")

    def start_check(self,operation):
        if self.is_running() or not self.revision or not self.selected_path():
            return
        self.worker=_CheckWorker(self.service,str(self.revision.revision_id),self.selected_path(),operation,self)
        self.worker.completed.connect(self.check_completed)
        self.worker.failed.connect(lambda error:self.message.setText("Check could not complete: "+error))
        self.worker.finished.connect(self.check_finished)
        self.message.setText(f"Running {operation.upper()} on an input snapshot. You can continue using Studio.")
        self.update_actions()
        self.worker.start()

    def check_completed(self,result):
        if self.revision and result.get("revision_id")==str(self.revision.revision_id):
            self.message.setText(f"{result['effective_status']}: {result['diagnostic']}")
            self.refresh()

    def check_finished(self):
        worker=self.worker
        self.worker=None
        if worker:
            worker.deleteLater()
        self.update_actions()

    def show_check(self):
        item=self.history.item(self.history.currentRow(),0)
        self.evidence_button.setEnabled(bool(item))
        if item and self.revision:
            result=self.service.pcb.read_check(self.revision.revision_id,item.data(Qt.UserRole))
            self.details.setPlainText(json.dumps(result,indent=2))
        else:
            self.details.clear()

    def open_check_evidence(self):
        item=self.history.item(self.history.currentRow(),0)
        if item and self.revision:
            self.service.pcb.open_check_evidence(self.revision.revision_id,item.data(Qt.UserRole))
