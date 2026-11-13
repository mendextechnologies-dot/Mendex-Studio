# Active engineering dataset reset — 13 November 2026

The user explicitly requested clearing current product data before starting with
generic engineering prompts. The active dataset was replaced with an empty dataset;
old records and files were archived without deletion or disabling append-only protections.

Archive: `C:/Mendex studio/.mendex-archives/reset_20261113_013428_f1165ab5/`.
It contains `originals/`, a consistent online SQLite `database-backup.sqlite3`,
`manifest.json` with original file SHA-256/size metadata and `reset-result.json`.
All **9,848 archived files** matched their pre-reset hashes. The database backup
passed SQLite quick_check and matched original record counts.

Before reset: 1 product, 2 revisions, 5 reports, 5 integration jobs, 2 integration
workspaces, 1 visual workflow and 14 historical approval records. No running/queued
solver jobs were present. Studio/desktop reader sessions were closed before switching
directories to prevent stale clients writing back into the fresh dataset.

After reset: all active product/revision/validation/report/simulation/workspace/
workflow/review/measurement/lifecycle/engineering-record counts are zero. CLI and
MCP/core independently confirm zero projects, workspaces and designs. No new product,
example specification, simulated waveform or physical evidence was created.

Workstation tool-setting rows, UI preferences and local plugin configuration were
retained. Source code, generic prompt library and historical documentation/audit
evidence were retained. Tracked native model/design files removed from active
directories are preserved byte-for-byte in the archive, not permanently destroyed.

The old reset helper disabled immutable triggers and deleted records. It now uses
checked directory moves, a pre-switch verified fresh database, full-file verification
and rollback that restores original directories on failure. Windows long paths are
supported during evidence hashing; SQLite handles are explicitly closed before moving
directories. No recursive deletion is used.

Local checks: three isolated reset tests passed (frozen evidence/settings preservation,
failure rollback, read-only preview and running-job protection), plus the generic
prompt-library contract check. These are software tests, not engineering qualification.

To restore: stop every client; archive the current active dataset separately; move
each `originals/<name>` directory back to its original location as a whole. Do not merge
datasets, overwrite current files or copy an open SQLite database. Consult the manifest
and consistent database backup when verifying recovery.

Start instructions: `engineering-workflows/MASTER_ENGINEERING_INSTRUCTIONS.md`, then
the appropriate prompt under `engineering-workflows/stages/`. The active dataset is
empty and ready for user-supplied project context. Existing application/migration work
is retained; separate desktop acceptance milestones are not implied by a data reset.
