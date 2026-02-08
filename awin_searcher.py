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


def _ci_get(row, *keys):
    """Case-insensitive dict lookup: try each key against actual row keys."""
    # Fast path: try exact match first
    for k in keys:
        v = row.get(k)
        if v:
            return v.strip() if isinstance(v, str) else v
    # Slow path: case-insensitive match
    row_lower = {k.lower().strip(): v for k, v in row.items()}
    for k in keys:
        v = row_lower.get(k.lower().strip())
        if v:
            return v.strip() if isinstance(v, str) else v
    return ""


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

    # Log actual column names on first fetch for debugging
    if rows:
        logger.info("Awin feed list columns: %s", list(rows[0].keys()))
        # Sample membership status values to debug joined=0
        statuses = set()
        for r in rows[:30]:
            for k in r:
                if 'status' in k.lower() or 'member' in k.lower() or 'join' in k.lower():
                    statuses.add(f"{k}={r[k]}")
            # Also check by common Awin column names
            for col in ("Membership Status", "membership_status", "Joined", "Status"):
                v = r.get(col)
                if v:
                    statuses.add(f"{col}={v}")
        if statuses:
            logger.info("Awin feed list status-like values (sample): %s", statuses)

    # Normalize column names (could be with/without spaces); include Vertical and Feed Name for relevance
    out = []
    for row in rows:
        # Case-insensitive column lookup helper
        ci = {k.lower().strip(): v for k, v in row.items()}
        url_val = (ci.get("url") or "").strip()
        feed_id = (ci.get("feed id") or ci.get("feed_id") or "").strip()
        advertiser = (ci.get("advertiser name") or ci.get("advertiser_name") or "").strip()
        # Awin uses various column names for membership: check all known variants
        status = (ci.get("membership status") or ci.get("membership_status")
                  or ci.get("joined") or ci.get("status") or "").strip()
        feed_name = (ci.get("feed name") or ci.get("feed_name") or ci.get("name") or "").strip()
        vertical = (ci.get("vertical") or ci.get("primary region") or "").strip()
        # Also extract number of products and language for smarter feed selection
        num_products = 0
        for np_col in ("no of products", "no_of_products", "number of products", "products"):
            np_val = ci.get(np_col)
            if np_val:
                try:
                    num_products = int(str(np_val).strip().replace(",", ""))
                except (ValueError, TypeError):
                    pass
                break
        language = (ci.get("language") or ci.get("primary region") or "").strip()
        if url_val:
            out.append({
                "url": url_val,
                "feed_id": feed_id,
                "advertiser_name": advertiser,
                "membership_status": status,
                "feed_name": feed_name,
                "vertical": vertical,
                "num_products": num_products,
                "language": language,
            })
    _awin_feed_list_cache[api_key] = out
    _awin_feed_list_ts = now
    # Log breakdown of statuses
    status_counts = {}
    for f in out:
        s = f.get("membership_status", "").lower() or "(empty)"
        status_counts[s] = status_counts.get(s, 0) + 1
    logger.info("Awin feed list: %s feeds, status breakdown: %s", len(out), status_counts)
    return out


# Max rows to read per feed when loading full feed (legacy path)
MAX_ROWS_PER_FEED = 800
# When streaming: max rows to scan per feed before moving to next (finds matches without loading full feed)
MAX_ROWS_TO_SCAN_PER_FEED = 3500


def _stream_feed_and_match(feed_url, search_queries, max_results_from_feed, seen_ids):
    """
    Download a feed CSV (buffered, not raw-stream) and yield rows that match any search query.
    Stops when we have max_results_from_feed matches or after MAX_ROWS_TO_SCAN_PER_FEED rows.

    We buffer the first ~4 MB into memory rather than wrapping the raw socket with TextIOWrapper,
    because many Awin feeds close the socket mid-read ("I/O operation on closed file").
    """
    BUFFER_BYTES = 4 * 1024 * 1024  # 4 MB — enough for ~3500 CSV rows

    try:
        r = requests.get(feed_url, timeout=90, stream=True)
        r.raise_for_status()
    except requests.RequestException as e:
        logger.warning("Awin feed stream failed: %s", e)
        return

    r.raw.decode_content = True  # handle gzip/deflate at the urllib3 level

    # Buffer first BUFFER_BYTES so we aren't at the mercy of the socket staying open
    try:
        chunks = []
        total = 0
        for chunk in r.iter_content(chunk_size=64 * 1024):
            chunks.append(chunk)
            total += len(chunk)
            if total >= BUFFER_BYTES:
                break
        r.close()
        data = b"".join(chunks)
    except Exception as e:
        logger.warning("Awin feed download failed: %s", e)
        try:
            r.close()
        except Exception:
            pass
        return

    if not data:
        return

    count = 0
    scanned = 0
    try:
        text = data.decode("utf-8", errors="replace")
        reader = csv.DictReader(io.StringIO(text, newline=""))
        for row in reader:
            scanned += 1
            # Log column names from first row for debugging
            if scanned == 1:
                logger.info("Awin feed CSV columns: %s", list(row.keys())[:20])
                # Log a sample product to see what data we're working with
                sample_title = _ci_get(row, "product_name", "title", "product_title", "name")
                sample_link = _ci_get(row, "aw_deep_link", "merchant_deep_link", "deep_link", "link", "aw_product_url")
                logger.info("Awin feed sample row: title=%s link=%s",
                            (sample_title or "(none)")[:60], (sample_link or "(none)")[:60])
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
        logger.warning("Awin feed parse failed (buffered): %s", e)
    if scanned > 0:
        logger.info("Awin buffered: scanned %s rows, matched %s from %s", scanned, count, feed_url[:80])


def _fetch_feed_nonstream(feed_url, search_queries, max_results_from_feed, seen_ids):
    """
    Fallback: fetch feed with requests.get (no stream), parse CSV from r.text.
    Use when streaming fails with 'I/O operation on closed file' (e.g. gzip/connection issues).
    """
    try:
        r = requests.get(feed_url, timeout=90)
        r.raise_for_status()
    except requests.RequestException as e:
        logger.warning("Awin feed non-stream fetch failed: %s", e)
        return
    count = 0
    scanned = 0
    try:
        reader = csv.DictReader(io.StringIO(r.text, newline=""))
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
        logger.warning("Awin feed non-stream parse failed: %s", e)
    if scanned > 0:
        logger.debug("Awin non-stream: scanned %s rows, matched %s", scanned, count)


def _stream_feed_first_n(feed_url, n, seen_ids):
    """Yield first n valid products from feed (no query match). Used when matching returns 0."""
    BUFFER_BYTES = 1 * 1024 * 1024  # 1 MB — only need a few rows

    try:
        r = requests.get(feed_url, timeout=90, stream=True)
        r.raise_for_status()
    except requests.RequestException as e:
        logger.warning("Awin feed stream failed: %s", e)
        return
    r.raw.decode_content = True

    try:
        chunks = []
        total = 0
        for chunk in r.iter_content(chunk_size=64 * 1024):
            chunks.append(chunk)
            total += len(chunk)
            if total >= BUFFER_BYTES:
                break
        r.close()
        data = b"".join(chunks)
    except Exception as e:
        logger.warning("Awin feed download failed (first_n): %s", e)
        try:
            r.close()
        except Exception:
            pass
        return

    if not data:
        return

    count = 0
    try:
        text = data.decode("utf-8", errors="replace")
        reader = csv.DictReader(io.StringIO(text, newline=""))
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
        logger.warning("Awin feed parse failed (first_n): %s", e)


def _download_feed_csv(feed_url):
    """Download feed CSV; buffer first 4 MB and cap at MAX_ROWS_PER_FEED to avoid OOM on large feeds."""
    BUFFER_BYTES = 4 * 1024 * 1024

    try:
        r = requests.get(feed_url, timeout=60, stream=True)
        r.raise_for_status()
    except requests.RequestException as e:
        logger.warning("Awin feed download failed: %s", e)
        return []
    r.raw.decode_content = True

    try:
        chunks = []
        total = 0
        for chunk in r.iter_content(chunk_size=64 * 1024):
            chunks.append(chunk)
            total += len(chunk)
            if total >= BUFFER_BYTES:
                break
        r.close()
        data = b"".join(chunks)
    except Exception as e:
        logger.warning("Awin feed download read failed: %s", e)
        try:
            r.close()
        except Exception:
            pass
        return []

    rows = []
    try:
        text = data.decode("utf-8", errors="replace")
        reader = csv.DictReader(io.StringIO(text, newline=""))
        for i, row in enumerate(reader):
            if i >= MAX_ROWS_PER_FEED:
                break
            rows.append(row)
    except Exception as e:
        logger.warning("Awin feed parse failed: %s", e)
        return []
    logger.info("Awin feed parsed: %s product rows (max %s per feed)", len(rows), MAX_ROWS_PER_FEED)
    return rows


def _row_to_product(row, interest, query, priority):
    """Map Awin feed row to our product dict. Case-insensitive column lookup for robustness."""
    title = _ci_get(row, "product_name", "product name", "title", "product_title", "name",
                    "Product Name", "Title")
    link = _ci_get(row, "aw_deep_link", "merchant_deep_link", "deep_link", "link",
                   "aw_product_url", "product_url", "URL", "Merchant Deep Link")
    image = _ci_get(row, "merchant_image_url", "aw_image_url", "aw_thumb_url",
                    "image_url", "merchant_thumb", "product_image", "thumb_url",
                    "image_link", "thumbnail_url", "Image URL", "Merchant Image URL")
    price = _ci_get(row, "search_price", "store_price", "price", "Price",
                    "rrp_price", "display_price")
    merchant = _ci_get(row, "merchant_name", "Merchant Name", "brand_name", "brand",
                       "advertiser_name")
    if not title:
        return None
    if not link:
        return None
    description = _ci_get(row, "product_short_description", "description", "Description",
                          "product_description", "Product Description")
    snippet = description[:150] if description else (f"From {merchant}" if merchant else title[:120])
    source_domain = (
        merchant.lower().replace(" ", "").replace("-", "") + ".com"
        if merchant
        else "awin.com"
    )
    product_id = _ci_get(row, "aw_product_id", "merchant_product_id", "product_id",
                         "Product ID") or str(hash(title + link))[:16]
    return {
        "title": title[:200],
        "link": link,
        "snippet": snippet,
        "image": image,
        "thumbnail": image,
        "image_url": image,
        "source_domain": source_domain,
        "search_query": query,
        "interest_match": interest,
        "priority": priority,
        "price": str(price) if price else "",
        "product_id": str(product_id),
    }


def _product_text(row):
    """All searchable text from a feed row; case-insensitive column lookup."""
    name = (_ci_get(row, "product_name", "product name", "Product Name", "Name",
                    "Title", "title", "product_title") or "").lower()
    keywords = (_ci_get(row, "keywords", "product_short_description", "description",
                        "Description", "product_description", "category_name",
                        "merchant_category") or "").lower()
    brand = (_ci_get(row, "brand_name", "brand", "merchant_name") or "").lower()
    return name + " " + keywords + " " + brand


def _matches_query(row, query_terms):
    """True if product text contains the primary interest term (not just generic words like 'gift')."""
    text = _product_text(row)
    generic_terms = {"and", "the", "or", "with", "from", "gift", "present", "idea", "unique", "personalized", "accessories", "lover", "fan"}
    meaningful_matches = 0
    for term in query_terms:
        t = (term or "").strip().lower()
        if len(t) <= 1 or t in generic_terms:
            continue
        if t in text:
            meaningful_matches += 1
    return meaningful_matches >= 1


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

    # Prefer Joined/active feeds; accept multiple status values
    _active_statuses = {"joined", "active", "approved", "yes", "1", "true"}
    _niche_keywords = ("bunch", "flower", "florist", "roses", "bouquet", "tooled up", "tools")

    def _is_niche_retailer(advertiser_name):
        name = (advertiser_name or "").lower()
        return any(k in name for k in _niche_keywords)

    joined = [f for f in feed_list if (f.get("membership_status") or "").lower() in _active_statuses]
    logger.info("Awin joined/active feeds: %d (out of %d total)", len(joined), len(feed_list))
    candidates = joined if joined else feed_list

    # Prefer English-language feeds and gift-relevant verticals
    _gift_verticals = {"retail", "gifts", "home & garden", "sports & outdoors", "clothing & accessories",
                       "food & drink", "health & beauty", "entertainment", "travel", "toys & games",
                       "arts & crafts", "books", "music", "pets", "jewelry"}

    # Score each feed for selection (higher = better)
    interest_keywords = set()
    for q in search_queries:
        pt = q.get("primary_term")
        if pt:
            interest_keywords.add(pt)
        for w in re.split(r"\s+", (q.get("interest") or "")):
            if len(w) > 2:
                interest_keywords.add(w.lower())

    def _feed_score(feed_info):
        score = 0
        text = " ".join([
            (feed_info.get("vertical") or "").lower(),
            (feed_info.get("feed_name") or "").lower(),
            (feed_info.get("advertiser_name") or "").lower(),
        ])
        # Interest keyword matches
        score += sum(2 for k in interest_keywords if k in text)
        # Gift-relevant vertical bonus
        vertical_lower = (feed_info.get("vertical") or "").lower()
        if any(v in vertical_lower for v in _gift_verticals):
            score += 5
        # Larger catalogs are more likely to have matches
        num_products = feed_info.get("num_products", 0)
        if num_products > 10000:
            score += 3
        elif num_products > 1000:
            score += 2
        elif num_products > 100:
            score += 1
        # English preference
        lang = (feed_info.get("language") or "").lower()
        if "en" in lang or "english" in lang or not lang:
            score += 1
        # Penalize niche single-category retailers
        if _is_niche_retailer(feed_info.get("advertiser_name", "")):
            score -= 5
        return score

    scored_feeds = sorted(candidates, key=lambda f: -_feed_score(f))

    # Deduplicate by advertiser name — only keep the best feed per advertiser
    seen_advertisers = set()
    ordered_feeds = []
    for f in scored_feeds:
        adv = (f.get("advertiser_name") or "").lower().strip()
        if adv in seen_advertisers:
            continue
        seen_advertisers.add(adv)
        ordered_feeds.append(f)

    # Log top selections for debugging
    for i, f in enumerate(ordered_feeds[:10]):
        logger.info("Awin feed rank %d: %s (%s) score=%d products=%s",
                     i + 1, f.get("advertiser_name", "?"), f.get("vertical", "?"),
                     _feed_score(f), f.get("num_products", "?"))

    # Stream-and-match: search top feeds, scan up to MAX_ROWS_TO_SCAN_PER_FEED per feed
    max_feeds = 12
    per_feed_target = max((target_count + max_feeds - 1) // max_feeds, 3)
    all_products = []
    seen_ids = set()
    feeds_used = []

    logger.info("Awin searching %d feeds (joined=%d, total=%d)", min(max_feeds, len(ordered_feeds)), len(joined), len(feed_list))
    for idx, feed_info in enumerate(ordered_feeds[:max_feeds]):
        if len(all_products) >= target_count:
            break
        feed_url = feed_info.get("url")
        advertiser = feed_info.get("advertiser_name", "Awin")
        logger.info("Awin feed %d/%d: %s (%s)", idx + 1, min(max_feeds, len(ordered_feeds)), advertiser, feed_info.get("vertical", "?"))
        need = min(per_feed_target, target_count - len(all_products))
        feed_count = 0
        for product in _stream_feed_and_match(feed_url, search_queries, need, seen_ids):
            all_products.append(product)
            feed_count += 1
            if len(all_products) >= target_count:
                break
        if feed_count == 0:
            for product in _fetch_feed_nonstream(feed_url, search_queries, need, seen_ids):
                all_products.append(product)
                feed_count += 1
                if len(all_products) >= target_count:
                    break
            if feed_count > 0:
                logger.info("Awin used non-stream fallback for %s", advertiser)
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