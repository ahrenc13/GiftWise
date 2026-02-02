"""
GIFTWISE MAIN APPLICATION - COMPREHENSIVE UPDATE v2
AI-Powered Gift Recommendations from Social Media

UPDATES IN THIS VERSION:
✅ Data quality assessment
✅ Dynamic recommendation counts
✅ 4-tier relationship system
✅ Web search for real product URLs
✅ Link fixing functionality
✅ Username autocomplete support
✅ Collectible series intelligence
✅ Freemium tier structure
✅ Your/Their pronoun handling
✅ TikTok repost intelligence
✅ CRITICAL BUG FIXES (Jan 28, 2026)

Author: Chad + Claude
Date: January 2026
"""

import os
import json
import time
import uuid
import threading
import re
import logging
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, session, jsonify, url_for, Response
import stripe
import anthropic
from dotenv import load_dotenv
from collections import Counter, defaultdict, OrderedDict

# Load environment variables FIRST (before any code that uses them)
load_dotenv()

# Import new recommendation architecture (profile → search → curate)
try:
    from profile_analyzer import build_recipient_profile
    from product_searcher import search_real_products
    from gift_curator import curate_gifts
    NEW_RECOMMENDATION_FLOW = True
except ImportError:
    NEW_RECOMMENDATION_FLOW = False
    pass

# Import enhanced recommendation engine (legacy fallback)
try:
    from enhanced_recommendation_engine import (
        extract_deep_signals,
        integrate_wishlist_data,
        detect_duplicates,
        build_enhanced_prompt,
        validate_recommendations
    )
    from enhanced_data_extraction import combine_all_signals
    ENHANCED_ENGINE_AVAILABLE = True
except ImportError:
    ENHANCED_ENGINE_AVAILABLE = False
    # logger not defined yet, will log later if needed
    pass

# Import wishlist integrations
try:
    from wishlist_integrations import (
        fetch_etsy_favorites,
        fetch_goodreads_shelves,
        parse_wishlist_for_duplicates
    )
    WISHLIST_INTEGRATIONS_AVAILABLE = True
except ImportError:
    WISHLIST_INTEGRATIONS_AVAILABLE = False
    # logger not defined yet, will log later if needed
    pass

# Import usage tracker
try:
    from usage_tracker import (
        track_anthropic_usage,
        track_apify_usage,
        get_usage_summary,
        get_daily_usage,
        get_monthly_usage
    )
    USAGE_TRACKING_AVAILABLE = True
except ImportError:
    USAGE_TRACKING_AVAILABLE = False
    pass  # Logger not defined yet

# Import link validation
try:
    from link_validation import process_recommendation_links
    LINK_VALIDATION_AVAILABLE = True
except ImportError:
    LINK_VALIDATION_AVAILABLE = False
    # logger not defined yet, will log later if needed
    pass

# Import image fetcher
try:
    from image_fetcher import process_recommendation_images
    # Set API keys for image fetching
    import image_fetcher
    # Get image API keys from environment (load_dotenv() already called above)
    google_key = os.environ.get('GOOGLE_CSE_API_KEY', '')
    google_engine = os.environ.get('GOOGLE_CUSTOM_SEARCH_ENGINE_ID', '')
    unsplash_key = os.environ.get('UNSPLASH_ACCESS_KEY', '')
    
    if google_key:
        image_fetcher.GOOGLE_CUSTOM_SEARCH_API_KEY = google_key
    if google_engine:
        image_fetcher.GOOGLE_CUSTOM_SEARCH_ENGINE_ID = google_engine
    if unsplash_key:
        image_fetcher.UNSPLASH_ACCESS_KEY = unsplash_key
    IMAGE_FETCHING_AVAILABLE = True
except ImportError:
    IMAGE_FETCHING_AVAILABLE = False
    # logger not defined yet, use print or skip
    pass

# Import favorites and share managers
try:
    from favorites_manager import add_favorite, remove_favorite, is_favorite, get_favorites
    from share_manager import generate_share_id, save_share, get_share
    FAVORITES_AVAILABLE = True
except ImportError:
    FAVORITES_AVAILABLE = False
    pass  # Logger not defined yet

# OAuth libraries
from requests_oauthlib import OAuth2Session
import requests

# Import OAuth integrations
try:
    from oauth_integrations import (
        get_pinterest_authorization_url,
        exchange_pinterest_code,
        fetch_pinterest_data as oauth_fetch_pinterest_data,
        get_spotify_authorization_url,
        exchange_spotify_code,
        fetch_spotify_data as oauth_fetch_spotify_data,
        get_etsy_authorization_url,
        exchange_etsy_code,
        fetch_etsy_favorites as oauth_fetch_etsy_favorites,
        get_google_authorization_url,
        exchange_google_code,
        fetch_youtube_subscriptions
    )
    OAUTH_INTEGRATIONS_AVAILABLE = True
except ImportError as e:
    OAUTH_INTEGRATIONS_AVAILABLE = False
    pass  # Logger not defined yet

# Import Valentine's Day features
try:
    from share_generator import generate_share_image, generate_story_image
    from referral_system import (
        generate_referral_code,
        validate_referral_code,
        apply_referral_to_user,
        credit_referrer,
        get_referral_stats,
        get_valentines_day_bonus
    )
    from flask import send_file
    VALENTINES_FEATURES_AVAILABLE = True
except ImportError:
    VALENTINES_FEATURES_AVAILABLE = False
    pass

# Enhanced modules (FIXED VERSIONS)
try:
    from link_validation import process_recommendation_links, get_reliable_link
    LINK_VALIDATION_AVAILABLE = True
except ImportError:
    LINK_VALIDATION_AVAILABLE = False
    pass  # Logger not defined yet

try:
    from image_fetcher import process_recommendation_images, get_product_image
    IMAGE_FETCHING_AVAILABLE = True
except ImportError:
    IMAGE_FETCHING_AVAILABLE = False
    pass  # Logger not defined yet

try:
    from recommendation_engine import generate_recommendations, enhance_recommendations_with_context
    RECOMMENDATION_ENGINE_AVAILABLE = True
except ImportError:
    RECOMMENDATION_ENGINE_AVAILABLE = False
    pass  # Logger not defined yet

try:
    import stripe_integration
    STRIPE_INTEGRATION_AVAILABLE = True
except ImportError:
    STRIPE_INTEGRATION_AVAILABLE = False
    pass  # Logger not defined yet

# Database (using simple JSON for MVP - upgrade to PostgreSQL later)
import shelve

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('giftwise')

app = Flask(__name__)

# SECURITY FIX: Fail fast if SECRET_KEY not set
SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    raise ValueError("SECRET_KEY environment variable is required. Set it in your .env file.")
app.secret_key = SECRET_KEY

# API Keys from environment variables
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY')
STRIPE_PRICE_ID = os.environ.get('STRIPE_PRICE_ID')
AMAZON_AFFILIATE_TAG = os.environ.get('AMAZON_AFFILIATE_TAG', '')  # Optional: for affiliate links

# Image fetching APIs (optional)
SERPAPI_API_KEY = os.environ.get('SERPAPI_API_KEY', '')
UNSPLASH_ACCESS_KEY = os.environ.get('UNSPLASH_ACCESS_KEY', '')

# Pinterest OAuth Configuration
PINTEREST_CLIENT_ID = os.environ.get('PINTEREST_CLIENT_ID')
PINTEREST_CLIENT_SECRET = os.environ.get('PINTEREST_CLIENT_SECRET')
PINTEREST_REDIRECT_URI = os.environ.get('PINTEREST_REDIRECT_URI', 'http://localhost:5000/oauth/pinterest/callback')
PINTEREST_AUTH_URL = 'https://www.pinterest.com/oauth/'
PINTEREST_TOKEN_URL = 'https://api.pinterest.com/v5/oauth/token'
PINTEREST_API_URL = 'https://api.pinterest.com/v5'

# Apify Configuration
APIFY_API_TOKEN = os.environ.get('APIFY_API_TOKEN')
APIFY_INSTAGRAM_ACTOR = 'nH2AHrwxeTRJoN5hX'
APIFY_TIKTOK_ACTOR = '0FXVyOXXEmdGcV88a'

# Spotify OAuth Configuration
SPOTIFY_CLIENT_ID = os.environ.get('SPOTIFY_CLIENT_ID', '')
SPOTIFY_CLIENT_SECRET = os.environ.get('SPOTIFY_CLIENT_SECRET', '')
SPOTIFY_REDIRECT_URI = os.environ.get('SPOTIFY_REDIRECT_URI', 'http://localhost:5000/oauth/spotify/callback')

# Etsy OAuth Configuration
ETSY_CLIENT_ID = os.environ.get('ETSY_CLIENT_ID', '')
ETSY_CLIENT_SECRET = os.environ.get('ETSY_CLIENT_SECRET', '')
ETSY_REDIRECT_URI = os.environ.get('ETSY_REDIRECT_URI', 'http://localhost:5000/oauth/etsy/callback')

# Google OAuth Configuration (for YouTube)
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')
GOOGLE_REDIRECT_URI = os.environ.get('GOOGLE_REDIRECT_URI', 'http://localhost:5000/oauth/google/callback')
GOOGLE_YOUTUBE_API_KEY = os.environ.get('GOOGLE_YOUTUBE_API_KEY', '')

# Initialize clients
if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY
if ANTHROPIC_API_KEY:
    claude_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
else:
    logger.warning("ANTHROPIC_API_KEY not set - recommendation generation will fail")

# ============================================================================
# FREEMIUM TIER CONFIGURATION + HYBRID PRICING
# ============================================================================

SUBSCRIPTION_TIERS = {
    'free': {
        'name': 'Free',
        'price': 0,
        'max_profiles': 1,
        'recommendations_per_profile': 5,
        'monthly_updates': False,
        'platforms': ['instagram', 'tiktok'],  # No Pinterest
        'features': ['basic_recommendations', 'shareable_profile']
    },
    'pro': {
        'name': 'Pro',
        'price': 4.99,
        'stripe_price_id': os.environ.get('STRIPE_PRO_PRICE_ID'),
        'max_profiles': 5,
        'recommendations_per_profile': 10,
        'monthly_updates': True,
        'platforms': ['instagram', 'tiktok', 'pinterest'],
        'features': ['basic_recommendations', 'monthly_updates', 'gift_calendar', 
                    'shareable_profile', 'all_platforms', 'priority_support']
    },
    'pro_annual': {
        'name': 'Pro Annual',
        'price': 39.99,
        'price_per_month': 3.33,
        'stripe_price_id': os.environ.get('STRIPE_PRO_ANNUAL_PRICE_ID'),
        'max_profiles': 5,
        'recommendations_per_profile': 10,
        'monthly_updates': True,
        'platforms': ['instagram', 'tiktok', 'pinterest'],
        'features': ['basic_recommendations', 'monthly_updates', 'gift_calendar',
                    'shareable_profile', 'all_platforms', 'priority_support'],
        'billing': 'annual',
        'savings': 'Save $20/year'
    },
    'gift_emergency': {
        'name': 'Gift Emergency',
        'price': 2.99,
        'type': 'one_time',
        'max_profiles': 1,
        'recommendations_per_profile': 10,
        'monthly_updates': False,
        'platforms': ['instagram', 'tiktok'],
        'features': ['basic_recommendations'],
        'description': 'One-time recommendations - no subscription needed'
    },
    'premium': {
        'name': 'Premium',
        'price': 24.99,
        'stripe_price_id': os.environ.get('STRIPE_PREMIUM_PRICE_ID'),
        'max_profiles': 999,  # Unlimited
        'recommendations_per_profile': 10,
        'monthly_updates': True,
        'platforms': ['instagram', 'tiktok', 'pinterest'],
        'features': ['basic_recommendations', 'monthly_updates', 'gift_calendar',
                    'shareable_profile', 'all_platforms', 'priority_support',
                    'concierge_service', 'manual_link_fixes', 'gift_purchase_assistance']
    }
}

# ============================================================================
# RELATIONSHIP CONTEXT - 4 TIERS
# ============================================================================

RELATIONSHIP_OPTIONS = [
    ('romantic', '❤️ Romantic Partner', 'Spouse, boyfriend/girlfriend, partner'),
    ('close_personal', '👥 Close Personal', 'Best friend, sibling, parent, child'),
    ('friendly', '😊 Friendly', 'Friend, cousin, favorite coworker'),
    ('professional', '🤝 Professional', 'Colleague, client, boss, acquaintance')
]

RELATIONSHIP_PROMPTS = {
    'romantic': """
RELATIONSHIP: Romantic Partner
- Can be intimate and sentimental
- Romantic gestures appropriate
- Higher price point acceptable ($75-200 items okay)
- Reference shared memories/inside jokes
- Jewelry, clothing, personal items are good
- Think: "What would make them feel loved and understood?"
""",
    'close_personal': """
RELATIONSHIP: Close Friend/Family
- Thoughtful and personal, but NOT romantic
- Fun, meaningful, shows you "get them"
- Mid-range pricing ($30-100 sweet spot)
- Avoid anything too intimate (no jewelry, perfume)
- Think: "What would make them excited and feel seen?"
""",
    'friendly': """
RELATIONSHIP: Friendly Connection
- Thoughtful but not too personal
- Safe, universally appealing
- Lower-mid pricing ($20-75)
- Avoid anything intimate or too specific
- Think: "What would they appreciate without feeling awkward?"
""",
    'professional': """
RELATIONSHIP: Professional Contact
- Tasteful and appropriate for work context
- Quality over sentimentality
- Mid-range pricing ($40-100)
- Nothing too personal or casual
- Think: "What shows respect and good taste?"
"""
}

# ============================================================================
# PROGRESS TRACKING (Fixed: Memory leak prevention)
# ============================================================================

scraping_progress = OrderedDict()
MAX_PROGRESS_ENTRIES = 1000

def set_progress(task_id, status, message, percent=0):
    """Update scraping progress with automatic cleanup"""
    scraping_progress[task_id] = {
        'status': status,
        'message': message,
        'percent': percent,
        'timestamp': datetime.now().isoformat()
    }
    
    # Clean up old entries to prevent memory leak
    if len(scraping_progress) > MAX_PROGRESS_ENTRIES:
        # Remove oldest 100 entries
        for _ in range(100):
            if scraping_progress:
                scraping_progress.popitem(last=False)

def get_progress(task_id):
    """Get scraping progress"""
    return scraping_progress.get(task_id, {
        'status': 'unknown',
        'message': 'Unknown status',
        'percent': 0
    })

# ============================================================================
# DATABASE HELPERS (Fixed: Thread-safe operations)
# ============================================================================

# Thread locks for database operations
db_locks = {}
lock_lock = threading.Lock()

def get_db_lock(user_id):
    """Get or create a lock for a specific user"""
    with lock_lock:
        if user_id not in db_locks:
            db_locks[user_id] = threading.Lock()
        return db_locks[user_id]

def get_user(user_id):
    """Get user data from database"""
    if not user_id:
        return None
    try:
        with shelve.open('giftwise_db') as db:
            return db.get(f'user_{user_id}')
    except Exception as e:
        logger.error(f"Error getting user {user_id}: {e}")
        return None

def save_user(user_id, data):
    """Save user data to database (thread-safe)"""
    if not user_id:
        logger.error("Attempted to save user with no user_id")
        return False
    
    lock = get_db_lock(user_id)
    try:
        with lock:
            with shelve.open('giftwise_db') as db:
                existing = db.get(f'user_{user_id}', {})
                existing.update(data)
                db[f'user_{user_id}'] = existing
        return True
    except Exception as e:
        logger.error(f"Error saving user {user_id}: {e}")
        return False

def get_session_user():
    """Get current user from session"""
    user_id = session.get('user_id')
    if user_id:
        return get_user(user_id)
    return None

def get_user_tier(user):
    """Get user's subscription tier"""
    if not user:
        return 'free'
    return user.get('subscription_tier', 'free')

def check_tier_limit(user, feature):
    """Check if user's tier allows a feature"""
    tier = get_user_tier(user)
    tier_config = SUBSCRIPTION_TIERS.get(tier, SUBSCRIPTION_TIERS['free'])
    
    if feature == 'profiles':
        current_profiles = len(user.get('saved_profiles', []))
        return current_profiles < tier_config['max_profiles']
    elif feature == 'monthly_updates':
        return tier_config['monthly_updates']
    elif feature in tier_config['features']:
        return True
    return False

# ============================================================================
# INPUT SANITIZATION
# ============================================================================

def sanitize_username(username):
    """Sanitize username input - remove dangerous characters"""
    if not username:
        return ''
    # Remove @ symbols, whitespace, special chars
    username = username.strip().replace('@', '').replace(' ', '')
    # Only allow alphanumeric, underscore, dot, hyphen (for Pinterest)
    username = re.sub(r'[^a-zA-Z0-9_.-]', '', username)
    # Limit length
    return username[:30]

# ============================================================================
# DATA QUALITY ASSESSMENT
# ============================================================================

def check_data_quality(platforms):
    """
    Assess data quality based on post counts
    Returns: dict with quality level, message, recommended rec count
    """
    total_posts = 0
    platform_counts = {}
    
    if 'instagram' in platforms:
        ig_data = platforms['instagram'].get('data', {})
        ig_posts = ig_data.get('total_posts', 0)
        platform_counts['instagram'] = ig_posts
        total_posts += ig_posts
    
    if 'tiktok' in platforms:
        tt_data = platforms['tiktok'].get('data', {})
        tt_videos = tt_data.get('total_videos', 0)
        platform_counts['tiktok'] = tt_videos
        total_posts += tt_videos
    
    if 'pinterest' in platforms:
        pinterest_pins = platforms['pinterest'].get('total_pins', 0)
        platform_counts['pinterest'] = pinterest_pins
        total_posts += pinterest_pins
    
    # Quality thresholds
    if total_posts >= 30:
        return {
            'quality': 'excellent',
            'message': f'Great! Found {total_posts} posts across platforms.',
            'recommendation_count': 10,
            'confidence': 'high',
            'total_posts': total_posts,
            'platform_counts': platform_counts
        }
    elif total_posts >= 15:
        return {
            'quality': 'good',
            'message': f'Found {total_posts} posts. Recommendations will be solid.',
            'recommendation_count': 8,
            'confidence': 'medium',
            'total_posts': total_posts,
            'platform_counts': platform_counts
        }
    elif total_posts >= 5:
        return {
            'quality': 'limited',
            'message': f'Only found {total_posts} posts. Recommendations will be more general.',
            'recommendation_count': 5,
            'confidence': 'low',
            'warning': 'Limited data - consider connecting more platforms for better results',
            'total_posts': total_posts,
            'platform_counts': platform_counts
        }
    else:
        return {
            'quality': 'insufficient',
            'message': f'Only found {total_posts} posts. Not enough data for quality recommendations.',
            'recommendation_count': 3,
            'confidence': 'very_low',
            'warning': 'Very limited data - recommendations may not be accurate',
            'total_posts': total_posts,
            'platform_counts': platform_counts
        }

# ============================================================================
# USERNAME VALIDATION (Privacy Check)
# ============================================================================

def check_instagram_privacy(username):
    """
    Simplified Instagram account check - just verify account exists
    Privacy verification is unreliable due to Instagram's changing HTML/API,
    so we let the scraping process handle privacy detection.
    
    This reduces friction - users don't need to verify account status upfront.
    Scraping will fail gracefully if account is private.
    
    Returns: dict with valid, exists, message
    """
    try:
        # Simplified approach: Just check if account exists (basic validation)
        # Don't try to verify privacy - it's too unreliable and causes friction
        # Scraping will handle privacy detection gracefully
        
        url = f'https://www.instagram.com/{username}/'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
        
        response = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
        
        # Account doesn't exist (404 is definitive)
        if response.status_code == 404:
            return {
                'valid': False,
                'exists': False,
                'message': '✗ Account not found - please check the username',
                'icon': '❌'
            }
        
        # If we got any response from Instagram (even redirects), account likely exists
        # Be very lenient - just verify it's not a 404
        # Scraping will handle privacy detection and fail gracefully if private
        if response.status_code in [200, 302, 301] or len(response.text) > 100:
            return {
                'valid': True,
                'exists': True,
                'message': '✓ Account found - we\'ll check if it\'s public when connecting',
                'icon': '✅'
            }
        
        # If we can't determine, allow them to try anyway
        return {
            'valid': True,
            'exists': True,
            'message': '✓ Ready to connect - we\'ll verify when connecting',
            'icon': '✅'
        }
    
    except requests.Timeout:
        return {
            'valid': False,
            'error': 'Request timed out',
            'message': '⚠️ Instagram is slow to respond - try again',
            'icon': '⚠️'
        }
    except Exception as e:
        logger.error(f"Instagram privacy check error: {e}")
        return {
            'valid': True,  # Allow them to try anyway
            'error': str(e),
            'message': '⚠️ Unable to verify - click Connect to try',
            'icon': '⚠️'
        }

def check_tiktok_privacy(username):
    """
    Check if TikTok account exists
    (Privacy detection is unreliable due to JS rendering, so we just check existence)
    """
    try:
        url = f'https://www.tiktok.com/@{username}'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        # Account doesn't exist
        if response.status_code == 404:
            return {
                'valid': False,
                'private': False,
                'exists': False,
                'message': '✗ Account not found - please check the username',
                'icon': '❌'
            }
        
        if response.status_code != 200:
            return {
                'valid': False,
                'error': 'Unable to check account',
                'message': '⚠️ Unable to verify account - try again',
                'icon': '⚠️'
            }
        
        # If we get 200, account exists
        # Privacy detection via HTML is unreliable for TikTok (JS-rendered)
        # Let Apify handle it during actual scraping
        return {
            'valid': True,
            'private': False,
            'exists': True,
            'message': '✓ Account found - we\'ll verify access when connecting',
            'icon': '✅'
        }
    
    except requests.Timeout:
        return {
            'valid': False,
            'error': 'Request timed out',
            'message': '⚠️ TikTok is slow to respond - try again',
            'icon': '⚠️'
        }
    except Exception as e:
        logger.error(f"TikTok validation error for @{username}: {e}")
        # If validation fails, let them try anyway
        return {
            'valid': True,
            'error': str(e),
            'message': '✓ Unable to verify - click Connect to try',
            'icon': '⚠️'
        }

def check_pinterest_profile(username):
    """
    Check if Pinterest profile exists and is accessible
    Returns: dict with valid, exists, message
    """
    try:
        url = f'https://www.pinterest.com/{username}/'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10, allow_redirects=False)
        
        # Account doesn't exist
        if response.status_code == 404:
            return {
                'valid': False,
                'exists': False,
                'message': '✗ Profile not found - please check the username',
                'icon': '❌'
            }
        
        # Profile exists
        if response.status_code == 200:
            return {
                'valid': True,
                'exists': True,
                'message': '✓ Profile found',
                'icon': '✅'
            }
        
        return {
            'valid': False,
            'exists': False,
            'message': '⚠️ Unable to verify profile',
            'icon': '⚠️'
        }
    
    except Exception as e:
        logger.error(f"Pinterest profile check error: {e}")
        return {
            'valid': True,  # Allow them to try anyway
            'error': str(e),
            'message': '⚠️ Unable to verify - click Connect to try',
            'icon': '⚠️'
        }

# ============================================================================
# SCRAPING FUNCTIONS (with progress tracking)
# ============================================================================

def scrape_instagram_profile(username, max_posts=50, task_id=None):
    """
    Scrape Instagram with progress tracking
    """
    if not APIFY_API_TOKEN:
        logger.warning("No Apify token configured")
        return None
    
    try:
        if task_id:
            set_progress(task_id, 'running', 'Starting Instagram scraper...', 5)
        
        logger.info(f"Starting Instagram scrape for @{username}")
        
        response = requests.post(
            f'https://api.apify.com/v2/acts/{APIFY_INSTAGRAM_ACTOR}/runs?token={APIFY_API_TOKEN}',
            json={
                'username': [username],
                'resultsLimit': max_posts
            },
            timeout=30
        )
        
        if response.status_code != 201:
            if task_id:
                set_progress(task_id, 'error', 'Failed to start scraper', 0)
            logger.error(f"Failed to start Instagram scraper: {response.status_code}")
            return None
        
        run_id = response.json()['data']['id']
        if task_id:
            set_progress(task_id, 'running', f'Finding @{username}...', 15)
        
        # Poll for completion
        max_wait = 120
        elapsed = 0
        
        while elapsed < max_wait:
            wait_time = 2 if elapsed < 30 else 5
            time.sleep(wait_time)
            elapsed += wait_time
            
            # Update progress
            if task_id:
                progress_pct = min(15 + (elapsed / max_wait) * 75, 90)
                messages = {
                    10: f'Finding @{username}...',
                    30: 'Analyzing profile...',
                    50: 'Downloading posts...',
                    70: 'Extracting interests...',
                    85: 'Processing data...'
                }
                msg = messages.get(int(progress_pct // 10) * 10, 'Analyzing profile...')
                set_progress(task_id, 'running', msg, progress_pct)
            
            status_response = requests.get(
                f'https://api.apify.com/v2/actor-runs/{run_id}?token={APIFY_API_TOKEN}',
                timeout=10
            )
            
            if status_response.status_code != 200:
                continue
                
            status = status_response.json()['data']['status']
            
            if status == 'SUCCEEDED':
                break
            elif status in ['FAILED', 'ABORTED', 'TIMED-OUT']:
                if task_id:
                    set_progress(task_id, 'error', 'Instagram scraping failed', 0)
                logger.error(f"Instagram scraping failed with status: {status}")
                return None
        
        # Check if we timed out
        if elapsed >= max_wait:
            logger.warning(f"Instagram scrape timeout after {max_wait}s")
            if task_id:
                set_progress(task_id, 'error', 'Scraping timed out', 0)
            return None
        
        # Get results
        results_response = requests.get(
            f'https://api.apify.com/v2/actor-runs/{run_id}/dataset/items?token={APIFY_API_TOKEN}',
            timeout=30
        )
        
        if results_response.status_code != 200:
            if task_id:
                set_progress(task_id, 'error', 'Failed to retrieve data', 0)
            logger.error(f"Failed to retrieve Instagram data: {results_response.status_code}")
            return None
        
        data = results_response.json()
        
        if not data:
            if task_id:
                set_progress(task_id, 'error', 'No posts found', 0)
            logger.warning(f"No posts found for Instagram user @{username}")
            return None
        
        # Parse data
        first_post = data[0]
        owner_username = first_post.get('ownerUsername', username)
        owner_full_name = first_post.get('ownerFullName', '')
        
        posts = data[:max_posts]
        
        result = {
            'username': owner_username,
            'full_name': owner_full_name,
            'bio': '',
            'followers': 0,
            'posts': [
                {
                    'caption': post.get('caption', ''),
                    'likes': post.get('likesCount', 0),
                    'comments': post.get('commentsCount', 0),
                    'timestamp': post.get('timestamp', ''),
                    'type': post.get('type', 'image'),
                    'url': post.get('url', ''),
                    'hashtags': post.get('hashtags', [])
                }
                for post in posts
            ],
            'highlights': [],
            'total_posts': len(posts),
            'total_highlights': 0,
            'scraped_at': datetime.now().isoformat()
        }
        
        if task_id:
            set_progress(task_id, 'complete', f'✓ Connected! Found {len(posts)} posts', 100)
        
        logger.info(f"Successfully scraped {len(posts)} Instagram posts for @{username}")
        
        # Track Apify usage (typically 1 compute unit per run)
        if USAGE_TRACKING_AVAILABLE:
            try:
                track_apify_usage(1, 'instagram')
            except Exception as e:
                logger.warning(f"Failed to track Apify usage: {e}")

        # Track Apify usage
        if USAGE_TRACKING_AVAILABLE:
            track_apify_usage(1, 'instagram')
        
        return result
        
    except Exception as e:
        logger.error(f"Instagram scraping error: {e}", exc_info=True)
        if task_id:
            set_progress(task_id, 'error', f'Error: {str(e)}', 0)
        return None

def scrape_tiktok_profile(username, max_videos=50, task_id=None):
    """
    Scrape TikTok with progress tracking and repost analysis
    """
    if not APIFY_API_TOKEN:
        logger.warning("No Apify token configured")
        return None
    
    try:
        if task_id:
            set_progress(task_id, 'running', 'Starting TikTok scraper...', 5)
        
        logger.info(f"Starting TikTok scrape for @{username}")
        
        response = requests.post(
            f'https://api.apify.com/v2/acts/{APIFY_TIKTOK_ACTOR}/runs?token={APIFY_API_TOKEN}',
            json={
                'profiles': [username],
                'resultsPerPage': max_videos
            },
            timeout=30
        )
        
        if response.status_code != 201:
            if task_id:
                set_progress(task_id, 'error', 'Failed to start scraper', 0)
            logger.error(f"Failed to start TikTok scraper: {response.status_code}")
            return None
        
        run_id = response.json()['data']['id']
        if task_id:
            set_progress(task_id, 'running', f'Finding @{username}...', 15)
        
        # Poll for completion
        max_wait = 120
        elapsed = 0
        
        while elapsed < max_wait:
            wait_time = 2 if elapsed < 30 else 5
            time.sleep(wait_time)
            elapsed += wait_time
            
            # Update progress
            if task_id:
                progress_pct = min(15 + (elapsed / max_wait) * 75, 90)
                messages = {
                    10: f'Finding @{username}...',
                    30: 'Analyzing videos...',
                    50: 'Detecting reposts...',
                    70: 'Extracting interests...',
                    85: 'Processing data...'
                }
                msg = messages.get(int(progress_pct // 10) * 10, 'Analyzing videos...')
                set_progress(task_id, 'running', msg, progress_pct)
            
            status_response = requests.get(
                f'https://api.apify.com/v2/actor-runs/{run_id}?token={APIFY_API_TOKEN}',
                timeout=10
            )
            
            if status_response.status_code != 200:
                continue
                
            status = status_response.json()['data']['status']
            
            if status == 'SUCCEEDED':
                break
            elif status in ['FAILED', 'ABORTED', 'TIMED-OUT']:
                if task_id:
                    set_progress(task_id, 'error', 'TikTok scraping failed', 0)
                logger.error(f"TikTok scraping failed with status: {status}")
                return None
        
        # Get results
        results_response = requests.get(
            f'https://api.apify.com/v2/actor-runs/{run_id}/dataset/items?token={APIFY_API_TOKEN}',
            timeout=30
        )
        
        if results_response.status_code != 200:
            if task_id:
                set_progress(task_id, 'error', 'Failed to retrieve data', 0)
            logger.error(f"Failed to retrieve TikTok data: {results_response.status_code}")
            return None
        
        data = results_response.json()
        
        if not data:
            if task_id:
                set_progress(task_id, 'error', 'No videos found', 0)
            logger.warning(f"No videos found for TikTok user @{username}")
            return None
        
        # Parse with repost intelligence
        parsed_data = parse_tiktok_data(data, username)
        
        if task_id:
            total_videos = parsed_data.get('total_videos', 0)
            set_progress(task_id, 'complete', f'✓ Connected! Found {total_videos} videos', 100)
        
        logger.info(f"Successfully scraped {parsed_data.get('total_videos', 0)} TikTok videos for @{username}")
        
        # Track Apify usage (typically 1 compute unit per run)
        if USAGE_TRACKING_AVAILABLE:
            try:
                track_apify_usage(1, 'tiktok')
            except Exception as e:
                logger.warning(f"Failed to track Apify usage: {e}")
        
        return parsed_data
        
    except Exception as e:
        logger.error(f"TikTok scraping error: {e}", exc_info=True)
        if task_id:
            set_progress(task_id, 'error', f'Error: {str(e)}', 0)
        return None

def scrape_pinterest_profile(username, max_pins=100, task_id=None):
    """
    Scrape Pinterest profile (boards and pins)
    Uses basic web scraping - can be enhanced with Apify later
    """
    try:
        if task_id:
            set_progress(task_id, 'scraping', f'Scraping Pinterest profile @{username}...', 10)
        
        logger.info(f"Starting Pinterest scrape for @{username}")
        
        # Pinterest profile URL
        profile_url = f'https://www.pinterest.com/{username}/'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        if task_id:
            set_progress(task_id, 'scraping', 'Fetching profile page...', 30)
        
        response = requests.get(profile_url, headers=headers, timeout=15)
        
        if response.status_code != 200:
            if task_id:
                set_progress(task_id, 'error', f'Failed to access Pinterest profile (status {response.status_code})', 0)
            logger.error(f"Pinterest profile not accessible: {response.status_code}")
            return None
        
        html = response.text
        
        if task_id:
            set_progress(task_id, 'scraping', 'Parsing pins and boards...', 50)
        
        # Extract basic data from HTML
        import re
        import json
        
        pins = []
        boards = []
        hashtags = []
        
        # Try to extract JSON-LD or embedded JSON data
        json_patterns = [
            r'<script[^>]*type="application/json"[^>]*>(.*?)</script>',
            r'window\.__initialData__\s*=\s*({.*?});',
            r'<script[^>]*id="initial-state"[^>]*>(.*?)</script>'
        ]
        
        extracted_data = None
        for pattern in json_patterns:
            matches = re.findall(pattern, html, re.DOTALL)
            for match in matches:
                try:
                    data = json.loads(match)
                    if isinstance(data, dict) and ('pins' in str(data).lower() or 'boards' in str(data).lower()):
                        extracted_data = data
                        break
                except:
                    continue
            if extracted_data:
                break
        
        # Fallback: Extract basic info from HTML
        # Get board names
        board_pattern = r'<a[^>]*href="/[^/]+/([^/]+)/"[^>]*>.*?<div[^>]*>([^<]+)</div>'
        board_matches = re.findall(board_pattern, html)
        for board_slug, board_name in board_matches[:20]:  # Limit to 20 boards
            boards.append({
                'name': board_name.strip(),
                'slug': board_slug,
                'url': f'https://www.pinterest.com/{username}/{board_slug}/'
            })
        
        # Extract hashtags from pin descriptions
        hashtag_pattern = r'#(\w+)'
        hashtag_matches = re.findall(hashtag_pattern, html)
        hashtags = list(set(hashtag_matches[:50]))  # Unique hashtags, limit 50
        
        # Extract pin descriptions/titles
        pin_patterns = [
            r'<div[^>]*class="[^"]*pin[^"]*"[^>]*>.*?<div[^>]*>([^<]+)</div>',
            r'alt="([^"]+)"[^>]*class="[^"]*pin[^"]*"',
            r'<img[^>]*alt="([^"]+)"[^>]*>'
        ]
        
        pin_titles = []
        for pattern in pin_patterns:
            matches = re.findall(pattern, html, re.DOTALL)
            pin_titles.extend([m.strip() for m in matches if len(m.strip()) > 5])
        
        # Create pin objects
        for i, title in enumerate(pin_titles[:max_pins]):
            pins.append({
                'title': title,
                'description': title,
                'index': i
            })
        
        if task_id:
            set_progress(task_id, 'scraping', f'Found {len(pins)} pins, {len(boards)} boards', 80)
        
        # Extract interests from boards and pins
        interests = []
        for board in boards:
            interests.append(board['name'].lower())
        for pin in pins[:20]:  # Analyze top pins
            interests.append(pin['title'].lower())
        
        # Build result
        result = {
            'platform': 'pinterest',
            'username': username,
            'method': 'scraping',
            'pins': pins[:max_pins],
            'boards': boards,
            'hashtags': hashtags[:30],
            'total_pins': len(pins),
            'total_boards': len(boards),
            'interests': list(set(interests))[:50],
            'collected_at': datetime.now().isoformat()
        }
        
        if task_id:
            set_progress(task_id, 'complete', f'Scraped {len(pins)} pins from {len(boards)} boards', 100)
        
        logger.info(f"Successfully scraped {len(pins)} Pinterest pins for @{username}")
        return result
    
    except Exception as e:
        logger.error(f"Pinterest scraping error for @{username}: {e}", exc_info=True)
        if task_id:
            set_progress(task_id, 'error', f'Error: {str(e)}', 0)
        return None

def parse_tiktok_data(data, username):
    """
    Parse TikTok data with repost analysis
    """
    videos = []
    reposts = []
    original_creators = []
    hashtags_all = []
    music_all = []
    
    for item in data:
        video_info = {
            'description': item.get('text', ''),
            'likes': item.get('diggCount', 0),
            'comments': item.get('commentCount', 0),
            'shares': item.get('shareCount', 0),
            'plays': item.get('playCount', 0),
            'timestamp': item.get('createTime', ''),
            'url': item.get('webVideoUrl', ''),
            'hashtags': [tag.get('name', '') for tag in item.get('hashtags', [])],
            'music': item.get('musicMeta', {}).get('musicName', '')
        }
        
        # Check if this is a repost (diversificationId indicates repost)
        is_repost = item.get('diversificationId') is not None
        
        if is_repost:
            # This is a repost - track original creator
            original_author = item.get('authorMeta', {}).get('name', 'unknown')
            reposts.append(video_info)
            original_creators.append(original_author)
        
        videos.append(video_info)
        hashtags_all.extend(video_info['hashtags'])
        if video_info['music']:
            music_all.append(video_info['music'])
    
    # Analyze repost patterns
    creator_frequency = Counter(original_creators)
    hashtag_frequency = Counter(hashtags_all)
    music_frequency = Counter(music_all)
    
    return {
        'username': username,
        'videos': videos,
        'reposts': reposts,
        'total_videos': len(videos),
        'total_reposts': len(reposts),
        'repost_percentage': (len(reposts) / len(videos) * 100) if videos else 0,
        'favorite_creators': creator_frequency.most_common(10),
        'top_hashtags': dict(hashtag_frequency.most_common(15)),
        'top_music': dict(music_frequency.most_common(10)),
        'repost_patterns': {
            'total_reposts': len(reposts),
            'favorite_creators': creator_frequency.most_common(5),
            'repost_percentage': (len(reposts) / len(videos) * 100) if videos else 0
        },
        'scraped_at': datetime.now().isoformat()
    }

# ============================================================================
# API ROUTES
# ============================================================================

@app.route('/')
def index():
    """Landing page"""
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """Signup page with 4-tier relationship selection"""
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        recipient_type = request.form.get('recipient_type')
        relationship = request.form.get('relationship', '')
        
        if not email:
            return render_template('signup.html', 
                                 relationship_options=RELATIONSHIP_OPTIONS,
                                 error='Email is required')
        
        # Create user
        user_id = email
        save_user(user_id, {
            'email': email,
            'recipient_type': recipient_type,
            'relationship': relationship,
            'subscription_tier': 'free',  # Default to free tier
            'created_at': datetime.now().isoformat()
        })
        
        session['user_id'] = user_id
        logger.info(f"New user signed up: {email}")
        
        return redirect('/connect-platforms')
    
    return render_template('signup.html', relationship_options=RELATIONSHIP_OPTIONS)


@app.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    """Create Stripe checkout session for Pro subscription"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Please log in first'}), 401
    
    user = get_user(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    email = user.get('email', '')
    if not email:
        return jsonify({'error': 'Email required'}), 400
    
    # Determine which plan
    plan = request.form.get('plan', 'pro')
    
    if not STRIPE_INTEGRATION_AVAILABLE:
        logger.error("Stripe integration not available")
        return jsonify({'error': 'Payment system not configured'}), 500
    
    # Get correct price ID
    if plan == 'premium':
        price_id = stripe_integration.STRIPE_PREMIUM_PRICE_ID
    elif plan == 'pro_annual':
        price_id = stripe_integration.STRIPE_PRO_ANNUAL_PRICE_ID
    else:
        price_id = stripe_integration.STRIPE_PRO_PRICE_ID
    
    if not price_id:
        logger.error(f"Stripe price ID not configured for plan: {plan}")
        return jsonify({'error': 'Subscription plan not available'}), 500
    
    # Create checkout session
    checkout_url = stripe_integration.create_checkout_session(
        user_email=email,
        price_id=price_id,
        success_url=request.url_root + 'upgrade/success',
        cancel_url=request.url_root + 'upgrade',
        metadata={'user_id': user_id, 'plan': plan}
    )
    
    if checkout_url:
        logger.info(f"Created Stripe checkout for {user_id} - plan: {plan}")
        return redirect(checkout_url)
    else:
        logger.error("Failed to create Stripe checkout session")
        return jsonify({'error': 'Payment system error'}), 500

@app.route('/stripe/webhook', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhook events"""
    if not STRIPE_INTEGRATION_AVAILABLE:
        return jsonify({'error': 'Stripe not configured'}), 500
    
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')
    
    if not sig_header:
        logger.error("Stripe webhook missing signature")
        return jsonify({'error': 'Missing signature'}), 400
    
    event_data = stripe_integration.handle_webhook(payload, sig_header)
    
    if not event_data:
        logger.error("Invalid Stripe webhook")
        return jsonify({'error': 'Invalid webhook'}), 400
    
    event_type = event_data.get('event_type')
    logger.info(f"Processing Stripe webhook: {event_type}")
    
    # Handle subscription created
    if event_type == 'subscription_created':
        customer_email = event_data.get('customer_email')
        subscription_id = event_data.get('subscription_id')
        customer_id = event_data.get('customer_id')
        metadata = event_data.get('metadata', {})
        
        user_id = metadata.get('user_id')
        if user_id:
            user = get_user(user_id)
            if user:
                user['subscription_tier'] = 'pro'
                user['stripe_customer_id'] = customer_id
                user['stripe_subscription_id'] = subscription_id
                user['subscription_started_at'] = datetime.now().isoformat()
                save_user(user_id, user)
                logger.info(f"User {customer_email} upgraded to Pro")
    
    # Handle subscription cancelled
    elif event_type == 'subscription_cancelled':
        subscription_id = event_data.get('subscription_id')
        # Find and downgrade user
        try:
            with shelve.open(USER_DB, flag='r') as db:
                for uid, user_data in db.items():
                    if user_data.get('stripe_subscription_id') == subscription_id:
                        user_data['subscription_tier'] = 'free'
                        user_data['stripe_subscription_id'] = None
                        save_user(uid, user_data)
                        logger.info(f"User downgraded to free")
                        break
        except Exception as e:
            logger.error(f"Error downgrading user: {e}")
    
    return jsonify({'status': 'success'}), 200


@app.route('/connect-platforms')
def connect_platforms():
    """Platform connection page"""
    user = get_session_user()
    if not user:
        return redirect('/signup')
    
    # Get user's subscription tier
    tier = get_user_tier(user)
    tier_config = SUBSCRIPTION_TIERS[tier]
    allowed_platforms = tier_config['platforms']
    
    # Get platforms with safe defaults
    platforms = user.get('platforms', {})
    
    # Initialize platforms if they don't exist
    for platform_name in ['instagram', 'tiktok', 'pinterest']:
        if platform_name not in platforms:
            platforms[platform_name] = {'status': 'not_connected', 'username': ''}
    
    # Count connected platforms
    connected_count = sum(1 for p in platforms.values() if p.get('status') == 'connected')
    total_available = len(allowed_platforms)
    
    return render_template('connect_platforms.html', 
                         user=user,
                         platforms=platforms,
                         allowed_platforms=allowed_platforms,
                         subscription_tier=tier,
                         connected_count=connected_count,
                         total_available=total_available,
                         recipient_type=user.get('recipient_type', 'myself'),
                         wishlists=user.get('wishlists', []))

@app.route('/api/validate-username', methods=['POST'])
def validate_username():
    """Instant username validation endpoint"""
    try:
        data = request.get_json()
        platform = data.get('platform')
        username = sanitize_username(data.get('username', ''))
        
        if not username:
            return jsonify({'valid': False, 'message': 'Username required'})
        
        if platform == 'instagram':
            result = check_instagram_privacy(username)
        elif platform == 'tiktok':
            result = check_tiktok_privacy(username)
        elif platform == 'pinterest':
            result = check_pinterest_profile(username)
        else:
            return jsonify({'valid': False, 'message': 'Invalid platform'})
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Username validation error: {e}")
        return jsonify({'valid': False, 'message': 'Validation error occurred'}), 500

@app.route('/connect/instagram', methods=['POST'])
def connect_instagram():
    """Save Instagram username (scraping happens on generate)"""
    user = get_session_user()
    if not user:
        return jsonify({'success': False, 'error': 'Not logged in'}), 401
    
    # Accept JSON data from frontend
    data = request.get_json()
    username = sanitize_username(data.get('username', '') if data else '')
    
    if not username:
        return jsonify({'success': False, 'error': 'Username required'}), 400
    
    user_id = session['user_id']
    
    # Just save the username - don't scrape yet
    platforms = user.get('platforms', {})
    platforms['instagram'] = {
        'username': username,
        'status': 'connected',  # Mark as connected
        'method': 'scraping',
        'connected_at': datetime.now().isoformat()
    }
    save_user(user_id, {'platforms': platforms})
    logger.info(f"User {user_id} connected Instagram: @{username}")
    
    return jsonify({'success': True, 'username': username})

@app.route('/connect/tiktok', methods=['POST'])
def connect_tiktok():
    """Save TikTok username (scraping happens on generate)"""
    user = get_session_user()
    if not user:
        return jsonify({'success': False, 'error': 'Not logged in'}), 401
    
    # Accept JSON data from frontend
    data = request.get_json()
    username = sanitize_username(data.get('username', '') if data else '')
    
    if not username:
        return jsonify({'success': False, 'error': 'Username required'}), 400
    
    user_id = session['user_id']
    
    # Just save the username - don't scrape yet
    platforms = user.get('platforms', {})
    platforms['tiktok'] = {
        'username': username,
        'status': 'connected',  # Mark as connected
        'method': 'scraping',
        'connected_at': datetime.now().isoformat()
    }
    save_user(user_id, {'platforms': platforms})
    logger.info(f"User {user_id} connected TikTok: @{username}")
    
    return jsonify({'success': True, 'username': username})

@app.route('/connect/etsy', methods=['POST'])
def connect_etsy():
    """Connect Etsy wishlist via OAuth"""
    user = get_session_user()
    if not user:
        return redirect('/signup')
    
    if not OAUTH_INTEGRATIONS_AVAILABLE:
        return redirect('/connect-platforms?error=oauth_not_available')
    
    auth_url = get_etsy_authorization_url()
    
    if not auth_url:
        return redirect('/connect-platforms?error=etsy_not_configured')
    
    # Store state for CSRF protection
    session['etsy_oauth_state'] = 'etsy_auth'
    
    return redirect(auth_url)

@app.route('/oauth/etsy/callback')
def etsy_oauth_callback():
    """Handle Etsy OAuth callback"""
    user = get_session_user()
    if not user:
        return redirect('/signup')
    
    code = request.args.get('code')
    state = request.args.get('state')
    
    # Verify state
    if state != session.get('etsy_oauth_state'):
        return redirect('/connect-platforms?error=oauth_state_mismatch')
    
    if not code:
        return redirect('/connect-platforms?error=etsy_auth_failed')
    
    # Exchange code for token
    token_data = exchange_etsy_code(code)
    
    if not token_data:
        return redirect('/connect-platforms?error=etsy_token_failed')
    
    # Fetch favorites
    favorites_data = oauth_fetch_etsy_favorites(token_data['access_token'])
    
    if not favorites_data:
        return redirect('/connect-platforms?error=etsy_fetch_failed')
    
    # Save to user
    user_id = session['user_id']
    wishlists = user.get('wishlists', [])
    
    # Update or add Etsy wishlist
    etsy_wishlist = next((w for w in wishlists if w.get('platform') == 'etsy'), None)
    if etsy_wishlist:
        etsy_wishlist.update({
            'status': 'complete',
            'data': favorites_data,
            'access_token': token_data['access_token'],
            'refresh_token': token_data.get('refresh_token'),
            'connected_at': datetime.now().isoformat()
        })
    else:
        wishlists.append({
            'platform': 'etsy',
            'status': 'complete',
            'data': favorites_data,
            'access_token': token_data['access_token'],
            'refresh_token': token_data.get('refresh_token'),
            'connected_at': datetime.now().isoformat()
        })
    
    save_user(user_id, {'wishlists': wishlists})
    logger.info(f"User {user_id} connected Etsy via OAuth")
    
    return redirect('/connect-platforms?success=etsy_connected')

@app.route('/disconnect/<platform>', methods=['POST'])
def disconnect_platform(platform):
    """Disconnect a platform"""
    user = get_session_user()
    if not user:
        return redirect('/signup')
    
    user_id = session['user_id']
    platforms = user.get('platforms', {})
    wishlists = user.get('wishlists', [])
    
    # Remove from platforms
    if platform in platforms:
        del platforms[platform]
        logger.info(f"User {user_id} disconnected {platform}")
    
    # Remove from wishlists if it's a wishlist platform
    wishlists = [w for w in wishlists if w.get('platform') != platform]
    
    save_user(user_id, {'platforms': platforms, 'wishlists': wishlists})
    
    return redirect('/connect-platforms?success=disconnected')

@app.route('/connect/goodreads', methods=['POST'])
def connect_goodreads():
    """Connect Goodreads (scraping public profile)"""
    user = get_session_user()
    if not user:
        return redirect('/signup')
    
    username = sanitize_username(request.form.get('username', ''))
    
    if not username:
        return redirect('/connect-platforms?error=goodreads_no_username')
    
    user_id = session['user_id']
    
    # Save Goodreads username (will scrape "want to read" shelf)
    wishlists = user.get('wishlists', [])
    
    # Check if already connected
    goodreads_wishlist = next((w for w in wishlists if w.get('platform') == 'goodreads'), None)
    
    if goodreads_wishlist:
        goodreads_wishlist['username'] = username
        goodreads_wishlist['status'] = 'ready'
    else:
        wishlists.append({
            'platform': 'goodreads',
            'username': username,
            'status': 'ready',
            'method': 'scraping'
        })
    
    save_user(user_id, {'wishlists': wishlists})
    logger.info(f"User {user_id} connected Goodreads: {username}")
    
    return redirect('/connect-platforms?success=goodreads_ready')

@app.route('/connect/youtube', methods=['POST'])
def connect_youtube():
    """Connect YouTube via API key (alternative to OAuth)"""
    user = get_session_user()
    if not user:
        return redirect('/signup')
    
    channel_id_or_username = sanitize_username(request.form.get('channel_id', ''))
    
    if not channel_id_or_username:
        return redirect('/connect-platforms?error=youtube_no_channel')
    
    user_id = session['user_id']
    
    # Try to fetch subscriptions using API key method
    if GOOGLE_YOUTUBE_API_KEY and OAUTH_INTEGRATIONS_AVAILABLE:
        try:
            youtube_data = fetch_youtube_subscriptions(
                api_key=GOOGLE_YOUTUBE_API_KEY,
                channel_id=channel_id_or_username
            )
            
            if youtube_data:
                platforms = user.get('platforms', {})
                platforms['youtube'] = {
                    'channel_id': channel_id_or_username,
                    'data': youtube_data,
                    'status': 'complete',
                    'method': 'api_key',
                    'connected_at': datetime.now().isoformat()
                }
                save_user(user_id, {'platforms': platforms})
                logger.info(f"User {user_id} connected YouTube via API key: {channel_id_or_username}")
                return redirect('/connect-platforms?success=youtube_connected')
        except Exception as e:
            logger.error(f"YouTube API key fetch error: {e}")
    
    # Fallback: just save channel ID for later
    platforms = user.get('platforms', {})
    platforms['youtube'] = {
        'channel_id': channel_id_or_username,
        'status': 'ready',
        'method': 'api'
    }
    save_user(user_id, {'platforms': platforms})
    logger.info(f"User {user_id} saved YouTube channel ID: {channel_id_or_username}")
    
    return redirect('/connect-platforms?success=youtube_ready')

@app.route('/start-scraping', methods=['POST'])
def start_scraping():
    """Start parallel scraping for all connected platforms"""
    user = get_session_user()
    if not user:
        return redirect('/signup')
    
    platforms = user.get('platforms', {})
    user_id = session['user_id']
    
    # Generate task IDs for tracking
    scrape_tasks = {}
    
    # Start scraping threads for all platforms in parallel
    if 'instagram' in platforms and platforms['instagram'].get('status') in ['ready', 'connected']:
        task_id = str(uuid.uuid4())
        scrape_tasks['instagram'] = task_id
        username = platforms['instagram']['username']
        
        def scrape_ig():
            data = scrape_instagram_profile(username, max_posts=50, task_id=task_id)
            if data:
                user = get_user(user_id)
                if user:
                    platforms = user.get('platforms', {})
                    platforms['instagram']['data'] = data
                    platforms['instagram']['status'] = 'complete'
                    platforms['instagram']['connected_at'] = datetime.now().isoformat()
                    save_user(user_id, {'platforms': platforms})
        
        thread = threading.Thread(target=scrape_ig)
        thread.daemon = True
        thread.start()
    
    if 'tiktok' in platforms and platforms['tiktok'].get('status') in ['ready', 'connected']:
        task_id = str(uuid.uuid4())
        scrape_tasks['tiktok'] = task_id
        username = platforms['tiktok']['username']
        
        def scrape_tt():
            data = scrape_tiktok_profile(username, max_videos=50, task_id=task_id)
            if data:
                user = get_user(user_id)
                if user:
                    platforms = user.get('platforms', {})
                    platforms['tiktok']['data'] = data
                    platforms['tiktok']['status'] = 'complete'
                    platforms['tiktok']['connected_at'] = datetime.now().isoformat()
                    save_user(user_id, {'platforms': platforms})
        
        thread = threading.Thread(target=scrape_tt)
        thread.daemon = True
        thread.start()
    
    # Pinterest scraping (if using scraping method, not OAuth)
    if 'pinterest' in platforms:
        pinterest_data = platforms['pinterest']
        # Only scrape if method is 'scraping' and status is 'ready'
        if pinterest_data.get('method') == 'scraping' and pinterest_data.get('status') == 'ready':
            task_id = str(uuid.uuid4())
            scrape_tasks['pinterest'] = task_id
            username = pinterest_data['username']
            
            def scrape_pin():
                try:
                    data = scrape_pinterest_profile(username, max_pins=100, task_id=task_id)
                    if data:
                        user = get_user(user_id)
                        if user:
                            platforms = user.get('platforms', {})
                            platforms['pinterest']['data'] = data
                            platforms['pinterest']['status'] = 'complete'
                            platforms['pinterest']['connected_at'] = datetime.now().isoformat()
                            save_user(user_id, {'platforms': platforms})
                            logger.info(f"Pinterest scraping completed for @{username}")
                    else:
                        # Mark as failed if scraping returned None
                        logger.warning(f"Pinterest scraping returned None for @{username}")
                        user = get_user(user_id)
                        if user:
                            platforms = user.get('platforms', {})
                            platforms['pinterest']['status'] = 'failed'
                            platforms['pinterest']['error'] = 'Failed to scrape Pinterest profile'
                            save_user(user_id, {'platforms': platforms})
                except Exception as e:
                    logger.error(f"Error scraping Pinterest for @{username}: {e}")
                    user = get_user(user_id)
                    if user:
                        platforms = user.get('platforms', {})
                        platforms['pinterest']['status'] = 'failed'
                        platforms['pinterest']['error'] = f'Scraping error: {str(e)}'
                        save_user(user_id, {'platforms': platforms})
            
            thread = threading.Thread(target=scrape_pin)
            thread.daemon = True
            thread.start()
            logger.info(f"Started Pinterest scraping thread for @{username}")
    
    # Redirect to multi-platform progress page
    return redirect('/scraping-in-progress')

@app.route('/scraping-in-progress')
def scraping_in_progress():
    """Show scraping progress page"""
    user = get_session_user()
    if not user:
        return redirect('/signup')
    
    # Get platforms that are being scraped
    platforms = user.get('platforms', {})
    
    # Filter to only platforms that are connected or scraping
    active_platforms = {}
    for platform_name, platform_data in platforms.items():
        if platform_data.get('status') in ['scraping', 'ready', 'complete', 'connected']:
            active_platforms[platform_name] = platform_data
    
    # If no platforms are being scraped, redirect to connect page
    if not active_platforms:
        return redirect('/connect-platforms')
    
    # Get recipient type for correct pronouns
    recipient_type = user.get('recipient_type', 'myself')
    
    return render_template(
        'scraping_in_progress.html',
        platforms=active_platforms,
        user_id=user.get('user_id'),
        recipient_type=recipient_type
    )

@app.route('/scraping-progress')
def scraping_progress_alias():
    """Alias for backward compatibility"""
    return scraping_in_progress()

@app.route('/api/scraping-status')
def api_scraping_status():
    """API endpoint to check scraping status (alias for /api/check-scraping-status)"""
    return check_scraping_status()

@app.route('/connect-progress/<platform>/<task_id>')
def connect_progress(platform, task_id):
    """Progress page for scraping"""
    return render_template('scraping_progress.html', platform=platform, task_id=task_id)

@app.route('/api/scrape-progress/<task_id>')
def scrape_progress_stream(task_id):
    """Server-Sent Events endpoint for progress updates"""
    def generate():
        timeout = 180  # 3 minutes
        start = time.time()
        
        while time.time() - start < timeout:
            progress = get_progress(task_id)
            yield f"data: {json.dumps(progress)}\n\n"
            
            if progress.get('status') in ['complete', 'error']:
                break
            
            time.sleep(1)
    
    return Response(generate(), mimetype='text/event-stream')

@app.route('/generate-recommendations')
def generate_recommendations_route():
    """Generate gift recommendations - start scraping if needed"""
    user = get_session_user()
    if not user:
        return redirect('/signup')
    
    # FIXED: Get user_id from session FIRST
    user_id = session.get('user_id')
    if not user_id:
        return redirect('/signup')
    
    platforms = user.get('platforms', {})
    
    # Check for timed out scraping (status='scraping' for >3 minutes)
    for platform, data in platforms.items():
        if data.get('status') == 'scraping':
            scraping_started = data.get('scraping_started_at')
            if scraping_started:
                try:
                    start_time = datetime.fromisoformat(scraping_started)
                    elapsed = (datetime.now() - start_time).total_seconds()
                    
                    if elapsed > 180:  # 3 minutes
                        logger.warning(f"{platform} scraping timed out after {elapsed}s - marking as failed")
                        platforms[platform]['status'] = 'failed'
                        platforms[platform]['error'] = 'Scraping timed out - please try again'
                        save_user(user_id, {'platforms': platforms})
                except Exception as e:
                    logger.error(f"Error checking timeout for {platform}: {e}")
    
    # Reload user data after timeout check
    user = get_user(user_id)
    if not user:
        return redirect('/signup')
    
    platforms = user.get('platforms', {})
    
    if len(platforms) < 1:
        return redirect('/connect-platforms?error=need_platforms')
    
    # Check status and start scraping ONLY if ready
    for platform, data in platforms.items():
        if data.get('status') == 'ready':
            # IMMEDIATELY change status to prevent re-scraping
            platforms[platform]['status'] = 'scraping'
            platforms[platform]['scraping_started_at'] = datetime.now().isoformat()
            save_user(user_id, {'platforms': platforms})
            
            username = data['username']
            task_id = str(uuid.uuid4())
            
            if platform == 'instagram':
                def scrape_ig():
                    ig_data = scrape_instagram_profile(username, max_posts=50, task_id=task_id)
                    if ig_data:
                        user = get_user(user_id)
                        if user:
                            platforms = user.get('platforms', {})
                            platforms['instagram']['data'] = ig_data
                            platforms['instagram']['status'] = 'complete'
                            save_user(user_id, {'platforms': platforms})
                
                thread = threading.Thread(target=scrape_ig)
                thread.daemon = True
                thread.start()
            
            elif platform == 'tiktok':
                def scrape_tt():
                    tt_data = scrape_tiktok_profile(username, max_videos=50, task_id=task_id)
                    if tt_data:
                        user = get_user(user_id)
                        if user:
                            platforms = user.get('platforms', {})
                            platforms['tiktok']['data'] = tt_data
                            platforms['tiktok']['status'] = 'complete'
                            save_user(user_id, {'platforms': platforms})
                
                thread = threading.Thread(target=scrape_tt)
                thread.daemon = True
                thread.start()
            
            elif platform == 'pinterest':
                # Pinterest scraping (if using scraping method)
                if data.get('method') == 'scraping':
                    def scrape_pin():
                        try:
                            pin_data = scrape_pinterest_profile(username, max_pins=100, task_id=task_id)
                            if pin_data:
                                user = get_user(user_id)
                                if user:
                                    platforms = user.get('platforms', {})
                                    platforms['pinterest']['data'] = pin_data
                                    platforms['pinterest']['status'] = 'complete'
                                    platforms['pinterest']['connected_at'] = datetime.now().isoformat()
                                    save_user(user_id, {'platforms': platforms})
                                    logger.info(f"Pinterest scraping completed for @{username}")
                            else:
                                # Mark as failed if scraping returned None
                                logger.warning(f"Pinterest scraping returned None for @{username}")
                                user = get_user(user_id)
                                if user:
                                    platforms = user.get('platforms', {})
                                    platforms['pinterest']['status'] = 'failed'
                                    platforms['pinterest']['error'] = 'Failed to scrape Pinterest profile'
                                    save_user(user_id, {'platforms': platforms})
                        except Exception as e:
                            logger.error(f"Error scraping Pinterest for @{username}: {e}")
                            user = get_user(user_id)
                            if user:
                                platforms = user.get('platforms', {})
                                platforms['pinterest']['status'] = 'failed'
                                platforms['pinterest']['error'] = f'Scraping error: {str(e)}'
                                save_user(user_id, {'platforms': platforms})
                    
                    thread = threading.Thread(target=scrape_pin)
                    thread.daemon = True
                    thread.start()
                    logger.info(f"Started Pinterest scraping thread for @{username}")
    
    # Reload fresh data after saving
    user = get_user(user_id)
    if not user:
        return redirect('/signup')
    
    platforms = user.get('platforms', {})
    
    # Check if scraping is in progress
    scraping_in_progress = False
    for platform, data in platforms.items():
        if data.get('status') == 'scraping':
            scraping_in_progress = True
            break
    
    if scraping_in_progress:
        return render_template('scraping_in_progress.html',
                             platforms=list(platforms.keys()),
                             recipient_type=user.get('recipient_type', 'myself'))
    
    # Check if all have data
    quality = check_data_quality(platforms)
    
    if quality['quality'] == 'insufficient' and not request.args.get('force'):
        return render_template('low_data_warning.html', 
                             quality=quality,
                             ig_count=quality['platform_counts'].get('instagram', 0),
                             tt_count=quality['platform_counts'].get('tiktok', 0),
                             total_count=quality['total_posts'],
                             rec_count=quality['recommendation_count'])
    
    recipient_type = user.get('recipient_type', 'myself')
    return render_template('generating.html', 
                         platforms=list(platforms.keys()),
                         recipient_type=recipient_type)


@app.route('/review-profile')
def review_profile():
    """Build profile from scraped data and show validation UI so user can correct work vs hobby, prioritize, etc."""
    user = get_session_user()
    if not user:
        return redirect('/signup')
    platforms = user.get('platforms', {})
    if not platforms:
        return redirect('/connect-platforms?error=need_platforms')
    if not NEW_RECOMMENDATION_FLOW or not claude_client:
        return redirect('/generate-recommendations')
    recipient_type = user.get('recipient_type', 'myself')
    relationship = user.get('relationship', '')
    recipient_name = "Your recipient" if recipient_type == 'someone_else' else "You"
    # Build profile (one Claude call) so user can review before we search/curate
    logger.info("Building profile for review step...")
    profile = build_recipient_profile(platforms, recipient_type, relationship, claude_client)
    if not profile.get('interests'):
        return redirect('/connect-platforms?error=no_profile')
    # Prepare interests for template (description = evidence for display)
    interests = []
    for i in profile.get('interests', []):
        interests.append({
            'name': i.get('name', ''),
            'description': i.get('description') or i.get('evidence', ''),
            'is_work': i.get('is_work', False),
            'activity_type': i.get('activity_type', 'both'),
            'confidence': 0.8
        })
    # Ensure location_context has state for template (optional)
    loc = profile.get('location_context', {})
    if loc and 'state' not in loc:
        loc = dict(loc)
        loc['state'] = ''
    else:
        loc = loc or {}
    profile_for_template = dict(profile)
    profile_for_template['location_context'] = loc
    profile_for_template.setdefault('pet_details', '')
    profile_for_template.setdefault('family_context', '')
    generation_id = str(uuid.uuid4())
    session['review_generation_id'] = generation_id
    return render_template('profile_validation_fun.html',
                          recipient_name=recipient_name,
                          interests=interests,
                          profile=profile_for_template,
                          profile_json=json.dumps(profile_for_template),
                          generation_id=generation_id)


@app.route('/api/approve-profile', methods=['POST'])
def api_approve_profile():
    """Save user-approved profile and redirect to generating (search + curate use this profile)."""
    user = get_session_user()
    if not user:
        return jsonify({'success': False, 'error': 'Not logged in'}), 401
    data = request.get_json() or {}
    profile = data.get('profile')
    generation_id = data.get('generation_id')
    if not profile or not isinstance(profile, dict):
        return jsonify({'success': False, 'error': 'Invalid profile'}), 400
    if generation_id and session.get('review_generation_id') != generation_id:
        logger.warning("approve-profile generation_id mismatch")
    session['approved_profile'] = profile
    session.pop('review_generation_id', None)
    return jsonify({'success': True, 'redirect': '/generating'})


@app.route('/generating')
def generating_page():
    """Show generating screen (used after profile approval). Renders same template as /generate-recommendations flow."""
    user = get_session_user()
    if not user:
        return redirect('/signup')
    platforms = user.get('platforms', {})
    if not platforms:
        return redirect('/connect-platforms?error=need_platforms')
    recipient_type = user.get('recipient_type', 'myself')
    return render_template('generating.html',
                         platforms=list(platforms.keys()),
                         recipient_type=recipient_type)


@app.route('/api/generate-recommendations', methods=['POST'])
def api_generate_recommendations():
    """
    Generate recommendations with NEW ARCHITECTURE:
    1. Build deep recipient profile from social media
    2. Search for 30-50 real products using Google CSE
    3. Curate best 10 products + 2-3 experience gifts
    
    Falls back to old logic if new modules unavailable.
    """
    user = get_session_user()
    if not user:
        return jsonify({'success': False, 'error': 'Not logged in'}), 401
    
    if not ANTHROPIC_API_KEY or not claude_client:
        return jsonify({
            'success': False,
            'error': 'AI service not configured. Please contact support.'
        }), 503
    
    # NEW RECOMMENDATION FLOW (Profile → Search → Curate)
    if NEW_RECOMMENDATION_FLOW:
        try:
            logger.info("="*60)
            logger.info("USING NEW RECOMMENDATION ARCHITECTURE")
            logger.info("="*60)
            
            platforms = user.get('platforms', {})
            recipient_type = user.get('recipient_type', 'myself')
            relationship = user.get('relationship', '')
            user_id = session['user_id']
            
            # Check if SerpAPI is configured
            if not SERPAPI_API_KEY:
                logger.error("SerpAPI not configured")
                return jsonify({
                    'success': False,
                    'error': 'Product search is not configured. Please contact support.'
                }), 503
            
            # STEP 1: Build or use approved recipient profile
            if session.get('approved_profile'):
                profile = session.pop('approved_profile')
                logger.info("Using user-approved profile from review step")
            else:
                logger.info("STEP 1: Building deep recipient profile...")
                profile = build_recipient_profile(platforms, recipient_type, relationship, claude_client)
            
            if not profile.get('interests'):
                logger.warning("No interests extracted from profile - data quality issue")
                return jsonify({
                    'success': False,
                    'error': 'Unable to extract enough information from social media. Please connect more platforms or ensure profiles are public.'
                }), 422
            
            logger.info(f"Profile built: {len(profile.get('interests', []))} interests, location: {profile.get('location_context', {}).get('city_region')}")
            
            # STEP 2: Search for real products based on profile
            logger.info("STEP 2: Searching for real products...")
            products = search_real_products(
                profile,
                SERPAPI_API_KEY,
                target_count=40
            )
            
            if len(products) < 10:
                logger.warning(f"Only found {len(products)} products - may not be enough for good curation")
            
            logger.info(f"Found {len(products)} real products")
            
            # Apply smart filters BEFORE curation
            from smart_filters import apply_smart_filters, filter_workplace_experiences
            from relationship_rules import RelationshipRules
            
            # Filter out work-related and wrong activity type items
            products = apply_smart_filters(products, profile)
            logger.info(f"After smart filters: {len(products)} products")
            
            # Filter by relationship appropriateness
            if recipient_type == 'someone_else' and relationship:
                products = RelationshipRules.filter_by_relationship(products, relationship)
                logger.info(f"After relationship filter ({relationship}): {len(products)} products")
            
            # STEP 3: Curate best gifts from real products + generate experiences
            logger.info("STEP 3: Curating gifts...")
            curated = curate_gifts(profile, products, recipient_type, relationship, claude_client, rec_count=10)
            
            product_gifts = curated.get('product_gifts', [])
            experience_gifts = curated.get('experience_gifts', [])
            # Remove experience gifts at recipient's workplace (e.g. behind-the-scenes IMS when they work at IMS)
            experience_gifts = filter_workplace_experiences(experience_gifts, profile)
            logger.info(f"After workplace-experience filter: {len(experience_gifts)} experiences")
            
            if not product_gifts and not experience_gifts:
                logger.error("Curation returned no gifts")
                return jsonify({
                    'success': False,
                    'error': 'Unable to generate recommendations. Please try again.'
                }), 500
            
            logger.info(f"Curated {len(product_gifts)} products + {len(experience_gifts)} experiences")
            
            # Build product URL -> image map for backfilling thumbnails
            product_url_to_image = {p.get('link', ''): (p.get('image') or p.get('thumbnail', '')) for p in products if p.get('link')}
            
            # Combine and format recommendations
            all_recommendations = []
            
            # Add product gifts (backfill image from search results when curator didn't return one)
            for gift in product_gifts:
                product_url = gift.get('product_url', '')
                image_url = gift.get('image_url', '') or product_url_to_image.get(product_url, '')
                all_recommendations.append({
                    'name': gift.get('name', 'Unknown Product'),
                    'description': gift.get('description', ''),
                    'why_perfect': gift.get('why_perfect', ''),
                    'price_range': gift.get('price', 'Price unknown'),
                    'where_to_buy': gift.get('where_to_buy', 'Online'),
                    'product_url': product_url,
                    'purchase_link': product_url,  # Compatibility
                    'image_url': image_url,
                    'gift_type': 'physical',
                    'confidence_level': gift.get('confidence_level', 'safe_bet'),
                    'interest_match': gift.get('interest_match', ''),
                    'is_direct_link': True,  # These are from search, so they're real
                    'link_source': 'serpapi_search'
                })
            
            # Add experience gifts
            for exp in experience_gifts:
                materials_list = exp.get('materials_needed', [])
                materials_summary = ""
                if materials_list:
                    materials_items = [f"{m.get('item', 'Item')} ({m.get('estimated_price', '$XX')})" for m in materials_list[:3]]
                    materials_summary = f"Materials needed: {', '.join(materials_items)}"
                how_special = exp.get('how_to_make_it_special', '')
                parts = [exp.get('description', ''), exp.get('how_to_execute', ''), how_special, materials_summary]
                full_description = '\n\n'.join(p for p in parts if p).strip()
                location_info = ""
                if exp.get('location_specific'):
                    location_info = f" | {exp.get('location_details', 'Location-based')}"
                all_recommendations.append({
                    'name': exp.get('name', 'Experience Gift'),
                    'description': full_description,
                    'why_perfect': exp.get('why_perfect', ''),
                    'price_range': 'Variable',
                    'where_to_buy': f"Experience{location_info}",
                    'product_url': materials_list[0].get('product_url', '') if materials_list else '',
                    'purchase_link': materials_list[0].get('product_url', '') if materials_list else '',
                    'image_url': '',  # Experiences don't have product images
                    'gift_type': 'experience',
                    'confidence_level': exp.get('confidence_level', 'adventurous'),
                    'materials_needed': materials_list,
                    'location_specific': exp.get('location_specific', False),
                    'how_to_make_it_special': how_special
                })
            
            logger.info(f"Total recommendations: {len(all_recommendations)}")
            
            # Backfill thumbnails for recs missing image_url (physical gifts only)
            if IMAGE_FETCHING_AVAILABLE:
                try:
                    all_recommendations = process_recommendation_images(all_recommendations)
                    with_images = sum(1 for r in all_recommendations if r.get('image_url') and 'placeholder' not in (r.get('image_url') or '').lower())
                    logger.info(f"Images: {with_images}/{len(all_recommendations)} with thumbnails")
                except Exception as img_err:
                    logger.warning(f"Image backfill failed (continuing): {img_err}")
            
            # Calculate data quality for compatibility
            quality = check_data_quality(platforms)
            
            # Save recommendations
            save_user(user_id, {
                'recommendations': all_recommendations,
                'data_quality': quality,
                'last_generated': datetime.now().isoformat(),
                'recipient_profile': profile  # Save profile for future use
            })
            
            return jsonify({
                'success': True,
                'recommendations': all_recommendations,
                'data_quality': quality
            })
            
        except Exception as e:
            logger.error(f"Error in new recommendation flow: {e}", exc_info=True)
            logger.warning("Falling back to legacy recommendation flow")
            # Fall through to legacy flow below
    
    # LEGACY RECOMMENDATION FLOW (fallback)
    logger.warning("New recommendation flow not available - using simplified fallback")
    try:
        platforms = user.get('platforms', {})
        recipient_type = user.get('recipient_type', 'myself')
        relationship = user.get('relationship', '')
        
        # Simplified fallback: Return error asking to configure new system
        return jsonify({
            'success': False,
            'error': 'New recommendation system not fully configured. Please ensure profile_analyzer.py, product_searcher.py, and gift_curator.py are deployed.'
        }), 503
        
    except Exception as e:
        logger.error(f"Recommendation generation error: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'An unexpected error occurred. Please try again or contact support.'
        }), 500

@app.route('/recommendations')
def view_recommendations():
    """Display recommendations with fix link buttons"""
    user = get_session_user()
    if not user:
        return redirect('/signup')
    
    recommendations = user.get('recommendations', [])
    
    if not recommendations:
        return redirect('/connect-platforms?error=no_recommendations')
    
    data_quality = user.get('data_quality', {})
    connected_count = len(user.get('platforms', {}))
    
    # Mark favorites
    favorites = user.get('favorites', [])
    
    return render_template('recommendations.html', 
                         recommendations=recommendations,
                         data_quality=data_quality,
                         connected_count=connected_count,
                         user=user,
                         favorites=favorites)

@app.route('/api/favorite/<int:rec_index>', methods=['POST'])
def toggle_favorite(rec_index):
    """Add or remove favorite"""
    user = get_session_user()
    if not user:
        return jsonify({'success': False, 'error': 'Not logged in'}), 401
    
    if not FAVORITES_AVAILABLE:
        return jsonify({'success': False, 'error': 'Favorites not available'}), 503
    
    user_id = session['user_id']
    recommendations = user.get('recommendations', [])
    
    if rec_index < 0 or rec_index >= len(recommendations):
        return jsonify({'success': False, 'error': 'Invalid recommendation index'}), 400
    
    favorites = user.get('favorites', [])
    
    if rec_index in favorites:
        # Remove favorite
        favorites.remove(rec_index)
        action = 'removed'
    else:
        # Add favorite
        favorites.append(rec_index)
        action = 'added'
    
    user['favorites'] = favorites
    save_user(user_id, {'favorites': favorites})
    
    return jsonify({'success': True, 'action': action, 'favorited': rec_index in favorites})

@app.route('/api/share', methods=['POST'])
def create_share():
    """Create shareable link"""
    user = get_session_user()
    if not user:
        return jsonify({'success': False, 'error': 'Not logged in'}), 401
    
    if not FAVORITES_AVAILABLE:
        return jsonify({'success': False, 'error': 'Sharing not available'}), 503
    
    user_id = session['user_id']
    recommendations = user.get('recommendations', [])
    
    if not recommendations:
        return jsonify({'success': False, 'error': 'No recommendations to share'}), 400
    
    share_id = generate_share_id(recommendations, user_id)
    save_share(share_id, recommendations, user_id)
    
    share_url = request.url_root.rstrip('/') + f'/share/{share_id}'
    
    return jsonify({'success': True, 'share_url': share_url, 'share_id': share_id})

@app.route('/share/<share_id>')
def view_shared_recommendations(share_id):
    """View shared recommendations"""
    share_data = get_share(share_id)
    
    if not share_data:
        return render_template('error.html', 
                             error="This share link has expired or doesn't exist.",
                             error_code=404)
    
    recommendations = share_data['recommendations']
    
    return render_template('shared_recommendations.html',
                         recommendations=recommendations,
                         share_id=share_id)

@app.route('/favorites')
def view_favorites():
    """View favorited recommendations"""
    user = get_session_user()
    if not user:
        return redirect('/signup')
    
    if not FAVORITES_AVAILABLE:
        return redirect('/recommendations')
    
    recommendations = user.get('recommendations', [])
    favorites = user.get('favorites', [])
    
    favorited_recs = [recommendations[i] for i in favorites if i < len(recommendations)]
    
    if not favorited_recs:
        return render_template('recommendations.html',
                             recommendations=[],
                             data_quality={},
                             connected_count=len(user.get('platforms', {})),
                             user=user,
                             favorites=favorites,
                             message="No favorites yet. Click the ❤️ icon on recommendations to save them!")
    
    return render_template('recommendations.html',
                         recommendations=favorited_recs,
                         data_quality={},
                         connected_count=len(user.get('platforms', {})),
                         user=user,
                         favorites=favorites,
                         is_favorites_page=True)

@app.route('/api/check-scraping-status')
def check_scraping_status():
    """Check if scraping is complete (for AJAX polling, no page reload)"""
    user = get_session_user()
    if not user:
        return jsonify({'complete': False, 'error': 'Not logged in'}), 401
    
    platforms = user.get('platforms', {})
    
    if not platforms:
        return jsonify({'complete': False, 'error': 'No platforms connected'})
    
    # Check status of each platform
    scraping_in_progress = False
    completed_count = 0
    total_platforms = len(platforms)
    platform_statuses = {}
    
    for platform, data in platforms.items():
        status = data.get('status', '')
        has_data = bool(data.get('data'))
        platform_statuses[platform] = {'status': status, 'has_data': has_data}
        
        # Still scraping
        if status == 'scraping':
            scraping_in_progress = True
            logger.info(f"Platform {platform} still scraping (status: {status})")
        
        # Has completed data
        elif status == 'complete' and has_data:
            completed_count += 1
            logger.debug(f"Platform {platform} complete with data")
        
        # Ready but not started (shouldn't happen, but handle it)
        elif status == 'ready':
            logger.warning(f"Platform {platform} is ready but scraping hasn't started")
            scraping_in_progress = True  # Treat as in progress
    
    logger.info(f"Scraping status check: {completed_count}/{total_platforms} complete, in_progress={scraping_in_progress}")
    
    # If still scraping, return in progress
    if scraping_in_progress:
        return jsonify({
            'complete': False, 
            'in_progress': True,
            'completed': completed_count,
            'total': total_platforms,
            'statuses': platform_statuses
        })
    
    # If no data yet, might still be processing
    if completed_count == 0:
        logger.warning("No platforms have completed scraping yet")
        return jsonify({
            'complete': False, 
            'in_progress': True, 
            'message': 'Processing data...',
            'statuses': platform_statuses
        })
    
    # CRITICAL: Check if ALL platforms are complete (not just some)
    if completed_count < total_platforms:
        logger.info(f"Still waiting for {total_platforms - completed_count} platform(s) to complete")
        return jsonify({
            'complete': False,
            'in_progress': True,
            'completed': completed_count,
            'total': total_platforms,
            'statuses': platform_statuses
        })
    
    # Check if we have sufficient data
    quality = check_data_quality(platforms)
    
    if quality['quality'] == 'insufficient':
        logger.warning(f"Insufficient data quality: {quality}")
        return jsonify({
            'complete': False, 
            'error': 'Insufficient data',
            'quality': quality,
            'statuses': platform_statuses
        })
    
    # All done!
    logger.info(f"All scraping complete! Redirecting to recommendations.")
    return jsonify({
        'complete': True,
        'platforms': list(platforms.keys()),
        'quality': quality,
        'statuses': platform_statuses
    })

@app.route('/usage')
def usage_dashboard():
    """API usage dashboard - shows daily/monthly usage and remaining capacity"""
    user = get_session_user()
    if not user:
        return redirect('/signup')
    
    if not USAGE_TRACKING_AVAILABLE:
        return render_template('usage.html', 
                             error="Usage tracking not available",
                             summary=None)
    
    try:
        summary = get_usage_summary()
        return render_template('usage.html', summary=summary, error=None)
    except Exception as e:
        logger.error(f"Error loading usage dashboard: {e}")
        return render_template('usage.html', 
                             error=f"Error loading usage: {str(e)}",
                             summary=None)

@app.route('/api/usage')
def api_usage():
    """API endpoint for usage data (JSON)"""
    if not USAGE_TRACKING_AVAILABLE:
        return jsonify({'error': 'Usage tracking not available'}), 503
    
    try:
        summary = get_usage_summary()
        return jsonify(summary)
    except Exception as e:
        logger.error(f"Error getting usage data: {e}")
        return jsonify({'error': str(e)}), 500

# ============================================================================
# OAUTH ROUTES
# ============================================================================

@app.route('/connect/pinterest', methods=['POST'])
def connect_pinterest():
    """Connect Pinterest via scraping (alternative to OAuth)"""
    user = get_session_user()
    if not user:
        return redirect('/signup')
    
    username_input = request.form.get('username', '').strip()
    
    # Pinterest usernames can have dots, hyphens, underscores
    # Remove @ if present, but keep dots and hyphens
    username = username_input.replace('@', '').replace(' ', '')
    
    # Basic validation - Pinterest usernames are usually 3-30 chars, alphanumeric + dots/hyphens/underscores
    if not username:
        return redirect('/connect-platforms?error=pinterest_no_username')
    
    if len(username) < 3:
        return redirect('/connect-platforms?error=pinterest_username_too_short')
    
    # Clean but preserve valid Pinterest characters
    username = re.sub(r'[^a-zA-Z0-9_.-]', '', username)
    
    if not username:
        return redirect('/connect-platforms?error=pinterest_invalid_username')
    
    user_id = session['user_id']
    
    # Save Pinterest username (will scrape on generate)
    platforms = user.get('platforms', {})
    platforms['pinterest'] = {
        'username': username,
        'status': 'ready',
        'method': 'scraping'  # Scraping method instead of OAuth
    }
    save_user(user_id, {'platforms': platforms})
    logger.info(f"User {user_id} connected Pinterest via scraping: {username}")
    
    return redirect('/connect-platforms?success=pinterest_ready')

@app.route('/oauth/pinterest')
def pinterest_oauth():
    """Initiate Pinterest OAuth"""
    user = get_session_user()
    if not user:
        return redirect('/signup')
    
    if not OAUTH_INTEGRATIONS_AVAILABLE:
        return redirect('/connect-platforms?error=oauth_not_available')
    
    auth_url = get_pinterest_authorization_url()
    
    if not auth_url:
        return redirect('/connect-platforms?error=pinterest_not_configured')
    
    # Store state
    session['pinterest_oauth_state'] = 'pinterest_auth'
    
    return redirect(auth_url)

@app.route('/oauth/pinterest/callback')
def pinterest_oauth_callback():
    """Handle Pinterest OAuth callback"""
    user = get_session_user()
    if not user:
        return redirect('/signup')
    
    code = request.args.get('code')
    state = request.args.get('state')
    
    # Verify state
    if state != session.get('pinterest_oauth_state'):
        return redirect('/connect-platforms?error=pinterest_invalid_state')
    
    if not code:
        return redirect('/connect-platforms?error=pinterest_no_code')
    
    # Exchange code for token
    token_data = exchange_pinterest_code(code)
    
    if not token_data:
        return redirect('/connect-platforms?error=pinterest_token_failed')
    
    user_id = session['user_id']
    
    # Fetch Pinterest data
    pinterest_data = oauth_fetch_pinterest_data(token_data['access_token'])
    
    if pinterest_data:
        platforms = user.get('platforms', {})
        platforms['pinterest'] = {
            'access_token': token_data['access_token'],
            'refresh_token': token_data.get('refresh_token'),
            'data': pinterest_data,
            'status': 'complete',
            'method': 'oauth',
            'connected_at': datetime.now().isoformat()
        }
        
        save_user(user_id, {'platforms': platforms})
        logger.info(f"User {user_id} connected Pinterest OAuth")
        
        return redirect('/connect-platforms?success=pinterest_connected')
    else:
        return redirect('/connect-platforms?error=pinterest_fetch_failed')

@app.route('/oauth/spotify')
def spotify_oauth():
    """Initiate Spotify OAuth"""
    user = get_session_user()
    if not user:
        return redirect('/signup')
    
    if not OAUTH_INTEGRATIONS_AVAILABLE:
        return redirect('/connect-platforms?error=oauth_not_available')
    
    auth_url = get_spotify_authorization_url()
    
    if not auth_url:
        return redirect('/connect-platforms?error=spotify_not_configured')
    
    session['spotify_oauth_state'] = 'spotify_auth'
    
    return redirect(auth_url)

@app.route('/oauth/spotify/callback')
def spotify_oauth_callback():
    """Handle Spotify OAuth callback"""
    user = get_session_user()
    if not user:
        return redirect('/signup')
    
    code = request.args.get('code')
    state = request.args.get('state')
    
    if state != session.get('spotify_oauth_state'):
        return redirect('/connect-platforms?error=spotify_invalid_state')
    
    if not code:
        return redirect('/connect-platforms?error=spotify_no_code')
    
    token_data = exchange_spotify_code(code)
    
    if not token_data:
        return redirect('/connect-platforms?error=spotify_token_failed')
    
    user_id = session['user_id']
    
    # Fetch Spotify data
    spotify_data = oauth_fetch_spotify_data(token_data['access_token'])
    
    if spotify_data:
        platforms = user.get('platforms', {})
        platforms['spotify'] = {
            'access_token': token_data['access_token'],
            'refresh_token': token_data.get('refresh_token'),
            'data': spotify_data,
            'status': 'complete',
            'method': 'oauth',
            'connected_at': datetime.now().isoformat()
        }
        
        save_user(user_id, {'platforms': platforms})
        logger.info(f"User {user_id} connected Spotify OAuth")
        
        return redirect('/connect-platforms?success=spotify_connected')
    else:
        return redirect('/connect-platforms?error=spotify_fetch_failed')

@app.route('/oauth/google')
def google_oauth():
    """Initiate Google OAuth (for YouTube)"""
    user = get_session_user()
    if not user:
        return redirect('/signup')
    
    if not OAUTH_INTEGRATIONS_AVAILABLE:
        return redirect('/connect-platforms?error=oauth_not_available')
    
    auth_url = get_google_authorization_url()
    
    if not auth_url:
        return redirect('/connect-platforms?error=google_not_configured')
    
    session['google_oauth_state'] = 'google_auth'
    
    return redirect(auth_url)

@app.route('/oauth/google/callback')
def google_oauth_callback():
    """Handle Google OAuth callback"""
    user = get_session_user()
    if not user:
        return redirect('/signup')
    
    code = request.args.get('code')
    state = request.args.get('state')
    
    if state != session.get('google_oauth_state'):
        return redirect('/connect-platforms?error=google_invalid_state')
    
    if not code:
        return redirect('/connect-platforms?error=google_no_code')
    
    token_data = exchange_google_code(code)
    
    if not token_data:
        return redirect('/connect-platforms?error=google_token_failed')
    
    user_id = session['user_id']
    
    # Fetch YouTube subscriptions
    youtube_data = fetch_youtube_subscriptions(access_token=token_data['access_token'])
    
    if youtube_data:
        platforms = user.get('platforms', {})
        platforms['youtube'] = {
            'access_token': token_data['access_token'],
            'refresh_token': token_data.get('refresh_token'),
            'data': youtube_data,
            'status': 'complete',
            'method': 'oauth',
            'connected_at': datetime.now().isoformat()
        }
        
        save_user(user_id, {'platforms': platforms})
        logger.info(f"User {user_id} connected YouTube OAuth")
        
        return redirect('/connect-platforms?success=youtube_connected')
    else:
        return redirect('/connect-platforms?error=youtube_fetch_failed')

@app.route('/logout')
def logout():
    """Logout user"""
    session.clear()
    return redirect('/')


# ========================================
# VALENTINE'S DAY ROUTES
# ========================================

@app.route('/api/generate-share-image', methods=['POST'])
def api_generate_share_image():
    """Generate shareable social media image"""
    if not VALENTINES_FEATURES_AVAILABLE:
        return jsonify({'error': 'Feature not available'}), 503
    
    user = get_session_user()
    if not user:
        return jsonify({'error': 'Not logged in'}), 401
    
    # Get user's recommendations count
    recommendations = user.get('recommendations', [])
    rec_count = len(recommendations)
    
    user_name = user.get('name', '').split()[0] if user.get('name') else 'Friend'
    relationship = user.get('last_generation_relationship', 'someone special')
    
    # Generate image
    try:
        img_bytes = generate_share_image(
            user_name=user_name,
            rec_count=rec_count,
            relationship=relationship
        )
        
        return send_file(
            img_bytes,
            mimetype='image/png',
            as_attachment=True,
            download_name='my-valentine-gifts.png'
        )
    except Exception as e:
        logger.error(f"Error generating share image: {e}")
        return jsonify({'error': 'Failed to generate image'}), 500


@app.route('/api/referral-stats')
def api_referral_stats():
    """Get user's referral statistics"""
    if not VALENTINES_FEATURES_AVAILABLE:
        return jsonify({'error': 'Feature not available'}), 503
    
    user = get_session_user()
    if not user:
        return jsonify({'error': 'Not logged in'}), 401
    
    stats = get_referral_stats(user)
    
    # Add Valentine's Day bonus info
    vday_bonus = get_valentines_day_bonus()
    stats['valentines_bonus'] = vday_bonus
    
    return jsonify(stats)


# Error handlers for better crash reporting
@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}", exc_info=True)
    return render_template('error.html', 
                         error="An internal error occurred. Please try again.",
                         error_code=500), 500

@app.errorhandler(404)
def not_found(error):
    return render_template('error.html', 
                         error="Page not found.",
                         error_code=404), 404

@app.errorhandler(Exception)
def handle_exception(e):
    logger.error(f"Unhandled exception: {e}", exc_info=True)
    return render_template('error.html', 
                         error=f"An error occurred: {str(e)}",
                         error_code=500), 500

if __name__ == '__main__':
    # Railway sets PORT env var automatically
    port = int(os.environ.get('PORT', 5000))
    # Don't use debug=True in production (Railway)
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug_mode)
