"""
SITE STATS - Lightweight event counter for admin dashboard.

Migrated from shelve to SQLite (WAL mode) with atomic upsert so concurrent
writes from multiple Gunicorn workers don't corrupt counter state.

Tracks: signups, recommendation runs, shares created, share views,
page hits (guides), errors, product clicks, demo mode usage.

Author: Chad + Claude
Date: February 2026
"""

import os
import sqlite3
from datetime import datetime, timedelta

_DATA_DIR = os.environ.get('DATA_DIR', 'data')
_DB_PATH = os.path.join(_DATA_DIR, 'stats.db')
os.makedirs(_DATA_DIR, exist_ok=True)


def _connect() -> sqlite3.Connection:
    """Open a WAL-mode SQLite connection and ensure tables exist."""
    conn = sqlite3.connect(_DB_PATH, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS counters (
            key   TEXT PRIMARY KEY,
            count INTEGER NOT NULL DEFAULT 0
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS scalars (
            key   TEXT PRIMARY KEY,
            value INTEGER NOT NULL DEFAULT 0
        )
    """)
    return conn


def _today() -> str:
    return datetime.now().strftime('%Y-%m-%d')


def _this_week_keys() -> list:
    """Return date-string keys for the last 7 days (inclusive of today)."""
    today = datetime.now().date()
    return [(today - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7)]


def track_event(event_name: str) -> None:
    """
    Increment a counter for an event on today's date.

    event_name: one of 'signup', 'rec_run', 'share_create', 'share_view',
                'guide_hit', 'product_click', 'error', 'demo_mode'
    """
    key = f"{_today()}:{event_name}"
    conn = _connect()
    try:
        conn.execute(
            "INSERT INTO counters (key, count) VALUES (?, 1) "
            "ON CONFLICT(key) DO UPDATE SET count = count + 1",
            (key,)
        )
        conn.commit()
    finally:
        conn.close()


def get_and_increment_position() -> int:
    """
    Get and increment global position counter for viral growth tracking.
    Returns the position number (e.g., 2847 means "You're pick #2,847").
    """
    key = 'global:position_counter'
    conn = _connect()
    try:
        conn.execute(
            "INSERT INTO scalars (key, value) VALUES (?, 1) "
            "ON CONFLICT(key) DO UPDATE SET value = value + 1",
            (key,)
        )
        conn.commit()
        row = conn.execute("SELECT value FROM scalars WHERE key=?", (key,)).fetchone()
        return row[0] if row else 1
    finally:
        conn.close()


def get_count(event_name: str, date_str: str = None) -> int:
    """Get count for a specific event on a specific date (default: today)."""
    date_str = date_str or _today()
    key = f"{date_str}:{event_name}"
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT count FROM counters WHERE key=?", (key,)
        ).fetchone()
        return row[0] if row else 0
    finally:
        conn.close()


def get_dashboard_data() -> dict:
    """
    Return a summary dict for the admin dashboard.

    {
        'today': {'signup': N, 'rec_run': N, ...},
        'week':  {'signup': N, 'rec_run': N, ...},
        'daily': [{'date': '2026-02-09', 'signup': N, ...}, ...],  # last 7 days
        'generated_at': '2026-02-09 14:30:00',
    }
    """
    events = ['signup', 'rec_run', 'share_create', 'share_view',
              'guide_hit', 'product_click', 'error', 'demo_mode']

    today_str = _today()
    week_keys = _this_week_keys()

    conn = _connect()
    try:
        # Load all relevant keys in one query for efficiency
        all_keys = [f"{d}:{ev}" for d in week_keys for ev in events]
        placeholders = ','.join('?' * len(all_keys))
        rows = conn.execute(
            f"SELECT key, count FROM counters WHERE key IN ({placeholders})",
            all_keys
        ).fetchall()
        counts = {row[0]: row[1] for row in rows}

        today_counts = {ev: counts.get(f"{today_str}:{ev}", 0) for ev in events}
        week_counts = {
            ev: sum(counts.get(f"{d}:{ev}", 0) for d in week_keys)
            for ev in events
        }
        daily = [
            {'date': d, **{ev: counts.get(f"{d}:{ev}", 0) for ev in events}}
            for d in week_keys
        ]

        return {
            'today': today_counts,
            'week': week_counts,
            'daily': daily,
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }
    finally:
        conn.close()
