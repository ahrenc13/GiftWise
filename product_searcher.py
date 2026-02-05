"""
PRODUCT SEARCHER - DEBUG VERSION
Shows exactly what's being filtered and why

Author: Chad + Claude  
Date: February 2026
"""

import requests
import logging
import time
from collections import defaultdict
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

MAX_SEARCH_QUERIES = 10
INVENTORY_MULTIPLIER = 3


def is_listicle_or_blog(title, url):
    """Only block obvious blog URLs"""
    if not url:
        return True
    url_lower = url.lower()
    if '/blog/' in url_lower or '/article/' in url_lower:
        return True
    if any(d in url_lower for d in ['buzzfeed.com', 'wirecutter.com', 'bustle.com']):
        return True
    return False


def search_real_products(profile, serpapi_key, target_count=None, rec_count=10, validate_realtime=False):
    """Pull inventory - no validation, no rate limiting"""
    if target_count is None:
        target_count = max(rec_count * INVENTORY_MULTIPLIER, 20)
    
    logger.info(f"Inventory target: {target_count} products")
    
    if not serpapi_key:
        logger.error("SerpAPI key not configured")
        return []
    
    interests = profile.get('interests', [])
    if not interests:
        logger.warning("No interests in profile")
        return []
    
    search_queries = []
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
    
    all_products = []
    products_by_interest = defaultdict(list)
    
    for query_info in search_queries:
        query = query_info['query']
        interest = query_info['interest']
        
        try:
            response = requests.get(
                "https://serpapi.com/search",
                params={
                    'q': query,
                    'api_key': serpapi_key,
                    'num': 10,
                    'engine': 'google',
                    'gl': 'us',
                    'hl': 'en',
                    'tbm': 'shop'
                },
                timeout=10
            )
            
            if response.status_code != 200:
                logger.warning(f"Search failed for: {query} status={response.status_code}")
                continue
            
            data = response.json()
            shopping_items = data.get('shopping_results', [])
            
            if not shopping_items:
                logger.warning(f"No shopping results for: {query}")
                continue
            
            logger.info(f"Got {len(shopping_items)} results for: {query}")
            
            for i, item in enumerate(shopping_items[:10]):
                title = item.get('title', '').strip()
                link = (item.get('link') or item.get('product_link') or '').strip()
                
                logger.info(f"  [{i+1}] Checking: {title[:60]}...")
                logger.info(f"       Link: {link[:80]}...")
                
                if not title or not link:
                    logger.info(f"  [{i+1}] ❌ SKIPPED: Missing title or link")
                    continue
                
                if is_listicle_or_blog(title, link):
                    logger.info(f"  [{i+1}] ❌ SKIPPED: Listicle/blog filter")
                    continue
                
                product = {
                    'title': title,
                    'link': link,
                    'snippet': item.get('snippet', ''),
                    'image': item.get('thumbnail', ''),
                    'source_domain': urlparse(link).netloc.replace('www.', ''),
                    'search_query': query,
                    'interest_match': interest,
                    'priority': query_info['priority'],
                    'price': item.get('price', '')
                }
                
                if not any(p['link'] == link for p in all_products):
                    all_products.append(product)
                    products_by_interest[interest].append(product)
                    logger.info(f"  [{i+1}] ✅ ADDED product")
                else:
                    logger.info(f"  [{i+1}] ❌ SKIPPED: Duplicate link")
            
            logger.info(f"Total added for '{interest}': {len(products_by_interest[interest])} products")
            time.sleep(0.5)
            
        except Exception as e:
            logger.error(f"Error searching '{query}': {e}")
            continue
    
    if not all_products:
        logger.warning("No products collected")
        return []
    
    num_interests = len(products_by_interest)
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
    
    logger.info(f"Found {len(balanced)} products total")
    return balanced[:target_count]