"""
PRODUCT SEARCHER - Find Real Products Using SerpAPI (Google Search)
Searches for actual products based on recipient profile interests

Author: Chad + Claude
Date: February 2026
"""

import requests
import logging
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from link_validation import is_bad_product_url
except ImportError:
    def is_bad_product_url(url):
        return False

logger = logging.getLogger(__name__)

# Max concurrent SerpAPI requests (stay within rate limits)
MAX_CONCURRENT_SEARCHES = 5
# Sleep between batches to avoid rate limits
SLEEP_BETWEEN_REQUESTS = 0.3
# Cap total queries for speed
MAX_SEARCH_QUERIES = 10


def search_real_products(profile, serpapi_key, target_count=40):
    """
    Search for real products using SerpAPI (Google Search) based on recipient profile.
    
    Args:
        profile: Recipient profile dict from build_recipient_profile()
        serpapi_key: SerpAPI API key
        target_count: Target number of products to find (default 40)
    
    Returns:
        List of product dicts with:
        - title: Product name
        - link: Direct product URL
        - snippet: Product description
        - image: Product image URL
        - price: Extracted price if available
        - source_domain: Where it's from
        - search_query: What query found it
        - interest_match: Which interest(s) it matches
    """
    
    if not serpapi_key:
        logger.error("SerpAPI key not configured")
        return []
    
    logger.info(f"Searching for real products based on profile interests...")
    
    # Build search queries from interests
    search_queries = []
    
    interests = profile.get('interests', [])
    if not interests:
        logger.warning("No interests in profile - cannot search for products")
        return []
    
    # Generate targeted search queries (varied phrasing to avoid only "first Google result" feel)
    for interest in interests:
        name = interest.get('name', '')
        intensity = interest.get('intensity', 'moderate')
        interest_type = interest.get('type', 'current')
        if not name:
            continue
        priority = 'high' if intensity == 'passionate' else 'medium'
        if interest_type == 'aspirational':
            search_queries.append({'query': f"thoughtful gift for someone who loves {name}", 'interest': name, 'priority': priority})
            search_queries.append({'query': f"{name} starter kit unique", 'interest': name, 'priority': priority})
        else:
            search_queries.append({'query': f"thoughtful gift for someone who loves {name}", 'interest': name, 'priority': priority})
            search_queries.append({'query': f"unusual {name} gift not generic", 'interest': name, 'priority': priority})
    
    brands = profile.get('style_preferences', {}).get('brands', [])
    for brand in brands[:2]:
        search_queries.append({'query': f"{brand} gift", 'interest': brand, 'priority': 'medium'})
    
    search_queries = search_queries[:MAX_SEARCH_QUERIES]
    logger.info(f"Generated {len(search_queries)} search queries (max {MAX_SEARCH_QUERIES})")
    
    def run_one_search(query_info):
        query = query_info['query']
        interest = query_info['interest']
        try:
            url = "https://serpapi.com/search"
            params = {'q': query, 'api_key': serpapi_key, 'num': 10, 'engine': 'google', 'gl': 'us', 'hl': 'en'}
            response = requests.get(url, params=params, timeout=10)
            if response.status_code != 200:
                # Log generic message so server logs don't expose "Google" / "no access" to operators
                logger.warning(
                    "Product search request failed: status=%s query=%s (check API key and quota)",
                    response.status_code, query[:50]
                )
                logger.debug(
                    "SerpAPI response: %s",
                    response.text[:300] if response.text else "empty"
                )
                return query_info, [], interest
            data = response.json()
            items = data.get('organic_results', [])
            shopping_items = data.get('shopping_results', [])
            results = []
            if shopping_items:
                for shop_item in shopping_items[:10]:
                    product = {
                        'title': shop_item.get('title', ''),
                        'link': shop_item.get('link', ''),
                        'snippet': shop_item.get('snippet', ''),
                        'image': shop_item.get('thumbnail', ''),
                        'source_domain': extract_domain(shop_item.get('link', '')),
                        'search_query': query,
                        'interest_match': interest,
                        'priority': query_info['priority'],
                        'price': shop_item.get('price', '')
                    }
                    results.append((product, interest))
            else:
                for item in items[:10]:
                    image_url = item.get('thumbnail', '')
                    product = {
                        'title': item.get('title', ''),
                        'link': item.get('link', ''),
                        'snippet': item.get('snippet', ''),
                        'image': image_url,
                        'source_domain': extract_domain(item.get('link', '')),
                        'search_query': query,
                        'interest_match': interest,
                        'priority': query_info['priority']
                    }
                    price = extract_price(item.get('snippet', ''))
                    if price:
                        product['price'] = price
                    results.append((product, interest))
            return query_info, results, interest
        except Exception as e:
            logger.error(f"Error searching for '{query}': {e}")
            return query_info, [], interest
    
    all_products = []
    products_by_interest = defaultdict(list)
    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_SEARCHES) as executor:
        for i in range(0, len(search_queries), MAX_CONCURRENT_SEARCHES):
            batch = search_queries[i:i + MAX_CONCURRENT_SEARCHES]
            futures = [executor.submit(run_one_search, q) for q in batch]
            for future in as_completed(futures):
                _qinfo, results, _interest = future.result()
                for product, intr in results:
                    link = product.get('link', '')
                    if is_bad_product_url(link):
                        logger.debug(f"Skipping bad product URL: {link[:60]}...")
                        continue
                    if not any(p['link'] == link for p in all_products):
                        all_products.append(product)
                        products_by_interest[intr].append(product)
            if i + MAX_CONCURRENT_SEARCHES < len(search_queries):
                time.sleep(SLEEP_BETWEEN_REQUESTS)
    
    logger.info(f"Found {len(all_products)} total products across {len(products_by_interest)} interests")
    
    # Ensure diverse representation across interests
    balanced_products = balance_products_by_interest(products_by_interest, target_count)
    
    logger.info(f"Balanced to {len(balanced_products)} products with diverse interest coverage")
    
    return balanced_products


def extract_domain(url):
    """Extract domain from URL"""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.netloc
        # Remove www.
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain
    except:
        return 'unknown'


def extract_price(text):
    """Extract price from text snippet"""
    import re
    
    # Look for price patterns like $XX.XX or $XX
    price_patterns = [
        r'\$\s?(\d+(?:,\d{3})*(?:\.\d{2})?)',  # $XX.XX or $XX
        r'(\d+(?:,\d{3})*(?:\.\d{2})?)\s?USD',  # XX.XX USD
    ]
    
    for pattern in price_patterns:
        match = re.search(pattern, text)
        if match:
            price_str = match.group(1).replace(',', '')
            try:
                price = float(price_str)
                return f"${price:.2f}"
            except:
                pass
    
    return None


def balance_products_by_interest(products_by_interest, target_count):
    """
    Balance products to ensure diverse coverage across interests.
    Avoids having all products from one interest category.
    """
    
    if not products_by_interest:
        return []
    
    # Calculate products per interest
    num_interests = len(products_by_interest)
    products_per_interest = max(2, target_count // num_interests)
    
    balanced = []
    
    # Take products from each interest, prioritizing high-priority queries
    for interest, products in products_by_interest.items():
        # Sort by priority
        sorted_products = sorted(products, key=lambda p: 0 if p.get('priority') == 'high' else 1)
        balanced.extend(sorted_products[:products_per_interest])
    
    # If we haven't hit target, add more from high-priority
    if len(balanced) < target_count:
        all_remaining = []
        for interest, products in products_by_interest.items():
            for p in products:
                if p not in balanced and p.get('priority') == 'high':
                    all_remaining.append(p)
        
        needed = target_count - len(balanced)
        balanced.extend(all_remaining[:needed])
    
    return balanced[:target_count]
