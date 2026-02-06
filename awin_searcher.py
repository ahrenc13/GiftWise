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
    # Normalize column names (could be with/without spaces); include Vertical and Feed Name for relevance
    out = []
    for row in rows:
        url_val = (row.get("URL") or row.get("url") or "").strip()
        feed_id = (row.get("Feed ID") or row.get("Feed Id") or row.get("feed_id") or "").strip()
        advertiser = (row.get("Advertiser Name") or row.get("advertiser_name") or "").strip()
        status = (row.get("Membership Status") or row.get("membership_status") or "").strip()
        feed_name = (row.get("Feed Name") or row.get("feed_name") or "").strip()
        vertical = (row.get("Vertical") or row.get("vertical") or "").strip()
        if url_val:
            out.append({
                "url": url_val,
                "feed_id": feed_id,
                "advertiser_name": advertiser,
                "membership_status": status,
                "feed_name": feed_name,
                "vertical": vertical,
            })
    _awin_feed_list_cache[api_key] = out
    _awin_feed_list_ts = now
    logger.info("Awin feed list: %s feeds", len(out))
    return out


# Max rows to read per feed when loading full feed (legacy path)
MAX_ROWS_PER_FEED = 800
# When streaming: max rows to scan per feed before moving to next (finds matches without loading full feed)
MAX_ROWS_TO_SCAN_PER_FEED = 3500


def _stream_feed_and_match(feed_url, search_queries, max_results_from_feed, seen_ids):
    """
    Stream a feed CSV and yield only rows that match any search query (terms or primary_term).
    Stops when we have max_results_from_feed matches or after MAX_ROWS_TO_SCAN_PER_FEED rows.
    Keeps memory small so we can afford to open many feeds.
    """
    try:
        r = requests.get(feed_url, timeout=90, stream=True)
        r.raise_for_status()
    except requests.RequestException as e:
        logger.warning("Awin feed stream failed: %s", e)
        return

    count = 0
    scanned = 0
    try:
        text_stream = io.TextIOWrapper(r.raw, encoding="utf-8", errors="replace")
        reader = csv.DictReader(text_stream)
        for row in reader:
            scanned += 1
            if count >= max_results_from_feed or scanned > MAX_ROWS_TO_SCAN_PER_FEED:
                break
            for q in search_queries:
                if count >= max_results_from_feed:
                    break
                terms = list(re.split(r"\s+", q["query"]))
                if q.get("primary_term") and q["primary_term"] not in (t.lower() for t in terms):
                    terms.append(q["primary_term"])
                if not _matches_query(row, terms):
                    continue
                product = _row_to_product(
                    row,
                    q.get("interest", "general"),
                    q.get("query", "gift"),
                    q.get("priority", "medium"),
                )
                if not product or product["product_id"] in seen_ids:
                    continue
                seen_ids.add(product["product_id"])
                count += 1
                yield product
                break
    except Exception as e:
        logger.warning("Awin feed stream parse failed: %s", e)
    finally:
        try:
            r.close()
        except Exception:
            pass
    if scanned > 0:
        logger.debug("Awin stream: scanned %s rows, matched %s", scanned, count)


def _stream_feed_first_n(feed_url, n, seen_ids):
    """Yield first n valid products from feed (no query match). Used when matching returns 0."""
    try:
        r = requests.get(feed_url, timeout=90, stream=True)
        r.raise_for_status()
    except requests.RequestException as e:
        logger.warning("Awin feed stream failed: %s", e)
        return
    count = 0
    try:
        text_stream = io.TextIOWrapper(r.raw, encoding="utf-8", errors="replace")
        reader = csv.DictReader(text_stream)
        for row in reader:
            if count >= n:
                break
            product = _row_to_product(row, "general", "gift", "medium")
            if not product or product["product_id"] in seen_ids:
                continue
            seen_ids.add(product["product_id"])
            count += 1
            yield product
    except Exception as e:
        logger.warning("Awin feed stream parse failed: %s", e)
    finally:
        try:
            r.close()
        except Exception:
            pass


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
    title = (row.get("product_name") or row.get("product name") or row.get("title") or row.get("product_title") or "").strip()
    link = (row.get("aw_deep_link") or row.get("merchant_deep_link") or row.get("deep_link") or row.get("link") or "").strip()
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
        or row.get("Name") or row.get("Title") or row.get("title") or row.get("product_title") or ""
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
            t = term.strip()
            words = [w for w in re.split(r"\s+", t) if len(w) > 1 and w.lower() not in ("and", "the", "or", "for")]
            primary = words[0].lower() if words else t.lower()[:20]
            search_queries.append({
                "query": f"{t} gift",
                "interest": t,
                "primary_term": primary,
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

    # Relevance: prefer feeds whose vertical, feed_name, or advertiser_name mention any interest
    interest_keywords = set()
    for q in search_queries:
        pt = q.get("primary_term")
        if pt:
            interest_keywords.add(pt)
        for w in re.split(r"\s+", (q.get("interest") or "")):
            if len(w) > 2:
                interest_keywords.add(w.lower())
    def _feed_relevance(feed_info):
        text = " ".join([
            (feed_info.get("vertical") or "").lower(),
            (feed_info.get("feed_name") or "").lower(),
            (feed_info.get("advertiser_name") or "").lower(),
        ])
        return sum(1 for k in interest_keywords if k in text)
    ordered_feeds = sorted(ordered_feeds, key=lambda f: -_feed_relevance(f))

    # Stream-and-match: use more feeds (8), scan up to MAX_ROWS_TO_SCAN_PER_FEED per feed, only keep matches
    max_feeds = 8
    per_feed_target = max((target_count + max_feeds - 1) // max_feeds, 3)
    all_products = []
    seen_ids = set()
    feeds_used = []

    for feed_info in ordered_feeds[:max_feeds]:
        if len(all_products) >= target_count:
            break
        feed_url = feed_info.get("url")
        advertiser = feed_info.get("advertiser_name", "Awin")
        need = min(per_feed_target, target_count - len(all_products))
        feed_count = 0
        for product in _stream_feed_and_match(feed_url, search_queries, need, seen_ids):
            all_products.append(product)
            feed_count += 1
            if len(all_products) >= target_count:
                break
        if feed_count > 0:
            feeds_used.append(advertiser)

    # Fallback: if no matches from any feed, take first few products from first feed for diversity
    if not all_products and ordered_feeds:
        first_feed = ordered_feeds[0]
        for product in _stream_feed_first_n(first_feed.get("url"), 5, seen_ids):
            all_products.append(product)
        if all_products:
            feeds_used.append(first_feed.get("advertiser_name", "Awin"))
            logger.info("Awin fallback: took first %s products from %s", len(all_products), first_feed.get("advertiser_name"))

    logger.info("Found %s Awin products from %s", len(all_products), ", ".join(feeds_used) or "Awin")
    return all_products[:target_count]
