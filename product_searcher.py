"""
PRODUCT SEARCHER - MINIMAL FILTERING + VISIBLE LOGS
Shows exactly what's being filtered so we can debug

CHANGES:
- Changed logger.debug() to logger.info() for visibility
- MUCH less aggressive filtering
- Only blocks OBVIOUS listicles with numbers (e.g., "77 gift ideas")

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
import re

try:
    from link_validation import is_bad_product_url, validate_url_exists
except ImportError:
    def is_bad_product_url(url):
        return False
    def validate_url_exists(url, timeout=3):
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

MAX_CONCURRENT_SEARCHES = 5
SLEEP_BETWEEN_REQUESTS = 0.3
MAX_SEARCH_QUERIES = 10
INVENTORY_MULTIPLIER = 3

_product_cache = {}


def is_listicle_or_blog(title, url):
    """
    MINIMAL filtering - only block OBVIOUS blog posts
    
    Returns True ONLY for clear listicles with numbers
    """
    if not title or not url:
        return True
    
    title_lower = title.lower()
    url_lower = url.lower()
    
    # ONLY block numbered listicles (e.g., "77 gift ideas", "25 best gifts")
    numbered_listicle = re.search(r'\d+\s+(best|top|unique|great)\s+gift', title_lower)
    if numbered_listicle:
        logger.info(f"❌ FILTERED numbered listicle: {title[:70]}")
        return True
    
    # Block obvious gift guide phrases
    if 'gift guide' in title_lower or 'gift ideas for 20' in title_lower:
        logger.info(f"❌ FILTERED gift guide: {title[:70]}")
        return True
    
    # Block known blog domains
    blog_domains = ['buzzfeed', 'bustle', 'wirecutter', 'giftlab']
    for domain in blog_domains:
        if domain in url_lower:
            logger.info(f"❌ FILTERED blog domain: {url[:70]}")
            return True
    
    # Otherwise allow it
    return False


def search_real_products(profile, serpapi_key, target_count=None, rec_count=10, validate_realtime=True):
    """Pull inventory with MINIMAL filtering"""
    if target_count is None:
        target_count = max(rec_count * INVENTORY_MULTIPLIER, 20)
    target_count = max(target_count, rec_count * 2)
    
    logger.info(f"Inventory target: {target_count} products")
    
    if not serpapi_key:
        logger.error("SerpAPI key not configured")
        return []
    
    search_queries = []
    interests = profile.get('interests', [])
    
    if not interests:
        logger.warning("No interests in profile")
        return []
    
    # Simple queries
    for interest in interests:
        name = interest.get('name', '')
        if not name:
            continue
            
        intensity = interest.get('intensity', 'moderate')
        priority = 'high' if intensity == 'passionate' else 'medium'
        
        search_queries.append({
            'query': f"{name} buy",
            'interest': name,
            'priority': priority
        })
    
    search_queries = search_queries[:MAX_SEARCH_QUERIES]
    logger.info(f"Running {len(search_queries)} searches")
    
    def run_one_search_with_validation(query_info):
        query = query_info['query']
        interest = query_info['interest']
        validated_products = []
        
        try:
            url = "https://serpapi.com/search"
            params = {
                'q': query,
                'api_key': serpapi_key,
                'num': 10,
                'engine': 'google',
                'gl': 'us',
                'hl': 'en',
                'tbm': 'shop'
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code != 200:
                logger.warning(f"Search failed for: {query}")
                return query_info, [], interest
            
            data = response.json()
            shopping_items = data.get('shopping_results', [])
            
            if not shopping_items:
                logger.warning(f"No shopping results for: {query}")
                return query_info, [], interest
            
            logger.info(f"✓ Got {len(shopping_items)} results for: {query}")
            
            # Process each result
            for i, shop_item in enumerate(shopping_items[:10]):
                title = shop_item.get('title', '')
                link = shop_item.get('link', '')
                
                logger.info(f"  [{i+1}] Checking: {title[:60]}...")
                
                # Minimal filtering
                if is_listicle_or_blog(title, link):
                    continue
                
                # Extract product
                product = extract_and_validate_product(
                    shop_item,
                    query,
                    interest,
                    query_info['priority'],
                    validate_realtime=validate_realtime
                )
                
                if product:
                    validated_products.append((product, interest))
                    logger.info(f"  ✓ VALIDATED: {title[:60]}")
                else:
                    logger.info(f"  ✗ Failed validation: {title[:60]}")
            
            logger.info(f"Final: {len(validated_products)} products validated for '{interest}'")
            return query_info, validated_products, interest
            
        except Exception as e:
            logger.error(f"Error searching '{query}': {e}")
            return query_info, [], interest
    
    # Run searches
    all_products = []
    products_by_interest = defaultdict(list)
    
    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_SEARCHES) as executor:
        for i in range(0, len(search_queries), MAX_CONCURRENT_SEARCHES):
            batch = search_queries[i:i + MAX_CONCURRENT_SEARCHES]
            futures = [executor.submit(run_one_search_with_validation, q) for q in batch]
            
            for future in as_completed(futures):
                _qinfo, results, _interest = future.result()
                
                for product, intr in results:
                    link = product.get('link', '')
                    if not any(p['link'] == link for p in all_products):
                        all_products.append(product)
                        products_by_interest[intr].append(product)
            
            if i + MAX_CONCURRENT_SEARCHES < len(search_queries):
                time.sleep(SLEEP_BETWEEN_REQUESTS)
    
    logger.info(f"TOTAL: Found {len(all_products)} products")
    
    balanced_products = balance_products_by_interest(products_by_interest, target_count)
    logger.info(f"Balanced to {len(balanced_products)} products")
    
    return balanced_products


def extract_and_validate_product(item, query, interest, priority, validate_realtime=True):
    """Extract and validate product"""
    try:
        title = item.get('title', '')
        link = item.get('link', '')
        
        if not title or not link:
            return None
        
        if len(title) < 10:
            return None
        
        product = {
            'title': title,
            'link': link,
            'snippet': item.get('snippet', ''),
            'image': item.get('thumbnail', ''),
            'source_domain': extract_domain(link),
            'search_query': query,
            'interest_match': interest,
            'priority': priority,
            'price': item.get('price', '')
        }
        
        # Real-time validation
        if validate_realtime:
            if is_bad_product_url(product['link']):
                return None
            
            if not validate_url_exists(product['link'], timeout=3):
                return None
        
        return product
        
    except Exception as e:
        logger.error(f"Error extracting product: {e}")
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


def balance_products_by_interest(products_by_interest, target_count):
    """Balance products across interests"""
    if not products_by_interest:
        return []
    
    num_interests = len(products_by_interest)
    products_per_interest = max(2, target_count // num_interests)
    
    balanced = []
    
    for interest, products in products_by_interest.items():
        sorted_products = sorted(
            products,
            key=lambda p: 0 if p.get('priority') == 'high' else 1
        )
        balanced.extend(sorted_products[:products_per_interest])
    
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
