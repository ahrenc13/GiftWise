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
    # Multiple query suffixes for variety — different runs get different products
    GIFT_SUFFIXES = ["gift", "present", "gift idea", "accessories", "lover gift"]
    FAN_SUFFIXES = ["fan gift", "merchandise", "memorabilia", "fan gear", "collectible"]
    SPORTS_SUFFIXES = ["fan merchandise", "gear", "fan gift", "memorabilia", "apparel"]

    search_queries = []
    for interest in interests:
        name = interest.get("name", "")
        if not name:
            continue
        if interest.get("is_work", False):
            logger.info("Skipping work interest for eBay: %s", name)
            continue
        name_lower = name.lower()
        if any(term in name_lower for term in ["music", "band", "singer", "artist"]):
            suffix = random.choice(FAN_SUFFIXES)
        elif any(term in name_lower for term in ["sports", "basketball", "team"]):
            suffix = random.choice(SPORTS_SUFFIXES)
        else:
            suffix = random.choice(GIFT_SUFFIXES)
        search_queries.append({
            "query": f"{name} {suffix}",
            "interest": name,
            "priority": "high" if interest.get("intensity") == "passionate" else "medium",
        })
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
        params = {
            "q": query[:100],
            "limit": min(per_query, 50),
            "offset": random.choice([0, 0, 0, 5, 10, 15]),
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
            link = item.get("itemWebUrl") or ""
            if not link:
                continue
            image_obj = item.get("image") or {}
            image = image_obj.get("imageUrl", "")
            price_obj = item.get("price") or {}
            price_val = price_obj.get("value", "")
            currency = price_obj.get("currency", "USD")
            price = f"${price_val} {currency}" if price_val else ""
            seller = item.get("seller") or {}
            seller_name = seller.get("username", "")
            snippet = f"From {seller_name}" if seller_name else title[:100]

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
