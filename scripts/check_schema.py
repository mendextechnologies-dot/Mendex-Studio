import sqlite3

conn = sqlite3.connect('.mendex/studio.sqlite3')
cur = conn.cursor()
tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
print('Tables in studio.sqlite3:', tables)
for t in tables:
    row = cur.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{t}'").fetchone()
    sql = row[0] if row else ""
    if 'product' in sql.lower() or 'revision' in sql.lower():
        print(f"Table {t}:")
        print("  ", sql)
