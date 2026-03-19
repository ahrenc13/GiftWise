"""
POST-CURATION CLEANUP — Programmatic enforcement of gift quality rules.

Runs AFTER the curator (LLM) returns its selections but BEFORE display.
Fixes problems that prompt instructions alone cannot guarantee:

1. Brand deduplication — max 1 product per brand
2. Category deduplication — max 1 product per item type (candle, mug, etc.)
3. Interest spread — max 2 products per interest
4. URL inventory validation — every product_url must exist in the original pool
5. Title cleanup — strip SEO spam, model numbers, size specs

⚠️  OPUS-ONLY ZONE — NO EXCEPTIONS ⚠️
The rule RELAXATIONS in this file are intentional and nuanced. Sonnet sessions
must NOT modify:
  - Rule 3 brand dedup relaxation (same brand allowed across DIFFERENT categories —
    e.g., Taylor Swift poster + Taylor Swift enamel pin both pass. This is correct.)
  - Rule 4b uncategorized near-duplicate logic (3+ word overlap threshold)
  - MAX_PER_SOURCE_PCT (60% source diversity cap)
  - The deferred→replacement backfill logic
These were tuned to balance diversity with not killing good picks. Tightening any
rule without understanding the cascade effects will silently degrade output quality.
If you're Sonnet and see a cleanup problem, add "# SONNET-FLAG:" comment and move on.

Safe for any session: adding new category patterns to detect_category(), adding
new brand patterns to extract_brand(), fixing crashes or logging.

Author: Chad + Claude
Date: February 2026
"""

import re
import logging
from collections import defaultdict

# Marketplace names that should never appear as the display retailer.
# When a product comes from one of these, show the brand instead.
_MARKETPLACE_NAMES = {'tiktok shop', 'cj affiliate', 'cj', 'shareasale', 'unknown'}


def _build_replacement_why_perfect(product):
    """Build a why_perfect for replacement/backfill products.

    The generic "rounds out the gift set" template signals to users that
    the recommendation is filler. This version uses the product title,
    interest match, and snippet to construct something that at least names
    the product and connects it to the person's interest.
    """
    interest = product.get('interest_match', '')
    title = (product.get('title') or '').strip()
    snippet = (product.get('snippet') or '').strip()

    # Truncate overly long marketplace titles
    title_words = title.split()
    title_short = ' '.join(title_words[:8]).lower() if len(title_words) > 8 else title.lower()

    if interest and snippet:
        snippet_clean = snippet[:100].rstrip('.').strip()
        return (f"Picked for their {interest} side — {snippet_clean.lower()}. "
                f"Something they'd want but probably wouldn't grab for themselves.")
    elif interest:
        return (f"A solid find for their {interest} passion — {title_short} "
                f"that hits the mark.")
    else:
        return f"A thoughtful pick — {title_short} that adds something personal to the set."


def _display_retailer(source_domain, brand=None):
    """Return a display-friendly retailer label.

    TikTok Shop, CJ Affiliate, etc. are backend networks — showing them
    on cards signals 'dropship' to users and hurts conversion. When a
    product comes from one of these, surface the brand if we have it,
    otherwise fall back to 'Online Shop'.
    """
    if not source_domain or source_domain.lower() in _MARKETPLACE_NAMES:
        if brand and len(brand.strip()) > 1:
            return brand.strip().title()
        return 'Online Shop'
    return source_domain

logger = logging.getLogger(__name__)

# Words that look like proper nouns in product titles but are NOT person surnames.
# Used to filter false positives when detecting artist/person name brands.
_TITLE_CASE_NON_NAMES = {
    # Temporal / seasonal
    'christmas', 'holiday', 'halloween', 'thanksgiving', 'birthday', 'wedding',
    'valentine', 'mothers', 'fathers', 'anniversary', 'seasonal', 'spring',
    'summer', 'autumn', 'winter', 'fall',
    # Descriptors
    'vintage', 'retro', 'classic', 'special', 'limited', 'official', 'licensed',
    'handmade', 'custom', 'personalized', 'engraved', 'premium', 'deluxe',
    'unique', 'original', 'authentic', 'genuine', 'exclusive', 'rare',
    # Media / entertainment genre words
    'movie', 'music', 'band', 'film', 'show', 'concert', 'tour', 'album',
    'musical', 'theater', 'broadway', 'musicals', 'horror', 'comedy', 'drama',
    'rock', 'punk', 'jazz', 'blues', 'folk', 'country', 'metal', 'pop', 'soul',
    'swing', 'disco', 'funk', 'reggae', 'gospel', 'gothic', 'grunge', 'emo',
    'rockabilly', 'classical', 'opera',
    # Product/category words
    'poster', 'print', 'framed', 'unframed', 'canvas', 'wall', 'art', 'decor',
    'style', 'design', 'pattern', 'graphic',
    'shirt', 'tshirt', 'hoodie', 'jacket', 'pants', 'shorts', 'dress', 'skirt',
    'tote', 'bag', 'purse', 'backpack', 'wallet',
    'earring', 'necklace', 'bracelet', 'ring', 'charm', 'pendant',
    'mug', 'cup', 'tumbler', 'glass', 'bottle', 'flask',
    'book', 'guide', 'journal', 'planner', 'notebook',
    'vinyl', 'record', 'tape', 'digital',
    'set', 'pack', 'bundle', 'collection', 'kit',
    'ornament', 'decoration', 'ball',
    'pillow', 'blanket', 'throw', 'quilt',
    # Common adjectives / prepositions that can appear Title-cased mid-title
    'dark', 'light', 'black', 'white', 'red', 'blue', 'pink', 'green', 'gold',
    'silver', 'brown', 'purple', 'orange', 'yellow', 'grey', 'gray',
    'before', 'after', 'during', 'with', 'from', 'into', 'onto', 'upon',
    'little', 'big', 'small', 'mini', 'large', 'giant', 'super', 'mega', 'ultra',
    'new', 'old', 'young', 'cute', 'funny', 'cool', 'best', 'great', 'awesome',
    'night', 'day', 'morning', 'evening', 'love', 'heart', 'soul', 'dream',
    # Halloween / costume descriptors
    'clown', 'witch', 'vampire', 'zombie', 'ghost', 'skeleton', 'monster',
    # Material
    'cotton', 'wool', 'silk', 'leather', 'velvet', 'linen', 'wooden', 'ceramic',
    # Ticket/event words
    'concert', 'tickets', 'show', 'tour', 'festival',
}


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

    # Look for person/artist name patterns: two ADJACENT Title-case words
    # that don't look like product descriptors.
    # e.g. "Nightmare Before Christmas Danny Elfman Poster" → "danny elfman"
    #       "Danny Elfman Movie & TV Music Book"            → "danny elfman"
    #       "Leslie Odom Jr. Concert Tickets - Boston"      → "leslie odom"
    #
    # Strategy: extract all Title-case words in order, then check consecutive pairs.
    # Use _is_non_name() to handle plurals (records→record, earrings→earring).
    def _is_non_name(word):
        w = word.lower()
        return w in _TITLE_CASE_NON_NAMES or w.rstrip('s') in _TITLE_CASE_NON_NAMES

    title_words = re.findall(r'\b([A-Z][a-z]{1,15})\b', title)
    for i in range(len(title_words) - 1):
        first, second = title_words[i], title_words[i + 1]
        # Verify the pair actually appears adjacent in the original title
        if not re.search(r'\b' + re.escape(first) + r'\s+' + re.escape(second) + r'\b', title):
            continue
        if not _is_non_name(first) and not _is_non_name(second):
            return f"{first.lower()} {second.lower()}"

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
# Replacement relevance check
# ---------------------------------------------------------------------------

_QUERY_STOPWORDS = {'a', 'an', 'the', 'and', 'or', 'for', 'of', 'in', 'on', 'at', 'to', 'with', 'fan', 'gift', 'music'}

# Price threshold for the replacement relevance gate. Replacements above this
# price are only kept if at least one meaningful word from interest_match
# appears in the product title. This prevents high-ticket off-interest items
# (e.g. an $180 power drill from an Awin home-improvement feed) from winning
# the replacement competition via source-diversity bonus alone.
REPLACEMENT_PRICE_THRESHOLD = 120

# For holiday/occasion interests, the product title must contain at least one
# thematically related word. Without this, eBay's search can return a generic
# "Wall-Mounted Storage Box" for "halloween decorating" because Halloween is
# buried in the listing description/tags — but the product has no Halloween theming.
# This is a factual/rule mismatch (zero overlap), not a taste judgment.
_OCCASION_TITLE_ANCHORS = {
    'halloween': {
        'halloween', 'spooky', 'scary', 'creepy', 'eerie', 'ghoulish', 'macabre', 'sinister',
        'ghost', 'ghostly', 'spirit', 'specter',
        'witch', 'witchy', 'cauldron', 'broomstick', 'coven',
        'pumpkin', 'jack-o-lantern', 'jack o lantern',
        'skull', 'skeleton', 'bones', 'grim reaper',
        'horror', 'horrifying', 'haunted', 'haunt',
        'bat', 'boo', 'trick', 'treat', 'costume',
        'undead', 'zombie', 'vampire', 'werewolf', 'mummy', 'demon', 'frankenstein', 'dracula',
        'cobweb', 'spider', 'raven', 'black cat', 'graveyard', 'cemetery', 'tombstone',
        'monster', 'goblin', 'ogre', 'wicked',
    },
    'christmas': {
        'christmas', 'xmas', 'x-mas',
        'santa', 'saint nick', 'st nick', 'st. nick', 'father christmas',
        'holiday', 'festive', 'yuletide', 'jolly', 'merry',
        'ornament', 'garland', 'tinsel', 'wreath', 'stocking',
        'reindeer', 'rudolph', 'prancer', 'dasher', 'comet', 'vixen', 'sleigh', 'jingle',
        'elf', 'elves', 'workshop', 'north pole',
        'noel', 'advent', 'carol', 'caroling',
        'snowflake', 'snowman', 'frosty',
        'mistletoe', 'holly', 'nutcracker', 'gingerbread',
    },
    'thanksgiving': {
        'thanksgiving', 'turkey', 'gobble',
        'harvest', 'cornucopia', 'pilgrim', 'mayflower',
        'pumpkin pie', 'cranberry', 'stuffing', 'gravy',
        'autumn', 'fall leaves', 'november',
    },
    'easter': {
        'easter', 'bunny', 'rabbit',
        'egg hunt', 'easter egg', 'pastel',
        'chick', 'duckling', 'spring basket',
        'resurrection', 'cross', 'lily',
    },
    'hanukkah': {
        'hanukkah', 'chanukah', 'hanukah',
        'menorah', 'dreidel', 'gelt', 'latke',
        'star of david', 'jewish', 'hebrew',
    },
    'valentine': {
        'valentine', "valentine's", 'valentines',
        'love', 'romantic', 'romance', 'sweetheart', 'darling',
        'heart', 'hearts', 'cupid', 'roses', 'red roses', 'bouquet',
        'anniversary', 'beloved', 'affection', 'xoxo',
    },
    "st patrick": {
        "st patrick", "saint patrick", "st. patrick",
        'shamrock', 'clover', 'four leaf', 'leprechaun',
        'irish', 'ireland', 'celtic', 'emerald',
    },
    'mothers day': {
        "mother's day", 'mothers day',
        'mom', 'mother', 'mama', 'mommy', 'mum',
    },
    'fathers day': {
        "father's day", 'fathers day',
        'dad', 'father', 'papa', 'daddy',
    },
    'fourth of july': {
        'fourth of july', '4th of july', 'independence day',
        'patriotic', 'american flag', 'fireworks', 'stars and stripes',
        'usa', 'red white blue', 'liberty', 'freedom',
    },
    'new year': {
        'new year', "new year's", 'nye', 'new years eve',
        'countdown', 'midnight', 'champagne', 'resolution',
        'celebration', 'confetti', 'fireworks',
    },
}

def _is_query_relevant_to_product(product):
    """
    Check that an inventory product is genuinely relevant to the search query it came from.
    Catches cases like artist-name searches (e.g. "JD McPherson") returning generic
    surname-only products (e.g. "McPherson T-Shirt", "Clan McPherson Tote Bag").
    Also catches holiday searches returning generic storage/utility products with no
    thematic connection to the holiday (e.g. "Wall-Mounted Storage Box" for "halloween decorating").

    Returns True if the product is relevant (keep), False if it's a mismatch (skip).
    """
    title = (product.get('title') or '').lower()
    query = (product.get('search_query') or '').lower().strip()
    interest = (product.get('interest_match') or '').lower().strip()

    if not title:
        return True  # Can't judge — keep it

    # Hard block: generic surname/clan/heritage products are always low-relevance
    # These are mass-produced eBay/Amazon products for any possible last name
    bad_phrases = ('surname', 'clan gift', 'family name gift', 'family crest', 'heritage gift',
                   'coat of arms', 'scottish clan', 'irish clan', 'welsh clan')
    if any(phrase in title for phrase in bad_phrases):
        logger.info(f"CLEANUP: Skipping replacement (generic surname product): {title[:60]}")
        return False

    # Holiday/occasion check: if the interest is holiday-themed, require at least one
    # thematically related word in the title. eBay sometimes returns products with
    # holiday keywords buried in description/tags that don't belong in a gift set.
    for occasion, anchor_words in _OCCASION_TITLE_ANCHORS.items():
        if occasion in interest or occasion in query:
            if not any(w in title for w in anchor_words):
                logger.info(f"CLEANUP: Skipping replacement (no {occasion} theme in title): {title[:60]}")
                return False
            break  # Only one occasion can apply; stop after first match

    if not query:
        return True

    # For person-name queries (2 tokens, first is short initial OR normal first name),
    # require the title to contain the first token (first name / initial).
    # Example: query="jd mcpherson" → title must contain "jd" OR "j.d." to pass.
    # This blocks "mcpherson t-shirt" (matches only on last name).
    query_words = [w for w in query.split() if w not in _QUERY_STOPWORDS and len(w) > 1]
    if len(query_words) == 2:
        first, last = query_words
        # Check if this looks like a person name (last word is a significant proper noun)
        # by seeing if only the last name appears in the title
        if last in title and first not in title:
            # Last name found but first name/initial missing — likely a surname-only match
            logger.info(f"CLEANUP: Skipping replacement (surname-only match, query='{query}'): {title[:60]}")
            return False

    # Price × interest-relevance gate for replacements.
    # High-price items from broad-catalog feeds (Awin, CJ) can enter the pool via
    # coincidental keyword matches and then win the replacement competition through
    # the +3 source-diversity bonus. If price > threshold AND no meaningful word from
    # interest_match appears in the product title, reject the replacement.
    # This catches: $180 power drill (interest="home renovation", title has no
    # interest words). This keeps: $150 espresso machine (interest="coffee",
    # title contains "espresso" → shared domain word).
    price_str = product.get('price', '')
    try:
        price_val = float(re.sub(r'[^\d.]', '', str(price_str).split('-')[0].split('From')[-1]))
    except (ValueError, TypeError, IndexError):
        price_val = None

    if price_val is not None and price_val > REPLACEMENT_PRICE_THRESHOLD:
        interest_words = [w for w in interest.split() if w not in _QUERY_STOPWORDS and len(w) > 2]
        title_has_interest_word = any(w in title for w in interest_words)
        if not title_has_interest_word:
            logger.info(
                f"CLEANUP: Skipping replacement (price ${price_val:.0f} > ${REPLACEMENT_PRICE_THRESHOLD}, "
                f"no interest words in title, interest='{interest}'): {title[:60]}"
            )
            return False

    return True


# ---------------------------------------------------------------------------
# Category detection
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# MECE PRODUCT FORM TAXONOMY
#
# Mutually exclusive, collectively exhaustive. The test for each category:
# "Would two of these in the same result set feel redundant to the recipient?"
#
# Organized into form classes for documentation, but the dedup engine uses
# the flat category key. Order matters: first match wins, so more specific
# patterns (e.g. 'journal') must come before broader ones (e.g. 'book').
#
# Form classes (for reference, not used in code):
#   WEARABLE:    t-shirt, hoodie, hat, jewelry, watch, socks, bag, wallet
#   DECORATIVE:  poster, candle, blanket, pillow, ornament, figurine, plant
#   DRINKWARE:   mug, bottle, glass
#   MEDIA:       book, journal, vinyl, game, puzzle
#   EQUIPMENT:   headphones, speaker, adapter, kitchen
#   NOVELTY:     keychain, sticker, magnet, coaster, phone-case
#   CRAFT:       kit
#   OTHER:       hook (catch-all for misc hardware)
# ---------------------------------------------------------------------------
CATEGORY_PATTERNS = {
    # --- WEARABLE ---
    't-shirt': r'\b(?:t-?shirt|tee|tshirt|graphic tee)[s]?\b',
    'hoodie': r'\b(?:hoodie|sweatshirt|pullover|crewneck)[s]?\b',
    'hat': r'\b(?:hat|cap|beanie|snapback|trucker hat)[s]?\b',
    'jewelry': r'\b(?:necklace|bracelet|earring|ring|pendant|charm|anklet|brooch)[s]?\b',
    'watch': r'\b(?:watch|smartwatch|wristwatch)(?:es)?\b',
    'socks': r'\b(?:socks|sock set)\b',
    'bag': r'\b(?:bag|tote|backpack|purse|clutch|toiletry|duffel|messenger bag|crossbody)[s]?\b',
    'wallet': r'\b(?:wallet|card holder|money clip)\b',

    # --- DECORATIVE ---
    'poster': r'\b(?:poster|wall art|print|art print)[s]?\b',
    'candle': r'\bcandle[s]?\b',
    'blanket': r'\b(?:blanket|throw|quilt|afghan)[s]?\b',
    'pillow': r'\b(?:pillow|cushion)[s]?\b',
    'ornament': r'\b(?:ornament|decoration)[s]?\b',
    'figurine': r'\b(?:figurine|figure|statue|bust|bobblehead|funko)[s]?\b',
    'plant': r'\b(?:plant|planter|succulent|terrarium|herb garden)[s]?\b',

    # --- DRINKWARE (split: mug ≠ bottle ≠ glass) ---
    'mug': r'\b(?:mug|coffee cup|tea cup)[s]?\b',
    'bottle': r'\b(?:water bottle|thermos|tumbler|flask|hydro)[s]?\b',
    'glass': r'\b(?:glass|glasses|pint glass|wine glass|glassware|whiskey glass|rocks glass)\b',

    # --- MEDIA (journal split from book; vinyl standalone) ---
    'journal': r'\b(?:journal|diary|planner|notebook|bullet journal)[s]?\b',
    'book': r'\b(?:book|novel|cookbook|memoir|biography|graphic novel)[s]?\b',
    'vinyl': r'\b(?:vinyl|vinyl record|LP|record album)[s]?\b',
    'game': r'\b(?:board game|card game|game set|tabletop game)\b',
    'puzzle': r'\b(?:puzzle|jigsaw)[s]?\b',

    # --- EQUIPMENT ---
    'headphones': r'\b(?:headphone|earbuds?|earbud|in-ear|over-ear|wireless buds?)[s]?\b',
    'speaker': r'\b(?:speaker|bluetooth speaker|portable speaker|soundbar)[s]?\b',
    'adapter': r'\b(?:adapter|converter|plug|charger)[s]?\b',
    'kitchen': r'\b(?:kitchen utensil|cooking set|utensil set|chef set|wooden spoon set|spatula set|apron set|cookware set|grilling set)\b',

    # --- NOVELTY / SMALL ITEMS ---
    'keychain': r'\b(?:keychain|key chain|key ring)[s]?\b',
    'sticker': r'\b(?:sticker|decal)[s]?\b',
    'magnet': r'\b(?:magnet|fridge magnet)[s]?\b',
    'coaster': r'\b(?:coaster)[s]?\b',
    'phone-case': r'\b(?:phone case|iphone case|case for)\b',

    # --- CRAFT ---
    'kit': r'\b(?:essentials kit|starter kit|travel kit|care kit|making kit|craft kit|diy kit)\b',

    # --- SUBSCRIPTION ---
    'subscription': r'\b(?:subscription|of the month|monthly club|membership box)[s]?\b',

    # --- OTHER ---
    'hook': r'\b(?:hook[s]?|hanger[s]?|door hook)\b',
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
# Title dedup helper
# ---------------------------------------------------------------------------

def _normalize_title_for_dedup(title):
    """Normalize a product title for duplicate detection.
    Strips common noise words so 'Christmas Necktie Holiday Traditions' and
    'Hallmark Holiday Traditions Christmas Silk Tie' collapse to the same key."""
    if not title:
        return ''
    # Lowercase, strip non-alpha, remove very common filler (including colors/sizes
    # which only distinguish variants of the same product, not distinct products)
    words = re.sub(r'[^a-z0-9 ]', '', title.lower()).split()
    noise = {'the', 'a', 'an', 'and', 'or', 'for', 'of', 'with', 'in', 'on',
             'new', 'set', 'lot', 'pack', 'pcs', 'piece', 'pieces',
             # Colors / variant words that distinguish SKUs but not distinct products
             'black', 'white', 'red', 'blue', 'green', 'pink', 'grey', 'gray',
             'brown', 'beige', 'navy', 'gold', 'silver', 'purple', 'orange', 'yellow',
             'small', 'medium', 'large', 'xlarge', 'xxl', 'mini', 'size', 'single', 'double'}
    key_words = sorted(w for w in words if w not in noise and len(w) > 2)
    return ' '.join(key_words)


def _is_near_duplicate_title(norm_title, used_titles_set):
    """Return True if norm_title is an exact or near-duplicate of any title in used_titles_set.
    Near-duplicate = 85%+ word overlap (catches color/size variants with identical base titles)."""
    if not norm_title:
        return False
    if norm_title in used_titles_set:
        return True
    candidate_words = set(norm_title.split())
    if len(candidate_words) < 3:
        return False  # Too short to fuzzy-match reliably
    for existing in used_titles_set:
        existing_words = set(existing.split())
        if not existing_words:
            continue
        overlap = len(candidate_words & existing_words)
        smaller = min(len(candidate_words), len(existing_words))
        if smaller > 0 and overlap / smaller >= 0.85:
            return True
    return False


# ---------------------------------------------------------------------------
# Main cleanup function
# ---------------------------------------------------------------------------

def cleanup_curated_gifts(product_gifts, inventory, rec_count=10, profile_interests=None):
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
    used_titles = set()  # For title-based dedup (used in Rule 4b for uncategorized products)

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

        # Rule 3: Brand diversity — max 1 per brand, UNLESS categories differ
        # (e.g., Taylor Swift poster + Taylor Swift enamel pin are different gift types)
        if brand and brand in used_brands:
            if not category or category in used_categories:
                logger.info(f"CLEANUP: Deferred (duplicate brand '{brand}'): {name[:50]}")
                deferred.append(gift)
                continue
            else:
                logger.info(f"CLEANUP: Allowed duplicate brand '{brand}' (different category '{category}'): {name[:50]}")

        # Rule 4: Category diversity — max 1 per category
        if category and category in used_categories:
            logger.info(f"CLEANUP: Deferred (duplicate category '{category}'): {name[:50]}")
            deferred.append(gift)
            continue

        # Rule 4b: Uncategorized duplicate detection — if two products share no
        # recognized category but have 3+ title words in common, treat as duplicate
        if not category:
            norm = _normalize_title_for_dedup(name)
            if _is_near_duplicate_title(norm, used_titles):
                logger.info(f"CLEANUP: Deferred (uncategorized near-duplicate title): {name[:50]}")
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
        norm_t = _normalize_title_for_dedup(name)
        if norm_t:
            used_titles.add(norm_t)
        source_counts[source] += 1
        cleaned.append(gift)

    logger.info(f"After rules: {len(cleaned)} passed, {len(deferred)} deferred")

    # If we're short, try to fill from inventory (products not already selected)
    if len(cleaned) < rec_count:
        needed = rec_count - len(cleaned)
        logger.info(f"Need {needed} replacements from inventory pool")

        # Build word set from profile interests for relevance gating.
        # Only words longer than 2 chars — filters out 'of', 'in', 'a', etc.
        profile_interest_words = set()
        if profile_interests:
            for name in profile_interests:
                profile_interest_words.update(
                    w.lower() for w in name.lower().split() if len(w) > 2
                )

        # Score remaining inventory by whether they bring diversity
        candidates = []
        for p in (inventory or []):
            link = (p.get('link') or '').strip()
            if not link or link in used_urls or link.rstrip('/') in used_urls:
                continue
            # Skip products whose titles match (exact or near-duplicate) something already selected
            norm_title = _normalize_title_for_dedup(p.get('title', ''))
            if _is_near_duplicate_title(norm_title, used_titles):
                continue
            brand = extract_brand(p.get('title', ''))
            category = detect_category(p.get('title', ''), p.get('snippet', ''))
            # Skip if brand or category already used (same rules as main loop)
            if brand and brand in used_brands:
                continue
            if category and category in used_categories:
                continue
            # Skip low-relevance replacements — products that only matched on surname/last name
            # when the search query was a full artist/person name (e.g. "JD McPherson" → "McPherson T-Shirt")
            if not _is_query_relevant_to_product(p):
                continue
            # Skip replacements whose interest has zero overlap with the actual profile.
            # The database cache spans multiple sessions — a candy product cached from a
            # "sweets lover" profile should never replace a deferred jewelry item for a
            # miniature-crafting / vintage-fashion profile. We check word-level overlap
            # (e.g. interest_match='sweets' vs profile_interests=['miniature crafting',
            # 'vintage fashion', 'pug']). Empty interest_match passes through (can't judge).
            p_interest = (p.get('interest_match') or '').lower()
            if profile_interest_words and p_interest:
                interest_words = [w for w in p_interest.split() if len(w) > 2]
                if interest_words and not any(w in profile_interest_words for w in interest_words):
                    continue
            # Prefer products that bring new brands, categories, and source diversity
            score = 0
            if brand and brand not in used_brands:
                score += 2
            if category and category not in used_categories:
                score += 2
            interest = (p.get('interest_match') or '').lower()
            if interest and interest_counts.get(interest, 0) < 2:
                score += 1
            else:
                score -= 1  # Penalize interest already at cap
            p_source = p.get('source_domain', 'unknown').lower()
            if source_counts.get(p_source, 0) == 0:
                score += 3  # Strongly prefer unrepresented sources
            elif source_counts.get(p_source, 0) < max(2, int(rec_count * MAX_PER_SOURCE_PCT)):
                score += 1
            candidates.append((score, p))

        # Sort by diversity score (highest first)
        candidates.sort(key=lambda x: x[0], reverse=True)

        added = 0
        for score, p in candidates:
            if added >= needed:
                break
            link = (p.get('link') or '').strip()
            # Re-check dedup guards: candidates were built before any replacements
            # were added, so the same product can appear multiple times in the list.
            if not link or link in used_urls or link.rstrip('/') in used_urls:
                continue
            norm_title = _normalize_title_for_dedup(p.get('title', ''))
            if _is_near_duplicate_title(norm_title, used_titles):
                continue
            brand = extract_brand(p.get('title', ''))
            category = detect_category(p.get('title', ''), p.get('snippet', ''))
            interest = (p.get('interest_match') or '').lower()

            # Build a gift dict from inventory product
            replacement = {
                'name': clean_title(p.get('title', 'Gift')),
                'description': p.get('snippet', ''),
                'why_perfect': _build_replacement_why_perfect(p),
                'price': p.get('price', 'Price unknown'),
                'where_to_buy': _display_retailer(p.get('source_domain'), p.get('brand')),
                'product_url': link,
                'image_url': p.get('image', '') or p.get('thumbnail', ''),
                'confidence_level': 'safe_bet',
                'gift_type': 'physical',
                'interest_match': p.get('interest_match', ''),
            }
            cleaned.append(replacement)
            added += 1
            used_urls.add(link)
            if norm_title:
                used_titles.add(norm_title)
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
