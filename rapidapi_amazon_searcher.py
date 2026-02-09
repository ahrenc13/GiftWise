"""
RapidAPI Amazon product search – Real-Time Amazon Data API.

Uses the "Real-Time Amazon Data" API on RapidAPI (OpenWeb Ninja).
- Subscribe: https://rapidapi.com/letscrape-6bRBa3QguO5/api/real-time-amazon-data
- Endpoint: GET /search (Product Search)
- Env: RAPIDAPI_KEY (your RapidAPI key; same key works for any RapidAPI API you subscribe to)

Returns products in our standard format (title, link, image, price, source_domain, etc.).
"""

import logging
import re
import requests

logger = logging.getLogger(__name__)

# Real-Time Amazon Data API (OpenWeb Ninja)
RAPIDAPI_AMAZON_HOST = "real-time-amazon-data.p.rapidapi.com"
RAPIDAPI_SEARCH_URL = "https://real-time-amazon-data.p.rapidapi.com/search"


# Filler phrases the profile analyzer puts in interest names that hurt search quality.
# "Dog ownership and care" → "Dog", "International travel" stays as-is,
# "Family celebrations and milestone events" → "celebrations milestone"
_INTEREST_FILLER = re.compile(
    r'\b(?:and care|ownership|and maintenance|fandom|and lifestyle|'
    r'personalized|and (?:pop |rock |country )?culture|'
    r'connections and|celebrations and milestone events|'
    r'family celebrations)\b',
    re.IGNORECASE,
)

# Suffixes keyed by category — more specific than generic "gift"
_QUERY_SUFFIXES = {
    'music':   ['merch', 'fan gift', 'vinyl', 'poster', 'accessories'],
    'sports':  ['fan gear', 'jersey', 'memorabilia', 'apparel', 'wall art'],
    'travel':  ['accessories', 'organizer', 'essentials', 'travel kit', 'gadget'],
    'food':    ['lover gift', 'accessories', 'cookbook', 'kitchen gift', 'kit'],
    'pet':     ['accessories', 'toy', 'lover gift', 'supplies', 'treats'],
    'fashion': ['accessories', 'jewelry', 'style gift', 'wardrobe', 'trendy'],
    'home':    ['decor', 'organizer', 'gadget', 'accessories', 'cozy gift'],
    'tech':    ['gadget', 'accessories', 'electronics', 'smart device', 'gear'],
    'fitness': ['gear', 'accessories', 'equipment', 'workout gift', 'apparel'],
    'beauty':  ['set', 'skincare', 'beauty gift', 'tools', 'kit'],
    'default': ['gift', 'unique gift', 'lover gift', 'accessories', 'gift idea'],
}

# Keywords that map interest names to suffix categories
_CATEGORY_SIGNALS = {
    'music':   ['music', 'band', 'singer', 'artist', 'concert', 'vinyl', 'album', 'rap', 'pop', 'rock', 'jazz', 'hip hop'],
    'sports':  ['sports', 'basketball', 'football', 'soccer', 'baseball', 'team', 'nba', 'nfl', 'mlb', 'hockey', 'racing'],
    'travel':  ['travel', 'cruise', 'vacation', 'international', 'destination', 'adventure', 'backpack'],
    'food':    ['cook', 'food', 'baking', 'kitchen', 'culinary', 'recipe', 'chef', 'grill', 'bbq'],
    'pet':     ['dog', 'cat', 'pet', 'puppy', 'kitten', 'animal'],
    'fashion': ['fashion', 'style', 'clothing', 'outfit', 'wardrobe', 'jewelry', 'sneaker', 'shoe'],
    'home':    ['home', 'decor', 'renovation', 'garden', 'plant', 'interior', 'candle', 'cozy'],
    'tech':    ['tech', 'gaming', 'computer', 'gadget', 'electronic', 'phone', 'smart'],
    'fitness': ['fitness', 'gym', 'yoga', 'running', 'workout', 'exercise', 'hiking', 'outdoor'],
    'beauty':  ['beauty', 'skincare', 'makeup', 'cosmetic', 'hair', 'nail', 'spa', 'self-care'],
}


def _clean_interest_for_search(name):
    """Strip filler phrases from interest names to make better search queries.

    'Dog ownership and care' → 'Dog'
    'Taylor Swift fandom' → 'Taylor Swift'
    'Chappell Roan and pop music' → 'Chappell Roan pop music'
    'Home renovation and design' → 'Home renovation design'
    """
    cleaned = _INTEREST_FILLER.sub('', name).strip()
    # Collapse double spaces and trailing 'and'
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    cleaned = re.sub(r'\band\b\s*$', '', cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r'^\band\b\s*', '', cleaned, flags=re.IGNORECASE).strip()
    return cleaned or name


def _categorize_interest(name_lower):
    """Map an interest name to a suffix category."""
    for category, signals in _CATEGORY_SIGNALS.items():
        if any(signal in name_lower for signal in signals):
            return category
    return 'default'


def search_products_rapidapi_amazon(profile, api_key, target_count=20):
    """
    Search Amazon via RapidAPI Real-Time Amazon Data (product search).

    Builds queries from profile interests, cleans interest names for search,
    and uses category-specific suffixes for better product relevance.
    """
    if not (api_key and api_key.strip()):
        logger.warning("RapidAPI key not configured - skipping Amazon search")
        return []

    key = api_key.strip()
    interests = profile.get("interests", [])
    if not interests:
        return []

    import random

    search_queries = []
    for interest in interests:
        name = interest.get("name", "")
        if not name:
            continue
        if interest.get("is_work", False):
            logger.info("Skipping work interest for Amazon: %s", name)
            continue
        cleaned = _clean_interest_for_search(name)
        category = _categorize_interest(cleaned.lower())
        suffix = random.choice(_QUERY_SUFFIXES[category])
        query = f"{cleaned} {suffix}"
        search_queries.append({
            "query": query,
            "interest": name,
            "priority": "high" if interest.get("intensity") == "passionate" else "medium",
        })
        logger.debug("Amazon query: '%s' → '%s' (category: %s)", name, query, category)
    search_queries = search_queries[:12]
    if not search_queries:
        return []

    all_products = []
    seen_asins = set()
    # Allow more per query when target_count is higher; still cap to keep interest diversity
    per_query = min(5, max(2, (target_count + len(search_queries) - 1) // len(search_queries)))

    headers = {
        "X-RapidAPI-Key": key,
        "X-RapidAPI-Host": RAPIDAPI_AMAZON_HOST,
    }

    for q in search_queries:
        if len(all_products) >= target_count:
            break
        query = q["query"]
        interest = q["interest"]
        priority = q["priority"]
        # Randomize page so repeat runs surface different products
        params = {
            "query": query[:100],
            "country": "US",
            "page": random.choice([1, 1, 1, 2, 3]),
        }
        try:
            r = requests.get(
                RAPIDAPI_SEARCH_URL,
                headers=headers,
                params=params,
                timeout=15,
            )
            r.raise_for_status()
            data = r.json()
        except requests.RequestException as e:
            logger.warning("RapidAPI Amazon search failed for '%s': %s", query, e)
            continue

        # Response: { "status": "OK", "request_id": "...", "data": { "products": [...] } or "data": [...] }
        if data.get("status") != "OK":
            logger.warning("RapidAPI Amazon returned status: %s", data.get("status"))
            continue

        raw = data.get("data")
        if isinstance(raw, dict):
            products_list = raw.get("products", raw.get("results", []))
        elif isinstance(raw, list):
            products_list = raw
        else:
            products_list = []

        added_this_query = 0
        for item in products_list:
            if added_this_query >= per_query or len(all_products) >= target_count:
                break
            asin = item.get("asin") or item.get("product_id") or ""
            if asin and asin in seen_asins:
                continue
            title = (item.get("title") or item.get("product_title") or "").strip()
            if not title:
                continue
            link = (item.get("product_url") or item.get("url") or item.get("link") or "").strip()
            if not link:
                link = f"https://www.amazon.com/dp/{asin}" if asin else ""
            if not link:
                continue
            image = (
                item.get("product_photo") or item.get("thumbnail") or item.get("image")
                or item.get("product_thumbnail") or item.get("product_image")
                or item.get("main_image") or item.get("image_url") or item.get("photo")
            )
            if not image and isinstance(item.get("images"), list) and item["images"]:
                image = item["images"][0]
            if isinstance(image, dict):
                image = image.get("url") or image.get("link") or ""
            image = (image or "").strip()
            price_obj = item.get("price") or item.get("current_price") or {}
            if isinstance(price_obj, dict):
                price_val = price_obj.get("value") or price_obj.get("raw") or price_obj.get("current_price")
            else:
                price_val = price_obj
            price = f"${price_val}" if price_val is not None and str(price_val).strip() else ""
            if not price and item.get("price"):
                price = str(item.get("price", "")).strip()

            product = {
                "title": title[:200],
                "link": link,
                "snippet": title[:100],
                "image": image,
                "thumbnail": image,
                "image_url": image,
                "source_domain": "amazon.com",
                "search_query": query,
                "interest_match": interest,
                "priority": priority,
                "price": price or "",
                "product_id": asin or str(hash(title + link))[:16],
            }
            if asin:
                seen_asins.add(asin)
            all_products.append(product)
            added_this_query += 1

    logger.info("Found %s Amazon products (RapidAPI Real-Time Amazon Data)", len(all_products))
    return all_products[:target_count]
