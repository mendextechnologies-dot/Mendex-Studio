"""Additive schema v4. Uses the same database and short-lived connections."""
def migrate(db):
    db.executescript('''
        BEGIN IMMEDIATE;
        CREATE TABLE IF NOT EXISTS integration_settings (tool_id TEXT PRIMARY KEY, payload TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS integration_health (tool_id TEXT PRIMARY KEY, payload TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS integration_workspaces (id TEXT PRIMARY KEY, name TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS integration_jobs (id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL REFERENCES integration_workspaces(id), status TEXT NOT NULL, payload TEXT NOT NULL, manifest_sha256 TEXT);
        CREATE TABLE IF NOT EXISTS integration_datasets (id TEXT PRIMARY KEY, tool_id TEXT NOT NULL, payload TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS integration_job_status ON integration_jobs(status);
        PRAGMA user_version=4;
        COMMIT;
    ''')
