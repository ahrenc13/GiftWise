"""
GIFTWISE MAIN APPLICATION - UPDATED WITH ACTIVATION ENERGY IMPROVEMENTS
AI-Powered Gift Recommendations from Social Media

UPDATES (January 26, 2026):
✅ Real-time privacy validation for Instagram/TikTok
✅ Progress indicators during scraping operations
✅ Simplified relationship selector
✅ Error state preservation
✅ Clear platform requirements

CURRENT PLATFORM STATUS:
✅ Pinterest - OAuth available (full data access)
✅ Instagram - Public scraping via Apify (50 posts)
✅ TikTok - Public scraping via Apify (50 videos with repost analysis)
⏳ Spotify - OAuth blocked (not accepting new apps)

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

# Pinterest OAuth Configuration (AVAILABLE NOW)
PINTEREST_CLIENT_ID = os.environ.get('PINTEREST_CLIENT_ID')
PINTEREST_CLIENT_SECRET = os.environ.get('PINTEREST_CLIENT_SECRET')
PINTEREST_REDIRECT_URI = os.environ.get('PINTEREST_REDIRECT_URI', 'http://localhost:5000/oauth/pinterest/callback')
PINTEREST_AUTH_URL = 'https://www.pinterest.com/oauth/'
PINTEREST_TOKEN_URL = 'https://api.pinterest.com/v5/oauth/token'
PINTEREST_API_URL = 'https://api.pinterest.com/v5'

# Apify Configuration
APIFY_API_TOKEN = os.environ.get('APIFY_API_TOKEN')
APIFY_INSTAGRAM_ACTOR = 'nH2AHrwxeTRJoN5hX'  # Tested and working actor ID
APIFY_TIKTOK_ACTOR = '0FXVyOXXEmdGcV88a'  # Tested and working actor ID

# Spotify (keeping for future)
SPOTIFY_CLIENT_ID = os.environ.get('SPOTIFY_CLIENT_ID', '')
SPOTIFY_CLIENT_SECRET = os.environ.get('SPOTIFY_CLIENT_SECRET', '')

# Initialize clients
stripe.api_key = STRIPE_SECRET_KEY
claude_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# ============================================================================
# PROGRESS TRACKING (In-memory for MVP - use Redis in production)
# ============================================================================

scraping_progress = {}

def set_progress(task_id, status, message, percent=0):
    """Update progress for a scraping task"""
    scraping_progress[task_id] = {
        'status': status,  # 'running', 'success', 'error'
        'message': message,
        'percent': percent,
        'timestamp': time.time()
    }

def get_progress(task_id):
    """Get current progress for a task"""
    return scraping_progress.get(task_id, {
        'status': 'unknown',
        'message': 'Unknown task',
        'percent': 0
    })

# ============================================================================
# PLATFORM AVAILABILITY STATUS
# ============================================================================

PLATFORM_STATUS = {
    'pinterest': {
        'available': True,
        'method': 'oauth',
        'status': 'Full data access via OAuth',
        'icon': '📌',
        'color': '#E60023'
    },
    'instagram': {
        'available': True,
        'method': 'scraping',
        'status': 'Public profile data (50 posts)',
        'icon': '📷',
        'color': '#E1306C',
        'note': 'OAuth blocked by Meta - using public data via Apify'
    },
    'tiktok': {
        'available': True,
        'method': 'scraping',
        'status': 'Public profile data (50 videos)',
        'icon': '🎬',
        'color': '#000000',
        'note': 'No OAuth available - using public data via Apify'
    },
    'spotify': {
        'available': False,
        'method': 'oauth',
        'status': 'Coming soon',
        'icon': '🎵',
        'color': '#1DB954',
        'note': 'OAuth currently blocked - working on access'
    }
}

# ============================================================================
# SIMPLIFIED RELATIONSHIP CONTEXT OPTIONS
# ============================================================================

RELATIONSHIP_OPTIONS = [
    ('close', 'Close relationship (partner, best friend, family)'),
    ('friendly', 'Friendly relationship (friend, extended family, favorite coworker)'),
    ('professional', 'Professional relationship (colleague, client, acquaintance)')
]

# Mapping to old categories for backend compatibility
RELATIONSHIP_MAPPING = {
    'close': 'romantic_partner',
    'friendly': 'close_friend',
    'professional': 'coworker'
}

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

# ============================================================================
# REAL-TIME USERNAME VALIDATION
# ============================================================================

@app.route('/api/validate-username', methods=['POST'])
def validate_username():
    """
    Instant validation of Instagram/TikTok username
    Returns whether account exists and is public
    
    This prevents users from submitting private accounts and waiting 
    30-120 seconds only to get an error.
    """
    data = request.get_json()
    platform = data.get('platform')
    username = data.get('username', '').strip().replace('@', '')
    
    if not username:
        return jsonify({
            'valid': False,
            'error': 'Username required'
        })
    
    try:
        if platform == 'instagram':
            result = check_instagram_privacy(username)
        elif platform == 'tiktok':
            result = check_tiktok_privacy(username)
        else:
            return jsonify({'valid': False, 'error': 'Invalid platform'})
        
        return jsonify(result)
    
    except Exception as e:
        print(f"Validation error for {platform}/{username}: {e}")
        return jsonify({
            'valid': False,
            'error': 'Validation failed - please try again'
        })


def check_instagram_privacy(username):
    """
    Check if Instagram account exists and is public
    Returns: dict with valid, private, message
    """
    try:
        url = f'https://www.instagram.com/{username}/'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=5)
        
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
        
        # Parse embedded JSON data
        html = response.text
        
        # Instagram embeds data in script tags that include "is_private"
        is_private = '"is_private":true' in html or '"isPrivate":true' in html
        
        if is_private:
            return {
                'valid': False,
                'private': True,
                'exists': True,
                'message': '✗ Private account - we can only analyze public profiles',
                'help': 'Ask them to make their profile public temporarily, or try a different platform',
                'icon': '🔒'
            }
        
        # Extract follower count for additional context (optional)
        follower_count = None
        if '"edge_followed_by":{"count":' in html:
            try:
                count_str = html.split('"edge_followed_by":{"count":')[1].split('}')[0]
                follower_count = int(count_str)
            except:
                pass
        
        message = f'✓ Public profile found'
        if follower_count:
            message += f' ({follower_count:,} followers)'
        
        return {
            'valid': True,
            'private': False,
            'exists': True,
            'message': message,
            'icon': '✅',
            'follower_count': follower_count
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
            'valid': False,
            'error': str(e),
            'message': '⚠️ Unable to check account - you can still try connecting',
            'icon': '⚠️'
        }


def check_tiktok_privacy(username):
    """
    Check if TikTok account exists and is public
    Returns: dict with valid, private, message
    """
    try:
        url = f'https://www.tiktok.com/@{username}'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=5)
        
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
        
        # TikTok privacy indicators
        is_private = 'This account is private' in html or '"privateAccount":true' in html
        
        if is_private:
            return {
                'valid': False,
                'private': True,
                'exists': True,
                'message': '✗ Private account - we can only analyze public profiles',
                'help': 'Ask them to make their account public temporarily, or try a different platform',
                'icon': '🔒'
            }
        
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
            'message': '⚠️ TikTok is slow to respond - try again',
            'icon': '⚠️'
        }
    except Exception as e:
        print(f"TikTok privacy check error: {e}")
        return {
            'valid': False,
            'error': str(e),
            'message': '⚠️ Unable to check account - you can still try connecting',
            'icon': '⚠️'
        }

# ============================================================================
# PROGRESS STREAMING ENDPOINT (Server-Sent Events)
# ============================================================================

@app.route('/api/scrape-progress/<task_id>')
def stream_scrape_progress(task_id):
    """
    Server-Sent Events endpoint for real-time progress updates
    
    Usage from frontend:
    const eventSource = new EventSource('/api/scrape-progress/' + taskId);
    eventSource.onmessage = (event) => {
        const progress = JSON.parse(event.data);
        updateUI(progress);
    };
    """
    def generate():
        """Generator function for SSE"""
        last_status = None
        max_iterations = 120  # 2 minutes max
        iteration = 0
        
        while iteration < max_iterations:
            progress = get_progress(task_id)
            
            # Send update if status changed
            if progress != last_status:
                yield f"data: {json.dumps(progress)}\n\n"
                last_status = progress
            
            # Stop if completed or errored
            if progress.get('status') in ['success', 'error']:
                break
            
            time.sleep(1)  # Check every second
            iteration += 1
        
        # Timeout safety
        if iteration >= max_iterations:
            yield f"data: {json.dumps({'status': 'error', 'message': 'Operation timed out', 'percent': 0})}\n\n"
    
    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'  # Disable nginx buffering
        }
    )

# ============================================================================
# INSTAGRAM SCRAPING WITH PROGRESS
# ============================================================================

def scrape_instagram_profile(username, max_posts=50, task_id=None):
    """
    Scrape Instagram profile using Apify with progress tracking
    Returns: dict with posts, captions, engagement data
    """
    if not APIFY_API_TOKEN:
        if task_id:
            set_progress(task_id, 'error', 'Apify not configured', 0)
        print("No Apify token configured")
        return None
    
    try:
        if task_id:
            set_progress(task_id, 'running', 'Starting Instagram scraper...', 5)
        
        print(f"Starting Instagram scrape for @{username}")
        
        # Start Apify actor
        response = requests.post(
            f'https://api.apify.com/v2/acts/{APIFY_INSTAGRAM_ACTOR}/runs?token={APIFY_API_TOKEN}',
            json={
                'username': [username],  # Actor wants array format
                'resultsLimit': max_posts
            }
        )
        
        if response.status_code != 201:
            if task_id:
                set_progress(task_id, 'error', 'Failed to start scraper', 0)
            print(f"Apify Instagram actor start failed: {response.text}")
            return None
        
        run_id = response.json()['data']['id']
        if task_id:
            set_progress(task_id, 'running', f'Finding @{username} profile...', 15)
        print(f"Instagram scrape started, run ID: {run_id}")
        
        # Poll for completion with adaptive intervals and progress updates
        max_wait = 120  # 2 minutes max
        elapsed = 0
        
        while elapsed < max_wait:
            wait_time = 2 if elapsed < 30 else 5
            time.sleep(wait_time)
            elapsed += wait_time
            
            # Update progress based on elapsed time
            if task_id:
                percent = min(15 + (elapsed / max_wait * 70), 85)
                
                if elapsed < 20:
                    message = f'Analyzing @{username} profile...'
                elif elapsed < 40:
                    message = f'Downloading recent posts...'
                elif elapsed < 60:
                    message = f'Extracting interests and hashtags...'
                else:
                    message = f'Almost done - processing data...'
                
                set_progress(task_id, 'running', message, percent)
            
            status_response = requests.get(
                f'https://api.apify.com/v2/actor-runs/{run_id}?token={APIFY_API_TOKEN}'
            )
            
            if status_response.status_code != 200:
                print(f"Instagram status check failed: {status_response.text}")
                continue
                
            status = status_response.json()['data']['status']
            print(f"Instagram scrape status after {elapsed}s: {status}")
            
            if status == 'SUCCEEDED':
                if task_id:
                    set_progress(task_id, 'running', 'Processing results...', 90)
                break
            elif status in ['FAILED', 'ABORTED', 'TIMED-OUT']:
                if task_id:
                    set_progress(task_id, 'error', f'Scraping failed: {status}', 0)
                print(f"Instagram scrape failed with status: {status}")
                return None
        
        # Get results
        results_response = requests.get(
            f'https://api.apify.com/v2/actor-runs/{run_id}/dataset/items?token={APIFY_API_TOKEN}'
        )
        
        if results_response.status_code != 200:
            if task_id:
                set_progress(task_id, 'error', 'Failed to retrieve results', 0)
            print(f"Failed to get Instagram results: {results_response.text}")
            return None
        
        data = results_response.json()
        print(f"Instagram scrape complete: {len(data)} items retrieved")
        
        if not data or len(data) == 0:
            if task_id:
                set_progress(task_id, 'error', 'No data found - account may be private', 0)
            return None
        
        # DEBUG: Print data structure
        if data and len(data) > 0:
            print(f"DEBUG - Instagram data keys: {list(data[0].keys())}")
        
        # Parse and structure data (keeping your existing parsing logic)
        parsed_data = parse_instagram_data(data, username)
        
        if task_id:
            set_progress(task_id, 'success', f'✓ Connected! Found {len(data)} posts', 100)
        
        return parsed_data
        
    except Exception as e:
        if task_id:
            set_progress(task_id, 'error', f'Error: {str(e)}', 0)
        print(f"Instagram scraping error: {e}")
        import traceback
        traceback.print_exc()
        return None


def parse_instagram_data(data, username):
    """Parse Instagram data from Apify response"""
    from collections import Counter
    
    posts = []
    all_hashtags = []
    all_captions = []
    
    for item in data:
        caption = item.get('caption', '')
        likes = item.get('likesCount', 0)
        comments = item.get('commentsCount', 0)
        
        posts.append({
            'caption': caption,
            'likes': likes,
            'comments': comments,
            'engagement': likes + comments
        })
        
        if caption:
            all_captions.append(caption)
            # Extract hashtags
            words = caption.split()
            hashtags = [w for w in words if w.startswith('#')]
            all_hashtags.extend(hashtags)
    
    hashtag_counts = Counter(all_hashtags)
    
    return {
        'username': username,
        'total_posts': len(posts),
        'posts': posts,
        'top_hashtags': dict(hashtag_counts.most_common(30)),
        'captions': all_captions[:50]
    }

# ============================================================================
# TIKTOK SCRAPING WITH PROGRESS
# ============================================================================

def scrape_tiktok_profile(username, max_videos=50, task_id=None):
    """
    Scrape TikTok profile using Apify with progress tracking and repost analysis
    """
    if not APIFY_API_TOKEN:
        if task_id:
            set_progress(task_id, 'error', 'Apify not configured', 0)
        print("No Apify token configured")
        return None
    
    try:
        if task_id:
            set_progress(task_id, 'running', 'Starting TikTok scraper...', 5)
        
        print(f"Starting TikTok scrape for @{username}")
        
        # Start Apify actor
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
            print(f"Apify TikTok actor start failed: {response.text}")
            return None
        
        run_data = response.json()['data']
        run_id = run_data['id']
        
        if task_id:
            set_progress(task_id, 'running', f'Finding @{username} profile...', 15)
        print(f"TikTok scrape started, run ID: {run_id}")
        
        # Poll for completion with progress updates
        max_wait = 120
        elapsed = 0
        
        while elapsed < max_wait:
            wait_time = 2 if elapsed < 30 else 5
            time.sleep(wait_time)
            elapsed += wait_time
            
            # Update progress
            if task_id:
                percent = min(15 + (elapsed / max_wait * 70), 85)
                
                if elapsed < 20:
                    message = f'Analyzing @{username} profile...'
                elif elapsed < 40:
                    message = f'Downloading recent videos...'
                elif elapsed < 60:
                    message = f'Identifying reposts and interests...'
                else:
                    message = f'Almost done - processing data...'
                
                set_progress(task_id, 'running', message, percent)
            
            status_response = requests.get(
                f'https://api.apify.com/v2/actor-runs/{run_id}?token={APIFY_API_TOKEN}'
            )
            
            if status_response.status_code != 200:
                continue
            
            status = status_response.json()['data']['status']
            print(f"TikTok scrape status after {elapsed}s: {status}")
            
            if status == 'SUCCEEDED':
                if task_id:
                    set_progress(task_id, 'running', 'Processing results...', 90)
                break
            elif status in ['FAILED', 'ABORTED', 'TIMED-OUT']:
                if task_id:
                    set_progress(task_id, 'error', f'Scraping failed: {status}', 0)
                print(f"TikTok scrape failed: {status}")
                return None
        
        # Get results
        results_response = requests.get(
            f'https://api.apify.com/v2/actor-runs/{run_id}/dataset/items?token={APIFY_API_TOKEN}'
        )
        
        if results_response.status_code != 200:
            if task_id:
                set_progress(task_id, 'error', 'Failed to retrieve results', 0)
            return None
        
        data = results_response.json()
        print(f"TikTok scrape complete: {len(data)} items retrieved")
        
        if not data or len(data) == 0:
            if task_id:
                set_progress(task_id, 'error', 'No data found - account may be private', 0)
            return None
        
        # Parse data
        parsed_data = parse_tiktok_data(data, username)
        
        if task_id:
            repost_count = parsed_data.get('repost_patterns', {}).get('total_reposts', 0)
            set_progress(task_id, 'success', f'✓ Connected! Found {len(data)} videos, {repost_count} reposts', 100)
        
        return parsed_data
        
    except Exception as e:
        if task_id:
            set_progress(task_id, 'error', f'Error: {str(e)}', 0)
        print(f"TikTok scraping error: {e}")
        import traceback
        traceback.print_exc()
        return None


def parse_tiktok_data(data, username):
    """Parse TikTok data with repost analysis"""
    from collections import Counter
    
    videos = []
    all_hashtags = []
    all_music = []
    reposts = []
    creators = []
    
    for item in data:
        description = item.get('text', '')
        likes = item.get('diggCount', 0)
        is_repost = item.get('diversificationId', 0) > 0
        author_username = item.get('authorMeta', {}).get('name', '')
        
        video_data = {
            'description': description,
            'likes': likes,
            'is_repost': is_repost
        }
        
        videos.append(video_data)
        
        if is_repost:
            reposts.append(video_data)
            creators.append(author_username)
        
        # Extract hashtags
        hashtags = item.get('hashtags', [])
        for tag in hashtags:
            if isinstance(tag, dict):
                all_hashtags.append(tag.get('name', ''))
            else:
                all_hashtags.append(str(tag))
        
        # Extract music
        music = item.get('musicMeta', {})
        if music:
            all_music.append(music.get('musicName', ''))
    
    hashtag_counts = Counter([h for h in all_hashtags if h])
    music_counts = Counter([m for m in all_music if m])
    creator_counts = Counter([c for c in creators if c])
    
    return {
        'username': username,
        'total_videos': len(videos),
        'videos': videos,
        'top_hashtags': dict(hashtag_counts.most_common(30)),
        'top_music': dict(music_counts.most_common(20)),
        'reposts': reposts,
        'repost_patterns': {
            'total_reposts': len(reposts),
            'repost_percentage': (len(reposts) / len(videos) * 100) if videos else 0,
            'favorite_creators': list(creator_counts.most_common(10))
        }
    }

# ============================================================================
# PINTEREST DATA FETCHING (Unchanged)
# ============================================================================

def fetch_pinterest_data(pinterest_platform_data):
    """
    Fetch Pinterest boards and pins for a connected user
    """
    access_token = pinterest_platform_data.get('access_token')
    if not access_token:
        return {}
    
    try:
        boards = fetch_pinterest_boards(access_token)
        pins = fetch_pinterest_pins(access_token)
        
        return {
            'boards': boards[:20],
            'pins': pins[:100],
            'board_count': len(boards),
            'pin_count': len(pins),
            'connected': True
        }
    except Exception as e:
        print(f"Error fetching Pinterest data: {e}")
        return {'connected': True, 'error': str(e)}


def fetch_pinterest_boards(access_token):
    """Fetch user's Pinterest boards"""
    try:
        all_boards = []
        bookmark = None
        
        for _ in range(5):
            params = {'page_size': 25}
            if bookmark:
                params['bookmark'] = bookmark
            
            response = requests.get(
                f"{PINTEREST_API_URL}/boards",
                headers={'Authorization': f'Bearer {access_token}'},
                params=params
            )
            
            if response.status_code != 200:
                print(f"Pinterest boards error: {response.text}")
                break
            
            data = response.json()
            boards = data.get('items', [])
            
            if not boards:
                break
                
            all_boards.extend(boards)
            
            bookmark = data.get('bookmark')
            if not bookmark:
                break
        
        return all_boards
    
    except Exception as e:
        print(f"Error fetching Pinterest boards: {e}")
        return []


def fetch_pinterest_pins(access_token, max_pins=100):
    """Fetch user's Pinterest pins"""
    try:
        all_pins = []
        bookmark = None
        
        while len(all_pins) < max_pins:
            params = {'page_size': 25}
            if bookmark:
                params['bookmark'] = bookmark
            
            response = requests.get(
                f"{PINTEREST_API_URL}/pins",
                headers={'Authorization': f'Bearer {access_token}'},
                params=params
            )
            
            if response.status_code != 200:
                print(f"Pinterest pins error: {response.text}")
                break
            
            data = response.json()
            pins = data.get('items', [])
            
            if not pins:
                break
                
            all_pins.extend(pins)
            
            bookmark = data.get('bookmark')
            if not bookmark:
                break
        
        return all_pins[:max_pins]
    
    except Exception as e:
        print(f"Error fetching Pinterest pins: {e}")
        return []


def fetch_pinterest_user_info(access_token):
    """Fetch user's basic Pinterest profile info"""
    try:
        response = requests.get(
            f"{PINTEREST_API_URL}/user_account",
            headers={'Authorization': f'Bearer {access_token}'}
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Pinterest user info error: {response.text}")
            return {}
    except Exception as e:
        print(f"Error fetching Pinterest user info: {e}")
        return {}

# ============================================================================
# ROUTES - Landing Page & Marketing
# ============================================================================

@app.route('/')
def index():
    """Landing page"""
    return render_template('index.html')

@app.route('/how-it-works')
def how_it_works():
    """Detailed explanation page"""
    return render_template('how_it_works.html')

@app.route('/privacy')
def privacy_policy():
    """Privacy policy page"""
    return render_template('privacy.html')

# ============================================================================
# ROUTES - User Onboarding WITH SIMPLIFIED RECIPIENT SELECTION
# ============================================================================

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """User signup flow with simplified recipient selection"""
    if request.method == 'POST':
        email = request.form.get('email')
        recipient_type = request.form.get('recipient_type')  # 'myself' or 'someone_else'
        relationship = request.form.get('relationship', '')  # Only if someone_else
        
        # Map simplified relationship to backend category
        if relationship in RELATIONSHIP_MAPPING:
            relationship = RELATIONSHIP_MAPPING[relationship]
        
        # Create user in database
        user_id = email  # Simple user ID for MVP
        user_data = {
            'email': email,
            'created_at': datetime.now().isoformat(),
            'recipient_type': recipient_type,
            'platforms': {}
        }
        
        if recipient_type == 'someone_else' and relationship:
            user_data['relationship'] = relationship
        
        save_user(user_id, user_data)
        
        # Set session
        session['user_id'] = user_id
        
        return redirect('/connect-platforms')
    
    return render_template('signup.html', relationships=RELATIONSHIP_OPTIONS)

# ============================================================================
# ROUTES - Platform Connections WITH PROGRESS TRACKING
# ============================================================================

@app.route('/connect-platforms')
def connect_platforms():
    """Platform connection page"""
    user = get_session_user()
    if not user:
        return redirect('/signup')
    
    recipient_type = user.get('recipient_type', 'myself')
    
    # Determine platform access (for pro features)
    platform_access = {
        'instagram': True,
        'pinterest': True,  # Set to False if pro-only
        'tiktok': True,     # Set to False if pro-only
        'spotify': False
    }
    
    return render_template('connect_platforms.html',
                         user=user,
                         recipient_type=recipient_type,
                         platform_status=PLATFORM_STATUS,
                         platform_access=platform_access)

# ============================================================================
# PINTEREST OAUTH (Unchanged)
# ============================================================================

@app.route('/oauth/pinterest/start')
def pinterest_oauth_start():
    """Initiate Pinterest OAuth flow"""
    user = get_session_user()
    if not user:
        return redirect('/signup')
    
    params = {
        'client_id': PINTEREST_CLIENT_ID,
        'redirect_uri': PINTEREST_REDIRECT_URI,
        'response_type': 'code',
        'scope': 'boards:read,pins:read,user_accounts:read'
    }
    
    import urllib.parse
    query_string = urllib.parse.urlencode(params)
    authorization_url = f"{PINTEREST_AUTH_URL}?{query_string}"
    
    print(f"Pinterest OAuth start - redirecting to: {authorization_url}")
    
    return redirect(authorization_url)

@app.route('/oauth/pinterest/callback')
def pinterest_oauth_callback():
    """Handle Pinterest OAuth callback and fetch data"""
    user = get_session_user()
    if not user:
        return redirect('/signup')
    
    code = request.args.get('code')
    error = request.args.get('error')
    
    if error:
        print(f"Pinterest OAuth error from Pinterest: {error}")
        return redirect(f'/connect-platforms?error=pinterest_{error}')
    
    if not code:
        print("Pinterest callback: No code provided")
        return redirect('/connect-platforms?error=pinterest_no_code')
    
    try:
        print(f"Attempting Pinterest token exchange...")
        
        response = requests.post(
            PINTEREST_TOKEN_URL, 
            data={
                'grant_type': 'authorization_code',
                'code': code,
                'redirect_uri': PINTEREST_REDIRECT_URI
            },
            auth=(PINTEREST_CLIENT_ID, PINTEREST_CLIENT_SECRET),
            headers={
                'Content-Type': 'application/x-www-form-urlencoded'
            }
        )
        
        print(f"Pinterest token response status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"Pinterest token error: {response.text}")
            return redirect('/connect-platforms?error=pinterest_token_failed')
        
        token_data = response.json()
        access_token = token_data.get('access_token')
        
        if not access_token:
            print("Pinterest: No access token in response")
            return redirect('/connect-platforms?error=pinterest_no_token')
        
        print("Pinterest: Token received, fetching data...")
        
        # Fetch Pinterest data immediately
        user_info = fetch_pinterest_user_info(access_token)
        boards = fetch_pinterest_boards(access_token)
        pins = fetch_pinterest_pins(access_token)
        
        print(f"Pinterest: Fetched {len(boards)} boards and {len(pins)} pins")
        
        # Save everything to database
        platforms = user.get('platforms', {})
        platforms['pinterest'] = {
            'access_token': access_token,
            'refresh_token': token_data.get('refresh_token'),
            'connected_at': datetime.now().isoformat(),
            'user_info': user_info,
            'boards': boards[:10],
            'pins': pins[:50],
            'total_boards': len(boards),
            'total_pins': len(pins)
        }
        
        save_user(session['user_id'], {'platforms': platforms})
        
        print("Pinterest: Successfully connected!")
        return redirect('/connect-platforms?success=pinterest')
    
    except Exception as e:
        print(f"Pinterest OAuth exception: {str(e)}")
        import traceback
        traceback.print_exc()
        return redirect('/connect-platforms?error=pinterest_exception')

# ============================================================================
# INSTAGRAM - PUBLIC SCRAPING WITH PROGRESS
# ============================================================================

@app.route('/connect/instagram', methods=['POST'])
def connect_instagram():
    """Connect Instagram via username and scrape with Apify - WITH PROGRESS"""
    user = get_session_user()
    if not user:
        return redirect('/signup')
    
    username = request.form.get('username', '').strip().replace('@', '')
    
    if not username:
        return redirect('/connect-platforms?error=instagram_no_username')
    
    # Generate unique task ID
    task_id = str(uuid.uuid4())
    
    # Get user_id BEFORE starting thread (request context available here)
    user_id = session['user_id']
    
    # Start scraping in background thread
    def scrape_task():
        instagram_data = scrape_instagram_profile(username, max_posts=50, task_id=task_id)
        
        if instagram_data:
            # Save to database using passed user_id (no session access needed)
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

# ============================================================================
# TIKTOK - PUBLIC SCRAPING WITH PROGRESS
# ============================================================================

@app.route('/connect/tiktok', methods=['POST'])
def connect_tiktok():
    """Connect TikTok via username and scrape with Apify - WITH PROGRESS"""
    user = get_session_user()
    if not user:
        return redirect('/signup')
    
    username = request.form.get('username', '').strip().lstrip('@')
    
    if not username:
        return redirect('/connect-platforms?error=tiktok_no_username')
    
    # Generate unique task ID
    task_id = str(uuid.uuid4())
    
    # Get user_id BEFORE starting thread (request context available here)
    user_id = session['user_id']
    
    # Start scraping in background thread
    def scrape_task():
        tiktok_data = scrape_tiktok_profile(username, max_videos=50, task_id=task_id)
        
        if tiktok_data:
            # Save to database using passed user_id (no session access needed)
            user = get_user(user_id)
            platforms = user.get('platforms', {})
            platforms['tiktok'] = {
                'username': username,
                'connected_at': datetime.now().isoformat(),
                'method': 'scraping',
                'data': tiktok_data
            }
            save_user(session['user_id'], {'platforms': platforms})
    
    thread = threading.Thread(target=scrape_task)
    thread.daemon = True
    thread.start()
    
    # Redirect to progress page
    return redirect(f'/connect-progress/tiktok/{task_id}')

# ============================================================================
# PROGRESS PAGE
# ============================================================================

@app.route('/connect-progress/<platform>/<task_id>')
def show_progress(platform, task_id):
    """Show progress page while scraping"""
    return render_template('scraping_progress.html', 
                         platform=platform,
                         task_id=task_id)

# ============================================================================
# DISCONNECT PLATFORMS
# ============================================================================

@app.route('/disconnect/<platform>')
def disconnect_platform(platform):
    """Disconnect a platform"""
    user = get_session_user()
    if not user:
        return redirect('/signup')
    
    platforms = user.get('platforms', {})
    if platform in platforms:
        del platforms[platform]
        save_user(session['user_id'], {'platforms': platforms})
    
    return redirect('/connect-platforms?disconnected=' + platform)

# ============================================================================
# GENERATE RECOMMENDATIONS - WITH MINIMUM PLATFORM CHECK
# ============================================================================

@app.route('/generate-recommendations')
def generate_recommendations_route():
    """Generate gift recommendations from connected platforms"""
    user = get_session_user()
    if not user:
        return redirect('/signup')
    
    platforms = user.get('platforms', {})
    
    # Require at least 1 platform (updated from 2 - lower barrier)
    if len(platforms) < 1:
        return redirect('/connect-platforms?error=need_platforms')
    
    # Show loading page
    return render_template('generating.html', platforms=list(platforms.keys()))

@app.route('/api/generate-recommendations', methods=['POST'])
def api_generate_recommendations():
    """API endpoint to generate recommendations using all platform data"""
    user = get_session_user()
    if not user:
        return jsonify({'error': 'Not logged in'}), 401
    
    try:
        platforms = user.get('platforms', {})
        recipient_type = user.get('recipient_type', 'myself')
        relationship = user.get('relationship', '')
        
        # Build comprehensive platform data summary (keeping your existing logic)
        platform_insights = []
        
        # Pinterest data
        if 'pinterest' in platforms:
            pinterest = platforms['pinterest']
            boards = pinterest.get('boards', [])
            pins = pinterest.get('pins', [])
            
            board_names = [b.get('name', '') for b in boards if b.get('name')]
            pin_descriptions = [p.get('description', '')[:200] for p in pins[:30] if p.get('description')]
            
            platform_insights.append(f"""
PINTEREST DATA ({pinterest.get('total_boards', 0)} boards, {pinterest.get('total_pins', 0)} pins):
- Board Names: {', '.join(board_names[:20])}
- Key Interests from Pins: {'; '.join(pin_descriptions[:15])}
""")
        
        # Instagram data
        if 'instagram' in platforms:
            instagram = platforms['instagram'].get('data', {})
            if instagram and instagram.get('posts'):
                posts = instagram['posts']
                captions = [p['caption'][:150] for p in posts[:20] if p.get('caption')]
                
                platform_insights.append(f"""
INSTAGRAM DATA ({instagram.get('total_posts', 0)} posts analyzed):
- Username: @{instagram.get('username', 'unknown')}
- Post Themes: {'; '.join(captions[:15])}
- Engagement Style: {"High engagement" if instagram.get('followers', 0) > 1000 else "Personal account"}
""")
        
        # TikTok data with repost intelligence
        if 'tiktok' in platforms:
            tiktok = platforms['tiktok'].get('data', {})
            if tiktok and tiktok.get('videos'):
                videos = tiktok['videos']
                descriptions = [v['description'][:150] for v in videos[:20] if v.get('description')]
                reposts = tiktok.get('reposts', [])
                repost_patterns = tiktok.get('repost_patterns', {})
                favorite_creators = repost_patterns.get('favorite_creators', [])
                
                creator_insights = ""
                if favorite_creators:
                    creator_list = [f"@{creator[0]} ({creator[1]} reposts)" for creator in favorite_creators[:5]]
                    creator_insights = f"\n- Frequently Reposts From: {', '.join(creator_list)}"
                    creator_insights += f"\n- This suggests affinity for: content styles, values, and product categories these creators represent"
                
                platform_insights.append(f"""
TIKTOK DATA ({tiktok.get('total_videos', 0)} videos analyzed):
- Username: @{tiktok.get('username', 'unknown')}
- Video Themes: {'; '.join(descriptions[:15])}
- Repost Behavior: {repost_patterns.get('total_reposts', 0)} reposts out of {tiktok.get('total_videos', 0)} total videos{creator_insights}
- Key Insight: Reposts reveal deeper interests - what they choose to amplify shows what resonates most
""")
        
        # Build relationship context
        relationship_context = ""
        if recipient_type == 'someone_else':
            relationship_map = {
                'romantic_partner': "This is for a romantic partner - focus on thoughtful, personal gifts that show deep understanding",
                'close_friend': "This is for a close friend - prioritize fun, meaningful gifts that strengthen the friendship",
                'family_member': "This is for a family member - consider practical yet heartfelt gifts",
                'coworker': "This is for a coworker - keep it professional but thoughtful",
                'acquaintance': "This is for an acquaintance - opt for tasteful, universally appealing gifts",
                'other': "Consider the nature of the relationship when selecting gifts"
            }
            relationship_context = f"\n\nRELATIONSHIP CONTEXT:\n{relationship_map.get(relationship, '')}"
        
        # Build comprehensive prompt (keeping your existing prompt)
        prompt = f"""You are an expert gift curator. Based on the following social media data, generate 10 highly specific, actionable gift recommendations.

USER DATA:
{chr(10).join(platform_insights)}{relationship_context}

CRITICAL INSTRUCTIONS:
1. Prioritize UNIQUE, SPECIALTY items over generic mass-market products
2. Focus on independent makers, artisan shops, and unique experiences
3. Each recommendation MUST include a REAL, WORKING purchase link - DO NOT generate placeholder URLs
4. For purchase links: Search for actual products on Etsy, UncommonGoods, or specialty retailers and provide their EXACT URLs
5. If you cannot find a specific product URL, use a search URL format like: https://www.etsy.com/search?q=specific+product+name
6. Balance quality with affiliate potential - NEVER recommend generic Amazon items just for easy commission
7. Use TikTok repost patterns to identify deeper interests - what they choose to amplify reveals what truly resonates
8. Look for the special, thoughtful items that show you really understand them
9. BE SPECIFIC: Instead of "vintage record player", say "Crosley C6 Belt-Drive Turntable in Cherry" with exact URL
10. VERIFY PRODUCTS EXIST: Only recommend items you can find real links for

PRICE DISTRIBUTION:
- 3-4 items in $20-50 range
- 3-4 items in $50-100 range
- 2-3 items in $100-200 range

Return EXACTLY 10 recommendations as a JSON array with this structure:
[
  {{
    "name": "SPECIFIC product or experience name with brand/model",
    "description": "2-3 sentence description of what this is and why it's special",
    "why_perfect": "Why this matches their interests based on specific social media signals",
    "price_range": "$XX-$XX",
    "where_to_buy": "Specific retailer name (Etsy shop name, UncommonGoods, etc)",
    "purchase_link": "https://REAL-WORKING-URL.com (NOT a placeholder - must be actual product page or search URL)",
    "gift_type": "physical" or "experience",
    "confidence_level": "safe_bet" or "adventurous"
  }}
]

IMPORTANT: Return ONLY the JSON array. No markdown, no backticks, no explanatory text."""

        print(f"Generating recommendations for user: {user.get('email', 'unknown')}")
        print(f"Using platforms: {list(platforms.keys())}")
        print(f"Recipient type: {recipient_type}, Relationship: {relationship}")
        
        # Call Claude API
        message = claude_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=6000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        # Get response text
        response_text = message.content[0].text.strip()
        
        print(f"Claude response received, length: {len(response_text)}")
        
        # Parse JSON response
        try:
            # Remove markdown code fences if present
            if response_text.startswith('```'):
                response_text = response_text.split('```')[1]
                if response_text.startswith('json'):
                    response_text = response_text[4:]
                response_text = response_text.strip()
            
            recommendations = json.loads(response_text)
            print(f"Successfully parsed {len(recommendations)} recommendations")
            
        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}")
            # Fallback if parsing fails
            recommendations = [{
                'name': 'Recommendations generated',
                'description': response_text[:500],
                'why_perfect': 'See full response',
                'price_range': 'Various',
                'where_to_buy': 'Various retailers',
                'purchase_link': '',
                'gift_type': 'physical',
                'confidence_level': 'safe_bet'
            }]
        
        # Save recommendations to user
        save_user(session['user_id'], {
            'recommendations': recommendations,
            'last_generated': datetime.now().isoformat()
        })
        
        return jsonify({
            'success': True,
            'recommendations': recommendations
        })
        
    except Exception as e:
        print(f"Recommendation generation error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ============================================================================
# VIEW RECOMMENDATIONS
# ============================================================================

@app.route('/recommendations')
def view_recommendations():
    """Display recommendations with filters"""
    user = get_session_user()
    if not user:
        return redirect('/signup')
    
    recommendations = user.get('recommendations', [])
    
    if not recommendations:
        return redirect('/connect-platforms?error=no_recommendations')
    
    return render_template('recommendations.html', 
                         recommendations=recommendations,
                         user=user)

# ============================================================================
# FEEDBACK SYSTEM (Unchanged)
# ============================================================================

@app.route('/feedback', methods=['GET', 'POST'])
def feedback():
    """Feedback survey page"""
    user = get_session_user()
    
    if request.method == 'POST':
        feedback_data = {
            'landing_page': request.form.get('landing_page'),
            'connection_flow': request.form.get('connection_flow'),
            'recommendation_quality': request.form.get('recommendation_quality'),
            'would_pay': request.form.get('would_pay'),
            'price_point': request.form.get('price_point'),
            'free_response': request.form.get('free_response'),
            'submitted_at': datetime.now().isoformat()
        }
        
        session['feedback_draft'] = feedback_data
        
        if user:
            user_id = session.get('user_id')
            existing_feedback = user.get('feedback_history', [])
            existing_feedback.append(feedback_data)
            
            save_user(user_id, {
                'feedback_history': existing_feedback,
                'latest_feedback': feedback_data
            })
        
        return render_template('feedback.html', success=True)
    
    existing_feedback = session.get('feedback_draft', {})
    return render_template('feedback.html', existing_feedback=existing_feedback)

@app.route('/admin/feedback')
def admin_feedback():
    """View all feedback (debug mode only)"""
    if not app.debug:
        return "Unauthorized", 403
    
    all_feedback = []
    
    with shelve.open('giftwise_db') as db:
        for key in db.keys():
            if key.startswith('user_'):
                user_data = db[key]
                feedback_history = user_data.get('feedback_history', [])
                
                for feedback in feedback_history:
                    all_feedback.append({
                        'user_email': user_data.get('email', 'Anonymous'),
                        'feedback': feedback
                    })
    
    all_feedback.sort(key=lambda x: x['feedback'].get('submitted_at', ''), reverse=True)
    
    return jsonify(all_feedback)

# ============================================================================
# ADMIN / UTILS
# ============================================================================

@app.route('/logout')
def logout():
    """Logout user"""
    session.clear()
    return redirect('/')

@app.route('/debug/user')
def debug_user():
    """Debug: View current user data"""
    if not app.debug:
        return "Debug mode only", 403
    
    user = get_session_user()
    return jsonify(user) if user else jsonify({'error': 'No user in session'})

# ============================================================================
# RUN APPLICATION
# ============================================================================

if __name__ == '__main__':
    app.run(debug=True, port=5000)
