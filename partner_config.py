"""
Partner config — schema + CRUD for the v2 creator-embed wedge.

A "partner" is a creator/publisher who embeds GiftWise. Each partner has:
  - a slug (URL-safe id, used in /embed/<slug>)
  - a display name
  - a status (draft / live / paused)
  - a voice_axis float in [0.0, 1.0]:
      0.0 = practical / on-signal / actionable
      0.5 = balanced (default)
      1.0 = taste-edited / aspirational
  - theme colors (primary + accent) for the embed
  - retailer_allowlist: which retailers' affiliate links to use, JSON array
  - commission_split_partner_pct: percent of commission going to partner (rest to GiftWise)
  - custom_intake_questions: JSON array of {question, optional} objects
  - affiliate_inventory_source: URL or path for partner's own affiliate feed (CSV / API / etc.)
  - notes: free-text internal notes

Storage is SQLite at data/partners.db — separate from the production catalog
DB so partner config can evolve without risking it. Move into the main DB
once schema is stable.

Usage:
    import partner_config as pc
    pc.init_db()
    p = pc.create_partner(slug="weeknight-wines", name="Weeknight Wines", ...)
    pc.list_partners()
    pc.get_partner_by_slug("weeknight-wines")
    pc.update_partner(p["id"], voice_axis=0.3)
    pc.delete_partner(p["id"])
"""

import json
import os
import sqlite3
import re
from datetime import datetime
from typing import Optional

DB_PATH = os.environ.get("PARTNERS_DB", "data/partners.db")

VALID_STATUSES = ("draft", "live", "paused")

DEFAULT_RETAILERS = ["amazon", "ebay", "cj", "awin"]


_SCHEMA = """
CREATE TABLE IF NOT EXISTS partners (
    id                            INTEGER PRIMARY KEY AUTOINCREMENT,
    slug                          TEXT UNIQUE NOT NULL,
    name                          TEXT NOT NULL,
    status                        TEXT NOT NULL DEFAULT 'draft',
    voice_axis                    REAL NOT NULL DEFAULT 0.5,
    theme_primary_color           TEXT DEFAULT '#2c5cff',
    theme_accent_color            TEXT DEFAULT '#1e7a3a',
    retailer_allowlist            TEXT NOT NULL DEFAULT '[]',
    commission_split_partner_pct  REAL NOT NULL DEFAULT 50.0,
    custom_intake_questions       TEXT NOT NULL DEFAULT '[]',
    affiliate_inventory_source    TEXT,
    notes                         TEXT,
    created_at                    TEXT NOT NULL,
    updated_at                    TEXT NOT NULL
);
"""


def _connect():
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create the partners table if it doesn't exist. Idempotent."""
    conn = _connect()
    try:
        conn.executescript(_SCHEMA)
        conn.commit()
    finally:
        conn.close()


_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$")


def _validate_slug(slug: str):
    if not slug or not _SLUG_RE.match(slug):
        raise ValueError(
            f"invalid slug {slug!r}: must be lowercase a-z, 0-9, hyphens; "
            "start and end alphanumeric"
        )


def _validate_voice(v: float):
    if not (0.0 <= v <= 1.0):
        raise ValueError(f"voice_axis must be in [0.0, 1.0], got {v}")


def _validate_status(s: str):
    if s not in VALID_STATUSES:
        raise ValueError(f"status must be one of {VALID_STATUSES}, got {s!r}")


def _validate_split(pct: float):
    if not (0.0 <= pct <= 100.0):
        raise ValueError(f"commission_split_partner_pct must be in [0, 100], got {pct}")


def _row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["retailer_allowlist"] = json.loads(d.get("retailer_allowlist") or "[]")
    d["custom_intake_questions"] = json.loads(d.get("custom_intake_questions") or "[]")
    return d


def create_partner(
    *,
    slug: str,
    name: str,
    status: str = "draft",
    voice_axis: float = 0.5,
    theme_primary_color: str = "#2c5cff",
    theme_accent_color: str = "#1e7a3a",
    retailer_allowlist: Optional[list] = None,
    commission_split_partner_pct: float = 50.0,
    custom_intake_questions: Optional[list] = None,
    affiliate_inventory_source: Optional[str] = None,
    notes: Optional[str] = None,
) -> dict:
    _validate_slug(slug)
    if not name or not name.strip():
        raise ValueError("name is required")
    _validate_status(status)
    _validate_voice(voice_axis)
    _validate_split(commission_split_partner_pct)

    if retailer_allowlist is None:
        retailer_allowlist = list(DEFAULT_RETAILERS)
    if custom_intake_questions is None:
        custom_intake_questions = []

    now = datetime.utcnow().isoformat(timespec="seconds")
    conn = _connect()
    try:
        cur = conn.execute(
            """INSERT INTO partners
               (slug, name, status, voice_axis,
                theme_primary_color, theme_accent_color,
                retailer_allowlist, commission_split_partner_pct,
                custom_intake_questions, affiliate_inventory_source,
                notes, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (slug, name.strip(), status, voice_axis,
             theme_primary_color, theme_accent_color,
             json.dumps(retailer_allowlist),
             commission_split_partner_pct,
             json.dumps(custom_intake_questions),
             affiliate_inventory_source,
             notes, now, now),
        )
        conn.commit()
        return get_partner(cur.lastrowid)
    except sqlite3.IntegrityError as e:
        raise ValueError(f"slug {slug!r} already exists") from e
    finally:
        conn.close()


def get_partner(partner_id: int) -> Optional[dict]:
    conn = _connect()
    try:
        row = conn.execute("SELECT * FROM partners WHERE id = ?", (partner_id,)).fetchone()
        return _row_to_dict(row) if row else None
    finally:
        conn.close()


def get_partner_by_slug(slug: str) -> Optional[dict]:
    conn = _connect()
    try:
        row = conn.execute("SELECT * FROM partners WHERE slug = ?", (slug,)).fetchone()
        return _row_to_dict(row) if row else None
    finally:
        conn.close()


def list_partners(status: Optional[str] = None) -> list:
    conn = _connect()
    try:
        if status:
            _validate_status(status)
            rows = conn.execute(
                "SELECT * FROM partners WHERE status = ? ORDER BY created_at DESC",
                (status,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM partners ORDER BY created_at DESC"
            ).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


_UPDATABLE = (
    "name", "status", "voice_axis",
    "theme_primary_color", "theme_accent_color",
    "retailer_allowlist", "commission_split_partner_pct",
    "custom_intake_questions", "affiliate_inventory_source",
    "notes",
)


def update_partner(partner_id: int, **fields) -> Optional[dict]:
    if not fields:
        return get_partner(partner_id)

    sets = []
    values = []

    for key, value in fields.items():
        if key not in _UPDATABLE:
            raise ValueError(f"field {key!r} is not updatable")
        if key == "status":
            _validate_status(value)
        elif key == "voice_axis":
            _validate_voice(value)
        elif key == "commission_split_partner_pct":
            _validate_split(value)
        elif key in ("retailer_allowlist", "custom_intake_questions"):
            value = json.dumps(value if value is not None else [])
        elif key == "name":
            if not value or not value.strip():
                raise ValueError("name cannot be empty")
            value = value.strip()
        sets.append(f"{key} = ?")
        values.append(value)

    sets.append("updated_at = ?")
    values.append(datetime.utcnow().isoformat(timespec="seconds"))
    values.append(partner_id)

    conn = _connect()
    try:
        conn.execute(
            f"UPDATE partners SET {', '.join(sets)} WHERE id = ?",
            values,
        )
        conn.commit()
        return get_partner(partner_id)
    finally:
        conn.close()


def delete_partner(partner_id: int) -> bool:
    conn = _connect()
    try:
        cur = conn.execute("DELETE FROM partners WHERE id = ?", (partner_id,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def voice_axis_label(v: float) -> str:
    """Human-readable label for a voice_axis value."""
    if v <= 0.2:
        return "practical"
    if v <= 0.4:
        return "leans practical"
    if v <= 0.6:
        return "balanced"
    if v <= 0.8:
        return "leans taste-edited"
    return "taste-edited"
