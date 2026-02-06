"""
Awin product search via Data Feed API.

Awin does not offer a keyword search API. Product data comes from product feeds (CSV).
This module:
1. Fetches the feed list: https://productdata.awin.com/datafeed/list/apikey/{key}
2. Downloads one or more feed CSVs (prefer "Joined" advertisers)
3. Searches within cached feed rows by profile interests (e.g. "hiking gift")

Env: AWIN_DATA_FEED_API_KEY (from Awin Toolbox → Create-a-Feed).
"""

import csv
import io
import logging
import re
import time
import zlib
import requests

logger = logging.getLogger(__name__)

# In-memory cache: feed list and one feed's products. TTL 1 hour.
_awin_feed_list_cache = {}
_awin_feed_list_ts = 0
_awin_products_cache = {}
_awin_products_ts = 0
AWIN_CACHE_TTL = 3600


def _get_feed_list(api_key):
    """Fetch CSV list of feeds. Returns list of dicts with url, feed_id, advertiser_name, membership_status."""
    global _awin_feed_list_ts, _awin_feed_list_cache
    now = time.time()
    if now - _awin_feed_list_ts < AWIN_CACHE_TTL and api_key in _awin_feed_list_cache:
        return _awin_feed_list_cache[api_key]

    url = f"https://productdata.awin.com/datafeed/list/apikey/{api_key}"
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
    except requests.RequestException as e:
        logger.warning("Awin feed list request failed: %s", e)
        return []

    text = r.text
    if not text.strip():
        return []

    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)
    # Normalize column names (could be with/without spaces)
    out = []
    for row in rows:
        url_val = (row.get("URL") or row.get("url") or "").strip()
        feed_id = (row.get("Feed ID") or row.get("Feed Id") or row.get("feed_id") or "").strip()
        advertiser = (row.get("Advertiser Name") or row.get("advertiser_name") or "").strip()
        status = (row.get("Membership Status") or row.get("membership_status") or "").strip()
        if url_val:
            out.append({
                "url": url_val,
                "feed_id": feed_id,
                "advertiser_name": advertiser,
                "membership_status": status,
            })
    _awin_feed_list_cache[api_key] = out
    _awin_feed_list_ts = now
    logger.info("Awin feed list: %s feeds", len(out))
    return out


def _download_feed_csv(feed_url):
    """Download feed CSV; handle gzip if needed. Returns list of dicts (one per product row)."""
    try:
        r = requests.get(feed_url, timeout=60, stream=True)
        r.raise_for_status()
    except requests.RequestException as e:
        logger.warning("Awin feed download failed: %s", e)
        return []

    raw = r.content
    if r.headers.get("Content-Encoding") == "gzip" or raw[:2] == b"\x1f\x8b":
        try:
            raw = zlib.decompress(raw, 16 + zlib.MAX_WBITS)
        except Exception as e:
            logger.warning("Awin feed gzip decompress failed: %s", e)
            return []

    try:
        text = raw.decode("utf-8", errors="replace")
    except Exception as e:
        logger.warning("Awin feed decode failed: %s", e)
        return []

    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)
    logger.info("Awin feed parsed: %s product rows", len(rows))
    return rows


def _row_to_product(row, interest, query, priority):
    """Map Awin feed row to our product dict."""
    title = (row.get("product_name") or row.get("product name") or "").strip()
    link = (row.get("aw_deep_link") or row.get("merchant_deep_link") or "").strip()
    image = (row.get("merchant_image_url") or row.get("aw_image_url") or row.get("aw_thumb_url") or "").strip()
    price = (row.get("search_price") or row.get("store_price") or "").strip()
    merchant = (row.get("merchant_name") or "").strip()
    if not title:
        return None
    if not link:
        return None
    snippet = f"From {merchant}" if merchant else title[:100]
    source_domain = (
        merchant.lower().replace(" ", "").replace("-", "") + ".com"
        if merchant
        else "awin.com"
    )
    product_id = (row.get("aw_product_id") or row.get("merchant_product_id") or "").strip() or str(hash(title + link))[:16]
    return {
        "title": title[:200],
        "link": link,
        "snippet": snippet,
        "image": image,
        "source_domain": source_domain,
        "search_query": query,
        "interest_match": interest,
        "priority": priority,
        "price": str(price) if price else "",
        "product_id": str(product_id),
    }


def _matches_query(row, query_terms):
    """True if product_name or keywords contain any of the query terms (e.g. hiking, gift)."""
    name = (row.get("product_name") or row.get("product name") or "").lower()
    keywords = (row.get("keywords") or row.get("product_short_description") or "").lower()
    text = name + " " + keywords
    for term in query_terms:
        if term and term.lower() in text:
            return True
    return False


def search_products_awin(profile, data_feed_api_key, target_count=20):
    """
    Search Awin product feeds by profile interests.

    Uses feed list + one feed CSV (cached). Prefers Joined advertisers.
    Returns list of product dicts in our standard format.
    """
    if not (data_feed_api_key and data_feed_api_key.strip()):
        logger.warning("Awin data feed API key not set - skipping Awin search")
        return []

    api_key = data_feed_api_key.strip()
    logger.info("Searching Awin feeds for %s products", target_count)

    interests = profile.get("interests", [])
    if not interests:
        return []

    search_queries = []
    for interest in interests:
        name = interest.get("name", "")
        if not name:
            continue
        if interest.get("is_work", False):
            logger.info("Skipping work interest: %s", name)
            continue
        search_queries.append({
            "query": f"{name} gift",
            "interest": name,
            "priority": "high" if interest.get("intensity") == "passionate" else "medium",
        })
    search_queries = search_queries[:10]
    if not search_queries:
        return []

    feed_list = _get_feed_list(api_key)
    if not feed_list:
        logger.warning("Awin feed list empty or failed")
        return []

    # Prefer Joined; then take first feed we can use
    joined = [f for f in feed_list if (f.get("membership_status") or "").lower() == "joined"]
    to_use = joined[:1] if joined else feed_list[:1]
    feed_url = to_use[0].get("url")
    advertiser = to_use[0].get("advertiser_name", "Awin")

    global _awin_products_ts, _awin_products_cache
    cache_key = api_key + "|" + (to_use[0].get("feed_id") or "")
    now = time.time()
    if now - _awin_products_ts < AWIN_CACHE_TTL and cache_key in _awin_products_cache:
        all_rows = _awin_products_cache[cache_key]
    else:
        all_rows = _download_feed_csv(feed_url)
        if all_rows:
            _awin_products_cache[cache_key] = all_rows
            _awin_products_ts = now

    if not all_rows:
        return []

    all_products = []
    seen_ids = set()
    for q in search_queries:
        query = q["query"]
        interest = q["interest"]
        priority = q["priority"]
        terms = re.split(r"\s+", query)
        for row in all_rows:
            if len(all_products) >= target_count:
                break
            if not _matches_query(row, terms):
                continue
            product = _row_to_product(row, interest, query, priority)
            if not product or product["product_id"] in seen_ids:
                continue
            seen_ids.add(product["product_id"])
            all_products.append(product)
        if len(all_products) >= target_count:
            break

    logger.info("Found %s Awin products from %s", len(all_products), advertiser)
    return all_products[:target_count]
