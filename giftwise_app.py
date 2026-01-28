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
from collections import Counter, OrderedDict

# Import enhanced recommendation engine
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
    logger.warning("Enhanced recommendation engine not available - using basic prompts")

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
    logger.warning("Wishlist integrations not available")

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
    logger.warning("Usage tracking not available")

# OAuth libraries
from requests_oauthlib import OAuth2Session
import requests

# Database (using simple JSON for MVP - upgrade to PostgreSQL later)
import shelve

load_dotenv()

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

# Spotify (keeping for future)
SPOTIFY_CLIENT_ID = os.environ.get('SPOTIFY_CLIENT_ID', '')
SPOTIFY_CLIENT_SECRET = os.environ.get('SPOTIFY_CLIENT_SECRET', '')

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
    # Only allow alphanumeric, underscore, dot
    username = re.sub(r'[^a-zA-Z0-9_.]', '', username)
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
    Check if Instagram account exists and is public
    Returns: dict with valid, private, exists, message
    """
    try:
        url = f'https://www.instagram.com/{username}/'
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
        
        html = response.text
        
        # Check for privacy indicators
        # Instagram embeds JSON-LD data with is_private field
        is_private = '"is_private":true' in html or '"is_private": true' in html
        
        if is_private:
            return {
                'valid': False,
                'private': True,
                'exists': True,
                'message': '✗ Private account - we can only analyze public profiles',
                'help': 'Ask them to make their account public temporarily, or try a different platform',
                'icon': '🔒'
            }
        
        # Public account found
        return {
            'valid': True,
            'private': False,
            'exists': True,
            'message': '✓ Public profile found',
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

@app.route('/connect-platforms')
def connect_platforms():
    """Platform connection page"""
    user = get_session_user()
    if not user:
        return redirect('/signup')
    
    # Check which platforms user's tier allows
    tier = get_user_tier(user)
    tier_config = SUBSCRIPTION_TIERS[tier]
    allowed_platforms = tier_config['platforms']
    
    platform_access = {
        'instagram': 'instagram' in allowed_platforms,
        'tiktok': 'tiktok' in allowed_platforms,
        'pinterest': 'pinterest' in allowed_platforms
    }
    
    return render_template('connect_platforms.html', 
                         user=user,
                         platforms=user.get('platforms', {}),
                         recipient_type=user.get('recipient_type', 'myself'),
                         platform_access=platform_access,
                         user_tier=tier,
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
        return redirect('/signup')
    
    username = sanitize_username(request.form.get('username', ''))
    
    if not username:
        return redirect('/connect-platforms?error=instagram_no_username')
    
    user_id = session['user_id']
    
    # Just save the username - don't scrape yet
    platforms = user.get('platforms', {})
    platforms['instagram'] = {
        'username': username,
        'status': 'ready',  # Ready to scrape
        'method': 'scraping'
    }
    save_user(user_id, {'platforms': platforms})
    logger.info(f"User {user_id} connected Instagram: @{username}")
    
    return redirect('/connect-platforms?success=instagram_ready')

@app.route('/connect/tiktok', methods=['POST'])
def connect_tiktok():
    """Save TikTok username (scraping happens on generate)"""
    user = get_session_user()
    if not user:
        return redirect('/signup')
    
    username = sanitize_username(request.form.get('username', ''))
    
    if not username:
        return redirect('/connect-platforms?error=tiktok_no_username')
    
    user_id = session['user_id']
    
    # Just save the username - don't scrape yet
    platforms = user.get('platforms', {})
    platforms['tiktok'] = {
        'username': username,
        'status': 'ready',  # Ready to scrape
        'method': 'scraping'
    }
    save_user(user_id, {'platforms': platforms})
    logger.info(f"User {user_id} connected TikTok: @{username}")
    
    return redirect('/connect-platforms?success=tiktok_ready')

@app.route('/connect/etsy', methods=['POST'])
def connect_etsy():
    """Connect Etsy wishlist via OAuth"""
    user = get_session_user()
    if not user:
        return redirect('/signup')
    
    # Etsy OAuth flow (simplified - would need full OAuth implementation)
    # For now, save that user wants to connect Etsy
    user_id = session['user_id']
    wishlists = user.get('wishlists', [])
    
    # Check if already connected
    etsy_wishlist = next((w for w in wishlists if w.get('platform') == 'etsy'), None)
    
    if not etsy_wishlist:
        # Initiate Etsy OAuth (would redirect to Etsy)
        # For MVP: Just save intent, implement OAuth later
        wishlists.append({
            'platform': 'etsy',
            'status': 'pending',
            'connected_at': datetime.now().isoformat()
        })
        save_user(user_id, {'wishlists': wishlists})
        logger.info(f"User {user_id} initiated Etsy connection")
    
    return redirect('/connect-platforms?success=etsy_pending')

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
    """Connect YouTube (channel subscriptions indicate interests)"""
    user = get_session_user()
    if not user:
        return redirect('/signup')
    
    channel_id_or_username = sanitize_username(request.form.get('channel_id', ''))
    
    if not channel_id_or_username:
        return redirect('/connect-platforms?error=youtube_no_channel')
    
    user_id = session['user_id']
    
    # Save YouTube channel (will analyze subscriptions)
    platforms = user.get('platforms', {})
    platforms['youtube'] = {
        'channel_id': channel_id_or_username,
        'status': 'ready',
        'method': 'api'  # YouTube Data API
    }
    save_user(user_id, {'platforms': platforms})
    logger.info(f"User {user_id} connected YouTube: {channel_id_or_username}")
    
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
    if 'instagram' in platforms and platforms['instagram'].get('status') == 'ready':
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
    
    if 'tiktok' in platforms and platforms['tiktok'].get('status') == 'ready':
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
    
    # Redirect to multi-platform progress page
    return redirect(f"/scraping-progress?tasks={','.join([f'{k}:{v}' for k, v in scrape_tasks.items()])}")

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

@app.route('/api/generate-recommendations', methods=['POST'])
def api_generate_recommendations():
    """
    Generate recommendations with:
    - Dynamic rec count based on data quality
    - Collectible series intelligence
    - Relationship-specific prompts
    - FIXED: Comprehensive error handling
    """
    user = get_session_user()
    if not user:
        return jsonify({'success': False, 'error': 'Not logged in'}), 401
    
    if not ANTHROPIC_API_KEY or not claude_client:
        return jsonify({
            'success': False,
            'error': 'AI service not configured. Please contact support.'
        }), 503
    
    try:
        platforms = user.get('platforms', {})
        recipient_type = user.get('recipient_type', 'myself')
        relationship = user.get('relationship', '')
        
        # Check tier limits
        tier = get_user_tier(user)
        tier_config = SUBSCRIPTION_TIERS[tier]
        
        # Check data quality
        quality = check_data_quality(platforms)
        rec_count = min(quality['recommendation_count'], tier_config['recommendations_per_profile'])
        
        # ENHANCED: Extract ALL possible signals from platforms
        signals = {}
        wishlist_data = {}
        avoid_items = []
        all_extracted_signals = {}
        
        if ENHANCED_ENGINE_AVAILABLE:
            try:
                # Extract deep signals (engagement, aspirational, brands)
                signals = extract_deep_signals(platforms)
                
                # ENHANCED: Extract ALL signals from each platform (comprehensive mining)
                try:
                    all_extracted_signals = combine_all_signals(platforms)
                    # Merge combined signals into main signals dict
                    if all_extracted_signals.get('combined'):
                        combined = all_extracted_signals['combined']
                        # Merge hashtags, brands, activities, etc.
                        if combined.get('all_hashtags'):
                            signals.setdefault('high_engagement_topics', {}).update(combined['all_hashtags'])
                        if combined.get('all_brands'):
                            signals.setdefault('brand_preferences', {}).update(combined['all_brands'])
                        if combined.get('aspirational_interests'):
                            signals.setdefault('aspirational_interests', []).extend(combined['aspirational_interests'])
                        if combined.get('current_interests'):
                            signals.setdefault('current_interests', []).extend(combined['current_interests'])
                        if combined.get('price_preferences'):
                            signals['price_preferences'] = combined['price_preferences']
                    
                    logger.info(f"Extracted comprehensive signals: {len(all_extracted_signals)} platform signals")
                except Exception as e:
                    logger.warning(f"Enhanced data extraction not available: {e}")
                
                # Get wishlist data (if user has connected)
                user_wishlists = user.get('wishlists', [])
                if user_wishlists:
                    wishlist_data = integrate_wishlist_data(user_wishlists, platforms)
                    duplicates = detect_duplicates(platforms, user_wishlists)
                    avoid_items = duplicates.get('avoid', [])
                    logger.info(f"Found {len(avoid_items)} items to avoid from wishlists")
            except Exception as e:
                logger.error(f"Error in enhanced signal extraction: {e}", exc_info=True)
                signals = {}
                wishlist_data = {}
                all_extracted_signals = {}
        
        # Build platform insights (ENHANCED with comprehensive data extraction)
        platform_insights = []
        
        # Use enhanced extracted signals if available, otherwise fallback to basic
        use_enhanced = all_extracted_signals and any(all_extracted_signals.values())
        
        if use_enhanced and all_extracted_signals.get('instagram'):
            # Enhanced Instagram insights
            ig_signals = all_extracted_signals['instagram']
            ig_data = platforms['instagram'].get('data', {})
            posts = ig_data.get('posts', [])
            
            high_engagement_count = len(ig_signals.get('high_engagement_content', []))
            top_hashtags = list(ig_signals.get('hashtags', {}).keys())[:15]
            top_brands = list(ig_signals.get('brand_mentions', {}).keys())[:10]
            top_activities = list(ig_signals.get('activity_types', {}).keys())[:10]
            aesthetics = list(ig_signals.get('aesthetic_keywords', {}).keys())[:10]
            
            platform_insights.append(f"""
INSTAGRAM DATA ({len(posts)} posts analyzed):
- Username: @{ig_data.get('username', 'unknown')}
- High Engagement Posts: {high_engagement_count} posts with 50+ engagement (strongest interest signals)
- Top Hashtags: {', '.join(top_hashtags)}
- Brand Preferences: {', '.join(top_brands)}
- Activity Types: {', '.join(top_activities)}
- Aesthetic Style: {', '.join(aesthetics)}
- Recent Interests: {', '.join(ig_signals.get('recent_interests', [])[:10])}
- Locations Mentioned: {', '.join(list(ig_signals.get('locations', {}).keys())[:5])}
""")
        elif 'instagram' in platforms:
            # Basic Instagram insights (fallback)
            ig_data = platforms['instagram'].get('data', {})
            if ig_data:
                posts = ig_data.get('posts', [])
                captions = [p['caption'][:200] for p in posts if p.get('caption')]
                hashtags_all = []
                for p in posts:
                    hashtags_all.extend(p.get('hashtags', []))
                top_hashtags = Counter(hashtags_all).most_common(15)
                
                avg_likes = sum(p.get('likes', 0) for p in posts) / len(posts) if posts else 0
                
                platform_insights.append(f"""
INSTAGRAM DATA ({len(posts)} posts analyzed):
- Username: @{ig_data.get('username', 'unknown')}
- Recent Post Themes: {'; '.join(captions[:15])}
- Top Hashtags: {', '.join([tag[0] for tag in top_hashtags])}
- Engagement: Average {avg_likes:.0f} likes per post
""")
        
        # TikTok data (enhanced if available, otherwise basic)
        if use_enhanced and all_extracted_signals.get('tiktok'):
            tt_signals = all_extracted_signals['tiktok']
            tt_data = platforms['tiktok'].get('data', {})
            
            repost_count = len(tt_signals.get('aspirational_content', []))
            top_hashtags = list(tt_signals.get('hashtags', {}).keys())[:10]
            music_trends = list(tt_signals.get('music_trends', {}).keys())[:5]
            creator_styles = [c['creator'] for c in tt_signals.get('creator_styles', [])[:5]]
            
            platform_insights.append(f"""
TIKTOK DATA ({tt_data.get('total_videos', 0)} videos analyzed):
- Username: @{tt_data.get('username', 'unknown')}
- Aspirational Content: {repost_count} reposts analyzed (what they WANT but don't have)
- Top Hashtags: {', '.join(top_hashtags)}
- Music Trends: {', '.join(music_trends)}
- Creator Styles: {', '.join(creator_styles)}
- Trending Topics: {', '.join(tt_signals.get('trending_topics', [])[:10])}
- CRITICAL: Reposts reveal ASPIRATIONAL interests - prioritize these for gifts
""")
        elif 'tiktok' in platforms:
            # TikTok data (basic fallback if enhanced not available)
            tt_data = platforms['tiktok'].get('data', {})
            if tt_data:
                videos = tt_data.get('videos', [])
                descriptions = [v['description'][:150] for v in videos[:20] if v.get('description')]
                favorite_creators = tt_data.get('favorite_creators', [])
                repost_patterns = tt_data.get('repost_patterns', {})
                top_hashtags = tt_data.get('top_hashtags', {})
                top_music = tt_data.get('top_music', {})
                
                creator_insights = ""
                if favorite_creators:
                    creator_list = [f"@{creator[0]} ({creator[1]} reposts)" for creator in favorite_creators[:5]]
                    creator_insights = f"\n- Frequently Reposts From: {', '.join(creator_list)}"
                    creator_insights += f"\n- CRITICAL: These creators represent their aspirations"
                
                music_insights = ""
                if top_music:
                    music_list = list(top_music.keys())[:5]
                    music_insights = f"\n- Popular Sounds: {', '.join(music_list)}"
                
                platform_insights.append(f"""
TIKTOK DATA ({tt_data.get('total_videos', 0)} videos analyzed):
- Username: @{tt_data.get('username', 'unknown')}
- Original Content Themes: {'; '.join(descriptions[:15])}
- Repost Behavior: {repost_patterns.get('total_reposts', 0)} reposts ({repost_patterns.get('repost_percentage', 0):.1f}%)
{creator_insights}
{music_insights}
- Top Hashtags: {', '.join(list(top_hashtags.keys())[:10])}
""")
        
        # Pinterest data (enhanced if available)
        if use_enhanced and all_extracted_signals.get('pinterest'):
            pin_signals = all_extracted_signals['pinterest']
            boards = platforms['pinterest'].get('boards', [])
            
            board_themes = list(pin_signals.get('board_themes', {}).keys())[:10]
            pin_keywords = list(pin_signals.get('pin_keywords', {}).keys())[:20]
            specific_wants = pin_signals.get('specific_wants', [])[:10]
            price_prefs = pin_signals.get('price_preferences', {})
            
            price_info = ""
            if price_prefs:
                price_info = f"\n- Price Preferences: ${price_prefs.get('min', 0)}-${price_prefs.get('max', 0)} (avg ${price_prefs.get('avg', 0):.0f})"
            
            platform_insights.append(f"""
PINTEREST DATA ({len(boards)} boards analyzed):
- Board Themes: {', '.join(board_themes)}
- Pin Keywords: {', '.join(pin_keywords)}
- Specific Wants: {', '.join(specific_wants)}
- Planning Mindset: {'Yes' if pin_signals.get('planning_mindset') else 'No'}{price_info}
- CRITICAL: Pinterest = EXPLICIT WISHLIST - they're pinning what they want
""")
        elif 'pinterest' in platforms:
            # Basic Pinterest insights (fallback)
            pinterest = platforms['pinterest']
            boards = pinterest.get('boards', [])
            if boards:
                board_names = [b['name'] for b in boards[:10]]
                platform_insights.append(f"""
PINTEREST DATA ({len(boards)} boards):
- Board Names: {', '.join(board_names)}
- Saved Interests: Visual preferences, aspirations, planning mindset
""")
        
        # Relationship context
        relationship_context = ""
        if recipient_type == 'someone_else' and relationship:
            relationship_context = RELATIONSHIP_PROMPTS.get(relationship, "")
        
        # ENHANCED: Use enhanced prompt if available, otherwise fallback to basic
        if ENHANCED_ENGINE_AVAILABLE and signals:
            try:
                prompt = build_enhanced_prompt(
                    platforms,
                    wishlist_data,
                    signals,
                    relationship_context,
                    recipient_type,
                    quality,
                    rec_count
                )
                logger.info("Using enhanced recommendation engine")
            except Exception as e:
                logger.error(f"Error building enhanced prompt: {e}", exc_info=True)
                # Fallback to basic prompt below
                prompt = None
        else:
            prompt = None
        
        # Build basic prompt (fallback or if enhanced not available)
        if not prompt:
            low_data_instructions = ""
            if quality['quality'] in ['limited', 'insufficient']:
                low_data_instructions = f"""
NOTE: Limited data available ({quality['total_posts']} posts) - focus on SAFE, OBVIOUS choices based on clear signals.
Generate ONLY {rec_count} recommendations (NOT 10 - we have limited data).
With limited data, prioritize SAFE BETS - obvious choices that won't miss.
Each recommendation MUST cite specific posts/behaviors that justify it.
If you only have evidence for {rec_count - 1} gifts, return {rec_count - 1} gifts, not {rec_count}.
DO NOT make assumptions - only recommend what you have clear evidence for.
"""
            
            prompt = f"""You are an expert gift curator. Based on the following social media data, generate {rec_count} highly specific, actionable gift recommendations.

USER DATA:
{chr(10).join(platform_insights)}{relationship_context}

{low_data_instructions}

CRITICAL INSTRUCTIONS:
1. For each recommendation, provide specific product URLs:
   - Direct brand URLs when possible: https://brandname.com/products/specific-item
   - Specialty retailers: https://www.etsy.com/search?q=specific+product+name
   - Amazon search as fallback: https://www.amazon.com/s?k=specific+product+name
2. Be as specific as possible with product names, brands, and model numbers
3. Prioritize UNIQUE, SPECIALTY items over generic mass-market products
4. Focus on independent makers, artisan shops, unique items that show thoughtfulness
5. Use evidence from their actual posts - cite specific captions, hashtags, or creators they follow

COLLECTIBLE SERIES INTELLIGENCE:
- If someone collects something (LEGO sets, Funko Pops, vinyl variants, sneakers, trading cards, action figures, etc.):
  * Identify the series/collection they're building
  * Note what they already have based on posts
  * Suggest the BEST next item considering:
    - Recency (new releases they might not know about)
    - Rarity (hard-to-find items that are valuable)
    - Completion (missing pieces in their collection)
    - Personal relevance (e.g., Tokyo LEGO set for someone who posts about Tokyo)
  * Include "collectible_series" field with 2-3 alternatives and reasoning
  * Example: If they collect LEGO Architecture, suggest specific sets with alternatives

PRICE DISTRIBUTION:
{f"- {rec_count // 2} items in $15-50 range" if rec_count >= 5 else "- Most items in $15-50 range"}
{f"- {rec_count // 3} items in $50-100 range" if rec_count >= 6 else "- Some items in $50-100 range"}
{f"- {rec_count // 5} items in $100-200 range" if rec_count >= 8 else "- 1-2 items in $100-200 range"}

Return EXACTLY {rec_count} recommendations as a JSON array with this structure:
[
  {{
    "name": "SPECIFIC product name with brand/model (e.g., 'LEGO Architecture: Tokyo Skyline Set 21051')",
    "description": "2-3 sentence description of what this is and why it's special",
    "why_perfect": "Why this matches their interests with SPECIFIC evidence from their posts/reposts/hashtags",
    "price_range": "$XX-$XX",
    "where_to_buy": "Specific retailer name (Etsy shop name, UncommonGoods, brand site, Amazon)",
    "product_url": "https://REAL-URL.com (construct the most specific URL possible)",
    "gift_type": "physical" or "experience",
    "confidence_level": "safe_bet" or "adventurous",
    "collectible_series": {{  // OPTIONAL - only if this is part of a collectible series
      "series_name": "LEGO Architecture",
      "current_suggestion": "Tokyo Skyline (newest 2024 release)",
      "alternatives": [
        "Dubai Skyline - More intricate, 740 pieces ($60)",
        "New York City - Iconic skyline, 598 pieces ($50)",
        "The White House - Historic architecture, 1,483 pieces ($100)"
      ],
      "why_these": "Based on their travel posts (Tokyo tagged 3x) and architecture interest shown in hashtags"
    }}
  }}
]

IMPORTANT: 
- Return ONLY the JSON array, no markdown, no backticks, no explanatory text
- Each recommendation must have clear evidence from their social media
- URLs should be as specific as possible (not just homepage links)
- For collectibles, research the series and suggest thoughtful alternatives"""

        logger.info(f"Generating {rec_count} recommendations for user: {user.get('email', 'unknown')}")
        logger.info(f"Data quality: {quality['quality']} ({quality['total_posts']} posts)")
        logger.info(f"Platforms: {list(platforms.keys())}")
        
        # FIXED: Comprehensive error handling for Claude API
        try:
            message = claude_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=8000,
                messages=[{"role": "user", "content": prompt}],
                timeout=120.0  # Increased to 2 minutes for complex prompts
            )
            
            # Track API usage
            if USAGE_TRACKING_AVAILABLE:
                try:
                    # Get actual token usage from response if available
                    if hasattr(message, 'usage'):
                        input_tokens = message.usage.input_tokens
                        output_tokens = message.usage.output_tokens
                        total_tokens = input_tokens + output_tokens
                    else:
                        # Estimate tokens (rough: 1 token ≈ 4 characters)
                        input_tokens = len(prompt) // 4
                        output_tokens = 2000  # Estimate for output
                        total_tokens = input_tokens + output_tokens
                    track_anthropic_usage(total_tokens, 'recommendation')
                except Exception as e:
                    logger.warning(f"Failed to track Anthropic usage: {e}")
        except anthropic.APIError as e:
            logger.error(f"Claude API error: {e}")
            return jsonify({
                'success': False,
                'error': 'AI service temporarily unavailable. Please try again in a moment.',
                'retry_after': 60
            }), 503
        except anthropic.APIConnectionError as e:
            logger.error(f"Claude connection error: {e}")
            return jsonify({
                'success': False,
                'error': 'Unable to connect to AI service. Please check your internet connection and try again.'
            }), 503
        except anthropic.RateLimitError as e:
            logger.error(f"Claude rate limit error: {e}")
            return jsonify({
                'success': False,
                'error': 'Service is busy. Please try again in a few minutes.',
                'retry_after': 300
            }), 429
        except Exception as e:
            logger.error(f"Unexpected Claude API error: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': 'An unexpected error occurred. Please contact support if this persists.'
            }), 500
        
        # Extract response
        response_text = ""
        try:
            for block in message.content:
                if block.type == "text":
                    response_text += block.text
        except Exception as e:
            logger.error(f"Error extracting Claude response: {e}")
            return jsonify({
                'success': False,
                'error': 'Error processing AI response. Please try again.'
            }), 500
        
        response_text = response_text.strip()
        
        logger.info(f"Claude response received, length: {len(response_text)}")
        
        # Parse JSON
        try:
            if response_text.startswith('```'):
                response_text = response_text.split('```')[1]
                if response_text.startswith('json'):
                    response_text = response_text[4:]
                response_text = response_text.strip()
            
            recommendations = json.loads(response_text)
            
            # Validate recommendations structure
            if not isinstance(recommendations, list):
                raise ValueError("Recommendations must be a list")
            
            if len(recommendations) == 0:
                raise ValueError("No recommendations generated")
            
            # ENHANCED: Post-process validation if enhanced engine available
            if ENHANCED_ENGINE_AVAILABLE and avoid_items:
                try:
                    recommendations = validate_recommendations(recommendations, avoid_items, signals)
                    logger.info(f"Validated {len(recommendations)} recommendations (filtered duplicates)")
                except Exception as e:
                    logger.error(f"Error validating recommendations: {e}")
                    # Continue with unvalidated recommendations
            
            logger.info(f"Successfully parsed {len(recommendations)} recommendations")
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            logger.error(f"Response text (first 500 chars): {response_text[:500]}")
            return jsonify({
                'success': False,
                'error': 'AI returned invalid response format. Please try again.',
                'debug': response_text[:200] if len(response_text) < 200 else response_text[:200] + '...'
            }), 500
        except Exception as e:
            logger.error(f"Error parsing recommendations: {e}")
            return jsonify({
                'success': False,
                'error': 'Error processing recommendations. Please try again.'
            }), 500
        
        # Save recommendations
        user_id = session['user_id']
        save_user(user_id, {
            'recommendations': recommendations,
            'data_quality': quality,
            'last_generated': datetime.now().isoformat()
        })
        
        return jsonify({
            'success': True,
            'recommendations': recommendations,
            'data_quality': quality
        })
        
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
    
    return render_template('recommendations.html', 
                         recommendations=recommendations,
                         data_quality=data_quality,
                         connected_count=connected_count,
                         user=user)

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

@app.route('/logout')
def logout():
    """Logout user"""
    session.clear()
    return redirect('/')

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
