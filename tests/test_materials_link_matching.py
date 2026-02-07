"""
Tests for experience link validation and materials_needed URL resolver.

Verifies:
- Curator URLs validated against inventory (with normalization)
- Fuzzy word-overlap matching scores candidates and picks best
- Minimum overlap requirements prevent false matches
- Multi-retailer search fallback (not just Amazon)
- Stopwords excluded from matching
- Non-purchasable items skip inventory matching
- Experience reservation/venue URL validation
- Smart search link generation for experiences
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import patch, MagicMock
from giftwise_app import (
    _backfill_materials_links,
    _normalize_url_for_matching,
    _validate_experience_url,
    _make_experience_search_link,
)


# Helper: never reject any URL
def _no_bad_urls(url):
    return False


# Helper: reject search URLs
def _reject_search_urls(url):
    return '/s?' in url or '/search' in url


# ---------------------------------------------------------------------------
# URL normalization for matching
# ---------------------------------------------------------------------------

class TestNormalizeUrlForMatching:
    def test_strips_whitespace_and_trailing_slash(self):
        assert _normalize_url_for_matching("  https://amazon.com/dp/B123/  ") == "https://amazon.com/dp/B123"

    def test_strips_query_from_amazon_dp(self):
        assert _normalize_url_for_matching("https://amazon.com/dp/B123?ref=abc") == "https://amazon.com/dp/B123"

    def test_strips_query_from_etsy_listing(self):
        assert _normalize_url_for_matching("https://etsy.com/listing/123?click=x") == "https://etsy.com/listing/123"

    def test_strips_query_from_ebay_itm(self):
        assert _normalize_url_for_matching("https://ebay.com/itm/456?_trk=x") == "https://ebay.com/itm/456"

    def test_preserves_query_for_other_urls(self):
        assert _normalize_url_for_matching("https://shop.com/product?id=7") == "https://shop.com/product?id=7"

    def test_empty_and_none(self):
        assert _normalize_url_for_matching("") == ""
        assert _normalize_url_for_matching(None) == ""


# ---------------------------------------------------------------------------
# Inventory URL validation (curator-provided URLs)
# ---------------------------------------------------------------------------

class TestInventoryUrlValidation:
    def test_exact_match_keeps_url(self):
        products = [{"link": "https://amazon.com/dp/B123", "title": "Widget"}]
        materials = [{"item": "Widget", "product_url": "https://amazon.com/dp/B123"}]
        result = _backfill_materials_links(materials, products, _no_bad_urls)
        assert result[0]["product_url"] == "https://amazon.com/dp/B123"

    def test_normalized_match_keeps_url(self):
        """URL with trailing slash or query params should still match inventory."""
        products = [{"link": "https://amazon.com/dp/B123?ref=abc", "title": "Widget"}]
        materials = [{"item": "Widget", "product_url": "https://amazon.com/dp/B123"}]
        result = _backfill_materials_links(materials, products, _no_bad_urls)
        assert result[0]["product_url"] == "https://amazon.com/dp/B123"

    def test_invented_url_rejected(self):
        """Curator-invented URL not in inventory should be rejected and replaced."""
        products = [{"link": "https://amazon.com/dp/REAL123", "title": "Carbon Steel Wok"}]
        materials = [{"item": "Carbon Steel Wok", "product_url": "https://amazon.com/dp/FAKE999"}]
        result = _backfill_materials_links(materials, products, _no_bad_urls)
        # Should match to real product via fuzzy match, not keep fake URL
        assert result[0]["product_url"] == "https://amazon.com/dp/REAL123"

    def test_bad_url_excluded_from_inventory(self):
        """Products with bad URLs (search pages) should not be in inventory."""
        products = [{"link": "https://amazon.com/s?k=wok", "title": "Carbon Steel Wok"}]
        materials = [{"item": "Carbon Steel Wok", "product_url": "https://amazon.com/s?k=wok"}]
        result = _backfill_materials_links(materials, products, _reject_search_urls)
        assert result[0]["is_search_link"] is True


# ---------------------------------------------------------------------------
# Fuzzy word-overlap matching
# ---------------------------------------------------------------------------

class TestFuzzyMatching:
    def test_multi_word_match(self):
        """Item with multiple matching words should find the right product."""
        products = [
            {"link": "https://amazon.com/dp/A1", "title": "Carbon Steel Wok 14 Inch Flat Bottom"},
            {"link": "https://amazon.com/dp/A2", "title": "Stainless Steel Pot 8 Quart"},
        ]
        materials = [{"item": "Carbon Steel Wok"}]
        result = _backfill_materials_links(materials, products, _no_bad_urls)
        assert result[0]["product_url"] == "https://amazon.com/dp/A1"

    def test_picks_best_scoring_match(self):
        """When multiple products match, pick the one with highest word overlap."""
        products = [
            {"link": "https://amazon.com/dp/A1", "title": "Yoga Mat Extra Thick"},
            {"link": "https://amazon.com/dp/A2", "title": "Yoga Mat Premium Non-Slip Extra Thick Exercise Mat"},
        ]
        materials = [{"item": "Non-Slip Yoga Exercise Mat"}]
        result = _backfill_materials_links(materials, products, _no_bad_urls)
        # A2 has more word overlap: yoga, mat, non-slip, exercise (4 words)
        # A1 has: yoga, mat (2 words)
        assert result[0]["product_url"] == "https://amazon.com/dp/A2"

    def test_single_word_item_matches_with_one_word(self):
        """Single-word items should match with just 1 word overlap."""
        products = [{"link": "https://amazon.com/dp/A1", "title": "Watercolor Paint Brushes"}]
        materials = [{"item": "Brushes"}]
        result = _backfill_materials_links(materials, products, _no_bad_urls)
        assert result[0]["product_url"] == "https://amazon.com/dp/A1"

    def test_minimum_two_word_overlap_for_multi_word_items(self):
        """Multi-word items need at least 2 word overlap to match."""
        products = [
            {"link": "https://amazon.com/dp/A1", "title": "Cookbook for Beginners"},
        ]
        # "Cooking Class Supplies" only shares 0 meaningful words with "Cookbook for Beginners"
        # (stopwords like "for" are excluded)
        materials = [{"item": "Cooking Class Supplies"}]
        result = _backfill_materials_links(materials, products, _no_bad_urls)
        assert result[0]["is_search_link"] is True

    def test_stopwords_excluded(self):
        """Common words like 'the', 'and', 'for', 'set' should not count toward matching."""
        products = [
            {"link": "https://amazon.com/dp/A1", "title": "The Best Gift Set For Everyone"},
        ]
        materials = [{"item": "Gift Set for Home"}]
        result = _backfill_materials_links(materials, products, _no_bad_urls)
        # After removing stopwords ('the', 'best', 'gift', 'set', 'for'), very few meaningful words remain
        assert result[0]["is_search_link"] is True

    def test_no_match_falls_to_search(self):
        """Items with no inventory match should get search fallback."""
        products = [{"link": "https://amazon.com/dp/A1", "title": "Carbon Steel Wok"}]
        materials = [{"item": "Pottery Wheel Electric"}]
        result = _backfill_materials_links(materials, products, _no_bad_urls)
        assert result[0]["is_search_link"] is True
        assert "Pottery+Wheel+Electric" in result[0]["product_url"] or "Pottery%20Wheel%20Electric" in result[0]["product_url"]


# ---------------------------------------------------------------------------
# Multi-retailer search fallback
# ---------------------------------------------------------------------------

class TestSearchFallback:
    def test_default_amazon_search(self):
        materials = [{"item": "Yoga Mat"}]
        result = _backfill_materials_links(materials, [], _no_bad_urls)
        assert "amazon.com" in result[0]["product_url"]
        assert result[0]["where_to_buy"] == "Search Amazon"
        assert result[0]["is_search_link"] is True

    def test_etsy_search_when_where_to_buy_is_etsy(self):
        materials = [{"item": "Handmade Pottery Bowl", "where_to_buy": "Etsy"}]
        result = _backfill_materials_links(materials, [], _no_bad_urls)
        assert "etsy.com" in result[0]["product_url"]
        assert result[0]["where_to_buy"] == "Search Etsy"

    def test_ebay_search_when_where_to_buy_is_ebay(self):
        materials = [{"item": "Vintage Record Player", "where_to_buy": "eBay"}]
        result = _backfill_materials_links(materials, [], _no_bad_urls)
        assert "ebay.com" in result[0]["product_url"]
        assert result[0]["where_to_buy"] == "Search eBay"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_empty_materials_list(self):
        assert _backfill_materials_links([], [], _no_bad_urls) == []
        assert _backfill_materials_links(None, [], _no_bad_urls) is None

    def test_empty_item_name(self):
        materials = [{"item": "", "product_url": ""}]
        result = _backfill_materials_links(materials, [], _no_bad_urls)
        assert result[0]["is_search_link"] is True

    def test_preserves_estimated_price(self):
        materials = [{"item": "Yoga Mat", "estimated_price": "$25", "product_url": ""}]
        result = _backfill_materials_links(materials, [], _no_bad_urls)
        assert result[0]["estimated_price"] == "$25"

    def test_multiple_materials_independent(self):
        """Each material item should be matched independently."""
        products = [
            {"link": "https://amazon.com/dp/A1", "title": "Watercolor Paint Brushes Round Tip"},
            {"link": "https://amazon.com/dp/A2", "title": "Canvas Painting Stretched 16x20"},
        ]
        materials = [
            {"item": "Watercolor Paint Brushes"},
            {"item": "Stretched Canvas"},
        ]
        result = _backfill_materials_links(materials, products, _no_bad_urls)
        assert result[0]["product_url"] == "https://amazon.com/dp/A1"
        assert result[1]["product_url"] == "https://amazon.com/dp/A2"

    def test_does_not_mutate_original(self):
        """Should create copies of material dicts, not mutate originals."""
        materials = [{"item": "Yoga Mat", "product_url": "https://fake.com/fake"}]
        original_url = materials[0]["product_url"]
        _backfill_materials_links(materials, [], _no_bad_urls)
        assert materials[0]["product_url"] == original_url


# ---------------------------------------------------------------------------
# Non-purchasable item detection
# ---------------------------------------------------------------------------

class TestNonPurchasableItems:
    def test_playlist_skips_matching(self):
        """Items like 'custom playlist' should not match any product."""
        products = [
            {"link": "https://amazon.com/dp/A1", "title": "Taylor Swift Eras Tour Book"},
        ]
        materials = [{"item": "Custom playlist of Taylor Swift songs"}]
        result = _backfill_materials_links(materials, products, _no_bad_urls)
        assert result[0]["is_search_link"] is True

    def test_handwritten_letter_skips_matching(self):
        products = [{"link": "https://amazon.com/dp/A1", "title": "Letter Writing Stationery"}]
        materials = [{"item": "Handwritten letter to your friend"}]
        result = _backfill_materials_links(materials, products, _no_bad_urls)
        assert result[0]["is_search_link"] is True

    def test_diy_item_skips_matching(self):
        products = [{"link": "https://amazon.com/dp/A1", "title": "DIY Craft Kit"}]
        materials = [{"item": "DIY photo collage"}]
        result = _backfill_materials_links(materials, products, _no_bad_urls)
        assert result[0]["is_search_link"] is True

    def test_purchasable_item_still_matches(self):
        """Regular purchasable items should still match normally."""
        products = [{"link": "https://amazon.com/dp/A1", "title": "Watercolor Paint Brushes"}]
        materials = [{"item": "Watercolor Paint Brushes"}]
        result = _backfill_materials_links(materials, products, _no_bad_urls)
        assert result[0]["product_url"] == "https://amazon.com/dp/A1"
        assert result[0].get("is_search_link") is not True


# ---------------------------------------------------------------------------
# Experience URL validation
# ---------------------------------------------------------------------------

class TestExperienceUrlValidation:
    def test_empty_url_invalid(self):
        assert _validate_experience_url("") is False
        assert _validate_experience_url(None) is False

    def test_non_http_invalid(self):
        assert _validate_experience_url("ftp://venue.com") is False

    @patch('giftwise_app.requests.head')
    def test_valid_url_passes(self, mock_head):
        mock_head.return_value = MagicMock(status_code=200)
        assert _validate_experience_url("https://realvenue.com/events") is True

    @patch('giftwise_app.requests.head')
    def test_404_url_fails(self, mock_head):
        mock_head.return_value = MagicMock(status_code=404)
        assert _validate_experience_url("https://hallucinated-venue.com/book") is False

    @patch('giftwise_app.requests.head', side_effect=Exception("timeout"))
    @patch('giftwise_app.requests.get', side_effect=Exception("timeout"))
    def test_timeout_fails(self, mock_get, mock_head):
        assert _validate_experience_url("https://slow-venue.com") is False

    @patch('giftwise_app.requests.head')
    def test_redirect_to_valid_page_passes(self, mock_head):
        mock_head.return_value = MagicMock(status_code=301)
        # 301 < 400, so should pass
        assert _validate_experience_url("https://venue.com/old-page") is True


# ---------------------------------------------------------------------------
# Experience search link generation
# ---------------------------------------------------------------------------

class TestExperienceSearchLinks:
    def test_book_link(self):
        link = _make_experience_search_link("Taylor Swift Concert", "Indianapolis, Indiana", "book")
        assert "google.com/search" in link
        assert "Taylor" in link
        assert "tickets" in link
        assert "Indianapolis" in link

    def test_venue_link(self):
        link = _make_experience_search_link("Gainbridge Fieldhouse", "Indianapolis", "venue")
        assert "google.com/search" in link
        assert "Gainbridge" in link
        assert "tickets" not in link  # venue type doesn't add "tickets book"

    def test_empty_location_still_works(self):
        link = _make_experience_search_link("Cooking Class", "", "book")
        assert "Cooking" in link
