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
from collections import deque
import requests
import json

logger = logging.getLogger(__name__)

# CJ GraphQL API endpoint
CJ_GRAPHQL_ENDPOINT = "https://ads.api.cj.com/query"

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
