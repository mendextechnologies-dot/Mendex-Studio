"""Archive old data without deleting records or disabling immutable protections."""
import argparse
import hashlib
import json
import os
import shutil
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4
from mendex_core.service import StudioService

ROOT = Path(__file__).resolve().parents[1]
DIRECTORIES = (".mendex", "products", "engineering_designs", "workspaces", "reports", "temp_femm_test")
SETTINGS = {"tool_settings": ("tool_id", "path"), "integration_settings": ("tool_id", "payload")}
TABLES = ("products", "revisions", "validations", "reports", "runs", "integration_jobs", "integration_workspaces", "activities", "workflows", "workflow_runs", "lifecycle_approvals", "engineering_change_requests", "measurements", "engineering_lifecycle_assignments", "engineering_lifecycle_events", "engineering_records_entries", "engineering_records_receipts")

def io_path(path):
    # Preserve long Windows evidence paths after adding an archive directory prefix.
    text = str(path)
    return Path("\\\\?\\" + text) if os.name == "nt" and not text.startswith("\\\\?\\") and not text.startswith("\\\\") else path

def checksum(path):
    with io_path(path).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()

def checked(path, root):
    if path.is_symlink() or path.is_junction() or path.resolve() != path or not path.is_relative_to(root) or path == root:
        raise ValueError("Reset path escapes or redirects its boundary: " + str(path))
    return path

def move(source, target, root):
    checked(source, root)
    checked(target, root)
    if target.exists():
        raise FileExistsError("Archive never overwrites: " + str(target))
    target.parent.mkdir(parents=True, exist_ok=True)
    source.rename(target)

def hashes(root, directories):
    result = {}
    for name in directories:
        base = checked(root / name, root)
        if not base.exists():
            continue
        def fail(error):
            raise error
        walking = io_path(base)
        for directory, children, files in walking.walk(follow_symlinks=False, on_error=fail):
            normal = base / directory.relative_to(walking)
            for child in children:
                checked(normal / child, root)
            for name in files:
                path = checked(normal / name, root)
                result[path.relative_to(root).as_posix()] = {"sha256": checksum(path), "size": io_path(path).stat().st_size}
    return result

def counts(db):
    names = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    return {t: db.execute('SELECT COUNT(*) FROM "' + t + '"').fetchone()[0] if t in names else 0 for t in TABLES}

def inspect(root):
    root = Path(root).resolve()
    database = checked(root / ".mendex" / "studio.sqlite3", root)
    if not database.is_file():
        raise FileNotFoundError("No active database at " + str(root))
    with closing(sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)) as db:
        if db.execute("PRAGMA quick_check").fetchall() != [("ok",)]:
            raise ValueError("Database integrity failed; reset aborted")
        names = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        running = db.execute("SELECT COUNT(*) FROM integration_jobs WHERE status IN ('QUEUED','RUNNING')").fetchone()[0] if "integration_jobs" in names else 0
        settings = {t: db.execute("SELECT " + ",".join(cols) + " FROM " + t + " ORDER BY tool_id").fetchall() for t, cols in SETTINGS.items() if t in names}
        return {"root": str(root), "counts": counts(db), "running_jobs": running, "settings": settings}

def archive_and_remove(root=ROOT):
    root = Path(root).resolve()
    before = inspect(root)
    if before["running_jobs"]:
        raise ValueError("Running/queued solver jobs exist; wait before reset")
    base = checked(root / ".mendex-archives", root)
    stamp = datetime.now(timezone(timedelta(hours=5, minutes=30))).strftime("%Y%m%d_%H%M%S")
    archive = checked(base / ("reset_" + stamp + "_" + uuid4().hex[:8]), root)
    archive.mkdir(parents=True, exist_ok=False)
    originals, staged = archive / "originals", archive / "new-active-state"
    originals.mkdir()
    staged.mkdir()
    manifest = hashes(root, DIRECTORIES)
    backup = archive / "database-backup.sqlite3"
    database = root / ".mendex" / "studio.sqlite3"
    with closing(sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)) as source, closing(sqlite3.connect(backup)) as target:
        source.backup(target)
        if target.execute("PRAGMA quick_check").fetchall() != [("ok",)] or counts(target) != before["counts"]:
            raise ValueError("Backup verification failed; originals untouched")
    fresh = StudioService(staged)
    with fresh.connection() as db:
        for table, rows in before["settings"].items():
            cols = SETTINGS[table]
            db.executemany("INSERT INTO " + table + "(" + ",".join(cols) + ") VALUES(" + ",".join("?" for _ in cols) + ")", rows)
        if any(counts(db).values()):
            raise ValueError("Fresh database is not empty")
    preferences = root / ".mendex" / "ui_preferences.json"
    if preferences.exists():
        shutil.copy2(checked(preferences, root), staged / ".mendex" / preferences.name)
    plugins = root / ".mendex" / "plugins"
    if plugins.exists():
        shutil.copytree(checked(plugins, root), staged / ".mendex" / "plugins")
    for name in DIRECTORIES:
        (staged / name).mkdir(parents=True, exist_ok=True)
    (archive / "manifest.json").write_text(json.dumps({"timestamp": datetime.now(timezone(timedelta(hours=5, minutes=30))).isoformat(), "original_root": str(root), "counts_before": before["counts"], "files": manifest, "database_backup_sha256": checksum(backup), "restore": "Stop clients; archive current directories separately, then move originals/<name> back. Never merge or overwrite datasets."}, indent=2), encoding="utf-8")
    moved, installed = [], []
    try:
        for name in DIRECTORIES:
            if (root / name).exists():
                move(root / name, originals / name, root)
                moved.append(name)
        for name in DIRECTORIES:
            move(staged / name, root / name, root)
            installed.append(name)
        if hashes(originals, moved) != manifest:
            raise ValueError("Archived checksums differ; restoring originals")
        after = inspect(root)
        if any(after["counts"].values()) or after["settings"] != before["settings"]:
            raise ValueError("Reset verification failed; restoring originals")
        result = {"status": "RESET_COMPLETE", "archive": str(archive), "counts_before": before["counts"], "counts_after": after["counts"], "verified_archived_files": len(manifest), "originals_deleted": False, "settings_preserved": True}
        (archive / "reset-result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        return result
    except Exception:
        for name in reversed(installed):
            move(root / name, archive / "failed-new-state" / name, root)
        for name in reversed(moved):
            move(originals / name, root / name, root)
        raise

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--preview", action="store_true")
    args = parser.parse_args()
    result = inspect(args.root) if args.preview else archive_and_remove(args.root)
    if args.preview:
        result = {k: v for k, v in result.items() if k != "settings"}
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
