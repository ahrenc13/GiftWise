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

Author: Chad + Claude
Date: January 2026
"""

import os
import json
import time
import uuid
import threading
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, session, jsonify, url_for, Response
import stripe
import anthropic
from dotenv import load_dotenv
from collections import Counter

# OAuth libraries
from requests_oauthlib import OAuth2Session
import requests

# Database (using simple JSON for MVP - upgrade to PostgreSQL later)
import shelve

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')

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
stripe.api_key = STRIPE_SECRET_KEY
claude_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# ============================================================================
# FREEMIUM TIER CONFIGURATION
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
# PROGRESS TRACKING (In-memory for MVP, upgrade to Redis for production)
# ============================================================================

scraping_progress = {}

def set_progress(task_id, status, message, percent=0):
    """Update scraping progress"""
    scraping_progress[task_id] = {
        'status': status,
        'message': message,
        'percent': percent,
        'timestamp': datetime.now().isoformat()
    }

def get_progress(task_id):
    """Get scraping progress"""
    return scraping_progress.get(task_id, {
        'status': 'unknown',
        'message': 'Unknown status',
        'percent': 0
    })

# ============================================================================
# DATABASE HELPERS
# ============================================================================

def get_user(user_id):
    """Get user data from database"""
    with shelve.open('giftwise_db') as db:
        return db.get(f'user_{user_id}')

def save_user(user_id, data):
    """Save user data to database"""
    with shelve.open('giftwise_db') as db:
        existing = db.get(f'user_{user_id}', {})
        existing.update(data)
        db[f'user_{user_id}'] = existing

def get_session_user():
    """Get current user from session"""
    user_id = session.get('user_id')
    if user_id:
        return get_user(user_id)
    return None

def get_user_tier(user):
    """Get user's subscription tier"""
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
        print(f"Instagram privacy check error: {e}")
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
        print(f"TikTok validation error for @{username}: {e}")
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
        print("No Apify token configured")
        return None
    
    try:
        if task_id:
            set_progress(task_id, 'running', 'Starting Instagram scraper...', 5)
        
        print(f"Starting Instagram scrape for @{username}")
        
        response = requests.post(
            f'https://api.apify.com/v2/acts/{APIFY_INSTAGRAM_ACTOR}/runs?token={APIFY_API_TOKEN}',
            json={
                'username': [username],
                'resultsLimit': max_posts
            }
        )
        
        if response.status_code != 201:
            if task_id:
                set_progress(task_id, 'error', 'Failed to start scraper', 0)
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
                    10: 'Finding @{username}...',
                    30: 'Analyzing profile...',
                    50: 'Downloading posts...',
                    70: 'Extracting interests...',
                    85: 'Processing data...'
                }
                msg = messages.get(int(progress_pct // 10) * 10, 'Analyzing profile...')
                set_progress(task_id, 'running', msg, progress_pct)
            
            status_response = requests.get(
                f'https://api.apify.com/v2/actor-runs/{run_id}?token={APIFY_API_TOKEN}'
            )
            
            if status_response.status_code != 200:
                continue
                
            status = status_response.json()['data']['status']
            
            if status == 'SUCCEEDED':
                break
            elif status in ['FAILED', 'ABORTED', 'TIMED-OUT']:
                if task_id:
                    set_progress(task_id, 'error', 'Instagram scraping failed', 0)
                return None
        
        # Get results
        results_response = requests.get(
            f'https://api.apify.com/v2/actor-runs/{run_id}/dataset/items?token={APIFY_API_TOKEN}'
        )
        
        if results_response.status_code != 200:
            if task_id:
                set_progress(task_id, 'error', 'Failed to retrieve data', 0)
            return None
        
        data = results_response.json()
        
        if not data:
            if task_id:
                set_progress(task_id, 'error', 'No posts found', 0)
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
        
        return result
        
    except Exception as e:
        print(f"Instagram scraping error: {e}")
        if task_id:
            set_progress(task_id, 'error', f'Error: {str(e)}', 0)
        return None

def scrape_tiktok_profile(username, max_videos=50, task_id=None):
    """
    Scrape TikTok with progress tracking and repost analysis
    """
    if not APIFY_API_TOKEN:
        print("No Apify token configured")
        return None
    
    try:
        if task_id:
            set_progress(task_id, 'running', 'Starting TikTok scraper...', 5)
        
        print(f"Starting TikTok scrape for @{username}")
        
        response = requests.post(
            f'https://api.apify.com/v2/acts/{APIFY_TIKTOK_ACTOR}/runs?token={APIFY_API_TOKEN}',
            json={
                'profiles': [username],
                'resultsPerPage': max_videos
            }
        )
        
        if response.status_code != 201:
            if task_id:
                set_progress(task_id, 'error', 'Failed to start scraper', 0)
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
                    10: 'Finding @{username}...',
                    30: 'Analyzing videos...',
                    50: 'Detecting reposts...',
                    70: 'Extracting interests...',
                    85: 'Processing data...'
                }
                msg = messages.get(int(progress_pct // 10) * 10, 'Analyzing videos...')
                set_progress(task_id, 'running', msg, progress_pct)
            
            status_response = requests.get(
                f'https://api.apify.com/v2/actor-runs/{run_id}?token={APIFY_API_TOKEN}'
            )
            
            if status_response.status_code != 200:
                continue
                
            status = status_response.json()['data']['status']
            
            if status == 'SUCCEEDED':
                break
            elif status in ['FAILED', 'ABORTED', 'TIMED-OUT']:
                if task_id:
                    set_progress(task_id, 'error', 'TikTok scraping failed', 0)
                return None
        
        # Get results
        results_response = requests.get(
            f'https://api.apify.com/v2/actor-runs/{run_id}/dataset/items?token={APIFY_API_TOKEN}'
        )
        
        if results_response.status_code != 200:
            if task_id:
                set_progress(task_id, 'error', 'Failed to retrieve data', 0)
            return None
        
        data = results_response.json()
        
        if not data:
            if task_id:
                set_progress(task_id, 'error', 'No videos found', 0)
            return None
        
        # Parse with repost intelligence
        parsed_data = parse_tiktok_data(data, username)
        
        if task_id:
            total_videos = parsed_data.get('total_videos', 0)
            set_progress(task_id, 'complete', f'✓ Connected! Found {total_videos} videos', 100)
        
        return parsed_data
        
    except Exception as e:
        print(f"TikTok scraping error: {e}")
        if task_id:
            set_progress(task_id, 'error', f'Error: {str(e)}', 0)
        return None

def parse_tiktok_data(data, username):
    """
    Parse TikTok data with repost analysis
    """
    from collections import Counter
    
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
        email = request.form.get('email')
        recipient_type = request.form.get('recipient_type')
        relationship = request.form.get('relationship', '')
        
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
        
        return redirect('/connect-platforms')
    
    return render_template('signup.html', relationship_options=RELATIONSHIP_OPTIONS)

@app.route('/connect-platforms')
def connect_platforms():
    """Platform connection page"""
    user = get_session_user()
    if not user:
        return redirect('/signup')
    
    return render_template('connect_platforms.html', 
                         platforms=user.get('platforms', {}),
                         recipient_type=user.get('recipient_type', 'myself'))

@app.route('/api/validate-username', methods=['POST'])
def validate_username():
    """Instant username validation endpoint"""
    data = request.get_json()
    platform = data.get('platform')
    username = data.get('username', '').strip().replace('@', '')
    
    if not username:
        return jsonify({'valid': False, 'message': 'Username required'})
    
    if platform == 'instagram':
        result = check_instagram_privacy(username)
    elif platform == 'tiktok':
        result = check_tiktok_privacy(username)
    else:
        return jsonify({'valid': False, 'message': 'Invalid platform'})
    
    return jsonify(result)

@app.route('/connect/instagram', methods=['POST'])
def connect_instagram():
    """Connect Instagram with progress tracking"""
    user = get_session_user()
    if not user:
        return redirect('/signup')
    
    username = request.form.get('username', '').strip().replace('@', '')
    
    if not username:
        return redirect('/connect-platforms?error=instagram_no_username')
    
    # Generate unique task ID
    task_id = str(uuid.uuid4())
    
    # Get user_id BEFORE starting thread
    user_id = session['user_id']
    
    # Start scraping in background thread
    def scrape_task():
        instagram_data = scrape_instagram_profile(username, max_posts=50, task_id=task_id)
        
        if instagram_data:
            # Save to database using passed user_id
            user = get_user(user_id)
            platforms = user.get('platforms', {})
            platforms['instagram'] = {
                'username': username,
                'connected_at': datetime.now().isoformat(),
                'method': 'scraping',
                'data': instagram_data
            }
            save_user(user_id, {'platforms': platforms})
    
    thread = threading.Thread(target=scrape_task)
    thread.daemon = True
    thread.start()
    
    # Redirect to progress page
    return redirect(f'/connect-progress/instagram/{task_id}')

@app.route('/connect/tiktok', methods=['POST'])
def connect_tiktok():
    """Connect TikTok with progress tracking"""
    user = get_session_user()
    if not user:
        return redirect('/signup')
    
    username = request.form.get('username', '').strip().lstrip('@')
    
    if not username:
        return redirect('/connect-platforms?error=tiktok_no_username')
    
    # Generate unique task ID
    task_id = str(uuid.uuid4())
    
    # Get user_id BEFORE starting thread
    user_id = session['user_id']
    
    # Start scraping in background thread
    def scrape_task():
        tiktok_data = scrape_tiktok_profile(username, max_videos=50, task_id=task_id)
        
        if tiktok_data:
            # Save to database using passed user_id
            user = get_user(user_id)
            platforms = user.get('platforms', {})
            platforms['tiktok'] = {
                'username': username,
                'connected_at': datetime.now().isoformat(),
                'method': 'scraping',
                'data': tiktok_data
            }
            save_user(user_id, {'platforms': platforms})
    
    thread = threading.Thread(target=scrape_task)
    thread.daemon = True
    thread.start()
    
    # Redirect to progress page
    return redirect(f'/connect-progress/tiktok/{task_id}')

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
    """Generate gift recommendations with data quality check"""
    user = get_session_user()
    if not user:
        return redirect('/signup')
    
    platforms = user.get('platforms', {})
    
    if len(platforms) < 1:
        return redirect('/connect-platforms?error=need_platforms')
    
    # Check data quality
    quality = check_data_quality(platforms)
    
    # If insufficient data, show warning page
    if quality['quality'] == 'insufficient' and not request.args.get('force'):
        return render_template('low_data_warning.html', 
                             quality=quality,
                             ig_count=quality['platform_counts'].get('instagram', 0),
                             tt_count=quality['platform_counts'].get('tiktok', 0),
                             total_count=quality['total_posts'],
                             rec_count=quality['recommendation_count'])
    
    # Show loading page
    recipient_type = user.get('recipient_type', 'myself')
    return render_template('generating.html', 
                         platforms=list(platforms.keys()),
                         recipient_type=recipient_type)

@app.route('/api/generate-recommendations', methods=['POST'])
def api_generate_recommendations():
    """
    Generate recommendations with:
    - Web search for real URLs
    - Dynamic rec count based on data quality
    - Collectible series intelligence
    - Relationship-specific prompts
    """
    user = get_session_user()
    if not user:
        return jsonify({'success': False, 'error': 'Not logged in'}), 401
    
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
        
        # Build platform insights
        platform_insights = []
        
        # Instagram data
        if 'instagram' in platforms:
            ig_data = platforms['instagram'].get('data', {})
            if ig_data:
                posts = ig_data.get('posts', [])
                captions = [p['caption'][:200] for p in posts if p.get('caption')]
                hashtags_all = []
                for p in posts:
                    hashtags_all.extend(p.get('hashtags', []))
                top_hashtags = Counter(hashtags_all).most_common(15)
                
                platform_insights.append(f"""
INSTAGRAM DATA ({len(posts)} posts analyzed):
- Username: @{ig_data.get('username', 'unknown')}
- Recent Post Themes: {'; '.join(captions[:15])}
- Top Hashtags: {', '.join([tag[0] for tag in top_hashtags])}
- Engagement: Average {sum(p.get('likes', 0) for p in posts) / len(posts):.0f} likes per post
""")
        
        # TikTok data with repost intelligence
        if 'tiktok' in platforms:
            tt_data = platforms['tiktok'].get('data', {})
            if tt_data:
                videos = tt_data.get('videos', [])
                descriptions = [v['description'][:150] for v in videos[:20] if v.get('description')]
                favorite_creators = tt_data.get('favorite_creators', [])
                repost_patterns = tt_data.get('repost_patterns', {})
                top_hashtags = tt_data.get('top_hashtags', {})
                top_music = tt_data.get('top_music', {})
                
                # Creator personality insights
                creator_insights = ""
                if favorite_creators:
                    creator_list = [f"@{creator[0]} ({creator[1]} reposts)" for creator in favorite_creators[:5]]
                    creator_insights = f"\n- Frequently Reposts From: {', '.join(creator_list)}"
                    creator_insights += f"\n- CRITICAL: Research these creators' content themes, aesthetics, and product recommendations"
                    creator_insights += f"\n- What these creators represent is what the user aspires to or identifies with"
                
                # Music taste signals
                music_insights = ""
                if top_music:
                    music_list = list(top_music.keys())[:5]
                    music_insights = f"\n- Popular Sounds: {', '.join(music_list)}"
                    music_insights += f"\n- Music taste can indicate aesthetic preferences and subcultures"
                
                platform_insights.append(f"""
TIKTOK DATA ({tt_data.get('total_videos', 0)} videos analyzed):
- Username: @{tt_data.get('username', 'unknown')}
- Original Content Themes: {'; '.join(descriptions[:15])}
- Repost Behavior: {repost_patterns.get('total_reposts', 0)} reposts out of {tt_data.get('total_videos', 0)} total videos ({repost_patterns.get('repost_percentage', 0):.1f}%)
{creator_insights}
{music_insights}
- Top Hashtags: {', '.join(list(top_hashtags.keys())[:10])}

KEY INSIGHT: Their reposts are MORE revealing than original posts. What they choose to amplify shows what resonates most.
TASK: For each favorite creator, consider what aesthetic/lifestyle/values that creator represents.
""")
        
        # Pinterest data (if available)
        if 'pinterest' in platforms:
            pinterest = platforms['pinterest']
            boards = pinterest.get('boards', [])
            if boards:
                board_names = [b['name'] for b in boards[:10]]
                platform_insights.append(f"""
PINTEREST DATA ({len(boards)} boards):
- Board Names: {', '.join(board_names)}
- Saved Interests: Visual preferences, aspirations, planning
""")
        
        # Relationship context
        relationship_context = ""
        if recipient_type == 'someone_else' and relationship:
            relationship_context = RELATIONSHIP_PROMPTS.get(relationship, "")
        
        # Build prompt with all enhancements
        low_data_instructions = ""
        if quality['quality'] in ['limited', 'insufficient']:
            low_data_instructions = f"""
NOTE: Limited data available ({quality['total_posts']} posts) - focus on SAFE, OBVIOUS choices based on clear signals.
Generate ONLY {rec_count} recommendations (NOT 10 - we have limited data).
With limited data, prioritize SAFE BETS - obvious choices that won't miss.
Each recommendation MUST cite specific posts/behaviors that justify it.
If you only have evidence for {rec_count - 1} gifts, return {rec_count - 1} gifts, not {rec_count}.
"""
        
        prompt = f"""You are an expert gift curator with access to web search. Based on the following social media data, generate {rec_count} highly specific, actionable gift recommendations.

USER DATA:
{chr(10).join(platform_insights)}{relationship_context}

{low_data_instructions}

CRITICAL INSTRUCTIONS:
1. You have WEB SEARCH available - use it to find REAL product pages
2. For each recommendation, use web_search to find the ACTUAL product page:
   - Search for: "[Brand] [Product Name] [Model] buy online"
   - Prioritize: Direct brand website → Specialty retailers (Etsy, UncommonGoods) → Amazon
   - Return the REAL URL you found via search
   - If you cannot find a real URL, use: https://www.etsy.com/search?q=specific+product+name
3. VERIFY products exist before recommending them via search
4. Get real current prices via search
5. Prioritize UNIQUE, SPECIALTY items over generic mass-market products
6. Focus on independent makers, artisan shops, unique experiences

COLLECTIBLE SERIES INTELLIGENCE:
- If someone collects something (LEGO sets, Funko Pops, vinyl variants, sneakers, trading cards, etc.):
  * Identify the series/collection
  * Note what they already have (from posts)
  * Suggest the BEST next item considering:
    - Recency (new releases they might not know about)
    - Rarity (hard-to-find items)
    - Completion (missing pieces in their collection)
    - Personal relevance (e.g., Tokyo LEGO for someone who posts about Tokyo)
  * Include "collectible_series" field with alternatives

PRICE DISTRIBUTION:
{f"- {rec_count // 2} items in $15-50 range" if rec_count >= 5 else "- Most items in $15-50 range"}
{f"- {rec_count // 3} items in $50-100 range" if rec_count >= 6 else "- Some items in $50-100 range"}
{f"- {rec_count // 5} items in $100-200 range" if rec_count >= 8 else "- 1-2 items in $100-200 range"}

Return EXACTLY {rec_count} recommendations as a JSON array with this structure:
[
  {{
    "name": "SPECIFIC product name with brand/model (e.g., 'LEGO Architecture: Tokyo Skyline Set (21051)')",
    "description": "2-3 sentence description of what this is and why it's special",
    "why_perfect": "Why this matches their interests with SPECIFIC evidence from their posts/reposts",
    "price_range": "$XX-$XX",
    "where_to_buy": "Specific retailer name",
    "product_url": "https://REAL-URL-FROM-WEB-SEARCH.com",
    "gift_type": "physical" or "experience",
    "confidence_level": "safe_bet" or "adventurous",
    "collectible_series": {{  // OPTIONAL - only if this is part of a collectible series
      "series_name": "LEGO Architecture",
      "current_suggestion": "Tokyo Skyline (newest release)",
      "alternatives": [
        "Dubai Skyline - More intricate (740 pieces, $60)",
        "New York City - Iconic (598 pieces, $50)"
      ],
      "why_these": "Based on their travel posts and architecture interest"
    }}
  }}
]

IMPORTANT: Return ONLY the JSON array. No markdown, no backticks, no explanatory text."""

        print(f"Generating {rec_count} recommendations for user: {user.get('email', 'unknown')}")
        print(f"Data quality: {quality['quality']} ({quality['total_posts']} posts)")
        
        # Call Claude API with web search enabled
        message = claude_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=8000,
            tools=[
                {
                    "type": "web_search_20250305",
                    "name": "web_search"
                }
            ],
            messages=[{"role": "user", "content": prompt}]
        )
        
        # Extract response (handle tool use)
        response_text = ""
        for block in message.content:
            if block.type == "text":
                response_text += block.text
        
        response_text = response_text.strip()
        
        print(f"Claude response received, length: {len(response_text)}")
        
        # Parse JSON
        try:
            if response_text.startswith('```'):
                response_text = response_text.split('```')[1]
                if response_text.startswith('json'):
                    response_text = response_text[4:]
                response_text = response_text.strip()
            
            recommendations = json.loads(response_text)
            print(f"Successfully parsed {len(recommendations)} recommendations")
            
        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}")
            recommendations = [{
                'name': 'Recommendations generated',
                'description': response_text[:500],
                'why_perfect': 'See full response',
                'price_range': 'Various',
                'where_to_buy': 'Various retailers',
                'product_url': '',
                'gift_type': 'physical',
                'confidence_level': 'safe_bet'
            }]
        
        # Save recommendations
        save_user(session['user_id'], {
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
        print(f"Recommendation generation error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/fix-recommendation-link', methods=['POST'])
def fix_recommendation_link():
    """
    Use Claude with web search to find a working link for a recommendation
    """
    data = request.get_json()
    product_name = data.get('product_name')
    description = data.get('description', '')
    
    if not product_name:
        return jsonify({'success': False, 'error': 'Product name required'})
    
    try:
        prompt = f"""Find a working purchase link for this product:

Product: {product_name}
Description: {description}

Instructions:
1. Use web_search to find where this product can be purchased online
2. Prioritize: Brand website → Specialty retailers (Etsy, UncommonGoods) → Amazon
3. Return the REAL URL you found
4. Verify the link actually leads to this product or very similar

Return ONLY a JSON object with this structure:
{{
  "url": "https://actual-working-url.com/product",
  "retailer": "Name of retailer",
  "confidence": "high" or "medium",
  "note": "Brief note about what you found"
}}
"""
        
        message = claude_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            tools=[
                {
                    "type": "web_search_20250305",
                    "name": "web_search"
                }
            ],
            messages=[{"role": "user", "content": prompt}]
        )
        
        # Extract response
        response_text = ""
        for block in message.content:
            if block.type == "text":
                response_text += block.text
        
        # Parse JSON
        response_text = response_text.strip()
        if response_text.startswith('```'):
            response_text = response_text.split('```')[1]
            if response_text.startswith('json'):
                response_text = response_text[4:]
            response_text = response_text.strip()
        
        result = json.loads(response_text)
        
        print(f"Fixed link for '{product_name}': {result.get('url')} ({result.get('retailer')})")
        
        return jsonify({
            'success': True,
            'new_url': result.get('url'),
            'button_text': f"View on {result.get('retailer', 'Retailer')} →",
            'note': result.get('note')
        })
    
    except Exception as e:
        print(f"Link fix error for '{product_name}': {e}")
        
        # Fallback to search
        search_query = product_name.replace(' ', '+')
        return jsonify({
            'success': True,
            'new_url': f'https://www.amazon.com/s?k={search_query}',
            'button_text': 'Search on Amazon →',
            'note': 'Fallback to Amazon search'
        })

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

@app.route('/logout')
def logout():
    """Logout user"""
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True, port=5000)
