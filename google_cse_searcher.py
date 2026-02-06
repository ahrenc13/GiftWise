"""
GOOGLE CUSTOM SEARCH ENGINE PRODUCT SEARCHER
Uses Google CSE configured with 50+ e-commerce domains
Returns actual product pages with images

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
PRODUCTS_PER_QUERY = 10


def is_listicle_or_blog(title, url):
    """Filter out listicles, blogs, buying guides"""
    lower_title = title.lower()
    lower_url = url.lower()
    
    listicle_indicators = [
        'best', 'top 10', 'top 5', 'buying guide', 'how to choose',
        'reviews', 'comparison', 'vs', 'alternatives', 'ultimate guide'
    ]
    
    return any(ind in lower_title or ind in lower_url for ind in listicle_indicators)


def search_products_google_cse(profile, google_api_key, google_cse_id, target_count=20):
    """
    Search for gift products using Google Custom Search Engine
    
    Args:
        profile: Recipient profile dict
        google_api_key: Google API key
        google_cse_id: Google Custom Search Engine ID
        target_count: Target number of products to find
        
    Returns:
        List of product dicts with title, link, snippet, image
    """
    
    logger.info(f"Inventory target: {target_count} products")
    
    if not google_api_key or not google_cse_id:
        logger.error("Google CSE credentials not configured")
        return []
    
    interests = profile.get('interests', [])
    if not interests:
        logger.warning("No interests in profile")
        return []
    
    # Build search queries (skip work interests)
    search_queries = []
    for interest in interests:
        name = interest.get('name', '')
        if not name:
            continue
        
        # Skip work interests
        if interest.get('is_work', False):
            logger.info(f"Skipping work interest: {name}")
            continue
        
        intensity = interest.get('intensity', 'moderate')
        priority = 'high' if intensity == 'passionate' else 'medium'
        
        # Make query gift-oriented
        name_lower = name.lower()
        
        # For artists/musicians: use "merchandise"
        if any(term in name_lower for term in ['artist', 'musician', 'singer', 'band', 'roan', 'swift', 'nicks']):
            query = f"{name} merchandise"
        # For sports teams: use "memorabilia"
        elif any(term in name_lower for term in ['team', 'sports', 'basketball', 'pacers']):
            query = f"{name} memorabilia"
        # For hobbies: use "gifts for"
        elif any(term in name_lower for term in ['owner', 'enthusiast', 'lover', 'fan']):
            query = f"gifts for {name}"
        # For travel: use "souvenirs"
        elif any(term in name_lower for term in ['wisconsin', 'michigan', 'travel', 'cruise']):
            query = f"{name} souvenirs"
        # Default: just add "gifts"
        else:
            query = f"{name} gift"
        
        search_queries.append({
            'query': query,
            'interest': name,
            'priority': priority
        })
    
    search_queries = search_queries[:MAX_SEARCH_QUERIES]
    logger.info(f"Running {len(search_queries)} Google CSE searches")
    
    all_products = []
    products_by_interest = defaultdict(list)
    
    for query_info in search_queries:
        query = query_info['query']
        interest = query_info['interest']
        
        try:
            # Call Google Custom Search API
            response = requests.get(
                "https://www.googleapis.com/customsearch/v1",
                params={
                    'key': google_api_key,
                    'cx': google_cse_id,
                    'q': query,
                    'num': 10  # Max results per query
                },
                timeout=10
            )
            
            response.raise_for_status()
            data = response.json()
            
            items = data.get('items', [])
            
            # Debug: log first item structure
            if items and len(all_products) == 0:
                logger.info(f"Sample Google CSE response keys: {list(items[0].keys())}")
                sample_link = items[0].get('link', '')
                logger.info(f"Sample link field: {sample_link[:100]}")
            
            if not items:
                logger.warning(f"No results for: {query}")
                continue
            
            collected_count = 0
            filtered_count = 0
            
            for item in items:
                title = item.get('title', '').strip()
                link = item.get('link', '').strip()
                snippet = item.get('snippet', '').strip()
                
                if not title or not link:
                    continue
                
                # CRITICAL: Only accept DIRECT PRODUCT PAGES
                link_lower = link.lower()
                is_product_page = False
                
                if 'amazon.com' in link_lower:
                    if '/dp/' in link_lower or '/gp/product/' in link_lower:
                        is_product_page = True
                
                elif 'etsy.com' in link_lower:
                    if '/listing/' in link_lower:
                        is_product_page = True
                
                elif 'ebay.com' in link_lower:
                    if '/itm/' in link_lower:
                        is_product_page = True
                
                # For other domains in CSE, accept if not a search/category page
                elif not any(retailer in link_lower for retailer in ['amazon.com', 'etsy.com', 'ebay.com']):
                    # Check if it's NOT a category/search page
                    if not any(bad in link_lower for bad in ['/search', '/category', '/shop/', '/products/', '/collections/']):
                        is_product_page = True
                
                if not is_product_page:
                    filtered_count += 1
                    if filtered_count <= 2:
                        logger.info(f"FILTERED non-product page: {link[:100]}")
                    continue
                
                if is_listicle_or_blog(title, link):
                    filtered_count += 1
                    continue
                
                # Extract price from snippet if present
                price = ''
                price_match = re.search(r'\$[\d,]+\.?\d*', snippet)
                if price_match:
                    price = price_match.group(0)
                
                # Get image from pagemap if available
                image = ''
                pagemap = item.get('pagemap', {})
                if 'cse_image' in pagemap and pagemap['cse_image']:
                    image = pagemap['cse_image'][0].get('src', '')
                elif 'metatags' in pagemap and pagemap['metatags']:
                    # Try og:image
                    image = pagemap['metatags'][0].get('og:image', '')
                
                product = {
                    'title': title,
                    'link': link,
                    'snippet': snippet,
                    'image': image,
                    'source_domain': urlparse(link).netloc.replace('www.', ''),
                    'search_query': query,
                    'interest_match': interest,
                    'priority': query_info['priority'],
                    'price': price
                }
                
                # Deduplicate by link
                if not any(p['link'] == link for p in all_products):
                    all_products.append(product)
                    products_by_interest[interest].append(product)
                    collected_count += 1
                    
                    # Log first few products
                    if len(all_products) <= 3:
                        logger.info(f"Collected product: {title[:50]} | URL: {link[:100]}")
            
            logger.info(f"Added {len(products_by_interest[interest])} products for '{interest}' (filtered {filtered_count} non-product pages)")
            time.sleep(0.1)  # Rate limiting
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Google CSE request failed for '{query}': {e}")
            continue
        except Exception as e:
            logger.error(f"Error processing Google CSE results for '{query}': {e}")
            continue
    
    # Cap at target count
    if len(all_products) > target_count:
        all_products = all_products[:target_count]
    
    elapsed = time.time()
    logger.info(f"Found {len(all_products)} products")
    
    if all_products:
        sample_urls = [p['link'] for p in all_products[:3]]
        logger.info(f"Final sample product URLs: {sample_urls}")
    
    return all_products
