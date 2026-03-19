"""
CJ AFFILIATE PRODUCT SEARCHER
Searches CJ Affiliate network for gift products via GraphQL Product Feed API

API Documentation: https://developers.cj.com/graphql/reference/Product%20Feed%20API%20Reference
GraphQL Endpoint: https://ads.api.cj.com/query

Author: Chad + Claude
Date: February 2026
Status: ACTIVE - Using GraphQL Product Search API

CREDENTIALS (from env vars):
- CJ_API_KEY: Personal Access Token from CJ Developer Portal
- CJ_COMPANY_ID: Your publisher company ID (CID)
- CJ_PUBLISHER_ID: Your website/property ID (PID) for tracking links

API FEATURES:
- GraphQL product search across all joined advertisers
- Returns: title, description, price, image, affiliate tracking link
- Filters: keywords, partnerStatus (JOINED), price range, availability
- Rate limit: 500 calls per 5 minutes
- Max results: 1,000 per query (10,000 with pagination)
"""

import os
import logging
import time
import urllib.parse
from collections import deque
import requests

# Optional catalog cache — eliminates live CJ API calls for recently-synced terms.
# Degrades gracefully if catalog_sync.py isn't available or DB isn't warmed.
try:
    from catalog_sync import is_term_cache_fresh, get_cached_products_for_interest
    _CATALOG_CACHE_AVAILABLE = True
except ImportError:
    _CATALOG_CACHE_AVAILABLE = False
    def is_term_cache_fresh(*a, **kw): return False      # noqa: E704
    def get_cached_products_for_interest(*a, **kw): return []  # noqa: E704
import json

logger = logging.getLogger(__name__)

# CJ GraphQL API endpoint
CJ_GRAPHQL_ENDPOINT = "https://ads.api.cj.com/query"

# ---------------------------------------------------------------------------
# PEET'S COFFEE — Static curated products (approved CJ partner, Feb 17 2026)
# No product feed via CJ; deep links built off the Evergreen link (ID 15734720)
# Evergreen link: https://www.kqzyfj.com/click-101660899-15734720
# Gift bundle link (ID 15596392): https://www.kqzyfj.com/click-101660899-15596392
# T&C: NEWSUB30 (30% off first sub, valid Dec 2029) and WEBFRIEND5 (5% sitewide,
#       valid Dec 2026) are approved to promote. No other discount language.
# ---------------------------------------------------------------------------

# Evergreen link (ID 15734720) — deep-link enabled, use for specific product pages
_PEETS_EVERGREEN_BASE = "https://www.kqzyfj.com/click-101660899-15734720"

# Interests that trigger Peet's products
PEETS_TRIGGER_INTERESTS = {
    'coffee', 'espresso', 'tea', 'green tea', 'herbal tea', 'chai',
    'gourmet food', 'gourmet', 'specialty coffee', 'foodie',
    'cooking', 'indie folk', 'craft beer', 'baking', 'brunch',
    'morning routine', 'cafe culture', 'artisan', 'craft culture',
}


def _peets_deep_link(path):
    """Build a CJ deep link to a specific peets.com page."""
    destination = f"https://www.peets.com{path}"
    return f"{_PEETS_EVERGREEN_BASE}?url={urllib.parse.quote(destination, safe='')}"


# Static curated product list — direct CJ click URLs from CSV (Feb 17 2026)
# Images are real CJ banner images (300x250 or similar), not tracking pixels
_PEETS_ALL_PRODUCTS = [
    {
        # CJ link ID 15734720 (Evergreen, deep-link to product page)
        'title': "Peet's Major Dickason's Blend Coffee",
        'link': _peets_deep_link('/products/major-dickasons-blend'),
        'snippet': (
            "Peet's most iconic dark roast — bold, rich, and complex with layered "
            "flavors. A cult favorite since 1969. Use code WEBFRIEND5 for 5% off."
        ),
        'image': 'https://www.tqlkg.com/image-101660899-13437467',
        'thumbnail': 'https://www.tqlkg.com/image-101660899-13437467',
        'image_url': 'https://www.tqlkg.com/image-101660899-13437467',
        'source_domain': 'peets.com',
        'price': '$19.99',
        'product_id': 'peets-major-dickasons',
        'search_query': 'coffee',
        'interest_match': 'coffee',
        'priority': 2,
        'brand': "Peet's Coffee",
        'advertiser_id': 'peets-cj',
    },
    {
        # CJ link ID 13718353 — "Single Origin Series Subscription"
        'title': "Peet's Single Origin Series Coffee Subscription",
        'link': 'https://www.dpbolvw.net/click-101660899-13718353',
        'snippet': (
            "The quintessential expression of a coffee region in your cup — "
            "Peet's rotating single origin coffees from the world's finest farms. "
            "Use code NEWSUB30 for 30% off the first shipment."
        ),
        'image': 'https://www.lduhtrp.net/image-101660899-13625035',
        'thumbnail': 'https://www.lduhtrp.net/image-101660899-13625035',
        'image_url': 'https://www.lduhtrp.net/image-101660899-13625035',
        'source_domain': 'peets.com',
        'price': 'From $19.95/shipment',
        'product_id': 'peets-single-origin-sub',
        'search_query': 'coffee subscription',
        'interest_match': 'coffee',
        'priority': 2,
        'brand': "Peet's Coffee",
        'advertiser_id': 'peets-cj',
    },
    {
        # CJ link ID 13648651 — "Discover Mighty Leaf's most popular teas"
        'title': "Mighty Leaf Whole Leaf Tea Collection by Peet's",
        'link': 'https://www.kqzyfj.com/click-101660899-13648651',
        'snippet': (
            "Distinctive black, green, and herbal teas carefully crafted by Mighty Leaf, "
            "Peet's premium tea line. Whole-leaf pouches, rare single-origin varieties. "
            "Use code WEBFRIEND5 for 5% off."
        ),
        'image': 'https://www.ftjcfx.com/image-101660899-13588852',
        'thumbnail': 'https://www.ftjcfx.com/image-101660899-13588852',
        'image_url': 'https://www.ftjcfx.com/image-101660899-13588852',
        'source_domain': 'peets.com',
        'price': 'From $12.00',
        'product_id': 'peets-mighty-leaf-tea',
        'search_query': 'tea gift',
        'interest_match': 'tea',
        'priority': 2,
        'brand': "Peet's Coffee",
        'advertiser_id': 'peets-cj',
    },
    {
        # CJ link ID 15596392 — "Save with Bundles! Save up to 20% off"
        'title': "Peet's Coffee Gift Bundles — Save up to 20% off",
        'link': 'https://www.dpbolvw.net/click-101660899-15596392',
        'snippet': (
            "Peet's curated selection of best-selling coffee and tea bundles — "
            "save up to 20% off. Premium coffees, teas, and accessories. "
            "Use code WEBFRIEND5 for an extra 5% off."
        ),
        'image': 'https://www.tqlkg.com/image-101660899-15784148',
        'thumbnail': 'https://www.tqlkg.com/image-101660899-15784148',
        'image_url': 'https://www.tqlkg.com/image-101660899-15784148',
        'source_domain': 'peets.com',
        'price': 'From $35.00',
        'product_id': 'peets-gift-set',
        'search_query': 'coffee gift set',
        'interest_match': 'coffee',
        'priority': 2,
        'brand': "Peet's Coffee",
        'advertiser_id': 'peets-cj',
    },
    {
        # CJ link ID 13747502 — "Peet's Frequent Brewer Subscription + free shipping"
        'title': "Peet's Frequent Brewer Coffee Subscription",
        'link': 'https://www.jdoqocy.com/click-101660899-13747502',
        'snippet': (
            "Never run out of your favorite Peet's coffee — subscribe and get free "
            "shipping every time. Choose your roast, grind, and delivery frequency. "
            "First shipment 30% off with code NEWSUB30."
        ),
        'image': 'https://www.lduhtrp.net/image-101660899-13625035',
        'thumbnail': 'https://www.lduhtrp.net/image-101660899-13625035',
        'image_url': 'https://www.lduhtrp.net/image-101660899-13625035',
        'source_domain': 'peets.com',
        'price': 'From $19.95/month',
        'product_id': 'peets-frequent-brewer',
        'search_query': 'coffee subscription',
        'interest_match': 'coffee',
        'priority': 2,
        'brand': "Peet's Coffee",
        'advertiser_id': 'peets-cj',
    },
]


# ---------------------------------------------------------------------------
# ILLY CAFFÈ — Static curated products (approved CJ partner, Feb 17 2026)
# Evergreen link ID 15734901 — deep-link enabled, $48.81 EPC
#   Base: https://www.dpbolvw.net/click-101660899-15734901
#   Deep-link: append ?url=encoded_destination to route to specific illy pages
# ADV_CID: 2184930
#
# Commission: 6% new customers / 4% existing, 45-day cookie
# T&C (strictly enforced — illy audits publisher content):
#   PROHIBITED words on site: discount, discounts, % off, % savings,
#     save {x}%, cheap, cheapest, sale, bargain, rock bottom, clearance,
#     closeout, lowest
#   NO promo codes unless explicitly provided through CJ interface
#   NO SEM bidding on illy brand terms (not our concern — we're content)
#   Snippets must be factual/editorial, not promotional/deal-oriented
# ---------------------------------------------------------------------------

_ILLY_COMPANY_ID = '101660899'  # Same publisher company ID

# Evergreen link (ID 15734901) — deep-link enabled, use for specific product pages
_ILLY_EVERGREEN_BASE = "https://www.dpbolvw.net/click-101660899-15734901"


def _illy_deep_link(path):
    """Build a CJ deep link to a specific illy.com page."""
    destination = f"https://www.illy.com{path}"
    return f"{_ILLY_EVERGREEN_BASE}?url={urllib.parse.quote(destination, safe='')}"


_ILLY_ALL_PRODUCTS = [
    {
        # Evergreen deep link → illy ground coffee category
        'title': "illy Classico Medium Roast Ground Coffee",
        'link': _illy_deep_link('/en-us/coffee/ground-coffee'),
        'snippet': (
            "illy's signature medium-roast ground espresso — the taste of Italian café culture at home. "
            "Single-origin Arabica beans, perfectly balanced with notes of caramel and jasmine."
        ),
        'image': '',
        'thumbnail': '',
        'image_url': '',
        'source_domain': 'illy.com',
        'price': '$16.99',
        'product_id': 'illy-classico-ground',
        'search_query': 'espresso coffee gift',
        'interest_match': 'espresso',
        'priority': 2,
        'brand': 'illy',
        'advertiser_id': 'illy-cj',
    },
    {
        # Evergreen deep link → illy iperEspresso capsules category
        'title': "illy iperEspresso Capsules",
        'link': _illy_deep_link('/en-us/coffee/iperespresso-capsules'),
        'snippet': (
            "illy's patented iperEspresso capsules — barista-quality espresso in every cup, "
            "no skill required. Compatible with illy X1, Y1, Y3 machines. Eight roast varieties."
        ),
        'image': '',
        'thumbnail': '',
        'image_url': '',
        'source_domain': 'illy.com',
        'price': '$12.99',
        'product_id': 'illy-iperEspresso-capsules',
        'search_query': 'espresso capsules gift',
        'interest_match': 'espresso',
        'priority': 2,
        'brand': 'illy',
        'advertiser_id': 'illy-cj',
    },
    {
        # Evergreen deep link → illy espresso machines category
        'title': "illy iperEspresso Machine",
        'link': _illy_deep_link('/en-us/coffee-machines'),
        'snippet': (
            "illy's iconic espresso machine — authentic Italian espresso at the press of a button. "
            "Sleek design, one-touch operation. Includes a starter kit of iperEspresso capsules."
        ),
        'image': '',
        'thumbnail': '',
        'image_url': '',
        'source_domain': 'illy.com',
        'price': '$179.00',
        'product_id': 'illy-x1-machine',
        'search_query': 'espresso machine gift',
        'interest_match': 'espresso',
        'priority': 2,
        'brand': 'illy',
        'advertiser_id': 'illy-cj',
    },
]

_ILLY_TRIGGER_INTERESTS = {
    'coffee', 'espresso', 'italian culture', 'gourmet', 'foodie',
    'cafe culture', 'cooking', 'specialty coffee', 'morning routine',
    'gourmet food', 'coffee culture',
}


def get_illy_products_for_profile(profile):
    """
    Return curated illy caffè products when the profile has matching interests.

    illy has no product feed via CJ — static list using CJ deep links off
    Evergreen link ID 15734901. ADV_CID: 2184930.

    T&C: Do NOT use discount language — illy ToS prohibits it.
    Commission: 6% new / 4% existing, 45-day cookie.
    """
    interests = profile.get('interests', [])
    interest_names = {i.get('name', '').lower() for i in interests if i.get('name')}

    matched = interest_names & _ILLY_TRIGGER_INTERESTS
    if not matched:
        for name in interest_names:
            for trigger in _ILLY_TRIGGER_INTERESTS:
                if trigger in name or name in trigger:
                    matched.add(name)
                    break

    if not matched:
        return []

    logger.info(f"illy caffè triggered by profile interests: {matched}")
    return list(_ILLY_ALL_PRODUCTS)


# ---------------------------------------------------------------------------
# MONTHLYCLUBS.COM — Static curated products (approved CJ partner, Feb 2026)
# Publisher ID: 101660899 (embedded in all click URLs)
# Commission: 5–11.5% tiered by item group, 90-day referral period
# T&C: No cigar keywords. Only use promo codes provided via CJ interface.
# Links selected by highest 3-month EPC from CJ link data.
# ---------------------------------------------------------------------------

_MONTHLYCLUBS_ALL_PRODUCTS = [
    {
        # Beer Club Homepage — $8.96 EPC (link 10569413)
        'title': "Microbrewed Beer of the Month Club",
        'link': 'https://www.tkqlhce.com/click-101660899-10569413',
        'snippet': (
            "Monthly delivery of craft and imported microbrews from small-batch breweries. "
            "Each shipment includes tasting notes and brewery backstories."
        ),
        'image': 'https://www.lduhtrp.net/image-101660899-11162860',
        'thumbnail': 'https://www.lduhtrp.net/image-101660899-11162860',
        'image_url': 'https://www.lduhtrp.net/image-101660899-11162860',
        'source_domain': 'monthlyclubs.com',
        'price': 'From $42.95/month',
        'product_id': 'mc-beer-club',
        'search_query': 'craft beer subscription gift',
        'interest_match': 'craft beer',
        'interest_matches': {'beer', 'craft beer', 'brewery', 'drinking', 'homebrewing'},
        'priority': 2,
        'brand': 'MonthlyClubs',
        'advertiser_id': 'monthlyclubs-cj',
    },
    {
        # Hop Heads Beer Club — $68.00 EPC (link 15890384) — IPA lovers
        'title': "The Hop Heads Beer Club — IPA Subscription",
        'link': 'https://www.dpbolvw.net/click-101660899-15890384',
        'snippet': (
            "All hoppy beers, all the time — IPAs, DIPAs, and experimental hop-forward styles "
            "from craft breweries across the country. Monthly delivery with tasting notes."
        ),
        'image': 'https://www.lduhtrp.net/image-101660899-11162860',
        'thumbnail': 'https://www.lduhtrp.net/image-101660899-11162860',
        'image_url': 'https://www.lduhtrp.net/image-101660899-11162860',
        'source_domain': 'monthlyclubs.com',
        'price': 'From $42.95/month',
        'product_id': 'mc-hopheads-club',
        'search_query': 'IPA beer subscription gift',
        'interest_match': 'ipa',
        'interest_matches': {'ipa', 'hop', 'hops', 'hoppy beer', 'pale ale'},
        'priority': 3,
        'brand': 'MonthlyClubs',
        'advertiser_id': 'monthlyclubs-cj',
    },
    {
        # Premier Series Wine Club — $69.07 EPC (link 10569609) — highest EPC overall
        'title': "International Wine of the Month Club — Premier Series",
        'link': 'https://www.anrdoezrs.net/click-101660899-10569609',
        'snippet': (
            "Two hand-selected wines each month — red, white, and international varietals from "
            "hard-to-find producers. Includes vintage notes and food pairing suggestions."
        ),
        'image': 'https://www.awltovhc.com/image-101660899-10746026',
        'thumbnail': 'https://www.awltovhc.com/image-101660899-10746026',
        'image_url': 'https://www.awltovhc.com/image-101660899-10746026',
        'source_domain': 'monthlyclubs.com',
        'price': 'From $42.95/month',
        'product_id': 'mc-wine-club',
        'search_query': 'wine subscription gift club',
        'interest_match': 'wine',
        'interest_matches': {'wine', 'wine tasting', 'red wine', 'white wine', 'sommelier', 'oenophile'},
        'priority': 2,
        'brand': 'MonthlyClubs',
        'advertiser_id': 'monthlyclubs-cj',
    },
    {
        # Cheese Club Homepage — $25.06 EPC (link 10569573)
        'title': "Gourmet Cheese of the Month Club",
        'link': 'https://www.anrdoezrs.net/click-101660899-10569573',
        'snippet': (
            "Four artisan cheeses from small creameries monthly — domestic and international varieties. "
            "Each shipment includes a cheese guide and pairing recommendations."
        ),
        'image': 'https://www.awltovhc.com/image-101660899-12081130',
        'thumbnail': 'https://www.awltovhc.com/image-101660899-12081130',
        'image_url': 'https://www.awltovhc.com/image-101660899-12081130',
        'source_domain': 'monthlyclubs.com',
        'price': 'From $42.95/month',
        'product_id': 'mc-cheese-club',
        'search_query': 'artisan cheese subscription gift',
        'interest_match': 'cheese',
        'interest_matches': {'cheese', 'charcuterie', 'wine and cheese', 'gourmet food', 'foodie'},
        'priority': 2,
        'brand': 'MonthlyClubs',
        'advertiser_id': 'monthlyclubs-cj',
    },
    {
        # Gourmet Chocolate Club — $2.69 EPC (link 15890394)
        'title': "Gourmet Chocolate of the Month Club",
        'link': 'https://www.jdoqocy.com/click-101660899-15890394',
        'snippet': (
            "Premium chocolates from artisan makers monthly — dark, milk, Belgian, and single-origin varieties. "
            "Curated for chocolate lovers who want more than supermarket candy."
        ),
        'image': 'https://www.tqlkg.com/image-101660899-12082395',
        'thumbnail': 'https://www.tqlkg.com/image-101660899-12082395',
        'image_url': 'https://www.tqlkg.com/image-101660899-12082395',
        'source_domain': 'monthlyclubs.com',
        'price': 'From $42.95/month',
        'product_id': 'mc-chocolate-club',
        'search_query': 'gourmet chocolate subscription gift',
        'interest_match': 'chocolate',
        'interest_matches': {'chocolate', 'sweets', 'candy', 'baking', 'dessert', 'confectionery'},
        'priority': 2,
        'brand': 'MonthlyClubs',
        'advertiser_id': 'monthlyclubs-cj',
    },
    {
        # Flower Club Homepage — $1.86 EPC (link 10569584) — good for Mother's Day
        'title': "Fresh Cut Flower of the Month Club",
        'link': 'https://www.tkqlhce.com/click-101660899-10569584',
        'snippet': (
            "Professionally designed seasonal bouquets delivered monthly — orchids, roses, lilies, "
            "and more from specialty growers. A gift that arrives fresh every month."
        ),
        'image': 'https://www.lduhtrp.net/image-101660899-12082386',
        'thumbnail': 'https://www.lduhtrp.net/image-101660899-12082386',
        'image_url': 'https://www.lduhtrp.net/image-101660899-12082386',
        'source_domain': 'monthlyclubs.com',
        'price': 'From $42.95/month',
        'product_id': 'mc-flower-club',
        'search_query': 'flower subscription gift monthly bouquet',
        'interest_match': 'flowers',
        'interest_matches': {'flowers', 'gardening', 'floral', 'plants', 'botanicals', 'nature'},
        'priority': 2,
        'brand': 'MonthlyClubs',
        'advertiser_id': 'monthlyclubs-cj',
    },
]

_MONTHLYCLUBS_TRIGGER_INTERESTS = {
    'beer', 'craft beer', 'ipa', 'brewery', 'homebrewing', 'drinking',
    'wine', 'wine tasting', 'red wine', 'white wine', 'sommelier',
    'cheese', 'charcuterie', 'chocolate', 'sweets', 'baking', 'dessert',
    'flowers', 'gardening', 'floral', 'plants',
    'foodie', 'gourmet', 'gourmet food', 'entertaining', 'cooking', 'brunch',
}


def get_monthlyclubs_products_for_profile(profile):
    """
    Return MonthlyClubs subscription products when the profile has matching interests.

    Commission: 5–11.5% tiered, 90-day referral period.
    Selects the 2 products whose interest_matches best overlap the profile.
    """
    interests = profile.get('interests', [])
    interest_names = {i.get('name', '').lower() for i in interests if i.get('name')}

    # Score each product by how specifically it matches this profile's interests
    scored = []
    for p in _MONTHLYCLUBS_ALL_PRODUCTS:
        score = 0
        for key in p.get('interest_matches', set()):
            if key in interest_names:
                score += 2
            elif any(key in n or n in key for n in interest_names):
                score += 1
        if score > 0:
            scored.append((score, p))

    if not scored:
        return []

    scored.sort(key=lambda x: -x[0])
    result = [p for _, p in scored[:2]]
    logger.info(f"MonthlyClubs: {len(result)} products matched profile interests {interest_names & _MONTHLYCLUBS_TRIGGER_INTERESTS}")
    return result


# ---------------------------------------------------------------------------
# FLOWERS FAST — Static curated products (approved CJ partner, Feb 2026)
# Advertiser ID (ADV_CID): 231679
# Evergreen Link ID 15734454 — deep-link enabled, $74.28 3-month EPC
#   Base: https://www.tkqlhce.com/click-101660899-15734454
# Commission: 20%, 45-day referral period. AOV: ~$65, CR: ~3%.
# T&C:
#   - Do NOT use "FTD" or "Teleflora" trademarks anywhere in publisher copy
#   - Only use CJ-provided coupon codes (none currently active)
#   - Social media, email, sub-affiliates, and deep-linking allowed
# ---------------------------------------------------------------------------

_FLOWERSFAST_EVERGREEN_BASE = "https://www.tkqlhce.com/click-101660899-15734454"


def _flowersfast_deep_link(path):
    """Build a CJ deep link to a specific flowersfast.com page."""
    destination = f"https://www.flowersfast.com{path}"
    return f"{_FLOWERSFAST_EVERGREEN_BASE}?url={urllib.parse.quote(destination, safe='')}"


_FLOWERSFAST_ALL_PRODUCTS = [
    {
        # Link 1035863 — "Same Day Delivery" ($63.29 EPC — highest text link EPC)
        'title': "FlowersFast — Same-Day Fresh Flower Delivery",
        'link': 'https://www.tkqlhce.com/click-101660899-1035863',
        'snippet': (
            "Beautiful, hand-arranged bouquets delivered same-day from a local florist. "
            "Roses, lilies, sunflowers, and seasonal arrangements — fresh and delivered fast."
        ),
        'image': 'https://www.tqlkg.com/image-101660899-10542072',
        'thumbnail': 'https://www.tqlkg.com/image-101660899-10542072',
        'image_url': 'https://www.tqlkg.com/image-101660899-10542072',
        'source_domain': 'flowersfast.com',
        'price': 'From $39.99',
        'product_id': 'flowersfast-same-day',
        'search_query': 'flower delivery gift bouquet',
        'interest_match': 'flowers',
        'interest_matches': {'flowers', 'floral', 'gardening', 'plants', 'botanicals', 'nature', 'home decor', 'interior design'},
        'priority': 2,
        'brand': 'FlowersFast',
        'advertiser_id': 'flowersfast-cj',
    },
    {
        # Link 678765 — "Romance Flowers"
        'title': "FlowersFast — Anniversary & Romance Flower Arrangements",
        'link': 'https://www.tkqlhce.com/click-101660899-678765',
        'snippet': (
            "Romantic roses and signature arrangements for anniversaries, date nights, and "
            "special moments. Same-day delivery available."
        ),
        'image': 'https://www.awltovhc.com/image-101660899-13462919',
        'thumbnail': 'https://www.awltovhc.com/image-101660899-13462919',
        'image_url': 'https://www.awltovhc.com/image-101660899-13462919',
        'source_domain': 'flowersfast.com',
        'price': 'From $49.99',
        'product_id': 'flowersfast-romance',
        'search_query': 'anniversary romance flowers',
        'interest_match': 'romance',
        'interest_matches': {'romance', 'relationships', 'dating', 'anniversary', 'love', 'weddings', 'bridal'},
        'priority': 2,
        'brand': 'FlowersFast',
        'advertiser_id': 'flowersfast-cj',
    },
    {
        # Link 1035858 — "Birthday Flowers"
        'title': "FlowersFast — Birthday Bouquets",
        'link': 'https://www.kqzyfj.com/click-101660899-1035858',
        'snippet': (
            "Bright, cheerful birthday arrangements hand-designed by local florists — "
            "delivered same day. Sunflowers, gerbera daisies, and seasonal favorites."
        ),
        'image': 'https://www.lduhtrp.net/image-101660899-56033',
        'thumbnail': 'https://www.lduhtrp.net/image-101660899-56033',
        'image_url': 'https://www.lduhtrp.net/image-101660899-56033',
        'source_domain': 'flowersfast.com',
        'price': 'From $39.99',
        'product_id': 'flowersfast-birthday',
        'search_query': 'birthday flowers bouquet',
        'interest_match': 'birthday',
        'interest_matches': {'birthday', 'celebration', 'party', 'entertaining', 'festive'},
        'priority': 2,
        'brand': 'FlowersFast',
        'advertiser_id': 'flowersfast-cj',
    },
    {
        # Link 13462924 — "Get Well Flowers"
        'title': "FlowersFast — Get Well & Sympathy Flowers",
        'link': 'https://www.tkqlhce.com/click-101660899-13462924',
        'snippet': (
            "Uplifting arrangements and sympathy bouquets for life's tender moments — "
            "same-day delivery from local florists who know the occasion matters."
        ),
        'image': 'https://www.ftjcfx.com/image-101660899-13462924',
        'thumbnail': 'https://www.ftjcfx.com/image-101660899-13462924',
        'image_url': 'https://www.ftjcfx.com/image-101660899-13462924',
        'source_domain': 'flowersfast.com',
        'price': 'From $39.99',
        'product_id': 'flowersfast-get-well',
        'search_query': 'get well sympathy flowers',
        'interest_match': 'wellness',
        'interest_matches': {'wellness', 'health', 'yoga', 'mindfulness', 'self-care', 'meditation', 'kindness'},
        'priority': 3,
        'brand': 'FlowersFast',
        'advertiser_id': 'flowersfast-cj',
    },
]

_FLOWERSFAST_TRIGGER_INTERESTS = {
    'flowers', 'floral', 'gardening', 'plants', 'botanicals', 'nature',
    'home decor', 'interior design', 'romance', 'relationships', 'dating',
    'anniversary', 'love', 'birthday', 'celebration', 'weddings', 'bridal',
    'wellness', 'yoga', 'mindfulness', 'self-care',
}


# ---------------------------------------------------------------------------
# FRAGRANCESHOP.COM — Static curated products (approved CJ partner, Feb 2026)
# Advertiser ID (ADV_CID): 7287203
# Evergreen Link ID 16942179 — deep-link enabled, $43.59 3-month EPC
#   Base: https://www.tkqlhce.com/click-101660899-16942179
# Commission: 5%, 45-day referral period
# Daily updated product feed (products may also surface via CJ GraphQL search)
# T&C:
#   - Do NOT claim "authorized wholesaler" or "official site"
#   - Do NOT use specific discount percentages that may be outdated
#   - Only use CJ-provided coupon codes
#   - Social media, email, sub-affiliates, and deep-linking all allowed
# ---------------------------------------------------------------------------

_FRAGRANCESHOP_EVERGREEN_BASE = "https://www.tkqlhce.com/click-101660899-16942179"


def _fragranceshop_deep_link(path):
    """Build a CJ deep link to a specific fragranceshop.com page."""
    destination = f"https://www.fragranceshop.com{path}"
    return f"{_FRAGRANCESHOP_EVERGREEN_BASE}?url={urllib.parse.quote(destination, safe='')}"


_FRAGRANCESHOP_ALL_PRODUCTS = [
    {
        # Evergreen link 16942179 — $43.59 3-month EPC, $44.57 7-day EPC (best link)
        'title': "FragranceShop — Designer Fragrances & Colognes",
        'link': 'https://www.tkqlhce.com/click-101660899-16942179',
        'snippet': (
            "Over 10,000 authentic brand-name perfumes, colognes, and fragrances — "
            "Chanel, Dior, Versace, and more. Free shipping and a 30-day return policy."
        ),
        'image': 'https://www.lduhtrp.net/image-101660899-16941521',
        'thumbnail': 'https://www.lduhtrp.net/image-101660899-16941521',
        'image_url': 'https://www.lduhtrp.net/image-101660899-16941521',
        'source_domain': 'fragranceshop.com',
        'price': 'Varies by fragrance',
        'product_id': 'fragranceshop-general',
        'search_query': 'designer fragrance perfume gift',
        'interest_match': 'fragrance',
        'interest_matches': {'fragrance', 'perfume', 'cologne', 'beauty', 'luxury', 'fashion', 'style', 'grooming', 'self-care', 'cosmetics'},
        'priority': 2,
        'brand': 'FragranceShop',
        'advertiser_id': 'fragranceshop-cj',
    },
    {
        # Link 16942204 — Women's Perfume
        'title': "FragranceShop — Women's Perfume Collection",
        'link': 'https://www.kqzyfj.com/click-101660899-16942204',
        'snippet': (
            "Authentic designer perfumes for women — from classics to the latest releases. "
            "Chanel No. 5, Marc Jacobs, YSL, and hundreds more brands. Free shipping."
        ),
        'image': '',
        'thumbnail': '',
        'image_url': '',
        'source_domain': 'fragranceshop.com',
        'price': 'Varies by fragrance',
        'product_id': 'fragranceshop-womens',
        'search_query': "women's perfume gift",
        'interest_match': 'perfume',
        'interest_matches': {'perfume', 'beauty', 'makeup', 'skincare', 'fashion', 'style', 'luxury', 'self-care', 'personal care'},
        'priority': 2,
        'brand': 'FragranceShop',
        'advertiser_id': 'fragranceshop-cj',
    },
    {
        # Link 16942203 — Men's Cologne
        'title': "FragranceShop — Men's Cologne Collection",
        'link': 'https://www.tkqlhce.com/click-101660899-16942203',
        'snippet': (
            "Authentic designer colognes for men — from barbershop classics to modern niche releases. "
            "Acqua di Gio, Bleu de Chanel, Dior Sauvage, and hundreds more. Free shipping."
        ),
        'image': '',
        'thumbnail': '',
        'image_url': '',
        'source_domain': 'fragranceshop.com',
        'price': 'Varies by fragrance',
        'product_id': 'fragranceshop-mens',
        'search_query': "men's cologne gift",
        'interest_match': 'cologne',
        'interest_matches': {'cologne', 'grooming', 'menswear', 'fashion', 'style', 'luxury', 'self-care', 'personal care'},
        'priority': 2,
        'brand': 'FragranceShop',
        'advertiser_id': 'fragranceshop-cj',
    },
]

_FRAGRANCESHOP_TRIGGER_INTERESTS = {
    'fragrance', 'perfume', 'cologne', 'beauty', 'makeup', 'skincare',
    'grooming', 'self-care', 'fashion', 'style', 'luxury', 'cosmetics',
    'personal care', 'menswear', 'personal style',
}


# ---------------------------------------------------------------------------
# GAMEFLY — Static curated products (approved CJ partner, Feb 2026)
# Advertiser ID (ADV_CID): 1132500
# Evergreen Link ID 15733829 — deep-link enabled, $18.73 3-month / $37.00 7-day EPC
#   Base: https://www.dpbolvw.net/click-101660899-15733829
# Commission:
#   - $5.00 per subscription signup (25-day referral period)
#   - 10% on used games, accessories, collectibles, used movies (10-day referral)
#   - 0% on new games and consoles — do NOT recommend buying new via GameFly
#   - Gift certificates are non-commissionable
# T&C:
#   - No GameFly trademark in domains/URLs (not relevant)
#   - Only CJ-provided coupon codes
#   - Social media promotions must tag @GameFly and #GameFly
# ---------------------------------------------------------------------------

_GAMEFLY_EVERGREEN_BASE = "https://www.dpbolvw.net/click-101660899-15733829"


_GAMEFLY_ALL_PRODUCTS = [
    {
        # Evergreen link 15733829 — $37.00 7-day EPC, deep-link enabled
        'title': "GameFly — Video Game Rental Subscription",
        'link': 'https://www.dpbolvw.net/click-101660899-15733829',
        'snippet': (
            "Unlimited video game rentals delivered to their door — PS5, Xbox, and Nintendo Switch. "
            "Try the newest releases without paying full price. Plans start at $9.50/month."
        ),
        'image': 'https://www.lduhtrp.net/image-101660899-10671020',
        'thumbnail': 'https://www.lduhtrp.net/image-101660899-10671020',
        'image_url': 'https://www.lduhtrp.net/image-101660899-10671020',
        'source_domain': 'gamefly.com',
        'price': 'From $9.50/month',
        'product_id': 'gamefly-subscription',
        'search_query': 'video game subscription gift gaming',
        'interest_match': 'video games',
        'interest_matches': {'video games', 'gaming', 'console gaming', 'playstation', 'xbox', 'nintendo', 'nintendo switch', 'ps5', 'esports', 'game streaming', 'twitch', 'competitive gaming'},
        'priority': 2,
        'brand': 'GameFly',
        'advertiser_id': 'gamefly-cj',
    },
    {
        # Link 10891486 — Used Game Best Sellers ($9.09 EPC, 10% commission)
        'title': "GameFly — Pre-Played Video Games",
        'link': 'https://www.tkqlhce.com/click-101660899-10891486',
        'snippet': (
            "Pre-played PS5, Xbox, and Nintendo Switch games in excellent condition — "
            "original case and manuals included. A huge selection of titles at reduced prices."
        ),
        'image': 'https://www.ftjcfx.com/image-101660899-15520667',
        'thumbnail': 'https://www.ftjcfx.com/image-101660899-15520667',
        'image_url': 'https://www.ftjcfx.com/image-101660899-15520667',
        'source_domain': 'gamefly.com',
        'price': 'Varies by game',
        'product_id': 'gamefly-used-games',
        'search_query': 'used video games gift',
        'interest_match': 'video games',
        'interest_matches': {'video games', 'gaming', 'retro gaming', 'console gaming', 'playstation', 'xbox', 'nintendo'},
        'priority': 3,
        'brand': 'GameFly',
        'advertiser_id': 'gamefly-cj',
    },
]

_GAMEFLY_TRIGGER_INTERESTS = {
    'video games', 'gaming', 'console gaming', 'playstation', 'xbox',
    'nintendo', 'nintendo switch', 'ps5', 'esports', 'game streaming',
    'twitch', 'competitive gaming', 'retro gaming', 'pc gaming',
}


# ---------------------------------------------------------------------------
# GREATERGOOD — Static curated products (approved CJ partner, Feb 2026)
# Advertiser ID (ADV_CID): 4046728
# Evergreen Link ID 15734341 — deep-link enabled, $6.45 3-month EPC
#   Base: https://www.anrdoezrs.net/click-101660899-15734341
# Commission: 2% baseline; Animal Rescue Site items up to 10-15%
# AOV: $40+, 55% repeat customers, 45-day cookie
# Key angle: charity store — every purchase donates to causes (animals, veterans, etc.)
# T&C:
#   - No software/toolbar allowed
#   - Only CJ-provided coupon codes
#   - Social media, email, sub-affiliates allowed
# ---------------------------------------------------------------------------

_GREATERGOOD_ALL_PRODUCTS = [
    {
        # Link 11406091 — "Shop To Save Animals" ($4.97 3-month, $8.85 7-day EPC — best link)
        'title': "The Animal Rescue Site — Gifts That Feed Shelter Animals",
        'link': 'https://www.anrdoezrs.net/click-101660899-11406091',
        'snippet': (
            "Jewelry, apparel, and home goods where every purchase funds food for shelter animals. "
            "A gift for a dog or cat lover that gives back — 20+ years supporting animal rescue."
        ),
        'image': 'https://www.ftjcfx.com/image-101660899-11412871',
        'thumbnail': 'https://www.ftjcfx.com/image-101660899-11412871',
        'image_url': 'https://www.ftjcfx.com/image-101660899-11412871',
        'source_domain': 'greatergood.com',
        'price': 'From $20',
        'product_id': 'greatergood-animal-rescue',
        'search_query': 'animal rescue gift charity dog cat',
        'interest_match': 'dogs',
        'interest_matches': {'dogs', 'cats', 'animals', 'pets', 'dog parent', 'cat parent', 'animal rescue', 'animal welfare', 'wildlife', 'pet lover'},
        'priority': 2,
        'brand': 'GreaterGood / Animal Rescue Site',
        'advertiser_id': 'greatergood-cj',
    },
    {
        # Link 11954670 — GreaterGood general store ($2.79 EPC)
        'title': "GreaterGood — Shop Where Every Purchase Supports a Cause",
        'link': 'https://www.jdoqocy.com/click-101660899-11954670',
        'snippet': (
            "Artisan-made, fair trade, and unique gifts — jewelry, clothing, and home goods "
            "where every purchase funds charities for animals, veterans, hunger, and more."
        ),
        'image': 'https://www.ftjcfx.com/image-101660899-11412871',
        'thumbnail': 'https://www.ftjcfx.com/image-101660899-11412871',
        'image_url': 'https://www.ftjcfx.com/image-101660899-11412871',
        'source_domain': 'greatergood.com',
        'price': 'From $20',
        'product_id': 'greatergood-general',
        'search_query': 'charitable gift ethical shopping cause',
        'interest_match': 'philanthropy',
        'interest_matches': {'philanthropy', 'charity', 'giving back', 'activism', 'social justice', 'sustainability', 'environmentalism', 'conservation', 'volunteering', 'community'},
        'priority': 3,
        'brand': 'GreaterGood',
        'advertiser_id': 'greatergood-cj',
    },
]

_GREATERGOOD_TRIGGER_INTERESTS = {
    'dogs', 'cats', 'animals', 'pets', 'dog parent', 'cat parent',
    'animal rescue', 'animal welfare', 'wildlife', 'pet lover',
    'philanthropy', 'charity', 'giving back', 'activism', 'social justice',
    'sustainability', 'environmentalism', 'conservation', 'volunteering',
}


# ---------------------------------------------------------------------------
# GROUNDLUXE — Static curated products (approved CJ partner, Feb 2026)
# Advertiser ID (ADV_CID): 7681501
# Evergreen Link ID 17180505 — deep-link enabled, $150.60 3-month EPC (highest in stack)
#   Base: https://www.kqzyfj.com/click-101660899-17180505
# Commission: 10%, 30-day cookie
# Product: Luxury grounding sheets (90% organic cotton + 10% silver fiber)
# AOV: High — estimated $150-300+ based on EPC data
# Target: Wellness-minded adults 45-65, sleep/recovery/natural health seekers
# T&C: No trademark bidding (SEM, not our concern). No other restrictions noted.
# NOTE: Do NOT make specific medical/health claims ("proven to reduce pain").
#       Use earthing/grounding wellness framing instead.
# ---------------------------------------------------------------------------

_GROUNDLUXE_ALL_PRODUCTS = [
    {
        # Evergreen 17180505 — $150.60 EPC (best reliable link)
        'title': "GroundLuxe Luxury Grounding Sheets",
        'link': 'https://www.kqzyfj.com/click-101660899-17180505',
        'snippet': (
            "The #1 bestselling grounding (earthing) sheet set — 90% organic cotton with "
            "conductive silver fibers that connect you to the Earth's natural energy while you sleep. "
            "Soft as luxury hotel bedding. USA-owned, exceptional customer support."
        ),
        'image': 'https://www.lduhtrp.net/image-101660899-17168754',
        'thumbnail': 'https://www.lduhtrp.net/image-101660899-17168754',
        'image_url': 'https://www.lduhtrp.net/image-101660899-17168754',
        'source_domain': 'groundluxe.com',
        'price': 'From $149',
        'product_id': 'groundluxe-sheets',
        'search_query': 'grounding sheets wellness sleep gift',
        'interest_match': 'wellness',
        'interest_matches': {'wellness', 'yoga', 'meditation', 'mindfulness', 'holistic health', 'natural health', 'alternative medicine', 'sleep', 'sleep health', 'recovery', 'biohacking', 'self-care', 'health', 'pilates', 'fitness'},
        'priority': 1,  # Highest EPC in stack — prioritize this
        'brand': 'GroundLuxe',
        'advertiser_id': 'groundluxe-cj',
    },
    {
        # Link 17168758 — $221.09 EPC ("reduce inflammation" framing)
        'title': "GroundLuxe Grounding Sheet — Sleep & Recovery",
        'link': 'https://www.jdoqocy.com/click-101660899-17168758',
        'snippet': (
            "Grounding sheets used by athletes and wellness enthusiasts for overnight recovery — "
            "silver-fiber sheets that conduct the Earth's natural electrical charge. "
            "Organic cotton, made in the USA, trusted by thousands of sleepers."
        ),
        'image': 'https://www.awltovhc.com/image-101660899-17165115',
        'thumbnail': 'https://www.awltovhc.com/image-101660899-17165115',
        'image_url': 'https://www.awltovhc.com/image-101660899-17165115',
        'source_domain': 'groundluxe.com',
        'price': 'From $149',
        'product_id': 'groundluxe-recovery',
        'search_query': 'grounding earthing sheets sleep recovery',
        'interest_match': 'wellness',
        'interest_matches': {'recovery', 'fitness', 'running', 'cycling', 'sports', 'health', 'natural health', 'holistic health', 'wellness', 'chronic pain', 'inflammation', 'biohacking'},
        'priority': 1,
        'brand': 'GroundLuxe',
        'advertiser_id': 'groundluxe-cj',
    },
]

_GROUNDLUXE_TRIGGER_INTERESTS = {
    'wellness', 'yoga', 'meditation', 'mindfulness', 'holistic health',
    'natural health', 'alternative medicine', 'sleep', 'sleep health',
    'recovery', 'biohacking', 'self-care', 'health', 'pilates',
    'fitness', 'running', 'cycling', 'sports', 'chronic pain',
}


# ---------------------------------------------------------------------------
# RUSSELL STOVER CHOCOLATES — Static curated products (approved CJ partner, Feb 2026)
# Advertiser ID (ADV_CID): 4441453
# Evergreen Link ID 15736776 — deep-link enabled, $1.50 7-day EPC
#   Base: https://www.kqzyfj.com/click-101660899-15736776
# Commission: 5%, 5-day referral period (short — must buy within 5 days), 1 occurrence
# Non-commissionable: Gift Baskets, Gift Cards, Outlet items, Gift Wrap
# T&C:
#   - Trademark terms (Russell Stover, Whitman's, Build-A-Box, etc.) protected for SEM
#     bidding only — editorial content use is permitted
#   - Only CJ-provided images and creative
#   - Only CJ-provided coupon codes
#   - Email campaigns require prior written approval (not relevant — we don't email)
# ---------------------------------------------------------------------------

_RUSSELLSTOVER_ALL_PRODUCTS = [
    {
        # Evergreen link 15736776 — deep-link enabled (best general link)
        'title': "Russell Stover Chocolates — Classic American Boxed Chocolates",
        'link': 'https://www.kqzyfj.com/click-101660899-15736776',
        'snippet': (
            "Handcrafted American chocolates — assorted truffles, caramels, and creams "
            "in classic gift boxes. A timeless, universally loved gift for any occasion."
        ),
        'image': 'https://www.tqlkg.com/image-101660899-12221994',
        'thumbnail': 'https://www.tqlkg.com/image-101660899-12221994',
        'image_url': 'https://www.tqlkg.com/image-101660899-12221994',
        'source_domain': 'russellstover.com',
        'price': 'From $12.99',
        'product_id': 'russellstover-chocolates',
        'search_query': 'boxed chocolates gift candy',
        'interest_match': 'chocolate',
        'interest_matches': {'chocolate', 'sweets', 'candy', 'confectionery', 'dessert', 'baking', 'gourmet food', 'foodie', 'entertaining'},
        'priority': 3,
        'brand': 'Russell Stover',
        'advertiser_id': 'russellstover-cj',
    },
    {
        # Link 12377127 — Build-A-Box custom chocolate box (compelling gift angle)
        'title': "Russell Stover Build-A-Box — Custom Chocolate Gift",
        'link': 'https://www.kqzyfj.com/click-101660899-12377127',
        'snippet': (
            "Build a personalized box of chocolates — choose your favorite flavors "
            "from truffles, caramels, creams, and more. Available in four sizes."
        ),
        'image': 'https://www.lduhtrp.net/image-101660899-12222027',
        'thumbnail': 'https://www.lduhtrp.net/image-101660899-12222027',
        'image_url': 'https://www.lduhtrp.net/image-101660899-12222027',
        'source_domain': 'russellstover.com',
        'price': 'From $14.99',
        'product_id': 'russellstover-buildabox',
        'search_query': 'custom chocolate box personalized gift',
        'interest_match': 'chocolate',
        'interest_matches': {'chocolate', 'sweets', 'candy', 'confectionery', 'dessert', 'personalization', 'gourmet food', 'foodie'},
        'priority': 3,
        'brand': 'Russell Stover',
        'advertiser_id': 'russellstover-cj',
    },
]

_RUSSELLSTOVER_TRIGGER_INTERESTS = {
    'chocolate', 'sweets', 'candy', 'confectionery', 'dessert',
    'baking', 'gourmet food', 'foodie', 'entertaining',
}


def get_russellstover_products_for_profile(profile):
    """
    Return Russell Stover products when the profile has chocolate/sweets interests.

    Static list using direct CJ click URLs. ADV_CID: 4441453.
    Commission: 5%, 5-day cookie (short). NON-commissionable: Gift Baskets, Gift Cards.

    Returns at most 1 product — MonthlyClubs already covers artisan chocolate subscriptions;
    Russell Stover is the "classic American boxed chocolates" option.
    """
    interests = profile.get('interests', [])
    interest_names = {i.get('name', '').lower() for i in interests if i.get('name')}

    scored = []
    for p in _RUSSELLSTOVER_ALL_PRODUCTS:
        score = 0
        for key in p.get('interest_matches', set()):
            if key in interest_names:
                score += 2
            elif any(key in n or n in key for n in interest_names):
                score += 1
        if score > 0:
            scored.append((score, p))

    if not scored:
        return []

    scored.sort(key=lambda x: -x[0])
    # Prefer Build-A-Box when "personalization" matches; otherwise generic chocolates
    result = [p for _, p in scored[:1]]
    logger.info(f"Russell Stover: {len(result)} products matched profile interests {interest_names & _RUSSELLSTOVER_TRIGGER_INTERESTS}")
    return result


# ---------------------------------------------------------------------------
# GHIRARDELLI CHOCOLATE — Static curated products (approved CJ partner, Mar 2026)
# Advertiser ID (ADV_CID): 2692680
# Evergreen Link ID 15733738 — deep-link enabled, $76.96 3-mo EPC / $88.65 7-day EPC
#   Base: https://www.dpbolvw.net/click-101660899-15733738
# Pick & Mix Text Link ID 16950958 — $26.63 3-mo EPC
# Commission: Check CJ dashboard (Gourmet category)
# T&C: Standard CJ terms. Banner links only (no product feed).
# ---------------------------------------------------------------------------

_GHIRARDELLI_EVERGREEN_BASE = "https://www.dpbolvw.net/click-101660899-15733738"


def _ghirardelli_deep_link(path):
    """Build a CJ deep link to a specific ghirardelli.com page."""
    destination = f"https://www.ghirardelli.com{path}"
    return f"{_GHIRARDELLI_EVERGREEN_BASE}?url={urllib.parse.quote(destination, safe='')}"


_GHIRARDELLI_ALL_PRODUCTS = [
    {
        # Pick & Mix text link 16950958 — highest-converting product link ($26.63 EPC)
        'title': "Ghirardelli Pick & Mix — Build Your Own Chocolate Squares Box",
        'link': 'https://www.dpbolvw.net/click-101660899-16950958',
        'snippet': (
            "Choose from dozens of Ghirardelli's signature chocolate squares — dark, milk, "
            "caramel, sea salt, peppermint, and limited-edition flavors. Build a personalized "
            "box of San Francisco's finest chocolate. Ships free on orders $75+."
        ),
        'image': '',
        'thumbnail': '',
        'image_url': '',
        'source_domain': 'ghirardelli.com',
        'price': 'From $1.00/square',
        'product_id': 'ghirardelli-pick-mix',
        'search_query': 'chocolate gift box',
        'interest_match': 'chocolate',
        'interest_matches': {'chocolate', 'sweets', 'candy', 'confectionery', 'dessert', 'personalization', 'gourmet food', 'foodie', 'baking'},
        'priority': 2,
        'brand': 'Ghirardelli',
        'advertiser_id': 'ghirardelli-cj',
    },
    {
        # Evergreen link 15733738 — deep-link to gift shop ($76.96 / $88.65 EPC)
        'title': "Ghirardelli Chocolate Gift Boxes & Baskets",
        'link': _ghirardelli_deep_link('/collections/gift-shop'),
        'snippet': (
            "Premium chocolate gift boxes from Ghirardelli — San Francisco's iconic chocolatier "
            "since 1852. Beautifully packaged assortments of squares, bars, and truffles. "
            "Perfect for birthdays, holidays, and thank-you gifts."
        ),
        'image': '',
        'thumbnail': '',
        'image_url': '',
        'source_domain': 'ghirardelli.com',
        'price': 'From $15.00',
        'product_id': 'ghirardelli-gift-shop',
        'search_query': 'gourmet chocolate gift',
        'interest_match': 'chocolate',
        'interest_matches': {'chocolate', 'sweets', 'candy', 'confectionery', 'dessert', 'gourmet food', 'foodie', 'baking', 'entertaining'},
        'priority': 2,
        'brand': 'Ghirardelli',
        'advertiser_id': 'ghirardelli-cj',
    },
    {
        # Deep-link to baking collection — for baking enthusiasts
        'title': "Ghirardelli Baking Chocolates & Cocoa",
        'link': _ghirardelli_deep_link('/collections/baking'),
        'snippet': (
            "Premium baking chocolate, cocoa powder, and chocolate chips from Ghirardelli. "
            "The secret ingredient in serious home bakers' kitchens — intense flavor from "
            "bean-to-bar craftsmanship since 1852."
        ),
        'image': '',
        'thumbnail': '',
        'image_url': '',
        'source_domain': 'ghirardelli.com',
        'price': 'From $5.00',
        'product_id': 'ghirardelli-baking',
        'search_query': 'baking chocolate gift',
        'interest_match': 'baking',
        'interest_matches': {'baking', 'cooking', 'chocolate', 'dessert', 'gourmet food', 'foodie', 'chef'},
        'priority': 3,
        'brand': 'Ghirardelli',
        'advertiser_id': 'ghirardelli-cj',
    },
]

_GHIRARDELLI_TRIGGER_INTERESTS = {
    'chocolate', 'dark chocolate', 'milk chocolate', 'sweets', 'candy',
    'confectionery', 'dessert', 'baking', 'gourmet food', 'foodie',
    'cooking', 'chef', 'entertaining',
}


def get_ghirardelli_products_for_profile(profile):
    """
    Return Ghirardelli products when the profile has chocolate/baking/gourmet interests.

    Static list using direct CJ click URLs. ADV_CID: 2692680.
    Evergreen link $76.96/$88.65 EPC — strong performer.

    Ghirardelli is the "premium American chocolate" tier — between Russell Stover
    (mass-market boxed) and zChocolat (ultra-luxury French). Pick & Mix is the
    standout product for gifting (personalized, fun, accessible price point).

    Returns at most 2 products. Pick & Mix preferred for personalization profiles;
    baking collection surfaces when baking/cooking interests are strong.
    """
    interests = profile.get('interests', [])
    interest_names = {i.get('name', '').lower() for i in interests if i.get('name')}

    scored = []
    for p in _GHIRARDELLI_ALL_PRODUCTS:
        score = 0
        for key in p.get('interest_matches', set()):
            if key in interest_names:
                score += 2
            elif any(key in n or n in key for n in interest_names):
                score += 1
        if score > 0:
            scored.append((score, p))

    if not scored:
        return []

    scored.sort(key=lambda x: -x[0])
    result = [p for _, p in scored[:2]]
    logger.info(f"Ghirardelli: {len(result)} products matched profile interests {interest_names & _GHIRARDELLI_TRIGGER_INTERESTS}")
    return result


# ---------------------------------------------------------------------------
# SILVERRUSHSTYLE — Static curated products (approved CJ partner, Feb 2026)
# Advertiser ID (ADV_CID): 3874186
# Home page Link ID 11260306 — $16.79 EPC
#   Base: https://www.kqzyfj.com/click-101660899-11260306
# Turquoise category Link ID 11272766 — $147.62 EPC (highest for this partner)
#   Base: https://www.kqzyfj.com/click-101660899-11272766
# Commission: 15%, 60-day referral period (generous)
# AOV: ~$114, handmade artisan sterling silver gemstone jewelry, 10,000+ designs
# T&C:
#   - Public coupon codes are permitted (very clean T&C)
#   - No SEM bidding on trademark terms only
#   - Ships worldwide; 100% US conversions
# ---------------------------------------------------------------------------

_SILVERRUSHSTYLE_ALL_PRODUCTS = [
    {
        # Link 11272766 — Turquoise category ($147.62 EPC — best performing link)
        'title': "SilverRushStyle — Handcrafted Turquoise Sterling Silver Jewelry",
        'link': 'https://www.kqzyfj.com/click-101660899-11272766',
        'snippet': (
            "Artisan-crafted sterling silver jewelry featuring genuine turquoise, "
            "coral, and other natural gemstones. Over 10,000 handmade designs — "
            "rings, pendants, earrings, and bracelets. Each piece is one-of-a-kind."
        ),
        'image': '',
        'thumbnail': '',
        'image_url': '',
        'source_domain': 'silverrushstyle.com',
        'price': 'From $30',
        'product_id': 'silverrushstyle-turquoise',
        'search_query': 'turquoise sterling silver gemstone jewelry handmade',
        'interest_match': 'jewelry',
        'interest_matches': {
            'jewelry', 'turquoise', 'gemstones', 'crystals', 'minerals',
            'bohemian', 'boho', 'southwest', 'artisan', 'handmade',
            'silver jewelry', 'accessories', 'fashion', 'nature',
        },
        'priority': 2,
        'brand': 'SilverRushStyle',
        'advertiser_id': 'silverrushstyle-cj',
    },
    {
        # Link 11260306 — Home page ($16.79 EPC — broad gemstone jewelry)
        'title': "SilverRushStyle — Artisan Sterling Silver Gemstone Jewelry",
        'link': 'https://www.kqzyfj.com/click-101660899-11260306',
        'snippet': (
            "10,000+ handcrafted sterling silver jewelry pieces featuring genuine "
            "gemstones — amethyst, labradorite, moonstone, opal, and more. "
            "Unique artisan gifts that can't be found in mainstream stores."
        ),
        'image': '',
        'thumbnail': '',
        'image_url': '',
        'source_domain': 'silverrushstyle.com',
        'price': 'From $25',
        'product_id': 'silverrushstyle-home',
        'search_query': 'artisan sterling silver gemstone jewelry gift',
        'interest_match': 'jewelry',
        'interest_matches': {
            'jewelry', 'gemstones', 'crystals', 'minerals', 'amethyst',
            'labradorite', 'moonstone', 'opal', 'bohemian', 'boho',
            'artisan', 'handmade', 'silver jewelry', 'accessories',
            'fashion', 'witchy', 'spiritual', 'nature',
        },
        'priority': 2,
        'brand': 'SilverRushStyle',
        'advertiser_id': 'silverrushstyle-cj',
    },
]

_SILVERRUSHSTYLE_TRIGGER_INTERESTS = {
    'jewelry', 'accessories', 'fashion', 'gemstones', 'crystals', 'minerals',
    'turquoise', 'amethyst', 'labradorite', 'moonstone', 'opal',
    'bohemian', 'boho', 'southwest', 'artisan', 'handmade',
    'silver jewelry', 'witchy', 'spiritual', 'nature',
}


def get_silverrushstyle_products_for_profile(profile):
    """
    Return SilverRushStyle products when the profile has jewelry/gemstone interests.

    Static list using direct CJ click URLs. ADV_CID: 3874186.
    Commission: 15%, 60-day cookie. ~$114 AOV, 10,000+ handmade designs.
    Best link: Turquoise category (link 11272766, $147.62 EPC).

    T&C: Very clean — public coupon codes allowed; no SEM trademark bidding only.

    Returns at most 2 products — turquoise first when profile signals that interest.
    """
    interests = profile.get('interests', [])
    interest_names = {i.get('name', '').lower() for i in interests if i.get('name')}

    scored = []
    for p in _SILVERRUSHSTYLE_ALL_PRODUCTS:
        score = 0
        for key in p.get('interest_matches', set()):
            if key in interest_names:
                score += 2
            elif any(key in n or n in key for n in interest_names):
                score += 1
        # Require at least one exact match (score >= 2) — substring-only hits like
        # 'fashion' inside 'vintage fashion' are not specific enough for fine jewelry.
        if score >= 2:
            scored.append((score, p))

    if not scored:
        return []

    scored.sort(key=lambda x: -x[0])
    result = [p for _, p in scored[:2]]
    logger.info(f"SilverRushStyle: {len(result)} products matched profile interests {interest_names & _SILVERRUSHSTYLE_TRIGGER_INTERESTS}")
    return result


def get_groundluxe_products_for_profile(profile):
    """
    Return GroundLuxe products when the profile has wellness/sleep interests.

    Static list using direct CJ click URLs. ADV_CID: 7681501.
    Commission: 10%, 30-day cookie. Highest EPC in the static partner stack.

    NOTE: Write copy as earthing/grounding wellness — do NOT make specific
    medical claims ("proven to reduce pain") in publisher-generated content.

    Returns at most 1-2 products scored by interest match.
    """
    interests = profile.get('interests', [])
    interest_names = {i.get('name', '').lower() for i in interests if i.get('name')}

    scored = []
    for p in _GROUNDLUXE_ALL_PRODUCTS:
        score = 0
        for key in p.get('interest_matches', set()):
            if key in interest_names:
                score += 2
            elif any(key in n or n in key for n in interest_names):
                score += 1
        if score > 0:
            scored.append((score, p))

    if not scored:
        return []

    scored.sort(key=lambda x: -x[0])
    result = [p for _, p in scored[:2]]
    logger.info(f"GroundLuxe: {len(result)} products matched profile interests {interest_names & _GROUNDLUXE_TRIGGER_INTERESTS}")
    return result


def get_greatergood_products_for_profile(profile):
    """
    Return GreaterGood products when the profile has matching interests.

    Best for animal lovers (dog/cat parents) and cause-oriented buyers.
    Static list using direct CJ click URLs. ADV_CID: 4046728.
    Commission: 2% baseline, up to 10-15% on Animal Rescue Site items.

    Returns at most 1 product — this is a narrow niche trigger.
    """
    interests = profile.get('interests', [])
    interest_names = {i.get('name', '').lower() for i in interests if i.get('name')}

    scored = []
    for p in _GREATERGOOD_ALL_PRODUCTS:
        score = 0
        for key in p.get('interest_matches', set()):
            if key in interest_names:
                score += 2
            elif any(key in n or n in key for n in interest_names):
                score += 1
        if score > 0:
            scored.append((score, p))

    if not scored:
        return []

    scored.sort(key=lambda x: -x[0])
    result = [p for _, p in scored[:1]]  # Max 1 — narrow niche
    logger.info(f"GreaterGood: {len(result)} products matched profile interests {interest_names & _GREATERGOOD_TRIGGER_INTERESTS}")
    return result


def get_gamefly_products_for_profile(profile):
    """
    Return GameFly products when the profile has matching gaming interests.

    Static list using direct CJ click URLs. ADV_CID: 1132500.
    Commission: $5/lead for subscriptions, 10% on used games/accessories.
    NOTE: 0% commission on new games — only recommend rental or used game purchase.

    Returns at most 1-2 products scored by interest match.
    """
    interests = profile.get('interests', [])
    interest_names = {i.get('name', '').lower() for i in interests if i.get('name')}

    scored = []
    for p in _GAMEFLY_ALL_PRODUCTS:
        score = 0
        for key in p.get('interest_matches', set()):
            if key in interest_names:
                score += 2
            elif any(key in n or n in key for n in interest_names):
                score += 1
        if score > 0:
            scored.append((score, p))

    if not scored:
        return []

    scored.sort(key=lambda x: -x[0])
    # For gaming profiles, return both products; otherwise just the subscription
    result = [p for _, p in scored[:2]]
    logger.info(f"GameFly: {len(result)} products matched profile interests {interest_names & _GAMEFLY_TRIGGER_INTERESTS}")
    return result


def get_fragranceshop_products_for_profile(profile):
    """
    Return FragranceShop products when the profile has matching interests.

    Static list using direct CJ click URLs. ADV_CID: 7287203.
    Commission: 5%, 45-day cookie. Deep-link enabled via Evergreen link.

    T&C: Do not claim "authorized wholesaler" or "official site".
    Do not use outdated discount percentages. Only CJ-provided coupon codes.

    Returns at most 2 products scored by interest match.
    """
    interests = profile.get('interests', [])
    interest_names = {i.get('name', '').lower() for i in interests if i.get('name')}

    scored = []
    for p in _FRAGRANCESHOP_ALL_PRODUCTS:
        score = 0
        for key in p.get('interest_matches', set()):
            if key in interest_names:
                score += 2
            elif any(key in n or n in key for n in interest_names):
                score += 1
        # Require at least one exact match (score >= 2) — 'fashion' as substring of
        # 'vintage fashion' is not a signal that someone wants perfume.
        if score >= 2:
            scored.append((score, p))

    if not scored:
        return []

    scored.sort(key=lambda x: -x[0])
    result = [p for _, p in scored[:2]]
    logger.info(f"FragranceShop: {len(result)} products matched profile interests {interest_names & _FRAGRANCESHOP_TRIGGER_INTERESTS}")
    return result


def get_flowersfast_products_for_profile(profile):
    """
    Return FlowersFast products when the profile has matching interests.

    Static list using direct CJ click URLs. ADV_CID: 231679.
    Commission: 20%, 45-day cookie. AOV: ~$65.

    T&C: Do NOT use "FTD" or "Teleflora" trademarks in any publisher copy.
    No coupon codes currently available through CJ.

    Returns at most 2 products scored by interest match.
    """
    interests = profile.get('interests', [])
    interest_names = {i.get('name', '').lower() for i in interests if i.get('name')}

    scored = []
    for p in _FLOWERSFAST_ALL_PRODUCTS:
        score = 0
        for key in p.get('interest_matches', set()):
            if key in interest_names:
                score += 2
            elif any(key in n or n in key for n in interest_names):
                score += 1
        if score > 0:
            scored.append((score, p))

    if not scored:
        return []

    scored.sort(key=lambda x: -x[0])
    result = [p for _, p in scored[:2]]
    logger.info(f"FlowersFast: {len(result)} products matched profile interests {interest_names & _FLOWERSFAST_TRIGGER_INTERESTS}")
    return result


# ---------------------------------------------------------------------------
# SOCCERGARAGE.COM — Static curated products (approved CJ partner, Feb 2026)
# ADV_CID: 2061630
# Commission: 7% base (scales to 8/9/10% at $3.5K/$5.5K/$7.5K monthly sales)
# Cookie: 60 days (locking: 40 days) | AOV: ~$125 | US only
#
# No product feed — category/text links only.
# T&C: No SEM bidding on brand terms (irrelevant). No expired coupons
#   (2012-era coupon codes 5C4J2U / GARAGE10 are stale — do NOT use).
# ---------------------------------------------------------------------------

_SOCCERGARAGE_ALL_PRODUCTS = [
    {
        # Link ID 10479694 — Soccer Shoes category page
        'title': "Soccer Cleats & Shoes — SoccerGarage.com",
        'link': 'https://www.tkqlhce.com/click-101660899-10479694',
        'snippet': (
            "One of the largest online soccer retailers in the US — adidas, New Balance, "
            "Diadora, and more. Full range of cleats for firm ground, turf, and indoor play. "
            "Free shipping on orders over $150."
        ),
        'image': '',
        'thumbnail': '',
        'image_url': '',
        'source_domain': 'soccergarage.com',
        'price': 'From $30.00',
        'product_id': 'soccergarage-cleats',
        'search_query': 'soccer cleats gift',
        'interest_match': 'soccer',
        'priority': 2,
        'brand': 'SoccerGarage.com',
        'advertiser_id': 'soccergarage-cj',
    },
    {
        # Link ID 11017728 — Goalkeeper Soccer Sale (keeper-specific)
        'title': "Goalkeeper Gloves & Equipment — SoccerGarage.com",
        'link': 'https://www.anrdoezrs.net/click-101660899-11017728',
        'snippet': (
            "Full goalkeeper shop — Reusch, Storelli, and more. Gloves, chest protectors, "
            "training gear, and positional coaching equipment. Trusted by club keepers nationwide."
        ),
        'image': '',
        'thumbnail': '',
        'image_url': '',
        'source_domain': 'soccergarage.com',
        'price': 'From $25.00',
        'product_id': 'soccergarage-goalkeeper',
        'search_query': 'goalkeeper gear gift',
        'interest_match': 'goalkeeper',
        'priority': 2,
        'brand': 'SoccerGarage.com',
        'advertiser_id': 'soccergarage-cj',
    },
    {
        # Link ID 11017023 — Youth soccer gear
        'title': "Youth Soccer Gear — SoccerGarage.com",
        'link': 'https://www.dpbolvw.net/click-101660899-11017023',
        'snippet': (
            "Everything a young player needs — youth cleats, balls, shin guards, bags, "
            "and uniforms. All the top brands in kids' sizes. Ships to teams and clubs too."
        ),
        'image': '',
        'thumbnail': '',
        'image_url': '',
        'source_domain': 'soccergarage.com',
        'price': 'From $15.00',
        'product_id': 'soccergarage-youth',
        'search_query': 'youth soccer gear gift',
        'interest_match': 'youth soccer',
        'priority': 2,
        'brand': 'SoccerGarage.com',
        'advertiser_id': 'soccergarage-cj',
    },
    {
        # Link ID 10479704 — Evergreen homepage (general / browse)
        'title': "Soccer Equipment & Apparel — SoccerGarage.com",
        'link': 'https://www.tkqlhce.com/click-101660899-10479704',
        'snippet': (
            "The go-to online source for soccer players, teams, and clubs. "
            "Cleats, balls, jerseys, bags, goals, and training gear — "
            "all the top brands in one place. Free shipping on orders over $150."
        ),
        'image': '',
        'thumbnail': '',
        'image_url': '',
        'source_domain': 'soccergarage.com',
        'price': 'From $15.00',
        'product_id': 'soccergarage-home',
        'search_query': 'soccer gear gift',
        'interest_match': 'soccer',
        'priority': 2,
        'brand': 'SoccerGarage.com',
        'advertiser_id': 'soccergarage-cj',
    },
]

_SOCCERGARAGE_TRIGGER_INTERESTS = {
    'soccer', 'football', 'futbol', 'soccer player', 'soccer fan',
    'goalkeeper', 'goalie', 'keeper', 'soccer coach', 'coaching soccer',
    'youth soccer', 'kids soccer', 'soccer dad', 'soccer mom',
    'mls', 'premier league', 'champions league', 'la liga', 'bundesliga',
    'world cup', 'fifa', 'sports', 'athletic', 'team sports',
}

# Goalkeeper-specific interests — trigger the keeper product instead of general cleats
_SOCCERGARAGE_GOALKEEPER_INTERESTS = {
    'goalkeeper', 'goalie', 'keeper', 'soccer goalkeeper',
}

# Youth-specific signals — trigger youth gear product
_SOCCERGARAGE_YOUTH_INTERESTS = {
    'youth soccer', 'kids soccer', 'soccer dad', 'soccer mom',
    'youth sports', 'kids sports', 'parenting',
}


# ---------------------------------------------------------------------------
# TECH FOR LESS — Static curated products (approved CJ partner, Feb 2026)
# ADV_CID: 3297514
# Commission: 5% | Cookie: 14 days (locking: 60 days) | AOV: ~$185
# Serviceable: US, Canada, UK (effectively US-only per conversion data)
#
# Positioning: New, open box, and certified refurbished electronics —
#   same tech at 10-50% below retail. One of the web's highest-rated
#   refurb merchants (Amazon, Bizrate, PriceGrabber). In business since 2001.
#
# No product feed — category text links only.
# Deep-link enabled: Evergreen link ID 15733604
#   Base: https://www.kqzyfj.com/click-101660899-15733604
#   Deep-link: append ?url=encoded_destination
#
# T&C: Coupons only through CJ affiliate program interface (none currently
#   available). No SEM bidding on brand terms. Direct linking allowed.
# DO NOT use link 10891878 (explicitly labeled "DO NOT USE" by advertiser).
# ---------------------------------------------------------------------------

_TFL_EVERGREEN_BASE = "https://www.kqzyfj.com/click-101660899-15733604"


def _tfl_deep_link(path):
    """Build a CJ deep link to a specific techforless.com page."""
    destination = f"https://www.techforless.com{path}"
    return f"{_TFL_EVERGREEN_BASE}?url={urllib.parse.quote(destination, safe='')}"


_TFL_ALL_PRODUCTS = [
    {
        # Link ID 10886632 — Laptops (updated May 2023)
        'title': "Laptops & Notebooks — New & Open Box at TechForLess",
        'link': 'https://www.kqzyfj.com/click-101660899-10886632',
        'snippet': (
            "HP, Lenovo, Dell, and more — new, open box, and certified refurbished laptops "
            "at 10-50% below retail. Same technology, thoroughly tested. "
            "8,000+ items in stock, free shipping on thousands of items."
        ),
        'image': '',
        'thumbnail': '',
        'image_url': '',
        'source_domain': 'techforless.com',
        'price': 'From $150.00',
        'product_id': 'tfl-laptops',
        'search_query': 'laptop gift',
        'interest_match': 'technology',
        'priority': 2,
        'brand': 'Tech For Less',
        'advertiser_id': 'techforless-cj',
    },
    {
        # Link ID 15443907 — Apple MacBooks (updated Jan 2023, $9.15 EPC)
        'title': "MacBook Laptops — New & Open Box at TechForLess",
        'link': 'https://www.dpbolvw.net/click-101660899-15443907',
        'snippet': (
            "New and open box Apple MacBook and MacBook Air — same Apple hardware, "
            "10-50% below Apple Store pricing. Thoroughly tested, limited quantities. "
            "One of the web's highest-rated sources for open box Apple gear."
        ),
        'image': '',
        'thumbnail': '',
        'image_url': '',
        'source_domain': 'techforless.com',
        'price': 'From $400.00',
        'product_id': 'tfl-macbooks',
        'search_query': 'MacBook laptop gift',
        'interest_match': 'apple',
        'priority': 2,
        'brand': 'Tech For Less',
        'advertiser_id': 'techforless-cj',
    },
    {
        # Link ID 13446839 — Video Game Consoles & Accessories
        'title': "Video Game Consoles & Accessories — TechForLess",
        'link': 'https://www.anrdoezrs.net/click-101660899-13446839',
        'snippet': (
            "Gaming consoles and accessories — new, open box, and refurbished at "
            "significant savings. Controllers, headsets, and more from major brands. "
            "Free shipping on thousands of items."
        ),
        'image': '',
        'thumbnail': '',
        'image_url': '',
        'source_domain': 'techforless.com',
        'price': 'From $30.00',
        'product_id': 'tfl-gaming',
        'search_query': 'gaming console gift',
        'interest_match': 'gaming',
        'priority': 2,
        'brand': 'Tech For Less',
        'advertiser_id': 'techforless-cj',
    },
    {
        # Link ID 13446829 — Cameras (DSLR to webcams)
        'title': "Cameras — DSLR, Mirrorless & More at TechForLess",
        'link': 'https://www.kqzyfj.com/click-101660899-13446829',
        'snippet': (
            "DSLR, mirrorless, and point-and-shoot cameras — new and open box at "
            "10-50% below retail. Also webcams, lenses, and accessories. "
            "Thoroughly tested by one of the web's top-rated electronics resellers."
        ),
        'image': '',
        'thumbnail': '',
        'image_url': '',
        'source_domain': 'techforless.com',
        'price': 'From $75.00',
        'product_id': 'tfl-cameras',
        'search_query': 'camera gift',
        'interest_match': 'photography',
        'priority': 2,
        'brand': 'Tech For Less',
        'advertiser_id': 'techforless-cj',
    },
    {
        # Link ID 13067706 — Homepage ($6.88 EPC, evergreen)
        'title': "Computers & Electronics — Same Technology, Lower Prices",
        'link': 'https://www.dpbolvw.net/click-101660899-13067706',
        'snippet': (
            "TechForLess.com — new, open box, and certified refurbished computers, "
            "tablets, monitors, and electronics at 10-50% below retail. "
            "In business since 2001, one of the web's highest-rated tech retailers."
        ),
        'image': '',
        'thumbnail': '',
        'image_url': '',
        'source_domain': 'techforless.com',
        'price': 'From $15.00',
        'product_id': 'tfl-home',
        'search_query': 'electronics gift',
        'interest_match': 'technology',
        'priority': 2,
        'brand': 'Tech For Less',
        'advertiser_id': 'techforless-cj',
    },
]

_TFL_TRIGGER_INTERESTS = {
    'technology', 'tech', 'gadgets', 'electronics', 'computers', 'computing',
    'laptops', 'coding', 'programming', 'software', 'hardware',
    # 'it' removed — 2-letter string matches as substring inside 'productivity',
    # 'literature', etc., causing false triggers on unrelated profiles.
    'home office', 'remote work', 'work from home', 'streaming',
    'content creation', 'youtube', 'twitch', 'podcasting',
    'gaming', 'video games', 'pc gaming', 'esports',
    'photography', 'camera', 'filmmaker', 'videography',
    'apple', 'mac', 'macbook', 'ipad',
}

_TFL_GAMING_INTERESTS = {
    'gaming', 'video games', 'pc gaming', 'esports', 'game', 'gamer',
    'playstation', 'xbox', 'nintendo', 'console gaming',
}

_TFL_PHOTOGRAPHY_INTERESTS = {
    'photography', 'camera', 'filmmaker', 'videography', 'photo',
    'dslr', 'mirrorless', 'film photography', 'content creation',
}

_TFL_APPLE_INTERESTS = {
    'apple', 'mac', 'macbook', 'ipad', 'ios', 'apple ecosystem',
}


def get_techforless_products_for_profile(profile):
    """
    Return curated Tech For Less products when the profile has tech interest.

    No product feed — static list using category text link IDs.
    Commission: 5%, 14-day cookie. AOV ~$185.
    Specializes in new, open box, and certified refurbished electronics.

    Smart selection (cap 2):
    - Gaming profile → gaming consoles + laptops
    - Photography profile → cameras + general
    - Apple/Mac profile → MacBooks + general
    - General tech → laptops + general homepage

    T&C: No external coupons. Do NOT use link 10891878 (labeled DO NOT USE).
    """
    interests = profile.get('interests', [])
    interest_names = {i.get('name', '').lower() for i in interests if i.get('name')}

    matched = interest_names & _TFL_TRIGGER_INTERESTS
    if not matched:
        for name in interest_names:
            for trigger in _TFL_TRIGGER_INTERESTS:
                # Require trigger to be at least 4 chars before substring matching —
                # short strings like 'mac' can still false-match, but 2-3 char ones
                # like 'it' would embed in unrelated words ('productivity', 'literature').
                if len(trigger) >= 4 and (trigger in name or name in trigger):
                    matched.add(name)
                    break

    if not matched:
        return []

    logger.info(f"Tech For Less triggered by profile interests: {matched}")

    is_gaming = bool(interest_names & _TFL_GAMING_INTERESTS) or any(
        'gam' in n or 'xbox' in n or 'playstation' in n or 'nintendo' in n
        for n in interest_names
    )
    is_photography = bool(interest_names & _TFL_PHOTOGRAPHY_INTERESTS) or any(
        'photo' in n or 'camera' in n or 'film' in n for n in interest_names
    )
    is_apple = bool(interest_names & _TFL_APPLE_INTERESTS) or any(
        'apple' in n or 'mac' in n or 'ipad' in n for n in interest_names
    )

    def _get(pid):
        return next((p for p in _TFL_ALL_PRODUCTS if p['product_id'] == pid), None)

    if is_gaming:
        return [p for p in [_get('tfl-gaming'), _get('tfl-laptops')] if p]
    elif is_photography:
        return [p for p in [_get('tfl-cameras'), _get('tfl-home')] if p]
    elif is_apple:
        return [p for p in [_get('tfl-macbooks'), _get('tfl-home')] if p]
    else:
        return [p for p in [_get('tfl-laptops'), _get('tfl-home')] if p]


# ---------------------------------------------------------------------------
# TENERGY — Static curated products (approved CJ partner, Feb 2026)
# ADV_CID: 1826017
# Commission: 8% | Cookie: 30 days | EPC: $11.64 (3-mo) / $13.09 (7-day)
# Two sites: power.tenergy.com (batteries/chargers) | life.tenergy.com (appliances)
#
# No product feed — Evergreen link ID 15733324 is deep-link enabled.
#   Base: https://www.anrdoezrs.net/click-101660899-15733324
#   Deep-link: append ?url=encoded_destination
#
# Promo code THANKS: free ground shipping on orders $50+ (lower 48 states).
#   Sourced from official CJ affiliate materials — treat as evergreen until
#   it stops working. Do NOT stack with other promo codes.
#
# T&C: No SEM bidding on brand terms (irrelevant for content). No obscene,
#   harmful, or discriminatory site content.
# ---------------------------------------------------------------------------

_TENERGY_EVERGREEN_BASE = "https://www.anrdoezrs.net/click-101660899-15733324"


def _tenergy_deep_link(path, site='power'):
    """Build a CJ deep link to a specific Tenergy page.

    Args:
        path: URL path (e.g., '/collections/aa-batteries')
        site: 'power' for power.tenergy.com or 'life' for life.tenergy.com
    """
    destination = f"https://{site}.tenergy.com{path}"
    return f"{_TENERGY_EVERGREEN_BASE}?url={urllib.parse.quote(destination, safe='')}"


_TENERGY_ALL_PRODUCTS = [
    {
        # Deep-link → Tenergy Power homepage (rechargeable batteries for home)
        'title': "Rechargeable AA/AAA Battery Kit — Tenergy Power",
        'link': _tenergy_deep_link('/'),
        'snippet': (
            "Tenergy rechargeable NiMH batteries and smart chargers — high-capacity AA and AAA "
            "for remotes, cameras, toys, and everyday devices. American brand since 2004. "
            "Use code THANKS for free shipping on orders $50+."
        ),
        'image': '',
        'thumbnail': '',
        'image_url': '',
        'source_domain': 'power.tenergy.com',
        'price': 'From $20.00',
        'product_id': 'tenergy-rechargeable',
        'search_query': 'rechargeable battery kit gift',
        'interest_match': 'sustainability',
        'priority': 2,
        'brand': 'Tenergy',
        'advertiser_id': 'tenergy-cj',
    },
    {
        # Deep-link → Tenergy RC/hobby battery category
        'title': "RC Hobby & Drone Batteries — Tenergy Power",
        'link': _tenergy_deep_link('/collections/hobby-rc'),
        'snippet': (
            "High-performance LiPo, NiMH, and NiCd packs for RC cars, trucks, boats, "
            "airsoft AEGs, and drones. Tenergy is the go-to brand for hobbyists who need "
            "reliable power. Use code THANKS for free shipping on orders $50+."
        ),
        'image': '',
        'thumbnail': '',
        'image_url': '',
        'source_domain': 'power.tenergy.com',
        'price': 'From $25.00',
        'product_id': 'tenergy-rc-hobby',
        'search_query': 'RC car battery gift',
        'interest_match': 'rc cars',
        'priority': 2,
        'brand': 'Tenergy',
        'advertiser_id': 'tenergy-cj',
    },
    {
        # Deep-link → Tenergy Life homepage (small kitchen/home appliances)
        'title': "Kitchen & Home Appliances — Tenergy Life",
        'link': _tenergy_deep_link('/', site='life'),
        'snippet': (
            "Tenergy Life — small kitchen appliances and home electronics built to the same "
            "exacting standard as their battery line. Blenders, air fryers, toasters, and more. "
            "Use code THANKS for free shipping on orders $50+."
        ),
        'image': '',
        'thumbnail': '',
        'image_url': '',
        'source_domain': 'life.tenergy.com',
        'price': 'From $30.00',
        'product_id': 'tenergy-life-appliances',
        'search_query': 'kitchen appliance gift',
        'interest_match': 'cooking',
        'priority': 2,
        'brand': 'Tenergy',
        'advertiser_id': 'tenergy-cj',
    },
    {
        # Evergreen base → general Power site (smart chargers + batteries)
        'title': "Smart Battery Charger & Batteries — Tenergy Power",
        'link': _TENERGY_EVERGREEN_BASE,
        'snippet': (
            "Tenergy smart chargers with AA, AAA, C, and D rechargeable batteries — "
            "the practical gift that pays for itself. Trusted for photography, RC hobbies, "
            "and everyday devices. Use code THANKS for free shipping on orders $50+."
        ),
        'image': '',
        'thumbnail': '',
        'image_url': '',
        'source_domain': 'power.tenergy.com',
        'price': 'From $30.00',
        'product_id': 'tenergy-charger-kit',
        'search_query': 'battery charger gift',
        'interest_match': 'gadgets',
        'priority': 2,
        'brand': 'Tenergy',
        'advertiser_id': 'tenergy-cj',
    },
]

_TENERGY_TRIGGER_INTERESTS = {
    # RC / hobby
    'rc cars', 'remote control', 'radio controlled', 'rc trucks', 'rc boats',
    'rc helicopters', 'rc planes', 'hobby rc', 'model cars',
    # Airsoft / tactical
    'airsoft', 'airsoft guns', 'tactical',
    # Drone
    'drones', 'drone', 'quadcopter', 'fpv', 'fpv racing',
    # Photography (camera flash batteries)
    'photography', 'camera', 'flash photography',
    # Sustainability / eco
    'sustainability', 'eco-friendly', 'green living', 'zero waste', 'environment',
    # Kitchen / home
    'cooking', 'baking', 'kitchen', 'home cooking', 'meal prep',
    # General tech/gadgets that may need lots of batteries
    'gadgets', 'smart home', 'robotics',
}

_TENERGY_RC_INTERESTS = {
    'rc cars', 'remote control', 'radio controlled', 'rc trucks', 'rc boats',
    'rc helicopters', 'rc planes', 'hobby rc', 'model cars',
    'airsoft', 'drones', 'drone', 'quadcopter', 'fpv', 'fpv racing',
}

_TENERGY_KITCHEN_INTERESTS = {
    'cooking', 'baking', 'kitchen', 'home cooking', 'meal prep', 'air fryer',
    'homemaker', 'food', 'culinary',
}


def get_tenergy_products_for_profile(profile):
    """
    Return curated Tenergy products when the profile has matching interests.

    No product feed — static list using CJ deep links off Evergreen ID 15733324.
    Commission: 8%, 30-day cookie. Strong EPC ($13).

    Smart selection (cap 2):
    - RC/airsoft/drone profile → RC batteries + charger kit
    - Kitchen/home profile → Life appliances + rechargeable
    - General eco/gadget → rechargeable kit + charger kit

    Promo code THANKS = free ground shipping $50+ (lower 48 states only).
    """
    interests = profile.get('interests', [])
    interest_names = {i.get('name', '').lower() for i in interests if i.get('name')}

    matched = interest_names & _TENERGY_TRIGGER_INTERESTS
    if not matched:
        for name in interest_names:
            for trigger in _TENERGY_TRIGGER_INTERESTS:
                if trigger in name or name in trigger:
                    matched.add(name)
                    break

    if not matched:
        return []

    logger.info(f"Tenergy triggered by profile interests: {matched}")

    is_rc_or_drone = bool(interest_names & _TENERGY_RC_INTERESTS) or any(
        'rc' in n or 'drone' in n or 'airsoft' in n or 'quadcopter' in n
        or 'remote control' in n or 'fpv' in n
        for n in interest_names
    )
    is_kitchen = bool(interest_names & _TENERGY_KITCHEN_INTERESTS) or any(
        'cook' in n or 'bak' in n or 'kitchen' in n for n in interest_names
    )

    def _get(pid):
        return next((p for p in _TENERGY_ALL_PRODUCTS if p['product_id'] == pid), None)

    if is_rc_or_drone:
        return [p for p in [_get('tenergy-rc-hobby'), _get('tenergy-charger-kit')] if p]
    elif is_kitchen:
        return [p for p in [_get('tenergy-life-appliances'), _get('tenergy-rechargeable')] if p]
    else:
        return [p for p in [_get('tenergy-rechargeable'), _get('tenergy-charger-kit')] if p]


# ---------------------------------------------------------------------------
# TRINITY ROAD WEBSITES (The Catholic Company) — Static curated products
# Approved CJ partner, Feb 2026 | ADV_CID: 2871603
# Commission: 8% across all sites | Cookie: 30-45 days
# EPC: $2.66 (3-mo) / $2.27 (7-day)
# Sites: catholiccompany.com (main), catholiccoffee.com, thankgodforcoffee.com,
#        goodcatholic.com, jlily.com, rosary.com
#
# No product feed — category text links + deep links to catholiccompany.com.
# Deep link ID 12058792 for catholiccompany.com (use for custom landing pages).
# Free shipping on orders $75+. 20,000+ items.
#
# T&C: Coupons only through CJ affiliate program. No external coupon codes.
#   The "15% off first order" link (13286183) IS CJ-provided — valid to promote.
#   Do NOT use RetailMeNot co-brand links (12666306, 13424511) — those are for
#   RetailMeNot publishers only. No brand SEM bidding (irrelevant for content).
#   Affiliates may not represent themselves as any Trinity Road brand.
#
# Key occasions: First Communion, Confirmation, Baptism/Christening, Christmas,
#   Easter, Catholic wedding, Lent. These are high-intent milestone gift moments.
# ---------------------------------------------------------------------------

_CATHOLICCO_DEEP_LINK_BASE = "https://www.tkqlhce.com/click-101660899-12058792"


def _catholicco_deep_link(path):
    """Build a CJ deep link to a specific catholiccompany.com page."""
    destination = f"https://www.catholiccompany.com{path}"
    return f"{_CATHOLICCO_DEEP_LINK_BASE}?url={urllib.parse.quote(destination, safe='')}"


_TRINITYROAD_ALL_PRODUCTS = [
    {
        # Link ID 10753028 — General Catholic Books & Gifts ($12.43 EPC)
        'title': "Catholic Books & Gifts — The Catholic Company",
        'link': 'https://www.anrdoezrs.net/click-101660899-10753028',
        'snippet': (
            "The world's #1 Catholic store — 20,000+ Catholic books, rosaries, jewelry, "
            "art, and gifts. Patron saint medals, personalized items, and sacramental gifts "
            "for every occasion. Free shipping on orders $75+."
        ),
        'image': '',
        'thumbnail': '',
        'image_url': '',
        'source_domain': 'catholiccompany.com',
        'price': 'From $8.00',
        'product_id': 'catholicco-gifts',
        'search_query': 'Catholic gifts',
        'interest_match': 'catholicism',
        'priority': 2,
        'brand': 'The Catholic Company',
        'advertiser_id': 'trinityroad-cj',
    },
    {
        # Link ID 13291163 — Exclusive Rosaries ($14.09 EPC)
        'title': "Catholic Company Exclusive Rosaries",
        'link': 'https://www.jdoqocy.com/click-101660899-13291163',
        'snippet': (
            "Beautifully crafted rosaries — sterling silver, heirloom wood, crystal, and "
            "handmade artisan styles. Catholic Company exclusive designs not found elsewhere. "
            "A timeless and meaningful gift for any occasion. Free shipping on orders $75+."
        ),
        'image': '',
        'thumbnail': '',
        'image_url': '',
        'source_domain': 'catholiccompany.com',
        'price': 'From $15.00',
        'product_id': 'catholicco-rosary',
        'search_query': 'Catholic rosary gift',
        'interest_match': 'catholicism',
        'priority': 2,
        'brand': 'The Catholic Company',
        'advertiser_id': 'trinityroad-cj',
    },
    {
        # Link ID 13286147 — First Holy Communion Gifts (personalization available)
        'title': "First Holy Communion Gifts — The Catholic Company",
        'link': 'https://www.anrdoezrs.net/click-101660899-13286147',
        'snippet': (
            "Curated gifts for First Holy Communion — personalized rosaries, keepsake bibles, "
            "jewelry, prayer cards, and keepsakes. Many items can be engraved or personalized. "
            "Free shipping on orders $75+."
        ),
        'image': '',
        'thumbnail': '',
        'image_url': '',
        'source_domain': 'catholiccompany.com',
        'price': 'From $12.00',
        'product_id': 'catholicco-communion',
        'search_query': 'First Communion gift',
        'interest_match': 'first communion',
        'priority': 2,
        'brand': 'The Catholic Company',
        'advertiser_id': 'trinityroad-cj',
    },
    {
        # Link ID 13286185 — Confirmation Gifts
        'title': "Confirmation Gifts — The Catholic Company",
        'link': 'https://www.kqzyfj.com/click-101660899-13286185',
        'snippet': (
            "Gifts for the sacrament of Confirmation — saint medals, personalized crosses, "
            "bibles, jewelry, and keepsake items. Celebrate this milestone with a meaningful, "
            "lasting gift. Free shipping on orders $75+."
        ),
        'image': '',
        'thumbnail': '',
        'image_url': '',
        'source_domain': 'catholiccompany.com',
        'price': 'From $12.00',
        'product_id': 'catholicco-confirmation',
        'search_query': 'Catholic Confirmation gift',
        'interest_match': 'confirmation',
        'priority': 2,
        'brand': 'The Catholic Company',
        'advertiser_id': 'trinityroad-cj',
    },
    {
        # Link ID 13286177 — Baby Baptism and Christening Gifts
        'title': "Baby Baptism & Christening Gifts — The Catholic Company",
        'link': 'https://www.kqzyfj.com/click-101660899-13286177',
        'snippet': (
            "Baptism and christening keepsakes — personalized water bottles, godparent gifts, "
            "guardian angel pillowcases, rosaries, and Catholic baby items. "
            "Meaningful gifts for a child's first sacrament. Free shipping on orders $75+."
        ),
        'image': '',
        'thumbnail': '',
        'image_url': '',
        'source_domain': 'catholiccompany.com',
        'price': 'From $10.00',
        'product_id': 'catholicco-baptism',
        'search_query': 'Catholic baptism gift',
        'interest_match': 'baptism',
        'priority': 2,
        'brand': 'The Catholic Company',
        'advertiser_id': 'trinityroad-cj',
    },
    {
        # Link ID 15590515 — Catholic Coffee Main (US only)
        'title': "Catholic Coffee — Heavenly Roasts",
        'link': 'https://www.kqzyfj.com/click-101660899-15590515',
        'snippet': (
            "Faith-inspired specialty coffee from Catholic Coffee — uniquely named roasts "
            "that make a conversation-starting gift for the Catholic coffee lover in your life. "
            "Rich, carefully sourced blends with a sense of humor."
        ),
        'image': '',
        'thumbnail': '',
        'image_url': '',
        'source_domain': 'catholiccoffee.com',
        'price': 'From $14.00',
        'product_id': 'catholicco-coffee',
        'search_query': 'Catholic coffee gift',
        'interest_match': 'coffee',
        'priority': 2,
        'brand': 'Catholic Coffee',
        'advertiser_id': 'trinityroad-cj',
    },
    {
        # Link ID 13291965 — "Drinking with the Saints" Book & Bar Towel Gift Set
        'title': '"Drinking with the Saints" Book & Bar Towel Gift Set',
        'link': 'https://www.jdoqocy.com/click-101660899-13291965',
        'snippet': (
            "The beloved Catholic drinking guide meets bar towel — the perfect gift for "
            "Catholics who appreciate a good cocktail and a great story. "
            "Recipes, saint stories, and liturgical humor in one irreverent package."
        ),
        'image': '',
        'thumbnail': '',
        'image_url': '',
        'source_domain': 'catholiccompany.com',
        'price': 'From $25.00',
        'product_id': 'catholicco-saints-book',
        'search_query': 'Catholic gift for adults',
        'interest_match': 'catholicism',
        'priority': 2,
        'brand': 'The Catholic Company',
        'advertiser_id': 'trinityroad-cj',
    },
]

_TRINITYROAD_TRIGGER_INTERESTS = {
    # Faith signals
    'catholic', 'catholicism', 'roman catholic', 'christianity', 'christian',
    'faith', 'religion', 'religious', 'church', 'mass', 'prayer',
    # Catholic-specific practices
    'rosary', 'saints', 'saint', 'patron saint', 'lent', 'advent',
    'scripture', 'bible', 'gospel', 'pope', 'vatican',
    # Sacraments / milestones
    'first communion', 'confirmation', 'baptism', 'christening',
    'sacrament', 'rcia',
    # Lifestyle signals
    'catholic school', 'parochial school', 'catholic education',
}

# Occasion-specific interest signals — trigger the milestone product first
_TRINITYROAD_COMMUNION_SIGNALS = {
    'first communion', 'first holy communion', 'communion',
}
_TRINITYROAD_CONFIRMATION_SIGNALS = {
    'confirmation', 'confirmed', 'sacrament of confirmation',
}
_TRINITYROAD_BAPTISM_SIGNALS = {
    'baptism', 'christening', 'baptismal', 'godparent', 'godfather', 'godmother',
}
_TRINITYROAD_COFFEE_SIGNALS = {
    'coffee', 'espresso', 'specialty coffee', 'cafe culture', 'morning routine',
    'craft coffee', 'artisan',
}
_TRINITYROAD_ADULT_HUMOR_SIGNALS = {
    'beer', 'cocktails', 'wine', 'pub', 'humor', 'books', 'reading', 'history',
    'craft beer', 'drinking', 'bar',
}


def get_trinityroad_products_for_profile(profile):
    """
    Return curated Trinity Road / Catholic Company products for faith-aligned profiles.

    No product feed — static list using CJ category text links and deep links.
    Commission: 8%, 30-45 day cookie. Free shipping $75+.

    Smart selection (cap 2):
    - First Communion signals → communion gifts + rosary
    - Confirmation signals → confirmation gifts + general store
    - Baptism signals → baptism gifts + general store
    - Catholic + coffee → Catholic Coffee + general store
    - Catholic + adult humor/books → Drinking with Saints + rosary
    - General Catholic/Christian faith → general store + rosary

    T&C: No external coupons. Do NOT use RetailMeNot co-brand links.
    """
    interests = profile.get('interests', [])
    interest_names = {i.get('name', '').lower() for i in interests if i.get('name')}

    matched = interest_names & _TRINITYROAD_TRIGGER_INTERESTS
    if not matched:
        for name in interest_names:
            for trigger in _TRINITYROAD_TRIGGER_INTERESTS:
                if trigger in name or name in trigger:
                    matched.add(name)
                    break

    if not matched:
        return []

    logger.info(f"Trinity Road (Catholic Co.) triggered by profile interests: {matched}")

    def _get(pid):
        return next((p for p in _TRINITYROAD_ALL_PRODUCTS if p['product_id'] == pid), None)

    is_communion = bool(interest_names & _TRINITYROAD_COMMUNION_SIGNALS) or any(
        'communion' in n for n in interest_names
    )
    is_confirmation = bool(interest_names & _TRINITYROAD_CONFIRMATION_SIGNALS) or any(
        'confirm' in n for n in interest_names
    )
    is_baptism = bool(interest_names & _TRINITYROAD_BAPTISM_SIGNALS) or any(
        'bapti' in n or 'christen' in n or 'godpar' in n for n in interest_names
    )
    is_coffee = bool(interest_names & _TRINITYROAD_COFFEE_SIGNALS) or any(
        'coffee' in n or 'espresso' in n for n in interest_names
    )
    is_adult_humor = bool(interest_names & _TRINITYROAD_ADULT_HUMOR_SIGNALS) or any(
        'beer' in n or 'cocktail' in n or 'pub' in n for n in interest_names
    )

    if is_communion:
        return [p for p in [_get('catholicco-communion'), _get('catholicco-rosary')] if p]
    elif is_confirmation:
        return [p for p in [_get('catholicco-confirmation'), _get('catholicco-gifts')] if p]
    elif is_baptism:
        return [p for p in [_get('catholicco-baptism'), _get('catholicco-gifts')] if p]
    elif is_coffee:
        return [p for p in [_get('catholicco-coffee'), _get('catholicco-gifts')] if p]
    elif is_adult_humor:
        return [p for p in [_get('catholicco-saints-book'), _get('catholicco-rosary')] if p]
    else:
        return [p for p in [_get('catholicco-gifts'), _get('catholicco-rosary')] if p]


# ---------------------------------------------------------------------------
# ZCHOCOLAT.COM — Static curated products (approved CJ partner, Feb 2026)
# ADV_CID: 1124214
# Commission: 20% confirmed sale | Cookie: 45 days | AOV: $120
# EPC: Evergreen $75 (3-mo) / $367 (7-day) | Assortments $133 (3-mo) / $169 (7-day)
#
# Pascal Caffet, World-Champion chocolatier. Hand-made French chocolates.
# Ships worldwide via DHL to 244 countries. 4.9/5 on TrustPilot (5,000+ reviews).
# Rated "Best Chocolate Store 2022" (Top Consumer Reviews), NYT "Best Present Idea",
# Food Network "Top 5 Chocolate Gifts", WSJ "Best Lesser Known Gift Site on the Net."
#
# Evergreen link ID 15734455 — deep-link enabled.
#   Base: https://www.jdoqocy.com/click-101660899-15734455
#   Deep-link: append ?url=encoded_destination
#
# T&C: No bidding on "zchocolat", "zchocolat.com", "zchocolat coupon", or
#   misspellings in PPC (irrelevant for content). No other restrictions for
#   content publishers. Use any text/images from their website freely.
#
# NOTE: 20% commission is the highest of any partner in this file.
#   ~$24 per average sale. Prioritize for chocolate/gourmet/luxury triggers.
# ---------------------------------------------------------------------------

_ZCHOCOLAT_EVERGREEN_BASE = "https://www.jdoqocy.com/click-101660899-15734455"


def _zchocolat_deep_link(path):
    """Build a CJ deep link to a specific zchocolat.com page."""
    destination = f"https://www.zchocolat.com{path}"
    return f"{_ZCHOCOLAT_EVERGREEN_BASE}?url={urllib.parse.quote(destination, safe='')}"


_ZCHOCOLAT_ALL_PRODUCTS = [
    {
        # Link ID 13093353 — Chocolate Gift Assortments ($132.69 EPC / $169.13 EPC) ← STAR
        'title': "French Chocolate Gift Assortments — zChocolat",
        'link': 'https://www.jdoqocy.com/click-101660899-13093353',
        'snippet': (
            "Fifteen sumptuous French chocolate assortments by World-Champion pâtissier Pascal Caffet — "
            "hand-made, no preservatives, high cocoa content. Each box is a voyage through the "
            "zChocolat universe. Rated #1 by NYT, Food Network, and TrustPilot (4.9/5, 5,000+ reviews)."
        ),
        'image': '',
        'thumbnail': '',
        'image_url': '',
        'source_domain': 'zchocolat.com',
        'price': 'From $49.00',
        'product_id': 'zchocolat-assortments',
        'search_query': 'gourmet chocolate gift',
        'interest_match': 'chocolate',
        'priority': 2,
        'brand': 'zChocolat',
        'advertiser_id': 'zchocolat-cj',
    },
    {
        # Link ID 12981989 — Personalized Assortments (pick your own chocolates)
        'title': "Personalized French Chocolate Box — zChocolat",
        'link': 'https://www.kqzyfj.com/click-101660899-12981989',
        'snippet': (
            "Build your own dream chocolate collection — handpick your favorite zChocolat recipes "
            "to create a completely personalized box. World-champion hand-made French truffles, "
            "delivered worldwide in chic black and white packaging."
        ),
        'image': '',
        'thumbnail': '',
        'image_url': '',
        'source_domain': 'zchocolat.com',
        'price': 'From $49.00',
        'product_id': 'zchocolat-personalized',
        'search_query': 'personalized chocolate gift',
        'interest_match': 'personalization',
        'priority': 2,
        'brand': 'zChocolat',
        'advertiser_id': 'zchocolat-cj',
    },
    {
        # Link ID 12981986 — 24 Karat Edible Gold Collection (luxury/milestone)
        'title': "24 Karat Edible Gold French Chocolates — zChocolat",
        'link': 'https://www.tkqlhce.com/click-101660899-12981986',
        'snippet': (
            "Every piece of chocolate hand-coated in exquisite 24-karat edible gold by World-Champion "
            "chocolatier Pascal Caffet. Packaged in artisan mahogany boxes handcrafted in the Jura "
            "region of France. The ultimate luxury chocolate gift for milestone occasions."
        ),
        'image': '',
        'thumbnail': '',
        'image_url': '',
        'source_domain': 'zchocolat.com',
        'price': 'From $89.00',
        'product_id': 'zchocolat-gold',
        'search_query': 'luxury chocolate gift',
        'interest_match': 'luxury',
        'priority': 2,
        'brand': 'zChocolat',
        'advertiser_id': 'zchocolat-cj',
    },
    {
        # Link ID 13086892 — All-Natural Vegan Selection
        'title': "Vegan French Chocolate Collection — zChocolat",
        'link': 'https://www.kqzyfj.com/click-101660899-13086892',
        'snippet': (
            "World-champion French chocolates made for vegan palates — no animal or dairy products, "
            "no alcohol, no preservatives. High cocoa content, low sugar, 100% pure cocoa butter. "
            "Pascal Caffet's plant-based creations, delivered worldwide."
        ),
        'image': '',
        'thumbnail': '',
        'image_url': '',
        'source_domain': 'zchocolat.com',
        'price': 'From $49.00',
        'product_id': 'zchocolat-vegan',
        'search_query': 'vegan chocolate gift',
        'interest_match': 'vegan',
        'priority': 2,
        'brand': 'zChocolat',
        'advertiser_id': 'zchocolat-cj',
    },
    {
        # Link ID 10020803 — Homepage ($35.89 EPC / $52.54 EPC) — solid general fallback
        'title': "zChocolat — World's Finest French Chocolates",
        'link': 'https://www.anrdoezrs.net/click-101660899-10020803',
        'snippet': (
            "Hand-made French chocolates by Pascal Caffet, World-Champion pâtissier. "
            "Rated 'Best Chocolate Store' (Top Consumer Reviews), 'Best Present Idea' (NYT), "
            "'Top 5 Chocolate Gifts' (Food Network). Ships to 244 countries via DHL."
        ),
        'image': '',
        'thumbnail': '',
        'image_url': '',
        'source_domain': 'zchocolat.com',
        'price': 'From $49.00',
        'product_id': 'zchocolat-home',
        'search_query': 'French chocolate gift',
        'interest_match': 'chocolate',
        'priority': 2,
        'brand': 'zChocolat',
        'advertiser_id': 'zchocolat-cj',
    },
]

_ZCHOCOLAT_TRIGGER_INTERESTS = {
    # Must have a genuine chocolate/confectionery affinity — not just "foodie"
    'chocolate', 'dark chocolate', 'milk chocolate', 'truffles', 'bonbons',
    'confectionery', 'gourmet chocolate', 'french chocolate', 'artisan chocolate',
    # French food passion — zChocolat is quintessentially French patisserie
    'french cuisine', 'french food', 'patisserie', 'pastry',
    # Strong dessert/baking signal (not generic lifestyle)
    'gourmet food', 'desserts', 'baking', 'sweets',
    # Vegan — dedicated vegan line worth surfacing for plant-based profiles
    'vegan', 'plant-based',
    # Luxury taste — premium chocolate is a legitimate luxury gift category
    'luxury', 'fine dining',
    # NOTE: 'foodie', 'gourmet', 'entertaining', 'hosting', 'wine', 'champagne',
    # 'anniversary', 'romance', 'date night' intentionally excluded.
    # Those are too broad — chocolate should only appear when the profile
    # genuinely loves chocolate/French confectionery, not as a trope fallback.
}

_ZCHOCOLAT_VEGAN_SIGNALS = {
    'vegan', 'plant-based', 'plant based', 'dairy-free', 'dairy free',
    'veganism', 'plant-based diet', 'whole food', 'clean eating',
}

_ZCHOCOLAT_LUXURY_SIGNALS = {
    'luxury', 'luxury gifts', 'fine dining', 'indulgence', 'premium',
    'milestone', 'anniversary', 'engagement', 'wedding', 'champagne',
}

_ZCHOCOLAT_PERSONALIZATION_SIGNALS = {
    'personalization', 'personalized gifts', 'custom gifts', 'sentimental',
    'memory keeping', 'keepsake',
}


def get_zchocolat_products_for_profile(profile):
    """
    Return curated zChocolat.com products when the profile has matching interests.

    No product feed — static list using direct CJ click URLs + Evergreen deep links.
    Commission: 20% confirmed sale (highest in the partner set). 45-day cookie.
    AOV: $120 → ~$24 avg commission per sale. Strong EPC on Assortments link.

    Smart selection (cap 2):
    - Vegan/plant-based → Vegan Selection + Assortments
    - Luxury/milestone/anniversary → 24K Gold + Personalized
    - Personalization interest → Personalized + Assortments
    - General chocolate/gourmet/foodie → Assortments + Homepage

    T&C: No PPC brand bidding (irrelevant). No other restrictions for content.
    """
    interests = profile.get('interests', [])
    interest_names = {i.get('name', '').lower() for i in interests if i.get('name')}

    matched = interest_names & _ZCHOCOLAT_TRIGGER_INTERESTS
    if not matched:
        for name in interest_names:
            for trigger in _ZCHOCOLAT_TRIGGER_INTERESTS:
                if trigger in name or name in trigger:
                    matched.add(name)
                    break

    if not matched:
        return []

    logger.info(f"zChocolat triggered by profile interests: {matched}")

    def _get(pid):
        return next((p for p in _ZCHOCOLAT_ALL_PRODUCTS if p['product_id'] == pid), None)

    is_vegan = bool(interest_names & _ZCHOCOLAT_VEGAN_SIGNALS) or any(
        'vegan' in n or 'plant' in n or 'dairy' in n for n in interest_names
    )
    is_luxury = bool(interest_names & _ZCHOCOLAT_LUXURY_SIGNALS) or any(
        'luxury' in n or 'anniversar' in n or 'milestone' in n or 'engag' in n
        for n in interest_names
    )
    is_personalization = bool(interest_names & _ZCHOCOLAT_PERSONALIZATION_SIGNALS) or any(
        'personal' in n or 'custom' in n or 'sentimental' in n for n in interest_names
    )

    if is_vegan:
        return [p for p in [_get('zchocolat-vegan'), _get('zchocolat-assortments')] if p]
    elif is_luxury:
        return [p for p in [_get('zchocolat-gold'), _get('zchocolat-personalized')] if p]
    elif is_personalization:
        return [p for p in [_get('zchocolat-personalized'), _get('zchocolat-assortments')] if p]
    else:
        return [p for p in [_get('zchocolat-assortments'), _get('zchocolat-home')] if p]


# ---------------------------------------------------------------------------
# WINEBASKET / BABYBASKET / CAPALBOSONLINE — Static curated products
# Approved CJ partner, Feb 2026 | ADV_CID: 2387081
# Commission: 7% | Cookie: 15 days | AOV: $110
# EPC: Evergreen $66.39 (3-mo) / $52.96 (7-day)
#
# Three distinct sites under one CJ program:
#   winebasket.com     — wine gift baskets and wine-themed gifts
#   babybasket.com     — baby shower and newborn gift baskets
#   capalbosonline.com — gourmet fruit, cheese, and food gift baskets
#
# Evergreen link ID 15733435 — deep-link enabled.
#   Base: https://www.kqzyfj.com/click-101660899-15733435
#   Deep-link: append ?url=encoded_destination to route to specific site/page
#
# T&C: Standard CJ terms. No prohibited coupon sources noted.
# ---------------------------------------------------------------------------

_WINEBASKET_EVERGREEN_BASE = "https://www.kqzyfj.com/click-101660899-15733435"


def _winebasket_deep_link(domain, path='/'):
    """Build a CJ deep link to a specific site page under the Winebasket program."""
    destination = f"https://www.{domain}{path}"
    return f"{_WINEBASKET_EVERGREEN_BASE}?url={urllib.parse.quote(destination, safe='')}"


_WINEBASKET_ALL_PRODUCTS = [
    {
        # Deep-link → winebasket.com homepage
        'title': "Wine Gift Baskets — WineBasket.com",
        'link': _winebasket_deep_link('winebasket.com'),
        'snippet': (
            "Beautifully curated wine gift baskets delivered nationwide — red, white, rosé, "
            "and sparkling selections paired with gourmet snacks and accessories. "
            "Perfect for holidays, corporate gifts, hostess gifts, and celebrations."
        ),
        'image': '',
        'thumbnail': '',
        'image_url': '',
        'source_domain': 'winebasket.com',
        'price': 'From $49.00',
        'product_id': 'winebasket-wine',
        'search_query': 'wine gift basket',
        'interest_match': 'wine',
        'priority': 2,
        'brand': 'WineBasket.com',
        'advertiser_id': 'winebasket-cj',
    },
    {
        # Deep-link → babybasket.com homepage
        'title': "Baby Gift Baskets — BabyBasket.com",
        'link': _winebasket_deep_link('babybasket.com'),
        'snippet': (
            "Thoughtfully curated baby shower and newborn gift baskets delivered nationwide — "
            "soft essentials, keepsakes, and pampering items for new parents. "
            "Gender-neutral and themed options available."
        ),
        'image': '',
        'thumbnail': '',
        'image_url': '',
        'source_domain': 'babybasket.com',
        'price': 'From $49.00',
        'product_id': 'winebasket-baby',
        'search_query': 'baby gift basket',
        'interest_match': 'baby shower',
        'priority': 2,
        'brand': 'BabyBasket.com',
        'advertiser_id': 'winebasket-cj',
    },
    {
        # Deep-link → capalbosonline.com homepage
        'title': "Gourmet Fruit & Cheese Gift Baskets — Capalbo's",
        'link': _winebasket_deep_link('capalbosonline.com'),
        'snippet': (
            "Capalbo's classic gourmet gift baskets — premium fresh fruit, artisan cheeses, "
            "charcuterie, and gourmet snacks beautifully arranged and delivered nationwide. "
            "A timeless gift for foodies, hosts, and corporate occasions."
        ),
        'image': '',
        'thumbnail': '',
        'image_url': '',
        'source_domain': 'capalbosonline.com',
        'price': 'From $59.00',
        'product_id': 'winebasket-gourmet',
        'search_query': 'gourmet gift basket',
        'interest_match': 'gourmet',
        'priority': 2,
        'brand': "Capalbo's",
        'advertiser_id': 'winebasket-cj',
    },
]

_WINEBASKET_TRIGGER_INTERESTS = {
    # Wine enthusiasts only — not just "drinks" or "social"
    'wine', 'wine tasting', 'winery', 'vineyard', 'wine lover', 'wine bar',
    'champagne', 'sparkling wine', 'red wine', 'white wine', 'rosé', 'sommelier',
    # Baby/new parent — high-intent, genuinely occasion-specific for baby basket
    'baby shower', 'newborn', 'new baby', 'new parent', 'pregnancy',
    'expecting', 'motherhood', 'fatherhood', 'nursery',
    # Direct food/cheese passion — not generic "foodie" or "entertaining"
    'gourmet food', 'cheese', 'charcuterie', 'artisan food', 'food lover',
    # NOTE: 'craft beer', 'cocktails', 'drinking', 'entertaining', 'hosting',
    # 'corporate gifts', 'housewarming', 'get well', 'sympathy', 'gourmet',
    # 'foodie' intentionally excluded — those are trope-adjacent triggers that
    # would surface gift baskets as a lazy fallback for social/hosting profiles.
}

_WINEBASKET_WINE_SIGNALS = {
    # Genuine wine lover signals only
    'wine', 'wine tasting', 'winery', 'vineyard', 'wine lover', 'wine bar',
    'champagne', 'sparkling wine', 'red wine', 'white wine', 'rosé', 'sommelier',
}

_WINEBASKET_BABY_SIGNALS = {
    'baby shower', 'newborn', 'new baby', 'new parent', 'pregnancy',
    'expecting', 'motherhood', 'fatherhood', 'nursery', 'parenting',
}

_WINEBASKET_GOURMET_SIGNALS = {
    # Direct food passion — not "foodie" (too generic) or occasion-based
    'gourmet food', 'cheese', 'charcuterie', 'artisan food', 'food lover',
}


def get_winebasket_products_for_profile(profile):
    """
    Return curated Winebasket / Babybasket / Capalbo's products for matching profiles.

    No product feed — static list using Evergreen deep links to each site.
    Commission: 7%, 15-day cookie. Strong EPC ($66 3-mo / $53 7-day on Evergreen).
    AOV ~$110 → ~$7.70 avg commission per sale.

    Smart selection (cap 2):
    - Wine/drinks/entertaining → WineBasket + Capalbo's gourmet
    - Baby/new parent/pregnancy → BabyBasket + WineBasket (as add-on)
    - Gourmet/foodie/cheese → Capalbo's + WineBasket
    - General gifting occasions → WineBasket + Capalbo's
    """
    interests = profile.get('interests', [])
    interest_names = {i.get('name', '').lower() for i in interests if i.get('name')}

    matched = interest_names & _WINEBASKET_TRIGGER_INTERESTS
    if not matched:
        for name in interest_names:
            for trigger in _WINEBASKET_TRIGGER_INTERESTS:
                if trigger in name or name in trigger:
                    matched.add(name)
                    break

    if not matched:
        return []

    logger.info(f"Winebasket/BabyBasket/Capalbo's triggered by profile interests: {matched}")

    def _get(pid):
        return next((p for p in _WINEBASKET_ALL_PRODUCTS if p['product_id'] == pid), None)

    is_baby = bool(interest_names & _WINEBASKET_BABY_SIGNALS) or any(
        'baby' in n or 'newborn' in n or 'pregnan' in n or 'parent' in n
        or 'nursery' in n or 'expect' in n
        for n in interest_names
    )
    is_gourmet = bool(interest_names & _WINEBASKET_GOURMET_SIGNALS) or any(
        'gourmet' in n or 'foodie' in n or 'cheese' in n or 'charcuteri' in n
        for n in interest_names
    )
    is_wine = bool(interest_names & _WINEBASKET_WINE_SIGNALS) or any(
        'wine' in n or 'champagne' in n or 'cocktail' in n or 'winery' in n
        for n in interest_names
    )

    if is_baby:
        return [p for p in [_get('winebasket-baby'), _get('winebasket-wine')] if p]
    elif is_gourmet:
        return [p for p in [_get('winebasket-gourmet'), _get('winebasket-wine')] if p]
    elif is_wine:
        return [p for p in [_get('winebasket-wine'), _get('winebasket-gourmet')] if p]
    else:
        return [p for p in [_get('winebasket-wine'), _get('winebasket-gourmet')] if p]


def get_soccergarage_products_for_profile(profile):
    """
    Return curated SoccerGarage.com products when the profile has soccer interest.

    No product feed via CJ — static list using category text link IDs.
    Commission: 7% base, scales to 8-10% at volume thresholds. 60-day cookie.

    Smart selection:
    - Goalkeeper profile → goalkeeper gear + cleats
    - Youth/parent profile → youth gear + general
    - General soccer fan → cleats + general homepage
    Cap: 2 products max to keep recommendation pool balanced.

    T&C: Do NOT use expired 2012 coupon codes (GARAGE10, 5C4J2U).
    """
    interests = profile.get('interests', [])
    interest_names = {i.get('name', '').lower() for i in interests if i.get('name')}

    matched = interest_names & _SOCCERGARAGE_TRIGGER_INTERESTS
    if not matched:
        for name in interest_names:
            for trigger in _SOCCERGARAGE_TRIGGER_INTERESTS:
                if trigger in name or name in trigger:
                    matched.add(name)
                    break

    if not matched:
        return []

    logger.info(f"SoccerGarage.com triggered by profile interests: {matched}")

    is_goalkeeper = bool(interest_names & _SOCCERGARAGE_GOALKEEPER_INTERESTS) or any(
        'goal' in n or 'keeper' in n or 'goalie' in n for n in interest_names
    )
    is_youth_or_parent = bool(interest_names & _SOCCERGARAGE_YOUTH_INTERESTS) or any(
        'youth' in n or 'kid' in n or 'child' in n or 'parent' in n for n in interest_names
    )

    def _get(pid):
        return next((p for p in _SOCCERGARAGE_ALL_PRODUCTS if p['product_id'] == pid), None)

    if is_goalkeeper:
        return [p for p in [_get('soccergarage-goalkeeper'), _get('soccergarage-cleats')] if p]
    elif is_youth_or_parent:
        return [p for p in [_get('soccergarage-youth'), _get('soccergarage-home')] if p]
    else:
        return [p for p in [_get('soccergarage-cleats'), _get('soccergarage-home')] if p]


def get_peets_products_for_profile(profile):
    """
    Return curated Peet's Coffee products when the profile has matching interests.

    Peet's has no product feed via CJ — this static list uses CJ deep links
    off the Evergreen link (ID 15734720).

    Triggers: coffee, espresso, tea, gourmet, and lifestyle/aesthetic signals
    (indie folk, craft culture, brunch, etc.).

    T&C: Do NOT use discount language beyond NEWSUB30 and WEBFRIEND5.
    """
    interests = profile.get('interests', [])
    interest_names = {i.get('name', '').lower() for i in interests if i.get('name')}

    # Check direct and partial matches against trigger set
    matched = interest_names & PEETS_TRIGGER_INTERESTS
    if not matched:
        for name in interest_names:
            for trigger in PEETS_TRIGGER_INTERESTS:
                if trigger in name or name in trigger:
                    matched.add(name)
                    break

    if not matched:
        logger.debug(f"Peet's: no trigger interests found (profile interests: {interest_names})")
        return []

    logger.info(f"Peet's Coffee triggered by profile interests: {matched}")

    tea_only_interests = {'tea', 'green tea', 'herbal tea', 'chai'}
    is_tea_only = bool(tea_only_interests & interest_names) and 'coffee' not in interest_names and 'espresso' not in interest_names

    if is_tea_only:
        # Tea-only profile: return tea product + gift set only
        return [p for p in _PEETS_ALL_PRODUCTS if p['interest_match'] == 'tea' or p['product_id'] == 'peets-gift-set']

    return list(_PEETS_ALL_PRODUCTS)

# Credentials from environment
CJ_API_KEY = os.environ.get('CJ_API_KEY', '')
CJ_COMPANY_ID = os.environ.get('CJ_COMPANY_ID', '')  # Your publisher CID
CJ_PUBLISHER_ID = os.environ.get('CJ_PUBLISHER_ID', '')  # Your PID for tracking


class CJRateLimiter:
    """
    Rate limiter for CJ GraphQL API

    Limit: 500 calls per 5 minutes (per API documentation)
    """
    def __init__(self, max_requests=500, time_window=300):  # 300 seconds = 5 minutes
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = deque()

    def wait_if_needed(self):
        """Wait if rate limit would be exceeded"""
        now = time.time()

        # Remove requests older than time window
        while self.requests and self.requests[0] < now - self.time_window:
            self.requests.popleft()

        # If at limit, wait
        if len(self.requests) >= self.max_requests:
            sleep_time = self.requests[0] + self.time_window - now
            logger.info(f"CJ rate limit reached, sleeping {sleep_time:.1f}s")
            time.sleep(sleep_time)

        self.requests.append(now)


# Global rate limiter instance
rate_limiter = CJRateLimiter()


class CJAPIError(Exception):
    """CJ API error"""
    pass


def _build_auth_headers(api_key):
    """
    Build authentication headers for CJ GraphQL API

    Uses Bearer token authentication
    """
    if not api_key:
        raise CJAPIError("CJ_API_KEY not provided")

    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }


def _build_graphql_query(keywords, company_id, publisher_id, limit=50, joined_only=False):
    """
    Build GraphQL query for CJ product search

    Args:
        keywords: List of keywords to search for
        company_id: Your CJ publisher company ID (CID)
        publisher_id: Your publisher ID (PID) for tracking links
        limit: Max number of products to return (default 50, max 1000)
        joined_only: If True, only search advertisers you've joined (default False)

    Returns:
        GraphQL query string
    """
    # Convert keywords list to GraphQL array format
    keywords_str = json.dumps(keywords)

    # Build partner status filter if needed
    partner_filter = ""
    if joined_only:
        partner_filter = "partnerStatus: JOINED,"

    query = f"""
    {{
      products(
        companyId: "{company_id}",
        keywords: {keywords_str},
        {partner_filter}
        limit: {limit}
      ) {{
        totalCount
        count
        resultList {{
          id
          title
          description
          price {{
            amount
            currency
          }}
          imageLink
          link
          brand
          advertiserId
          advertiserName
          linkCode(pid: "{publisher_id}") {{
            clickUrl
          }}
        }}
      }}
    }}
    """
    return query


def _parse_graphql_response(data, search_term):
    """
    Parse CJ GraphQL product response into standardized format

    Args:
        data: GraphQL response data
        search_term: The search keyword used (for tagging products)

    Returns:
        List of product dicts with standardized keys
    """
    products = []

    # Navigate to products result list
    try:
        products_data = data.get('data', {}).get('products', {})
        total_count = products_data.get('totalCount', 0)
        result_list = products_data.get('resultList', [])

        logger.info(f"CJ GraphQL response: {len(result_list)} products (total available: {total_count})")

        for item in result_list:
            try:
                # Extract price
                price_obj = item.get('price', {})
                price_amount = price_obj.get('amount', '')
                price_currency = price_obj.get('currency', 'USD')

                if price_amount:
                    try:
                        price_float = float(price_amount)
                        price_str = f"${price_float:.2f}"
                    except (ValueError, TypeError):
                        price_str = f"{price_currency} {price_amount}"
                else:
                    price_str = "Price varies"

                # Extract affiliate tracking link.
                # linkCode is None for advertisers you haven't joined —
                # those are non-joined global retailers (Martinus.cz, Hood.de,
                # OnBuy.com, etc.) we can't earn commission from. Skip them.
                link_code = item.get('linkCode')
                if not link_code or not isinstance(link_code, dict):
                    logger.debug(
                        f"Skipping non-joined advertiser: {item.get('advertiserName')} "
                        f"— {(item.get('title') or '')[:50]}"
                    )
                    continue

                tracking_url = link_code.get('clickUrl', '')
                if not tracking_url:
                    logger.debug(f"Skipping product with empty click URL: {(item.get('title') or '')[:50]}")
                    continue

                # Map to GiftWise standard format
                product = {
                    'title': item.get('title', 'Unknown Product'),
                    'link': tracking_url,  # Affiliate tracking link
                    'snippet': (item.get('description', '') or '')[:200],  # Truncate description
                    'image': item.get('imageLink', ''),
                    'thumbnail': item.get('imageLink', ''),
                    'image_url': item.get('imageLink', ''),
                    'source_domain': item.get('advertiserName', 'CJ Affiliate'),
                    'price': price_str,
                    'product_id': item.get('id', ''),
                    'search_query': search_term,
                    'interest_match': search_term,
                    'priority': 2,  # CJ priority: higher than Amazon (3), lower than Etsy (1)
                    'brand': item.get('brand', ''),
                    'advertiser_id': item.get('advertiserId', ''),
                }

                products.append(product)

            except Exception as e:
                logger.error(f"Error parsing CJ product: {e}")
                continue

    except Exception as e:
        logger.error(f"Error parsing CJ GraphQL response: {e}")

    return products


def search_products_cj(profile, api_key, company_id=None, publisher_id=None, target_count=20, enhanced_search_terms=None, joined_only=False):
    """
    Search CJ Affiliate for products matching user profile using GraphQL API

    Args:
        profile: User profile dict with interests, demographics, etc.
        api_key: CJ Personal Access Token (from Developer Portal)
        company_id: Your CJ publisher company ID (CID) - optional, uses env var if not provided
        publisher_id: Your publisher ID (PID) for tracking links - optional, uses env var if not provided
        target_count: Target number of products to return
        enhanced_search_terms: Pre-computed search terms from enrichment (optional)
        joined_only: If True, only search advertisers you've joined (default False)

    Returns:
        List of product dicts matching GiftWise standard format

    Note: Set joined_only=False to search ALL CJ advertisers (recommended until you join more)
    """
    # Always inject static partners — they don't need CJ API credentials.
    # Collecting them here so they're returned even if CJ GraphQL is unavailable.
    static_products = []
    for getter, label in [
        (get_peets_products_for_profile, "Peet's Coffee"),
        (get_illy_products_for_profile, "illy caffè"),
        (get_monthlyclubs_products_for_profile, "MonthlyClubs"),
        (get_soccergarage_products_for_profile, "SoccerGarage.com"),
        (get_techforless_products_for_profile, "Tech For Less"),
        (get_tenergy_products_for_profile, "Tenergy"),
        (get_trinityroad_products_for_profile, "Trinity Road / Catholic Co."),
        (get_zchocolat_products_for_profile, "zChocolat"),
        (get_winebasket_products_for_profile, "Winebasket/BabyBasket/Capalbo's"),
        (get_flowersfast_products_for_profile, "FlowersFast"),
        (get_fragranceshop_products_for_profile, "FragranceShop"),
        (get_gamefly_products_for_profile, "GameFly"),
        (get_greatergood_products_for_profile, "GreaterGood"),
        (get_groundluxe_products_for_profile, "GroundLuxe"),
        (get_russellstover_products_for_profile, "Russell Stover"),
        (get_ghirardelli_products_for_profile, "Ghirardelli"),
        (get_silverrushstyle_products_for_profile, "SilverRushStyle"),
    ]:
        products = getter(profile)
        if products:
            static_products.extend(products)
            logger.info(f"Static partner: {len(products)} {label} products matched profile")

    if not api_key:
        logger.info(f"CJ API key not set — returning {len(static_products)} static partner products only")
        return static_products

    # Use provided credentials or fall back to environment
    cid = company_id or CJ_COMPANY_ID
    pid = publisher_id or CJ_PUBLISHER_ID

    if not cid or not pid:
        logger.warning("CJ company ID or publisher ID missing - skipping CJ search")
        return []

    logger.info(f"Starting CJ GraphQL product search (target: {target_count}, CID: {cid}, PID: {pid})")

    # Build search terms from profile
    interests = profile.get('interests', [])
    if not interests:
        logger.warning("No interests in profile - CJ search aborted")
        return []

    # Use enhanced search terms if available, otherwise clean interest names
    if enhanced_search_terms:
        search_terms = enhanced_search_terms[:5]  # Limit to top 5
    else:
        try:
            from search_query_utils import clean_interest_for_search
            search_terms = [clean_interest_for_search(interest.get('name', ''))
                           for interest in interests[:5]
                           if interest.get('name') and not interest.get('is_work', False)]
        except ImportError:
            search_terms = [interest.get('name', '') for interest in interests[:5]]

    all_products = []

    for term in search_terms:
        if not term:
            continue

        # ----------------------------------------------------------------
        # Cache check — use SQLite catalog if this term was synced recently.
        # Saves 3–5 seconds of live API latency per term.
        # Falls back to live API on cache miss, import error, or DB failure.
        # ----------------------------------------------------------------
        if _CATALOG_CACHE_AVAILABLE:
            try:
                if is_term_cache_fresh(term):
                    cached = get_cached_products_for_interest(
                        term, limit=min(60, target_count)
                    )
                    if cached:
                        all_products.extend(cached)
                        logger.info(
                            f"CJ catalog cache hit '{term}': {len(cached)} products"
                        )
                        if len(all_products) >= target_count:
                            break
                        continue
                    # Cache is fresh but empty for this term — fall through to live
            except Exception as _ce:
                logger.debug(f"Cache lookup failed for '{term}': {_ce}")
        # ----------------------------------------------------------------

        try:
            # Rate limiting
            rate_limiter.wait_if_needed()

            # Build GraphQL query
            query = _build_graphql_query(
                keywords=[term],
                company_id=cid,
                publisher_id=pid,
                limit=min(50, target_count),
                joined_only=joined_only
            )

            # Make GraphQL request
            headers = _build_auth_headers(api_key)

            logger.info(f"CJ GraphQL search: '{term}'")
            response = requests.post(
                CJ_GRAPHQL_ENDPOINT,
                json={"query": query},
                headers=headers,
                timeout=30
            )

            # Handle errors
            if response.status_code == 401:
                logger.error("CJ authentication failed - check CJ_API_KEY")
                return []
            elif response.status_code == 403:
                logger.warning("CJ 403 - not joined to any advertisers or access denied")
                return []
            elif response.status_code == 429:
                logger.warning("CJ rate limit exceeded - waiting 60s...")
                time.sleep(60)
                continue
            elif response.status_code != 200:
                logger.error(f"CJ API error {response.status_code}: {response.text}")
                continue

            # Parse GraphQL response
            data = response.json()

            # Check for GraphQL errors
            if 'errors' in data:
                logger.error(f"CJ GraphQL errors: {data['errors']}")
                continue

            # Parse products
            products = _parse_graphql_response(data, term)

            all_products.extend(products)
            logger.info(f"CJ search '{term}': found {len(products)} products")

            # Stop if we have enough
            if len(all_products) >= target_count:
                break

        except requests.RequestException as e:
            logger.error(f"CJ API request failed for '{term}': {e}")
            continue
        except Exception as e:
            logger.error(f"Unexpected error in CJ search for '{term}': {e}")
            continue

    # Merge static partner products with GraphQL results and deduplicate
    all_products.extend(static_products)

    # Deduplicate by product ID
    seen_ids = set()
    unique_products = []
    for p in all_products:
        pid_val = p.get('product_id')
        if pid_val and pid_val not in seen_ids:
            seen_ids.add(pid_val)
            unique_products.append(p)

    logger.info(f"CJ search complete: {len(unique_products)} unique products")
    return unique_products[:target_count]


# Test/validation
if __name__ == "__main__":
    print("CJ Affiliate GraphQL Searcher")
    print("=" * 50)
    print("API Endpoint:", CJ_GRAPHQL_ENDPOINT)
    print()
    print("Current credentials:")
    print(f"  CJ_API_KEY: {'✓ Set' if CJ_API_KEY else '✗ Missing'}")
    print(f"  CJ_COMPANY_ID: {'✓ Set' if CJ_COMPANY_ID else '✗ Missing'}")
    print(f"  CJ_PUBLISHER_ID: {'✓ Set' if CJ_PUBLISHER_ID else '✗ Missing'}")
    print()

    if CJ_API_KEY and CJ_COMPANY_ID and CJ_PUBLISHER_ID:
        print("✓ All credentials set - ready to test")
        print()
        print("Testing with sample search...")

        # Test profile
        test_profile = {
            'interests': [
                {'name': 'wine', 'strength': 'strong'},
                {'name': 'coffee', 'strength': 'medium'}
            ]
        }

        try:
            products = search_products_cj(
                profile=test_profile,
                api_key=CJ_API_KEY,
                company_id=CJ_COMPANY_ID,
                publisher_id=CJ_PUBLISHER_ID,
                target_count=5
            )

            print(f"\nFound {len(products)} products:")
            for i, p in enumerate(products[:3], 1):
                print(f"\n{i}. {p['title']}")
                print(f"   Price: {p['price']}")
                print(f"   From: {p['source_domain']}")
                print(f"   Link: {p['link'][:80]}...")

        except Exception as e:
            print(f"\nError during test: {e}")
    else:
        print("✗ Missing credentials - set environment variables:")
        print("   export CJ_API_KEY='your_personal_access_token'")
        print("   export CJ_COMPANY_ID='your_company_id'")
        print("   export CJ_PUBLISHER_ID='your_publisher_id'")
