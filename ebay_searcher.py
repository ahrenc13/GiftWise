"""
eBay product search via Browse API.

Uses OAuth client credentials (EBAY_CLIENT_ID, EBAY_CLIENT_SECRET) to get an
application token, then calls item_summary/search for keyword search.
Returns products in our standard format (title, link, image, price, etc.).
"""

import base64
import logging
import time

import requests

logger = logging.getLogger(__name__)

try:
    from rapidapi_amazon_searcher import _clean_interest_for_search, _categorize_interest, _QUERY_SUFFIXES
except ImportError:
    # Fallback if import fails — use simple passthrough
    def _clean_interest_for_search(name):
        return name
    def _categorize_interest(name_lower):
        return 'default'
    _QUERY_SUFFIXES = {'default': ['gift', 'accessories', 'lover gift']}

# Token cache: reuse until ~5 min before expiry
_ebay_token = None
_ebay_token_expires = 0
EBAY_TOKEN_BUFFER = 300

BROWSE_SEARCH_URL = "https://api.ebay.com/buy/browse/v1/item_summary/search"
TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"
SCOPE = "https://api.ebay.com/oauth/api_scope"


def _get_app_token(client_id, client_secret):
    """Get or refresh eBay application access token (client credentials grant)."""
    global _ebay_token, _ebay_token_expires
    now = time.time()
    if _ebay_token and now < _ebay_token_expires - EBAY_TOKEN_BUFFER:
        return _ebay_token
    credentials = f"{client_id}:{client_secret}"
    b64 = base64.b64encode(credentials.encode()).decode()
    try:
        r = requests.post(
            TOKEN_URL,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": f"Basic {b64}",
            },
            data={
                "grant_type": "client_credentials",
                "scope": SCOPE,
            },
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
        _ebay_token = data.get("access_token")
        expires_in = int(data.get("expires_in", 7200))
        _ebay_token_expires = now + expires_in
        logger.info("eBay app token obtained, expires in %s s", expires_in)
        return _ebay_token
    except requests.RequestException as e:
        logger.warning("eBay token request failed: %s", e)
        return None


def search_products_ebay(profile, client_id, client_secret, target_count=20):
    """
    Search eBay for gift products by profile interests.

    Uses Browse API item_summary/search. Builds queries from non-work interests
    (e.g. "dog gift", "basketball fan merchandise"). Returns list of product dicts.
    """
    if not (client_id and client_secret):
        logger.warning("eBay credentials not set - skipping eBay search")
        return []

    token = _get_app_token(client_id.strip(), client_secret.strip())
    if not token:
        return []

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
            logger.info("Skipping work interest for eBay: %s", name)
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
        logger.debug("eBay query: '%s' → '%s' (category: %s)", name, query, category)
    search_queries = search_queries[:10]
    if not search_queries:
        return []

    all_products = []
    seen_ids = set()
    per_query = max(3, (target_count // len(search_queries)) + 1)

    for q in search_queries:
        if len(all_products) >= target_count:
            break
        query = q["query"]
        interest = q["interest"]
        priority = q["priority"]
        # Randomize offset so repeat runs surface different products
        # Keep offset low — higher offsets cause 400 errors on narrow queries
        params = {
            "q": query[:100],
            "limit": min(per_query, 50),
            "offset": random.choice([0, 0, 0, 0, 5]),
            "filter": "conditionIds:{1000|1500|1750|2000|2500}",  # New, Open Box, New with defects, Certified Refurb, Seller Refurb
        }
        try:
            r = requests.get(
                BROWSE_SEARCH_URL,
                headers={
                    "Authorization": f"Bearer {token}",
                    "X-EBAY-C-MARKETPLACE-ID": "EBAY_US",
                },
                params=params,
                timeout=15,
            )
            r.raise_for_status()
            data = r.json()
        except requests.RequestException as e:
            logger.warning("eBay search failed for '%s': %s", query, e)
            continue

        summaries = data.get("itemSummaries") or []
        for item in summaries:
            if len(all_products) >= target_count:
                break
            item_id = item.get("itemId")
            if not item_id or item_id in seen_ids:
                continue
            title = (item.get("title") or "").strip()
            if not title:
                continue
            # Skip used/pre-owned items — bad gift quality
            condition = (item.get("condition") or "").strip()
            if condition.lower() in ("pre-owned", "used", "for parts or not working", "acceptable"):
                logger.debug("Skipping used eBay item: %s (%s)", title[:50], condition)
                continue
            link = item.get("itemWebUrl") or ""
            if not link:
                continue
            image_obj = item.get("image") or {}
            image = image_obj.get("imageUrl", "")
            price_obj = item.get("price") or {}
            price_val = price_obj.get("value", "")
            currency = price_obj.get("currency", "USD")
            price = f"${price_val} {currency}" if price_val else ""
            short_desc = (item.get("shortDescription") or "").strip()
            categories = item.get("categories") or []
            category_name = categories[0].get("categoryName", "") if categories else ""
            condition = (item.get("condition") or "").strip()
            snippet_parts = [s for s in [short_desc[:120], category_name, condition] if s]
            snippet = " | ".join(snippet_parts) if snippet_parts else title[:120]

            product = {
                "title": title[:200],
                "link": link,
                "snippet": snippet,
                "image": image,
                "thumbnail": image,
                "image_url": image,
                "source_domain": "ebay.com",
                "search_query": query,
                "interest_match": interest,
                "priority": priority,
                "price": price,
                "product_id": str(item_id),
            }
            seen_ids.add(item_id)
            all_products.append(product)

    logger.info("Found %s eBay products", len(all_products))
    return all_products[:target_count]
