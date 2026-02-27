"""
SHARE MANAGER
Generate shareable links for gift recommendations.

Migrated from shelve to SQLite (WAL mode) for cross-worker safety.
The previous shelve implementation had no locking, so concurrent saves
from multiple Gunicorn workers could corrupt the shelve file.

Author: Chad + Claude
Date: February 2026
"""

import hashlib
import json
import os
import sqlite3
from datetime import datetime, timedelta

_DATA_DIR = os.environ.get('DATA_DIR', 'data')
_DB_PATH = os.path.join(_DATA_DIR, 'shares.db')
SHARE_EXPIRY_DAYS = 30

os.makedirs(_DATA_DIR, exist_ok=True)


def _connect() -> sqlite3.Connection:
    """Open a WAL-mode SQLite connection and ensure the table exists."""
    conn = sqlite3.connect(_DB_PATH, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS shares (
            share_id        TEXT PRIMARY KEY,
            recommendations TEXT NOT NULL,
            user_id         TEXT NOT NULL,
            created_at      TEXT NOT NULL,
            expires_at      TEXT NOT NULL
        )
    """)
    return conn


def generate_share_id(recommendations, user_id) -> str:
    """Generate a unique share ID for recommendations."""
    data = json.dumps(recommendations, sort_keys=True) + str(user_id) + datetime.now().isoformat()
    return hashlib.md5(data.encode()).hexdigest()[:12]


def save_share(share_id: str, recommendations, user_id) -> bool:
    """
    Save shareable recommendations.

    Returns True if saved successfully.
    """
    conn = _connect()
    try:
        conn.execute(
            """INSERT OR REPLACE INTO shares
               (share_id, recommendations, user_id, created_at, expires_at)
               VALUES (?, ?, ?, ?, ?)""",
            (
                share_id,
                json.dumps(recommendations),
                str(user_id),
                datetime.now().isoformat(),
                (datetime.now() + timedelta(days=SHARE_EXPIRY_DAYS)).isoformat(),
            )
        )
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()


def get_share(share_id: str):
    """
    Get shared recommendations.

    Returns dict with recommendations and metadata, or None if not found/expired.
    """
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT recommendations, user_id, created_at, expires_at FROM shares WHERE share_id=?",
            (share_id,)
        ).fetchone()

        if not row:
            return None

        recommendations_json, user_id, created_at, expires_at = row

        # Check expiry
        if datetime.now() > datetime.fromisoformat(expires_at):
            conn.execute("DELETE FROM shares WHERE share_id=?", (share_id,))
            conn.commit()
            return None

        return {
            'recommendations': json.loads(recommendations_json),
            'user_id': user_id,
            'created_at': created_at,
            'expires_at': expires_at,
        }
    finally:
        conn.close()


def cleanup_expired_shares() -> int:
    """Delete all expired shares. Returns count of deleted records."""
    conn = _connect()
    try:
        cursor = conn.execute(
            "DELETE FROM shares WHERE expires_at < ?",
            (datetime.now().isoformat(),)
        )
        conn.commit()
        return cursor.rowcount
    finally:
        conn.close()
