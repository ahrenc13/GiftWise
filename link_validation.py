"""
LINK VALIDATION & GENERATION
Ensures reliable product links for gift recommendations

Strategies:
1. Validate URLs from AI
2. Generate Amazon links via search (if product name provided)
3. Generate Etsy links via search
4. Fallback to Google Shopping
"""

import requests
import re
from urllib.parse import quote, urlparse
import logging

logger = logging.getLogger('giftwise')

def validate_url(url):
    """
    Validate that a URL is accessible and returns 200
    """
    if not url or not isinstance(url, str):
        return False
    
    # Basic URL format check
    if not url.startswith(('http://', 'https://')):
        return False
    
    try:
        response = requests.head(url, timeout=5, allow_redirects=True)
        return response.status_code == 200
    except:
        return False

def generate_amazon_link(product_name, affiliate_tag=None):
    """
    Generate Amazon search link (reliable fallback)
    
    Args:
        product_name: Exact product name
        affiliate_tag: Amazon Associates tag (optional)
    
    Returns:
        Amazon search URL
    """
    # Clean product name
    search_query = product_name.replace(' ', '+')
    
    base_url = f"https://www.amazon.com/s?k={quote(product_name)}"
    
    if affiliate_tag:
        base_url += f"&tag={affiliate_tag}"
    
    return base_url

def generate_etsy_link(product_name):
    """
    Generate Etsy search link
    
    Args:
        product_name: Product name or keywords
    
    Returns:
        Etsy search URL
    """
    search_query = quote(product_name)
    return f"https://www.etsy.com/search?q={search_query}"

def generate_google_shopping_link(product_name):
    """
    Generate Google Shopping link (universal fallback)
    
    Args:
        product_name: Product name
    
    Returns:
        Google Shopping URL
    """
    search_query = quote(product_name)
    return f"https://www.google.com/search?tbm=shop&q={search_query}"

def is_search_url(url):
    """
    Check if URL is a search results page (not a product page)
    """
    if not url:
        return True
    
    search_indicators = [
        '/s?',  # Amazon search
        '/search?',  # Generic search
        '?q=',  # Query parameter
        '?k=',  # Amazon search key
        'tbm=shop',  # Google Shopping
        '/search/',  # Etsy search path
    ]
    
    url_lower = url.lower()
    for indicator in search_indicators:
        if indicator in url_lower:
            return True
    
    return False

def get_reliable_link(recommendation, amazon_affiliate_tag=None):
    """
    Get reliable link for a recommendation
    
    CRITICAL: Only return DIRECT product URLs, never search results
    
    Priority:
    1. Validate AI-provided URL (must be direct product page)
    2. If AI URL is search results, reject it
    3. Try to find actual product URL from retailer
    4. If no direct product URL available, return None (don't use search)
    
    Args:
        recommendation: Dict with name, product_url, retailer_type, where_to_buy
        amazon_affiliate_tag: Amazon Associates tag (optional)
    
    Returns:
        Dict with 'url', 'source', 'reliable', 'is_direct'
    """
    product_name = recommendation.get('name', '')
    ai_url = recommendation.get('product_url', '')
    retailer_type = recommendation.get('retailer_type', '').lower()
    where_to_buy = recommendation.get('where_to_buy', '').lower()
    
    # Strategy 1: Validate AI-provided URL
    if ai_url:
        # Check if it's a search URL (reject it)
        if is_search_url(ai_url):
            logger.warning(f"AI-provided URL is search results, rejecting: {ai_url}")
        elif validate_url(ai_url):
            # It's a valid direct URL
            return {
                'url': ai_url,
                'source': 'ai_provided',
                'reliable': True,
                'is_direct': True
            }
        else:
            logger.warning(f"AI-provided URL invalid: {ai_url}")
    
    # Strategy 2: Try to extract direct product URL from where_to_buy
    # If where_to_buy contains a URL, try to use it
    if where_to_buy:
        # Look for URLs in where_to_buy text
        import re
        url_pattern = r'https?://[^\s]+'
        urls = re.findall(url_pattern, where_to_buy)
        for url in urls:
            if not is_search_url(url) and validate_url(url):
                return {
                    'url': url,
                    'source': 'where_to_buy',
                    'reliable': True,
                    'is_direct': True
                }
    
    # Strategy 3: If retailer is specified but no direct URL, we can't generate one
    # Don't fall back to search - that's what the user complained about
    # Instead, return None or a note that direct URL is needed
    logger.warning(f"No direct product URL available for {product_name}. AI must provide direct product URL.")
    
    # Return a placeholder that indicates URL is needed
    return {
        'url': None,  # No valid direct URL
        'source': 'needs_direct_url',
        'reliable': False,
        'is_direct': False,
        'message': 'Direct product URL required - search results not acceptable'
    }

def process_recommendation_links(recommendations, amazon_affiliate_tag=None):
    """
    Process all recommendations to ensure reliable links
    
    CRITICAL: Only accept direct product URLs, reject search results
    
    Args:
        recommendations: List of recommendation dicts
        amazon_affiliate_tag: Amazon Associates tag (optional)
    
    Returns:
        List of recommendations with 'purchase_link' added/updated
        Recommendations without valid direct URLs will have purchase_link=None
    """
    processed = []
    
    for rec in recommendations:
        link_info = get_reliable_link(rec, amazon_affiliate_tag)
        
        # Only add purchase_link if we have a valid direct URL
        if link_info.get('is_direct') and link_info.get('url'):
            rec['purchase_link'] = link_info['url']
            rec['link_source'] = link_info['source']
            rec['link_reliable'] = link_info['reliable']
        else:
            # No valid direct URL - mark as needing URL
            rec['purchase_link'] = None
            rec['link_source'] = 'needs_direct_url'
            rec['link_reliable'] = False
            rec['link_error'] = link_info.get('message', 'Direct product URL required')
            logger.warning(f"Recommendation '{rec.get('name')}' has no valid direct product URL")
        
        processed.append(rec)
    
    return processed
