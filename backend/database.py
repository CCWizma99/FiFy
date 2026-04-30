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
        # 1. Scrape Job Tracking (Legacy/Single runs)
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

        # 2. Site Management
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sites (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                domain          TEXT UNIQUE NOT NULL,
                root_url        TEXT NOT NULL,
                is_active       INTEGER NOT NULL DEFAULT 1,
                status          TEXT DEFAULT 'idle',
                last_crawl_at   TEXT,
                total_products  INTEGER DEFAULT 0
            )
        """)

        # 3. Autonomous Crawl Queue
        conn.execute("""
            CREATE TABLE IF NOT EXISTS crawl_queue (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                site_id     INTEGER NOT NULL,
                url         TEXT NOT NULL,
                status      TEXT NOT NULL DEFAULT 'pending',
                page_type   TEXT DEFAULT 'unknown',
                depth       INTEGER DEFAULT 0,
                attempts    INTEGER DEFAULT 0,
                error       TEXT,
                FOREIGN KEY (site_id) REFERENCES sites(id),
                UNIQUE(site_id, url)
            )
        """)

        # 4. URL Deduplication Registry
        conn.execute("""
            CREATE TABLE IF NOT EXISTS url_hashes (
                url         TEXT PRIMARY KEY,
                hash        TEXT NOT NULL,
                last_seen   TEXT NOT NULL,
                is_active   INTEGER NOT NULL DEFAULT 1
            )
        """)

        # 5. Indexing Stats (for Charts)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS indexing_stats (
                date            TEXT NOT NULL,
                site_id         INTEGER NOT NULL,
                product_count   INTEGER DEFAULT 0,
                error_count     INTEGER DEFAULT 0,
                PRIMARY KEY (date, site_id),
                FOREIGN KEY (site_id) REFERENCES sites(id)
            )
        """)
        
        # Seed with initial sites if empty
        cursor = conn.execute("SELECT COUNT(*) FROM sites")
        if cursor.fetchone()[0] == 0:
            default_sites = [
                ("thilakawardhana.lk", "https://thilakawardhana.lk"),
                ("nolimit.lk", "https://www.nolimit.lk"),
                ("kandyselection.lk", "https://kandyselection.lk"),
                ("springandsummer.lk", "https://springandsummer.lk"),
                ("lady.lk", "https://lady.lk"),
            ]
            conn.executemany(
                "INSERT OR IGNORE INTO sites (domain, root_url) VALUES (?, ?)",
                default_sites
            )
        
        conn.commit()
