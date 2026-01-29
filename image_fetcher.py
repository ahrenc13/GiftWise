"""
IMAGE FETCHER
Get product images or evocative images for gift recommendations

Strategies:
1. Extract image from product URL (if it's a product page)
2. Google Custom Search API (product images)
3. Unsplash API (evocative images)
4. Fallback placeholder
"""

import requests
from bs4 import BeautifulSoup
import re
import logging
from urllib.parse import urlparse
import os

logger = logging.getLogger('giftwise')

# API Keys (optional - will use fallbacks if not set)
# These can be set from environment or passed in
GOOGLE_CUSTOM_SEARCH_API_KEY = os.environ.get('GOOGLE_CUSTOM_SEARCH_API_KEY', None)
GOOGLE_CUSTOM_SEARCH_ENGINE_ID = os.environ.get('GOOGLE_CUSTOM_SEARCH_ENGINE_ID', None)
UNSPLASH_ACCESS_KEY = os.environ.get('UNSPLASH_ACCESS_KEY', None)

def extract_image_from_url(url, timeout=5):
    """
    Try to extract product image from a product page URL
    
    Args:
        url: Product page URL
    
    Returns:
        Image URL or None
    """
    if not url or not url.startswith(('http://', 'https://')):
        return None
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        
        if response.status_code != 200:
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Try common product image selectors
        # Amazon
        img = soup.find('img', {'id': 'landingImage'}) or \
              soup.find('img', {'id': 'imgBlkFront'}) or \
              soup.find('img', {'class': re.compile(r'product-image|main-image|hero-image', re.I)})
        
        # Etsy
        if not img:
            img = soup.find('img', {'data-test-id': 'image-carousel-image'}) or \
                  soup.find('img', {'class': re.compile(r'listing-image', re.I)})
        
        # Generic Open Graph or Twitter Card
        if not img:
            img = soup.find('meta', {'property': 'og:image'}) or \
                  soup.find('meta', {'name': 'twitter:image'})
            if img:
                return img.get('content')
        
        # Generic product image
        if not img:
            # Look for images with "product" in class/id
            img = soup.find('img', {'class': re.compile(r'product', re.I)}) or \
                  soup.find('img', {'id': re.compile(r'product|main|hero', re.I)})
        
        if img:
            img_url = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
            if img_url:
                # Make absolute URL if relative
                if img_url.startswith('//'):
                    img_url = 'https:' + img_url
                elif img_url.startswith('/'):
                    parsed = urlparse(url)
                    img_url = f"{parsed.scheme}://{parsed.netloc}{img_url}"
                elif not img_url.startswith('http'):
                    parsed = urlparse(url)
                    img_url = f"{parsed.scheme}://{parsed.netloc}/{img_url}"
                
                return img_url
        
        return None
    
    except Exception as e:
        logger.warning(f"Error extracting image from {url}: {e}")
        return None

def get_google_image_search(product_name, api_key=None, engine_id=None):
    """
    Get product image from Google Custom Search API
    
    Args:
        product_name: Product name to search
        api_key: Google Custom Search API key
        engine_id: Google Custom Search Engine ID
    
    Returns:
        Image URL or None
    """
    if not api_key or not engine_id:
        return None
    
    try:
        url = 'https://www.googleapis.com/customsearch/v1'
        params = {
            'key': api_key,
            'cx': engine_id,
            'q': product_name,
            'searchType': 'image',
            'num': 1,
            'safe': 'active'
        }
        
        response = requests.get(url, params=params, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if 'items' in data and len(data['items']) > 0:
                return data['items'][0]['link']
        
        return None
    
    except Exception as e:
        logger.warning(f"Google image search error: {e}")
        return None

def get_unsplash_image(keywords, access_key=None):
    """
    Get evocative image from Unsplash
    
    Args:
        keywords: Keywords to search (e.g., "gift", "present", product name)
        access_key: Unsplash API access key
    
    Returns:
        Image URL or None
    """
    if not access_key:
        return None
    
    try:
        # Use first 2-3 words of product name + "gift"
        search_terms = ' '.join(keywords.split()[:3]) + ' gift'
        
        url = 'https://api.unsplash.com/search/photos'
        headers = {
            'Authorization': f'Client-ID {access_key}'
        }
        params = {
            'query': search_terms,
            'per_page': 1,
            'orientation': 'squarish'
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if 'results' in data and len(data['results']) > 0:
                # Get small/regular size
                return data['results'][0]['urls'].get('regular') or \
                       data['results'][0]['urls'].get('small')
        
        return None
    
    except Exception as e:
        logger.warning(f"Unsplash API error: {e}")
        return None

def get_product_image(recommendation):
    """
    Get image for a recommendation using multiple strategies
    
    Priority:
    1. Extract from product URL (if direct product page)
    2. Google Image Search (if API configured) - ALWAYS try this for product images
    3. Unsplash (evocative image) - if Google fails
    4. Placeholder - last resort
    
    Args:
        recommendation: Dict with name, product_url, purchase_link, etc.
    
    Returns:
        Dict with 'image_url', 'image_source', 'fallback'
    """
    product_name = recommendation.get('name', '')
    product_url = recommendation.get('product_url', '') or recommendation.get('purchase_link', '')
    
    # Strategy 1: Extract from product URL (only if it's a direct product page, not search)
    if product_url and not is_search_url(product_url):
        img_url = extract_image_from_url(product_url)
        if img_url:
            return {
                'image_url': img_url,
                'image_source': 'product_page',
                'fallback': False
            }
    
    # Strategy 2: Google Image Search (if configured) - BEST for product images
    # This should work even without product_url
    if GOOGLE_CUSTOM_SEARCH_API_KEY and GOOGLE_CUSTOM_SEARCH_ENGINE_ID:
        img_url = get_google_image_search(
            product_name,
            GOOGLE_CUSTOM_SEARCH_API_KEY,
            GOOGLE_CUSTOM_SEARCH_ENGINE_ID
        )
        if img_url:
            return {
                'image_url': img_url,
                'image_source': 'google_search',
                'fallback': False
            }
    
    # Strategy 3: Unsplash (evocative image) - works without APIs if configured
    if UNSPLASH_ACCESS_KEY:
        img_url = get_unsplash_image(product_name, UNSPLASH_ACCESS_KEY)
        if img_url:
            return {
                'image_url': img_url,
                'image_source': 'unsplash',
                'fallback': True  # Evocative, not exact product
            }
    
    # Strategy 4: Placeholder service (always works)
    # Using a better placeholder that shows product name
    product_name_encoded = product_name.replace(' ', '+')[:30]
    return {
        'image_url': f'https://via.placeholder.com/400x400/667eea/ffffff?text={product_name_encoded}',
        'image_source': 'placeholder',
        'fallback': True
    }

def is_search_url(url):
    """
    Check if URL is a search results page (not a product page)
    """
    if not url:
        return False
    
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

def process_recommendation_images(recommendations):
    """
    Add images to all recommendations
    
    Args:
        recommendations: List of recommendation dicts
    
    Returns:
        List with 'image_url', 'image_source' added to each
    """
    processed = []
    
    for i, rec in enumerate(recommendations):
        try:
            product_name = rec.get('name', 'Unknown')
            logger.info(f"Fetching image for recommendation {i+1}/{len(recommendations)}: {product_name}")
            
            image_info = get_product_image(rec)
            
            rec['image_url'] = image_info['image_url']
            rec['image_source'] = image_info['image_source']
            rec['image_is_fallback'] = image_info['fallback']
            
            logger.info(f"Image fetched for '{product_name}': {image_info['image_source']}")
        except Exception as e:
            logger.error(f"Error fetching image for '{rec.get('name', 'Unknown')}': {e}")
            # Always provide a fallback image
            product_name = rec.get('name', 'Gift')[:30].replace(' ', '+')
            rec['image_url'] = f'https://via.placeholder.com/400x400/667eea/ffffff?text={product_name}'
            rec['image_source'] = 'error_fallback'
            rec['image_is_fallback'] = True
        
        processed.append(rec)
    
    logger.info(f"Processed images for {len(processed)} recommendations")
    return processed
