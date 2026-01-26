"""
GIFTWISE MAIN APPLICATION
AI-Powered Gift Recommendations from Social Media

CURRENT PLATFORM STATUS (January 2026):
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
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, session, jsonify, url_for
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
APIFY_INSTAGRAM_ACTOR = 'apify/instagram-post-scraper'  # Tested and working
APIFY_TIKTOK_ACTOR = 'clockworks/tiktok-profile-scraper'  # Tested and working

# Spotify (keeping for future)
SPOTIFY_CLIENT_ID = os.environ.get('SPOTIFY_CLIENT_ID', '')
SPOTIFY_CLIENT_SECRET = os.environ.get('SPOTIFY_CLIENT_SECRET', '')

# Initialize clients
stripe.api_key = STRIPE_SECRET_KEY
claude_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

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
# RELATIONSHIP CONTEXT OPTIONS
# ============================================================================

RELATIONSHIP_OPTIONS = [
    'romantic_partner',
    'close_friend',
    'family_member',
    'coworker',
    'acquaintance',
    'other'
]

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
# APIFY SCRAPING FUNCTIONS
# ============================================================================

def scrape_instagram_profile(username, max_posts=50):
    """
    Scrape Instagram profile using Apify
    Returns: dict with posts, captions, engagement data
    """
    if not APIFY_API_TOKEN:
        print("No Apify token configured")
        return None
    
    try:
        print(f"Starting Instagram scrape for @{username}")
        
        # Start Apify actor
        response = requests.post(
            f'https://api.apify.com/v2/acts/{APIFY_INSTAGRAM_ACTOR}/runs?token={APIFY_API_TOKEN}',
            json={
                'usernames': [username],
                'resultsLimit': max_posts
            }
        )
        
        if response.status_code != 201:
            print(f"Apify Instagram actor start failed: {response.text}")
            return None
        
        run_id = response.json()['data']['id']
        print(f"Instagram scrape started, run ID: {run_id}")
        
        # Poll for completion (max 2 minutes)
        for _ in range(24):  # 24 * 5 seconds = 2 minutes
            time.sleep(5)
            status_response = requests.get(
                f'https://api.apify.com/v2/actor-runs/{run_id}?token={APIFY_API_TOKEN}'
            )
            status = status_response.json()['data']['status']
            
            if status == 'SUCCEEDED':
                break
            elif status in ['FAILED', 'ABORTED', 'TIMED-OUT']:
                print(f"Instagram scrape failed with status: {status}")
                return None
        
        # Get results
        results_response = requests.get(
            f'https://api.apify.com/v2/actor-runs/{run_id}/dataset/items?token={APIFY_API_TOKEN}'
        )
        
        if results_response.status_code != 200:
            print(f"Failed to get Instagram results: {results_response.text}")
            return None
        
        data = results_response.json()
        print(f"Instagram scrape complete: {len(data)} items retrieved")
        
        # Parse and structure data
        if not data:
            return None
            
        profile = data[0] if data else {}
        posts = profile.get('latestPosts', [])[:max_posts]
        
        return {
            'username': username,
            'full_name': profile.get('fullName', ''),
            'bio': profile.get('biography', ''),
            'followers': profile.get('followersCount', 0),
            'posts': [
                {
                    'caption': post.get('caption', ''),
                    'likes': post.get('likesCount', 0),
                    'comments': post.get('commentsCount', 0),
                    'timestamp': post.get('timestamp', ''),
                    'type': post.get('type', 'image')
                }
                for post in posts
            ],
            'total_posts': len(posts),
            'scraped_at': datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"Instagram scraping error: {e}")
        import traceback
        traceback.print_exc()
        return None


def scrape_tiktok_profile(username, max_videos=50):
    """
    Scrape TikTok profile using Apify with repost intelligence
    Returns: dict with videos, reposts, creator patterns
    """
    if not APIFY_API_TOKEN:
        print("No Apify token configured")
        return None
    
    try:
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
            print(f"Apify TikTok actor start failed: {response.text}")
            return None
        
        run_id = response.json()['data']['id']
        print(f"TikTok scrape started, run ID: {run_id}")
        
        # Poll for completion (max 2 minutes)
        for _ in range(24):
            time.sleep(5)
            status_response = requests.get(
                f'https://api.apify.com/v2/actor-runs/{run_id}?token={APIFY_API_TOKEN}'
            )
            status = status_response.json()['data']['status']
            
            if status == 'SUCCEEDED':
                break
            elif status in ['FAILED', 'ABORTED', 'TIMED-OUT']:
                print(f"TikTok scrape failed with status: {status}")
                return None
        
        # Get results
        results_response = requests.get(
            f'https://api.apify.com/v2/actor-runs/{run_id}/dataset/items?token={APIFY_API_TOKEN}'
        )
        
        if results_response.status_code != 200:
            print(f"Failed to get TikTok results: {results_response.text}")
            return None
        
        data = results_response.json()
        print(f"TikTok scrape complete: {len(data)} items retrieved")
        
        if not data:
            return None
        
        # Analyze videos for repost patterns
        videos = data[:max_videos]
        reposts = []
        original_creators = {}
        
        for video in videos:
            is_repost = video.get('isRepost', False) or video.get('duetInfo') or video.get('stitchInfo')
            
            if is_repost:
                original_author = video.get('authorMeta', {}).get('name', 'unknown')
                reposts.append({
                    'description': video.get('text', ''),
                    'original_author': original_author,
                    'likes': video.get('diggCount', 0),
                    'shares': video.get('shareCount', 0)
                })
                
                # Track frequency of reposts from each creator
                if original_author not in original_creators:
                    original_creators[original_author] = {
                        'count': 0,
                        'total_engagement': 0
                    }
                original_creators[original_author]['count'] += 1
                original_creators[original_author]['total_engagement'] += video.get('diggCount', 0)
        
        return {
            'username': username,
            'videos': [
                {
                    'description': v.get('text', ''),
                    'likes': v.get('diggCount', 0),
                    'shares': v.get('shareCount', 0),
                    'plays': v.get('playCount', 0),
                    'is_repost': v.get('isRepost', False),
                    'hashtags': v.get('hashtags', [])
                }
                for v in videos
            ],
            'reposts': reposts,
            'repost_patterns': {
                'total_reposts': len(reposts),
                'favorite_creators': sorted(
                    original_creators.items(),
                    key=lambda x: x[1]['count'],
                    reverse=True
                )[:10]  # Top 10 creators they repost from
            },
            'total_videos': len(videos),
            'scraped_at': datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"TikTok scraping error: {e}")
        import traceback
        traceback.print_exc()
        return None

# ============================================================================
# PINTEREST DATA FETCHING
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
# ROUTES - User Onboarding WITH RECIPIENT SELECTION
# ============================================================================

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """User signup flow with recipient selection"""
    if request.method == 'POST':
        email = request.form.get('email')
        recipient_type = request.form.get('recipient_type')  # 'myself' or 'someone_else'
        relationship = request.form.get('relationship', '')  # Only if someone_else
        
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
# ROUTES - Platform Connections
# ============================================================================

@app.route('/connect-platforms')
def connect_platforms():
    """Platform connection page"""
    user = get_session_user()
    if not user:
        return redirect('/signup')
    
    return render_template('connect_platforms.html',
                         user=user,
                         platform_status=PLATFORM_STATUS)

# ============================================================================
# PINTEREST OAUTH
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
# INSTAGRAM - PUBLIC SCRAPING WITH APIFY
# ============================================================================

@app.route('/connect/instagram', methods=['POST'])
def connect_instagram():
    """Connect Instagram via username and scrape with Apify"""
    user = get_session_user()
    if not user:
        return redirect('/signup')
    
    username = request.form.get('username', '').strip().replace('@', '')
    
    if not username:
        return redirect('/connect-platforms?error=instagram_no_username')
    
    try:
        print(f"Scraping Instagram profile: @{username}")
        
        # Scrape Instagram data via Apify
        instagram_data = scrape_instagram_profile(username, max_posts=50)
        
        if not instagram_data:
            return redirect('/connect-platforms?error=instagram_scrape_failed')
        
        # Save to user platforms
        platforms = user.get('platforms', {})
        platforms['instagram'] = {
            'username': username,
            'connected_at': datetime.now().isoformat(),
            'method': 'scraping',
            'data': instagram_data
        }
        
        save_user(session['user_id'], {'platforms': platforms})
        
        print(f"Instagram connected: {instagram_data['total_posts']} posts scraped")
        return redirect('/connect-platforms?success=instagram')
    
    except Exception as e:
        print(f"Instagram connection error: {e}")
        import traceback
        traceback.print_exc()
        return redirect('/connect-platforms?error=instagram_failed')

# ============================================================================
# TIKTOK - PUBLIC SCRAPING WITH APIFY
# ============================================================================

@app.route('/connect/tiktok', methods=['POST'])
def connect_tiktok():
    """Connect TikTok via username and scrape with Apify"""
    user = get_session_user()
    if not user:
        return redirect('/signup')
    
    username = request.form.get('username', '').strip().lstrip('@')
    
    if not username:
        return redirect('/connect-platforms?error=tiktok_no_username')
    
    try:
        print(f"Scraping TikTok profile: @{username}")
        
        # Scrape TikTok data via Apify with repost analysis
        tiktok_data = scrape_tiktok_profile(username, max_videos=50)
        
        if not tiktok_data:
            return redirect('/connect-platforms?error=tiktok_scrape_failed')
        
        # Save to user platforms
        platforms = user.get('platforms', {})
        platforms['tiktok'] = {
            'username': username,
            'connected_at': datetime.now().isoformat(),
            'method': 'scraping',
            'data': tiktok_data
        }
        
        save_user(session['user_id'], {'platforms': platforms})
        
        print(f"TikTok connected: {tiktok_data['total_videos']} videos scraped, {tiktok_data['repost_patterns']['total_reposts']} reposts identified")
        return redirect('/connect-platforms?success=tiktok')
    
    except Exception as e:
        print(f"TikTok connection error: {e}")
        import traceback
        traceback.print_exc()
        return redirect('/connect-platforms?error=tiktok_failed')

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
# GENERATE RECOMMENDATIONS - ENHANCED WITH ALL PLATFORMS
# ============================================================================

@app.route('/generate-recommendations')
def generate_recommendations_route():
    """Generate gift recommendations from connected platforms"""
    user = get_session_user()
    if not user:
        return redirect('/signup')
    
    platforms = user.get('platforms', {})
    
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
        
        # Build comprehensive platform data summary
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
- Bio: {instagram.get('bio', '')}
- Post Themes: {'; '.join(captions[:15])}
- Engagement Style: {"High engagement" if instagram.get('followers', 0) > 1000 else "Personal account"}
""")
            else:
                platform_insights.append(f"""
INSTAGRAM DATA:
- Username: @{platforms['instagram'].get('username', 'unknown')}
- Data pending scrape
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
                    creator_list = [f"@{creator[0]} ({creator[1]['count']} reposts)" for creator in favorite_creators[:5]]
                    creator_insights = f"\n- Frequently Reposts From: {', '.join(creator_list)}"
                    creator_insights += f"\n- This suggests affinity for: content styles, values, and product categories these creators represent"
                
                platform_insights.append(f"""
TIKTOK DATA ({tiktok.get('total_videos', 0)} videos analyzed):
- Username: @{tiktok.get('username', 'unknown')}
- Video Themes: {'; '.join(descriptions[:15])}
- Repost Behavior: {repost_patterns.get('total_reposts', 0)} reposts out of {tiktok.get('total_videos', 0)} total videos{creator_insights}
- Key Insight: Reposts reveal deeper interests - what they choose to amplify shows what resonates most
""")
            else:
                platform_insights.append(f"""
TIKTOK DATA:
- Username: @{platforms['tiktok'].get('username', 'unknown')}
- Data pending scrape
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
        
        # Build comprehensive prompt
        prompt = f"""You are an expert gift curator. Based on the following social media data, generate 10 highly specific, actionable gift recommendations.

USER DATA:
{chr(10).join(platform_insights)}{relationship_context}

CRITICAL INSTRUCTIONS:
1. Prioritize UNIQUE, SPECIALTY items over generic mass-market products
2. Focus on independent makers, artisan shops, and unique experiences
3. Each recommendation MUST include a direct purchase link (actual URL)
4. Prioritize affiliate-friendly sources (Etsy, UncommonGoods, specialty retailers, experience platforms)
5. Balance quality with affiliate potential - NEVER recommend generic Amazon items just for easy commission
6. Use TikTok repost patterns to identify deeper interests - what they choose to amplify reveals what truly resonates
7. Look for the special, thoughtful items that show you really understand them

PRICE DISTRIBUTION:
- 3-4 items in $20-50 range
- 3-4 items in $50-100 range
- 2-3 items in $100-200 range

Return EXACTLY 10 recommendations as a JSON array with this structure:
[
  {{
    "name": "Specific product or experience name",
    "description": "2-3 sentence description of what this is and why it's special",
    "why_perfect": "Why this matches their interests based on specific social media signals",
    "price_range": "$XX-$XX",
    "where_to_buy": "Specific retailer name",
    "purchase_link": "https://actual-direct-link-to-product.com",
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
# FEEDBACK SYSTEM
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
