"""
IMAGE FETCHER - FIXED VERSION
Ensures product thumbnails are STABLE and ACCESSIBLE

KEY FIXES:
1. Validates thumbnail URLs are accessible BEFORE using them
2. Falls back to stable sources when SerpAPI thumbnails fail
3. Extracts images from product pages when possible
4. Uses smart placeholders only when necessary

Author: Chad + Claude
Date: February 2026
"""

import requests
from bs4 import BeautifulSoup
import re
import logging
from urllib.parse import urlparse
import os
import hashlib

logger = logging.getLogger('giftwise')

# API Keys
GOOGLE_CUSTOM_SEARCH_API_KEY = os.environ.get('GOOGLE_CSE_API_KEY') or os.environ.get('GOOGLE_CUSTOM_SEARCH_API_KEY', None)
GOOGLE_CUSTOM_SEARCH_ENGINE_ID = os.environ.get('GOOGLE_CUSTOM_SEARCH_ENGINE_ID', None)
UNSPLASH_ACCESS_KEY = os.environ.get('UNSPLASH_ACCESS_KEY', None)

# Cache
_image_cache = {}


def validate_image_url(image_url, timeout=3):
    """
    Validate that an image URL is accessible
    
    Returns:
        bool: True if image loads successfully
    """
    if not image_url or not image_url.startswith(('http://', 'https://')):
        return False
    
    # Check cache first
    cache_key = f"img_{hashlib.md5(image_url.encode()).hexdigest()[:12]}"
    if cache_key in _image_cache:
        return _image_cache[cache_key]
    
    try:
        response = requests.head(image_url, timeout=timeout, allow_redirects=True)
        
        # Check if it's actually an image
        content_type = response.headers.get('content-type', '').lower()
        is_image = response.status_code == 200 and 'image' in content_type
        
        _image_cache[cache_key] = is_image
        return is_image
        
    except:
        # If HEAD fails, try GET with very small read
        try:
            response = requests.get(image_url, timeout=timeout, stream=True, allow_redirects=True)
            content_type = response.headers.get('content-type', '').lower()
            is_image = response.status_code == 200 and 'image' in content_type
            response.close()
            
            _image_cache[cache_key] = is_image
            return is_image
        except:
            _image_cache[cache_key] = False
            return False


def extract_image_from_url(url, timeout=5):
    """
    Extract product image from a product page URL
    
    This is MORE RELIABLE than SerpAPI thumbnails because:
    - It comes from the actual product page
    - It's not a temporary CDN link
    - It's the image the retailer wants to show
    """
    if not url or not url.startswith(('http://', 'https://')):
        return None
    
    # Check cache
    cache_key = hashlib.md5(url.encode()).hexdigest()[:16]
    if cache_key in _image_cache:
        return _image_cache[cache_key]
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        
        if response.status_code != 200:
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Try Open Graph image first (most reliable and stable)
        og_image = soup.find('meta', property='og:image')
        if og_image and og_image.get('content'):
            img_url = og_image.get('content')
            if validate_image_url(img_url):
                _image_cache[cache_key] = img_url
                return img_url
        
        # Try Twitter Card image
        twitter_image = soup.find('meta', {'name': 'twitter:image'})
        if twitter_image and twitter_image.get('content'):
            img_url = twitter_image.get('content')
            if validate_image_url(img_url):
                _image_cache[cache_key] = img_url
                return img_url
        
        # Try common product image selectors
        # Amazon
        img = soup.find('img', {'id': 'landingImage'}) or \
              soup.find('img', {'id': 'imgBlkFront'}) or \
              soup.find('img', {'class': re.compile(r'product-image|main-image', re.I)})
        
        # Etsy
        if not img:
            img = soup.find('img', {'data-test-id': 'image-carousel-image'}) or \
                  soup.find('img', {'class': re.compile(r'listing-image', re.I)})
        
        # Generic product image
        if not img:
            img = soup.find('img', {'class': re.compile(r'product', re.I)}) or \
                  soup.find('img', {'id': re.compile(r'product|main|hero', re.I)})
        
        if img:
            img_url = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
            if img_url:
                # Make absolute URL
                if img_url.startswith('//'):
                    img_url = 'https:' + img_url
                elif img_url.startswith('/'):
                    parsed = urlparse(url)
                    img_url = f"{parsed.scheme}://{parsed.netloc}{img_url}"
                elif not img_url.startswith('http'):
                    parsed = urlparse(url)
                    img_url = f"{parsed.scheme}://{parsed.netloc}/{img_url}"
                
                # Validate before caching
                if validate_image_url(img_url):
                    _image_cache[cache_key] = img_url
                    return img_url
        
        return None
    
    except Exception as e:
        logger.debug(f"Error extracting image from {url[:60]}: {e}")
        return None


def get_google_image_search(product_name, api_key=None, engine_id=None):
    """
    Get product image from Google Custom Search API
    REQUIRES: Paid Google Custom Search API setup
    """
    api_key = api_key or GOOGLE_CUSTOM_SEARCH_API_KEY
    engine_id = engine_id or GOOGLE_CUSTOM_SEARCH_ENGINE_ID
    
    if not api_key or not engine_id:
        return None
    
    cache_key = f"google_img_{hashlib.md5(product_name.encode()).hexdigest()[:16]}"
    if cache_key in _image_cache:
        return _image_cache[cache_key]
    
    try:
        url = 'https://www.googleapis.com/customsearch/v1'
        params = {
            'key': api_key,
            'cx': engine_id,
            'q': product_name,
            'searchType': 'image',
            'num': 1,
            'safe': 'active',
            'imgSize': 'medium'
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if 'items' in data and len(data['items']) > 0:
                item = data['items'][0]
                img_url = item['link']
                
                # Validate image URL before caching
                if validate_image_url(img_url):
                    result = {
                        'url': img_url,
                        'width': item.get('image', {}).get('width'),
                        'height': item.get('image', {}).get('height'),
                        'thumbnail': item.get('image', {}).get('thumbnailLink')
                    }
                    _image_cache[cache_key] = result
                    return result
        
        return None
    
    except Exception as e:
        logger.debug(f"Google image search error: {e}")
        return None


def generate_placeholder_image(product_name):
    """Generate placeholder image URL"""
    product_name_clean = re.sub(r'[^a-zA-Z0-9 ]', '', product_name)[:30]
    product_name_encoded = product_name_clean.replace(' ', '+')
    return f'https://via.placeholder.com/400x400/667eea/ffffff?text={product_name_encoded}'


def get_product_image(recommendation, prioritize_stability=True):
    """
    Get image for a recommendation with STABILITY as priority
    
    NEW STRATEGY (prioritizes stability over everything):
    1. Extract from product URL (MOST STABLE - from actual retailer)
    2. Google Image Search (if configured - also stable)
    3. Validate SerpAPI thumbnail (if it exists and is valid)
    4. Placeholder (last resort)
    
    Args:
        recommendation: Dict with name, product_url, image, etc.
        prioritize_stability: If True, extract from product page first
    
    Returns:
        Dict with 'image_url', 'image_source', 'fallback'
    """
    product_name = recommendation.get('name', '')
    product_url = recommendation.get('product_url', '') or recommendation.get('purchase_link', '')
    # Existing thumbnail from feed (Awin, Etsy, etc.) or backfill
    existing_image = (recommendation.get('image_url') or recommendation.get('image') or '').strip()

    try:
        from link_validation import is_bad_product_url
    except ImportError:
        def is_bad_product_url(url):
            return False

    # Strategy 1: Extract from product URL (most stable)
    if product_url and not is_bad_product_url(product_url) and prioritize_stability:
        img_url = extract_image_from_url(product_url)
        if img_url:
            logger.info(f"Extracted stable image from product page for '{product_name[:40]}'")
            return {
                'image_url': img_url,
                'image_source': 'product_page',
                'fallback': False
            }

    # Strategy 2: Validate existing feed/backfill image (Awin, Etsy, etc.)
    if existing_image and existing_image.startswith('http'):
        if validate_image_url(existing_image):
            logger.info(f"Feed/backfill thumbnail validated for '{product_name[:40]}'")
            return {
                'image_url': existing_image,
                'image_source': 'feed_validated',
                'fallback': False
            }
        logger.debug(f"Feed image failed validation for '{product_name[:40]}'")

    # Strategy 3: Google Image Search (if configured)
    if GOOGLE_CUSTOM_SEARCH_API_KEY and GOOGLE_CUSTOM_SEARCH_ENGINE_ID:
        image_result = get_google_image_search(product_name)
        if image_result and image_result.get('url'):
            logger.info(f"Found Google image for '{product_name[:40]}'")
            return {
                'image_url': image_result['url'],
                'image_source': 'google_image_search',
                'fallback': False
            }

    # Strategy 4: Placeholder (last resort)
    logger.warning(f"Using placeholder for '{product_name[:40]}' - no stable image source")
    return {
        'image_url': generate_placeholder_image(product_name),
        'image_source': 'placeholder',
        'fallback': True
    }


def process_recommendation_images(recommendations, prioritize_stability=True):
    """
    Add validated images to all recommendations
    
    NEW: Validates thumbnails before using them
    
    Args:
        recommendations: List of recommendation dicts
        prioritize_stability: If True, extract from product pages first
    
    Returns:
        List with validated 'image_url', 'image_source', 'image_is_fallback'
    """
    processed = []
    
    # Statistics
    product_page_count = 0
    google_count = 0
    serpapi_validated_count = 0
    placeholder_count = 0
    
    try:
        from link_validation import is_bad_product_url
    except ImportError:
        def is_bad_product_url(url):
            return False
    
    for i, rec in enumerate(recommendations):
        try:
            product_name = rec.get('name', 'Unknown')
            product_url = rec.get('product_url') or rec.get('purchase_link') or ''
            
            # Experiences: simple placeholder (no API calls)
            if rec.get('gift_type') == 'experience':
                rec['image_url'] = generate_placeholder_image(product_name)
                rec['image_source'] = 'placeholder_experience'
                rec['image_is_fallback'] = True
                processed.append(rec)
                placeholder_count += 1
                continue
            
            # Bad product URL: use placeholder immediately
            if rec.get('gift_type') == 'physical' and is_bad_product_url(product_url):
                rec['image_url'] = generate_placeholder_image(product_name)
                rec['image_source'] = 'placeholder_bad_link'
                rec['image_is_fallback'] = True
                processed.append(rec)
                placeholder_count += 1
                continue
            
            logger.debug(f"Fetching validated image for {i+1}/{len(recommendations)}: {product_name[:40]}")
            
            image_info = get_product_image(rec, prioritize_stability=prioritize_stability)
            
            rec['image_url'] = image_info['image_url']
            rec['image_source'] = image_info['image_source']
            rec['image_is_fallback'] = image_info['fallback']
            
            # Track statistics
            source = image_info['image_source']
            if source == 'product_page':
                product_page_count += 1
            elif source == 'feed_validated':
                serpapi_validated_count += 1  # reuse counter for feed/backfill validated
            elif source == 'google_image_search':
                google_count += 1
            elif source == 'placeholder':
                placeholder_count += 1
            
        except Exception as e:
            logger.error(f"Error fetching image for '{rec.get('name', 'Unknown')[:40]}': {e}")
            rec['image_url'] = generate_placeholder_image(rec.get('name', 'Gift'))
            rec['image_source'] = 'error_fallback'
            rec['image_is_fallback'] = True
            placeholder_count += 1
        
        processed.append(rec)
    
    # Log statistics
    logger.info(
        f"Image validation complete: "
        f"{product_page_count} from product pages, "
        f"{google_count} from Google, "
        f"{serpapi_validated_count} feed validated, "
        f"{placeholder_count} placeholders"
    )
    
    # Warn if too many placeholders
    if placeholder_count > len(recommendations) * 0.3:
        logger.warning(
            f"HIGH PLACEHOLDER COUNT: {placeholder_count}/{len(recommendations)} using placeholders. "
            f"Consider: (1) Enabling Google Custom Search API, or (2) Checking product URL quality"
        )
    
    return processed


def clear_image_cache():
    """Clear the in-memory image cache"""
    global _image_cache
    _image_cache = {}
    logger.info("Image cache cleared")
