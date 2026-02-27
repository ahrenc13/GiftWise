"""
AWIN CATALOG SYNC

Downloads Awin merchant product feeds nightly, scores each product for
gift suitability, and caches locally in SQLite. Mirrors catalog_sync.py
(CJ sync) architecture.

KEY DIFFERENCE FROM CJ SYNC
----------------------------
CJ:   keyword search API → 1 query returns results from all joined advertisers
Awin: per-merchant CSV feeds → download each merchant's full product catalog,
      filter and score locally

This means we download every joined merchant's entire product catalog once
per sync run (capped at MAX_ROWS_PER_MERCHANT). We then score and store only
gift-worthy products (gift_score >= MIN_SCORE_TO_STORE).

MULTI-LABEL TAGGING
-------------------
Unlike the CJ sync (which tags products with a single search term), the Awin
sync uses product_tagger.py to tag each product with ALL matching interests
from the GiftWise ontology. A hiking backpack gets tags for:
  ["hiking", "camping", "backpacking", "rock climbing", "cycling", "skiing"]
...not just the interest that happened to be the search query.

On conflict (product already in DB), new tags are MERGED with existing tags —
existing tags are never removed.

SESSION-TIME INTEGRATION
-------------------------
The multi_retailer_searcher.py already has a "database first" path (lines
72–112) that queries the DB for cached products before hitting live APIs.
Since Awin products are stored in the same products table, they're served
automatically — no changes to awin_searcher.py or multi_retailer_searcher.py
are needed.

For code paths that need an explicit Awin cache check (e.g., future direct
Awin searcher cache-before-live), use get_cached_awin_products_for_interest().

PRUNING / FRESHNESS
-------------------
- Products synced within AWIN_SYNC_FRESH_HOURS are considered fresh
- Products not seen in AWIN_STALE_DAYS are soft-deleted (removed_at set)
- Re-running the sync refreshes products and clears stale markers
- Railway deploys wipe the SQLite DB — the /admin/sync-awin route or
  startup hook re-populates on cold start

USAGE (CLI)
-----------
  python3 awin_catalog_sync.py            # sync all joined merchants
  python3 awin_catalog_sync.py --dry-run  # preview only, no writes
  python3 awin_catalog_sync.py --stats    # show DB stats and exit

Author: Chad + Claude
Date: February 2026
"""

import csv
import io
import json
import logging
import os
import re
import sqlite3
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import requests

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------

# Awin Data Feed API key — same env var used by awin_searcher.py
AWIN_DATA_FEED_API_KEY = os.environ.get('AWIN_DATA_FEED_API_KEY', '')

# Database path — same DB as catalog_sync.py and database.py
_DB_PATH = os.environ.get('DATABASE_PATH', '/home/user/GiftWise/data/products.db')

# Max rows to download per merchant feed (prevents OOM on large catalogs).
# Most gift-focused Awin merchants have <5,000 gift-relevant products;
# this cap covers the full catalog for nearly all of them.
MAX_ROWS_PER_MERCHANT = 5000

# Buffer size for feed download (bytes). 8 MB covers ~6,000-8,000 CSV rows.
# Larger than awin_searcher.py's 4 MB live buffer — we want full coverage.
FEED_BUFFER_BYTES = 8 * 1024 * 1024

# Hours before a merchant's cache is considered stale
AWIN_SYNC_FRESH_HOURS = 20

# Days before a product not seen in any sync is soft-deleted
AWIN_STALE_DAYS = 14

# Delay between feed downloads (be polite to Awin servers)
FEED_DOWNLOAD_DELAY_SECONDS = 1.0


# ---------------------------------------------------------------------------
# DEPENDENCY IMPORTS (all graceful-fallback)
# ---------------------------------------------------------------------------

# From awin_searcher.py — reuse existing parsing/filtering logic
try:
    from awin_searcher import (
        _ci_get,
        _decompress_if_gzipped,
        AWIN_MAX_PRICE_USD,
        _AWIN_BLOCKED_DOMAINS,
        _get_feed_list,
    )
    _AWIN_SEARCHER_AVAILABLE = True
except ImportError:
    _AWIN_SEARCHER_AVAILABLE = False
    logger.warning("awin_catalog_sync: awin_searcher.py not found")

    # Stub fallbacks so the module doesn't crash on import
    AWIN_MAX_PRICE_USD = 200
    _AWIN_BLOCKED_DOMAINS: set = set()

    def _ci_get(row, *keys):
        for k in keys:
            v = row.get(k)
            if v:
                return v.strip() if isinstance(v, str) else v
        return ""

    def _decompress_if_gzipped(data):
        return data

    def _get_feed_list(api_key):
        return []

# From catalog_sync.py — reuse gift quality scorer
try:
    from catalog_sync import (
        score_product_gift_suitability,
        MIN_SCORE_TO_STORE,
        PRICE_SWEET_MIN,
        PRICE_SWEET_MAX,
        PRICE_ACCEPTABLE_MIN,
        PRICE_ACCEPTABLE_MAX,
    )
    _CATALOG_SYNC_AVAILABLE = True
except ImportError:
    _CATALOG_SYNC_AVAILABLE = False
    logger.warning("awin_catalog_sync: catalog_sync.py not found — using local scorer")
    MIN_SCORE_TO_STORE = 0.15
    PRICE_SWEET_MIN = 15.0
    PRICE_SWEET_MAX = 250.0
    PRICE_ACCEPTABLE_MIN = 8.0
    PRICE_ACCEPTABLE_MAX = 400.0

    # Minimal local scorer if catalog_sync unavailable
    def score_product_gift_suitability(product: Dict) -> float:
        score = 0.5
        image = product.get('image_url') or ''
        if image and image.startswith('http'):
            score += 0.15
        try:
            price = float(product.get('price') or 0)
            if PRICE_SWEET_MIN <= price <= PRICE_SWEET_MAX:
                score += 0.12
            elif PRICE_ACCEPTABLE_MIN <= price <= PRICE_ACCEPTABLE_MAX:
                score += 0.06
            elif 0 < price < PRICE_ACCEPTABLE_MIN:
                score -= 0.15
            elif price > PRICE_ACCEPTABLE_MAX:
                score -= 0.08
        except (TypeError, ValueError):
            pass
        desc = (product.get('description') or '')
        if len(desc) >= 80:
            score += 0.10
        title_lower = (product.get('title') or '').lower()
        boring = ['extension cord', 'cable organizer', 'pill case', 'drawer organizer',
                  'phone case', 'screen protector', 'travel adapter']
        if any(b in title_lower for b in boring):
            score -= 0.35
        bulk = ['100 pack', '50 pack', 'bulk pack', 'value pack', ' pack of ']
        if any(b in title_lower for b in bulk):
            score -= 0.30
        return round(max(0.0, min(1.0, score)), 3)

# From product_tagger.py — multi-label interest tagger
try:
    from product_tagger import tag_product_with_interests
    _TAGGER_AVAILABLE = True
except ImportError:
    _TAGGER_AVAILABLE = False
    logger.warning("awin_catalog_sync: product_tagger.py not found — single-label tagging only")

    def tag_product_with_interests(title: str, description: str) -> List[str]:
        return []


# ---------------------------------------------------------------------------
# SCHEMA MIGRATION
# Extends the products table with awin_advertiser_id column and creates
# the awin_sync_log table for per-merchant freshness tracking.
# Safe to call on every startup — all ops are IF NOT EXISTS.
# ---------------------------------------------------------------------------

def ensure_awin_catalog_schema():
    """
    Add awin_advertiser_id column and create awin_sync_log table.
    Called automatically on import.
    """
    os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)
    conn = sqlite3.connect(_DB_PATH, timeout=10)
    try:
        cur = conn.cursor()

        # Ensure base products table exists (in case database.py hasn't run yet)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id      TEXT NOT NULL,
                retailer        TEXT NOT NULL,
                title           TEXT NOT NULL,
                description     TEXT,
                price           REAL,
                currency        TEXT DEFAULT 'USD',
                image_url       TEXT,
                affiliate_link  TEXT NOT NULL,
                brand           TEXT,
                category        TEXT,
                interest_tags   TEXT,
                in_stock        BOOLEAN DEFAULT 1,
                last_checked    TIMESTAMP,
                last_updated    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                popularity_score INTEGER DEFAULT 0,
                removed_at      TIMESTAMP,
                UNIQUE(product_id, retailer)
            )
        """)

        # Add gift_score (may already exist from catalog_sync.py migration)
        try:
            cur.execute("ALTER TABLE products ADD COLUMN gift_score REAL DEFAULT 0.5")
        except sqlite3.OperationalError:
            pass  # Column already exists

        # Add awin_advertiser_id — the Awin discriminator column
        try:
            cur.execute("ALTER TABLE products ADD COLUMN awin_advertiser_id TEXT")
            logger.debug("Added awin_advertiser_id column to products table")
        except sqlite3.OperationalError:
            pass  # Column already exists

        # Index for fast Awin-product queries
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_awin_advertiser "
            "ON products(awin_advertiser_id)"
        )

        # Per-merchant sync log (one row per merchant, updated each sync run)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS awin_sync_log (
                advertiser_id    TEXT PRIMARY KEY,
                advertiser_name  TEXT,
                feed_url         TEXT,
                last_synced_at   TIMESTAMP,
                rows_scanned     INTEGER DEFAULT 0,
                products_found   INTEGER DEFAULT 0,
                products_stored  INTEGER DEFAULT 0,
                avg_gift_score   REAL    DEFAULT 0.0
            )
        """)

        conn.commit()
        logger.debug("Awin catalog schema migration complete")

    except Exception as e:
        conn.rollback()
        logger.error("Awin schema migration failed: %s", e)
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# FEED PARSER
# Extended version of awin_searcher._row_to_product() that extracts all
# fields needed for DB storage (brand, currency, price as float, etc.)
# ---------------------------------------------------------------------------

def _parse_price(price_str) -> float:
    """Parse a price string or number to a float. Returns 0.0 on failure."""
    try:
        return float(re.sub(r'[^\d.]', '', str(price_str)))
    except (ValueError, TypeError):
        return 0.0


def _row_to_db_product(row: Dict, advertiser_info: Dict) -> Optional[Dict]:
    """
    Map an Awin feed CSV row to a DB-ready product dict.

    Extends awin_searcher._row_to_product() to include brand, currency,
    price as float, and the DB-formatted field names.

    Returns None if essential fields (title, link) are missing.
    """
    title = _ci_get(row,
        "product_name", "product name", "title", "product_title", "name",
        "Product Name", "Title")
    link = _ci_get(row,
        "aw_deep_link", "merchant_deep_link", "deep_link", "link",
        "aw_product_url", "product_url", "URL", "Merchant Deep Link")

    if not title or not link:
        return None

    # Images
    image = _ci_get(row,
        "merchant_image_url", "aw_image_url", "aw_thumb_url",
        "image_url", "merchant_thumb", "product_image", "thumb_url",
        "image_link", "thumbnail_url", "Image URL", "Merchant Image URL")

    # Price (float for DB storage)
    price_raw = _ci_get(row,
        "search_price", "store_price", "price", "Price",
        "rrp_price", "display_price")
    price = _parse_price(price_raw)

    # Description (prefer longer field)
    description = _ci_get(row,
        "product_short_description", "description", "Description",
        "product_description", "Product Description")

    # Brand
    brand = _ci_get(row, "brand_name", "brand", "Brand",
                    "manufacturer", "Manufacturer")
    if not brand:
        brand = advertiser_info.get('advertiser_name', '')

    # Product ID
    product_id = _ci_get(row,
        "aw_product_id", "merchant_product_id", "product_id", "Product ID")
    if not product_id:
        product_id = str(abs(hash(title + link)))[:16]

    # Retailer = merchant name (consistent with CJ sync pattern)
    retailer = advertiser_info.get('advertiser_name', 'Awin')

    # Source domain (for curator display)
    merchant_name = advertiser_info.get('advertiser_name', '')
    if merchant_name:
        domain_match = re.search(
            r'(\w[\w-]*\.(?:com|co\.uk|net|org|io|shop|store))',
            merchant_name, re.IGNORECASE)
        if domain_match:
            source_domain = domain_match.group(1).lower()
        else:
            words = re.split(r'[\s\-]+', merchant_name)
            slug = ''.join(w.lower() for w in words[:3] if w)
            source_domain = slug + '.com' if slug else 'awin.com'
    else:
        source_domain = 'awin.com'

    return {
        'product_id':         str(product_id)[:64],
        'retailer':           retailer[:100],
        'title':              title[:200],
        'description':        (description or '')[:500],
        'price':              price,
        'currency':           'USD',
        'image_url':          image or '',
        'affiliate_link':     link,
        'brand':              brand[:100] if brand else '',
        'source_domain':      source_domain,
        'awin_advertiser_id': str(advertiser_info.get('advertiser_id', ''))[:32],
    }


# ---------------------------------------------------------------------------
# UPSERT WITH TAG MERGING
# Unlike the CJ sync's upsert (which never updates interest_tags on conflict),
# this upsert reads existing tags and MERGES new tags before writing.
# This ensures a product found for "hiking" that also matches "camping"
# accumulates both tags across sync runs.
# ---------------------------------------------------------------------------

def _upsert_awin_product(
    product: Dict,
    gift_score: float,
    new_tags: List[str],
    conn: sqlite3.Connection,
):
    """
    Upsert one Awin product into the products table.

    Tag merging: reads existing interest_tags for this product_id + retailer,
    merges with new_tags (new tags first for priority), then writes merged set.
    This means tags accumulate across sync runs — they're never lost.
    """
    cur = conn.cursor()
    now = datetime.now().isoformat()

    # Read existing tags for this product (if it already exists)
    cur.execute(
        "SELECT interest_tags FROM products WHERE product_id = ? AND retailer = ?",
        (product['product_id'], product['retailer'])
    )
    existing_row = cur.fetchone()
    existing_tags: List[str] = []
    if existing_row and existing_row[0]:
        try:
            existing_tags = json.loads(existing_row[0])
        except (json.JSONDecodeError, TypeError):
            pass

    # Merge: new tags first, then existing (deduplication via dict.fromkeys)
    merged_tags = list(dict.fromkeys(new_tags + existing_tags))

    cur.execute("""
        INSERT INTO products (
            product_id, retailer, title, description, price, currency,
            image_url, affiliate_link, brand, interest_tags,
            in_stock, last_checked, last_updated,
            gift_score, awin_advertiser_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?)
        ON CONFLICT(product_id, retailer) DO UPDATE SET
            title              = excluded.title,
            description        = excluded.description,
            price              = excluded.price,
            image_url          = excluded.image_url,
            affiliate_link     = excluded.affiliate_link,
            interest_tags      = excluded.interest_tags,
            in_stock           = 1,
            last_checked       = excluded.last_checked,
            last_updated       = excluded.last_updated,
            gift_score         = excluded.gift_score,
            awin_advertiser_id = excluded.awin_advertiser_id
    """, (
        product['product_id'],
        product['retailer'],
        product['title'],
        product['description'],
        product['price'],
        product.get('currency', 'USD'),
        product.get('image_url', ''),
        product['affiliate_link'],
        product.get('brand', ''),
        json.dumps(merged_tags),
        now,
        now,
        gift_score,
        product.get('awin_advertiser_id', ''),
    ))


# ---------------------------------------------------------------------------
# FEED DOWNLOADER
# Downloads the full feed for one merchant. Returns all CSV rows up to
# MAX_ROWS_PER_MERCHANT. Uses a larger buffer than the live searcher (8 MB
# vs 4 MB) since we want full catalog coverage, not just the first N rows.
# ---------------------------------------------------------------------------

def _download_feed_rows(feed_url: str) -> List[Dict]:
    """
    Download a merchant's product feed and return up to MAX_ROWS_PER_MERCHANT rows.

    Handles gzip-compressed feeds (Awin feeds often omit Content-Encoding header).
    Returns empty list on any failure — merchant is skipped, sync continues.
    """
    try:
        r = requests.get(feed_url, timeout=120, stream=True)
        r.raise_for_status()
    except requests.RequestException as e:
        logger.warning("Awin feed download failed (%s): %s", feed_url[:80], e)
        return []

    r.raw.decode_content = True

    try:
        chunks = []
        total_bytes = 0
        for chunk in r.iter_content(chunk_size=64 * 1024):
            chunks.append(chunk)
            total_bytes += len(chunk)
            if total_bytes >= FEED_BUFFER_BYTES:
                logger.debug("Awin feed buffer cap reached (%d bytes)", total_bytes)
                break
        r.close()
        data = b''.join(chunks)
    except Exception as e:
        logger.warning("Awin feed read error (%s): %s", feed_url[:80], e)
        try:
            r.close()
        except Exception:
            pass
        return []

    if not data:
        return []

    data = _decompress_if_gzipped(data)

    rows = []
    try:
        text = data.decode('utf-8', errors='replace')
        reader = csv.DictReader(io.StringIO(text, newline=''))
        for i, row in enumerate(reader):
            if i >= MAX_ROWS_PER_MERCHANT:
                logger.debug("Awin feed row cap reached (%d rows)", MAX_ROWS_PER_MERCHANT)
                break
            rows.append(row)
    except Exception as e:
        logger.warning("Awin feed CSV parse error: %s", e)
        return []

    logger.info("Awin feed downloaded: %d rows (%.1f KB compressed)",
                len(rows), total_bytes / 1024)
    return rows


# ---------------------------------------------------------------------------
# MERCHANT SYNC
# Downloads, scores, and stores all gift-worthy products for one merchant.
# ---------------------------------------------------------------------------

def sync_awin_merchant(
    feed_info: Dict,
    dry_run: bool = False,
) -> Dict:
    """
    Sync one Awin merchant's product feed to the DB.

    Returns a stats dict:
      { advertiser_id, advertiser_name, rows_scanned, found, stored,
        skipped_quality, skipped_price, skipped_domain, avg_score }
    """
    advertiser_id   = feed_info.get('feed_id') or feed_info.get('advertiser_id', '')
    advertiser_name = feed_info.get('advertiser_name', 'Unknown')
    feed_url        = feed_info.get('url', '')

    stats = {
        'advertiser_id':   advertiser_id,
        'advertiser_name': advertiser_name,
        'rows_scanned':    0,
        'found':           0,
        'stored':          0,
        'skipped_quality': 0,
        'skipped_price':   0,
        'skipped_domain':  0,
        'avg_score':       0.0,
    }

    if not feed_url:
        logger.warning("Awin sync: no feed URL for %s", advertiser_name)
        return stats

    logger.info("Awin sync: %s (%s)", advertiser_name, advertiser_id)

    rows = _download_feed_rows(feed_url)
    stats['rows_scanned'] = len(rows)

    if not rows:
        logger.warning("Awin sync: 0 rows from %s", advertiser_name)
        return stats

    # Log column names from first row for debugging
    logger.debug("Awin feed columns (%s): %s",
                 advertiser_name, list(rows[0].keys())[:15])

    advertiser_info = {
        'advertiser_name': advertiser_name,
        'advertiser_id':   advertiser_id,
    }

    scores_stored = []
    seen_ids = set()

    if not dry_run:
        conn = sqlite3.connect(_DB_PATH, timeout=15)
        conn.execute("PRAGMA journal_mode=WAL")

    try:
        if not dry_run:
            with conn:
                for row in rows:
                    product = _row_to_db_product(row, advertiser_info)
                    if not product:
                        continue

                    stats['found'] += 1

                    # Skip blocked merchant domains
                    if product.get('source_domain', '') in _AWIN_BLOCKED_DOMAINS:
                        stats['skipped_domain'] += 1
                        continue

                    # Apply upstream price cap
                    price = product.get('price', 0.0)
                    if price and price > AWIN_MAX_PRICE_USD:
                        stats['skipped_price'] += 1
                        continue

                    # Deduplicate within this feed run
                    pid = product['product_id']
                    if pid in seen_ids:
                        continue
                    seen_ids.add(pid)

                    # Score for gift suitability
                    gift_score = score_product_gift_suitability(product)
                    if gift_score < MIN_SCORE_TO_STORE:
                        stats['skipped_quality'] += 1
                        continue

                    # Multi-label interest tagging
                    tags = tag_product_with_interests(
                        product['title'],
                        product['description'],
                    )
                    # Always include advertiser name as a fallback tag
                    # so products are retrievable by merchant name search
                    if advertiser_name and advertiser_name.lower() not in tags:
                        tags.append(advertiser_name.lower())

                    _upsert_awin_product(product, gift_score, tags, conn)
                    scores_stored.append(gift_score)
                    stats['stored'] += 1

                # Update sync log for this merchant
                avg = round(sum(scores_stored) / len(scores_stored), 3) \
                      if scores_stored else 0.0
                stats['avg_score'] = avg

                conn.execute("""
                    INSERT INTO awin_sync_log
                        (advertiser_id, advertiser_name, feed_url,
                         last_synced_at, rows_scanned, products_found,
                         products_stored, avg_gift_score)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(advertiser_id) DO UPDATE SET
                        advertiser_name  = excluded.advertiser_name,
                        feed_url         = excluded.feed_url,
                        last_synced_at   = excluded.last_synced_at,
                        rows_scanned     = excluded.rows_scanned,
                        products_found   = excluded.products_found,
                        products_stored  = excluded.products_stored,
                        avg_gift_score   = excluded.avg_gift_score
                """, (
                    advertiser_id, advertiser_name, feed_url,
                    datetime.now().isoformat(),
                    stats['rows_scanned'], stats['found'],
                    stats['stored'], avg,
                ))

    except Exception as e:
        logger.error("Awin sync DB write failed (%s): %s", advertiser_name, e)
    finally:
        if not dry_run:
            conn.close()

    if dry_run:
        # Score products without writing to DB
        for row in rows:
            product = _row_to_db_product(row, advertiser_info)
            if not product:
                continue
            stats['found'] += 1
            price = product.get('price', 0.0)
            if price and price > AWIN_MAX_PRICE_USD:
                stats['skipped_price'] += 1
                continue
            gift_score = score_product_gift_suitability(product)
            if gift_score >= MIN_SCORE_TO_STORE:
                scores_stored.append(gift_score)
                stats['stored'] += 1
            else:
                stats['skipped_quality'] += 1
        stats['avg_score'] = round(
            sum(scores_stored) / len(scores_stored), 3) if scores_stored else 0.0

    logger.info(
        "Awin sync %s: %d rows → %d found → %d stored "
        "(quality_skip=%d, price_skip=%d, avg_score=%.2f)",
        advertiser_name, stats['rows_scanned'], stats['found'], stats['stored'],
        stats['skipped_quality'], stats['skipped_price'], stats['avg_score'],
    )
    return stats


# ---------------------------------------------------------------------------
# FULL SYNC RUNNER
# Orchestrates sync across all joined Awin merchants.
# ---------------------------------------------------------------------------

def run_awin_sync(dry_run: bool = False) -> Dict:
    """
    Sync all joined Awin merchants to the DB.

    Returns a summary dict with total stats and per-merchant breakdown.
    """
    ensure_awin_catalog_schema()

    if not AWIN_DATA_FEED_API_KEY:
        logger.warning("AWIN_DATA_FEED_API_KEY not set — skipping Awin catalog sync")
        return {'error': 'AWIN_DATA_FEED_API_KEY not set', 'merchants_synced': 0}

    logger.info("=" * 60)
    logger.info("AWIN CATALOG SYNC%s", " [DRY RUN]" if dry_run else "")
    logger.info("Started: %s", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    logger.info("=" * 60)

    # Get all joined merchant feeds
    feed_list = _get_feed_list(AWIN_DATA_FEED_API_KEY)
    if not feed_list:
        logger.warning("Awin feed list empty or failed")
        return {'error': 'Feed list empty', 'merchants_synced': 0}

    # Filter: joined, not blocked, not adult, not closed, English region
    _active_statuses = {"joined", "active", "approved", "yes", "1", "true"}
    _adult_kw = ("pleasure", "erotic", "lingerie", "adult", "sex", "vibrator", "fetish")

    def _is_gift_relevant(f):
        status = (f.get('membership_status') or '').lower()
        if status not in _active_statuses:
            return False
        text = ' '.join([
            (f.get('feed_name') or '').lower(),
            (f.get('advertiser_name') or '').lower(),
            (f.get('vertical') or '').lower(),
        ])
        if any(k in text for k in _adult_kw):
            return False
        if 'closed' in text:
            return False
        return True

    joined_feeds = [f for f in feed_list if _is_gift_relevant(f)]
    logger.info("Awin: %d joined/active merchants (of %d total in account)",
                len(joined_feeds), len(feed_list))

    if not joined_feeds:
        logger.warning("No joined Awin merchants — nothing to sync")
        return {'error': 'No joined merchants', 'merchants_synced': 0}

    # Deduplicate by advertiser name (keep first/best feed per advertiser)
    seen_advertisers = set()
    unique_feeds = []
    for f in joined_feeds:
        adv = (f.get('advertiser_name') or '').lower().strip()
        if adv not in seen_advertisers:
            seen_advertisers.add(adv)
            unique_feeds.append(f)

    logger.info("Awin: %d unique merchants to sync", len(unique_feeds))

    total_rows = total_found = total_stored = total_skipped = 0
    merchant_stats = []

    for i, feed_info in enumerate(unique_feeds, 1):
        logger.info("[%d/%d] %s", i, len(unique_feeds),
                    feed_info.get('advertiser_name', '?'))

        s = sync_awin_merchant(feed_info, dry_run=dry_run)
        merchant_stats.append(s)
        total_rows    += s['rows_scanned']
        total_found   += s['found']
        total_stored  += s['stored']
        total_skipped += s['skipped_quality'] + s['skipped_price'] + s['skipped_domain']

        # Polite delay between merchants
        if i < len(unique_feeds):
            time.sleep(FEED_DOWNLOAD_DELAY_SECONDS)

    # Soft-delete stale Awin products (not seen in AWIN_STALE_DAYS)
    stale_count = 0
    if not dry_run:
        conn = None
        try:
            conn = sqlite3.connect(_DB_PATH, timeout=10)
            cutoff = (datetime.now() - timedelta(days=AWIN_STALE_DAYS)).isoformat()
            with conn:
                cur = conn.cursor()
                cur.execute("""
                    UPDATE products
                    SET    removed_at = ?
                    WHERE  last_checked < ?
                      AND  removed_at IS NULL
                      AND  awin_advertiser_id IS NOT NULL
                      AND  awin_advertiser_id != ''
                """, (datetime.now().isoformat(), cutoff))
                stale_count = cur.rowcount
        except Exception as e:
            logger.error("Awin stale purge failed: %s", e)
        finally:
            if conn:
                conn.close()

    summary = {
        'dry_run':          dry_run,
        'merchants_synced': len(unique_feeds),
        'total_rows':       total_rows,
        'total_found':      total_found,
        'total_stored':     total_stored,
        'total_skipped':    total_skipped,
        'stale_purged':     stale_count,
        'started_at':       datetime.now().isoformat(),
        'merchant_stats':   merchant_stats,
    }

    logger.info("=" * 60)
    logger.info("AWIN SYNC COMPLETE")
    logger.info("  Merchants:       %d", len(unique_feeds))
    logger.info("  Rows scanned:    %d", total_rows)
    logger.info("  Products found:  %d", total_found)
    logger.info("  Products stored: %d", total_stored)
    logger.info("  Skipped (junk):  %d", total_skipped)
    logger.info("  Stale purged:    %d", stale_count)
    logger.info("=" * 60)

    return summary


# ---------------------------------------------------------------------------
# FRESHNESS CHECK
# Used by awin_searcher.py if it wants to check cache before live search.
# (Currently awin_searcher.py doesn't call this — the database_first path in
# multi_retailer_searcher.py handles it automatically. But this function is
# here so it can be wired in the future.)
# ---------------------------------------------------------------------------

def is_awin_merchant_fresh(
    advertiser_id: str,
    max_age_hours: float = AWIN_SYNC_FRESH_HOURS,
) -> bool:
    """Return True if this merchant was synced within max_age_hours."""
    try:
        conn = sqlite3.connect(_DB_PATH, timeout=5)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            "SELECT last_synced_at FROM awin_sync_log WHERE advertiser_id = ?",
            (str(advertiser_id),)
        )
        row = cur.fetchone()
        conn.close()
        if not row or not row['last_synced_at']:
            return False
        synced_at = datetime.fromisoformat(row['last_synced_at'])
        return (datetime.now() - synced_at) < timedelta(hours=max_age_hours)
    except Exception:
        return False


def is_any_awin_fresh() -> bool:
    """Return True if at least one Awin merchant was synced recently."""
    try:
        conn = sqlite3.connect(_DB_PATH, timeout=5)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cutoff = (datetime.now() - timedelta(hours=AWIN_SYNC_FRESH_HOURS)).isoformat()
        cur.execute(
            "SELECT COUNT(*) FROM awin_sync_log WHERE last_synced_at > ?",
            (cutoff,)
        )
        count = cur.fetchone()[0]
        conn.close()
        return count > 0
    except Exception:
        return False


# ---------------------------------------------------------------------------
# SESSION-TIME CACHE LOOKUP
# Returns cached Awin products for a profile interest in GiftWise standard
# product dict format. Used for direct Awin cache lookups (e.g., future
# integration with awin_searcher.py's live-fallback pattern).
#
# NOTE: The primary session-time path is multi_retailer_searcher.py lines
# 72-112 (database_first), which queries the DB automatically for ALL
# sources including Awin. This function is an explicit Awin-only lookup for
# code that wants to check Awin cache specifically.
# ---------------------------------------------------------------------------

def get_cached_awin_products_for_interest(
    interest: str,
    min_gift_score: float = 0.35,
    limit: int = 40,
) -> List[Dict]:
    """
    Return cached Awin products for an interest in GiftWise standard format.

    Searches interest_tags, title, and description. Results ranked by
    gift_score DESC, popularity_score DESC.

    Args:
        interest:       Interest/search term (e.g., "hiking", "coffee")
        min_gift_score: Minimum gift_score threshold (default 0.35)
        limit:          Max products to return

    Returns:
        List of product dicts in GiftWise standard format.
        Empty list if cache is cold or query fails.
    """
    try:
        conn = sqlite3.connect(_DB_PATH, timeout=5)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
            SELECT *
            FROM   products
            WHERE  in_stock = 1
              AND  removed_at IS NULL
              AND  awin_advertiser_id IS NOT NULL
              AND  awin_advertiser_id != ''
              AND  (
                       interest_tags LIKE ?
                    OR title          LIKE ?
                    OR description    LIKE ?
              )
              AND  (gift_score IS NULL OR gift_score >= ?)
            ORDER  BY gift_score DESC, popularity_score DESC
            LIMIT  ?
        """, (
            f'%"{interest.lower()}"%',
            f'%{interest}%',
            f'%{interest}%',
            min_gift_score,
            limit,
        ))
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return [_db_row_to_awin_format(r, interest) for r in rows]
    except Exception as e:
        logger.error("Awin cache lookup failed for '%s': %s", interest, e)
        return []


def _db_row_to_awin_format(row: Dict, interest: str) -> Dict:
    """Convert a products-table row to GiftWise standard product dict."""
    price_raw = row.get('price') or 0.0
    try:
        price_str = f"${float(price_raw):.2f}"
    except (TypeError, ValueError):
        price_str = "Price varies"

    image = row.get('image_url') or ''

    return {
        'title':          row.get('title', ''),
        'link':           row.get('affiliate_link', ''),
        'snippet':        row.get('description', ''),
        'image':          image,
        'thumbnail':      image,
        'image_url':      image,
        'source_domain':  row.get('retailer', 'awin'),
        'price':          price_str,
        'product_id':     row.get('product_id', ''),
        'search_query':   interest,
        'interest_match': interest,
        'priority':       2,
        'brand':          row.get('brand', ''),
        'awin_advertiser_id': row.get('awin_advertiser_id', ''),
        'gift_score':     row.get('gift_score', 0.5),
    }


# ---------------------------------------------------------------------------
# ADMIN STATS
# Used by giftwise_app.py admin dashboard.
# ---------------------------------------------------------------------------

def get_awin_catalog_stats() -> Dict:
    """Return Awin catalog stats for the admin dashboard."""
    try:
        conn = sqlite3.connect(_DB_PATH, timeout=5)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # Total active Awin products
        cur.execute("""
            SELECT COUNT(*) FROM products
            WHERE  awin_advertiser_id IS NOT NULL
              AND  awin_advertiser_id != ''
              AND  removed_at IS NULL
              AND  in_stock = 1
        """)
        total_products = cur.fetchone()[0]

        # Per-merchant breakdown
        cur.execute("""
            SELECT advertiser_name, products_stored, avg_gift_score, last_synced_at
            FROM   awin_sync_log
            ORDER  BY products_stored DESC
        """)
        merchants = [dict(r) for r in cur.fetchall()]

        # Last sync time
        cur.execute("SELECT MAX(last_synced_at) FROM awin_sync_log")
        row = cur.fetchone()
        last_sync = row[0] if row and row[0] else 'Never'

        # Fresh merchant count
        cutoff = (datetime.now() - timedelta(hours=AWIN_SYNC_FRESH_HOURS)).isoformat()
        cur.execute(
            "SELECT COUNT(*) FROM awin_sync_log WHERE last_synced_at > ?",
            (cutoff,)
        )
        fresh_merchants = cur.fetchone()[0]

        # Avg gift score
        cur.execute("""
            SELECT AVG(gift_score) FROM products
            WHERE  awin_advertiser_id IS NOT NULL
              AND  awin_advertiser_id != ''
              AND  removed_at IS NULL
              AND  gift_score IS NOT NULL
        """)
        avg_row = cur.fetchone()
        avg_gift_score = round(avg_row[0] or 0.0, 3)

        conn.close()

        return {
            'total_awin_products':  total_products,
            'merchants':            merchants,
            'last_sync':            last_sync,
            'fresh_merchants':      fresh_merchants,
            'avg_gift_score':       avg_gift_score,
            'cache_ttl_hours':      AWIN_SYNC_FRESH_HOURS,
        }

    except Exception as e:
        logger.error("Failed to get Awin catalog stats: %s", e)
        return {'error': str(e)}


# ---------------------------------------------------------------------------
# INITIALIZATION — run schema migration on import
# ---------------------------------------------------------------------------

try:
    ensure_awin_catalog_schema()
except Exception as _e:
    logger.warning("awin_catalog_sync: schema migration skipped (%s)", _e)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(name)s: %(message)s',
    )

    args = sys.argv[1:]
    dry_run = '--dry-run' in args

    if '--stats' in args:
        stats = get_awin_catalog_stats()
        print("\nAwin Catalog Stats")
        print("=" * 40)
        print(f"  Total products:   {stats.get('total_awin_products', 0)}")
        print(f"  Last sync:        {stats.get('last_sync', 'Never')}")
        print(f"  Fresh merchants:  {stats.get('fresh_merchants', 0)}")
        print(f"  Avg gift score:   {stats.get('avg_gift_score', 0):.3f}")
        merchants = stats.get('merchants', [])
        if merchants:
            print(f"\n  Merchants ({len(merchants)}):")
            for m in merchants:
                print(f"    {m['advertiser_name']}: "
                      f"{m['products_stored']} products, "
                      f"score={m['avg_gift_score']:.2f}, "
                      f"synced={m['last_synced_at'][:10] if m['last_synced_at'] else 'never'}")
        sys.exit(0)

    if not AWIN_DATA_FEED_API_KEY:
        print("ERROR: AWIN_DATA_FEED_API_KEY environment variable not set.")
        sys.exit(1)

    summary = run_awin_sync(dry_run=dry_run)

    print("\nSync Summary")
    print("=" * 40)
    print(f"  Merchants synced: {summary.get('merchants_synced', 0)}")
    print(f"  Rows scanned:     {summary.get('total_rows', 0)}")
    print(f"  Products found:   {summary.get('total_found', 0)}")
    print(f"  Products stored:  {summary.get('total_stored', 0)}")
    print(f"  Skipped (junk):   {summary.get('total_skipped', 0)}")
    print(f"  Stale purged:     {summary.get('stale_purged', 0)}")
    if summary.get('error'):
        print(f"  ERROR:            {summary['error']}")
