"""
SITE STATS - Lightweight event counter for admin dashboard.
Uses shelve for persistence (same pattern as share_manager.py).

Tracks: signups, recommendation runs, shares created, share views,
page hits (guides), errors, product clicks, demo mode usage.

Author: Chad + Claude
Date: February 2026
"""

import os
import shelve
import threading
from datetime import datetime, timedelta

STATS_DB_PATH = 'data/site_stats.db'
os.makedirs('data', exist_ok=True)

_lock = threading.Lock()


def _today():
    return datetime.now().strftime('%Y-%m-%d')


def _this_week_keys():
    """Return date-string keys for the last 7 days (inclusive of today)."""
    today = datetime.now().date()
    return [(today - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7)]


def track_event(event_name):
    """
    Increment a counter for an event on today's date.

    event_name: one of 'signup', 'rec_run', 'share_create', 'share_view',
                'guide_hit', 'product_click', 'error', 'demo_mode'
    """
    key = f"{_today()}:{event_name}"
    with _lock:
        db = shelve.open(STATS_DB_PATH, writeback=True)
        try:
            db[key] = db.get(key, 0) + 1
            db.sync()
        finally:
            db.close()


def get_and_increment_position():
    """
    Get and increment global position counter for viral growth tracking.
    Returns the position number (e.g., 2847 means "You're pick #2,847").

    This is used for social currency - showing users they're early adopters.
    """
    key = 'global:position_counter'
    with _lock:
        db = shelve.open(STATS_DB_PATH, writeback=True)
        try:
            current = db.get(key, 0)
            new_position = current + 1
            db[key] = new_position
            db.sync()
            return new_position
        finally:
            db.close()


def get_count(event_name, date_str=None):
    """Get count for a specific event on a specific date (default: today)."""
    date_str = date_str or _today()
    key = f"{date_str}:{event_name}"
    db = shelve.open(STATS_DB_PATH)
    try:
        return db.get(key, 0)
    finally:
        db.close()


def get_dashboard_data():
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

    db = shelve.open(STATS_DB_PATH)
    try:
        today_counts = {}
        week_counts = {}
        daily = []

        for ev in events:
            today_counts[ev] = db.get(f"{today_str}:{ev}", 0)
            week_counts[ev] = sum(db.get(f"{d}:{ev}", 0) for d in week_keys)

        for d in week_keys:
            row = {'date': d}
            for ev in events:
                row[ev] = db.get(f"{d}:{ev}", 0)
            daily.append(row)

        return {
            'today': today_counts,
            'week': week_counts,
            'daily': daily,
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }
    finally:
        db.close()
