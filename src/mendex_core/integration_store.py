"""Additive schema v4 and v5. Uses the same database and short-lived connections."""
from .sqlite_schema import execute_schema

def migrate(db):
    execute_schema(db, '''
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


def migrate_v5(db):
    """Additive schema v5 for product-independent workspaces and engineering activities."""
    cur = db.cursor()
    # Check integration_workspaces columns
    cols = [r[1] for r in cur.execute("PRAGMA table_info(integration_workspaces)").fetchall()]
    
    with db:
        if "description" not in cols:
            db.execute("ALTER TABLE integration_workspaces ADD COLUMN description TEXT DEFAULT ''")
        if "owner" not in cols:
            db.execute("ALTER TABLE integration_workspaces ADD COLUMN owner TEXT DEFAULT 'Engineer'")
        if "product_id" not in cols:
            db.execute("ALTER TABLE integration_workspaces ADD COLUMN product_id TEXT REFERENCES products(id)")
        if "created_at" not in cols:
            db.execute("ALTER TABLE integration_workspaces ADD COLUMN created_at TEXT")
        if "updated_at" not in cols:
            db.execute("ALTER TABLE integration_workspaces ADD COLUMN updated_at TEXT")

        # Activities table
        db.execute('''
            CREATE TABLE IF NOT EXISTS activities (
                id TEXT PRIMARY KEY,
                workspace_id TEXT NOT NULL REFERENCES integration_workspaces(id),
                name TEXT NOT NULL,
                activity_type TEXT NOT NULL,
                tool_id TEXT,
                payload TEXT NOT NULL,
                product_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        ''')
        db.execute("CREATE INDEX IF NOT EXISTS idx_activity_workspace ON activities(workspace_id)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_activity_product ON activities(product_id)")

        # Link jobs to activities if column doesn't exist
        job_cols = [r[1] for r in cur.execute("PRAGMA table_info(integration_jobs)").fetchall()]
        if "activity_id" not in job_cols:
            db.execute("ALTER TABLE integration_jobs ADD COLUMN activity_id TEXT REFERENCES activities(id)")
            db.execute("CREATE INDEX IF NOT EXISTS idx_job_activity ON integration_jobs(activity_id)")

        # db.execute("PRAGMA user_version=5")
