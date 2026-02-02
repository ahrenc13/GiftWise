"""
IMAGE FETCHER - ENHANCED VERSION
Get real product images for gift recommendations

IMPROVEMENTS:
- Better Google Custom Search integration
- Smarter fallbacks
- Clear logging when using placeholders
- Caching to reduce API calls

Author: Chad + Claude
Date: January 2026
"""

import requests
from bs4 import BeautifulSoup
import re
import logging
from urllib.parse import urlparse
import os
import hashlib

logger = logging.getLogger('giftwise')

# API Keys (set from environment or passed in) - accept both env var names
GOOGLE_CUSTOM_SEARCH_API_KEY = os.environ.get('GOOGLE_CSE_API_KEY') or os.environ.get('GOOGLE_CUSTOM_SEARCH_API_KEY', None)
GOOGLE_CUSTOM_SEARCH_ENGINE_ID = os.environ.get('GOOGLE_CUSTOM_SEARCH_ENGINE_ID', None)
UNSPLASH_ACCESS_KEY = os.environ.get('UNSPLASH_ACCESS_KEY', None)

# Simple in-memory cache for images
_image_cache = {}

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
    
    # Check cache first
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
        
        # Try Open Graph image first (most reliable)
        og_image = soup.find('meta', property='og:image')
        if og_image and og_image.get('content'):
            img_url = og_image.get('content')
            _image_cache[cache_key] = img_url
            return img_url
        
        # Try Twitter Card image
        twitter_image = soup.find('meta', {'name': 'twitter:image'})
        if twitter_image and twitter_image.get('content'):
            img_url = twitter_image.get('content')
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
                # Make absolute URL if relative
                if img_url.startswith('//'):
                    img_url = 'https:' + img_url
                elif img_url.startswith('/'):
                    parsed = urlparse(url)
                    img_url = f"{parsed.scheme}://{parsed.netloc}{img_url}"
                elif not img_url.startswith('http'):
                    parsed = urlparse(url)
                    img_url = f"{parsed.scheme}://{parsed.netloc}/{img_url}"
                
                _image_cache[cache_key] = img_url
                return img_url
        
        return None
    
    except Exception as e:
        logger.debug(f"Error extracting image from {url}: {e}")
        return None


def get_google_image_search(product_name, api_key=None, engine_id=None):
    """
    Get product image from Google Custom Search API
    
    This is the BEST method for product images when configured.
    
    Args:
        product_name: Product name to search
        api_key: Google Custom Search API key
        engine_id: Google Custom Search Engine ID
    
    Returns:
        dict with 'url', 'width', 'height' or None
    """
    # Use provided keys or fall back to environment
    api_key = api_key or GOOGLE_CUSTOM_SEARCH_API_KEY
    engine_id = engine_id or GOOGLE_CUSTOM_SEARCH_ENGINE_ID
    
    if not api_key or not engine_id:
        return None
    
    # Check cache
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
            'imgSize': 'medium'  # Get decent quality images
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if 'items' in data and len(data['items']) > 0:
                item = data['items'][0]
                result = {
                    'url': item['link'],
                    'width': item.get('image', {}).get('width'),
                    'height': item.get('image', {}).get('height'),
                    'thumbnail': item.get('image', {}).get('thumbnailLink')
                }
                _image_cache[cache_key] = result
                return result
        elif response.status_code == 429:
            logger.warning("Google Custom Search API rate limit exceeded (429)")
        else:
            try:
                err = response.json()
                logger.warning(
                    f"Google CSE (image) status={response.status_code} "
                    f"error={err.get('error', {}).get('message', response.text[:150])}"
                )
            except Exception:
                logger.warning(f"Google CSE (image) status={response.status_code} body={response.text[:200]}")
        
        return None
    
    except Exception as e:
        logger.error(f"Google image search error: {e}")
        return None


def get_unsplash_image(keywords, access_key=None):
    """
    Get evocative image from Unsplash (FALLBACK for when no product image available)
    
    Args:
        keywords: Keywords to search
        access_key: Unsplash API access key
    
    Returns:
        Image URL or None
    """
    access_key = access_key or UNSPLASH_ACCESS_KEY
    
    if not access_key:
        return None
    
    try:
        # Use first 2-3 words + "gift"
        search_terms = ' '.join(keywords.split()[:3]) + ' gift product'
        
        url = 'https://api.unsplash.com/search/photos'
        headers = {'Authorization': f'Client-ID {access_key}'}
        params = {
            'query': search_terms,
            'per_page': 1,
            'orientation': 'squarish'
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if 'results' in data and len(data['results']) > 0:
                return data['results'][0]['urls'].get('regular') or \
                       data['results'][0]['urls'].get('small')
        
        return None
    
    except Exception as e:
        logger.debug(f"Unsplash API error: {e}")
        return None


def is_search_url(url):
    """Check if URL is a search results page"""
    if not url:
        return False
    
    search_indicators = ['/s?', '/search?', '?q=', '?k=', 'tbm=shop', '/search/']
    url_lower = url.lower()
    return any(indicator in url_lower for indicator in search_indicators)


def generate_placeholder_image(product_name):
    """
    Generate placeholder image URL with product name
    
    Uses a better placeholder service that creates custom images
    """
    # Clean product name for URL
    product_name_clean = re.sub(r'[^a-zA-Z0-9 ]', '', product_name)[:30]
    product_name_encoded = product_name_clean.replace(' ', '+')
    
    # Use placeholder.com with custom text and nice colors
    return f'https://via.placeholder.com/400x400/667eea/ffffff?text={product_name_encoded}'


def get_product_image(recommendation):
    """
    Get image for a recommendation using multiple strategies
    
    Priority:
    1. Google Image Search (BEST - real product photos)
    2. Extract from product URL (if direct product page)
    3. Unsplash (evocative image)
    4. Placeholder (last resort)
    
    Args:
        recommendation: Dict with name, product_url, purchase_link, etc.
    
    Returns:
        Dict with 'image_url', 'image_source', 'fallback'
    """
    product_name = recommendation.get('name', '')
    product_url = recommendation.get('product_url', '') or recommendation.get('purchase_link', '')
    
    # Strategy 1: Google Image Search (BEST)
    # Always try this first if configured - gets real product images
    if GOOGLE_CUSTOM_SEARCH_API_KEY and GOOGLE_CUSTOM_SEARCH_ENGINE_ID:
        image_result = get_google_image_search(product_name)
        if image_result and image_result.get('url'):
            logger.info(f"Found Google image for '{product_name}'")
            return {
                'image_url': image_result['url'],
                'image_source': 'google_image_search',
                'fallback': False
            }
        else:
            logger.warning(f"Google Image Search returned no results for '{product_name}'")
    else:
        logger.debug("Google Custom Search not configured - skipping image search")
    
    # Strategy 2: Extract from product URL (if it's a direct product page)
    if product_url and not is_search_url(product_url):
        img_url = extract_image_from_url(product_url)
        if img_url:
            logger.info(f"Extracted image from product page for '{product_name}'")
            return {
                'image_url': img_url,
                'image_source': 'product_page',
                'fallback': False
            }
    
    # Strategy 3: Unsplash (evocative image)
    if UNSPLASH_ACCESS_KEY:
        img_url = get_unsplash_image(product_name)
        if img_url:
            logger.info(f"Using Unsplash evocative image for '{product_name}'")
            return {
                'image_url': img_url,
                'image_source': 'unsplash',
                'fallback': True  # Evocative, not exact product
            }
    
    # Strategy 4: Placeholder (last resort)
    logger.warning(f"Using placeholder image for '{product_name}' - no APIs configured")
    return {
        'image_url': generate_placeholder_image(product_name),
        'image_source': 'placeholder',
        'fallback': True
    }


def process_recommendation_images(recommendations):
    """
    Add images to all recommendations
    
    Args:
        recommendations: List of recommendation dicts
    
    Returns:
        List with 'image_url', 'image_source', 'image_is_fallback' added to each
    """
    processed = []
    
    # Track statistics
    google_count = 0
    product_page_count = 0
    unsplash_count = 0
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
            # If link is search page or bare domain, don't trust any image—use placeholder to avoid mismatched thumb
            if rec.get('gift_type') == 'physical' and is_bad_product_url(product_url):
                rec['image_url'] = generate_placeholder_image(product_name)
                rec['image_source'] = 'placeholder_bad_link'
                rec['image_is_fallback'] = True
                processed.append(rec)
                placeholder_count += 1
                continue
            # Skip if we already have a real image URL (e.g. from SerpAPI search results)
            existing = (rec.get('image_url') or '').strip()
            if existing and existing.startswith('http') and 'placeholder' not in existing.lower():
                rec['image_source'] = 'search_result'
                rec['image_is_fallback'] = False
                processed.append(rec)
                continue
            logger.debug(f"Fetching image for recommendation {i+1}/{len(recommendations)}: {product_name}")
            
            image_info = get_product_image(rec)
            
            rec['image_url'] = image_info['image_url']
            rec['image_source'] = image_info['image_source']
            rec['image_is_fallback'] = image_info['fallback']
            
            # Track statistics
            source = image_info['image_source']
            if source == 'google_image_search':
                google_count += 1
            elif source == 'product_page':
                product_page_count += 1
            elif source == 'unsplash':
                unsplash_count += 1
            elif source == 'placeholder':
                placeholder_count += 1
            
        except Exception as e:
            logger.error(f"Error fetching image for '{rec.get('name', 'Unknown')}': {e}")
            # Always provide a fallback
            rec['image_url'] = generate_placeholder_image(rec.get('name', 'Gift'))
            rec['image_source'] = 'error_fallback'
            rec['image_is_fallback'] = True
            placeholder_count += 1
        
        processed.append(rec)
    
    # Log statistics
    logger.info(f"Image processing complete: {google_count} Google, {product_page_count} product page, {unsplash_count} Unsplash, {placeholder_count} placeholder")
    
    # Warn if too many placeholders
    if placeholder_count > len(recommendations) * 0.5:
        logger.warning(f"HIGH PLACEHOLDER COUNT: {placeholder_count}/{len(recommendations)} using placeholders - consider configuring Google Custom Search API")
    
    return processed


def clear_image_cache():
    """Clear the in-memory image cache"""
    global _image_cache
    _image_cache = {}
    logger.info("Image cache cleared")
