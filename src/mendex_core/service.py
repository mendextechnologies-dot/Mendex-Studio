import shutil
import sqlite3
import json
import html
import os
import csv
from datetime import datetime, timezone
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from uuid import UUID, uuid4

from .models import Category, Lifecycle, Product, Revision, Specification, now
from .adapters import AdapterRegistry
from .evidence import ManualCheck, ValidationRecord, ValidationStatus, Report, SimulationRun, digest, specification_hash
from .rules import RuleRegistry
from .sqlite_schema import execute_schema


class StudioError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


class StudioService:
    def __init__(self, root: Path, registry=None):
        self._active_transaction = ContextVar("mendex_transaction", default=None)
        self.registry = registry or AdapterRegistry.defaults()
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        metadata = self.root / ".mendex"
        metadata.mkdir(exist_ok=True)
        self.database = metadata / "studio.sqlite3"
        self.rules = RuleRegistry.defaults()
        self.plugin_status = []
        from .plugins import load_plugin_file
        loaded_plugin_ids = set()
        for manifest in sorted((metadata / "plugins").glob("*.json")):
            try:
                self.plugin_status.append(load_plugin_file(manifest, self.registry, self.rules, loaded_plugin_ids))
            except (ValueError, OSError) as exc:
                self.plugin_status.append({"path": str(manifest), "status": "rejected", "diagnostic": str(exc)})
        with self.connection() as db:
            # Hold the writer lock before inspecting the version. Another process
            # may be starting against this same new data root.
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("PRAGMA synchronous=NORMAL")
            db.execute("BEGIN IMMEDIATE")
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version > 4:
                raise StudioError("STORAGE_ERROR", "Database is newer than this application")
            if version == 0:
                execute_schema(db, '''
                    CREATE TABLE products (id TEXT PRIMARY KEY, code TEXT UNIQUE COLLATE NOCASE, payload TEXT NOT NULL);
                    CREATE TABLE revisions (id TEXT PRIMARY KEY, product_id TEXT NOT NULL REFERENCES products(id), label TEXT NOT NULL COLLATE NOCASE, payload TEXT NOT NULL, UNIQUE(product_id,label));
                    PRAGMA user_version=1;
                ''')
            if version < 2:
                execute_schema(db, '''
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
                execute_schema(db, '''
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
            from .integration_store import migrate_v5
            migrate_v5(db)
            db.execute("CREATE TRIGGER IF NOT EXISTS reports_no_update BEFORE UPDATE ON reports BEGIN SELECT RAISE(ABORT,'Report records are append-only'); END;")
            db.execute("CREATE TRIGGER IF NOT EXISTS reports_no_delete BEFORE DELETE ON reports BEGIN SELECT RAISE(ABORT,'Report records are append-only'); END;")
        from .integration_service import IntegrationService
        self.integrations = IntegrationService(self)
        from .workflows import WorkflowStorageService, migrate_workflows_table, WorkflowExecutionEngine
        with self.connection() as db:
            migrate_workflows_table(db)
        self.workflows = WorkflowStorageService(self.database)
        self.workflow_engine = WorkflowExecutionEngine(self, self.workflows)
        from .lifecycle import ProductLifecycleEngine
        self.lifecycle = ProductLifecycleEngine(self)
        from .lifecycle.ecr import ECRService
        self.ecr = ECRService(self)
        from .measurements import MeasurementService
        self.measurements = MeasurementService(self)
        from .pcb import PCBWorkspaceService
        self.pcb = PCBWorkspaceService(self)
        from .design import EngineeringDesignService
        self.design = EngineeringDesignService(self.root)
        from .components import ComponentLibraryService
        self.components = ComponentLibraryService()
        from .engineering_lifecycle import EngineeringLifecycleService
        self.engineering_lifecycle = EngineeringLifecycleService(self)
        from .engineering_records.service import EngineeringRecordService
        self.engineering_records = EngineeringRecordService(self)
        from .engineering_reviews import EngineeringReviewService
        self.reviews = EngineeringReviewService(self)

    @contextmanager
    def connection(self):
        active = self._active_transaction.get()
        if active is not None:
            yield active
            return
        db = sqlite3.connect(self.database, timeout=30)
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA synchronous=NORMAL")
        try:
            with db:
                yield db
        except sqlite3.IntegrityError as exc:
            msg = str(exc)
            if "UNIQUE" in msg.upper():
                raise StudioError("CONFLICT", "Product code or revision label already exists") from exc
            if "FOREIGN KEY" in msg.upper():
                raise StudioError("NOT_FOUND", f"Referenced entity does not exist: {exc}") from exc
            raise StudioError("CONFLICT", f"Database integrity error: {exc}") from exc
        except sqlite3.Error as exc:
            raise StudioError("STORAGE_ERROR", str(exc)) from exc
        finally:
            db.close()

    @contextmanager
    def atomic(self):
        """Compose existing service operations in one task-local SQLite transaction."""
        if self._active_transaction.get() is not None:
            raise StudioError("CONFLICT", "An atomic operation is already active")
        with self.connection() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("PRAGMA synchronous=NORMAL")
            db.execute("BEGIN IMMEDIATE")
            token = self._active_transaction.set(db)
            try:
                yield db
            finally:
                self._active_transaction.reset(token)

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
        if not path.exists():
            for sub in ("reports", "pcb", "simulations", "mechanical", "circuit", "requirements", "bom"):
                candidate = (folder / sub / relative).resolve()
                if candidate.exists() and candidate.is_relative_to(folder):
                    path = candidate
                    break
        if relative.is_absolute() or not path.is_relative_to(folder) or not path.exists():
            raise StudioError("INVALID_INPUT", "Choose an existing file or folder inside this revision workspace")
        if path.is_file() and path.suffix.lower() not in NATIVE_EXTENSIONS:
            raise StudioError("INVALID_INPUT", "This file type cannot be launched from Studio; scripts and executables are excluded")
        try:
            open_native(path)
        except OSError as exc:
            raise StudioError("LAUNCH_ERROR", f"Could not open the file. Check the Windows file association: {exc}") from exc
        return str(path)

    def reveal_project_file(self, revision_id, relative_path="."):
        from .launch import reveal_in_explorer
        folder = self.workspace_path(self.get_revision(revision_id))
        relative = Path(relative_path)
        path = (folder / relative).resolve()
        if not path.exists():
            for sub in ("reports", "pcb", "simulations", "mechanical", "circuit", "requirements", "bom"):
                candidate = (folder / sub / relative).resolve()
                if candidate.exists() and candidate.is_relative_to(folder):
                    path = candidate
                    break
        if relative.is_absolute() or not path.is_relative_to(folder) or not path.exists():
            raise StudioError("INVALID_INPUT", "Choose an existing file or folder inside this revision workspace")
        reveal_in_explorer(path)
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



    def backup_database(self, destination=None):
        """Safely snapshot the SQLite engineering database using the online backup API."""
        if destination is None:
            ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            destination = self.root / ".mendex" / "backups" / f"studio_backup_{ts}.sqlite3"
        dest_path = Path(destination).resolve()
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as source:
            with sqlite3.connect(str(dest_path)) as target:
                source.backup(target)
        return dest_path

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

    def delete_product(self, product_id_or_code):
        try:
            product_uuid = UUID(str(product_id_or_code))
            product = self.get_product(product_uuid)
        except (ValueError, StudioError):
            with self.connection() as db:
                row = db.execute("SELECT id FROM products WHERE code=? COLLATE NOCASE", (str(product_id_or_code),)).fetchone()
            if not row:
                raise StudioError("NOT_FOUND", f"Product '{product_id_or_code}' not found")
            product_uuid = UUID(row[0])
            product = self.get_product(product_uuid)

        pid_str = str(product_uuid)
        with self.connection() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("PRAGMA synchronous=NORMAL")
            db.execute("BEGIN IMMEDIATE")
            rev_rows = db.execute("SELECT id, payload FROM revisions WHERE product_id=?", (pid_str,)).fetchall()
            rev_ids = [row[0] for row in rev_rows]
            # Frozen baselines and recorded evidence are immutable: only empty draft projects may be deleted.
            blockers = []
            for rid, payload in rev_rows:
                status = json.loads(payload).get("lifecycle_status", Lifecycle.DRAFT.value)
                if status != Lifecycle.DRAFT.value:
                    blockers.append(f"revision {rid} is {status}")
            evidence_queries = [
                ("runs", "SELECT COUNT(*) FROM runs WHERE revision_id=?"),
                ("validations", "SELECT COUNT(*) FROM validations WHERE revision_id=?"),
                ("reports", "SELECT COUNT(*) FROM reports WHERE revision_id=?"),
                ("lifecycle approvals", "SELECT COUNT(*) FROM lifecycle_approvals WHERE revision_id=?"),
                ("measurements", "SELECT COUNT(*) FROM measurements WHERE revision_id=?"),
                ("change requests", "SELECT COUNT(*) FROM engineering_change_requests WHERE revision_id=?"),
                ("engineering records", "SELECT COUNT(*) FROM engineering_records_entries WHERE revision_id=?"),
                ("lifecycle events", "SELECT COUNT(*) FROM engineering_lifecycle_events WHERE revision_id=?"),
                ("stage reviews", "SELECT COUNT(*) FROM engineering_stage_reviews WHERE revision_id=?"),
            ]
            for rid in rev_ids:
                for label, query in evidence_queries:
                    try:
                        count = db.execute(query, (rid,)).fetchone()[0]
                    except sqlite3.OperationalError:
                        continue  # table not created in this data root
                    if count:
                        blockers.append(f"revision {rid} has {count} {label}")
            if blockers:
                raise StudioError("DELETE_BLOCKED", "Product has frozen baselines or recorded evidence and cannot be deleted: " + "; ".join(blockers))
            for rid in rev_ids:
                db.execute("DELETE FROM validations WHERE revision_id=?", (rid,))
                db.execute("DELETE FROM reports WHERE revision_id=?", (rid,))
                db.execute("DELETE FROM runs WHERE revision_id=?", (rid,))
                try:
                    db.execute("DELETE FROM lifecycle_approvals WHERE revision_id=?", (rid,))
                except Exception:
                    pass
                try:
                    db.execute("DELETE FROM measurements WHERE revision_id=? OR product_id=?", (rid, pid_str))
                except Exception:
                    pass
                try:
                    db.execute("DELETE FROM engineering_change_requests WHERE revision_id=? OR product_id=?", (rid, pid_str))
                except Exception:
                    pass
                try:
                    db.execute("DELETE FROM engineering_lifecycle_events WHERE revision_id=?", (rid,))
                except Exception:
                    pass
                try:
                    db.execute("DELETE FROM engineering_lifecycle_assignments WHERE revision_id=?", (rid,))
                except Exception:
                    pass
                try:
                    db.execute("DELETE FROM engineering_records_receipts WHERE revision_id=?", (rid,))
                except Exception:
                    pass
                try:
                    db.execute("DELETE FROM engineering_records_entries WHERE revision_id=?", (rid,))
                except Exception:
                    pass
            try:
                db.execute("DELETE FROM integration_workspaces WHERE id=? OR product_id=?", (pid_str, pid_str))
            except Exception:
                pass
            try:
                db.execute("UPDATE activities SET product_id=NULL WHERE product_id=?", (pid_str,))
            except Exception:
                pass
            try:
                db.execute("UPDATE workflows SET product_id=NULL WHERE product_id=?", (pid_str,))
            except Exception:
                pass
            db.execute("DELETE FROM revisions WHERE product_id=?", (pid_str,))
            db.execute("DELETE FROM products WHERE id=?", (pid_str,))

        p_dir = (self.root / "products" / pid_str).resolve()
        if p_dir.is_relative_to(self.root / "products") and p_dir.exists():
            shutil.rmtree(p_dir, ignore_errors=True)
        return True

    def save_product_revision(self, product_id, revision_id, name, owner, description, specification):
        spec = Specification.model_validate(specification)
        with self.connection() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("PRAGMA synchronous=NORMAL")
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
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("PRAGMA synchronous=NORMAL")
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
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("PRAGMA synchronous=NORMAL")
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

    def list_plugins(self):
        return self.plugin_status

    def set_revision_status(self, revision_id, status):
        status = Lifecycle(status)
        if status not in (Lifecycle.DRAFT, Lifecycle.IN_REVIEW):
            raise StudioError("INVALID_INPUT", "Approval is not implemented. Archive a baseline by creating its next revision.")
        with self.connection() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("PRAGMA synchronous=NORMAL")
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
                if not db.in_transaction:
                    db.execute("PRAGMA journal_mode=WAL")
                    db.execute("PRAGMA synchronous=NORMAL")
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
        jobs = [self.engineering_records.job_detail(j.request.job_id)
                for j in self.integrations.list_jobs()
                if j.request.parameters.get("revision_id") == str(revision.revision_id)]
        warnings = ["DRAFT ONLY: no manufacturing approval or safety certification.",
                    "Manual values and criteria are supplied by the reviewer; their engineering validity is not independently verified.",
                    "Physical test origin and engineering review are not authenticated by Mendex.",
                    f"{len(jobs)} native job records attributed to this revision; execution is not engineering validation."]
        if any(not job["evidence_integrity"] for job in jobs):
            warnings.append("NOT_EVALUATED: one or more attributed job evidence manifests are unavailable or changed.")
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
        snapshot["native_jobs"] = jobs
        snapshot["calculation_runs"] = self.engineering_records.list_records("calculation", {"revision_id": revision_id})
        snapshot["registered_artifacts"] = self.engineering_records.list_records("artifact", {"revision_id": revision_id})
        text = json.dumps(snapshot, indent=2)
        p_out_w = revision.specification.vout_v * revision.specification.iout_a if revision.specification.vout_v is not None and revision.specification.iout_a is not None else None
        f_sw_khz = revision.specification.switching_frequency_hz / 1000 if revision.specification.switching_frequency_hz is not None else None

        def display_quantity(value, unit, digits=1):
            return f"{value:.{digits}f} {unit}" if value is not None else "NOT_EVALUATED"
        body = f'''<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Mendex Engineering Dossier — {html.escape(product.code)} ({html.escape(revision.revision_label)})</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; max-width: 1040px; margin: 24px auto; padding: 24px; color: #1e1e2e; background-color: #f8fafc; line-height: 1.5; }}
  .header-card {{ background: linear-gradient(135deg, #1e1e2e 0%, #2a2b3d 100%); color: #cdd6f4; border-radius: 10px; padding: 20px 24px; margin-bottom: 24px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }}
  .print-btn {{ float: right; background: #0ea5e9; color: #ffffff; border: none; padding: 8px 16px; border-radius: 6px; font-weight: 700; cursor: pointer; text-decoration: none; }}
  .print-btn:hover {{ background: #0284c7; }}
  .card {{ background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 18px; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }}
  .kpi-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin: 16px 0; }}
  .kpi-item {{ background: #f1f5f9; border: 1px solid #e2e8f0; border-radius: 6px; padding: 12px; text-align: center; }}
  .kpi-val {{ font-size: 20px; font-weight: 800; color: #0284c7; }}
  .kpi-lbl {{ font-size: 11px; font-weight: 700; text-transform: uppercase; color: #64748b; margin-top: 4px; }}
  table {{ border-collapse: collapse; width: 100%; margin: 12px 0 20px 0; font-size: 14px; }}
  th {{ background: #f1f5f9; color: #334155; font-weight: 700; text-align: left; padding: 10px 12px; border: 1px solid #cbd5e1; }}
  td {{ padding: 8px 12px; border: 1px solid #e2e8f0; color: #1e293b; }}
  tr:nth-child(even) {{ background: #f8fafc; }}
  pre {{ background: #1e1e2e; color: #a6adc8; padding: 14px; border-radius: 6px; overflow-x: auto; font-size: 12px; white-space: pre-wrap; overflow-wrap: anywhere; }}
  .badge-pass {{ display: inline-block; padding: 3px 8px; border-radius: 4px; font-weight: 700; background: #dcfce7; color: #15803d; border: 1px solid #86efac; font-size: 12px; }}
  .badge-blocked {{ display: inline-block; padding: 3px 8px; border-radius: 4px; font-weight: 700; background: #fee2e2; color: #b91c1c; border: 1px solid #fca5a5; font-size: 12px; }}
  .warning-box {{ background: #fffbeb; border: 1px solid #fef3c7; border-left: 4px solid #f59e0b; padding: 12px 16px; border-radius: 4px; margin-bottom: 20px; }}
  .warning-box li {{ color: #92400e; margin: 4px 0; font-size: 13px; }}
  @media print {{
    .print-btn {{ display: none; }}
    body {{ max-width: 100%; margin: 0; padding: 12px; background: #ffffff; color: #000; }}
    .card, .header-card {{ box-shadow: none; border: 1px solid #ccc; page-break-inside: avoid; }}
  }}
</style>
</head>
<body>
<div class="header-card">
  <button onclick="window.print()" class="print-btn">🖨️ Print / Save as PDF</button>
  <h1 style="margin:0 0 6px 0; font-size:24px; color:#ffffff;">Mendex Engineering Dossier · {html.escape(product.code)}</h1>
  <p style="margin:0; font-size:14px; color:#a6adc8;">Mendex engineering dossier | <b>Product Name:</b> {html.escape(product.name)} | <b>Revision:</b> {html.escape(revision.revision_label)} | <b>Generated:</b> {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}</p>
</div>
<div class="card">
  <h2 style="margin-top:0;">1. Executive Summary & Design Envelope</h2>
  <table style="width:100%; border:none; margin:14px 0; border-collapse:separate; border-spacing:10px;">
    <tr>
      <td style="background:#f1f5f9; border:1px solid #cbd5e1; border-radius:6px; padding:14px; text-align:center; width:33%;">
        <div style="font-size:22px; font-weight:800; color:#0284c7;">{display_quantity(revision.specification.vin_nom_v, 'V')}</div>
        <div style="font-size:11px; font-weight:700; color:#64748b; text-transform:uppercase; margin-top:4px;">Input Voltage (Nom)</div>
      </td>
      <td style="background:#f1f5f9; border:1px solid #cbd5e1; border-radius:6px; padding:14px; text-align:center; width:33%;">
        <div style="font-size:22px; font-weight:800; color:#0284c7;">{display_quantity(revision.specification.vout_v, 'V')}</div>
        <div style="font-size:11px; font-weight:700; color:#64748b; text-transform:uppercase; margin-top:4px;">Output Voltage</div>
      </td>
      <td style="background:#f1f5f9; border:1px solid #cbd5e1; border-radius:6px; padding:14px; text-align:center; width:33%;">
        <div style="font-size:22px; font-weight:800; color:#0284c7;">{display_quantity(p_out_w, 'W')}</div>
        <div style="font-size:11px; font-weight:700; color:#64748b; text-transform:uppercase; margin-top:4px;">Nominal Output Power</div>
      </td>
    </tr>
    <tr>
      <td style="background:#f1f5f9; border:1px solid #cbd5e1; border-radius:6px; padding:14px; text-align:center; width:33%;">
        <div style="font-size:22px; font-weight:800; color:#0284c7;">{display_quantity(f_sw_khz, 'kHz')}</div>
        <div style="font-size:11px; font-weight:700; color:#64748b; text-transform:uppercase; margin-top:4px;">Switching Frequency</div>
      </td>
      <td style="background:#f1f5f9; border:1px solid #cbd5e1; border-radius:6px; padding:14px; text-align:center; width:33%;">
        <div style="font-size:16px; font-weight:800; color:#0284c7;">{html.escape(revision.specification.isolation_requirement or 'NOT_EVALUATED')}</div>
        <div style="font-size:11px; font-weight:700; color:#64748b; text-transform:uppercase; margin-top:4px;">Isolation Requirement</div>
      </td>
      <td style="background:#f1f5f9; border:1px solid #cbd5e1; border-radius:6px; padding:14px; text-align:center; width:33%;">
        <div style="font-size:16px; font-weight:800; color:#0284c7;">{html.escape(revision.specification.standards_profile if revision.specification.standards_profile != 'UNASSIGNED' else 'NOT_EVALUATED')}</div>
        <div style="font-size:11px; font-weight:700; color:#64748b; text-transform:uppercase; margin-top:4px;">Standards Profile</div>
      </td>
    </tr>
  </table>
</div>
<div class="warning-box">
  <b>Engineering Notices & Provenance Safeguards:</b>
  <ul style="margin:6px 0 0 0; padding-left:20px;">
    {''.join(f'<li>{html.escape(w)}</li>' for w in warnings)}
  </ul>
</div>
<h2>Frozen input and evidence snapshot</h2><pre>{html.escape(text)}</pre></body></html>'''
        table = '<h2>Manual validation history</h2><table border="1" cellpadding="8" style="border-collapse:collapse"><tr><th>Requirement</th><th>Effective status</th><th>Origin</th><th>Value</th><th>Reviewer</th></tr>'
        for row in rows:
            check = row["record"]["check"]
            values = [row["check_id"], row["effective_status"], check["evidence_kind"], f'{check["measured_value"]} {check["unit"]}' if check["measured_value"] is not None else "Unavailable", check["reviewer"]]
            table += '<tr>' + ''.join(f'<td>{html.escape(str(value))}</td>' for value in values) + '</tr>'
        table += '</table><p>Entries are historical assessments, not a consolidated product approval.</p>'
        
        # If lifecycle engine is present and available, enrich report with complete lifecycle assessment & evidence register
        lifecycle_html = ""
        if hasattr(self, "lifecycle"):
            try:
                assessment = self.lifecycle.assess(product.product_id, revision.revision_id)
                evidence = self.lifecycle.get_evidence_register(product.product_id, revision.revision_id)
                status_color = "#1b4332" if assessment.prototype_ready else "#4a1525"
                status_text = "Legacy readiness assessment; no fabrication authorization" if assessment.prototype_ready else "PROTOTYPE BLOCKED"
                lifecycle_html += f"<h2>Product Engineering Lifecycle Maturity & Prototype Readiness</h2>"
                lifecycle_html += f"<p style='font-size:16px;font-weight:bold;color:{status_color};'>Overall Status: {html.escape(assessment.overall_status.value)} — {status_text}</p>"
                lifecycle_html += "<table border='1' cellpadding='8' style='border-collapse:collapse;width:100%;margin-bottom:20px;'>"
                lifecycle_html += "<tr style='background:#f1f3f5;'><th>Stage #</th><th>Stage Name</th><th>Status</th><th>Evidence Records</th><th>Blockers</th></tr>"
                for s_key, s_eval in assessment.stages.items():
                    blk_str = "; ".join(s_eval.blockers) if s_eval.blockers else "None"
                    lifecycle_html += f"<tr><td>#{s_eval.category_number}</td><td>{html.escape(s_eval.title)}</td><td><b>{html.escape(s_eval.status.value)}</b></td><td>{len(s_eval.evidence_records)}</td><td>{html.escape(blk_str)}</td></tr>"
                lifecycle_html += "</table>"
                if evidence:
                    lifecycle_html += f"<h2>Unified Cryptographic Evidence Register ({len(evidence)} Artifacts)</h2>"
                    lifecycle_html += "<table border='1' cellpadding='6' style='border-collapse:collapse;width:100%;font-size:13px;margin-bottom:20px;'>"
                    lifecycle_html += "<tr style='background:#f1f3f5;'><th>Stage</th><th>Artifact Type</th><th>Source Tool</th><th>File Name</th><th>Size (B)</th><th>SHA-256 Digest</th><th>Validation</th></tr>"
                    for rec in evidence:
                        h_short = (rec.sha256[:16] + "...") if rec.sha256 else "N/A"
                        lifecycle_html += f"<tr><td>{html.escape(rec.stage_id.value)}</td><td>{html.escape(rec.artifact_type.value)}</td><td>{html.escape(rec.source_tool)}</td><td>{html.escape(rec.source_file)}</td><td>{rec.file_size_bytes}</td><td><code>{html.escape(h_short)}</code></td><td>{html.escape(rec.validation_result)}</td></tr>"
                    lifecycle_html += "</table>"
            except Exception:
                pass

                # Enrich report with Sizing Analysis and BOM tables if available in workspace
        sizing_html = ''
        ws_p = self.workspace_path(revision)
        sizing_files = list(ws_p.glob('**/*sizing*.json')) + list(ws_p.glob('**/*calc*.json'))
        if sizing_files:
            candidate = sizing_files[0].resolve()
            if candidate.is_relative_to(ws_p.resolve()) and candidate.is_file() and candidate.stat().st_size <= 2 * 1024 * 1024:
                try:
                    s_data = json.loads(candidate.read_text(encoding="utf-8"))
                    sizing_html = '<div class="card"><h2>2. Recorded Analytical Inputs and Outputs</h2>'
                    sizing_html += '<p>Workspace-supplied content; source and applicability are not independently verified. Missing values remain unavailable.</p>'
                    sizing_html += '<p>Source: ' + html.escape(candidate.relative_to(ws_p).as_posix()) + '</p>'
                    sizing_html += '<pre>' + html.escape(json.dumps(s_data, indent=2, allow_nan=False)) + '</pre></div>'
                except (OSError, ValueError):
                    sizing_html = '<p>Analytical workspace data: NOT_EVALUATED (unreadable or malformed).</p>'

        bom_html = ''
        bom_files = list(ws_p.glob('**/*bom*.csv'))
        if bom_files:
            candidate = bom_files[0].resolve()
            if candidate.is_relative_to(ws_p.resolve()) and candidate.is_file() and candidate.stat().st_size <= 2 * 1024 * 1024:
                try:
                    with candidate.open(encoding="utf-8", newline="") as handle:
                        rows_b = list(csv.DictReader(handle))
                    if rows_b:
                        bom_html = '<div class="card"><h2>3. Recorded Bill of Materials</h2><p>Caller-supplied records; stock, ratings, prices and qualification are not independently verified.</p>'
                        fields = ("item", "designator", "part_number", "manufacturer", "description", "qty", "extended_price_usd", "status")
                        bom_html += '<table><tr>' + ''.join('<th>' + html.escape(field) + '</th>' for field in fields) + '</tr>'
                        for row in rows_b:
                            bom_html += '<tr>' + ''.join('<td>' + html.escape(str(row.get(field) or "NOT_EVALUATED")) + '</td>' for field in fields) + '</tr>'
                        bom_html += '</table></div>'
                except (OSError, ValueError, csv.Error):
                    bom_html = '<p>BOM data: NOT_EVALUATED (unreadable or malformed).</p>'

        body = body.replace('<h2>Frozen input and evidence snapshot</h2>', sizing_html + bom_html + '<div class="card">' + table + '</div>' + '<div class="card">' + lifecycle_html + '</div>' + '<h2>Frozen input and evidence snapshot</h2>')
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
                db.execute("PRAGMA journal_mode=WAL")
                db.execute("PRAGMA synchronous=NORMAL")
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

    def execute_workflow(self, workflow, workspace_id=None, timeout_s=300.0, progress_callback=None, cancel_token=None):
        return self.workflow_engine.execute_workflow(workflow, workspace_id=workspace_id, timeout_s=timeout_s, progress_callback=progress_callback, cancel_token=cancel_token)

    def list_workflows(self, workspace_id=None):
        return self.workflows.list_workflows(workspace_id)

    def get_workflow(self, workflow_id):
        return self.workflows.get_workflow(workflow_id)

    def save_workflow(self, workflow):
        return self.workflows.save_workflow(workflow)

    def delete_workflow(self, workflow_id):
        return self.workflows.delete_workflow(workflow_id)
