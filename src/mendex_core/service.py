import shutil
import sqlite3
import json
import html
import os
from contextlib import contextmanager
from pathlib import Path
from uuid import UUID, uuid4

from .models import Category, Lifecycle, Product, Revision, Specification, now
from .adapters import AdapterRegistry
from .evidence import ManualCheck, ValidationRecord, ValidationStatus, Report, SimulationRun, digest, specification_hash
from .rules import RuleRegistry
from .ai import AIRequest, UnavailableAIService


class StudioError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


class StudioService:
    def __init__(self, root: Path, registry=None):
        self.registry = registry or AdapterRegistry.defaults()
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        metadata = self.root / ".mendex"
        metadata.mkdir(exist_ok=True)
        self.database = metadata / "studio.sqlite3"
        self.rules = RuleRegistry.defaults()
        self.ai = UnavailableAIService()
        self.plugin_status = []
        from .plugins import load_plugin_file
        loaded_plugin_ids = set()
        for manifest in sorted((metadata / "plugins").glob("*.json")):
            try:
                self.plugin_status.append(load_plugin_file(manifest, self.registry, self.rules, loaded_plugin_ids))
            except (ValueError, OSError) as exc:
                self.plugin_status.append({"path": str(manifest), "status": "rejected", "diagnostic": str(exc)})
        with self.connection() as db:
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version > 4:
                raise StudioError("STORAGE_ERROR", "Database is newer than this application")
            if version == 0:
                db.executescript('''
                    CREATE TABLE products (id TEXT PRIMARY KEY, code TEXT UNIQUE COLLATE NOCASE, payload TEXT NOT NULL);
                    CREATE TABLE revisions (id TEXT PRIMARY KEY, product_id TEXT NOT NULL REFERENCES products(id), label TEXT NOT NULL COLLATE NOCASE, payload TEXT NOT NULL, UNIQUE(product_id,label));
                    PRAGMA user_version=1;
                ''')
            if version < 2:
                db.executescript('''
                    BEGIN IMMEDIATE;
                    CREATE TABLE IF NOT EXISTS tool_settings (tool_id TEXT PRIMARY KEY, path TEXT NOT NULL);
                    CREATE TABLE IF NOT EXISTS validations (id TEXT PRIMARY KEY, revision_id TEXT NOT NULL REFERENCES revisions(id), payload TEXT NOT NULL);
                    CREATE TABLE IF NOT EXISTS reports (id TEXT PRIMARY KEY, revision_id TEXT NOT NULL REFERENCES revisions(id), payload TEXT NOT NULL);
                    CREATE TRIGGER IF NOT EXISTS validation_no_update BEFORE UPDATE ON validations BEGIN SELECT RAISE(ABORT,'Validation records are append-only'); END;
                    CREATE TRIGGER IF NOT EXISTS validation_no_delete BEFORE DELETE ON validations BEGIN SELECT RAISE(ABORT,'Validation records are append-only'); END;
                    PRAGMA user_version=2;
                    COMMIT;
                ''')
            if version < 3:
                db.executescript('''
                    BEGIN IMMEDIATE;
                    CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, revision_id TEXT NOT NULL REFERENCES revisions(id), payload TEXT NOT NULL);
                    CREATE TRIGGER IF NOT EXISTS runs_no_update BEFORE UPDATE ON runs BEGIN SELECT RAISE(ABORT,'Run records are append-only'); END;
                    CREATE TRIGGER IF NOT EXISTS runs_no_delete BEFORE DELETE ON runs BEGIN SELECT RAISE(ABORT,'Run records are append-only'); END;
                    PRAGMA user_version=3;
                    COMMIT;
                ''')
            if version < 4:
                from .integration_store import migrate
                migrate(db)
            if version < 5:
                from .integration_store import migrate_v5
                migrate_v5(db)
        from .integration_service import IntegrationService
        self.integrations = IntegrationService(self)
        from .intelligence import EngineeringReasoningOrchestrator
        self.intelligence = EngineeringReasoningOrchestrator()
        from .workflows import WorkflowStorageService, migrate_workflows_table
        with self.connection() as db:
            migrate_workflows_table(db)
        self.workflows = WorkflowStorageService(self.database)

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.database, timeout=10)
        db.execute("PRAGMA foreign_keys=ON")
        try:
            with db:
                yield db
        except sqlite3.IntegrityError as exc:
            raise StudioError("CONFLICT", "Product code or revision label already exists") from exc
        except sqlite3.Error as exc:
            raise StudioError("STORAGE_ERROR", str(exc)) from exc
        finally:
            db.close()

    def list_products(self):
        with self.connection() as db:
            return [Product.model_validate_json(row[0]) for row in db.execute("SELECT payload FROM products ORDER BY code")]

    def _get(self, table, identifier, model):
        try:
            identifier = str(UUID(str(identifier)))
        except (ValueError, TypeError) as exc:
            raise StudioError("INVALID_INPUT", "Expected a valid product or revision UUID") from exc
        with self.connection() as db:
            row = db.execute(f"SELECT payload FROM {table} WHERE id=?", (identifier,)).fetchone()
        if row is None:
            raise StudioError("NOT_FOUND", f"{model.__name__} not found")
        return model.model_validate_json(row[0])

    def get_product(self, product_id):
        return self._get("products", product_id, Product)

    def get_revision(self, revision_id):
        return self._get("revisions", revision_id, Revision)

    def list_revisions(self, product_id):
        self.get_product(product_id)
        with self.connection() as db:
            return [Revision.model_validate_json(r[0]) for r in db.execute("SELECT payload FROM revisions WHERE product_id=? ORDER BY rowid", (str(product_id),))]

    def workspace_path(self, revision):
        path = (self.root / "products" / str(revision.product_id) / "revisions" / str(revision.revision_id)).resolve()
        if not path.is_relative_to(self.root):
            raise StudioError("INVALID_INPUT", "Workspace escapes configured root")
        return path

    def _workspace(self, revision):
        path = self.workspace_path(revision)
        for folder in ("requirements", "magnetics", "circuit", "pcb", "mechanical", "simulations", "validation", "reports"):
            (path / folder).mkdir(parents=True, exist_ok=True)
        snapshot = path / "revision.json"
        if not snapshot.exists():
            snapshot.write_text(revision.model_dump_json(indent=2), encoding="utf-8")
        return path

    def export_specification(self, revision_id):
        revision = self.get_revision(revision_id)
        folder = self.workspace_path(revision) / "requirements"
        destination = (folder / f"specification-{uuid4()}.json").resolve()
        if not destination.is_relative_to(self.root):
            raise StudioError("INVALID_INPUT", "Specification export escapes data root")
        with destination.open("x", encoding="utf-8") as handle:
            json.dump({"revision": revision.model_dump(mode="json"), "input_hash": specification_hash(revision.specification), "notice": "Read-only export; SQLite is canonical. This export does not approve the design."}, handle, indent=2)
        return destination

    def create_workspace(self, revision_id):
        return self._workspace(self.get_revision(revision_id))

    def open_in_vscode(self, revision_id):
        from .launch import launch_vscode
        revision = self.get_revision(revision_id)
        folder = self.workspace_path(revision)
        if not folder.is_dir():
            raise StudioError("NOT_FOUND", "Workspace is missing; restore the project files before opening")
        try:
            return launch_vscode(folder)
        except OSError as exc:
            raise StudioError("LAUNCH_ERROR", str(exc)) from exc

    def open_project_file(self, revision_id, relative_path="."):
        from .launch import NATIVE_EXTENSIONS, open_native
        folder = self.workspace_path(self.get_revision(revision_id))
        relative = Path(relative_path)
        path = (folder / relative).resolve()
        if relative.is_absolute() or not path.is_relative_to(folder) or not path.exists():
            raise StudioError("INVALID_INPUT", "Choose an existing file or folder inside this revision workspace")
        if path.is_file() and path.suffix.lower() not in NATIVE_EXTENSIONS:
            raise StudioError("INVALID_INPUT", "This file type cannot be launched from Studio; scripts and executables are excluded")
        try:
            open_native(path)
        except OSError as exc:
            raise StudioError("LAUNCH_ERROR", f"Could not open the file. Check the Windows file association: {exc}") from exc
        return str(path)

    def diagnostics(self):
        from .diagnostics import diagnose
        return diagnose(self)

    def export_diagnostics(self):
        destination = self.root / ".mendex" / "diagnostics" / f"{uuid4()}.json"
        destination.parent.mkdir(exist_ok=True)
        data = self.diagnostics()
        with destination.open("x", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)
        return destination

    def open_report(self, report_id):
        from .launch import open_native
        report = self._get("reports", report_id, Report)
        path = (self.root / report.report_path).resolve()
        if not path.is_relative_to(self.root) or not path.is_file() or path.suffix.lower() != ".html":
            raise StudioError("INVALID_INPUT", "Report is missing or outside the data root")
        try:
            open_native(path)
        except OSError as exc:
            raise StudioError("LAUNCH_ERROR", f"Could not open report. Check the default HTML application: {exc}") from exc
        return str(path)

    def create_product(self, code, name, category: Category, owner, description=""):
        revision_id = uuid4()
        product = Product(code=code, name=name, category=category, owner=owner, description=description, active_revision_id=revision_id)
        revision = Revision(revision_id=revision_id, product_id=product.product_id, revision_label="R001")
        path = self.workspace_path(revision)
        try:
            with self.connection() as db:
                db.execute("INSERT INTO products VALUES (?,?,?)", (str(product.product_id), product.code, product.model_dump_json()))
                db.execute("INSERT INTO revisions VALUES (?,?,?,?)", (str(revision_id), str(product.product_id), revision.revision_label, revision.model_dump_json()))
                self._workspace(revision)
        except Exception:
            if path.exists():
                shutil.rmtree(path)
            raise
        return product

    def update_product(self, product_id, name, owner, description):
        product = self.get_product(product_id)
        product = Product.model_validate({**product.model_dump(), "name": name, "owner": owner, "description": description, "updated_at": now()})
        with self.connection() as db:
            db.execute("UPDATE products SET payload=? WHERE id=?", (product.model_dump_json(), str(product_id)))
        return product

    def save_product_revision(self, product_id, revision_id, name, owner, description, specification):
        spec = Specification.model_validate(specification)
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            product_row = db.execute("SELECT payload FROM products WHERE id=?", (str(product_id),)).fetchone()
            revision_row = db.execute("SELECT payload FROM revisions WHERE id=?", (str(revision_id),)).fetchone()
            if not product_row or not revision_row:
                raise StudioError("NOT_FOUND", "Product or revision not found")
            product = Product.model_validate_json(product_row[0])
            revision = Revision.model_validate_json(revision_row[0])
            if revision.product_id != product.product_id:
                raise StudioError("INVALID_INPUT", "Revision does not belong to this product")
            if revision.lifecycle_status != Lifecycle.DRAFT:
                raise StudioError("IMMUTABLE", "Only draft revisions can be edited")
            product = Product.model_validate({**product.model_dump(), "name": name, "owner": owner, "description": description, "updated_at": now()})
            revision.specification = spec
            db.execute("UPDATE products SET payload=? WHERE id=?", (product.model_dump_json(), str(product.product_id)))
            db.execute("UPDATE revisions SET payload=? WHERE id=?", (revision.model_dump_json(), str(revision.revision_id)))
        return product, revision

    def rename_revision(self, revision_id, label):
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT payload FROM revisions WHERE id=?", (str(revision_id),)).fetchone()
            if not row:
                raise StudioError("NOT_FOUND", "Revision not found")
            revision = Revision.model_validate_json(row[0])
            if revision.lifecycle_status != Lifecycle.DRAFT:
                raise StudioError("IMMUTABLE", "Only a draft revision label can be edited")
            revision = Revision.model_validate({**revision.model_dump(), "revision_label": label})
            db.execute("UPDATE revisions SET label=?,payload=? WHERE id=?", (revision.revision_label, revision.model_dump_json(), str(revision.revision_id)))
        return revision

    def update_specification(self, revision_id, specification):
        spec = Specification.model_validate(specification)
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT payload FROM revisions WHERE id=?", (str(revision_id),)).fetchone()
            if not row:
                raise StudioError("NOT_FOUND", "Revision not found")
            revision = Revision.model_validate_json(row[0])
            if revision.lifecycle_status != Lifecycle.DRAFT:
                raise StudioError("IMMUTABLE", "Create a new revision to change this baseline")
            revision.specification = spec
            db.execute("UPDATE revisions SET payload=? WHERE id=?", (revision.model_dump_json(), str(revision_id)))
        return revision

    def configure_tool(self, tool_id, path=None):
        self.registry.get(tool_id)
        if path:
            candidate = Path(path)
            if not candidate.is_absolute() or not candidate.is_file() or (candidate.suffix.lower() != ".exe" if os.name == "nt" else not os.access(candidate, os.X_OK)):
                raise StudioError("INVALID_INPUT", "Select an existing absolute executable path")
            path = str(candidate.resolve())
        with self.connection() as db:
            if path:
                db.execute("INSERT OR REPLACE INTO tool_settings VALUES (?,?)", (tool_id, path))
            else:
                db.execute("DELETE FROM tool_settings WHERE tool_id=?", (tool_id,))
        return self.check_tool(tool_id)

    def check_tool(self, tool_id):
        with self.connection() as db:
            row = db.execute("SELECT path FROM tool_settings WHERE tool_id=?", (tool_id,)).fetchone()
        return self.registry.get(tool_id).probe(row[0] if row else None)

    def list_tools(self):
        return [self.check_tool(adapter.tool_id) for adapter in self.registry.list()]

    def list_runs(self, revision_id):
        self.get_revision(revision_id)
        with self.connection() as db:
            return [SimulationRun.model_validate_json(row[0]) for row in db.execute("SELECT payload FROM runs WHERE revision_id=? ORDER BY rowid", (str(revision_id),))]

    def request_simulation(self, revision_id, tool_id):
        revision = self.get_revision(revision_id)
        if revision.lifecycle_status != Lifecycle.DRAFT:
            raise StudioError("IMMUTABLE", "Simulation requests require a draft revision")
        adapter = self.registry.get(tool_id)
        record = SimulationRun(revision_id=revision.revision_id, tool_id=tool_id, adapter_version=adapter.capabilities().adapter_version, status="not_supported", input_hash=specification_hash(revision.specification), specification=revision.specification, tool_version=self.check_tool(tool_id).installed_version)
        with self.connection() as db:
            db.execute("INSERT INTO runs VALUES (?,?,?)", (str(record.run_id), str(revision_id), record.model_dump_json()))
        return record

    def list_rules(self, revision_id=None):
        if revision_id is None:
            return self.rules.list()
        revision = self.get_revision(revision_id)
        return self.rules.assess(self.get_product(revision.product_id).category, revision.specification)

    def ai_advice(self, revision_id, question):
        revision = self.get_revision(revision_id)
        return self.ai.advise(AIRequest(revision_id=revision.revision_id, question=question, context={"specification": revision.specification.model_dump(mode="json")}))

    def advise_engineering(self, question, workspace_context=None, provider_id=None):
        return self.intelligence.process_query(question, workspace_context, provider_id)

    def list_plugins(self):
        return self.plugin_status

    def set_revision_status(self, revision_id, status):
        status = Lifecycle(status)
        if status not in (Lifecycle.DRAFT, Lifecycle.IN_REVIEW):
            raise StudioError("INVALID_INPUT", "Approval is not implemented. Archive a baseline by creating its next revision.")
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT payload FROM revisions WHERE id=?", (str(revision_id),)).fetchone()
            if not row:
                raise StudioError("NOT_FOUND", "Revision not found")
            revision = Revision.model_validate_json(row[0])
            if revision.lifecycle_status not in (Lifecycle.DRAFT, Lifecycle.IN_REVIEW):
                raise StudioError("IMMUTABLE", "Archived or approved baselines cannot be reopened")
            revision.lifecycle_status = status
            db.execute("UPDATE revisions SET payload=? WHERE id=?", (revision.model_dump_json(), str(revision_id)))
        return revision

    def list_validation(self, revision_id):
        self.get_revision(revision_id)
        with self.connection() as db:
            return [ValidationRecord.model_validate_json(row[0]) for row in db.execute("SELECT payload FROM validations WHERE revision_id=? ORDER BY rowid", (str(revision_id),))]

    def record_validation(self, revision_id, check, evidence_path=None):
        check = ManualCheck.model_validate(check)
        revision = self.get_revision(revision_id)
        if revision.lifecycle_status != Lifecycle.DRAFT:
            raise StudioError("IMMUTABLE", "Validation cannot be appended to an archived baseline")
        if check.status in (ValidationStatus.PASS, ValidationStatus.FAIL) and evidence_path is None:
            raise StudioError("INVALID_INPUT", "PASS/FAIL requires an actual evidence file")
        record = ValidationRecord(revision_id=revision.revision_id, specification=revision.specification, input_hash=specification_hash(revision.specification), check=check)
        folder = (self.workspace_path(revision) / "validation" / str(record.record_id)).resolve()
        if not folder.is_relative_to(self.root):
            raise StudioError("INVALID_INPUT", "Evidence directory escapes the data root")
        try:
            with self.connection() as db:
                db.execute("BEGIN IMMEDIATE")
                fresh = Revision.model_validate_json(db.execute("SELECT payload FROM revisions WHERE id=?", (str(revision.revision_id),)).fetchone()[0])
                if fresh != revision:
                    raise StudioError("CONFLICT", "Revision changed; refresh and retry")
                folder.mkdir(parents=True, exist_ok=False)
                if evidence_path is not None:
                    source = Path(evidence_path)
                    if not source.is_absolute() or not source.is_file():
                        raise StudioError("INVALID_INPUT", "Evidence must be an existing absolute file path")
                    if source.stat().st_size > 50 * 1024 * 1024:
                        raise StudioError("INVALID_INPUT", "Evidence limit is 50 MiB per entry")
                    with source.open("rb") as handle:
                        data = handle.read(50 * 1024 * 1024 + 1)
                    if len(data) > 50 * 1024 * 1024:
                        raise StudioError("INVALID_INPUT", "Evidence limit is 50 MiB per entry")
                    if not data and check.status in (ValidationStatus.PASS, ValidationStatus.FAIL):
                        raise StudioError("INVALID_INPUT", "PASS/FAIL requires a nonempty evidence file")
                    raw_folder = folder / "raw"
                    raw_folder.mkdir()
                    destination = raw_folder / ("evidence" + source.suffix[:16])
                    with destination.open("xb") as handle:
                        handle.write(data)
                    record.evidence_uri = str(destination.relative_to(self.root))
                    record.evidence_sha256 = digest(data)
                    record.evidence_filename = source.name
                with (folder / "manifest.json").open("x", encoding="utf-8") as handle:
                    handle.write(record.model_dump_json(indent=2))
                db.execute("INSERT INTO validations VALUES (?,?,?)", (str(record.record_id), str(revision_id), record.model_dump_json()))
        except Exception:
            if folder.exists():
                shutil.rmtree(folder)
            raise
        return record

    def validation_integrity(self, record):
        if record.evidence_uri is None:
            return record.check.status not in (ValidationStatus.PASS, ValidationStatus.FAIL)
        path = (self.root / record.evidence_uri).resolve()
        try:
            return path.is_relative_to(self.root) and path.is_file() and path.stat().st_size <= 50 * 1024 * 1024 and digest(path.read_bytes()) == record.evidence_sha256
        except OSError:
            return False

    def open_evidence(self, record_id):
        from .launch import NATIVE_EXTENSIONS, open_native
        record = self._get("validations", record_id, ValidationRecord)
        if not record.evidence_uri or not self.validation_integrity(record):
            raise StudioError("INVALID_INPUT", "Evidence is unavailable or has changed")
        path = (self.root / record.evidence_uri).resolve()
        if path.suffix.lower() not in NATIVE_EXTENSIONS:
            raise StudioError("INVALID_INPUT", "Use the workspace folder to inspect this evidence format; direct launch is not allowed")
        try:
            open_native(path)
        except OSError as exc:
            raise StudioError("LAUNCH_ERROR", str(exc)) from exc
        return str(path)

    def validation_summary(self, revision_id):
        revision = self.get_revision(revision_id)
        current_hash = specification_hash(revision.specification)
        summary = []
        for record in self.list_validation(revision_id):
            integrity = self.validation_integrity(record)
            stale = record.input_hash != current_hash
            effective_status = record.check.status.value
            if stale or not integrity:
                effective_status = "not_evaluated"
            summary.append({"record": record, "effective_status": effective_status, "stale": stale, "evidence_integrity": integrity})
        return summary

    def list_reports(self, revision_id):
        self.get_revision(revision_id)
        with self.connection() as db:
            return [Report.model_validate_json(row[0]) for row in db.execute("SELECT payload FROM reports WHERE revision_id=? ORDER BY rowid", (str(revision_id),))]

    def generate_report(self, revision_id):
        revision = self.get_revision(revision_id)
        product = self.get_product(revision.product_id)
        summaries = self.validation_summary(revision_id)
        records = [entry["record"] for entry in summaries]
        current_hash = specification_hash(revision.specification)
        warnings = ["DRAFT ONLY: no manufacturing approval or safety certification.", "Manual values and criteria are supplied by the reviewer; their engineering validity is not independently verified.", "No automated simulations or physical tests were executed by Mendex."]
        if not records:
            warnings.append("NOT_EVALUATED: no validation records available.")
        rows = []
        for entry in summaries:
            record = entry["record"]
            status = entry["effective_status"]
            if entry["stale"]:
                warnings.append(f"{record.check.check_id}: evidence belongs to a different specification snapshot.")
            if not entry["evidence_integrity"]:
                warnings.append(f"{record.check.check_id}: evidence integrity failure (evidence missing or altered).")
            rows.append({"record_id": str(record.record_id), "check_id": record.check.check_id, "effective_status": status, "record": record.model_dump(mode="json")})
        report_id = uuid4()
        folder = (self.workspace_path(revision) / "reports" / str(report_id)).resolve()
        if not folder.is_relative_to(self.root):
            raise StudioError("INVALID_INPUT", "Report directory escapes the data root")
        report = Report(report_id=report_id, revision_id=revision.revision_id, input_hash=current_hash, report_path=str((folder / "report.html").relative_to(self.root)), included_check_ids=[r.check.check_id for r in records], warnings=warnings)
        snapshot = {"report": report.model_dump(mode="json"), "product": product.model_dump(mode="json"), "revision": revision.model_dump(mode="json"), "tools": [t.model_dump(mode="json") for t in self.list_tools()], "validation": rows, "simulation_requests": [run.model_dump(mode="json") for run in self.list_runs(revision_id)], "engineering_rules": [rule.model_dump(mode="json") for rule in self.list_rules(revision_id)], "plugins": self.list_plugins()}
        text = json.dumps(snapshot, indent=2)
        body = f'<!doctype html><html><head><meta charset="utf-8"><title>Mendex draft dossier</title><style>body{{font:16px Segoe UI,sans-serif;max-width:1000px;margin:40px auto;padding:20px}}pre{{white-space:pre-wrap;overflow-wrap:anywhere}}li{{margin:8px}}</style></head><body><h1>Mendex engineering dossier · DRAFT</h1><p>{html.escape(product.code)} · {html.escape(revision.revision_label)}</p><ul>' + ''.join(f'<li>{html.escape(w)}</li>' for w in warnings) + '</ul><h2>Frozen input and evidence snapshot</h2><pre>' + html.escape(text) + '</pre></body></html>'
        table = '<h2>Manual validation history</h2><table border="1" cellpadding="8" style="border-collapse:collapse"><tr><th>Requirement</th><th>Effective status</th><th>Origin</th><th>Value</th><th>Reviewer</th></tr>'
        for row in rows:
            check = row["record"]["check"]
            values = [row["check_id"], row["effective_status"], check["evidence_kind"], f'{check["measured_value"]} {check["unit"]}' if check["measured_value"] is not None else "Unavailable", check["reviewer"]]
            table += '<tr>' + ''.join(f'<td>{html.escape(str(value))}</td>' for value in values) + '</tr>'
        table += '</table><p>Entries are historical assessments, not a consolidated product approval.</p>'
        body = body.replace('<h2>Frozen input and evidence snapshot</h2>', table + '<h2>Frozen input and evidence snapshot</h2>')
        try:
            folder.mkdir(parents=True, exist_ok=False)
            (folder / "snapshot.json").write_text(text, encoding="utf-8")
            (folder / "report.html").write_text(body, encoding="utf-8")
            with self.connection() as db:
                db.execute("INSERT INTO reports VALUES (?,?,?)", (str(report_id), str(revision_id), report.model_dump_json()))
        except Exception:
            if folder.exists():
                shutil.rmtree(folder)
            raise
        return report

    def create_revision(self, product_id, label):
        product = self.get_product(product_id)
        previous = self.get_revision(product.active_revision_id)
        revision = Revision(product_id=product.product_id, revision_label=label, specification=previous.specification.model_copy(deep=True))
        path = self.workspace_path(revision)
        try:
            with self.connection() as db:
                db.execute("BEGIN IMMEDIATE")
                current = Product.model_validate_json(db.execute("SELECT payload FROM products WHERE id=?", (str(product_id),)).fetchone()[0])
                if current.active_revision_id != previous.revision_id:
                    raise StudioError("CONFLICT", "Active revision changed; refresh and retry")
                previous = Revision.model_validate_json(db.execute("SELECT payload FROM revisions WHERE id=?", (str(current.active_revision_id),)).fetchone()[0])
                revision.specification = previous.specification.model_copy(deep=True)
                previous.lifecycle_status = Lifecycle.ARCHIVED
                product.active_revision_id = revision.revision_id
                product.updated_at = now()
                db.execute("INSERT INTO revisions VALUES (?,?,?,?)", (str(revision.revision_id), str(product_id), revision.revision_label, revision.model_dump_json()))
                db.execute("UPDATE revisions SET payload=? WHERE id=?", (previous.model_dump_json(), str(previous.revision_id)))
                db.execute("UPDATE products SET payload=? WHERE id=?", (product.model_dump_json(), str(product_id)))
                self._workspace(revision)
        except Exception:
            if path.exists():
                shutil.rmtree(path)
            raise
        return revision
