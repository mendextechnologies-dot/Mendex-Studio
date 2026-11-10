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
from .evidence import ManualCheck, ValidationRecord, ValidationStatus, Report, digest, specification_hash


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
        with self.connection() as db:
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version > 2:
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
        identifier = str(UUID(str(identifier)))
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
        return path

    def create_workspace(self, revision_id):
        return self._workspace(self.get_revision(revision_id))

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
        return []  # No solver execution implemented. Never manufacture run records.

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
                    data = source.read_bytes()
                    destination = folder / "evidence.bin"
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
            return path.is_relative_to(self.root) and path.is_file() and digest(path.read_bytes()) == record.evidence_sha256
        except OSError:
            return False

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
        snapshot = {"report": report.model_dump(mode="json"), "product": product.model_dump(mode="json"), "revision": revision.model_dump(mode="json"), "tools": [t.model_dump(mode="json") for t in self.list_tools()], "validation": rows}
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
