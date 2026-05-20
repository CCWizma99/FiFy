import sqlite3
from pathlib import Path

DB_PATH = Path("data/job_status.db")
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
rows = conn.execute("SELECT * FROM sites").fetchall()
for row in rows:
    print(dict(row))
conn.close()
