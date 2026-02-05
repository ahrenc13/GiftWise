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
import threading
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

# SerpAPI: balance UX speed with rate-limit safety (one retry on 429)
MAX_SEARCH_QUERIES = 5
SLEEP_BETWEEN_REQUESTS = 1.5
SLEEP_ON_RATE_LIMIT = 12
MAX_429_RETRIES = 1
INVENTORY_MULTIPLIER = 3

# At scale: minimum gap between ANY SerpAPI call (all users). Raise when you upgrade SerpAPI plan.
_serpapi_lock = threading.Lock()
_serpapi_last_call = 0.0
MIN_GAP_BETWEEN_SERPAPI_CALLS = float(os.environ.get('SERPAPI_MIN_GAP_SECONDS', '2.0'))

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
    serpapi_key = serpapi_key.strip()
    logger.info(f"SerpAPI key present (len={len(serpapi_key)})")
    
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
            response = None
            for attempt in range(MAX_429_RETRIES + 1):
                # Global rate limit: space out SerpAPI calls across all users so we don't 429 at scale
                with _serpapi_lock:
                    now = time.time()
                    wait = _serpapi_last_call + MIN_GAP_BETWEEN_SERPAPI_CALLS - now
                    if wait > 0:
                        if wait >= 1.0:
                            logger.info(f"SerpAPI: waiting {wait:.1f}s (another user just used the API)")
                        time.sleep(wait)
                    response = requests.get(url, params=params, timeout=10)
                    _serpapi_last_call = time.time()
                if response.status_code == 429 and attempt < MAX_429_RETRIES:
                    logger.warning(f"Rate limited (429) for: {query}, waiting {SLEEP_ON_RATE_LIMIT}s before retry {attempt + 1}/{MAX_429_RETRIES}")
                    time.sleep(SLEEP_ON_RATE_LIMIT)
                    continue
                break
            if response.status_code != 200:
                try:
                    body = response.text[:500] if response.text else ""
                    logger.warning(f"Search failed for: {query} status={response.status_code} body={body}")
                except Exception:
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
            if not shopping_items and isinstance(data, dict):
                logger.info(f"SerpAPI response keys for '{query}': {list(data.keys())}")
            raw_count = len(shopping_items)
            for item in shopping_items:
                if not isinstance(item, dict):
                    continue
                # SerpAPI Shopping can use 'link' (retailer) or 'product_link' (Google Shopping URL)
                link = (item.get('link') or item.get('product_link') or '').strip()
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
            logger.info(f"Search '{query}': {raw_count} raw -> {len(validated_products)} products")
            if raw_count > 0 and len(validated_products) == 0:
                first = shopping_items[0] if shopping_items else {}
                link = (first.get('link') or first.get('product_link') or '').strip()
                title = (first.get('title') or '').strip()
                logger.info(f"All filtered: sample link={link[:60]}... title={title[:50]}... (listicle={is_listicle_or_blog(title, link)}, bad_url={is_bad_product_url(link)})")
            return query_info, validated_products, interest
        except Exception as e:
            q = query_info.get('query', '?')
            logger.warning(f"Search error for {q}: {e}", exc_info=True)
            return query_info, [], interest

    all_products = []
    products_by_interest = defaultdict(list)
    for i, q in enumerate(search_queries):
        if i > 0:
            time.sleep(SLEEP_BETWEEN_REQUESTS)
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
    _elapsed = time.time() - _start
    logger.info(f"Found {len(balanced)} products in {_elapsed:.1f}s (validate_realtime={validate_realtime})")
    return balanced[:target_count]