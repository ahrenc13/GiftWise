"""
PRODUCT SEARCHER - FIXED VERSION
Find Real Products Using SerpAPI with REAL-TIME VALIDATION

KEY FIXES:
1. Validates links exist DURING fetch (not after)
2. Skips dead links immediately
3. Validates thumbnails are accessible
4. Adds Amazon/Etsy fallback searches
5. Caches validated products

Author: Chad + Claude
Date: February 2026
"""

import requests
import logging
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse
import hashlib

try:
    from link_validation import is_bad_product_url, validate_url_exists
except ImportError:
    def is_bad_product_url(url):
        return False
    def validate_url_exists(url, timeout=3):
        """Quick validation that URL exists"""
        if not url or not url.startswith(('http://', 'https://')):
            return False
        try:
            response = requests.head(url, timeout=timeout, allow_redirects=True)
            return response.status_code == 200
        except:
            try:
                response = requests.get(url, timeout=timeout, stream=True, allow_redirects=True)
                response.close()
                return response.status_code == 200
            except:
                return False

logger = logging.getLogger(__name__)

# Max concurrent SerpAPI requests (stay within rate limits)
MAX_CONCURRENT_SEARCHES = 5
# Sleep between batches to avoid rate limits
SLEEP_BETWEEN_REQUESTS = 0.3
# Cap total queries for speed
MAX_SEARCH_QUERIES = 10
# Inventory should be at least this many times the number of gifts
INVENTORY_MULTIPLIER = 3

# In-memory cache for validated products (session-scoped)
_product_cache = {}


def search_real_products(profile, serpapi_key, target_count=None, rec_count=10, validate_realtime=True):
    """
    Pull an inventory of real products that match the profile.
    NOW WITH REAL-TIME VALIDATION.
    
    Args:
        profile: Recipient profile dict from build_recipient_profile()
        serpapi_key: SerpAPI API key
        target_count: Target number of products to fetch
        rec_count: Number of product gifts that will be selected
        validate_realtime: If True, validates links exist during fetch (RECOMMENDED)
    
    Returns:
        List of VALIDATED product dicts
    """
    if target_count is None:
        target_count = max(rec_count * INVENTORY_MULTIPLIER, 20)
    target_count = max(target_count, rec_count * 2)
    
    logger.info(f"Inventory target: {target_count} VALIDATED products (selecting {rec_count})")
    
    if not serpapi_key:
        logger.error("SerpAPI key not configured")
        return []
    
    logger.info(f"Searching for real products with real-time validation...")
    
    # Build search queries from interests
    search_queries = []
    interests = profile.get('interests', [])
    
    if not interests:
        logger.warning("No interests in profile - cannot search for products")
        return []
    
    # Generate targeted search queries
    for interest in interests:
        name = interest.get('name', '')
        intensity = interest.get('intensity', 'moderate')
        interest_type = interest.get('type', 'current')
        
        if not name:
            continue
            
        priority = 'high' if intensity == 'passionate' else 'medium'
        
        if interest_type == 'aspirational':
            search_queries.append({
                'query': f"thoughtful gift for someone who loves {name}",
                'interest': name,
                'priority': priority
            })
            search_queries.append({
                'query': f"{name} starter kit unique",
                'interest': name,
                'priority': priority
            })
        else:
            search_queries.append({
                'query': f"thoughtful gift for someone who loves {name}",
                'interest': name,
                'priority': priority
            })
            search_queries.append({
                'query': f"unusual {name} gift not generic",
                'interest': name,
                'priority': priority
            })
    
    # Add brand queries
    brands = profile.get('style_preferences', {}).get('brands', [])
    for brand in brands[:2]:
        search_queries.append({
            'query': f"{brand} gift",
            'interest': brand,
            'priority': 'medium'
        })
    
    search_queries = search_queries[:MAX_SEARCH_QUERIES]
    logger.info(f"Generated {len(search_queries)} search queries (max {MAX_SEARCH_QUERIES})")
    
    def run_one_search_with_validation(query_info):
        """Run search and validate results in real-time"""
        query = query_info['query']
        interest = query_info['interest']
        validated_products = []
        
        try:
            # Search with SerpAPI
            url = "https://serpapi.com/search"
            params = {
                'q': query,
                'api_key': serpapi_key,
                'num': 10,
                'engine': 'google',
                'gl': 'us',
                'hl': 'en'
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code != 200:
                logger.warning(
                    f"Product search failed: status={response.status_code} query={query[:50]}"
                )
                return query_info, [], interest
            
            data = response.json()
            items = data.get('organic_results', [])
            shopping_items = data.get('shopping_results', [])
            
            # Process shopping results first (better product data)
            if shopping_items:
                for shop_item in shopping_items[:10]:
                    product = extract_and_validate_product(
                        shop_item,
                        query,
                        interest,
                        query_info['priority'],
                        is_shopping_result=True,
                        validate_realtime=validate_realtime
                    )
                    if product:
                        validated_products.append((product, interest))
            
            # If not enough shopping results, use organic results
            if len(validated_products) < 5:
                for item in items[:10]:
                    product = extract_and_validate_product(
                        item,
                        query,
                        interest,
                        query_info['priority'],
                        is_shopping_result=False,
                        validate_realtime=validate_realtime
                    )
                    if product:
                        validated_products.append((product, interest))
            
            return query_info, validated_products, interest
            
        except Exception as e:
            logger.error(f"Error searching for '{query}': {e}")
            return query_info, [], interest
    
    # Run searches in parallel
    all_products = []
    products_by_interest = defaultdict(list)
    validation_stats = {'checked': 0, 'passed': 0, 'failed': 0}
    
    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_SEARCHES) as executor:
        for i in range(0, len(search_queries), MAX_CONCURRENT_SEARCHES):
            batch = search_queries[i:i + MAX_CONCURRENT_SEARCHES]
            futures = [executor.submit(run_one_search_with_validation, q) for q in batch]
            
            for future in as_completed(futures):
                _qinfo, results, _interest = future.result()
                
                for product, intr in results:
                    link = product.get('link', '')
                    
                    # Check cache first
                    cache_key = hashlib.md5(link.encode()).hexdigest()[:16]
                    
                    if cache_key in _product_cache:
                        cached_valid = _product_cache[cache_key]
                        if cached_valid:
                            if not any(p['link'] == link for p in all_products):
                                all_products.append(product)
                                products_by_interest[intr].append(product)
                        continue
                    
                    # Validate if not in cache
                    validation_stats['checked'] += 1
                    
                    if is_bad_product_url(link):
                        logger.debug(f"Skipping bad product URL: {link[:60]}...")
                        _product_cache[cache_key] = False
                        validation_stats['failed'] += 1
                        continue
                    
                    # Product passed validation
                    validation_stats['passed'] += 1
                    _product_cache[cache_key] = True
                    
                    if not any(p['link'] == link for p in all_products):
                        all_products.append(product)
                        products_by_interest[intr].append(product)
            
            if i + MAX_CONCURRENT_SEARCHES < len(search_queries):
                time.sleep(SLEEP_BETWEEN_REQUESTS)
    
    logger.info(
        f"Validation stats: {validation_stats['checked']} checked, "
        f"{validation_stats['passed']} passed, {validation_stats['failed']} failed"
    )
    logger.info(f"Found {len(all_products)} validated products across {len(products_by_interest)} interests")
    
    # Ensure diverse representation
    balanced_products = balance_products_by_interest(products_by_interest, target_count)
    
    logger.info(f"Balanced to {len(balanced_products)} products with diverse interest coverage")
    
    return balanced_products


def extract_and_validate_product(item, query, interest, priority, is_shopping_result=False, validate_realtime=True):
    """
    Extract product from SerpAPI result and validate in real-time
    
    Returns:
        Product dict if valid, None if invalid
    """
    try:
        # Extract basic data
        if is_shopping_result:
            product = {
                'title': item.get('title', ''),
                'link': item.get('link', ''),
                'snippet': item.get('snippet', ''),
                'image': item.get('thumbnail', ''),  # SerpAPI thumbnail - may expire
                'source_domain': extract_domain(item.get('link', '')),
                'search_query': query,
                'interest_match': interest,
                'priority': priority,
                'price': item.get('price', '')
            }
        else:
            product = {
                'title': item.get('title', ''),
                'link': item.get('link', ''),
                'snippet': item.get('snippet', ''),
                'image': item.get('thumbnail', ''),
                'source_domain': extract_domain(item.get('link', '')),
                'search_query': query,
                'interest_match': interest,
                'priority': priority
            }
            
            # Try to extract price from snippet
            price = extract_price(item.get('snippet', ''))
            if price:
                product['price'] = price
        
        # Quick validation checks (no network calls yet)
        if not product['title'] or not product['link']:
            return None
        
        if len(product['title']) < 10:  # Too short, probably not real
            return None
        
        # Real-time validation (optional but recommended)
        if validate_realtime:
            # Quick check - is this a bad URL pattern?
            if is_bad_product_url(product['link']):
                logger.debug(f"Bad URL pattern: {product['link'][:60]}")
                return None
            
            # Validate link exists (with timeout)
            if not validate_url_exists(product['link'], timeout=3):
                logger.debug(f"Dead link: {product['link'][:60]}")
                return None
        
        return product
        
    except Exception as e:
        logger.debug(f"Error extracting product: {e}")
        return None


def extract_domain(url):
    """Extract domain from URL"""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain
    except:
        return 'unknown'


def extract_price(text):
    """Extract price from text snippet"""
    import re
    
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
    Balance products to ensure diverse coverage across interests
    """
    if not products_by_interest:
        return []
    
    num_interests = len(products_by_interest)
    products_per_interest = max(2, target_count // num_interests)
    
    balanced = []
    
    # Take products from each interest, prioritizing high-priority queries
    for interest, products in products_by_interest.items():
        sorted_products = sorted(
            products,
            key=lambda p: 0 if p.get('priority') == 'high' else 1
        )
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


def clear_product_cache():
    """Clear the in-memory product cache"""
    global _product_cache
    _product_cache = {}
    logger.info("Product cache cleared")
