"""
Tests for the image resolution path — specifically the URL normalization
and inventory-map lookup that replaced the curator image_url path (Change 1).

These functions are defined inside giftwise_app.py's recommendation route,
so we replicate the logic here rather than importing from a 3000+ line file.
This keeps tests fast and independent of Flask.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest


# Replicate the normalize function exactly as it appears in giftwise_app.py
# after Change 1e. If the app function changes, update this copy and add a
# test that verifies they stay in sync.
def _normalize_url_for_image(u):
    if not u or not isinstance(u, str):
        return ''
    u = u.strip().rstrip('/')
    # Strip tracking query params that don't affect the product page
    if '?' in u:
        base, _, qs = u.partition('?')
        # Keep Amazon dp/ URLs clean; strip query from most URLs
        if '/dp/' in base or '/listing/' in base or '/itm/' in base:
            u = base
    return u or ''


# Replicate the inventory map builder
def build_product_url_to_image(products):
    """Build URL -> image map the same way giftwise_app.py does."""
    product_url_to_image = {}
    for p in products:
        raw_link = (p.get('link') or '').strip()
        if raw_link:
            link = _normalize_url_for_image(raw_link)
            if link:
                img = (p.get('image_url') or p.get('image') or p.get('thumbnail') or '').strip()
                product_url_to_image[link] = img
            if raw_link and raw_link not in product_url_to_image:
                product_url_to_image[raw_link] = (p.get('image_url') or p.get('image') or p.get('thumbnail') or '').strip()
    return product_url_to_image


# ---------------------------------------------------------------------------
# URL normalization
# ---------------------------------------------------------------------------

class TestNormalizeUrl:
    def test_strips_whitespace(self):
        assert _normalize_url_for_image("  https://amazon.com/dp/B123  ") == "https://amazon.com/dp/B123"

    def test_strips_trailing_slash(self):
        assert _normalize_url_for_image("https://amazon.com/dp/B123/") == "https://amazon.com/dp/B123"

    def test_strips_query_from_amazon_dp(self):
        url = "https://amazon.com/dp/B0CX23V2ZK?ref=abc&tag=xyz"
        assert _normalize_url_for_image(url) == "https://amazon.com/dp/B0CX23V2ZK"

    def test_strips_query_from_etsy_listing(self):
        url = "https://etsy.com/listing/123456?click_key=abc"
        assert _normalize_url_for_image(url) == "https://etsy.com/listing/123456"

    def test_strips_query_from_ebay_itm(self):
        url = "https://ebay.com/itm/789012?_trkparms=abc"
        assert _normalize_url_for_image(url) == "https://ebay.com/itm/789012"

    def test_preserves_query_for_other_urls(self):
        """Non-product URLs keep their query params (could be meaningful)."""
        url = "https://somestore.com/product?id=12345"
        assert _normalize_url_for_image(url) == "https://somestore.com/product?id=12345"

    def test_empty_string(self):
        assert _normalize_url_for_image("") == ""

    def test_none(self):
        assert _normalize_url_for_image(None) == ""

    def test_non_string(self):
        assert _normalize_url_for_image(12345) == ""


# ---------------------------------------------------------------------------
# Inventory map building + lookup
# ---------------------------------------------------------------------------

class TestInventoryImageMap:
    def test_basic_lookup(self):
        products = [{"link": "https://amazon.com/dp/B123", "image": "https://img.amazon.com/B123.jpg"}]
        img_map = build_product_url_to_image(products)
        assert img_map.get("https://amazon.com/dp/B123") == "https://img.amazon.com/B123.jpg"

    def test_lookup_with_trailing_slash(self):
        products = [{"link": "https://amazon.com/dp/B123/", "image": "https://img.amazon.com/B123.jpg"}]
        img_map = build_product_url_to_image(products)
        # Normalized key strips trailing slash
        assert img_map.get("https://amazon.com/dp/B123") == "https://img.amazon.com/B123.jpg"

    def test_lookup_with_query_params(self):
        """Curator might return URL with query params stripped; map should match."""
        products = [{"link": "https://amazon.com/dp/B123?ref=abc", "image": "https://img.amazon.com/B123.jpg"}]
        img_map = build_product_url_to_image(products)
        # Both raw URL and normalized should be in map
        assert img_map.get("https://amazon.com/dp/B123?ref=abc") == "https://img.amazon.com/B123.jpg"
        assert img_map.get("https://amazon.com/dp/B123") == "https://img.amazon.com/B123.jpg"

    def test_prefers_image_url_over_image(self):
        products = [{"link": "https://x.com/p1", "image_url": "https://best.jpg", "image": "https://ok.jpg", "thumbnail": "https://small.jpg"}]
        img_map = build_product_url_to_image(products)
        assert img_map.get(_normalize_url_for_image("https://x.com/p1")) == "https://best.jpg"

    def test_falls_back_to_image(self):
        products = [{"link": "https://x.com/p1", "image": "https://ok.jpg", "thumbnail": "https://small.jpg"}]
        img_map = build_product_url_to_image(products)
        assert img_map.get(_normalize_url_for_image("https://x.com/p1")) == "https://ok.jpg"

    def test_falls_back_to_thumbnail(self):
        products = [{"link": "https://x.com/p1", "thumbnail": "https://small.jpg"}]
        img_map = build_product_url_to_image(products)
        assert img_map.get(_normalize_url_for_image("https://x.com/p1")) == "https://small.jpg"

    def test_empty_image_returns_empty_string(self):
        products = [{"link": "https://x.com/p1"}]
        img_map = build_product_url_to_image(products)
        assert img_map.get(_normalize_url_for_image("https://x.com/p1")) == ""

    def test_multiple_products(self):
        products = [
            {"link": "https://amazon.com/dp/A1", "image": "https://img/a1.jpg"},
            {"link": "https://etsy.com/listing/E1", "image": "https://img/e1.jpg"},
            {"link": "https://ebay.com/itm/B1", "image": "https://img/b1.jpg"},
        ]
        img_map = build_product_url_to_image(products)
        assert img_map.get("https://amazon.com/dp/A1") == "https://img/a1.jpg"
        assert img_map.get("https://etsy.com/listing/E1") == "https://img/e1.jpg"
        assert img_map.get("https://ebay.com/itm/B1") == "https://img/b1.jpg"

    def test_no_link_skipped(self):
        products = [{"title": "No Link Product", "image": "https://img/x.jpg"}]
        img_map = build_product_url_to_image(products)
        assert len(img_map) == 0
