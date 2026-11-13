"""Opt-in additive component migration, with a consistent pre-change SQLite backup."""
import hashlib
import json
import sqlite3
from pathlib import Path
from uuid import uuid4

from ..models import now
from ..service import StudioError

PREFIX = "engineering_lifecycle_"
TABLES = ("definitions", "assignments", "events")


def installed(db):
    exists = db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (PREFIX + "schema",)).fetchone()
    if not exists:
        if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name LIKE ?", (PREFIX + "%",)).fetchone():
            raise StudioError("STORAGE_ERROR", "Incomplete lifecycle component schema")
        return False
    versions = db.execute("SELECT version FROM engineering_lifecycle_schema").fetchall()
    if versions != [(1,)]:
        raise StudioError("STORAGE_ERROR", "Unsupported lifecycle component schema")
    for table in TABLES:
        if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (PREFIX + table,)).fetchone():
            raise StudioError("STORAGE_ERROR", "Incomplete lifecycle component schema")
    return True


def file_hash(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def backup_before_migration(service):
    """Backup metadata and hash existing artifacts. Never change original evidence."""
    folder = service.root / ".mendex" / "backups" / ("lifecycle-" + str(uuid4()))
    if not folder.resolve().is_relative_to(service.root):
        raise StudioError("STORAGE_ERROR", "Backup directory escapes data root")
    folder.mkdir(parents=True, exist_ok=False)
    backup_path = folder / "studio.sqlite3"
    with sqlite3.connect(service.database.as_uri() + "?mode=ro", uri=True) as source:
        with sqlite3.connect(backup_path) as target:
            source.backup(target)
            if target.execute("PRAGMA quick_check").fetchall() != [("ok",)]:
                raise StudioError("STORAGE_ERROR", "Pre-migration backup verification failed")
    hashes = {}
    for name in ("products", "workspaces", "engineering_designs", "reports", ".mendex"):
        base = service.root / name
        if not base.exists():
            continue
        if not base.resolve().is_relative_to(service.root):
            raise StudioError("STORAGE_ERROR", "Artifact manifest directory escapes data root")
        # Walk without following directory symlinks; refuse external file references.
        for directory, dirs, files in base.walk(follow_symlinks=False):
            dirs[:] = [d for d in dirs if not (directory == service.root / ".mendex" and d == "backups")]
            for filename in files:
                path = directory / filename
                if path.parent == service.database.parent and filename in ("studio.sqlite3", "studio.sqlite3-wal", "studio.sqlite3-shm", "studio.sqlite3-journal"):
                    continue
                if not path.resolve().is_relative_to(service.root):
                    raise StudioError("STORAGE_ERROR", "Artifact manifest path escapes data root")
                hashes[path.relative_to(service.root).as_posix()] = file_hash(path)
    manifest = {"created_at": now().isoformat(), "database_sha256": file_hash(backup_path),
                "artifact_hashes": hashes, "note": "Artifacts are unchanged originals, not copied by this schema-only migration."}
    (folder / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return folder.relative_to(service.root).as_posix()


def initialize(service):
    with service.connection() as db:
        if installed(db):
            return
    backup = backup_before_migration(service)
    with service.connection() as db:
        db.execute("BEGIN IMMEDIATE")
        if installed(db):
            return
        statements = [
            "CREATE TABLE engineering_lifecycle_schema (version INTEGER PRIMARY KEY CHECK(version=1), backup_path TEXT NOT NULL)",
            "CREATE TABLE engineering_lifecycle_definitions (id TEXT NOT NULL, version TEXT NOT NULL, digest TEXT NOT NULL, payload TEXT NOT NULL, source TEXT NOT NULL, created_at TEXT NOT NULL, PRIMARY KEY(id,version))",
            "CREATE TABLE engineering_lifecycle_assignments (id TEXT PRIMARY KEY, revision_id TEXT NOT NULL UNIQUE REFERENCES revisions(id), definition_id TEXT NOT NULL, definition_version TEXT NOT NULL, created_at TEXT NOT NULL, FOREIGN KEY(definition_id,definition_version) REFERENCES engineering_lifecycle_definitions(id,version))",
            "CREATE TABLE engineering_lifecycle_events (sequence INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT NOT NULL UNIQUE, assignment_id TEXT NOT NULL REFERENCES engineering_lifecycle_assignments(id), stage_id TEXT, request_key TEXT NOT NULL, request_digest TEXT NOT NULL, payload TEXT NOT NULL, UNIQUE(assignment_id,request_key))",
            "CREATE INDEX engineering_lifecycle_events_assignment ON engineering_lifecycle_events(assignment_id,sequence)",
        ]
        for statement in statements:
            db.execute(statement)
        for table in (*TABLES, "schema"):
            for operation in ("UPDATE", "DELETE"):
                db.execute(f"CREATE TRIGGER {PREFIX}{table}_no_{operation.lower()} BEFORE {operation} ON {PREFIX}{table} BEGIN SELECT RAISE(ABORT,'Lifecycle records are append-only'); END")
        db.execute("INSERT INTO engineering_lifecycle_schema VALUES(1,?)", (backup,))
        # Global user_version remains unchanged: old v4 readers still work.
