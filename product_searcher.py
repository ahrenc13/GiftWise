"""
PRODUCT SEARCHER - Find Real Products Using Google Custom Search
Searches for actual products based on recipient profile interests

Author: Chad + Claude
Date: February 2026
"""

import requests
import logging
import time
from collections import defaultdict

logger = logging.getLogger(__name__)


def search_real_products(profile, google_api_key, google_cse_id, target_count=40):
    """
    Search for real products using Google Custom Search based on recipient profile.
    
    Args:
        profile: Recipient profile dict from build_recipient_profile()
        google_api_key: Google Custom Search API key
        google_cse_id: Custom Search Engine ID
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
    
    if not google_api_key or not google_cse_id:
        logger.error("Google Custom Search API credentials not configured")
        return []
    
    logger.info(f"Searching for real products based on profile interests...")
    
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
        
        # For aspirational interests, search for gifts that would help them get into it
        # For current interests, search for advanced/specialty items
        
        if interest_type == 'aspirational':
            # Beginner/starter gifts for aspirational interests
            search_queries.append({
                'query': f"{name} beginner gift set",
                'interest': name,
                'priority': 'high' if intensity == 'passionate' else 'medium'
            })
            search_queries.append({
                'query': f"{name} starter kit unique",
                'interest': name,
                'priority': 'high' if intensity == 'passionate' else 'medium'
            })
        else:
            # Advanced/specialty items for current interests
            search_queries.append({
                'query': f"{name} premium gift",
                'interest': name,
                'priority': 'high' if intensity == 'passionate' else 'medium'
            })
            search_queries.append({
                'query': f"{name} enthusiast gift unique",
                'interest': name,
                'priority': 'medium'
            })
    
    # Add brand-specific searches if they have brand preferences
    brands = profile.get('style_preferences', {}).get('brands', [])
    for brand in brands[:3]:  # Top 3 brands
        search_queries.append({
            'query': f"{brand} gift",
            'interest': brand,
            'priority': 'medium'
        })
    
    # Limit to reasonable number of searches
    search_queries = search_queries[:15]  # Max 15 searches
    
    logger.info(f"Generated {len(search_queries)} search queries")
    
    # Execute searches
    all_products = []
    products_by_interest = defaultdict(list)
    
    for query_info in search_queries:
        query = query_info['query']
        interest = query_info['interest']
        
        try:
            # Call Google Custom Search API
            url = "https://www.googleapis.com/customsearch/v1"
            params = {
                'key': google_api_key,
                'cx': google_cse_id,
                'q': query,
                'num': 10,  # Get 10 results per query
                'searchType': 'image',  # Get image results (better for products)
                'safe': 'off'
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            items = data.get('items', [])
            
            logger.info(f"Query '{query}' returned {len(items)} results")
            
            for item in items:
                # Extract product info
                product = {
                    'title': item.get('title', ''),
                    'link': item.get('link', ''),
                    'snippet': item.get('snippet', ''),
                    'image': item.get('image', {}).get('thumbnailLink', ''),
                    'source_domain': extract_domain(item.get('link', '')),
                    'search_query': query,
                    'interest_match': interest,
                    'priority': query_info['priority']
                }
                
                # Try to extract price from snippet
                price = extract_price(item.get('snippet', ''))
                if price:
                    product['price'] = price
                
                # Avoid duplicates
                if not any(p['link'] == product['link'] for p in all_products):
                    all_products.append(product)
                    products_by_interest[interest].append(product)
            
            # Rate limiting - wait between requests
            time.sleep(0.5)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error searching for '{query}': {e}")
            continue
        except Exception as e:
            logger.error(f"Unexpected error searching for '{query}': {e}")
            continue
    
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
