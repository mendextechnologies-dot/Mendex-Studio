"""Execute schema statements without sqlite3.executescript's implicit commit."""
import sqlite3


def execute_schema(db, script):
    statement = ""
    for line in script.splitlines():
        if line.strip() in {"BEGIN IMMEDIATE;", "COMMIT;"}:
            continue
        statement += line + "\n"
        if sqlite3.complete_statement(statement):
            db.execute(statement)
            statement = ""
    if statement.strip():
        raise ValueError("Incomplete schema statement")
