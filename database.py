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
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Return rows as dicts
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

        logger.info("Database schema initialized")


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


def search_products_by_interests(interests: List[str], limit: int = 100) -> List[Dict]:
    """
    Search products matching any of the given interests.
    Returns list of product dicts.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Build query to match any interest tag
        # SQLite JSON functions or simple LIKE for now
        conditions = " OR ".join([f"interest_tags LIKE ?" for _ in interests])
        params = [f'%"{interest}"%' for interest in interests]

        cursor.execute(f"""
            SELECT * FROM products
            WHERE in_stock = 1
              AND removed_at IS NULL
              AND ({conditions})
            ORDER BY popularity_score DESC, RANDOM()
            LIMIT ?
        """, params + [limit])

        return [dict(row) for row in cursor.fetchall()]


def get_products_by_retailer(retailer: str, limit: int = 100) -> List[Dict]:
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
