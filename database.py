"""
PRODUCT DATABASE - SQLite catalog for gift products

Reduces API calls by caching products from retailers.
Refreshed daily via automated cron job.

Author: Chad + Claude
Date: February 2026
"""

import sqlite3
import os
import json
import logging
from datetime import datetime, timedelta
from contextlib import contextmanager
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# Database location
DB_PATH = os.environ.get('DATABASE_PATH', '/home/user/GiftWise/data/products.db')


@contextmanager
def get_db_connection():
    """Context manager for database connections"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row  # Return rows as dicts
    conn.execute("PRAGMA journal_mode=WAL")   # Better read/write concurrency
    conn.execute("PRAGMA synchronous=NORMAL") # Safe + faster than FULL under WAL
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        conn.close()


def init_database():
    """
    Initialize database schema.
    Safe to run multiple times (IF NOT EXISTS clauses).
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Products table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id TEXT NOT NULL,
                retailer TEXT NOT NULL,

                -- Product details
                title TEXT NOT NULL,
                description TEXT,
                price REAL,
                currency TEXT DEFAULT 'USD',
                image_url TEXT,
                affiliate_link TEXT NOT NULL,

                -- Categorization
                brand TEXT,
                category TEXT,
                interest_tags TEXT,  -- JSON array: ["yoga", "fitness"]

                -- Stock/availability
                in_stock BOOLEAN DEFAULT 1,
                last_checked TIMESTAMP,

                -- Metadata
                popularity_score INTEGER DEFAULT 0,  -- Click count
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                removed_at TIMESTAMP,

                -- Ensure uniqueness per retailer
                UNIQUE(product_id, retailer)
            )
        """)

        # Indexes for fast queries
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_interest_tags ON products(interest_tags)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_retailer ON products(retailer)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_in_stock ON products(in_stock)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_brand ON products(brand)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_category ON products(category)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_popularity ON products(popularity_score)")

        # Profile cache table (save Claude API costs)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cached_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_hash TEXT UNIQUE NOT NULL,
                profile_json TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                access_count INTEGER DEFAULT 0
            )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_profile_hash ON cached_profiles(profile_hash)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_expires ON cached_profiles(expires_at)")

        # Database metadata (track refresh status)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS database_metadata (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Product intelligence (learn which products are good gifts)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS product_intelligence (
                product_id TEXT,
                retailer TEXT,

                -- Gift quality metrics (learned from curation)
                gift_worthiness_score REAL DEFAULT 0.5,  -- 0.0-1.0
                best_for_interests TEXT,                 -- JSON: ["taylor-swift", "music"]
                best_for_relationship TEXT,              -- JSON: ["friend", "partner"]
                avoid_reasons TEXT,                      -- JSON: ["too generic", "low quality"]

                -- Performance metrics (learn what converts)
                times_recommended INTEGER DEFAULT 0,
                times_clicked INTEGER DEFAULT 0,
                times_favorited INTEGER DEFAULT 0,
                click_through_rate REAL DEFAULT 0.0,

                -- Commission tracking (prioritize high-commission products)
                commission_rate REAL DEFAULT 0.01,
                estimated_commission_per_sale REAL,

                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                PRIMARY KEY (product_id, retailer)
            )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_gift_worthiness ON product_intelligence(gift_worthiness_score)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ctr ON product_intelligence(click_through_rate)")

        # Interest intelligence (cache what works for each interest)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS interest_intelligence (
                interest_name TEXT PRIMARY KEY,

                -- Static intelligence (from enrichment_data.py)
                do_buy TEXT,              -- JSON: ["concert tickets", "vinyl records"]
                dont_buy TEXT,            -- JSON: ["generic music player"]
                demographics TEXT,        -- Who has this interest
                trending_level TEXT,      -- "evergreen|trending|declining"

                -- Dynamic intelligence (learned from sessions)
                top_products TEXT,        -- JSON: product_ids that converted well
                top_brands TEXT,          -- JSON: brands that work
                avg_price_point REAL,     -- What people actually buy

                times_seen INTEGER DEFAULT 0,  -- How many profiles have this interest
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_interest_times_seen ON interest_intelligence(times_seen)")

        # Rate limits table (per-IP, 1 full pipeline run per 24 hours)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rate_limits (
                ip TEXT PRIMARY KEY,
                last_run TIMESTAMP NOT NULL
            )
        """)

        logger.info("Database schema initialized (with product/interest intelligence)")

    # Seed interest intelligence from enrichment_data.py if table is empty
    _seed_interest_intelligence_if_empty()


def _seed_interest_intelligence_if_empty():
    """
    One-time seed of interest_intelligence from enrichment_data.py.
    Safe to call every startup — only inserts if table is empty.
    Handles Railway ephemeral storage (DB resets on each deploy).
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM interest_intelligence")
            count = cursor.fetchone()[0]

        if count > 0:
            logger.debug(f"interest_intelligence already seeded ({count} rows) — skipping")
            return

        # Table is empty — seed from static enrichment data
        from enrichment_data import GIFT_INTELLIGENCE
        import json

        seeded = 0
        with get_db_connection() as conn:
            cursor = conn.cursor()
            for interest_name, data in GIFT_INTELLIGENCE.items():
                trending_level = 'trending' if data.get('trending_2026') else 'evergreen'
                cursor.execute("""
                    INSERT OR IGNORE INTO interest_intelligence
                        (interest_name, do_buy, dont_buy, trending_level)
                    VALUES (?, ?, ?, ?)
                """, (
                    interest_name,
                    json.dumps(data.get('do_buy', [])),
                    json.dumps(data.get('dont_buy', [])),
                    trending_level,
                ))
                seeded += 1

        logger.info(f"Seeded {seeded} interests into interest_intelligence from enrichment_data.py")

    except ImportError:
        logger.warning("enrichment_data.py not available — interest_intelligence not seeded")
    except Exception as e:
        logger.error(f"Failed to seed interest_intelligence: {e}")


# =============================================================================
# PRODUCT CRUD OPERATIONS
# =============================================================================

def upsert_product(product: Dict) -> int:
    """
    Insert or update a product.
    Returns product ID.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO products (
                product_id, retailer, title, description, price, currency,
                image_url, affiliate_link, brand, category, interest_tags,
                in_stock, last_checked, last_updated
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(product_id, retailer) DO UPDATE SET
                title = excluded.title,
                description = excluded.description,
                price = excluded.price,
                image_url = excluded.image_url,
                affiliate_link = excluded.affiliate_link,
                in_stock = excluded.in_stock,
                last_checked = excluded.last_checked,
                last_updated = excluded.last_updated
        """, (
            product.get('product_id'),
            product.get('retailer'),
            product.get('title'),
            product.get('description', ''),
            product.get('price'),
            product.get('currency', 'USD'),
            product.get('image_url'),
            product.get('affiliate_link'),
            product.get('brand'),
            product.get('category'),
            json.dumps(product.get('interest_tags', [])),
            product.get('in_stock', True),
            datetime.now().isoformat(),
            datetime.now().isoformat()
        ))

        return cursor.lastrowid


def _interest_to_keywords(interest: str) -> List[str]:
    """
    Extract meaningful keywords from a profile interest name.
    Mirrors the logic in catalog_sync._tag_awin_product_with_interests so that
    profile interests (e.g. 'dog care') match sync tags (e.g. 'dog toy', 'dog treats').
    """
    GENERIC = {"and", "the", "or", "with", "gift", "accessories",
               "lover", "fan", "from", "for", "set", "kit"}
    return [w.lower() for w in interest.split() if len(w) > 2 and w.lower() not in GENERIC]


def _build_interest_conditions(interests: List[str]):
    """
    Build SQL condition parts and params for matching a list of profile interests
    against the products table.

    For each interest we generate three match types:
      1. Exact tag match:    interest_tags LIKE '%"dog care"%'
         (catches cases where profile interest IS a sync term)
      2. Keyword tag match:  interest_tags LIKE '%dog%'
         (catches sync tags like 'dog toy', 'dog treats' for interest 'dog care')
      3. Title keyword match: title LIKE '%dog%'
         (fallback for products whose tags are sparse)

    This mirrors how _tag_awin_product_with_interests tags products at sync time.
    """
    condition_parts = []
    params = []
    for interest in interests:
        # 1. Exact tag match
        condition_parts.append("interest_tags LIKE ?")
        params.append(f'%"{interest.lower()}"%')
        # 2 & 3. Keyword matches
        for word in _interest_to_keywords(interest):
            condition_parts.append("interest_tags LIKE ?")
            params.append(f'%{word}%')
            condition_parts.append("title LIKE ?")
            params.append(f'%{word}%')
    return condition_parts, params


def search_products_by_interests(interests: List[str], limit: int = 100) -> List[Dict]:
    """
    Search products matching any of the given interests.
    Returns list of product dicts.
    """
    if not interests:
        return []

    with get_db_connection() as conn:
        cursor = conn.cursor()

        condition_parts, params = _build_interest_conditions(interests)
        conditions = " OR ".join(condition_parts)

        cursor.execute(f"""
            SELECT * FROM products
            WHERE in_stock = 1
              AND removed_at IS NULL
              AND ({conditions})
            ORDER BY popularity_score DESC, RANDOM()
            LIMIT ?
        """, params + [limit])

        return [dict(row) for row in cursor.fetchall()]


def search_products_diverse(interests: List[str], limit: int = 100,
                            max_per_category: int = 4,
                            splurge_min: float = 200.0,
                            splurge_max: float = 1500.0) -> Dict:
    """
    Search products with form diversity and splurge separation.

    Uses SQLite window functions to return at most max_per_category products
    per product form (category column), ensuring the curator sees a diverse
    pool rather than 15 candles and 12 mugs.

    Returns dict with:
      - 'regular': form-diverse products under splurge_min price
      - 'splurge_candidates': products in the splurge price range ($200-$1500)
      - 'per_interest_counts': dict of interest -> count (for eBay gap detection)
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()

        if not interests:
            return {'regular': [], 'splurge_candidates': [], 'per_interest_counts': {}}

        condition_parts, params = _build_interest_conditions(interests)
        conditions = " OR ".join(condition_parts)

        # Form-diverse query: rank products within each category, keep top N per form.
        # Products with no category get category='_uncategorized' so they still participate
        # in the window function but don't block each other (uncategorized is a big bucket).
        cursor.execute(f"""
            WITH matched AS (
                SELECT *,
                    COALESCE(NULLIF(category, ''), '_uncategorized') AS form,
                    ROW_NUMBER() OVER (
                        PARTITION BY COALESCE(NULLIF(category, ''), '_uncategorized')
                        ORDER BY gift_score DESC, popularity_score DESC
                    ) AS form_rank
                FROM products
                WHERE in_stock = 1
                  AND removed_at IS NULL
                  AND ({conditions})
            )
            SELECT * FROM matched
            WHERE form_rank <= ?
            ORDER BY gift_score DESC, popularity_score DESC
            LIMIT ?
        """, params + [max_per_category, limit * 2])

        all_rows = [dict(row) for row in cursor.fetchall()]

    # Separate regular vs splurge
    regular = []
    splurge = []
    per_interest_counts = {}

    for row in all_rows:
        price = row.get('price') or 0
        try:
            price = float(price)
        except (TypeError, ValueError):
            price = 0.0

        # Count per-interest for gap detection
        tags_raw = row.get('interest_tags', '[]')
        try:
            tags = json.loads(tags_raw) if isinstance(tags_raw, str) else tags_raw
        except (json.JSONDecodeError, TypeError):
            tags = []
        for tag in (tags if isinstance(tags, list) else []):
            t = tag.lower().strip()
            if t:
                per_interest_counts[t] = per_interest_counts.get(t, 0) + 1

        if splurge_min <= price <= splurge_max:
            splurge.append(row)
        else:
            regular.append(row)

    return {
        'regular': regular[:limit],
        'splurge_candidates': splurge[:20],
        'per_interest_counts': per_interest_counts,
    }


def search_products_by_title(keywords: List[str], limit: int = 10) -> List[Dict]:
    """
    Search products by title keywords. Used for matching experience materials
    against the full CJ/Awin catalog when the interest-fetched inventory pool
    doesn't contain a match.

    Requires at least 2 keyword matches (or 1 if only 1 keyword provided).
    Returns products sorted by gift_score.
    """
    if not keywords:
        return []

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Each keyword must appear in the title (AND logic within, scored by overlap)
        # Use LIKE for each keyword, require at least min_match
        conditions = " AND ".join([f"LOWER(title) LIKE ?" for _ in keywords])
        params = [f'%{kw.lower()}%' for kw in keywords]

        cursor.execute(f"""
            SELECT * FROM products
            WHERE in_stock = 1
              AND removed_at IS NULL
              AND ({conditions})
            ORDER BY gift_score DESC
            LIMIT ?
        """, params + [limit])

        return [dict(row) for row in cursor.fetchall()]
    """Get all products from a specific retailer"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM products
            WHERE retailer = ?
              AND in_stock = 1
              AND removed_at IS NULL
            ORDER BY last_updated DESC
            LIMIT ?
        """, (retailer, limit))

        return [dict(row) for row in cursor.fetchall()]


def increment_popularity(product_id: str, retailer: str):
    """Increment popularity score when product is clicked/recommended"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE products
            SET popularity_score = popularity_score + 1
            WHERE product_id = ? AND retailer = ?
        """, (product_id, retailer))


def mark_stale_products(days: int = 7) -> int:
    """
    Mark products as removed if not seen in X days.
    Returns count of marked products.
    """
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE products
            SET removed_at = ?
            WHERE last_checked < ?
              AND removed_at IS NULL
        """, (datetime.now().isoformat(), cutoff))

        count = cursor.rowcount
        logger.info(f"Marked {count} products as stale (not seen in {days} days)")
        return count


def get_database_stats() -> Dict:
    """Get database health statistics for admin dashboard"""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Total products
        cursor.execute("SELECT COUNT(*) FROM products WHERE removed_at IS NULL AND in_stock = 1")
        total_products = cursor.fetchone()[0]

        # By retailer
        cursor.execute("""
            SELECT retailer, COUNT(*) as count
            FROM products
            WHERE removed_at IS NULL AND in_stock = 1
            GROUP BY retailer
            ORDER BY count DESC
        """)
        by_retailer = {row['retailer']: row['count'] for row in cursor.fetchall()}

        # Recently added (last 24 hours)
        yesterday = (datetime.now() - timedelta(days=1)).isoformat()
        cursor.execute("SELECT COUNT(*) FROM products WHERE created_at > ?", (yesterday,))
        added_today = cursor.fetchone()[0]

        # Stale products (not checked in 7 days)
        week_ago = (datetime.now() - timedelta(days=7)).isoformat()
        cursor.execute("SELECT COUNT(*) FROM products WHERE last_checked < ? AND removed_at IS NULL", (week_ago,))
        stale_count = cursor.fetchone()[0]

        # Last refresh time
        cursor.execute("SELECT value FROM database_metadata WHERE key = 'last_refresh'")
        row = cursor.fetchone()
        last_refresh = row['value'] if row else 'Never'

        # Top brands
        cursor.execute("""
            SELECT brand, COUNT(*) as count
            FROM products
            WHERE removed_at IS NULL AND in_stock = 1 AND brand IS NOT NULL
            GROUP BY brand
            ORDER BY count DESC
            LIMIT 10
        """)
        top_brands = [{'brand': row['brand'], 'count': row['count']} for row in cursor.fetchall()]

        return {
            'total_products': total_products,
            'by_retailer': by_retailer,
            'added_today': added_today,
            'stale_count': stale_count,
            'last_refresh': last_refresh,
            'top_brands': top_brands,
        }


def set_metadata(key: str, value: str):
    """Set database metadata value"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO database_metadata (key, value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = excluded.updated_at
        """, (key, value, datetime.now().isoformat()))


# =============================================================================
# PROFILE CACHE OPERATIONS (Save Claude API costs)
# =============================================================================

def cache_profile(profile_hash: str, profile_json: str, ttl_days: int = 7):
    """Cache analyzed profile to avoid re-analyzing same social media data"""
    expires_at = (datetime.now() + timedelta(days=ttl_days)).isoformat()

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO cached_profiles (profile_hash, profile_json, expires_at)
            VALUES (?, ?, ?)
            ON CONFLICT(profile_hash) DO UPDATE SET
                profile_json = excluded.profile_json,
                expires_at = excluded.expires_at,
                access_count = access_count + 1
        """, (profile_hash, profile_json, expires_at))


def get_cached_profile(profile_hash: str) -> Optional[Dict]:
    """Get cached profile if not expired"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT profile_json, expires_at
            FROM cached_profiles
            WHERE profile_hash = ?
              AND expires_at > ?
        """, (profile_hash, datetime.now().isoformat()))

        row = cursor.fetchone()
        if row:
            # Increment access count
            cursor.execute("""
                UPDATE cached_profiles
                SET access_count = access_count + 1
                WHERE profile_hash = ?
            """, (profile_hash,))

            return json.loads(row['profile_json'])

        return None


def clean_expired_profiles() -> int:
    """Remove expired profile caches"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            DELETE FROM cached_profiles
            WHERE expires_at < ?
        """, (datetime.now().isoformat(),))

        count = cursor.rowcount
        logger.info(f"Cleaned {count} expired profile caches")
        return count


# =============================================================================
# PRODUCT INTELLIGENCE (Revenue Optimization)
# =============================================================================

def get_product_intelligence(product_id: str, retailer: str) -> Optional[Dict]:
    """Get intelligence data for a product"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM product_intelligence
            WHERE product_id = ? AND retailer = ?
        """, (product_id, retailer))

        row = cursor.fetchone()
        if row:
            return dict(row)
        return None


def update_product_intelligence(product_id: str, retailer: str, updates: Dict):
    """Update product intelligence metrics"""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Build SET clause dynamically from updates dict
        set_clauses = [f"{key} = ?" for key in updates.keys()]
        set_clause = ", ".join(set_clauses)
        values = list(updates.values())

        cursor.execute(f"""
            INSERT INTO product_intelligence (product_id, retailer, {', '.join(updates.keys())}, last_updated)
            VALUES (?, ?, {', '.join(['?' for _ in updates])}, ?)
            ON CONFLICT(product_id, retailer) DO UPDATE SET
                {set_clause},
                last_updated = ?
        """, [product_id, retailer] + values + [datetime.now().isoformat()] + values + [datetime.now().isoformat()])


def track_product_recommended(product_id: str, retailer: str):
    """Increment recommended count for a product"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO product_intelligence (product_id, retailer, times_recommended, last_updated)
            VALUES (?, ?, 1, ?)
            ON CONFLICT(product_id, retailer) DO UPDATE SET
                times_recommended = times_recommended + 1,
                last_updated = ?
        """, (product_id, retailer, datetime.now().isoformat(), datetime.now().isoformat()))


def track_product_clicked(product_id: str, retailer: str):
    """Increment clicked count and update CTR"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE product_intelligence
            SET times_clicked = times_clicked + 1,
                click_through_rate = CAST(times_clicked + 1 AS REAL) / NULLIF(times_recommended, 0),
                last_updated = ?
            WHERE product_id = ? AND retailer = ?
        """, (datetime.now().isoformat(), product_id, retailer))


def track_product_favorited(product_id: str, retailer: str):
    """Increment favorited count"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE product_intelligence
            SET times_favorited = times_favorited + 1,
                last_updated = ?
            WHERE product_id = ? AND retailer = ?
        """, (datetime.now().isoformat(), product_id, retailer))


# =============================================================================
# INTEREST INTELLIGENCE (Reuse Analysis)
# =============================================================================

def get_interest_intelligence(interest_name: str) -> Optional[Dict]:
    """Get intelligence data for an interest"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM interest_intelligence
            WHERE interest_name = ?
        """, (interest_name.lower(),))

        row = cursor.fetchone()
        if row:
            intel = dict(row)
            # Parse JSON fields
            for field in ['do_buy', 'dont_buy', 'top_products', 'top_brands']:
                if intel.get(field):
                    try:
                        intel[field] = json.loads(intel[field])
                    except:
                        intel[field] = []
            return intel
        return None


def upsert_interest_intelligence(interest_name: str, data: Dict):
    """Insert or update interest intelligence"""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Serialize JSON fields
        do_buy = json.dumps(data.get('do_buy', []))
        dont_buy = json.dumps(data.get('dont_buy', []))
        top_products = json.dumps(data.get('top_products', []))
        top_brands = json.dumps(data.get('top_brands', []))

        cursor.execute("""
            INSERT INTO interest_intelligence (
                interest_name, do_buy, dont_buy, demographics, trending_level,
                top_products, top_brands, avg_price_point, times_seen, last_updated
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(interest_name) DO UPDATE SET
                do_buy = excluded.do_buy,
                dont_buy = excluded.dont_buy,
                demographics = excluded.demographics,
                trending_level = excluded.trending_level,
                top_products = excluded.top_products,
                top_brands = excluded.top_brands,
                avg_price_point = excluded.avg_price_point,
                times_seen = times_seen + 1,
                last_updated = excluded.last_updated
        """, (
            interest_name.lower(),
            do_buy,
            dont_buy,
            data.get('demographics', ''),
            data.get('trending_level', 'evergreen'),
            top_products,
            top_brands,
            data.get('avg_price_point', 0.0),
            1,
            datetime.now().isoformat()
        ))


def increment_interest_seen(interest_name: str):
    """Track that we've seen this interest in a profile"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO interest_intelligence (interest_name, times_seen, last_updated)
            VALUES (?, 1, ?)
            ON CONFLICT(interest_name) DO UPDATE SET
                times_seen = times_seen + 1,
                last_updated = ?
        """, (interest_name.lower(), datetime.now().isoformat(), datetime.now().isoformat()))


# =============================================================================
# RATE LIMITING
# =============================================================================

def check_and_record_pipeline_run(ip: str) -> tuple:
    """
    Check if an IP is allowed to run the full pipeline (1 run per 24 hours).
    Records the run atomically if allowed.

    Returns:
        (allowed: bool, reset_time: datetime | None)
        - (True, None) if allowed (first run or >24h since last run)
        - (False, reset_time) if rate limited
    """
    now = datetime.now()
    window = timedelta(hours=24)

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Check existing record
        cursor.execute("SELECT last_run FROM rate_limits WHERE ip = ?", (ip,))
        row = cursor.fetchone()

        if row:
            last_run = datetime.fromisoformat(row['last_run'])
            elapsed = now - last_run
            if elapsed < window:
                reset_time = last_run + window
                return False, reset_time

        # Allowed — record this run (INSERT OR REPLACE is atomic)
        cursor.execute(
            "INSERT OR REPLACE INTO rate_limits (ip, last_run) VALUES (?, ?)",
            (ip, now.isoformat())
        )
        return True, None


# =============================================================================
# INITIALIZATION
# =============================================================================

# Initialize database on module import
try:
    init_database()
    logger.info("Product database ready")
except Exception as e:
    logger.error(f"Failed to initialize database: {e}")


if __name__ == "__main__":
    # Manual testing/inspection
    print("Product Database Utilities")
    print("=" * 50)

    stats = get_database_stats()
    print(f"Total products: {stats['total_products']}")
    print(f"Added today: {stats['added_today']}")
    print(f"Last refresh: {stats['last_refresh']}")
    print(f"\nBy retailer:")
    for retailer, count in stats['by_retailer'].items():
        print(f"  {retailer}: {count}")
    print(f"\nStale products: {stats['stale_count']}")
