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

_PEETS_EVERGREEN_BASE = "https://www.kqzyfj.com/click-101660899-15734720"
_PEETS_GIFT_BUNDLE_LINK = "https://www.kqzyfj.com/click-101660899-15596392"

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


# Static curated product list — curator will select at most 1-2 of these
_PEETS_ALL_PRODUCTS = [
    {
        'title': "Peet's Major Dickason's Blend Coffee",
        'link': _peets_deep_link('/products/major-dickasons-blend'),
        'snippet': (
            "Peet's most iconic dark roast — bold, rich, and complex with layered "
            "flavors. A cult favorite since 1969. Use code WEBFRIEND5 for 5% off."
        ),
        'image': '',
        'thumbnail': '',
        'image_url': '',
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
        'title': "Peet's Single Origin Coffee Subscription",
        'link': _peets_deep_link('/pages/coffee-subscriptions'),
        'snippet': (
            "Monthly delivery of Peet's single origin coffees — a rotating selection "
            "of the world's finest beans. Use code NEWSUB30 for 30% off the first shipment."
        ),
        'image': '',
        'thumbnail': '',
        'image_url': '',
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
        'title': "Mighty Leaf Whole Leaf Tea Collection by Peet's",
        'link': _peets_deep_link('/collections/tea'),
        'snippet': (
            "Whole-leaf tea pouches from Mighty Leaf, Peet's premium tea line — "
            "rare single-origin varieties and classic blends. Use code WEBFRIEND5 for 5% off."
        ),
        'image': '',
        'thumbnail': '',
        'image_url': '',
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
        'title': "Peet's Coffee Gift Set",
        'link': _PEETS_GIFT_BUNDLE_LINK,
        'snippet': (
            "Curated gift bundles from Peet's Coffee — premium coffees, teas, and "
            "accessories for the coffee lover in your life. Use code WEBFRIEND5 for 5% off."
        ),
        'image': '',
        'thumbnail': '',
        'image_url': '',
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
        'title': "Peet's Frequent Brewer Coffee Subscription",
        'link': _peets_deep_link('/pages/coffee-subscriptions'),
        'snippet': (
            "Subscribe and save on Peet's premium coffees — choose your roast, grind, "
            "and delivery frequency. First shipment 30% off with code NEWSUB30."
        ),
        'image': '',
        'thumbnail': '',
        'image_url': '',
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

                # Extract affiliate tracking link
                # linkCode is None for advertisers you haven't joined
                link_code = item.get('linkCode')
                if link_code and isinstance(link_code, dict):
                    tracking_url = link_code.get('clickUrl', '')
                else:
                    tracking_url = ''

                # Fall back to direct link if no tracking link
                if not tracking_url:
                    tracking_url = item.get('link', '')

                # Skip products without any link
                if not tracking_url:
                    logger.warning(f"Skipping product without link: {item.get('title')}")
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
    if not api_key:
        logger.warning("CJ API key not provided - skipping CJ search")
        return []

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

    # Inject Peet's static curated products (no product feed via CJ)
    peets_products = get_peets_products_for_profile(profile)
    if peets_products:
        all_products.extend(peets_products)
        logger.info(f"Added {len(peets_products)} Peet's Coffee static products")

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
