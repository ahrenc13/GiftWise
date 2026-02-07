"""
Tests for gift_curator.py formatting functions.

Verifies that format_products, format_interests, and format_venues
produce correct prompt text — and critically, that image_url is NOT
included in format_products output (Change 1 from architecture audit).
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from gift_curator import format_products, format_interests, format_venues


# ---------------------------------------------------------------------------
# format_products
# ---------------------------------------------------------------------------

class TestFormatProducts:
    def test_basic_formatting(self):
        products = [{
            "title": "Carbon Steel Wok",
            "link": "https://amazon.com/wok",
            "snippet": "14-inch flat bottom wok for stir fry",
            "price": "$45.99",
            "source_domain": "amazon.com",
            "interest_match": "cooking",
            "image": "https://img.amazon.com/wok.jpg",
            "thumbnail": "https://img.amazon.com/wok_thumb.jpg",
        }]
        result = format_products(products)
        assert "Carbon Steel Wok" in result
        assert "$45.99" in result
        assert "amazon.com" in result
        assert "cooking" in result
        assert "https://amazon.com/wok" in result

    def test_no_image_url_in_output(self):
        """Change 1: image_url must NOT appear in formatted product text sent to curator."""
        products = [{
            "title": "Test Product",
            "link": "https://amazon.com/test",
            "snippet": "A test",
            "price": "$10",
            "source_domain": "amazon.com",
            "interest_match": "testing",
            "image": "https://img.example.com/photo.jpg",
            "thumbnail": "https://img.example.com/thumb.jpg",
        }]
        result = format_products(products)
        assert "Image:" not in result
        assert "img.example.com" not in result

    def test_snippet_truncated_to_150(self):
        long_snippet = "x" * 300
        products = [{
            "title": "Item",
            "link": "https://example.com/item",
            "snippet": long_snippet,
            "price": "$10",
            "source_domain": "example.com",
            "interest_match": "test",
        }]
        result = format_products(products)
        # The snippet in output should be at most 150 chars of the original
        assert "x" * 151 not in result

    def test_multiple_products_numbered(self):
        products = [
            {"title": f"Product {i}", "link": f"https://example.com/p{i}",
             "snippet": "desc", "price": "$10", "source_domain": "example.com",
             "interest_match": "test"}
            for i in range(3)
        ]
        result = format_products(products)
        assert "1. Product 0" in result
        assert "2. Product 1" in result
        assert "3. Product 2" in result

    def test_caps_at_50_products(self):
        products = [
            {"title": f"Product {i}", "link": f"https://example.com/p{i}",
             "snippet": "desc", "price": "$10", "source_domain": "example.com",
             "interest_match": "test"}
            for i in range(60)
        ]
        result = format_products(products)
        assert "51. Product 50" not in result

    def test_empty_products(self):
        assert format_products([]) == "No products available"

    def test_missing_fields_use_defaults(self):
        products = [{"title": "Bare Product"}]
        result = format_products(products)
        assert "Bare Product" in result
        assert "Price unknown" in result
        assert "unknown" in result  # source_domain default


# ---------------------------------------------------------------------------
# format_interests
# ---------------------------------------------------------------------------

class TestFormatInterests:
    def test_basic_interest(self):
        interests = [{"name": "Cooking", "evidence": "Posts about recipes", "intensity": "high", "type": "current"}]
        result = format_interests(interests)
        assert "Cooking" in result
        assert "high" in result
        assert "Posts about recipes" in result

    def test_caps_at_15(self):
        interests = [{"name": f"Interest {i}", "evidence": "ev", "intensity": "low", "type": "current"}
                     for i in range(20)]
        result = format_interests(interests)
        assert "Interest 14" in result
        assert "Interest 15" not in result

    def test_empty_returns_none_identified(self):
        assert format_interests([]) == "None identified"
        assert format_interests(None) == "None identified"


# ---------------------------------------------------------------------------
# format_venues
# ---------------------------------------------------------------------------

class TestFormatVenues:
    def test_basic_venue(self):
        venues = [{"name": "Blue Door Jazz Club", "type": "music venue", "evidence": "Visited 3x", "location": "Indianapolis"}]
        result = format_venues(venues)
        assert "Blue Door Jazz Club" in result
        assert "Indianapolis" in result

    def test_caps_at_10(self):
        venues = [{"name": f"Venue {i}", "type": "bar", "evidence": "ev", "location": "City"}
                  for i in range(15)]
        result = format_venues(venues)
        assert "Venue 9" in result
        assert "Venue 10" not in result

    def test_empty_returns_none_identified(self):
        assert format_venues([]) == "None identified"
        assert format_venues(None) == "None identified"
