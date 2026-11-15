"""Transactional request budgets, shared across local workers and restarts.
Stores counters and salted client hashes only, never chat text or raw IP addresses.
"""
import hashlib
import secrets
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock


class UsageLimiter:
    def __init__(self, path, per_minute, daily):
        self.path = path
        self.per_minute = max(1, per_minute)
        self.daily = max(1, daily)
        self.lock = Lock()

    def consume(self, client, now=None):
        now = time.time() if now is None else now
        minute = str(int(now // 60))
        day = datetime.fromtimestamp(now, timezone.utc).strftime('%Y-%m-%d')
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self.lock, sqlite3.connect(self.path, timeout=5) as db:
            db.execute('CREATE TABLE IF NOT EXISTS usage (bucket TEXT PRIMARY KEY, count INTEGER NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
            db.execute('BEGIN IMMEDIATE')
            db.execute("INSERT OR IGNORE INTO metadata VALUES ('salt', ?)", (secrets.token_hex(32),))
            salt = db.execute("SELECT value FROM metadata WHERE key='salt'").fetchone()[0]
            digest = hashlib.sha256((salt + client).encode()).hexdigest()
            daily_key = 'day:' + day
            ip_key = 'minute:' + minute + ':' + digest
            counts = dict(db.execute('SELECT bucket, count FROM usage WHERE bucket IN (?, ?)', (daily_key, ip_key)))
            if counts.get(daily_key, 0) >= self.daily:
                return 'The demo has reached its daily message budget. Please try again tomorrow.', 3600
            if counts.get(ip_key, 0) >= self.per_minute:
                return 'You are sending messages too quickly. Please try again in a minute.', 60
            for key in (daily_key, ip_key):
                db.execute('INSERT INTO usage VALUES (?, 1) ON CONFLICT(bucket) DO UPDATE SET count=count+1', (key,))
            # Counters carry no chat data and need not be kept after their period ends.
            db.execute("DELETE FROM usage WHERE bucket LIKE 'day:%' AND bucket != ?", (daily_key,))
            db.execute("DELETE FROM usage WHERE bucket LIKE 'minute:%' AND bucket NOT LIKE ?", ('minute:' + minute + ':%',))
        return None
