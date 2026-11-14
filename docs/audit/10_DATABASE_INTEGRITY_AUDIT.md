# 10 — Database Integrity Audit (independent, 2026-11-14)

Audit only. Live tests ran exclusively against `%TEMP%\mendex-audit3\core\{db1,db2,conc,kill,mig,mig_v1,mig_v9,ctl}`.
The repo DB was only copied read-only (`sqlite3 ... ?mode=ro` + `backup()`) in `mig.py`.
Note: the repo `.mendex/studio.sqlite3` mtime changed to 11:27:20 while my pytest run was active; several other
python processes (other auditors/app) were running, and my run did not include `tests/command_center`. Attribution NOT VERIFIED.
However `tests/command_center/test_react_command_center.py:54,62` constructs `MendexEngineeringController()` with the
**default (real) data root** and deletes a project there — a test that writes to user data.

## 1. Schema & versioning

* Core store: single SQLite file `<root>/.mendex/studio.sqlite3`, `journal_mode=delete` (no WAL), `timeout=10`.
* `PRAGMA user_version` = 4. Migrations v1-v4 inline in `service.py:44-79` (`BEGIN IMMEDIATE` held across checks), v4 in
  `integration_store.py:4-14`. `migrate_v5` (`integration_store.py:17-59`) is applied on **every** start because
  `user_version=5` is commented out (`:59`); it is idempotent but nested `with db:` commits the outer IMMEDIATE transaction early.
* Opt-in sub-schemas with own version tables + pre-migration verified backups (`engineering_lifecycle/storage.py:35-92`,
  `engineering_records/storage.py:21-36`, `engineering_reviews/storage.py:45-107`).
* Lazily created tables without versioning: `lifecycle_approvals` (`lifecycle/engine.py:76-92`, errors swallowed),
  `measurements`, `engineering_change_requests`, `workflows`, `workflow_runs`.
* Fresh DB: 17 tables, 4 triggers. Repo copy: 29 tables, 23 triggers, `integrity_check=ok`, `foreign_key_check` = 0 rows.
* IDs: UUID4 text PKs; product `code` UNIQUE NOCASE; `(product_id,label)` UNIQUE.
* FKs: declared on revisions, validations, reports, runs, approvals, records, lifecycle tables. `PRAGMA foreign_keys` is
  OFF by default and only enabled per-connection in `StudioService.connection()` (`service.py:116`). `workflows/storage.py`
  opens its own connections — FK enforcement there NOT VERIFIED.

## 2. Findings (severity-ranked)

| # | Sev | Finding | Evidence |
|---|-----|---------|----------|
| D1 | HIGH | `lifecycle_approvals` has no immutability triggers. Raw `UPDATE lifecycle_approvals SET passed=1` and `DELETE` succeeded. API is append-only but "latest wins" (`get_stage_approvals`), accepts empty reviewer `""`, accepts approvals on IN_REVIEW revisions, and is not invalidated when the revision returns to DRAFT and the spec is edited (`set_revision_status` allows IN_REVIEW->DRAFT, `service.py:475-489`). | `db2.py` output: "approval on in_review -> OK", "approval override FAIL -> OK", "RAW UPDATE/DELETE lifecycle_approvals -> ALLOWED" |
| D2 | HIGH | `reports` table has no append-only triggers (validations/runs do). Raw `UPDATE reports SET payload='{}'` and `DELETE FROM reports` succeeded. `measurements` and `engineering_change_requests` (`lifecycle/ecr.py:171` UPDATEs payload) are also mutable. | `db2.py` |
| D3 | MED | `delete_product` does not pre-check `engineering_records_entries`/lifecycle/reviews; the DELETE hits the append-only trigger inside a swallowed `try/except`, then the revision DELETE fails the FK and the whole transaction rolls back with the wrong message `CONFLICT: Product code or revision label already exists`. Data is preserved (good) but diagnosis is wrong. `DELETE FROM engineering_lifecycle_events WHERE revision_id=?` targets a non-existent column (`service.py:347`), silently ignored. | `service.py:330-375`; `db2.py`: "delete product with engineering record -> ERR CONFLICT", product still exists |
| D4 | MED | Error mapping: any `sqlite3.IntegrityError` (incl. FK failure for approval on unknown revision) -> `CONFLICT "Product code or revision label already exists"` (`service.py:119-120`). | `db2.py`: "approval bad revision -> ERR CONFLICT" |
| D5 | MED | Non-Core clients bypass FKs: with default pragma an orphan `INSERT INTO validations VALUES('x','nonexistent','{}')` was accepted (rejected once `foreign_keys=ON`). Any tool/script/second module not using `connection()` can corrupt referential integrity. | `db2.py` first run |
| D6 | MED | Interrupted writes: 5 hard kills (`taskkill /F`) during a create loop -> DB `integrity_check=ok`, 0 orphan revisions, hot journal recovered; but **5 workspace directories without DB rows** remained (`products/<uuid>` created inside the transaction, never cleaned). | `run_kill.sh`: `db 341 dirs 346 dirs_without_row 5` |
| D7 | MED | No user-facing backup/restore command (no `backup`/`restore` in `cli.py`, MCP, desktop routes). Only automatic pre-migration snapshots for opt-in sub-schemas; core v1-v4 migrations take no backup. `delete_product` removes files with `shutil.rmtree(ignore_errors=True)` after commit (`service.py:377-379`). | grep |
| D8 | LOW | `migrate_v5` never bumps version (see §1); version 4 DB reports itself as v4 though v5 columns exist. | `integration_store.py:59` |
| D9 | LOW | `runs` triggers present but untested by me with data (table empty, raw UPDATE trivially "allowed"). NOT VERIFIED. | |

## 3. Tests performed (temp roots)

| Test | Result |
|---|---|
| Duplicate product code (case-insensitive) | Rejected `CONFLICT` (correct) |
| PASS without evidence file | Rejected `INVALID_INPUT` (correct) |
| Raw UPDATE/DELETE on `validations` with a row | Blocked by trigger (correct) |
| Evidence file deleted after record | `validation_integrity=False`, `effective_status=not_evaluated` (correct, NOT_EVALUATED preserved) |
| Report generation | OK; report row then mutable (D2) |
| Delete product with validation | `DELETE_BLOCKED` (correct) |
| Delete clean draft product | OK |
| 2 concurrent processes x 60 iterations (unique + colliding codes) | 180 rows = 120 unique + 60 shared; 60 CONFLICT; no `database is locked`; 0 orphans; 180 dirs (`run_conc.sh`, 3.3 s) |
| Hard kill mid-write x5 | DB consistent; orphan dirs (D6) |
| Migration: synthetic v1 DB | Upgraded to v4, 17 tables |
| Migration: copy of repo DB (v4, 29 tables) | Opens cleanly, data intact |
| DB with user_version=9 | `STORAGE_ERROR Database is newer than this application` (correct) |
| Stale data: spec edit after report | Allowed on draft; validation summary reports `stale` flag (field present); approvals not marked stale (D1) |

## 4. Can completed evidence/approvals be overwritten or deleted?

* Validations, runs, engineering records/lifecycle/reviews: protected by SQLite triggers (raw SQL blocked; a DB-file owner can still drop triggers — no signing).
* Reports, lifecycle_approvals, measurements, ECRs: **mutable/deletable via raw SQL**; approvals effectively overridable via the API by appending a later row.
* Evidence files: hashed (sha256) and integrity-checked on read; deletion is detected, not prevented.
