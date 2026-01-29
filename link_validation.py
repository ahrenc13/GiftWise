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

def get_reliable_link(recommendation, amazon_affiliate_tag=None):
    """
    Get reliable link for a recommendation
    
    Priority:
    1. Validate AI-provided URL
    2. Generate retailer-specific link based on retailer_type
    3. Fallback to Google Shopping
    
    Args:
        recommendation: Dict with name, product_url, retailer_type, where_to_buy
        amazon_affiliate_tag: Amazon Associates tag (optional)
    
    Returns:
        Dict with 'url', 'source', 'reliable'
    """
    product_name = recommendation.get('name', '')
    ai_url = recommendation.get('product_url', '')
    retailer_type = recommendation.get('retailer_type', '').lower()
    where_to_buy = recommendation.get('where_to_buy', '').lower()
    
    # Strategy 1: Validate AI-provided URL
    if ai_url:
        if validate_url(ai_url):
            return {
                'url': ai_url,
                'source': 'ai_provided',
                'reliable': True
            }
        else:
            logger.warning(f"AI-provided URL invalid: {ai_url}")
    
    # Strategy 2: Generate retailer-specific link
    if retailer_type == 'amazon' or 'amazon' in where_to_buy:
        return {
            'url': generate_amazon_link(product_name, amazon_affiliate_tag),
            'source': 'amazon_search',
            'reliable': True
        }
    
    if retailer_type == 'etsy' or 'etsy' in where_to_buy:
        return {
            'url': generate_etsy_link(product_name),
            'source': 'etsy_search',
            'reliable': True
        }
    
    # Strategy 3: Try to extract domain from where_to_buy
    if where_to_buy and '.' in where_to_buy:
        # Try to construct URL
        domain = where_to_buy.split()[0]  # Get first word (might be domain)
        if not domain.startswith('http'):
            domain = f"https://{domain}"
        
        # Try to add product search path
        if 'etsy' in domain:
            return {
                'url': generate_etsy_link(product_name),
                'source': 'etsy_search',
                'reliable': True
            }
        elif 'amazon' in domain:
            return {
                'url': generate_amazon_link(product_name, amazon_affiliate_tag),
                'source': 'amazon_search',
                'reliable': True
            }
    
    # Strategy 4: Universal fallback - Google Shopping
    return {
        'url': generate_google_shopping_link(product_name),
        'source': 'google_shopping',
        'reliable': True  # Always works, just not direct
    }

def process_recommendation_links(recommendations, amazon_affiliate_tag=None):
    """
    Process all recommendations to ensure reliable links
    
    Args:
        recommendations: List of recommendation dicts
        amazon_affiliate_tag: Amazon Associates tag (optional)
    
    Returns:
        List of recommendations with 'purchase_link' added/updated
    """
    processed = []
    
    for rec in recommendations:
        link_info = get_reliable_link(rec, amazon_affiliate_tag)
        
        # Add purchase_link to recommendation
        rec['purchase_link'] = link_info['url']
        rec['link_source'] = link_info['source']
        rec['link_reliable'] = link_info['reliable']
        
        processed.append(rec)
    
    return processed
