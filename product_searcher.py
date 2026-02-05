"""
PRODUCT SEARCHER - FAST VERSION
Gets products quickly, no validation

Author: Chad + Claude  
Date: February 2026
"""

import requests
import logging
import time
import re
from collections import defaultdict
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

MAX_SEARCH_QUERIES = 10
INVENTORY_MULTIPLIER = 2  # Changed from 3 to reduce curation time


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
    """Pull inventory - FAST, no validation"""
    start_time = time.time()
    
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
        
        # Skip work interests - we don't want to search for work-related products
        if interest.get('is_work', False):
            logger.info(f"Skipping work interest: {name}")
            continue
        
        intensity = interest.get('intensity', 'moderate')
        priority = 'high' if intensity == 'passionate' else 'medium'
        
        # Make query more gift-oriented
        # Instead of "{name} buy", use gift-related terms
        name_lower = name.lower()
        
        # For artists/musicians/celebrities: use "merchandise" or "merch"
        if any(term in name_lower for term in ['artist', 'musician', 'singer', 'band', 'celebrity', 'roan', 'swift', 'nicks']):
            query = f"{name} merchandise gifts"
        # For sports teams/athletes: use "memorabilia" or "merchandise"
        elif any(term in name_lower for term in ['team', 'sports', 'basketball', 'football', 'baseball', 'pacers', 'indycar']):
            query = f"{name} memorabilia gifts"
        # For hobbies/activities: use "gifts for"
        elif any(term in name_lower for term in ['owner', 'enthusiast', 'lover', 'fan']):
            query = f"gifts for {name}"
        # For locations/travel: use "souvenirs" or "gifts"
        elif any(term in name_lower for term in ['wisconsin', 'michigan', 'travel', 'cruise', 'vacation']):
            query = f"{name} souvenirs gifts"
        # Default: just add "gifts"
        else:
            query = f"{name} gifts"
        
        search_queries.append({
            'query': query,
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
                    'q': f"{query} site:amazon.com OR site:etsy.com OR site:ebay.com",
                    'api_key': serpapi_key,
                    'num': 10,
                    'engine': 'google',
                    'gl': 'us',
                    'hl': 'en'
                },
                timeout=10
            )
            
            if response.status_code != 200:
                logger.warning(f"Search failed for: {query} status={response.status_code}")
                continue
            
            data = response.json()
            shopping_items = data.get('organic_results', [])
            
            # Debug: log first item structure to understand response format
            if shopping_items and len(all_products) == 0:
                logger.info(f"Sample SerpAPI response keys: {list(shopping_items[0].keys())}")
                sample_link = shopping_items[0].get('link', '')
                logger.info(f"Sample link field: {sample_link[:100]}")
            
            if not shopping_items:
                logger.warning(f"No results for: {query}")
                continue
            
            for item in shopping_items[:10]:
                title = item.get('title', '').strip()
                link = item.get('link', '').strip()
                snippet = item.get('snippet', '').strip()
                
                if not title or not link:
                    continue
                
                # Filter out non-product pages
                link_lower = link.lower()
                if not any(retailer in link_lower for retailer in ['amazon.com', 'etsy.com', 'ebay.com']):
                    continue
                    
                # Skip listing/search pages - we want specific product pages
                if any(bad in link_lower for bad in ['/s?', '/search', '/sr?', '/sch/i.html']):
                    continue
                
                if is_listicle_or_blog(title, link):
                    continue
                
                # Try to extract price from snippet (basic attempt)
                price = ''
                price_match = re.search(r'\$[\d,]+\.?\d*', snippet)
                if price_match:
                    price = price_match.group(0)
                
                product = {
                    'title': title,
                    'link': link,
                    'snippet': snippet,
                    'image': '',  # Organic results don't have thumbnails
                    'source_domain': urlparse(link).netloc.replace('www.', ''),
                    'search_query': query,
                    'interest_match': interest,
                    'priority': query_info['priority'],
                    'price': price
                }
                
                if not any(p['link'] == link for p in all_products):
                    all_products.append(product)
                    products_by_interest[interest].append(product)
                    
                    # Log first few products to verify URL quality
                    if len(all_products) <= 3:
                        logger.info(f"Collected product: {title[:50]} | URL: {link[:100]}")
            
            logger.info(f"Added {len(products_by_interest[interest])} products for '{interest}'")
            time.sleep(0.3)
            
        except Exception as e:
            logger.error(f"Error searching '{query}': {e}")
            continue
    
    if not all_products:
        logger.warning("No products collected")
        return []
    
    # Balance products across interests
    num_interests = len(products_by_interest)
    per_interest = max(2, target_count // num_interests)
    
    balanced = []
    for interest, prods in products_by_interest.items():
        balanced.extend(prods[:per_interest])
    
    # Fill remaining slots
    if len(balanced) < target_count:
        for interest, prods in products_by_interest.items():
            for p in prods:
                if p not in balanced:
                    balanced.append(p)
                    if len(balanced) >= target_count:
                        break
    
    elapsed = time.time() - start_time
    logger.info(f"Found {len(balanced)} products in {elapsed:.1f}s")
    
    if balanced:
        sample_urls = [p['link'][:100] for p in balanced[:3]]
        logger.info(f"Final sample product URLs: {sample_urls}")
    
    return balanced[:target_count]