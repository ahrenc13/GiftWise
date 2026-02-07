"""
POST-CURATION CLEANUP — Programmatic enforcement of gift quality rules.

Runs AFTER the curator (LLM) returns its selections but BEFORE display.
Fixes problems that prompt instructions alone cannot guarantee:

1. Brand deduplication — max 1 product per brand
2. Category deduplication — max 1 product per item type (candle, mug, etc.)
3. Interest spread — max 2 products per interest
4. URL inventory validation — every product_url must exist in the original pool
5. Title cleanup — strip SEO spam, model numbers, size specs

Author: Chad + Claude
Date: February 2026
"""

import re
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Brand extraction
# ---------------------------------------------------------------------------

# Well-known brands we can detect in titles (lowercase)
KNOWN_BRANDS = {
    'yankee candle', 'bath & body works', 'bath and body works',
    'nike', 'adidas', 'under armour', 'patagonia', 'north face', 'the north face',
    'stanley', 'yeti', 'hydro flask', 'contigo',
    'apple', 'samsung', 'sony', 'bose', 'jbl', 'beats',
    'lego', 'funko', 'disney', 'marvel', 'star wars',
    'kitchenaid', 'cuisinart', 'ninja', 'instant pot', 'breville', 'keurig',
    'dewalt', 'makita', 'milwaukee', 'bosch', 'black+decker', 'black & decker',
    'cricut', 'silhouette',
    'lodge', 'le creuset', 'staub',
    'moleskine', 'leuchtturm', 'field notes',
    'taylor swift', 'olivia rodrigo',  # artist brands in merch
    'nintendo', 'playstation', 'xbox',
    'carhartt', 'dickies', 'wrangler', "levi's", 'levis',
    'ray-ban', 'oakley', 'warby parker',
    'etsy',  # not a brand, but shows up in titles
}


def extract_brand(title):
    """
    Extract the likely brand/manufacturer from a product title.
    Returns lowercase brand string or '' if unknown.
    """
    if not title:
        return ''
    title_lower = title.lower().strip()

    # Check known brands first (longest match wins)
    matches = [b for b in KNOWN_BRANDS if b in title_lower]
    if matches:
        return max(matches, key=len)

    # Heuristic: first capitalized word(s) before a space + lowercase word
    # e.g. "DeWalt 20V MAX..." → "dewalt", "Breville BES870XL..." → "breville"
    # Take the first word as brand if it looks like a brand (capitalized, not generic)
    generic_starts = {
        'the', 'a', 'an', 'new', 'vintage', 'handmade', 'custom', 'personalized',
        'set', 'pack', 'lot', 'pair', 'premium', 'deluxe', 'official', 'licensed',
        'funny', 'cute', 'unique', 'best', 'great', 'awesome', 'cool',
    }
    words = title.split()
    if words and words[0].lower() not in generic_starts and len(words[0]) > 1:
        candidate = words[0].strip('®™©,.-').lower()
        if candidate and len(candidate) > 1:
            return candidate

    return ''


# ---------------------------------------------------------------------------
# Category detection
# ---------------------------------------------------------------------------

CATEGORY_PATTERNS = {
    'candle': r'\bcandle[s]?\b',
    'mug': r'\b(?:mug|cup|tumbler)[s]?\b',
    't-shirt': r'\b(?:t-?shirt|tee|tshirt)[s]?\b',
    'poster': r'\b(?:poster|wall art|print|art print)[s]?\b',
    'book': r'\b(?:book|novel|guide|cookbook)[s]?\b',
    'jewelry': r'\b(?:necklace|bracelet|earring|ring|pendant|charm)[s]?\b',
    'hat': r'\b(?:hat|cap|beanie)[s]?\b',
    'blanket': r'\b(?:blanket|throw|quilt)[s]?\b',
    'puzzle': r'\b(?:puzzle|jigsaw)[s]?\b',
    'game': r'\b(?:board game|card game|game set)\b',
    'socks': r'\b(?:socks|sock set)\b',
    'bag': r'\b(?:bag|tote|backpack|purse|clutch)[s]?\b',
    'keychain': r'\b(?:keychain|key chain|key ring)[s]?\b',
    'sticker': r'\b(?:sticker|decal)[s]?\b',
    'ornament': r'\b(?:ornament|decoration)[s]?\b',
    'pillow': r'\b(?:pillow|cushion)[s]?\b',
    'coaster': r'\b(?:coaster)[s]?\b',
    'magnet': r'\b(?:magnet|fridge magnet)[s]?\b',
    'phone case': r'\b(?:phone case|iphone case|case for)\b',
    'wallet': r'\b(?:wallet|card holder)\b',
}


def detect_category(title, description=''):
    """Detect product category from title + description. Returns category string or ''."""
    if not title:
        return ''
    combined = f"{title} {description or ''}".lower()
    for category, pattern in CATEGORY_PATTERNS.items():
        if re.search(pattern, combined):
            return category
    return ''


# ---------------------------------------------------------------------------
# Title cleanup
# ---------------------------------------------------------------------------

def clean_title(title):
    """
    Strip SEO spam, model numbers, size specs, and keyword stuffing from a product title.
    Returns a clean 3-8 word title.
    """
    if not title:
        return title

    original = title

    # Remove content in parentheses that looks like model numbers or specs
    title = re.sub(r'\([^)]*(?:pack|count|oz|ml|inch|cm|mm|set of|size|model|sku|asin)[^)]*\)', '', title, flags=re.IGNORECASE)

    # Remove common SEO suffixes
    for suffix_pattern in [
        r'\s*[-–—|,]\s*(?:great|perfect|best|ideal)\s+(?:gift|present|for)\b.*$',
        r'\s*[-–—|]\s*(?:free shipping|fast shipping|prime).*$',
        r'\s*\b\d+(?:\.\d+)?\s*(?:x\s*\d+|\s*inch(?:es)?|\s*cm|\s*mm)\b.*$',  # dimensions
    ]:
        title = re.sub(suffix_pattern, '', title, flags=re.IGNORECASE)

    # Remove model numbers like (DCD771C2), BES870XL
    title = re.sub(r'\b[A-Z]{2,}[\d]{2,}[A-Z]*\d*\b', '', title)
    # Remove standalone numbers that look like SKUs
    title = re.sub(r'\b\d{5,}\b', '', title)

    # Clean up multiple spaces and trailing punctuation
    title = re.sub(r'\s+', ' ', title).strip()
    title = title.rstrip(' ,-–—|/')

    # If the title is still very long, truncate intelligently
    words = title.split()
    if len(words) > 10:
        # Keep first 8 meaningful words
        title = ' '.join(words[:8])
        title = title.rstrip(' ,-–—|/')

    # If cleanup destroyed the title, use original
    if len(title) < 5 and len(original) > 5:
        return original

    return title


# ---------------------------------------------------------------------------
# Main cleanup function
# ---------------------------------------------------------------------------

def cleanup_curated_gifts(product_gifts, inventory, rec_count=10):
    """
    Programmatic post-curation cleanup. Enforces hard rules that prompts can't guarantee.

    Args:
        product_gifts: List of product gift dicts from curator (with name, product_url, etc.)
        inventory: Original product pool (list of dicts with 'link', 'title', etc.)
        rec_count: Target number of products to return

    Returns:
        Cleaned list of product gifts (same format as input, potentially with replacements)
    """
    if not product_gifts:
        return product_gifts

    # Build inventory lookup: URL → product dict
    inventory_by_url = {}
    for p in (inventory or []):
        link = (p.get('link') or '').strip()
        if link:
            inventory_by_url[link] = p
            inventory_by_url[link.rstrip('/')] = p

    # Track what's been used
    used_urls = set()
    used_brands = set()
    used_categories = set()
    interest_counts = {}
    source_counts = defaultdict(int)
    MAX_PER_SOURCE_PCT = 0.6  # No more than 60% from one source

    cleaned = []
    deferred = []  # Products that violated rules (might be used as replacements if needed)

    logger.info(f"Post-curation cleanup: {len(product_gifts)} gifts from curator, {len(inventory)} in pool")

    for gift in product_gifts:
        url = (gift.get('product_url') or '').strip()
        name = gift.get('name', '')
        interest = (gift.get('interest_match') or '').lower()

        # Rule 1: URL must be in inventory
        normalized_url = url.rstrip('/')
        if url not in inventory_by_url and normalized_url not in inventory_by_url:
            logger.info(f"CLEANUP: Dropped (not in inventory): {name[:50]}")
            continue

        # Rule 2: No duplicate URLs
        if url in used_urls or normalized_url in used_urls:
            logger.info(f"CLEANUP: Dropped (duplicate URL): {name[:50]}")
            continue

        # Clean the title
        gift['name'] = clean_title(name)

        # Extract brand and category
        inv_product = inventory_by_url.get(url) or inventory_by_url.get(normalized_url) or {}
        full_title = inv_product.get('title', name)
        brand = extract_brand(full_title)
        category = detect_category(full_title, inv_product.get('snippet', ''))

        # Rule 3: Brand diversity — max 1 per brand
        if brand and brand in used_brands:
            logger.info(f"CLEANUP: Deferred (duplicate brand '{brand}'): {name[:50]}")
            deferred.append(gift)
            continue

        # Rule 4: Category diversity — max 1 per category
        if category and category in used_categories:
            logger.info(f"CLEANUP: Deferred (duplicate category '{category}'): {name[:50]}")
            deferred.append(gift)
            continue

        # Rule 5: Interest spread — max 2 per interest
        if interest:
            count = interest_counts.get(interest, 0)
            if count >= 2:
                logger.info(f"CLEANUP: Deferred (3rd+ for interest '{interest}'): {name[:50]}")
                deferred.append(gift)
                continue
            interest_counts[interest] = count + 1

        # Rule 6: Source diversity — no more than 60% from one source
        inv_product = inventory_by_url.get(url) or inventory_by_url.get(normalized_url) or {}
        source = inv_product.get('source_domain', gift.get('where_to_buy', 'unknown')).lower()
        max_from_source = max(2, int(rec_count * MAX_PER_SOURCE_PCT))
        if source_counts[source] >= max_from_source:
            logger.info(f"CLEANUP: Deferred (source cap '{source}'): {name[:50]}")
            deferred.append(gift)
            continue

        # Passed all checks
        used_urls.add(url)
        used_urls.add(normalized_url)
        if brand:
            used_brands.add(brand)
        if category:
            used_categories.add(category)
        source_counts[source] += 1
        cleaned.append(gift)

    logger.info(f"After rules: {len(cleaned)} passed, {len(deferred)} deferred")

    # If we're short, try to fill from inventory (products not already selected)
    if len(cleaned) < rec_count:
        needed = rec_count - len(cleaned)
        logger.info(f"Need {needed} replacements from inventory pool")

        # Score remaining inventory by whether they bring diversity
        candidates = []
        for p in (inventory or []):
            link = (p.get('link') or '').strip()
            if not link or link in used_urls or link.rstrip('/') in used_urls:
                continue
            brand = extract_brand(p.get('title', ''))
            category = detect_category(p.get('title', ''), p.get('snippet', ''))
            # Prefer products that bring new brands, categories, and source diversity
            score = 0
            if brand and brand not in used_brands:
                score += 2
            if category and category not in used_categories:
                score += 2
            interest = (p.get('interest_match') or '').lower()
            if interest and interest_counts.get(interest, 0) < 2:
                score += 1
            p_source = p.get('source_domain', 'unknown').lower()
            if source_counts.get(p_source, 0) == 0:
                score += 3  # Strongly prefer unrepresented sources
            elif source_counts.get(p_source, 0) < max(2, int(rec_count * MAX_PER_SOURCE_PCT)):
                score += 1
            candidates.append((score, p))

        # Sort by diversity score (highest first)
        candidates.sort(key=lambda x: x[0], reverse=True)

        for score, p in candidates[:needed]:
            link = (p.get('link') or '').strip()
            brand = extract_brand(p.get('title', ''))
            category = detect_category(p.get('title', ''), p.get('snippet', ''))
            interest = (p.get('interest_match') or '').lower()

            # Build a gift dict from inventory product
            replacement = {
                'name': clean_title(p.get('title', 'Gift')),
                'description': p.get('snippet', ''),
                'why_perfect': f"Selected to bring variety — matches {p.get('interest_match', 'your')} interests",
                'price': p.get('price', 'Price unknown'),
                'where_to_buy': p.get('source_domain', 'Online'),
                'product_url': link,
                'image_url': p.get('image', '') or p.get('thumbnail', ''),
                'confidence_level': 'safe_bet',
                'gift_type': 'physical',
                'interest_match': p.get('interest_match', ''),
            }
            cleaned.append(replacement)
            used_urls.add(link)
            if brand:
                used_brands.add(brand)
            if category:
                used_categories.add(category)
            if interest:
                interest_counts[interest] = interest_counts.get(interest, 0) + 1
            r_source = p.get('source_domain', 'unknown').lower()
            source_counts[r_source] = source_counts.get(r_source, 0) + 1
            logger.info(f"CLEANUP: Added replacement from pool: {replacement['name'][:50]}")

    logger.info(f"Post-curation cleanup complete: {len(cleaned)} products "
                f"({len(used_brands)} unique brands, {len(used_categories)} unique categories)")

    return cleaned[:rec_count]
