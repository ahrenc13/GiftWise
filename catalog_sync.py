"""
CATALOG SYNC — CJ Affiliate product catalog downloader and gift pre-scorer

Downloads the full CJ product catalog for all joined advertisers (including
TikTok Shop), pre-scores each product for gift suitability, and stores locally
in SQLite so live sessions query the database instead of hitting the CJ API.

Benefits vs. live-only search:
  - Eliminates 3-5 seconds of CJ API latency per interest term per session
  - Enables pre-filtering by gift quality before products reach the curator
  - Supports learning loop: clicked/recommended products get score boosts
  - Full TikTok Shop catalog coverage without per-session API rate limits

Architecture:
  - catalog_sync.py runs nightly (Railway cron or /admin/sync-catalog route)
  - Queries CJ GraphQL with joined_only=True, paginating up to 300 products/term
  - Scores each product 0.0–1.0 for gift suitability at sync time
  - Stores in SQLite with gift_score + advertiser_id columns (schema migration safe)
  - cj_searcher.py checks get_cached_products_for_interest() before live calls

Sync modes:
  full      — all 130+ interest terms (~2h, run weekly)
  refresh   — top 40 high-value terms (~20min, run nightly)
  targeted  — specific interests from a live session miss (~30s, on-demand)

Usage:
  python3 catalog_sync.py                                  # refresh mode (default)
  python3 catalog_sync.py --mode full                      # full catalog sync
  python3 catalog_sync.py --mode targeted --terms "coffee,yoga,guitar"
  python3 catalog_sync.py --dry-run                        # preview only, no writes
  python3 catalog_sync.py --stats                          # print DB stats and exit

Author: Chad + Claude
Date: February 2026
"""

import os
import re
import sys
import json
import time
import logging
import argparse
import sqlite3
import requests
import urllib.parse
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------

CJ_GRAPHQL_ENDPOINT = "https://ads.api.cj.com/query"

# CJ credentials (from environment — same vars as cj_searcher.py)
CJ_API_KEY     = os.environ.get('CJ_API_KEY', '')
CJ_COMPANY_ID  = os.environ.get('CJ_COMPANY_ID', '')
CJ_PUBLISHER_ID = os.environ.get('CJ_PUBLISHER_ID', '')

# Database path — same DB as database.py
_DB_PATH = os.environ.get('DATABASE_PATH', '/home/user/GiftWise/data/products.db')

# Products per GraphQL page (max 1000; 100 balances depth vs. time)
PRODUCTS_PER_PAGE = 100

# Max pages per term for full sync (100/page × 3 = 300 products/term max)
MAX_PAGES_FULL = 3

# Max pages per term for refresh/targeted sync (100 products per term)
MAX_PAGES_REFRESH = 1

# Hours before a term's cache is considered stale and needs re-sync
CACHE_FRESH_HOURS = 20

# Days before a product not seen in any sync is marked stale
STALE_PRODUCT_DAYS = 14

# Delay between CJ API calls to stay under 500/5min rate limit
# 0.5s → 120/min → 600/5min — slightly over, so use 0.7s → safe
REQUEST_DELAY_SECONDS = 0.7

# Gift price sweet spots — outside these ranges products score lower
PRICE_SWEET_MIN = 15.0
PRICE_SWEET_MAX = 250.0
PRICE_ACCEPTABLE_MIN = 8.0
PRICE_ACCEPTABLE_MAX = 400.0

# Splurge tier: premium items that are the nicest version of something
# the recipient loves, or an extravagant experience product. These bypass
# the normal price penalty and get flagged for the splurge slot.
SPLURGE_PRICE_MIN = 200.0
SPLURGE_PRICE_MAX = 1500.0

# Minimum gift_score to store in DB (skip obvious junk)
MIN_SCORE_TO_STORE = 0.15

# TikTok Shop advertiser ID in CJ — used for TikTok-specific queries
TIKTOK_SHOP_ADV_ID = "7563286"


# ---------------------------------------------------------------------------
# INTEREST TERM CATALOG
# 130+ terms organized by category. priority 1 = run first (highest gifting
# affinity / most common in profiles). priority 2 = run in full sync only.
# ---------------------------------------------------------------------------

INTEREST_CATEGORIES: Dict[str, Dict] = {

    # ===================================================================
    # PRIORITY 1 — High-frequency interests, run in every nightly refresh
    # ===================================================================

    'music': {
        'priority': 1,
        'terms': [
            # Equipment & listening
            'vinyl record', 'record player', 'turntable', 'vinyl album',
            'headphones', 'wireless headphones', 'audiophile headphones',
            'bluetooth speaker', 'portable speaker',
            # Instruments
            'guitar', 'acoustic guitar', 'electric guitar', 'guitar picks',
            'guitar strap', 'guitar capo', 'guitar tuner',
            'piano keyboard', 'midi keyboard', 'ukulele', 'bass guitar',
            'drumsticks', 'drum pad', 'harmonica',
            # Production & accessories
            'music production', 'audio interface', 'studio monitors',
            'record storage', 'vinyl shelf', 'record cleaning kit',
            'concert gift', 'band merchandise', 'music poster',
            'band t-shirt', 'guitar wall mount',
        ]
    },

    'music_genres': {
        'priority': 2,
        'terms': [
            # Genre-specific merch (covers ontology interests)
            'jazz vinyl', 'jazz poster', 'jazz gift',
            'hip hop poster', 'hip hop vinyl',
            'country music gift', 'country vinyl',
            'classical music gift', 'orchestra gift',
            'indie band poster', 'indie vinyl',
            'punk rock poster', 'punk merchandise',
            'EDM festival gear', 'rave accessories',
            '80s music gift', '80s vinyl record',
            '90s music poster', 'retro music gift',
            'rock band poster', 'metal band shirt',
            'reggae vinyl', 'blues vinyl record',
            'folk music gift', 'Americana vinyl',
        ]
    },

    'coffee_tea': {
        'priority': 1,
        'terms': [
            'coffee', 'pour over coffee', 'coffee subscription', 'espresso',
            'coffee grinder', 'coffee maker', 'french press', 'moka pot',
            'coffee mug', 'espresso cup', 'latte art',
            'cold brew maker', 'coffee scale',
            'tea', 'loose leaf tea', 'matcha', 'matcha kit', 'chai',
            'tea infuser', 'teapot', 'tea set',
            'coffee gift set', 'tea gift set',
            'coffee beans', 'single origin coffee',
        ]
    },

    'sports_outdoor': {
        'priority': 1,
        'terms': [
            # Yoga & wellness fitness
            'yoga mat', 'yoga accessories', 'yoga block',
            'pilates ring', 'pilates accessories',
            'resistance bands', 'foam roller',
            # Hiking & camping
            'hiking gear', 'hiking backpack', 'trekking poles',
            'trail running shoes', 'hiking boots',
            'camping gear', 'camping tent', 'sleeping bag',
            'camping cookware', 'headlamp',
            # Running & cycling
            'running gear', 'running shoes', 'fitness tracker',
            'running belt', 'running watch',
            'cycling gear', 'bike accessories', 'cycling jersey',
            'bike light', 'cycling gloves',
            # Fishing
            'fishing gear', 'fly fishing', 'fishing rod',
            'fly tying kit', 'tackle box', 'fishing net',
            'fly fishing accessories', 'fishing vest',
            # Climbing & water sports
            'rock climbing', 'climbing chalk', 'bouldering',
            'climbing harness',
            'surfing', 'surf accessories', 'surf wax',
            'kayaking', 'paddleboard',
            'white water rafting gift',
            # Ball sports
            'soccer cleats', 'soccer gear', 'soccer ball',
            'basketball', 'basketball shoes', 'basketball jersey',
            'basketball hoop', 'basketball training',
            'tennis racket', 'tennis gift',
            'golf', 'golf accessories', 'golf balls',
            'volleyball', 'volleyball gear',
            # Other
            'skiing gear', 'ski goggles', 'snowboard',
            'skateboard', 'skateboard deck',
            'martial arts gear', 'boxing gloves',
            'swimming goggles', 'swim gear',
            'crossfit gear', 'weightlifting belt',
        ]
    },

    'tech_gaming': {
        'priority': 1,
        'terms': [
            # Gaming
            'gaming accessories', 'gaming headset', 'gaming mouse',
            'mechanical keyboard', 'gaming keyboard', 'gaming controller',
            'gaming chair', 'monitor stand', 'streaming setup',
            'gaming desk mat', 'gaming poster',
            'Nintendo Switch accessories', 'PlayStation gift',
            'Xbox accessories', 'retro gaming',
            'gaming gift card',
            # Photography & video
            'photography accessories', 'camera bag', 'camera lens',
            'camera strap', 'tripod', 'photo printer',
            'polaroid camera', 'film camera', 'instant camera',
            # Drones & tech
            'drone', 'fpv drone', 'drone accessories',
            'smart home', 'smart speaker', 'smart light',
            '3D printing filament', '3D printer accessories',
            'webcam', 'ring light', 'microphone',
            'USB hub', 'laptop stand', 'desk organizer',
            'wireless charger', 'portable charger',
            'programming gift', 'developer gift',
        ]
    },

    'beauty_wellness': {
        'priority': 1,
        'terms': [
            # Skincare
            'skincare', 'face serum', 'moisturizer', 'vitamin C serum',
            'sunscreen', 'face mask', 'eye cream',
            'skincare gift set', 'Korean skincare',
            # Fragrance
            'perfume', 'fragrance', 'cologne', 'perfume gift set',
            'perfume sampler', 'room spray',
            # Hair
            'hair care', 'hair oil', 'hair tools', 'hair accessories',
            'hair dryer', 'curling iron', 'silk scrunchie',
            # Nails
            'nail art', 'nail polish', 'nail gel kit',
            # Bath & body
            'bath bomb', 'bath soak', 'spa gift set',
            'body lotion', 'body oil', 'lip balm',
            # Tools & wellness
            'massage tool', 'gua sha', 'jade roller',
            'essential oils', 'aromatherapy diffuser',
            'meditation cushion', 'meditation gift',
            'mindfulness journal', 'wellness gift',
            'self care gift', 'relaxation gift',
        ]
    },

    'food_drink': {
        'priority': 1,
        'terms': [
            # Spirits & cocktails
            'whiskey', 'bourbon', 'whiskey glass', 'cocktail kit',
            'cocktail shaker', 'cocktail smoker kit',
            'whiskey stones', 'decanter set',
            # Wine
            'wine accessory', 'wine decanter', 'wine glass',
            'wine opener', 'wine rack', 'wine tasting',
            'wine subscription', 'wine gift basket',
            # Beer
            'craft beer', 'beer gift', 'home brewing kit',
            'beer glass set', 'beer subscription',
            # Cooking & baking
            'hot sauce', 'spice set', 'gourmet food gift',
            'baking tools', 'cooking gift', 'kitchen gadget',
            'charcuterie board', 'cheese board',
            'cast iron skillet', 'chef knife',
            'apron', 'cookbook', 'recipe book',
            'Thai cooking kit', 'sushi making kit',
            'BBQ accessories', 'grilling tools', 'smoker accessories',
            # Chocolate & sweets
            'chocolate', 'artisan chocolate', 'truffle chocolate',
            'chocolate gift box', 'candy gift',
            # Dietary
            'vegan snacks', 'plant-based food gift',
            'gluten free gift', 'organic food gift',
        ]
    },

    'art_creativity': {
        'priority': 1,
        'terms': [
            # Painting & drawing
            'acrylic paint set', 'watercolor set', 'painting supplies',
            'oil paint set', 'paint brush set', 'canvas',
            'sketchbook', 'drawing pencils', 'colored pencils',
            'art markers', 'charcoal pencils',
            # Pottery & sculpture
            'pottery tools', 'air dry clay', 'pottery wheel',
            'sculpting tools', 'ceramic glaze',
            # Fiber arts
            'knitting needles', 'yarn gift set', 'crochet kit',
            'embroidery kit', 'cross stitch kit',
            'sewing kit', 'quilting supplies',
            # Lettering & paper
            'calligraphy set', 'hand lettering',
            'journaling supplies', 'bullet journal',
            'washi tape', 'sticker set', 'planner',
            # DIY crafts
            'candle making kit', 'soap making kit',
            'resin art kit', 'jewelry making kit',
            'macrame kit', 'tie dye kit',
            'woodworking tools', 'wood carving kit',
            'leather craft kit',
        ]
    },

    'home_lifestyle': {
        'priority': 1,
        'terms': [
            # Candles & ambiance
            'scented candle', 'candle gift set', 'soy candle',
            'incense', 'incense holder',
            # Cozy
            'throw blanket', 'weighted blanket', 'throw pillow',
            'cozy socks', 'slippers',
            # Plants & garden
            'succulent plant', 'plant pot', 'indoor plant',
            'herb garden kit', 'terrarium kit',
            'gardening tools', 'garden gloves',
            'plant hanger', 'watering can',
            # Art & decor
            'wall art print', 'framed art', 'art poster',
            'photo frame', 'floating shelf',
            'home decor', 'aesthetic home',
            'decorative tray', 'vase',
            # Books & games
            'book', 'coffee table book', 'novel',
            'board game', 'card game', 'puzzle',
            'strategy board game', 'party game',
            'jigsaw puzzle', '1000 piece puzzle',
            # Stationery
            'journal', 'leather journal', 'notebook',
            'fountain pen', 'pen set', 'desk accessories',
        ]
    },

    'pets': {
        'priority': 1,
        'terms': [
            'dog toy', 'dog treats', 'dog collar', 'dog leash', 'dog bed',
            'dog bandana', 'dog sweater', 'dog harness',
            'cat toy', 'cat tree', 'cat accessories',
            'cat bed', 'cat scratcher', 'catnip toy',
            'pet portrait', 'personalized pet gift',
            'pet memorial', 'paw print kit',
            'bird feeder', 'aquarium accessory',
        ]
    },

    # ===================================================================
    # PRIORITY 2 — Run in weekly full sync, less common but important
    # ===================================================================

    'fashion_accessories': {
        'priority': 2,
        'terms': [
            # Wallets & bags
            'leather wallet', 'bifold wallet', 'card holder',
            'tote bag', 'canvas bag', 'crossbody bag',
            'backpack', 'weekender bag',
            # Eyewear
            'sunglasses', 'polarized sunglasses', 'blue light glasses',
            # Jewelry
            'jewelry', 'minimalist necklace', 'earrings', 'bracelet',
            'gold necklace', 'silver earrings', 'charm bracelet',
            'pendant necklace', 'hoop earrings', 'ring',
            # Watches
            'watch', 'men watch', 'women watch', 'smart watch',
            # Hats & headwear
            'hat', 'baseball cap', 'bucket hat', 'beanie',
            # Shoes
            'sneakers', 'shoes gift',
            # Clothing
            'streetwear', 'graphic tee', 'hoodie',
            'sustainable fashion', 'ethical clothing',
            'vintage clothing', 'denim jacket',
            # Scarves & accessories
            'silk scarf', 'winter scarf', 'gloves',
            'hair clip', 'scrunchie set',
        ]
    },

    'fandoms_entertainment': {
        'priority': 2,
        'terms': [
            # Anime & manga
            'anime merchandise', 'anime figure', 'manga',
            'anime poster', 'anime wall scroll',
            'Studio Ghibli gift', 'Naruto merchandise',
            # K-pop
            'K-pop merchandise', 'K-pop album', 'K-pop poster',
            # Specific fandoms
            'Taylor Swift merchandise', 'Swiftie gift',
            'Star Wars gift', 'Star Wars poster',
            'Marvel gift', 'Marvel poster',
            'Disney gift', 'Disney merchandise',
            'Harry Potter gift', 'Harry Potter merchandise',
            'Lord of the Rings gift',
            'Pokemon merchandise', 'Pokemon gift',
            # Broadway & theater
            'Broadway merchandise', 'Hamilton merchandise',
            'musical theater gift', 'Broadway poster',
            # TV & film
            'sports fan gift', 'fan merchandise',
            'movie poster', 'TV show merchandise',
            'film poster', 'cinema gift',
            'Muppets merchandise', 'Jim Henson gift',
            # Retro & nostalgia
            'retro movie poster', '80s nostalgia gift',
            '90s nostalgia gift', 'vintage poster',
        ]
    },

    'niche_high_value': {
        'priority': 2,
        'terms': [
            # RC & models
            'RC car', 'remote control car', 'RC hobby',
            'model train', 'miniature figurines',
            'model kit', 'scale model',
            # Astronomy
            'telescope', 'astronomy kit', 'stargazing',
            'star map poster', 'constellation gift',
            # Strategy & games
            'chess set', 'premium chess',
            'Dungeons and Dragons', 'D&D dice set',
            'D&D miniatures', 'tabletop RPG',
            # Leather & craft
            'leather goods', 'handmade leather',
            # Outdoors niche
            'archery set', 'hunting accessory',
            'bird watching binoculars', 'field guide',
            # Automotive & motorsport
            'Formula 1 merchandise', 'F1 poster',
            'car enthusiast gift', 'automotive gift',
            # Collectibles
            'trading cards', 'sports cards',
            'coin collecting', 'stamp collecting',
        ]
    },

    'spirituality_astrology': {
        'priority': 2,
        'terms': [
            'astrology gift', 'zodiac necklace',
            'birth chart poster', 'horoscope gift',
            'tarot cards', 'tarot deck', 'oracle cards',
            'crystal set', 'crystal gift',
            'sage bundle', 'smudge kit',
            'moon phase wall art', 'celestial jewelry',
        ]
    },

    'travel_adventure': {
        'priority': 2,
        'terms': [
            'travel accessories', 'packing cubes',
            'travel journal', 'scratch off map',
            'passport holder', 'luggage tag',
            'travel pillow', 'travel adapter',
            'adventure gift', 'experience gift',
            'travel photo book', 'world map poster',
        ]
    },

    'reading_literature': {
        'priority': 2,
        'terms': [
            # Books by genre (gift editions)
            'sci-fi book', 'fantasy novel',
            'true crime book', 'history book',
            'philosophy book', 'classic literature',
            'graphic novel', 'comic book',
            # Reader accessories
            'bookshelf', 'book ends', 'book light',
            'bookmark', 'leather bookmark',
            'book sleeve', 'reading pillow',
            'book subscription box', 'book lover gift',
            'e-reader case', 'Kindle accessories',
        ]
    },

    'sustainability_lifestyle': {
        'priority': 2,
        'terms': [
            'reusable water bottle', 'insulated bottle',
            'beeswax wrap', 'reusable straw',
            'bamboo utensils', 'zero waste kit',
            'eco friendly gift', 'sustainable gift',
            'compost bin', 'seed starting kit',
            'solar charger', 'recycled materials',
        ]
    },

    'dance_performance': {
        'priority': 2,
        'terms': [
            'dance accessories', 'dance shoes',
            'ballet gift', 'ballet accessories',
            'dance poster', 'dance jewelry',
            'leg warmers', 'dance bag',
        ]
    },

    'specific_artists_brands': {
        'priority': 2,
        'terms': [
            # These cover real user session interests that had zero catalog coverage
            'Stevie Nicks merchandise', 'Fleetwood Mac vinyl',
            'Sinead O Connor vinyl', 'Dolly Parton gift',
            'Beatles merchandise', 'Beatles vinyl',
            'Bob Marley poster', 'David Bowie poster',
            'Beyonce merchandise', 'Adele vinyl',
            'BTS merchandise', 'Blackpink merchandise',
            'Billie Eilish merchandise',
            'Bad Bunny merchandise',
            'Drake merchandise', 'Kanye merch',
            'The Office merchandise', 'Friends TV gift',
            'Stranger Things gift', 'Game of Thrones gift',
        ]
    },

    'home_theater_av': {
        'priority': 2,
        'terms': [
            # Projectors & home cinema (for AWOL Vision — Awin ID 98169)
            'projector', 'home projector', 'portable projector',
            'outdoor projector', 'mini projector',
            'home theater', 'home cinema',
            'projector screen', 'projection screen',
            'movie night setup', 'backyard movie',
            '4K projector', 'laser projector',
        ]
    },

    'body_jewelry_piercing': {
        'priority': 2,
        'terms': [
            # Body jewelry & piercing (for OUFER Body Jewelry — Awin ID 91941)
            'body jewelry', 'body piercing jewelry',
            'nose ring', 'septum ring', 'septum jewelry',
            'belly button ring', 'navel jewelry',
            'helix earring', 'cartilage earring',
            'tragus earring', 'daith piercing jewelry',
            'industrial barbell', 'piercing jewelry set',
            'nipple ring', 'lip ring',
            'tongue ring', 'eyebrow ring',
            'surgical steel jewelry', 'titanium body jewelry',
        ]
    },
}

# Flat ordered list: (term, priority, category)
ALL_SYNC_TERMS: List[Tuple[str, int, str]] = sorted(
    [
        (term, cat_data['priority'], cat_name)
        for cat_name, cat_data in INTEREST_CATEGORIES.items()
        for term in cat_data['terms']
    ],
    key=lambda x: (x[1], x[0])
)

# Top 40 highest-priority terms for nightly refresh (keeps sync under ~20 min)
REFRESH_TERMS = [
    # Music (5)
    'vinyl record', 'headphones', 'bluetooth speaker', 'guitar', 'band merchandise',
    # Coffee/tea (4)
    'coffee', 'pour over coffee', 'espresso', 'tea',
    # Sports/outdoor (10)
    'yoga mat', 'hiking gear', 'camping gear', 'running gear', 'fishing gear',
    'basketball', 'cycling gear', 'surfing', 'skiing gear', 'golf',
    # Tech/gaming (5)
    'gaming accessories', 'gaming headset', 'mechanical keyboard', 'drone', 'photography accessories',
    # Beauty/wellness (5)
    'skincare', 'perfume', 'bath bomb', 'essential oils', 'self care gift',
    # Food/drink (5)
    'whiskey', 'cocktail kit', 'craft beer', 'chocolate', 'cooking gift',
    # Art/creativity (4)
    'acrylic paint set', 'watercolor set', 'embroidery kit', 'candle making kit',
    # Home (5)
    'scented candle', 'throw blanket', 'succulent plant', 'board game', 'puzzle',
    # Pets (2)
    'dog toy', 'cat toy',
    # Stationery (2)
    'journal', 'leather journal',
    # Fashion (3)
    'jewelry', 'watch', 'sunglasses',
    # Fandoms (4)
    'anime merchandise', 'Taylor Swift merchandise', 'Broadway merchandise', 'movie poster',
    # Niche (2)
    'trading cards', 'tarot cards',
]


# ---------------------------------------------------------------------------
# SCHEMA MIGRATION
# Extends the existing products table with gift_score + advertiser_id,
# and creates catalog_sync_log to track per-term freshness.
# Safe to call on every startup — all operations are IF NOT EXISTS / IGNORE.
# ---------------------------------------------------------------------------

def ensure_catalog_schema():
    """
    Migrate the products table to support catalog sync columns,
    and create the catalog_sync_log table for freshness tracking.
    Called automatically on import.
    """
    os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)
    conn = sqlite3.connect(_DB_PATH, timeout=10)  # timeout prevents indefinite lock-wait
    try:
        cur = conn.cursor()

        # Add gift_score column to products (pre-computed suitability 0.0–1.0)
        try:
            cur.execute("ALTER TABLE products ADD COLUMN gift_score REAL DEFAULT 0.5")
            logger.debug("Added gift_score column to products table")
        except sqlite3.OperationalError:
            pass  # Column already exists

        # Add advertiser_id column (CJ advertiser, e.g. "7563286" for TikTok Shop)
        try:
            cur.execute("ALTER TABLE products ADD COLUMN cj_advertiser_id TEXT")
            logger.debug("Added cj_advertiser_id column to products table")
        except sqlite3.OperationalError:
            pass  # Column already exists

        # Add Awin advertiser_id column
        try:
            cur.execute("ALTER TABLE products ADD COLUMN awin_advertiser_id TEXT")
            logger.debug("Added awin_advertiser_id column to products table")
        except sqlite3.OperationalError:
            pass  # Column already exists

        # Catalog sync log: one row per term, updated each sync run
        cur.execute("""
            CREATE TABLE IF NOT EXISTS catalog_sync_log (
                term            TEXT PRIMARY KEY,
                category        TEXT,
                last_synced_at  TIMESTAMP,
                products_found  INTEGER DEFAULT 0,
                products_stored INTEGER DEFAULT 0,
                avg_gift_score  REAL DEFAULT 0.0,
                sync_mode       TEXT DEFAULT 'refresh'
            )
        """)

        # Index gift_score for fast "top gift candidates" queries
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_gift_score ON products(gift_score)"
        )
        # Index cj_advertiser_id for TikTok Shop-specific queries
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_cj_advertiser ON products(cj_advertiser_id)"
        )

        conn.commit()
        logger.debug("Catalog schema migration complete")

    except Exception as e:
        conn.rollback()
        logger.error(f"Schema migration failed: {e}")
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# GIFT SUITABILITY SCORER
# Runs at sync time on every product before it's stored.
# Returns 0.0–1.0; products below MIN_SCORE_TO_STORE are discarded.
# ---------------------------------------------------------------------------

# Patterns that disqualify a product as a gift (strong penalty)
_BORING_TITLE_PATTERNS = [
    'cable organizer', 'cord organizer', 'cable management',
    'extension cord', 'power strip', 'surge protector',
    'travel adapter', 'wall adapter', 'plug adapter',
    'first aid kit', 'medicine organizer', 'pill case', 'pill organizer',
    'luggage tag', 'packing cube', 'compression bag', 'toiletry bag',
    'label maker', 'label printer', 'drawer organizer', 'storage bin',
    'phone stand', 'tablet stand', 'screen protector', 'phone case',
    'cable clip', 'zip tie', 'velcro strap',
]

# Bulk/multi-pack signals (penalty — not gifts, they're supply runs)
_BULK_PATTERNS = [
    ' pack of ', ' lot of ', ' set of 10', ' set of 20', ' set of 50',
    '100 pack', '50 pack', '25 pack', 'value pack', 'bulk pack',
    'multi pack', 'multipack', '(10 count)', '(20 count)', '(50 count)',
]

# Gifting trope patterns (light penalty — not disqualifying, just attenuated)
_TROPE_PATTERNS = [
    'generic gift basket', 'generic gift set', 'assorted gift',
    'variety gift', 'mystery gift',
]


def score_product_gift_suitability(product: Dict) -> float:
    """
    Score a CJ product 0.0–1.0 for gift suitability.

    This runs once at sync time, not per session. The result is stored as
    gift_score in the products table. The curator makes final taste judgments;
    this removes the obviously un-giftable items and boosts clear winners.

    Scoring factors:
      + Has a real product image (+0.15)
      + Price in sweet spot $15–$250 (+0.12)
      + Price in acceptable range $8–$400 (+0.06)
      + Description has substance ≥80 chars (+0.10)
      + Clean title (4–12 words, not keyword-stuffed) (+0.06)
      + Brand is set (not anonymous marketplace listing) (+0.05)
      − Boring/practical item patterns (−0.35)
      − Bulk/multi-pack patterns (−0.30)
      − Gifting trope patterns (−0.08)
      − Too cheap (< $8, likely low quality) (−0.15)
      − Too expensive (> $400, outside most gift budgets) (−0.08)
      − Very short description < 20 chars (−0.08)
    """
    score = 0.5  # neutral baseline

    title = (product.get('title') or '').lower().strip()
    desc  = (product.get('description') or '').lower().strip()
    image = product.get('image_url') or ''
    brand = product.get('brand') or ''
    price = product.get('price') or 0.0

    try:
        price = float(price)
    except (TypeError, ValueError):
        price = 0.0

    # --- Positive signals ---

    if image and image.startswith('http') and len(image) > 20:
        score += 0.15  # Real image = revenue-generating product

    if PRICE_SWEET_MIN <= price <= PRICE_SWEET_MAX:
        score += 0.12
    elif SPLURGE_PRICE_MIN <= price <= SPLURGE_PRICE_MAX:
        # Splurge-tier items: don't penalize, give moderate boost.
        # These are premium versions of real gifts (e-bikes, high-end gear).
        # The splurge slot selection logic picks from these separately.
        score += 0.08
    elif PRICE_ACCEPTABLE_MIN <= price <= PRICE_ACCEPTABLE_MAX:
        score += 0.06

    if len(desc) >= 80:
        score += 0.10
    elif len(desc) < 20 and len(desc) > 0:
        score -= 0.08

    word_count = len(title.split())
    if 4 <= word_count <= 12:
        score += 0.06

    if brand and len(brand.strip()) > 1:
        score += 0.05

    # --- Negative signals ---

    if any(p in title for p in _BORING_TITLE_PATTERNS):
        score -= 0.35  # Not a gift. Period.

    if any(p in title for p in _BULK_PATTERNS):
        score -= 0.30  # Supply run, not a gift

    if any(p in title for p in _TROPE_PATTERNS):
        score -= 0.08  # Trope — attenuate but don't eliminate

    if 0 < price < PRICE_ACCEPTABLE_MIN:
        score -= 0.15  # Likely junk

    if price > SPLURGE_PRICE_MAX:
        score -= 0.15  # Above even splurge range — likely not a gift
    elif price > PRICE_ACCEPTABLE_MAX and price < SPLURGE_PRICE_MIN:
        score -= 0.08  # Awkward middle: too expensive for regular, too cheap for splurge

    return round(max(0.0, min(1.0, score)), 3)


# ---------------------------------------------------------------------------
# FORMAT CONVERTER
# Converts a products-table row back to GiftWise standard product dict
# (same keys as what search_products_cj() / _parse_graphql_response() return).
# ---------------------------------------------------------------------------

def _db_row_to_giftwise_format(row: Dict, interest: str) -> Dict:
    """Convert a products-table row to the GiftWise standard product dict."""
    price_raw = row.get('price') or 0.0
    try:
        price_str = f"${float(price_raw):.2f}"
    except (TypeError, ValueError):
        price_str = "Price varies"

    image = row.get('image_url') or ''

    return {
        'title':         row.get('title', ''),
        'link':          row.get('affiliate_link', ''),
        'snippet':       row.get('description', ''),
        'image':         image,
        'thumbnail':     image,
        'image_url':     image,
        'source_domain': row.get('retailer', 'cj'),
        'price':         price_str,
        'product_id':    row.get('product_id', ''),
        'search_query':  interest,
        'interest_match': interest,
        'priority':      2,
        'brand':         row.get('brand', ''),
        'advertiser_id': row.get('cj_advertiser_id', ''),
        'gift_score':    row.get('gift_score', 0.5),
    }


# ---------------------------------------------------------------------------
# CJ GRAPHQL FETCHER
# Low-level pagination layer. One page = one API call.
# ---------------------------------------------------------------------------

def _build_cj_headers() -> Dict:
    if not CJ_API_KEY:
        raise ValueError("CJ_API_KEY not set")
    return {
        "Authorization": f"Bearer {CJ_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _build_cj_query(keyword: str, offset: int = 0, limit: int = PRODUCTS_PER_PAGE,
                    advertiser_id: Optional[str] = None) -> str:
    """Build CJ GraphQL query for a single keyword with optional advertiser filter."""
    keyword_json = json.dumps([keyword])
    advertiser_filter = f'advertiserId: "{advertiser_id}",' if advertiser_id else ''

    return f"""
    {{
      products(
        companyId: "{CJ_COMPANY_ID}",
        keywords: {keyword_json},
        partnerStatus: JOINED,
        {advertiser_filter}
        limit: {limit},
        offset: {offset}
      ) {{
        totalCount
        count
        resultList {{
          id
          title
          description
          price {{ amount currency }}
          imageLink
          link
          brand
          advertiserId
          advertiserName
          linkCode(pid: "{CJ_PUBLISHER_ID}") {{
            clickUrl
          }}
        }}
      }}
    }}
    """


def _fetch_cj_page(keyword: str, page: int = 0,
                   advertiser_id: Optional[str] = None) -> Tuple[List[Dict], int]:
    """
    Fetch one page of CJ products for a keyword.
    Returns (products_list, total_count).
    Products with no affiliate link (non-joined advertiser) are filtered out.
    """
    offset = page * PRODUCTS_PER_PAGE
    query = _build_cj_query(keyword, offset=offset, advertiser_id=advertiser_id)

    try:
        resp = requests.post(
            CJ_GRAPHQL_ENDPOINT,
            json={"query": query},
            headers=_build_cj_headers(),
            timeout=30,
        )
    except requests.RequestException as e:
        logger.warning(f"CJ request failed for '{keyword}' page {page}: {e}")
        return [], 0

    if resp.status_code == 429:
        logger.warning("CJ rate limit hit — sleeping 60s")
        time.sleep(60)
        return [], 0

    if resp.status_code != 200:
        logger.warning(f"CJ HTTP {resp.status_code} for '{keyword}': {resp.text[:200]}")
        return [], 0

    data = resp.json()
    if 'errors' in data:
        logger.warning(f"CJ GraphQL errors for '{keyword}': {data['errors']}")
        return [], 0

    products_data = data.get('data', {}).get('products', {})
    total_count   = products_data.get('totalCount', 0)
    result_list   = products_data.get('resultList', [])

    parsed = []
    for item in result_list:
        link_code = item.get('linkCode')
        if not link_code or not isinstance(link_code, dict):
            continue  # Non-joined advertiser — skip

        click_url = link_code.get('clickUrl', '')
        if not click_url:
            continue

        price_obj = item.get('price') or {}
        try:
            price_val = float(price_obj.get('amount') or 0)
        except (TypeError, ValueError):
            price_val = 0.0

        parsed.append({
            'product_id':    item.get('id', ''),
            'retailer':      item.get('advertiserName', 'CJ'),
            'title':         item.get('title', ''),
            'description':   (item.get('description') or '')[:500],
            'price':         price_val,
            'currency':      price_obj.get('currency', 'USD'),
            'image_url':     item.get('imageLink', ''),
            'affiliate_link': click_url,
            'brand':         item.get('brand', ''),
            'cj_advertiser_id': item.get('advertiserId', ''),
        })

    return parsed, total_count


# ---------------------------------------------------------------------------
# TERM SYNC
# Fetches all pages for one term, scores products, upserts to DB.
# ---------------------------------------------------------------------------

def is_term_cache_fresh(term: str, max_age_hours: float = CACHE_FRESH_HOURS) -> bool:
    """
    Return True if the term was synced within max_age_hours.
    Used by cj_searcher.py to decide whether to use cache or hit live API.
    """
    try:
        conn = sqlite3.connect(_DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            "SELECT last_synced_at FROM catalog_sync_log WHERE term = ?",
            (term.lower(),)
        )
        row = cur.fetchone()
        conn.close()

        if not row or not row['last_synced_at']:
            return False

        synced_at = datetime.fromisoformat(row['last_synced_at'])
        age = datetime.now() - synced_at
        return age < timedelta(hours=max_age_hours)

    except Exception:
        return False


def get_cached_products_for_interest(
    interest: str,
    min_gift_score: float = 0.35,
    limit: int = 60,
) -> List[Dict]:
    """
    Return cached CJ products for an interest term in GiftWise standard format.

    This is the main cache-lookup function called by cj_searcher.py.
    Returns an empty list if the cache is cold (term never synced).

    Products are ranked by gift_score DESC, then popularity_score DESC,
    so the curator sees the highest-quality candidates first.

    Args:
        interest:       Interest/search term to look up
        min_gift_score: Filter out products below this threshold (default 0.35)
        limit:          Max products to return (default 60)
    """
    try:
        conn = sqlite3.connect(_DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
            SELECT *
            FROM products
            WHERE in_stock = 1
              AND removed_at IS NULL
              AND (cj_advertiser_id != '' OR awin_advertiser_id IS NOT NULL)
              AND (
                    interest_tags LIKE ?
                    OR title       LIKE ?
                    OR description LIKE ?
              )
              AND (gift_score IS NULL OR gift_score >= ?)
            ORDER BY gift_score DESC, popularity_score DESC
            LIMIT ?
        """, (
            f'%"{interest.lower()}"%',
            f'%{interest}%',
            f'%{interest}%',
            min_gift_score,
            limit,
        ))
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()

        return [_db_row_to_giftwise_format(r, interest) for r in rows]

    except Exception as e:
        logger.error(f"Cache lookup failed for '{interest}': {e}")
        return []


def get_cached_awin_products_for_interest(
    interest: str,
    min_gift_score: float = 0.35,
    limit: int = 30,
) -> List[Dict]:
    """
    Return cached Awin-only products for an interest term.

    Called by awin_searcher.py to check whether the nightly sync has
    already populated the DB for this interest. If it has, live feed
    downloads can be skipped entirely.

    Args:
        interest:       Interest/search term to look up
        min_gift_score: Filter out products below this threshold (default 0.35)
        limit:          Max products to return (default 30)
    """
    try:
        conn = sqlite3.connect(_DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
            SELECT *
            FROM products
            WHERE in_stock = 1
              AND removed_at IS NULL
              AND awin_advertiser_id IS NOT NULL
              AND awin_advertiser_id != ''
              AND (
                    interest_tags LIKE ?
                    OR title       LIKE ?
                    OR description LIKE ?
              )
              AND (gift_score IS NULL OR gift_score >= ?)
            ORDER BY gift_score DESC, popularity_score DESC
            LIMIT ?
        """, (
            f'%"{interest.lower()}"%',
            f'%{interest}%',
            f'%{interest}%',
            min_gift_score,
            limit,
        ))
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()

        return [_db_row_to_giftwise_format(r, interest) for r in rows]

    except Exception as e:
        logger.error(f"Awin cache lookup failed for '{interest}': {e}")
        return []


def _upsert_catalog_product(product: Dict, gift_score: float,
                             interest_tags: List[str], conn: sqlite3.Connection):
    """Upsert one product into the products table with gift_score, tags, and category.

    On conflict, merges new interest_tags with existing ones (union, preserving order).
    This lets CJ products accumulate tags across multiple sync terms.
    """
    from post_curation_cleanup import detect_category

    cur = conn.cursor()
    now = datetime.now().isoformat()
    category = detect_category(product.get('title', ''), product.get('description', ''))

    product_id = product.get('product_id')
    retailer = product.get('retailer', 'CJ')

    # Merge tags: read existing, union with new, preserving order (new first)
    existing_tags = []
    try:
        cur.execute(
            "SELECT interest_tags FROM products WHERE product_id = ? AND retailer = ?",
            (product_id, retailer)
        )
        row = cur.fetchone()
        if row and row[0]:
            existing_tags = json.loads(row[0])
    except Exception:
        pass
    merged_tags = list(dict.fromkeys(interest_tags + existing_tags))

    cur.execute("""
        INSERT INTO products (
            product_id, retailer, title, description, price, currency,
            image_url, affiliate_link, brand, category, interest_tags,
            in_stock, last_checked, last_updated,
            gift_score, cj_advertiser_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?)
        ON CONFLICT(product_id, retailer) DO UPDATE SET
            title           = excluded.title,
            description     = excluded.description,
            price           = excluded.price,
            image_url       = excluded.image_url,
            affiliate_link  = excluded.affiliate_link,
            category        = excluded.category,
            interest_tags   = excluded.interest_tags,
            in_stock        = 1,
            last_checked    = excluded.last_checked,
            last_updated    = excluded.last_updated,
            gift_score      = excluded.gift_score,
            cj_advertiser_id = excluded.cj_advertiser_id
    """, (
        product_id,
        retailer,
        product.get('title', ''),
        product.get('description', ''),
        product.get('price', 0.0),
        product.get('currency', 'USD'),
        product.get('image_url', ''),
        product.get('affiliate_link', ''),
        product.get('brand', ''),
        category,
        json.dumps(merged_tags),
        now,
        now,
        gift_score,
        product.get('cj_advertiser_id', ''),
    ))


# ---------------------------------------------------------------------------
# AWIN CATALOG SYNC
# Downloads Awin feed CSVs for all joined advertisers, scores products,
# tags with matching catalog interest terms, and upserts to the products table.
# Architecture mirrors the CJ sync above but uses Awin's CSV-based feed API
# instead of CJ's GraphQL endpoint.
# ---------------------------------------------------------------------------

# Awin credentials
AWIN_API_KEY = os.environ.get('AWIN_DATA_FEED_API_KEY', '')

# Awin sync price cap — raised from $200 to $1500 (Mar 2026) to allow
# splurge-worthy items (premium e-bikes, high-end kitchen gear, etc.)
# into the DB. The gift_score function and splurge tier logic handle
# quality filtering; the cap just prevents absurd outliers.
AWIN_SYNC_MAX_PRICE_USD = 1500

# Max rows to read per feed. Awin feeds can be huge; cap to keep sync time sane.
AWIN_MAX_ROWS_PER_FEED = 5000

# Buffer per feed download (8 MB covers ~5000 rows comfortably)
AWIN_BUFFER_BYTES = 8 * 1024 * 1024

# Domains hard-blocked from Awin (mirrors _AWIN_BLOCKED_DOMAINS in awin_searcher.py)
_AWIN_SYNC_BLOCKED_ADVERTISER_NAMES = {"yadea", "posie and penn", "king koil"}

# Flat list of all catalog terms for interest tagging
_ALL_CATALOG_TERMS: List[str] = [t for (t, _p, _c) in ALL_SYNC_TERMS]


def _awin_row_to_catalog_product(row: Dict, advertiser_name: str, advertiser_id: str) -> Optional[Dict]:
    """Convert one Awin CSV feed row into a catalog product dict for storage."""
    def ci(row, *keys):
        for k in keys:
            v = row.get(k)
            if v:
                return v.strip() if isinstance(v, str) else v
        row_lower = {k.lower().strip(): v for k, v in row.items()}
        for k in keys:
            v = row_lower.get(k.lower().strip())
            if v:
                return v.strip() if isinstance(v, str) else v
        return ""

    title = ci(row, "product_name", "product name", "title", "product_title",
               "name", "Product Name", "Title")
    link  = ci(row, "aw_deep_link", "merchant_deep_link", "deep_link", "link",
               "aw_product_url", "product_url", "URL")
    image = ci(row, "merchant_image_url", "aw_image_url", "aw_thumb_url",
               "image_url", "image_link", "Image URL", "Merchant Image URL")
    price_str = ci(row, "search_price", "store_price", "price", "Price",
                   "rrp_price", "display_price")
    desc  = ci(row, "product_short_description", "description", "Description",
               "product_description", "Product Description")
    brand = ci(row, "brand_name", "brand", "Brand Name", "Brand")
    pid   = ci(row, "aw_product_id", "merchant_product_id", "product_id", "Product ID")

    if not title or not link:
        return None

    try:
        price_val = float(re.sub(r'[^\d.]', '', str(price_str))) if price_str else 0.0
    except (ValueError, TypeError):
        price_val = 0.0

    if not pid:
        pid = str(hash(title + link))[:16]

    return {
        'product_id':        pid,
        'retailer':          advertiser_name or 'Awin',
        'title':             title[:200],
        'description':       (desc or '')[:500],
        'price':             price_val,
        'currency':          'USD',
        'image_url':         image or '',
        'affiliate_link':    link,
        'brand':             brand or '',
        'awin_advertiser_id': str(advertiser_id),
    }


def _tag_awin_product_with_interests(title: str, description: str,
                                      term_list: List[str]) -> List[str]:
    """
    Return all catalog terms whose keywords appear in this product's text.
    Used at sync time to pre-tag Awin/CJ products for fast DB lookup.

    Both single-word and multi-word terms require word-boundary matches.
    This prevents "music" from matching "musical", "jim" from matching "jimmy",
    and multi-word terms like "80s music" from tagging every product that
    mentions "music" somewhere in a different context.
    """
    text = ' ' + (title + ' ' + description).lower() + ' '
    generic = {"and", "the", "or", "with", "gift", "accessories",
               "lover", "fan", "from", "for", "set", "kit"}
    matching = []

    def _word_boundary_match(w: str) -> bool:
        """Check if word appears at a word boundary in text."""
        return ((' ' + w + ' ') in text or (' ' + w + ',') in text or
                (' ' + w + '.') in text or (' ' + w + ')') in text or
                (' ' + w + "'") in text or (' ' + w + '"') in text or
                (' ' + w + '-') in text or (' ' + w + '/') in text or
                text.startswith(w + ' ') or ('"' + w) in text)

    for term in term_list:
        words = [w.lower() for w in term.split()
                 if len(w) > 2 and w.lower() not in generic]
        if not words:
            continue
        # All keywords (single or multi-word) require word boundary match.
        # This prevents "jim" matching "jimmy", "music" matching "musical",
        # and cross-context matches like a gardening set being tagged "wine tasting"
        # because its description mentions "wine" and "tasting" in unrelated contexts.
        if all(_word_boundary_match(w) for w in words):
            matching.append(term.lower())
    return matching


def _upsert_awin_catalog_product(product: Dict, gift_score: float,
                                  interest_tags: List[str], conn: sqlite3.Connection):
    """Upsert one Awin product into the products table with category."""
    from post_curation_cleanup import detect_category

    cur = conn.cursor()
    now = datetime.now().isoformat()
    category = detect_category(product.get('title', ''), product.get('description', ''))

    cur.execute("""
        INSERT INTO products (
            product_id, retailer, title, description, price, currency,
            image_url, affiliate_link, brand, category, interest_tags,
            in_stock, last_checked, last_updated,
            gift_score, awin_advertiser_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?)
        ON CONFLICT(product_id, retailer) DO UPDATE SET
            title            = excluded.title,
            description      = excluded.description,
            price            = excluded.price,
            image_url        = excluded.image_url,
            affiliate_link   = excluded.affiliate_link,
            category         = excluded.category,
            in_stock         = 1,
            last_checked     = excluded.last_checked,
            last_updated     = excluded.last_updated,
            gift_score       = excluded.gift_score,
            interest_tags    = excluded.interest_tags,
            awin_advertiser_id = excluded.awin_advertiser_id
    """, (
        product['product_id'], product['retailer'],
        product['title'], product['description'],
        product['price'], product['currency'],
        product['image_url'], product['affiliate_link'], product['brand'],
        category,
        json.dumps(interest_tags),
        now, now,
        gift_score, product['awin_advertiser_id'],
    ))


def _download_awin_feed(feed_url: str, buffer_bytes: int = AWIN_BUFFER_BYTES) -> Optional[bytes]:
    """Download an Awin feed CSV; returns raw bytes or None on failure."""
    import gzip as _gzip, zlib as _zlib
    try:
        r = requests.get(feed_url, timeout=90, stream=True)
        r.raise_for_status()
    except requests.RequestException as e:
        logger.warning("Awin feed download failed (%s): %s", feed_url[:60], e)
        return None

    r.raw.decode_content = True
    try:
        chunks = []
        total = 0
        for chunk in r.iter_content(chunk_size=64 * 1024):
            chunks.append(chunk)
            total += len(chunk)
            if total >= buffer_bytes:
                break
        r.close()
        data = b"".join(chunks)
    except Exception as e:
        logger.warning("Awin feed read error: %s", e)
        try:
            r.close()
        except Exception:
            pass
        return None

    if not data:
        return None

    # Awin feeds often gzip without Content-Encoding header
    if data[:2] == b'\x1f\x8b':
        try:
            data = _gzip.decompress(data)
        except Exception:
            try:
                data = _zlib.decompress(data, _zlib.MAX_WBITS | 16)
            except Exception:
                pass  # Return as-is; CSV parser will handle the error

    return data


def sync_awin_feeds(dry_run: bool = False) -> Dict:
    """
    Download all joined Awin feeds, score and tag products, upsert to SQLite.

    Called by run_catalog_sync() at the end of each sync run.
    Products are tagged with all matching catalog interest terms so the
    DB cache lookup (get_cached_awin_products_for_interest) can serve
    them without any live feed download.

    Returns stats dict: feeds_synced, total_found, total_stored, total_skipped.
    """
    import csv as _csv
    import io as _io

    empty_stats = {'feeds_synced': 0, 'total_found': 0,
                   'total_stored': 0, 'total_skipped': 0}

    if not AWIN_API_KEY:
        logger.info("Awin sync skipped — AWIN_DATA_FEED_API_KEY not set")
        return empty_stats

    # Fetch the Awin feed list
    try:
        resp = requests.get(
            f"https://productdata.awin.com/datafeed/list/apikey/{AWIN_API_KEY}",
            timeout=30,
        )
        resp.raise_for_status()
        feed_list_text = resp.text
    except Exception as e:
        logger.warning("Awin feed list request failed: %s", e)
        return {**empty_stats, 'error': str(e)}

    # Parse feed list CSV — filter to joined feeds only
    _active_statuses = {"joined", "active", "approved", "yes", "1", "true"}
    _adult_keywords  = {"pleasure", "erotic", "lingerie", "adult", "sex", "fetish"}
    feeds = []
    try:
        reader = _csv.DictReader(_io.StringIO(feed_list_text))
        for row in reader:
            ci = {k.lower().strip(): v for k, v in row.items()}
            url_val    = (ci.get("url") or "").strip()
            advertiser = (ci.get("advertiser name") or ci.get("advertiser_name") or "").strip()
            adv_id     = (ci.get("advertiser id") or ci.get("advertiser_id") or "").strip()
            status     = (ci.get("membership status") or ci.get("membership_status")
                          or ci.get("joined") or ci.get("status") or "").strip()
            feed_name  = (ci.get("feed name") or ci.get("feed_name") or "").strip()

            if not url_val or status.lower() not in _active_statuses:
                continue
            text_check = (advertiser + ' ' + feed_name).lower()
            if any(k in text_check for k in _adult_keywords):
                continue
            if advertiser.lower() in _AWIN_SYNC_BLOCKED_ADVERTISER_NAMES:
                continue
            feeds.append({'url': url_val, 'advertiser': advertiser,
                          'advertiser_id': adv_id})
    except Exception as e:
        logger.warning("Awin feed list parse failed: %s", e)
        return {**empty_stats, 'error': str(e)}

    # Deduplicate by advertiser name (keep first/best feed per advertiser)
    seen_adv = set()
    unique_feeds = []
    for f in feeds:
        key = f['advertiser'].lower()
        if key not in seen_adv:
            seen_adv.add(key)
            unique_feeds.append(f)

    logger.info("=" * 60)
    logger.info("AWIN CATALOG SYNC — %d joined feeds", len(unique_feeds))
    logger.info("=" * 60)

    total_found = total_stored = total_skipped = 0

    for idx, feed_info in enumerate(unique_feeds, 1):
        advertiser = feed_info['advertiser']
        adv_id     = feed_info['advertiser_id']
        feed_url   = feed_info['url']

        logger.info("[%d/%d] %s", idx, len(unique_feeds), advertiser)

        data = _download_awin_feed(feed_url)
        if not data:
            logger.warning("  %s: download failed — skipping", advertiser)
            continue

        try:
            text_data = data.decode("utf-8", errors="replace")
            reader    = _csv.DictReader(_io.StringIO(text_data, newline=""))
        except Exception as e:
            logger.warning("  %s: CSV parse error — %s", advertiser, e)
            continue

        feed_found = feed_stored = feed_skipped = 0
        conn = None

        if not dry_run:
            try:
                conn = sqlite3.connect(_DB_PATH, timeout=15)
            except Exception as e:
                logger.error("  %s: DB connect failed — %s", advertiser, e)
                continue

        try:
            for i, row in enumerate(reader):
                if i >= AWIN_MAX_ROWS_PER_FEED:
                    break

                product = _awin_row_to_catalog_product(row, advertiser, adv_id)
                if not product:
                    feed_skipped += 1
                    continue

                # Price cap
                if product['price'] > AWIN_SYNC_MAX_PRICE_USD and product['price'] > 0:
                    feed_skipped += 1
                    continue

                feed_found += 1

                # Tag with matching catalog interest terms
                tags = _tag_awin_product_with_interests(
                    product['title'], product['description'], _ALL_CATALOG_TERMS
                )
                if not tags:
                    feed_skipped += 1
                    continue

                # Score
                gift_score = score_product_gift_suitability({
                    'title':       product['title'],
                    'description': product['description'],
                    'image_url':   product['image_url'],
                    'brand':       product['brand'],
                    'price':       product['price'],
                })

                if gift_score < MIN_SCORE_TO_STORE:
                    feed_skipped += 1
                    continue

                if not dry_run and conn:
                    try:
                        with conn:
                            _upsert_awin_catalog_product(product, gift_score, tags, conn)
                        feed_stored += 1
                    except Exception as e:
                        logger.debug("  upsert failed (%s): %s",
                                     product.get('title', '?')[:40], e)
                        feed_skipped += 1
                else:
                    feed_stored += 1  # dry_run count

        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

        logger.info("  %s: %d found → %d stored, %d skipped",
                    advertiser, feed_found, feed_stored, feed_skipped)

        total_found   += feed_found
        total_stored  += feed_stored
        total_skipped += feed_skipped

        time.sleep(0.5)  # polite delay between feeds

    logger.info("=" * 60)
    logger.info("AWIN SYNC COMPLETE")
    logger.info("  Feeds synced:    %d", len(unique_feeds))
    logger.info("  Products found:  %d", total_found)
    logger.info("  Products stored: %d", total_stored)
    logger.info("  Skipped:         %d", total_skipped)
    logger.info("=" * 60)

    return {
        'feeds_synced':  len(unique_feeds),
        'total_found':   total_found,
        'total_stored':  total_stored,
        'total_skipped': total_skipped,
    }


def sync_term(
    term: str,
    category: str = '',
    max_pages: int = MAX_PAGES_REFRESH,
    dry_run: bool = False,
    advertiser_id: Optional[str] = None,
) -> Dict:
    """
    Fetch, score, and store CJ products for one search term.

    Returns a stats dict:
      { 'term', 'found', 'stored', 'skipped', 'avg_score', 'pages_fetched' }
    """
    stats = {
        'term': term, 'found': 0, 'stored': 0,
        'skipped': 0, 'avg_score': 0.0, 'pages_fetched': 0,
    }

    if not CJ_API_KEY or not CJ_COMPANY_ID or not CJ_PUBLISHER_ID:
        logger.warning(f"Skipping '{term}' — CJ credentials not set")
        return stats

    all_products = []
    for page in range(max_pages):
        time.sleep(REQUEST_DELAY_SECONDS)
        products, total = _fetch_cj_page(term, page=page, advertiser_id=advertiser_id)
        stats['pages_fetched'] += 1

        if not products:
            break

        all_products.extend(products)
        logger.debug(f"  '{term}' page {page}: {len(products)} products "
                     f"(total available: {total})")

        # Stop early if we've fetched everything available
        if len(all_products) >= total or len(products) < PRODUCTS_PER_PAGE:
            break

    stats['found'] = len(all_products)

    if not all_products or dry_run:
        if dry_run and all_products:
            scores = [score_product_gift_suitability(p) for p in all_products]
            stats['avg_score'] = round(sum(scores) / len(scores), 3)
        return stats

    # Score and store
    scores_stored = []
    try:
        conn = sqlite3.connect(_DB_PATH)
        conn.row_factory = sqlite3.Row
        with conn:
            for product in all_products:
                gift_score = score_product_gift_suitability(product)

                if gift_score < MIN_SCORE_TO_STORE:
                    stats['skipped'] += 1
                    continue

                # Multi-label tagging: tag CJ products with ALL matching
                # catalog terms, not just the search term that found them.
                # This matches Awin's behavior and improves DB cache hit rate.
                cj_tags = _tag_awin_product_with_interests(
                    product.get('title', ''),
                    product.get('description', ''),
                    _ALL_CATALOG_TERMS
                )
                if term.lower() not in cj_tags:
                    cj_tags.append(term.lower())

                _upsert_catalog_product(
                    product,
                    gift_score=gift_score,
                    interest_tags=cj_tags,
                    conn=conn,
                )
                scores_stored.append(gift_score)
                stats['stored'] += 1

            # Record sync log
            avg = round(sum(scores_stored) / len(scores_stored), 3) if scores_stored else 0.0
            stats['avg_score'] = avg
            conn.execute("""
                INSERT INTO catalog_sync_log
                    (term, category, last_synced_at, products_found, products_stored, avg_gift_score)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(term) DO UPDATE SET
                    last_synced_at   = excluded.last_synced_at,
                    products_found   = excluded.products_found,
                    products_stored  = excluded.products_stored,
                    avg_gift_score   = excluded.avg_gift_score,
                    category         = excluded.category
            """, (
                term.lower(), category, datetime.now().isoformat(),
                stats['found'], stats['stored'], avg,
            ))

    except Exception as e:
        logger.error(f"DB write failed for '{term}': {e}")
    finally:
        conn.close()

    logger.info(
        f"  '{term}': {stats['found']} found → "
        f"{stats['stored']} stored (avg score {stats['avg_score']:.2f}), "
        f"{stats['skipped']} skipped"
    )
    return stats


# ---------------------------------------------------------------------------
# SYNC RUNNER
# Orchestrates a full, refresh, or targeted sync run.
# ---------------------------------------------------------------------------

def run_catalog_sync(
    mode: str = 'refresh',
    terms: Optional[List[str]] = None,
    advertiser_id: Optional[str] = None,
    dry_run: bool = False,
) -> Dict:
    """
    Run a catalog sync.

    Args:
        mode:          'full' | 'refresh' | 'targeted'
        terms:         Required for 'targeted' mode. Ignored otherwise.
        advertiser_id: Optional CJ advertiser ID to restrict to one program
                       (e.g. TIKTOK_SHOP_ADV_ID for TikTok Shop only).
        dry_run:       If True, fetch and score but do not write to DB.

    Returns:
        Summary dict with total stats and per-term breakdown.
    """
    ensure_catalog_schema()

    if mode == 'full':
        sync_list = [(t, p, c) for (t, p, c) in ALL_SYNC_TERMS]
        max_pages = MAX_PAGES_FULL
        label = f"FULL ({len(sync_list)} terms)"
    elif mode == 'targeted':
        if not terms:
            raise ValueError("'targeted' mode requires a terms list")
        sync_list = [(t, 1, 'targeted') for t in terms]
        max_pages = MAX_PAGES_REFRESH
        label = f"TARGETED ({len(sync_list)} terms)"
    else:  # refresh (default)
        sync_list = [(t, 1, 'refresh') for t in REFRESH_TERMS]
        max_pages = MAX_PAGES_REFRESH
        label = f"REFRESH ({len(sync_list)} terms)"

    adv_label = f" [advertiser {advertiser_id}]" if advertiser_id else ""
    dry_label  = " [DRY RUN]" if dry_run else ""

    logger.info("=" * 60)
    logger.info(f"CATALOG SYNC — {label}{adv_label}{dry_label}")
    logger.info(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)

    total_found = total_stored = total_skipped = 0
    term_stats = []

    for i, (term, _priority, category) in enumerate(sync_list, 1):
        logger.info(f"[{i}/{len(sync_list)}] {term}")
        s = sync_term(
            term,
            category=category,
            max_pages=max_pages,
            dry_run=dry_run,
            advertiser_id=advertiser_id,
        )
        term_stats.append(s)
        total_found   += s['found']
        total_stored  += s['stored']
        total_skipped += s['skipped']

    # Run Awin feed sync
    awin_stats = sync_awin_feeds(dry_run=dry_run)

    # Mark products not refreshed in STALE_PRODUCT_DAYS as removed
    stale_count = 0
    if not dry_run:
        conn = None
        try:
            conn = sqlite3.connect(_DB_PATH, timeout=10)
            cutoff = (datetime.now() - timedelta(days=STALE_PRODUCT_DAYS)).isoformat()
            with conn:
                cur = conn.cursor()
                cur.execute("""
                    UPDATE products
                    SET removed_at = ?
                    WHERE last_checked < ?
                      AND removed_at IS NULL
                      AND (retailer LIKE '%CJ%'
                           OR awin_advertiser_id IS NOT NULL)
                """, (datetime.now().isoformat(), cutoff))
                stale_count = cur.rowcount
        except Exception as e:
            logger.error(f"Stale purge failed: {e}")
        finally:
            if conn:
                conn.close()

    summary = {
        'mode':               mode,
        'dry_run':            dry_run,
        'terms_synced':       len(sync_list),
        'total_found':        total_found,
        'total_stored':       total_stored,
        'total_skipped':      total_skipped,
        'stale_purged':       stale_count,
        'awin_feeds_synced':  awin_stats.get('feeds_synced', 0),
        'awin_stored':        awin_stats.get('total_stored', 0),
        'started_at':         datetime.now().isoformat(),
        'term_stats':         term_stats,
    }

    logger.info("=" * 60)
    logger.info("SYNC COMPLETE")
    logger.info(f"  CJ terms synced:   {len(sync_list)}")
    logger.info(f"  CJ products found: {total_found}")
    logger.info(f"  CJ stored:         {total_stored}")
    logger.info(f"  CJ skipped:        {total_skipped}")
    logger.info(f"  Awin feeds synced: {awin_stats.get('feeds_synced', 0)}")
    logger.info(f"  Awin stored:       {awin_stats.get('total_stored', 0)}")
    logger.info(f"  Stale purged:      {stale_count}")
    logger.info("=" * 60)

    return summary


# ---------------------------------------------------------------------------
# ADMIN STATS
# Used by the admin dashboard to show catalog health.
# ---------------------------------------------------------------------------

def get_catalog_stats() -> Dict:
    """Return catalog sync stats for the admin dashboard."""
    try:
        conn = sqlite3.connect(_DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # Total catalog products in DB (all CJ advertisers, identified by cj_advertiser_id)
        cur.execute("""
            SELECT COUNT(*) FROM products
            WHERE cj_advertiser_id != '' AND removed_at IS NULL AND in_stock = 1
        """)
        total_cj = cur.fetchone()[0]

        # Total Awin catalog products
        cur.execute("""
            SELECT COUNT(*) FROM products
            WHERE awin_advertiser_id IS NOT NULL AND awin_advertiser_id != ''
              AND removed_at IS NULL AND in_stock = 1
        """)
        total_awin = cur.fetchone()[0]

        # TikTok Shop specifically
        cur.execute("""
            SELECT COUNT(*) FROM products
            WHERE cj_advertiser_id = ? AND removed_at IS NULL AND in_stock = 1
        """, (TIKTOK_SHOP_ADV_ID,))
        total_tikshop = cur.fetchone()[0]

        # Top 5 terms by product count
        cur.execute("""
            SELECT term, products_stored, avg_gift_score, last_synced_at
            FROM catalog_sync_log
            ORDER BY products_stored DESC
            LIMIT 5
        """)
        top_terms = [dict(r) for r in cur.fetchall()]

        # How many terms are fresh (synced within CACHE_FRESH_HOURS)
        cutoff = (datetime.now() - timedelta(hours=CACHE_FRESH_HOURS)).isoformat()
        cur.execute(
            "SELECT COUNT(*) FROM catalog_sync_log WHERE last_synced_at > ?",
            (cutoff,)
        )
        fresh_terms = cur.fetchone()[0]

        # Last sync time
        cur.execute(
            "SELECT MAX(last_synced_at) FROM catalog_sync_log"
        )
        row = cur.fetchone()
        last_sync = row[0] if row and row[0] else 'Never'

        # Avg gift score across all catalog products
        cur.execute("""
            SELECT AVG(gift_score) FROM products
            WHERE cj_advertiser_id != '' AND removed_at IS NULL
              AND gift_score IS NOT NULL
        """)
        avg_score_row = cur.fetchone()
        avg_gift_score = round(avg_score_row[0] or 0.0, 3)

        conn.close()

        return {
            'total_cj_products':   total_cj,
            'total_awin_products': total_awin,
            'total_tikshop':       total_tikshop,
            'fresh_terms':        fresh_terms,
            'top_terms':          top_terms,
            'last_sync':          last_sync,
            'avg_gift_score':     avg_gift_score,
            'cache_ttl_hours':    CACHE_FRESH_HOURS,
        }

    except Exception as e:
        logger.error(f"Failed to get catalog stats: {e}")
        return {'error': str(e)}


# ---------------------------------------------------------------------------
# INITIALIZATION — run schema migration on import
# ---------------------------------------------------------------------------

try:
    ensure_catalog_schema()
except Exception as _e:
    logger.warning(f"catalog_sync: schema migration skipped ({_e})")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [CATALOG_SYNC] %(levelname)s: %(message)s',
        datefmt='%H:%M:%S',
    )

    parser = argparse.ArgumentParser(
        description='CJ Affiliate catalog sync — download, score, and cache products.'
    )
    parser.add_argument(
        '--mode',
        choices=['full', 'refresh', 'targeted'],
        default='refresh',
        help=(
            'full: all 130+ terms (weekly); '
            'refresh: top 40 terms (nightly, default); '
            'targeted: specific terms via --terms'
        ),
    )
    parser.add_argument(
        '--terms',
        type=str,
        default='',
        help='Comma-separated terms for targeted mode (e.g. "coffee,yoga,guitar")',
    )
    parser.add_argument(
        '--tikshop',
        action='store_true',
        help='Restrict sync to TikTok Shop products only (ADV 7563286)',
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Fetch and score but do not write to database',
    )
    parser.add_argument(
        '--stats',
        action='store_true',
        help='Print catalog stats and exit',
    )

    args = parser.parse_args()

    if args.stats:
        stats = get_catalog_stats()
        print("\nCatalog Stats")
        print("=" * 40)
        print(f"Total CJ products:    {stats.get('total_cj_products', 0):,}")
        print(f"TikTok Shop products: {stats.get('total_tikshop', 0):,}")
        print(f"Fresh terms cached:   {stats.get('fresh_terms', 0)}")
        print(f"Avg gift score:       {stats.get('avg_gift_score', 0):.2f}")
        print(f"Last sync:            {stats.get('last_sync', 'Never')}")
        print(f"\nTop terms by product count:")
        for t in stats.get('top_terms', []):
            print(f"  {t['term']:<30} {t['products_stored']:>4} products  "
                  f"(avg score {t['avg_gift_score']:.2f})")
        sys.exit(0)

    if not CJ_API_KEY:
        print("ERROR: CJ_API_KEY not set. Export it before running.")
        sys.exit(1)

    adv_id = TIKTOK_SHOP_ADV_ID if args.tikshop else None
    term_list = [t.strip() for t in args.terms.split(',') if t.strip()] or None

    run_catalog_sync(
        mode=args.mode,
        terms=term_list,
        advertiser_id=adv_id,
        dry_run=args.dry_run,
    )
