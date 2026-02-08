"""
Skimlinks product search via Product Key API.

Skimlinks aggregates 48,500+ merchants across 50+ affiliate networks (Awin, CJ,
Rakuten, Impact, etc.) with a single publisher account. Products are returned with
pre-affiliated URLs — no per-merchant joining required.

APIs used:
1. Authentication: POST https://authentication.skimapis.com/access_token
2. Product Search: GET https://products.skimapis.com/v2/publisher/{pub_id}/product
   (searches by keywords across all merchants)
3. Link Wrapper: https://go.skimresources.com/?id={pub_id}&url={merchant_url}
   (wraps any merchant URL with affiliate tracking, no API call needed)

Env vars:
  SKIMLINKS_PUBLISHER_ID     — your publisher ID (from Skimlinks dashboard)
  SKIMLINKS_CLIENT_ID        — API client ID (request from account manager)
  SKIMLINKS_CLIENT_SECRET    — API client secret
  SKIMLINKS_PUBLISHER_DOMAIN_ID — your domain ID (from Skimlinks dashboard)
"""

import logging
import re
import time
import requests
from urllib.parse import quote

logger = logging.getLogger(__name__)

# Token cache
_access_token = None
_token_expires = 0
_TOKEN_BUFFER = 300  # refresh 5 min before expiry


def _get_access_token(client_id, client_secret):
    """Get or refresh Skimlinks access token (client credentials grant)."""
    global _access_token, _token_expires
    now = time.time()
    if _access_token and now < _token_expires - _TOKEN_BUFFER:
        return _access_token

    try:
        r = requests.post(
            "https://authentication.skimapis.com/access_token",
            json={
                "client_id": client_id,
                "client_secret": client_secret,
                "grant_type": "client_credentials",
            },
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
        _access_token = data.get("access_token")
        _token_expires = data.get("expiry_timestamp", now + 3600)
        logger.info("Skimlinks access token obtained, expires in %d s",
                     int(_token_expires - now))
        return _access_token
    except requests.RequestException as e:
        logger.error("Skimlinks auth failed: %s", e)
        return None


def _search_products(publisher_id, domain_id, access_token, query,
                     country="us", max_results=10):
    """
    Search Skimlinks product catalog by keywords.

    Uses the Product Key API v2 endpoint which returns products with
    pre-affiliated URLs across all Skimlinks merchants.
    """
    url = f"https://products.skimapis.com/v2/publisher/{publisher_id}/product"
    params = {
        "access_token": access_token,
        "publisher_domain_id": domain_id,
        "product_keywords": query,
        "country_code": country,
        "alternatives_size": max_results,
        "per_merchant_limit": 3,  # diversity: max 3 per merchant
        "sort_by": "epc",  # sort by earnings-per-click for best revenue
        "sort_desc": "desc",
    }

    try:
        r = requests.get(url, params=params, timeout=20)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        logger.warning("Skimlinks product search failed for '%s': %s", query[:40], e)
        return None


def _extract_domain(url):
    """Extract clean domain from URL."""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        # Strip www.
        if domain.startswith("www."):
            domain = domain[4:]
        return domain
    except Exception:
        return "skimlinks.com"


def _parse_product(product_data, interest, query, priority):
    """Convert Skimlinks product response into our standard product dict."""
    # Product details can be in product_details or at top level
    details = product_data.get("product_details", product_data)

    title = (details.get("product_name") or "").strip()
    if not title:
        return None

    # URLs — prefer affiliated URL, fall back to product URL
    urls = details.get("urls", {})
    link = urls.get("affiliated_url") or urls.get("product_url") or ""
    if not link:
        return None

    # Images
    images = details.get("product_images", [])
    image_url = ""
    if images:
        image_url = images[0].get("value", "") if isinstance(images[0], dict) else str(images[0])

    # Price
    price = details.get("price") or details.get("latest_price") or ""
    currency = details.get("currency", "USD")
    price_str = f"{currency} {price}" if price else ""

    # Merchant
    merchant = details.get("merchant_name", "")
    source_domain = _extract_domain(urls.get("product_url", "")) or (
        merchant.lower().replace(" ", "") + ".com" if merchant else "skimlinks.com"
    )

    # Description / snippet
    description = (details.get("description") or "").strip()
    snippet = description[:150] if description else (f"From {merchant}" if merchant else title[:120])

    # Product ID
    product_id = str(details.get("sku") or details.get("upc") or details.get("product_id")
                      or hash(title + link))

    return {
        "title": title[:200],
        "link": link,
        "snippet": snippet,
        "image": image_url,
        "thumbnail": image_url,
        "image_url": image_url,
        "source_domain": source_domain,
        "search_query": query,
        "interest_match": interest,
        "priority": priority,
        "price": price_str,
        "product_id": product_id,
    }


def wrap_affiliate_link(url, publisher_id):
    """
    Wrap any merchant URL with Skimlinks affiliate tracking.

    This is a URL-based redirect — no API call needed.
    Use this for experience material links, curator-provided URLs, etc.
    """
    if not url or not publisher_id:
        return url
    # Don't double-wrap
    if "skimresources.com" in url or "redirectingat.com" in url:
        return url
    encoded = quote(url, safe="")
    return f"https://go.skimresources.com/?id={publisher_id}&url={encoded}"


def search_products_skimlinks(profile, publisher_id, client_id, client_secret,
                               domain_id, target_count=20, enhanced_search_terms=None):
    """
    Search Skimlinks product catalog by profile interests.

    Returns list of product dicts in our standard format.
    Products come with pre-affiliated URLs (no per-merchant setup needed).
    """
    if not all([publisher_id, client_id, client_secret, domain_id]):
        logger.warning("Skimlinks credentials not fully configured - skipping")
        return []

    logger.info("Searching Skimlinks for %d products", target_count)

    access_token = _get_access_token(client_id, client_secret)
    if not access_token:
        return []

    # Build search queries from profile interests (skip work)
    interests = profile.get("interests", [])
    enhanced = list(enhanced_search_terms or [])

    search_queries = []
    for interest in interests:
        name = interest.get("name", "")
        if not name or interest.get("is_work", False):
            continue
        search_queries.append({
            "query": f"{name} gift",
            "interest": name,
            "priority": "high" if interest.get("intensity") == "passionate" else "medium",
        })

    # Add enhanced search terms from enrichment layer
    seen = {q["query"] for q in search_queries}
    for term in enhanced[:10]:
        if term and isinstance(term, str) and term.strip() not in seen:
            search_queries.append({
                "query": term.strip(),
                "interest": term.strip(),
                "priority": "medium",
            })
            seen.add(term.strip())

    search_queries = search_queries[:15]
    if not search_queries:
        return []

    # Run searches and collect products
    all_products = []
    seen_ids = set()
    per_query = max(3, (target_count + len(search_queries) - 1) // len(search_queries))

    for q_info in search_queries:
        if len(all_products) >= target_count:
            break

        result = _search_products(
            publisher_id, domain_id, access_token,
            q_info["query"], country="us", max_results=per_query,
        )
        if not result:
            continue

        # Parse alternatives (the main product search results)
        alternatives = result.get("product_alternatives", [])
        # Also check top-level product_details
        main_product = result.get("product_details")
        if main_product:
            alternatives = [{"product_details": main_product}] + alternatives

        for alt in alternatives:
            if len(all_products) >= target_count:
                break
            product = _parse_product(alt, q_info["interest"], q_info["query"], q_info["priority"])
            if not product or product["product_id"] in seen_ids:
                continue
            seen_ids.add(product["product_id"])
            all_products.append(product)

    logger.info("Found %d Skimlinks products", len(all_products))
    return all_products[:target_count]
