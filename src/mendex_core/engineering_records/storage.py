"""Backed-up opt-in record tables, separate from the immutable lifecycle schema."""
from ..engineering_lifecycle.storage import backup_before_migration
from ..service import StudioError

TABLES = ("engineering_records_entries", "engineering_records_receipts")


def installed(db):
    if not db.execute("SELECT 1 FROM sqlite_master WHERE name='engineering_records_schema' AND type='table'").fetchone():
        if any(db.execute("SELECT 1 FROM sqlite_master WHERE name=?", (name,)).fetchone() for name in TABLES):
            raise StudioError("STORAGE_ERROR", "Incomplete engineering record schema")
        return False
    if db.execute("SELECT version FROM engineering_records_schema").fetchall() != [(1,)]:
        raise StudioError("STORAGE_ERROR", "Unsupported engineering record schema")
    if not all(db.execute("SELECT 1 FROM sqlite_master WHERE name=? AND type='table'", (name,)).fetchone() for name in TABLES):
        raise StudioError("STORAGE_ERROR", "Incomplete engineering record schema")
    return True


def initialize(studio):
    with studio.connection() as db:
        if installed(db):
            return
    backup = backup_before_migration(studio)
    with studio.connection() as db:
        db.execute("BEGIN IMMEDIATE")
        if installed(db):
            return
        db.execute("CREATE TABLE engineering_records_schema(version INTEGER PRIMARY KEY CHECK(version=1), backup_path TEXT NOT NULL)")
        db.execute("CREATE TABLE engineering_records_entries(sequence INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT NOT NULL UNIQUE, revision_id TEXT NOT NULL REFERENCES revisions(id), kind TEXT NOT NULL, stage_id TEXT NOT NULL, payload TEXT NOT NULL, digest TEXT NOT NULL)")
        db.execute("CREATE INDEX engineering_records_revision ON engineering_records_entries(revision_id,kind,sequence)")
        db.execute("CREATE TABLE engineering_records_receipts(scope TEXT NOT NULL, request_key TEXT NOT NULL, operation TEXT NOT NULL, request_digest TEXT NOT NULL, response TEXT NOT NULL, source TEXT NOT NULL, reason TEXT NOT NULL, created_at TEXT NOT NULL, PRIMARY KEY(scope,request_key))")
        for table in (*TABLES, "engineering_records_schema"):
            for operation in ("UPDATE", "DELETE"):
                db.execute(f"CREATE TRIGGER {table}_no_{operation.lower()} BEFORE {operation} ON {table} BEGIN SELECT RAISE(ABORT,'Engineering records are append-only'); END")
        db.execute("INSERT INTO engineering_records_schema VALUES(1,?)", (backup,))
