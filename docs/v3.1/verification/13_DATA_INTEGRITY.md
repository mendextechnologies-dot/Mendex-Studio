# 13. Data Integrity & Storage Audit

**Target:** SQLite Database, Triggers & File Artifacts  
**Status:** **PASS**

---

## 1. SQLite Database Schema

- **Database File**: `C:\Mendex studio\.mendex\studio.sqlite3`
- **Schema Version**: `PRAGMA user_version = 4`
- **Foreign Keys**: `PRAGMA foreign_keys = ON` enforced on every connection.
- **Append-Only Triggers Verified**:
  - `runs_no_delete` / `runs_no_update`
  - `validation_no_delete` / `validation_no_update`
- **Evidence Integrity**: All evidence files copied into `.mendex/evidence/` or revision workspaces are hashed with SHA-256. Modifications trigger tamper warnings and force effective status to `NOT_EVALUATED`.
