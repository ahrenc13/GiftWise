"""
RapidAPI Amazon product search – Real-Time Amazon Data API.

Uses the "Real-Time Amazon Data" API on RapidAPI (OpenWeb Ninja).
- Subscribe: https://rapidapi.com/letscrape-6bRBa3QguO5/api/real-time-amazon-data
- Endpoint: GET /search (Product Search)
- Env: RAPIDAPI_KEY (your RapidAPI key; same key works for any RapidAPI API you subscribe to)

Returns products in our standard format (title, link, image, price, source_domain, etc.).
"""

import logging
import requests

logger = logging.getLogger(__name__)

# Real-Time Amazon Data API (OpenWeb Ninja)
RAPIDAPI_AMAZON_HOST = "real-time-amazon-data.p.rapidapi.com"
RAPIDAPI_SEARCH_URL = "https://real-time-amazon-data.p.rapidapi.com/search"


def search_products_rapidapi_amazon(profile, api_key, target_count=20):
    """
    Search Amazon via RapidAPI Real-Time Amazon Data (product search).

    Builds queries from profile interests (e.g. "dog gift", "basketball fan merchandise"),
    calls the search endpoint, and maps results to our product format.
    """
    if not (api_key and api_key.strip()):
        logger.warning("RapidAPI key not configured - skipping Amazon search")
        return []

    key = api_key.strip()
    interests = profile.get("interests", [])
    if not interests:
        return []

    search_queries = []
    for interest in interests:
        name = interest.get("name", "")
        if not name:
            continue
        if interest.get("is_work", False):
            logger.info("Skipping work interest for Amazon: %s", name)
            continue
        name_lower = name.lower()
        if any(term in name_lower for term in ["music", "band", "singer", "artist"]):
            query = f"{name} fan gift"
        elif any(term in name_lower for term in ["sports", "basketball", "team"]):
            query = f"{name} fan merchandise"
        else:
            query = f"{name} gift"
        search_queries.append({
            "query": query,
            "interest": name,
            "priority": "high" if interest.get("intensity") == "passionate" else "medium",
        })
    search_queries = search_queries[:8]
    if not search_queries:
        return []

    all_products = []
    seen_asins = set()
    # Cap at 2 per query so results span multiple interests (avoid "all dog" or "all one interest")
    per_query = min(2, max(1, (target_count + len(search_queries) - 1) // len(search_queries)))

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
        params = {
            "query": query[:100],
            "country": "US",
            "page": 1,
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
                item.get("thumbnail") or item.get("image") or item.get("product_thumbnail")
                or item.get("product_image") or item.get("main_image") or item.get("image_url")
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
