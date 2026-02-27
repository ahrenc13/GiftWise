"""
Cross-process generation progress storage.

Uses SQLite with WAL mode so any Gunicorn worker can read the status
written by any other worker. Replaces the previous in-memory dict which
was invisible across worker process boundaries.

Author: Chad + Claude
Date: February 2026
"""

import json
import os
import sqlite3
import time
from datetime import datetime

_DATA_DIR = os.environ.get('DATA_DIR', 'data')
_DB_PATH = os.path.join(_DATA_DIR, 'progress.db')

_DEFAULT_STATE = {
    'stage': 'starting',
    'stage_label': 'Getting started...',
    'interests': [],
    'retailers': {},
    'product_count': 0,
    'complete': False,
    'success': False,
    'error': None,
}


def _connect() -> sqlite3.Connection:
    """Open a WAL-mode SQLite connection and ensure the table exists."""
    os.makedirs(_DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(_DB_PATH, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS progress (
            user_id   TEXT PRIMARY KEY,
            data      TEXT NOT NULL,
            updated_at REAL NOT NULL
        )
    """)
    return conn


def set_progress(user_id: str, **kwargs) -> None:
    """
    Write/update progress state for user_id.

    Retailers dict is merged (not replaced) so each retailer's
    status accumulates across multiple calls.
    """
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT data FROM progress WHERE user_id=?", (user_id,)
        ).fetchone()
        if row:
            data = json.loads(row[0])
        else:
            data = dict(_DEFAULT_STATE, started_at=datetime.now().isoformat())

        # Merge retailers dict instead of overwriting it
        if 'retailers' in kwargs:
            merged = dict(data.get('retailers', {}))
            merged.update(kwargs.pop('retailers'))
            kwargs['retailers'] = merged

        data.update(kwargs)
        conn.execute(
            "INSERT OR REPLACE INTO progress (user_id, data, updated_at) VALUES (?, ?, ?)",
            (user_id, json.dumps(data), time.time())
        )
        conn.commit()
    finally:
        conn.close()


def get_progress(user_id: str) -> dict:
    """Read progress state for user_id. Returns default state if not found."""
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT data FROM progress WHERE user_id=?", (user_id,)
        ).fetchone()
        if row:
            return json.loads(row[0])
        return dict(_DEFAULT_STATE, stage='unknown', stage_label='Preparing...')
    finally:
        conn.close()


def clear_progress(user_id: str) -> None:
    """Remove progress state for user_id."""
    conn = _connect()
    try:
        conn.execute("DELETE FROM progress WHERE user_id=?", (user_id,))
        conn.commit()
    finally:
        conn.close()


def cleanup_old_progress(max_age_seconds: int = 7200) -> int:
    """Delete entries older than max_age_seconds. Returns count deleted."""
    conn = _connect()
    try:
        cutoff = time.time() - max_age_seconds
        cursor = conn.execute(
            "DELETE FROM progress WHERE updated_at < ?", (cutoff,)
        )
        conn.commit()
        return cursor.rowcount
    finally:
        conn.close()
