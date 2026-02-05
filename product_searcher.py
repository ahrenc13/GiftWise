"""
PRODUCT SEARCHER - EMERGENCY FIX
Filters out listicle articles and blog posts

CRITICAL FIXES:
1. Only use shopping_results (no blog posts)
2. Filter out "gift ideas" listicles
3. Better product-specific queries

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

MAX_CONCURRENT_SEARCHES = 5
SLEEP_BETWEEN_REQUESTS = 0.3
MAX_SEARCH_QUERIES = 10
INVENTORY_MULTIPLIER = 3

_product_cache = {}


def is_listicle_or_blog(title, url):
    """
    Check if this is a listicle article or blog post instead of a product
    
    CRITICAL: Filter out "gift ideas" articles
    """
    if not title or not url:
        return True
    
    title_lower = title.lower()
    url_lower = url.lower()
    
    # Listicle indicators in title
    listicle_phrases = [
        'gift ideas',
        'gift guide',
        'best gifts',
        'unique gifts',
        'gifts for',
        'perfect gifts',
        'top gifts',
        'gift list',
        'holiday gift',
        'christmas gift',
        'birthday gift',
        'valentines gift',
        'gift roundup',
        'actually useful gifts'
    ]
    
    for phrase in listicle_phrases:
        if phrase in title_lower:
            logger.debug(f"FILTERED LISTICLE (title): {title[:60]}")
            return True
    
    # Blog/article domains
    blog_domains = [
        'buzzfeed', 'bustle', 'refinery29', 'forbes', 'nytimes',
        'wirecutter', 'thegoodtrade', 'giftlab', 'giftguide',
        'blog.', '/blog/', 'article', 'news', 'magazine'
    ]
    
    for domain in blog_domains:
        if domain in url_lower:
            logger.debug(f"FILTERED BLOG (domain): {url[:60]}")
            return True
    
    # Article URL patterns
    if '/article/' in url_lower or '/blog/' in url_lower or '/news/' in url_lower:
        logger.debug(f"FILTERED ARTICLE (URL pattern): {url[:60]}")
        return True
    
    return False


def search_real_products(profile, serpapi_key, target_count=None, rec_count=10, validate_realtime=True):
    """
    Pull an inventory of real products (NOT listicles)
    
    EMERGENCY FIX: Only use shopping_results, filter out articles
    """
    if target_count is None:
        target_count = max(rec_count * INVENTORY_MULTIPLIER, 20)
    target_count = max(target_count, rec_count * 2)
    
    logger.info(f"Inventory target: {target_count} VALIDATED products (selecting {rec_count})")
    
    if not serpapi_key:
        logger.error("SerpAPI key not configured")
        return []
    
    logger.info(f"Searching for real products (SHOPPING RESULTS ONLY)...")
    
    search_queries = []
    interests = profile.get('interests', [])
    
    if not interests:
        logger.warning("No interests in profile - cannot search for products")
        return []
    
    # BETTER SEARCH QUERIES - More product-specific
    for interest in interests:
        name = interest.get('name', '')
        intensity = interest.get('intensity', 'moderate')
        interest_type = interest.get('type', 'current')
        
        if not name:
            continue
            
        priority = 'high' if intensity == 'passionate' else 'medium'
        
        # Product-specific queries (NOT "gift ideas")
        if interest_type == 'aspirational':
            search_queries.append({
                'query': f"{name} buy online shop",  # More product-focused
                'interest': name,
                'priority': priority
            })
        else:
            search_queries.append({
                'query': f"{name} product buy",  # Direct product query
                'interest': name,
                'priority': priority
            })
    
    # Brand queries
    brands = profile.get('style_preferences', {}).get('brands', [])
    for brand in brands[:2]:
        search_queries.append({
            'query': f"{brand} shop buy",
            'interest': brand,
            'priority': 'medium'
        })
    
    search_queries = search_queries[:MAX_SEARCH_QUERIES]
    logger.info(f"Generated {len(search_queries)} search queries (max {MAX_SEARCH_QUERIES})")
    
    def run_one_search_with_validation(query_info):
        """Run search and validate - SHOPPING RESULTS ONLY"""
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
                'tbm': 'shop'  # FORCE shopping results
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code != 200:
                logger.warning(f"Search failed: status={response.status_code} query={query[:50]}")
                return query_info, [], interest
            
            data = response.json()
            
            # ONLY use shopping_results (no organic results fallback)
            shopping_items = data.get('shopping_results', [])
            
            if not shopping_items:
                logger.warning(f"No shopping results for query: {query}")
                return query_info, [], interest
            
            for shop_item in shopping_items[:10]:
                title = shop_item.get('title', '')
                link = shop_item.get('link', '')
                
                # CRITICAL: Filter out listicles
                if is_listicle_or_blog(title, link):
                    continue
                
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
            
            return query_info, validated_products, interest
            
        except Exception as e:
            logger.error(f"Error searching for '{query}': {e}")
            return query_info, [], interest
    
    # Run searches in parallel
    all_products = []
    products_by_interest = defaultdict(list)
    validation_stats = {'checked': 0, 'passed': 0, 'failed': 0, 'listicles_filtered': 0}
    
    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_SEARCHES) as executor:
        for i in range(0, len(search_queries), MAX_CONCURRENT_SEARCHES):
            batch = search_queries[i:i + MAX_CONCURRENT_SEARCHES]
            futures = [executor.submit(run_one_search_with_validation, q) for q in batch]
            
            for future in as_completed(futures):
                _qinfo, results, _interest = future.result()
                
                for product, intr in results:
                    link = product.get('link', '')
                    
                    cache_key = hashlib.md5(link.encode()).hexdigest()[:16]
                    
                    if cache_key in _product_cache:
                        if _product_cache[cache_key]:
                            if not any(p['link'] == link for p in all_products):
                                all_products.append(product)
                                products_by_interest[intr].append(product)
                        continue
                    
                    validation_stats['checked'] += 1
                    
                    if is_bad_product_url(link):
                        logger.debug(f"Bad URL pattern: {link[:60]}")
                        _product_cache[cache_key] = False
                        validation_stats['failed'] += 1
                        continue
                    
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
    logger.info(f"Found {len(all_products)} REAL products (listicles filtered)")
    
    balanced_products = balance_products_by_interest(products_by_interest, target_count)
    
    logger.info(f"Balanced to {len(balanced_products)} products")
    
    return balanced_products


def extract_and_validate_product(item, query, interest, priority, is_shopping_result=False, validate_realtime=True):
    """Extract and validate - filter out listicles"""
    try:
        title = item.get('title', '')
        link = item.get('link', '')
        
        # Filter listicles at extraction time too
        if is_listicle_or_blog(title, link):
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
        
        if not product['title'] or not product['link']:
            return None
        
        if len(product['title']) < 10:
            return None
        
        if validate_realtime:
            if is_bad_product_url(product['link']):
                return None
            
            if not validate_url_exists(product['link'], timeout=3):
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
        r'\$\s?(\d+(?:,\d{3})*(?:\.\d{2})?)',
        r'(\d+(?:,\d{3})*(?:\.\d{2})?)\s?USD',
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