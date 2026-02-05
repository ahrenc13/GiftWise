"""
PRODUCT SEARCHER - MINIMAL FILTERING
Stop overthinking it. Just get products.

FILTERING:
- Only blocks if URL contains /blog/, /article/, or known blog domains
- That's it. No title checking. No clever patterns.

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
    MINIMAL filtering - only block obvious blog URLs
    """
    if not url:
        return True
    
    url_lower = url.lower()
    
    # Only block if URL path contains these
    if '/blog/' in url_lower or '/article/' in url_lower:
        return True
    
    # Block known blog domains
    if any(d in url_lower for d in ['buzzfeed.com', 'wirecutter.com', 'bustle.com']):
        return True
    
    return False


def search_real_products(profile, serpapi_key, target_count=None, rec_count=10, validate_realtime=True):
    """Pull inventory"""
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
                logger.warning(f"Search failed for: {query} status={response.status_code}")
                return query_info, [], interest
            
            try:
                data = response.json()
            except Exception as parse_err:
                logger.warning(f"Search response not JSON for: {query} err={parse_err}")
                return query_info, [], interest
            if not isinstance(data, dict):
                logger.warning(f"Unexpected search response for: {query}")
                return query_info, [], interest
            shopping_items = data.get('shopping_results') or data.get('organic_results') or []
            if not isinstance(shopping_items, list):
                shopping_items = []
            for item in shopping_items:
                if not isinstance(item, dict):
                    continue
                link = (item.get('link') or '').strip()
                if not link:
                    continue
                title = (item.get('title') or '').strip()
                if is_listicle_or_blog(title, link):
                    continue
                if is_bad_product_url(link):
                    continue
                if validate_realtime and not validate_url_exists(link, timeout=3):
                    continue
                product = {
                    'title': title,
                    'link': link,
                    'snippet': item.get('snippet', ''),
                    'image': item.get('thumbnail', '') or item.get('image', ''),
                    'source_domain': (urlparse(link).netloc or '').replace('www.', ''),
                    'search_query': query,
                    'interest_match': interest,
                    'priority': query_info.get('priority', 'medium'),
                    'price': item.get('price', ''),
                }
                validated_products.append(product)
            return query_info, validated_products, interest
        except Exception as e:
            q = query_info.get('query', '?')
            logger.warning(f"Search error for {q}: {e}", exc_info=True)
            return query_info, [], interest

    all_products = []
    products_by_interest = defaultdict(list)
    for q in search_queries:
        _qinfo, results, interest = run_one_search_with_validation(q)
        for p in results:
            if not any(x.get('link') == p.get('link') for x in all_products):
                all_products.append(p)
                products_by_interest[interest].append(p)
    if not all_products:
        logger.warning("No products collected from search")
        return []
    num_interests = len(products_by_interest) or 1
    per_interest = max(2, target_count // num_interests)
    balanced = []
    for interest, prods in products_by_interest.items():
        balanced.extend(prods[:per_interest])
    if len(balanced) < target_count:
        for interest, prods in products_by_interest.items():
            for p in prods:
                if p not in balanced:
                    balanced.append(p)
                    if len(balanced) >= target_count:
                        break
            if len(balanced) >= target_count:
                break
    logger.info(f"Found {len(balanced)} products (validate_realtime={validate_realtime})")
    return balanced[:target_count]