"""
URL Utilities for GiftWise
Consolidated URL normalization, validation, and parsing functions

This module replaces 4 scattered URL handling implementations:
1. _normalize_url_for_matching (giftwise_app.py line 2855)
2. _normalize_url_for_image (giftwise_app.py line 3383 - nested in _run_generation_thread)
3. URL validation functions (link_validation.py lines 137-208)
4. URL parsing in image_fetcher.py

Author: Chad + Claude
Date: February 16, 2026
"""

from urllib.parse import urlparse, quote
import logging

logger = logging.getLogger('giftwise')


# =============================================================================
# URL NORMALIZATION
# =============================================================================

def normalize_product_url(url):
    """
    Normalize a product URL for consistent matching and caching.

    Use cases:
    - Inventory matching (check if curator-selected URL exists in product pool)
    - Image URL resolution (map product URL to its image)
    - Deduplication (identify when two URLs point to same product)

    Normalization steps:
    1. Strip whitespace
    2. Remove trailing slash
    3. Strip tracking query params (preserve product ID in path like /dp/, /listing/, /itm/)

    Examples:
        >>> normalize_product_url("https://amazon.com/dp/B08N5WRWNW?tag=foo ")
        "https://amazon.com/dp/B08N5WRWNW"

        >>> normalize_product_url("https://etsy.com/listing/12345/?ref=shop_home_active ")
        "https://etsy.com/listing/12345"

        >>> normalize_product_url("https://ebay.com/itm/12345?_trksid=foo")
        "https://ebay.com/itm/12345"

    Args:
        url: Product URL string (may have whitespace, trailing slash, query params)

    Returns:
        str: Normalized URL without tracking params, or empty string if invalid
    """
    if not url or not isinstance(url, str):
        return ''

    url = url.strip().rstrip('/')

    # Strip query params if URL contains a product ID in the path
    # Preserve params for search/category pages (they need ?k= or ?q= to work)
    if '?' in url:
        base, _, query_string = url.partition('?')

        # Known product ID patterns in path (don't need query params)
        if any(pattern in base for pattern in ['/dp/', '/listing/', '/itm/', '/gp/product/']):
            url = base

    return url or ''


def extract_domain(url):
    """
    Extract the domain/netloc from a URL.

    Examples:
        >>> extract_domain("https://www.amazon.com/dp/B08N5WRWNW")
        "www.amazon.com"

        >>> extract_domain("https://etsy.com/listing/12345")
        "etsy.com"

    Args:
        url: Full URL string

    Returns:
        str: Domain (netloc) or empty string if URL is invalid
    """
    if not url or not isinstance(url, str):
        return ''

    try:
        parsed = urlparse(url)
        return parsed.netloc or ''
    except Exception:
        return ''


def extract_base_domain(url):
    """
    Extract the base domain without 'www.' prefix.

    Examples:
        >>> extract_base_domain("https://www.amazon.com/dp/B08N5WRWNW")
        "amazon.com"

        >>> extract_base_domain("https://shop.etsy.com/listing/12345")
        "etsy.com"

    Args:
        url: Full URL string

    Returns:
        str: Base domain without subdomain, or empty string if invalid
    """
    domain = extract_domain(url)
    if not domain:
        return ''

    # Remove 'www.' or 'shop.' prefix
    if domain.startswith('www.'):
        domain = domain[4:]
    elif domain.startswith('shop.'):
        domain = domain[5:]

    return domain


# =============================================================================
# URL VALIDATION
# =============================================================================

def is_search_url(url):
    """
    Check if URL is a search/category results page (not a direct product page).

    Search URLs are NOT valid product links because they show many products,
    not a specific gift recommendation.

    Detection patterns:
    - Path contains '/s', '/search', '/find', '/category', '/browse'
    - Query params like '?k=', '?q=', '?search='
    - Generic category pages

    Examples:
        >>> is_search_url("https://amazon.com/s?k=coffee+mug")
        True

        >>> is_search_url("https://etsy.com/search?q=vintage+poster")
        True

        >>> is_search_url("https://amazon.com/dp/B08N5WRWNW")
        False

    Args:
        url: URL string to check

    Returns:
        bool: True if this is a search/category page, False if it's a product page
    """
    if not url or not isinstance(url, str):
        return True  # Invalid URL = treat as search (don't use it)

    url_lower = url.lower().strip()

    try:
        parsed = urlparse(url_lower)
        path = (parsed.path or '/').strip('/')
        query = (parsed.query or '')
    except Exception:
        return True  # Parse error = treat as search

    # Search query params
    search_params = ['k=', 'q=', 'search=', 'query=', 'keyword=', 's=']
    if any(param in query for param in search_params):
        return True

    # Search paths
    search_paths = ['/s/', '/search', '/find', '/category', '/browse', '/shop/search']
    if any(pattern in path for pattern in search_paths):
        return True

    # Amazon-specific: /s is always search, /dp or /gp/product is always product
    if 'amazon.com' in parsed.netloc:
        if '/s/' in path or path == 's':
            return True
        if '/dp/' in path or '/gp/product/' in path:
            return False

    # Etsy-specific: /search is search, /listing is product
    if 'etsy.com' in parsed.netloc:
        if '/search' in path:
            return True
        if '/listing/' in path:
            return False

    # eBay-specific: /sch is search, /itm is product
    if 'ebay.com' in parsed.netloc:
        if '/sch/' in path:
            return True
        if '/itm/' in path:
            return False

    return False


def is_generic_domain_url(url):
    """
    Check if URL is just a homepage/domain (not a specific product).

    Examples:
        >>> is_generic_domain_url("https://amazon.com")
        True

        >>> is_generic_domain_url("https://amazon.com/")
        True

        >>> is_generic_domain_url("https://amazon.com/dp/B08N5WRWNW")
        False

    Args:
        url: URL string to check

    Returns:
        bool: True if this is a bare domain with no product path
    """
    if not url or not url.startswith(('http://', 'https://')):
        return True

    try:
        parsed = urlparse(url)
        path = (parsed.path or '/').strip('/').lower()

        # No path or just "www" = generic homepage
        if not path or path in ('www', ''):
            return True

        # Has a product-specific path = not generic
        product_patterns = ['/listing/', '/dp/', '/gp/product/', '/itm/']
        if any(pattern in path for pattern in product_patterns):
            return False

        return False
    except Exception:
        return True


def is_valid_product_url(url):
    """
    Check if URL is a valid, specific product page (not search or homepage).

    This is the main validation function. Use this to filter product URLs.

    Examples:
        >>> is_valid_product_url("https://amazon.com/dp/B08N5WRWNW")
        True

        >>> is_valid_product_url("https://amazon.com/s?k=coffee")
        False

        >>> is_valid_product_url("https://etsy.com")
        False

        >>> is_valid_product_url(None)
        False

    Args:
        url: URL string to validate

    Returns:
        bool: True if this is a valid product page URL
    """
    if not url or not isinstance(url, str):
        return False

    # Reject search pages and bare domains
    if is_search_url(url) or is_generic_domain_url(url):
        return False

    return True


def is_bad_product_url(url):
    """
    Inverse of is_valid_product_url (for backward compatibility).

    Returns True if URL should NOT be used as a product link.

    Args:
        url: URL string to check

    Returns:
        bool: True if URL is invalid/bad
    """
    return not is_valid_product_url(url)


# =============================================================================
# URL GENERATION
# =============================================================================

def generate_amazon_search_url(product_name, affiliate_tag=None):
    """
    Generate Amazon search URL as a fallback (LAST RESORT ONLY).

    Use this only when:
    - No direct product link is available
    - Need a "Search Amazon for X" fallback link

    Args:
        product_name: Product name to search for
        affiliate_tag: Optional Amazon affiliate tag (e.g. "giftwise-20")

    Returns:
        str: Amazon search URL with affiliate tag if provided
    """
    url = f"https://www.amazon.com/s?k={quote(product_name)}"
    if affiliate_tag:
        url += f"&tag={affiliate_tag}"
    return url


def generate_google_search_url(query):
    """
    Generate Google search URL (for experience gift fallbacks).

    Args:
        query: Search query string

    Returns:
        str: Google search URL
    """
    return f"https://www.google.com/search?q={quote(query)}"


# =============================================================================
# BACKWARD COMPATIBILITY (Legacy function names)
# =============================================================================

def _normalize_url_for_matching(url):
    """Legacy name. Use normalize_product_url() instead."""
    return normalize_product_url(url)


def _normalize_url_for_image(url):
    """Legacy name. Use normalize_product_url() instead."""
    return normalize_product_url(url)


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    print("URL Utils Test Suite\n" + "=" * 50)

    # Test normalize_product_url
    print("\n1. normalize_product_url()")
    test_urls = [
        "https://amazon.com/dp/B08N5WRWNW?tag=foo ",
        "https://etsy.com/listing/12345/?ref=shop_home_active ",
        "https://ebay.com/itm/12345?_trksid=foo",
        "",
        None,
    ]
    for url in test_urls:
        print(f"  {url!r} → {normalize_product_url(url)!r}")

    # Test is_valid_product_url
    print("\n2. is_valid_product_url()")
    test_urls = [
        ("https://amazon.com/dp/B08N5WRWNW", True),
        ("https://amazon.com/s?k=coffee", False),
        ("https://etsy.com", False),
        ("https://etsy.com/listing/12345", True),
        (None, False),
    ]
    for url, expected in test_urls:
        result = is_valid_product_url(url)
        status = "✓" if result == expected else "✗"
        print(f"  {status} {url!r} → {result}")

    # Test extract_base_domain
    print("\n3. extract_base_domain()")
    test_urls = [
        "https://www.amazon.com/dp/B08N5WRWNW",
        "https://shop.etsy.com/listing/12345",
        "https://ebay.com/itm/12345",
    ]
    for url in test_urls:
        print(f"  {url} → {extract_base_domain(url)}")

    print("\n" + "=" * 50)
    print("All tests complete. Use in giftwise_app.py:")
    print("  from url_utils import normalize_product_url, is_valid_product_url")
