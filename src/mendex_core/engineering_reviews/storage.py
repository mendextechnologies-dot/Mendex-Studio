"""Backed-up opt-in engineering review tables and reviewer credentials."""
import hashlib
import json
import os
from ..engineering_lifecycle.storage import backup_before_migration
from ..models import now
from ..service import StudioError

TABLES = ("engineering_reviewers", "engineering_reviews", "engineering_review_receipts")


def hash_secret(secret: str, salt: str | None = None) -> tuple[str, str]:
    if salt is None:
        salt = os.urandom(16).hex()
    hashed = hashlib.pbkdf2_hmac("sha256", secret.encode("utf-8"), salt.encode("utf-8"), 100_000).hex()
    return hashed, salt


def verify_secret(secret: str, salt: str, expected_hash: str) -> bool:
    hashed = hashlib.pbkdf2_hmac("sha256", secret.encode("utf-8"), salt.encode("utf-8"), 100_000).hex()
    return hashed == expected_hash


def installed(db) -> bool:
    if not db.execute("SELECT 1 FROM sqlite_master WHERE name='engineering_reviews_schema' AND type='table'").fetchone():
        if any(db.execute("SELECT 1 FROM sqlite_master WHERE name=?", (name,)).fetchone() for name in TABLES):
            raise StudioError("STORAGE_ERROR", "Incomplete engineering review schema")
        return False
    if db.execute("SELECT version FROM engineering_reviews_schema").fetchall() != [(1,)]:
        raise StudioError("STORAGE_ERROR", "Unsupported engineering review schema")
    if not all(db.execute("SELECT 1 FROM sqlite_master WHERE name=? AND type='table'", (name,)).fetchone() for name in TABLES):
        raise StudioError("STORAGE_ERROR", "Incomplete engineering review schema")
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
        db.execute("CREATE TABLE engineering_reviews_schema(version INTEGER PRIMARY KEY CHECK(version=1), backup_path TEXT NOT NULL)")
        
        # 1. Authorized human reviewers with salted secret credentials
        db.execute("""
            CREATE TABLE engineering_reviewers(
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                roles TEXT NOT NULL,
                secret_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        
        # 2. Immutable, append-only human review decisions
        db.execute("""
            CREATE TABLE engineering_reviews(
                sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                id TEXT NOT NULL UNIQUE,
                project_id TEXT NOT NULL REFERENCES products(id),
                revision_id TEXT NOT NULL REFERENCES revisions(id),
                stage_id TEXT NOT NULL,
                attempt INTEGER NOT NULL,
                requirements_record_id TEXT,
                requirements_digest TEXT NOT NULL,
                specification_hash TEXT NOT NULL,
                document_hashes TEXT NOT NULL,
                evidence_hashes TEXT NOT NULL,
                conflicts TEXT NOT NULL,
                deferrals TEXT NOT NULL,
                submitter TEXT NOT NULL,
                reviewer_id TEXT NOT NULL REFERENCES engineering_reviewers(id),
                decision TEXT NOT NULL CHECK(decision IN ('APPROVED', 'REJECTED', 'CHANGES_REQUESTED')),
                comments TEXT NOT NULL,
                signature TEXT NOT NULL,
                idempotency_key TEXT NOT NULL,
                created_at TEXT NOT NULL,
                payload TEXT NOT NULL
            )
        """)
        db.execute("CREATE INDEX engineering_reviews_lookup ON engineering_reviews(revision_id, stage_id, attempt, sequence)")

        # 3. Idempotent receipts
        db.execute("""
            CREATE TABLE engineering_review_receipts(
                scope TEXT NOT NULL,
                request_key TEXT NOT NULL,
                operation TEXT NOT NULL,
                request_digest TEXT NOT NULL,
                response TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY(scope, request_key)
            )
        """)

        # 4. Triggers to enforce append-only immutability
        for table in ("engineering_reviews", "engineering_reviews_schema"):
            for op in ("UPDATE", "DELETE"):
                db.execute(f"CREATE TRIGGER {table}_no_{op.lower()} BEFORE {op} ON {table} BEGIN SELECT RAISE(ABORT, 'Engineering review records are append-only'); END")
        
        db.execute("CREATE TRIGGER engineering_reviewers_no_delete BEFORE DELETE ON engineering_reviewers BEGIN SELECT RAISE(ABORT, 'Reviewer registry is append-only'); END")

        db.execute("INSERT INTO engineering_reviews_schema VALUES(1,?)", (backup,))
