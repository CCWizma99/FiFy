"""
backend/database.py
SQLite setup for APScheduler job tracking.
Uses a lightweight table to persist scrape job state across restarts.
"""
import sqlite3
from pathlib import Path

DB_PATH = Path("data/job_status.db")


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create tables if they don't exist."""
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS scrape_jobs (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                site        TEXT NOT NULL,
                started_at  TEXT NOT NULL,
                finished_at TEXT,
                status      TEXT NOT NULL DEFAULT 'running',
                products_scraped INTEGER DEFAULT 0,
                error_message    TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS url_hashes (
                url         TEXT PRIMARY KEY,
                hash        TEXT NOT NULL,
                last_seen   TEXT NOT NULL,
                is_active   INTEGER NOT NULL DEFAULT 1
            )
        """)
        conn.commit()
