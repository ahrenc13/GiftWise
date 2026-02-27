"""
PRODUCT INTEREST TAGGER

Multi-label interest tagging for products stored in the GiftWise catalog.
Given a product title and description, returns all interest tags from the
GiftWise ontology that the product plausibly matches.

This is deterministic, zero-cost code — no LLM calls.

HOW IT WORKS
------------
Two detection passes are combined:

  Pass 1 — Domain detection (broad)
    Uses KEYWORD_HEURISTICS from interest_ontology.py to identify what
    domain a product belongs to (food, outdoor, wellness, etc.), then tags
    it with ALL interests that share that domain.
    Example: "hiking backpack" → "hik" → domain "outdoor"
             → hiking, camping, backpacking, fishing, skiing, surfing all tagged

  Pass 2 — Direct interest name matching (targeted)
    Checks each known interest name's first meaningful word against the
    product text.
    Example: "pour over coffee dripper" → "coffee" in text
             → "coffee" interest tagged ✓

  Supplementary keywords (gap-filler)
    A small dictionary in this file covers common product vocabulary not
    captured by the ontology heuristics (camera, candle, speaker, etc.).
    Safe to extend — this file is NOT Opus-only.

FALSE POSITIVES ARE ACCEPTABLE
-------------------------------
The tagger is intentionally high-recall. A coffee product tagged with
"wine" (same food-drink domain) is a minor false positive — the curator
makes the final taste judgment. Missing tags (false negatives) are worse
than extra tags, because missed tags mean the product is never considered
for relevant profiles.

OPUS-ONLY SAFETY
----------------
This module only READS from interest_ontology.py — it never writes to it
and never calls enrich_profile_with_ontology(). The INTEREST_ATTRIBUTES
and KEYWORD_HEURISTICS dicts are used as static lookup tables only.
Adding new entries to _SUPPLEMENTARY_KEYWORDS in this file is safe for
any session.

USAGE
-----
  from product_tagger import tag_product_with_interests, backfill_interest_tags

  # Tag a single product:
  tags = tag_product_with_interests("Yoga Mat", "Premium non-slip yoga mat")
  # → ["yoga", "pilates", "meditation", "self-care", ...]

  # Backfill all existing DB products with expanded tags:
  stats = backfill_interest_tags('/path/to/products.db', dry_run=True)

Author: Chad + Claude
Date: February 2026
"""

import json
import logging
import re
import sqlite3
from typing import Dict, List, Set

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# ONTOLOGY IMPORT (read-only — never modify these dicts)
# ---------------------------------------------------------------------------

try:
    from interest_ontology import INTEREST_ATTRIBUTES, KEYWORD_HEURISTICS
    _ONTOLOGY_AVAILABLE = True
except ImportError:
    INTEREST_ATTRIBUTES: Dict = {}
    KEYWORD_HEURISTICS: Dict = {}
    _ONTOLOGY_AVAILABLE = False
    logger.warning("product_tagger: interest_ontology.py not found — tagging disabled")


# ---------------------------------------------------------------------------
# SUPPLEMENTARY KEYWORD → INTEREST MAPPING
# Covers product vocabulary not caught by ontology heuristics.
# Safe to extend in Sonnet sessions — this is NOT Opus-only.
# ---------------------------------------------------------------------------

_SUPPLEMENTARY: Dict[str, List[str]] = {
    # Photography / cameras
    'camera':       ['photography'],
    'lens':         ['photography'],
    'tripod':       ['photography'],
    'mirrorless':   ['photography'],
    'dslr':         ['photography'],
    'shutter':      ['photography'],
    'lightroom':    ['photography'],
    'flash':        ['photography'],

    # Music / audio
    'headphone':    ['vinyl collecting'],
    'speaker':      ['vinyl collecting'],
    'turntable':    ['vinyl collecting', 'vinyl record collecting'],
    'record player':['vinyl collecting', 'vinyl record collecting'],
    'amplifier':    ['vinyl collecting'],
    'microphone':   ['vinyl collecting'],
    'earphone':     ['vinyl collecting'],

    # Home / candles / plants
    'candle':       ['candles'],
    'wax melt':     ['candles'],
    'succulent':    ['plants', 'gardening'],
    'terrarium':    ['plants'],
    'planter':      ['plants', 'gardening'],
    'houseplant':   ['plants'],
    'flower pot':   ['plants', 'gardening'],

    # Gaming
    'controller':   ['video games'],
    'gamepad':      ['video games'],
    'console':      ['video games'],
    'steam':        ['video games'],
    'playstation':  ['playstation'],
    'nintendo':     ['nintendo'],
    'switch':       ['nintendo'],

    # Board games / tabletop
    'board game':   ['board games'],
    'card game':    ['board games'],
    'tabletop':     ['board games'],
    'dice':         ['board games', 'dungeons and dragons'],
    'dungeon':      ['dungeons and dragons'],
    'dragon':       ['dungeons and dragons'],
    'rpg':          ['dungeons and dragons'],

    # Fandoms
    'anime':        ['anime'],
    'manga':        ['anime'],
    'marvel':       ['film'],
    'disney':       ['disney'],
    'star wars':    ['film'],
    'harry potter': ['fantasy'],
    'kpop':         ['hip hop'],   # close enough domain-wise

    # Outdoor / sports specific
    'climbing':     ['rock climbing'],
    'bouldering':   ['rock climbing'],
    'chalk bag':    ['rock climbing'],
    'surfboard':    ['surfing'],
    'wetsuit':      ['surfing'],
    'kayak':        ['camping'],   # same outdoor domain
    'paddleboard':  ['camping'],
    'ski':          ['skiing'],
    'snowboard':    ['skiing'],
    'fishing rod':  ['fishing'],
    'fly fishing':  ['fishing'],
    'tackle':       ['fishing'],

    # Fashion / beauty specific
    'perfume':      ['fragrance'],
    'cologne':      ['fragrance'],
    'eau de':       ['fragrance'],
    'serum':        ['skincare'],
    'moisturizer':  ['skincare'],
    'sunscreen':    ['skincare'],
    'foundation':   ['makeup'],
    'eyeshadow':    ['makeup'],
    'lipstick':     ['makeup'],
    'mascara':      ['makeup'],

    # Tech
    'smart home':   ['smart home'],
    'smart speaker':['smart home', 'technology'],
    'smart light':  ['smart home'],
    'drone':        ['drones'],
    'fpv':          ['drones'],
    'telescope':    ['astronomy'],
    'stargazing':   ['astronomy'],
    'binocular':    ['astronomy'],

    # Wellness / spiritual
    'crystal':      ['astrology', 'yoga'],
    'tarot':        ['tarot'],
    'chakra':       ['yoga', 'meditation'],
    'meditation':   ['meditation'],
    'mindfulness':  ['meditation'],
    'affirmation':  ['meditation'],
    'reiki':        ['yoga', 'meditation'],
    'sage':         ['astrology', 'tarot'],

    # Pets
    'dog treat':    ['dogs'],
    'dog toy':      ['dogs'],
    'dog collar':   ['dogs'],
    'dog leash':    ['dogs'],
    'cat toy':      ['cats'],
    'cat tree':     ['cats'],
    'cat bed':      ['cats'],
    'litter':       ['cats'],
    'pet portrait': ['dogs', 'cats'],

    # Soccer specific (supplement the "sport" heuristic)
    'soccer':       ['soccer'],
    'football cleat':['soccer'],
    'futsal':       ['soccer'],
}


# ---------------------------------------------------------------------------
# PRE-COMPUTED LOOKUP TABLES (built once on import)
# ---------------------------------------------------------------------------

def _build_domain_to_interests() -> Dict[str, List[str]]:
    """Build {domain_value -> [interest_name, ...]} from INTEREST_ATTRIBUTES."""
    mapping: Dict[str, List[str]] = {}
    for interest_name, attrs in INTEREST_ATTRIBUTES.items():
        domain = attrs.get('domain')
        if domain:
            mapping.setdefault(domain, []).append(interest_name)
    return mapping


def _build_direct_keywords() -> Dict[str, str]:
    """
    Build {first_meaningful_word -> interest_name} for direct name matching.
    Single-word interests (yoga, coffee, hiking) are matched exactly.
    Multi-word interests (vinyl collecting) matched on first meaningful word.
    """
    mapping: Dict[str, str] = {}
    for interest_name in INTEREST_ATTRIBUTES:
        words = [w for w in re.split(r'[\s\-]+', interest_name.lower())
                 if len(w) > 3]  # skip short/stop words
        if words:
            # Only add if no collision — first-registered wins
            if words[0] not in mapping:
                mapping[words[0]] = interest_name
    return mapping


_DOMAIN_TO_INTERESTS: Dict[str, List[str]] = _build_domain_to_interests()
_DIRECT_KEYWORDS: Dict[str, str] = _build_direct_keywords()


# ---------------------------------------------------------------------------
# CORE TAGGING FUNCTION
# ---------------------------------------------------------------------------

def _word_in_text(word: str, text: str) -> bool:
    """
    True if `word` appears as a standalone word (or word prefix) in `text`.
    Uses word-boundary regex to prevent "run" matching "brunette".
    """
    return bool(re.search(r'\b' + re.escape(word), text))


def tag_product_with_interests(title: str, description: str) -> List[str]:
    """
    Return all interest tags that plausibly match this product.

    Uses three detection passes (domain, direct name, supplementary keywords)
    then deduplicates. See module docstring for full explanation.

    Args:
        title:       Product title (e.g., "Osprey Atmos 65 Hiking Backpack")
        description: Product description or snippet

    Returns:
        Deduplicated list of matching interest names, e.g.:
        ["hiking", "camping", "backpacking", "rock climbing"]
    """
    if not _ONTOLOGY_AVAILABLE:
        return []

    text = (title + ' ' + description).lower()
    collected: Set[str] = set()

    # ------------------------------------------------------------------
    # Pass 1: Domain detection via KEYWORD_HEURISTICS
    # Detect what domain this product belongs to, then tag all interests
    # in that domain.
    # ------------------------------------------------------------------

    # Some KEYWORD_HEURISTICS fragment keys are too ambiguous for product
    # text matching — they were designed to match interest *names* (controlled
    # vocabulary) not arbitrary product descriptions. Excluding them prevents
    # noise like "fits mirrorless" → fitness domain, or "technical climbing" →
    # tech domain. Cannot modify KEYWORD_HEURISTICS (Opus-only).
    _HEURISTIC_SKIP = {'fit', 'tech'}

    detected_domains: Set[str] = set()
    for kw, attrs in KEYWORD_HEURISTICS.items():
        if kw in _HEURISTIC_SKIP:
            continue
        domain = attrs.get('domain')
        if domain and _word_in_text(kw, text):
            detected_domains.add(domain)

    for domain in detected_domains:
        for interest_name in _DOMAIN_TO_INTERESTS.get(domain, []):
            collected.add(interest_name)

    # ------------------------------------------------------------------
    # Pass 2: Direct interest name matching
    # Check the first meaningful word of each known interest name.
    # Catches cases where the interest word itself appears in the title.
    # ------------------------------------------------------------------
    for keyword, interest_name in _DIRECT_KEYWORDS.items():
        if _word_in_text(keyword, text):
            collected.add(interest_name)

    # ------------------------------------------------------------------
    # Pass 3: Supplementary keywords (product-vocabulary gap-filler)
    # ------------------------------------------------------------------
    for keyword, interest_names in _SUPPLEMENTARY.items():
        if keyword in text:  # substring match (handles multi-word phrases)
            for name in interest_names:
                collected.add(name)

    # Return as list, sorted for stable output
    return sorted(collected)


# ---------------------------------------------------------------------------
# BACKFILL UTILITY
# Re-tags existing DB products that have single-label or empty interest_tags.
# Safe to run at any time — only ADDS tags, never removes existing ones.
# ---------------------------------------------------------------------------

def backfill_interest_tags(
    db_path: str,
    dry_run: bool = False,
    batch_size: int = 500,
    min_new_tags: int = 1,
) -> Dict:
    """
    Expand interest_tags on existing products in the DB.

    Reads all active products, runs the tagger on each title + description,
    and merges any new tags into the existing tag list. Never removes tags.

    This is the remediation for the single-label bug in catalog_sync.py's
    upsert, which stored only the search term that found each product.
    Running this backfill once (and periodically) upgrades all CJ products
    to multi-label tags without touching catalog_sync.py.

    Args:
        db_path:      Path to products.db (e.g. /home/user/GiftWise/data/products.db)
        dry_run:      If True, report what would change but don't write anything
        batch_size:   Rows to process per transaction (reduces lock time)
        min_new_tags: Only update rows where tagger adds at least this many new tags

    Returns:
        Stats dict: {'scanned', 'updated', 'skipped', 'dry_run', 'error'?}
    """
    stats: Dict = {
        'scanned': 0,
        'updated': 0,
        'skipped': 0,
        'dry_run': dry_run,
    }

    if not _ONTOLOGY_AVAILABLE:
        logger.warning("backfill_interest_tags: ontology unavailable, skipping")
        return stats

    try:
        conn = sqlite3.connect(db_path, timeout=15)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        offset = 0
        while True:
            cur.execute("""
                SELECT rowid, title, description, interest_tags
                FROM   products
                WHERE  removed_at IS NULL
                  AND  in_stock = 1
                ORDER  BY rowid
                LIMIT  ? OFFSET ?
            """, (batch_size, offset))

            rows = cur.fetchall()
            if not rows:
                break

            batch_updates = []
            for row in rows:
                stats['scanned'] += 1

                existing_tags: List[str] = []
                if row['interest_tags']:
                    try:
                        existing_tags = json.loads(row['interest_tags'])
                    except (json.JSONDecodeError, TypeError):
                        pass

                new_tags = tag_product_with_interests(
                    row['title'] or '',
                    row['description'] or '',
                )

                # Merge: new tags first (higher recall priority), then existing
                merged = list(dict.fromkeys(new_tags + existing_tags))
                added = len(set(merged) - set(existing_tags))

                if added < min_new_tags:
                    stats['skipped'] += 1
                    continue

                batch_updates.append((json.dumps(merged), row['rowid']))
                stats['updated'] += 1

            if batch_updates and not dry_run:
                cur.executemany("""
                    UPDATE products
                    SET    interest_tags = ?,
                           last_updated  = datetime('now')
                    WHERE  rowid = ?
                """, batch_updates)
                conn.commit()

            offset += batch_size

        conn.close()

    except Exception as e:
        logger.error("backfill_interest_tags failed: %s", e)
        stats['error'] = str(e)

    logger.info(
        "Tag backfill complete: scanned=%d updated=%d skipped=%d dry_run=%s",
        stats['scanned'], stats['updated'], stats['skipped'], dry_run,
    )
    return stats


# ---------------------------------------------------------------------------
# CLI — run as standalone script
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    import sys
    import os

    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

    # Quick tagger test
    test_products = [
        ("Osprey Atmos 65 Hiking Backpack",
         "Ultralight hiking backpack with AntiGravity suspension. 65L. Hydration compatible."),
        ("Pour Over Coffee Dripper",
         "Ceramic pour over coffee maker. Brings out bright, clean flavors from single-origin beans."),
        ("Canon R6 Camera Bag",
         "Padded camera bag fits mirrorless and DSLR kit. Waterproof exterior, laptop sleeve."),
        ("Handmade Yoga Mat",
         "Eco-friendly natural rubber yoga mat with alignment lines, non-slip surface."),
        ("Extension Cord 12ft Power Strip",
         "Heavy-duty surge protector, 6 outlets, 2 USB ports. UL certified."),
        ("Scented Soy Candle — Sandalwood",
         "Hand-poured soy candle with sandalwood and vanilla notes. 60-hour burn time."),
        ("Sony WH-1000XM5 Headphones",
         "Industry-leading noise canceling wireless headphones. 30-hour battery."),
        ("Osprey Tempest Climbing Pack",
         "Technical climbing pack for single-pitch and gym climbing. Fits chalk bag."),
        ("Rose Quartz Facial Roller",
         "Crystal facial roller for lymphatic drainage and de-puffing. Pairs with gua sha."),
    ]

    print("Product Tagger — Test Run")
    print("=" * 60)
    for title, desc in test_products:
        tags = tag_product_with_interests(title, desc)
        print(f"\n{title}")
        print(f"  Tags ({len(tags)}): {', '.join(tags) if tags else '(none)'}")

    # Backfill test (dry-run only if DB exists)
    db_path = os.environ.get('DATABASE_PATH', '/home/user/GiftWise/data/products.db')
    if '--backfill' in sys.argv and os.path.exists(db_path):
        print(f"\n{'=' * 60}")
        print("Backfill dry-run...")
        dry = '--write' not in sys.argv
        result = backfill_interest_tags(db_path, dry_run=dry)
        print(f"  Scanned:  {result['scanned']}")
        print(f"  Updated:  {result['updated']}")
        print(f"  Skipped:  {result['skipped']}")
        if result.get('error'):
            print(f"  ERROR:    {result['error']}")
