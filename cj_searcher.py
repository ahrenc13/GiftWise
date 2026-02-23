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
# MONTHYCLUBS.COM — Static curated products (approved CJ partner, Feb 16 2026)
# TODO: Replace PLACEHOLDER link IDs with real IDs from CJ dashboard:
#   CJ Dashboard → Advertisers → MonthlyClubs.com → Links → Get Links
# Commission: 8-15% per CLAUDE.md, high AOV gift subscriptions
# Trigger: beer/wine/cheese/chocolate/foodie/gourmet interests
# ---------------------------------------------------------------------------

_MONTHLYCLUBS_ALL_PRODUCTS = [
    {
        'title': "Beer of the Month Club — Craft Beer Subscription",
        'link': f'https://www.dpbolvw.net/click-{_ILLY_COMPANY_ID}-PLACEHOLDER_MC_LINK_1',
        'snippet': (
            "Monthly delivery of 12 handcrafted beers from small-batch breweries across the country. "
            "Includes tasting notes and brewery stories. Perfect for the craft beer enthusiast."
        ),
        'image': '',
        'thumbnail': '',
        'image_url': '',
        'source_domain': 'monthlyclub.com',
        'price': 'From $42.95/month',
        'product_id': 'mc-beer-club',
        'search_query': 'craft beer subscription gift',
        'interest_match': 'craft beer',
        'priority': 2,
        'brand': 'MonthlyClubs',
        'advertiser_id': 'monthyclubs-cj',
        '_needs_real_link': True,
    },
    {
        'title': "Wine of the Month Club — Wine Subscription",
        'link': f'https://www.dpbolvw.net/click-{_ILLY_COMPANY_ID}-PLACEHOLDER_MC_LINK_2',
        'snippet': (
            "Two expertly selected wines delivered monthly — mix of reds, whites, and international varietals. "
            "Includes vintage notes and food pairing suggestions. A gift that keeps giving."
        ),
        'image': '',
        'thumbnail': '',
        'image_url': '',
        'source_domain': 'monthlyclub.com',
        'price': 'From $42.95/month',
        'product_id': 'mc-wine-club',
        'search_query': 'wine subscription gift',
        'interest_match': 'wine',
        'priority': 2,
        'brand': 'MonthlyClubs',
        'advertiser_id': 'monthlyclubs-cj',
        '_needs_real_link': True,
    },
    {
        'title': "Cheese of the Month Club",
        'link': f'https://www.dpbolvw.net/click-{_ILLY_COMPANY_ID}-PLACEHOLDER_MC_LINK_3',
        'snippet': (
            "4 artisan cheeses selected from small creameries monthly — domestic and international varieties. "
            "Each shipment includes a cheese guide and pairing recommendations."
        ),
        'image': '',
        'thumbnail': '',
        'image_url': '',
        'source_domain': 'monthlyclub.com',
        'price': 'From $42.95/month',
        'product_id': 'mc-cheese-club',
        'search_query': 'cheese subscription gift',
        'interest_match': 'cheese',
        'priority': 2,
        'brand': 'MonthlyClubs',
        'advertiser_id': 'monthlyclubs-cj',
        '_needs_real_link': True,
    },
]

_MONTHLYCLUBS_TRIGGER_INTERESTS = {
    'beer', 'craft beer', 'wine', 'cheese', 'chocolate', 'foodie',
    'gourmet', 'gourmet food', 'entertaining', 'cooking', 'drinking',
    'wine tasting', 'brewery', 'charcuterie', 'brunch',
}


def get_monthlyclubs_products_for_profile(profile):
    """
    Return MonthlyClubs subscription products when the profile has matching interests.

    TODO: Fill in real CJ link IDs from dashboard before enabling.
    Commission: 8-15%.
    """
    if any(p.get('_needs_real_link') for p in _MONTHLYCLUBS_ALL_PRODUCTS):
        logger.debug("MonthlyClubs products skipped — link IDs not yet filled in (see TODO in cj_searcher.py)")
        return []

    interests = profile.get('interests', [])
    interest_names = {i.get('name', '').lower() for i in interests if i.get('name')}

    matched = interest_names & _MONTHLYCLUBS_TRIGGER_INTERESTS
    if not matched:
        for name in interest_names:
            for trigger in _MONTHLYCLUBS_TRIGGER_INTERESTS:
                if trigger in name or name in trigger:
                    matched.add(name)
                    break

    if not matched:
        return []

    logger.info(f"MonthlyClubs triggered by profile interests: {matched}")

    # Select products relevant to matched interests
    relevant = []
    for p in _MONTHLYCLUBS_ALL_PRODUCTS:
        if p['interest_match'] in interest_names or any(t in interest_names for t in _MONTHLYCLUBS_TRIGGER_INTERESTS):
            relevant.append(p)

    return relevant[:2]  # Cap at 2 — subscription products take up significant card space


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
    'laptops', 'coding', 'programming', 'software', 'hardware', 'it',
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
                if trigger in name or name in trigger:
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
        return next(p for p in _TFL_ALL_PRODUCTS if p['product_id'] == pid)

    if is_gaming:
        return [_get('tfl-gaming'), _get('tfl-laptops')]
    elif is_photography:
        return [_get('tfl-cameras'), _get('tfl-home')]
    elif is_apple:
        return [_get('tfl-macbooks'), _get('tfl-home')]
    else:
        return [_get('tfl-laptops'), _get('tfl-home')]


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
        return next(p for p in _TENERGY_ALL_PRODUCTS if p['product_id'] == pid)

    if is_rc_or_drone:
        return [_get('tenergy-rc-hobby'), _get('tenergy-charger-kit')]
    elif is_kitchen:
        return [_get('tenergy-life-appliances'), _get('tenergy-rechargeable')]
    else:
        return [_get('tenergy-rechargeable'), _get('tenergy-charger-kit')]


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
        return next(p for p in _TRINITYROAD_ALL_PRODUCTS if p['product_id'] == pid)

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
        return [_get('catholicco-communion'), _get('catholicco-rosary')]
    elif is_confirmation:
        return [_get('catholicco-confirmation'), _get('catholicco-gifts')]
    elif is_baptism:
        return [_get('catholicco-baptism'), _get('catholicco-gifts')]
    elif is_coffee:
        return [_get('catholicco-coffee'), _get('catholicco-gifts')]
    elif is_adult_humor:
        return [_get('catholicco-saints-book'), _get('catholicco-rosary')]
    else:
        return [_get('catholicco-gifts'), _get('catholicco-rosary')]


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

    if is_goalkeeper:
        # Lead with goalkeeper gear, add cleats as second pick
        return [
            next(p for p in _SOCCERGARAGE_ALL_PRODUCTS if p['product_id'] == 'soccergarage-goalkeeper'),
            next(p for p in _SOCCERGARAGE_ALL_PRODUCTS if p['product_id'] == 'soccergarage-cleats'),
        ]
    elif is_youth_or_parent:
        # Lead with youth gear, add general homepage
        return [
            next(p for p in _SOCCERGARAGE_ALL_PRODUCTS if p['product_id'] == 'soccergarage-youth'),
            next(p for p in _SOCCERGARAGE_ALL_PRODUCTS if p['product_id'] == 'soccergarage-home'),
        ]
    else:
        # General soccer fan: cleats (highest AOV, most gifted) + homepage
        return [
            next(p for p in _SOCCERGARAGE_ALL_PRODUCTS if p['product_id'] == 'soccergarage-cleats'),
            next(p for p in _SOCCERGARAGE_ALL_PRODUCTS if p['product_id'] == 'soccergarage-home'),
        ]


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
