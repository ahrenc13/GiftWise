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


# Max rows to read per feed to avoid OOM on Railway (feeds can be 100k+ rows)
MAX_ROWS_PER_FEED = 800


def _download_feed_csv(feed_url):
    """Download feed CSV; stream-read and cap at MAX_ROWS_PER_FEED to avoid OOM on large feeds."""
    try:
        r = requests.get(feed_url, timeout=60, stream=True)
        r.raise_for_status()
    except requests.RequestException as e:
        logger.warning("Awin feed download failed: %s", e)
        return []

    rows = []
    try:
        # r.raw streams decompressed bytes; we only read until we have MAX_ROWS_PER_FEED rows
        text_stream = io.TextIOWrapper(r.raw, encoding="utf-8", errors="replace")
        reader = csv.DictReader(text_stream)
        for i, row in enumerate(reader):
            if i >= MAX_ROWS_PER_FEED:
                break
            rows.append(row)
    except Exception as e:
        logger.warning("Awin feed parse failed: %s", e)
        return []
    finally:
        try:
            r.close()
        except Exception:
            pass
    logger.info("Awin feed parsed: %s product rows (max %s per feed)", len(rows), MAX_ROWS_PER_FEED)
    return rows


def _row_to_product(row, interest, query, priority):
    """Map Awin feed row to our product dict. Supports multiple Awin feed column naming conventions."""
    title = (row.get("product_name") or row.get("product name") or "").strip()
    link = (row.get("aw_deep_link") or row.get("merchant_deep_link") or row.get("deep_link") or "").strip()
    # Awin feeds use various image column names; check all common variants for thumbnails
    image = (
        (row.get("merchant_image_url") or row.get("aw_image_url") or row.get("aw_thumb_url")
         or row.get("image_url") or row.get("merchant_thumb") or row.get("product_image")
         or row.get("thumb_url") or row.get("image_link") or row.get("thumbnail_url"))
        or ""
    ).strip()
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


def _product_text(row):
    """All searchable text from a feed row; supports multiple column naming conventions."""
    name = (
        row.get("product_name") or row.get("product name") or row.get("Product Name")
        or row.get("Name") or row.get("Title") or row.get("product_title") or ""
    ).strip().lower()
    keywords = (
        row.get("keywords") or row.get("product_short_description") or row.get("description")
        or row.get("Description") or row.get("product_description") or ""
    ).strip().lower()
    return name + " " + keywords


def _matches_query(row, query_terms):
    """True if product name/keywords/description contain any of the query terms (skip stopwords)."""
    text = _product_text(row)
    stopwords = {"and", "the", "or", "with", "from"}  # allow "gift" and "for" to match
    for term in query_terms:
        t = (term or "").strip().lower()
        if len(t) <= 1 or t in stopwords:
            continue
        if t in text:
            return True
    return False


def search_products_awin(profile, data_feed_api_key, target_count=20, enhanced_search_terms=None):
    """
    Search Awin product feeds by profile interests and intelligence-layer search terms.

    Uses feed list + multiple feed CSVs (cached) for full breadth. Prefers Joined advertisers.
    If enhanced_search_terms (from enrichment) are provided, also matches products against those.
    Returns list of product dicts in our standard format.
    """
    if not (data_feed_api_key and data_feed_api_key.strip()):
        logger.warning("Awin data feed API key not set - skipping Awin search")
        return []

    api_key = data_feed_api_key.strip()
    logger.info("Searching Awin feeds for %s products (full breadth)", target_count)

    interests = profile.get("interests", [])
    enhanced = list(enhanced_search_terms or [])
    if not interests and not enhanced:
        return []

    # Build search queries from profile interests (skip work); include primary term for relaxed matching
    search_queries = []
    for interest in interests:
        name = interest.get("name", "")
        if not name:
            continue
        if interest.get("is_work", False):
            logger.info("Skipping work interest: %s", name)
            continue
        # Primary term = first significant word (e.g. "dog" from "Dog ownership and care") for broader Awin matching
        words = [w for w in re.split(r"\s+", name) if len(w) > 1 and w.lower() not in ("and", "the", "or", "for")]
        primary = words[0].lower() if words else name.lower()[:20]
        search_queries.append({
            "query": f"{name} gift",
            "interest": name,
            "primary_term": primary,
            "priority": "high" if interest.get("intensity") == "passionate" else "medium",
        })
    # Add intelligence-layer enhanced search terms as extra queries (broaden match)
    for term in enhanced[:15]:
        if term and isinstance(term, str) and term.strip() and term.strip() not in {q["query"] for q in search_queries}:
            search_queries.append({
                "query": f"{term.strip()} gift",
                "interest": term.strip(),
                "priority": "medium",
            })
    search_queries = search_queries[:20]
    if not search_queries:
        return []

    feed_list = _get_feed_list(api_key)
    if not feed_list:
        logger.warning("Awin feed list empty or failed")
        return []

    # Prefer Joined; deprioritize single-category retailers (e.g. florists) for diversity
    _florist_keywords = ("bunch", "flower", "florist", "roses", "bouquet")
    def _is_likely_florist(advertiser_name):
        name = (advertiser_name or "").lower()
        return any(k in name for k in _florist_keywords)

    joined = [f for f in feed_list if (f.get("membership_status") or "").lower() == "joined"]
    candidates = joined if joined else feed_list
    general = [f for f in candidates if not _is_likely_florist(f.get("advertiser_name", ""))]
    florists = [f for f in candidates if _is_likely_florist(f.get("advertiser_name", ""))]
    ordered_feeds = general + florists
    # Use up to 3 feeds to balance breadth vs memory (Railway OOM if too many large feeds cached)
    max_feeds = 3
    per_feed_target = max((target_count + max_feeds - 1) // max_feeds, 2)

    global _awin_products_ts, _awin_products_cache
    now = time.time()
    all_products = []
    seen_ids = set()
    feeds_used = []

    for feed_info in ordered_feeds[:max_feeds]:
        if len(all_products) >= target_count:
            break
        feed_url = feed_info.get("url")
        feed_id = feed_info.get("feed_id") or ""
        advertiser = feed_info.get("advertiser_name", "Awin")
        cache_key = api_key + "|" + feed_id
        if now - _awin_products_ts < AWIN_CACHE_TTL and cache_key in _awin_products_cache:
            all_rows = _awin_products_cache[cache_key]
        else:
            all_rows = _download_feed_csv(feed_url)
            if all_rows:
                _awin_products_cache[cache_key] = all_rows
                _awin_products_ts = now
        if not all_rows:
            continue

        feed_count = 0
        for q in search_queries:
            if feed_count >= per_feed_target:
                break
            query = q["query"]
            interest = q["interest"]
            priority = q["priority"]
            terms = list(re.split(r"\s+", query))
            if q.get("primary_term") and q["primary_term"] not in (t.lower() for t in terms):
                terms.append(q["primary_term"])
            for row in all_rows:
                if feed_count >= per_feed_target or len(all_products) >= target_count:
                    break
                if not _matches_query(row, terms):
                    continue
                product = _row_to_product(row, interest, query, priority)
                if not product or product["product_id"] in seen_ids:
                    continue
                seen_ids.add(product["product_id"])
                all_products.append(product)
                feed_count += 1
        if feed_count > 0:
            feeds_used.append(advertiser)
        # Fallback: if this feed had no interest matches, take first few products for diversity
        elif len(all_products) < target_count:
            for row in all_rows[:5]:
                if len(all_products) >= target_count:
                    break
                product = _row_to_product(row, "general", "gift", "medium")
                if product and product["product_id"] not in seen_ids:
                    seen_ids.add(product["product_id"])
                    all_products.append(product)
                    feed_count += 1
            if feed_count > 0:
                feeds_used.append(advertiser)

    logger.info("Found %s Awin products from %s", len(all_products), ", ".join(feeds_used) or "Awin")
    return all_products[:target_count]
