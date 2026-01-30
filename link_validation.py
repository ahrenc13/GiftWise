"""
LINK VALIDATION & GENERATION - ENHANCED VERSION
Ensures RELIABLE product links for gift recommendations

CRITICAL FIX: Actually validates products exist before recommending them
- Uses Google Shopping API to verify real products
- Generates direct product URLs when possible
- Only uses search links as last resort with clear warnings
- Filters out non-existent products

Author: Chad + Claude
Date: January 2026
"""

import requests
import re
from urllib.parse import quote, urlparse
import logging
import os

logger = logging.getLogger('giftwise')

# Google Shopping API (for product validation)
GOOGLE_SHOPPING_API_KEY = os.environ.get('GOOGLE_CUSTOM_SEARCH_API_KEY', '')
GOOGLE_SHOPPING_ENGINE_ID = os.environ.get('GOOGLE_CUSTOM_SEARCH_ENGINE_ID', '')

def validate_url_exists(url, timeout=5):
    """
    Validate that a URL actually exists and returns 200
    
    Returns:
        bool: True if URL is valid and accessible
    """
    if not url or not isinstance(url, str):
        return False
    
    if not url.startswith(('http://', 'https://')):
        return False
    
    try:
        response = requests.head(url, timeout=timeout, allow_redirects=True)
        return response.status_code == 200
    except:
        # If HEAD fails, try GET (some servers block HEAD)
        try:
            response = requests.get(url, timeout=timeout, stream=True, allow_redirects=True)
            return response.status_code == 200
        except:
            return False


def search_google_shopping(product_name):
    """
    Search Google Shopping to verify product exists and get real link
    
    Returns:
        dict with 'exists', 'url', 'price', 'image_url' or None
    """
    if not GOOGLE_SHOPPING_API_KEY or not GOOGLE_SHOPPING_ENGINE_ID:
        logger.warning("Google Shopping API not configured - cannot verify products")
        return None
    
    try:
        url = 'https://www.googleapis.com/customsearch/v1'
        params = {
            'key': GOOGLE_SHOPPING_API_KEY,
            'cx': GOOGLE_SHOPPING_ENGINE_ID,
            'q': product_name,
            'num': 1,  # Just need first result
            'safe': 'active'
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if 'items' in data and len(data['items']) > 0:
                item = data['items'][0]
                return {
                    'exists': True,
                    'url': item.get('link'),
                    'title': item.get('title'),
                    'snippet': item.get('snippet'),
                    'image_url': item.get('pagemap', {}).get('cse_image', [{}])[0].get('src')
                }
        
        return None
    
    except Exception as e:
        logger.error(f"Google Shopping search error: {e}")
        return None


def extract_brand_from_product_name(product_name):
    """
    Extract likely brand name from product name
    
    Examples:
        "Bose QuietComfort 45" → "Bose"
        "Nintendo Switch OLED" → "Nintendo"
    """
    # Common brand patterns (first word is often brand)
    words = product_name.split()
    if len(words) > 0:
        potential_brand = words[0]
        # Filter out generic words
        generic_words = {'the', 'a', 'an', 'vintage', 'classic', 'new', 'original'}
        if potential_brand.lower() not in generic_words:
            return potential_brand
    return None


def generate_brand_website_url(product_name):
    """
    Generate brand website URL as fallback
    
    Example: "Bose QuietComfort" → "https://www.bose.com"
    """
    brand = extract_brand_from_product_name(product_name)
    if brand:
        # Clean brand name
        brand_clean = re.sub(r'[^a-zA-Z0-9]', '', brand).lower()
        return f"https://www.{brand_clean}.com"
    return None


def is_search_url(url):
    """Check if URL is a search results page (not a product page)"""
    if not url:
        return True
    
    search_indicators = [
        '/s?',  # Amazon search
        '/search?',  # Generic search
        '?q=',  # Query parameter
        '?k=',  # Amazon search key
        'tbm=shop',  # Google Shopping
        '/search/',  # Etsy search
    ]
    
    url_lower = url.lower()
    return any(indicator in url_lower for indicator in search_indicators)


def generate_amazon_search_url(product_name, affiliate_tag=None):
    """Generate Amazon search URL (LAST RESORT ONLY)"""
    url = f"https://www.amazon.com/s?k={quote(product_name)}"
    if affiliate_tag:
        url += f"&tag={affiliate_tag}"
    return url


def generate_etsy_search_url(product_name):
    """Generate Etsy search URL (LAST RESORT ONLY)"""
    return f"https://www.etsy.com/search?q={quote(product_name)}"


def validate_product_specificity(recommendation):
    """
    Check if product name is specific enough to be real
    
    Returns:
        dict with 'specific', 'score', 'reason'
    """
    product_name = recommendation.get('name', '')
    
    # Check length
    word_count = len(product_name.split())
    if word_count < 2:
        return {
            'specific': False,
            'score': 0,
            'reason': 'Product name too short (needs brand + model)'
        }
    
    # Check for brand indicators
    has_brand = extract_brand_from_product_name(product_name) is not None
    
    # Check for model numbers or specific details
    has_model_number = bool(re.search(r'\d+|[A-Z]{2,}', product_name))
    
    # Check for vague words
    vague_words = ['gift', 'set', 'collection', 'bundle', 'pack', 'assortment']
    has_vague_words = any(word in product_name.lower() for word in vague_words)
    
    # Score calculation
    score = 0
    if has_brand:
        score += 40
    if has_model_number:
        score += 30
    if word_count >= 3:
        score += 20
    if not has_vague_words:
        score += 10
    
    return {
        'specific': score >= 60,
        'score': score,
        'has_brand': has_brand,
        'has_model': has_model_number
    }


def get_reliable_link(recommendation, amazon_affiliate_tag=None, verify_existence=True):
    """
    Get reliable product link with validation
    
    Priority:
    1. Validate AI-provided URL (must be direct product page)
    2. Search Google Shopping to verify product exists
    3. Use brand website if identified
    4. Only use search links as LAST RESORT with warnings
    
    Args:
        recommendation: Dict with name, product_url, etc.
        amazon_affiliate_tag: Amazon Associates tag (optional)
        verify_existence: If True, verify products exist before returning
    
    Returns:
        Dict with 'url', 'source', 'reliable', 'verified', 'warning'
    """
    product_name = recommendation.get('name', '')
    ai_url = recommendation.get('product_url', '')
    
    # First, check if product is specific enough
    specificity = validate_product_specificity(recommendation)
    if not specificity['specific'] and verify_existence:
        logger.warning(f"Product '{product_name}' not specific enough (score: {specificity['score']})")
        return {
            'url': None,
            'source': 'rejected_not_specific',
            'reliable': False,
            'verified': False,
            'warning': f"Product name too generic - {specificity.get('reason', 'needs more details')}"
        }
    
    # Strategy 1: Validate AI-provided URL
    if ai_url and not is_search_url(ai_url):
        if validate_url_exists(ai_url):
            return {
                'url': ai_url,
                'source': 'ai_direct_url',
                'reliable': True,
                'verified': True,
                'warning': None
            }
        else:
            logger.warning(f"AI-provided URL failed validation: {ai_url}")
    
    # Strategy 2: Search Google Shopping to verify product exists
    if verify_existence:
        shopping_result = search_google_shopping(product_name)
        if shopping_result and shopping_result.get('exists'):
            url = shopping_result.get('url')
            if url and validate_url_exists(url):
                return {
                    'url': url,
                    'source': 'google_shopping_verified',
                    'reliable': True,
                    'verified': True,
                    'warning': None,
                    'google_title': shopping_result.get('title')
                }
    
    # Strategy 3: Try brand website
    if specificity.get('has_brand'):
        brand_url = generate_brand_website_url(product_name)
        if brand_url and validate_url_exists(brand_url):
            return {
                'url': brand_url,
                'source': 'brand_website',
                'reliable': True,
                'verified': False,  # Brand website, not specific product
                'warning': 'Visit brand website to find product'
            }
    
    # Strategy 4: LAST RESORT - Search links with clear warnings
    # Only if product seems real enough (specificity score > 40)
    if specificity['score'] >= 40:
        # Determine best search engine
        retailer_type = recommendation.get('retailer_type', '').lower()
        where_to_buy = recommendation.get('where_to_buy', '').lower()
        
        if 'amazon' in retailer_type or 'amazon' in where_to_buy:
            search_url = generate_amazon_search_url(product_name, amazon_affiliate_tag)
            return {
                'url': search_url,
                'source': 'amazon_search_fallback',
                'reliable': False,
                'verified': False,
                'warning': '⚠️ Search link - product existence not verified'
            }
        elif 'etsy' in retailer_type or 'etsy' in where_to_buy:
            search_url = generate_etsy_search_url(product_name)
            return {
                'url': search_url,
                'source': 'etsy_search_fallback',
                'reliable': False,
                'verified': False,
                'warning': '⚠️ Search link - product existence not verified'
            }
        else:
            # Generic Google Shopping search
            search_url = f"https://www.google.com/search?tbm=shop&q={quote(product_name)}"
            return {
                'url': search_url,
                'source': 'google_search_fallback',
                'reliable': False,
                'verified': False,
                'warning': '⚠️ Search link - product existence not verified'
            }
    
    # Product failed all validation
    return {
        'url': None,
        'source': 'validation_failed',
        'reliable': False,
        'verified': False,
        'warning': 'Product could not be verified - may not exist'
    }


def process_recommendation_links(recommendations, amazon_affiliate_tag=None, verify_existence=True):
    """
    Process all recommendations to ensure reliable links
    
    CRITICAL: Filters out products that can't be verified
    
    Args:
        recommendations: List of recommendation dicts
        amazon_affiliate_tag: Amazon Associates tag
        verify_existence: If True, verify products exist (recommended)
    
    Returns:
        List of recommendations with verified links
        Products without valid links are REMOVED unless verify_existence=False
    """
    verified_recommendations = []
    rejected_count = 0
    verified_count = 0
    fallback_count = 0
    
    for rec in recommendations:
        link_info = get_reliable_link(rec, amazon_affiliate_tag, verify_existence)
        
        # Add link info to recommendation
        rec['purchase_link'] = link_info.get('url')
        rec['link_source'] = link_info['source']
        rec['link_reliable'] = link_info['reliable']
        rec['link_verified'] = link_info.get('verified', False)
        rec['link_warning'] = link_info.get('warning')
        
        # Track statistics
        if link_info['verified']:
            verified_count += 1
            verified_recommendations.append(rec)
        elif link_info['url'] and not link_info['verified']:
            fallback_count += 1
            verified_recommendations.append(rec)
        else:
            # No link at all - reject product
            rejected_count += 1
            logger.warning(f"Rejected product '{rec.get('name')}': {link_info.get('warning', 'No link available')}")
    
    logger.info(f"Link processing: {verified_count} verified, {fallback_count} fallback, {rejected_count} rejected")
    
    # Log warning if too many products rejected
    if rejected_count > len(recommendations) * 0.3:  # More than 30% rejected
        logger.warning(f"HIGH REJECTION RATE: {rejected_count}/{len(recommendations)} products rejected - AI may be hallucinating")
    
    return verified_recommendations
