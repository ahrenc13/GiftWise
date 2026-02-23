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
        if score > 0:
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
        if score > 0:
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
        (get_flowersfast_products_for_profile, "FlowersFast"),
        (get_fragranceshop_products_for_profile, "FragranceShop"),
        (get_gamefly_products_for_profile, "GameFly"),
        (get_greatergood_products_for_profile, "GreaterGood"),
        (get_groundluxe_products_for_profile, "GroundLuxe"),
        (get_russellstover_products_for_profile, "Russell Stover"),
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
