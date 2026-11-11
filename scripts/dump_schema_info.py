import sqlite3

con = sqlite3.connect(".mendex/studio.sqlite3")
cur = con.cursor()
tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
print("Tables in .mendex/studio.sqlite3:")
uv = cur.execute("PRAGMA user_version").fetchone()[0]
print("PRAGMA user_version:", uv)
for t in tables:
    count = cur.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
    print(f"  {t}: {count} rows")
con.close()
