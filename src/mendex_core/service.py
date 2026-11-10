import shutil
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from uuid import UUID, uuid4

from .models import Category, Lifecycle, Product, Revision, Specification, now


class StudioError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


class StudioService:
    def __init__(self, root: Path):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        metadata = self.root / ".mendex"
        metadata.mkdir(exist_ok=True)
        self.database = metadata / "studio.sqlite3"
        with self.connection() as db:
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version > 1:
                raise StudioError("STORAGE_ERROR", "Database is newer than this application")
            if version == 0:
                db.executescript('''
                    CREATE TABLE products (id TEXT PRIMARY KEY, code TEXT UNIQUE COLLATE NOCASE, payload TEXT NOT NULL);
                    CREATE TABLE revisions (id TEXT PRIMARY KEY, product_id TEXT NOT NULL REFERENCES products(id), label TEXT NOT NULL COLLATE NOCASE, payload TEXT NOT NULL, UNIQUE(product_id,label));
                    PRAGMA user_version=1;
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
