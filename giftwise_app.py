"""
GIFTWISE MAIN APPLICATION
AI-Powered Gift Recommendations from Social Media

CURRENT PLATFORM STATUS (January 2026):
✅ Pinterest - OAuth available (full data access)
✅ Instagram - Public scraping only (OAuth blocked by Meta)
✅ TikTok - Public scraping only (no OAuth available)
⏳ Spotify - OAuth blocked (not accepting new apps)

Author: Chad + Claude
Date: January 2026
"""

import os
import json
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

# Instagram - Public Scraping Only (OAuth not available)
APIFY_API_TOKEN = os.environ.get('APIFY_API_TOKEN')

# Spotify - Blocked (keeping config for future if they reopen)
SPOTIFY_CLIENT_ID = os.environ.get('SPOTIFY_CLIENT_ID', '')
SPOTIFY_CLIENT_SECRET = os.environ.get('SPOTIFY_CLIENT_SECRET', '')
SPOTIFY_REDIRECT_URI = os.environ.get('SPOTIFY_REDIRECT_URI', '')
SPOTIFY_AUTH_URL = 'https://accounts.spotify.com/authorize'
SPOTIFY_TOKEN_URL = 'https://accounts.spotify.com/api/token'
SPOTIFY_API_URL = 'https://api.spotify.com/v1'

# Instagram (keeping for reference, not used)
INSTAGRAM_AUTH_URL = 'https://api.instagram.com/oauth/authorize'
INSTAGRAM_TOKEN_URL = 'https://api.instagram.com/oauth/access_token'
INSTAGRAM_API_URL = 'https://graph.instagram.com/me'

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
        'status': 'Public profile data only',
        'icon': '📷',
        'color': '#E1306C',
        'note': 'OAuth blocked by Meta - using public data only'
    },
    'tiktok': {
        'available': True,
        'method': 'scraping',
        'status': 'Public profile data only',
        'icon': '🎬',
        'color': '#000000',
        'note': 'No OAuth available - using public data only'
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
# SIMPLIFIED PRICING (NO FREEMIUM FOR NOW)
# ============================================================================

# Pricing to be determined based on user feedback
# For now, everything is available to all users during testing phase

PRICING = {
    'testing_phase': True,  # Set to False when ready to charge
    'target_price': None,   # Will be set based on feedback (likely $3-10/month)
    'features': {
        'all_platforms': True,
        'unlimited_recommendations': True,
        'monthly_updates': True
    }
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
# PINTEREST DATA FETCHING
# ============================================================================

def fetch_pinterest_data(pinterest_platform_data):
    """
    Fetch Pinterest boards and pins for a connected user
    
    Args:
        pinterest_platform_data: Dict containing access_token and other Pinterest data
    
    Returns:
        Dict with boards and pins data ready for recommendation engine
    """
    access_token = pinterest_platform_data.get('access_token')
    if not access_token:
        return {}
    
    try:
        # Fetch boards
        boards = fetch_pinterest_boards(access_token)
        
        # Fetch pins (sample from different boards)
        pins = fetch_pinterest_pins(access_token)
        
        return {
            'boards': boards[:20],  # Top 20 boards
            'pins': pins[:100],     # Top 100 pins
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
        
        # Pinterest uses cursor-based pagination
        for _ in range(5):  # Limit to 5 pages max
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
            
            # Check if there are more pages
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
        
        # Fetch pins (Pinterest returns user's saved pins)
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
            
            # Check if there are more pages
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
# ROUTES - User Onboarding
# ============================================================================

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """User signup flow - simplified without tier selection"""
    if request.method == 'POST':
        email = request.form.get('email')
        referrer = request.form.get('referrer', '')
        
        # Create user in database
        user_id = email  # Simple user ID for MVP
        save_user(user_id, {
            'email': email,
            'created_at': datetime.now().isoformat(),
            'referrer': referrer,
            'platforms': {}
        })
        
        # Set session
        session['user_id'] = user_id
        
        return redirect('/connect-platforms')
    
    return render_template('signup.html')

# ============================================================================
# ROUTES - Platform Connections
# ============================================================================

@app.route('/connect-platforms')
def connect_platforms():
    """Platform connection page - simplified without tier restrictions"""
    user = get_session_user()
    if not user:
        return redirect('/signup')
    
    # Pass platform availability status to template
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
    
    # Pinterest OAuth parameters
    params = {
        'client_id': PINTEREST_CLIENT_ID,
        'redirect_uri': PINTEREST_REDIRECT_URI,
        'response_type': 'code',
        'scope': 'boards:read,pins:read,user_accounts:read'
    }
    
    # Build authorization URL manually
    import urllib.parse
    query_string = urllib.parse.urlencode(params)
    authorization_url = f"{PINTEREST_AUTH_URL}?{query_string}"
    
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
        # Exchange code for access token - send credentials in POST body
        print(f"Attempting Pinterest token exchange...")
        print(f"Redirect URI: {PINTEREST_REDIRECT_URI}")
        
        response = requests.post(
            PINTEREST_TOKEN_URL, 
            data={
                'grant_type': 'authorization_code',
                'code': code,
                'redirect_uri': PINTEREST_REDIRECT_URI,
                'client_id': PINTEREST_CLIENT_ID,
                'client_secret': PINTEREST_CLIENT_SECRET
            },
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
            'boards': boards[:10],  # Save first 10 boards
            'pins': pins[:50],      # Save first 50 pins
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
# INSTAGRAM - PUBLIC SCRAPING (USERNAME INPUT)
# ============================================================================

@app.route('/connect/instagram', methods=['POST'])
def connect_instagram():
    """Connect Instagram via username (public scraping)"""
    user = get_session_user()
    if not user:
        return redirect('/signup')
    
    username = request.form.get('username', '').strip().replace('@', '')
    
    if not username:
        return redirect('/connect-platforms?error=instagram_no_username')
    
    try:
        # Save Instagram username (scraping happens during recommendation generation)
        platforms = user.get('platforms', {})
        platforms['instagram'] = {
            'username': username,
            'connected_at': datetime.now().isoformat(),
            'method': 'scraping'
        }
        
        save_user(session['user_id'], {'platforms': platforms})
        
        return redirect('/connect-platforms?success=instagram')
    
    except Exception as e:
        print(f"Instagram connection error: {e}")
        return redirect('/connect-platforms?error=instagram_failed')

# ============================================================================
# TIKTOK - PUBLIC SCRAPING (USERNAME INPUT)
# ============================================================================

@app.route('/connect/tiktok', methods=['POST'])
def connect_tiktok():
    """Connect TikTok via username (public scraping)"""
    user = get_session_user()
    if not user:
        return redirect('/signup')
    
    username = request.form.get('username', '').strip().lstrip('@')
    
    if not username:
        return redirect('/connect-platforms?error=tiktok_no_username')
    
    # Save TikTok username (scraping happens during recommendation generation)
    platforms = user.get('platforms', {})
    platforms['tiktok'] = {
        'username': username,
        'method': 'scraping',
        'connected_at': datetime.now().isoformat()
    }
    
    save_user(session['user_id'], {'platforms': platforms})
    
    return redirect('/connect-platforms?success=tiktok')

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
# GENERATE RECOMMENDATIONS
# ============================================================================

@app.route('/generate-recommendations')
def generate_recommendations_route():
    """Generate gift recommendations from connected platforms"""
    user = get_session_user()
    if not user:
        return redirect('/signup')
    
    platforms = user.get('platforms', {})
    
    if len(platforms) < 2:
        return redirect('/connect-platforms?error=need_more_platforms')
    
    # Show loading page
    return render_template('generating.html', platforms=list(platforms.keys()))

@app.route('/api/generate-recommendations', methods=['POST'])
def api_generate_recommendations():
    """API endpoint to actually generate recommendations"""
    user = get_session_user()
    if not user:
        return jsonify({'error': 'Not logged in'}), 401
    
    try:
        # Import platform-specific data fetchers
        from platform_integrations import (
            fetch_instagram_data,
            fetch_spotify_data,
            fetch_tiktok_data
        )
        from recommendation_engine import generate_multi_platform_recommendations
        
        platforms = user.get('platforms', {})
        all_data = {}
        
        # Fetch data from each connected platform (no tier restrictions)
        if 'instagram' in platforms:
            all_data['instagram'] = fetch_instagram_data(platforms['instagram'])
        
        if 'spotify' in platforms:
            all_data['spotify'] = fetch_spotify_data(platforms['spotify'])
        
        if 'pinterest' in platforms:
            all_data['pinterest'] = fetch_pinterest_data(platforms['pinterest'])
        
        if 'tiktok' in platforms:
            all_data['tiktok'] = fetch_tiktok_data(platforms['tiktok'], APIFY_API_TOKEN)
        
        # Generate recommendations (no max limit during testing)
        recommendations = generate_multi_platform_recommendations(
            all_data,
            user.get('email', 'user'),
            claude_client,
            max_recommendations=10  # Fixed at 10 for testing
        )
        
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
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ============================================================================
# VIEW RECOMMENDATIONS
# ============================================================================

@app.route('/recommendations')
def view_recommendations():
    """Display recommendations - simplified without tier checking"""
    user = get_session_user()
    if not user:
        return redirect('/signup')
    
    recommendations = user.get('recommendations', [])
    
    if not recommendations:
        return redirect('/connect-platforms?error=no_recommendations')
    
    # All users get all recommendations (no tier limits)
    return render_template('recommendations.html', 
                         recommendations=recommendations,
                         user=user)

# ============================================================================
# PUBLIC SHAREABLE PROFILES (Keep for future)
# ============================================================================

@app.route('/u/<username>')
def public_profile(username):
    """Public shareable gift profile - anyone can view without login"""
    # Find user by username
    user_found = None
    with shelve.open('giftwise_db') as db:
        for key in db.keys():
            if key.startswith('user_'):
                user_data = db[key]
                # Create username from email
                import re
                user_username = re.sub(r'[^a-z0-9]', '', user_data.get('email', '').split('@')[0].lower())
                if user_username == username:
                    user_found = user_data
                    break
    
    if not user_found:
        return render_template('profile_not_found.html', username=username)
    
    recommendations = user_found.get('recommendations', [])
    if not recommendations:
        return render_template('profile_no_recs.html', username=username)
    
    # Get user's first name (from email or set a default)
    display_name = user_found.get('name') or user_found.get('email', '').split('@')[0].title()
    
    return render_template('public_profile.html',
                         recommendations=recommendations,
                         display_name=display_name,
                         username=username,
                         platforms=list(user_found.get('platforms', {}).keys()))

# ============================================================================
# FEEDBACK SYSTEM
# ============================================================================

@app.route('/feedback', methods=['GET', 'POST'])
def feedback():
    """Feedback survey page with session persistence"""
    user = get_session_user()
    
    if request.method == 'POST':
        # Get all form data
        feedback_data = {
            'landing_page': request.form.get('landing_page'),
            'connection_flow': request.form.get('connection_flow'),
            'recommendation_quality': request.form.get('recommendation_quality'),
            'would_pay': request.form.get('would_pay'),
            'price_point': request.form.get('price_point'),
            'free_response': request.form.get('free_response'),
            'submitted_at': datetime.now().isoformat()
        }
        
        # Store in session for persistence
        session['feedback_draft'] = feedback_data
        
        # Save to database if user is logged in
        if user:
            user_id = session.get('user_id')
            
            # Get existing feedback or create new
            existing_feedback = user.get('feedback_history', [])
            existing_feedback.append(feedback_data)
            
            save_user(user_id, {
                'feedback_history': existing_feedback,
                'latest_feedback': feedback_data
            })
        
        # Show success message
        return render_template('feedback.html', success=True)
    
    # GET request - show form with any existing draft
    existing_feedback = session.get('feedback_draft', {})
    
    return render_template('feedback.html', existing_feedback=existing_feedback)


@app.route('/admin/feedback')
def admin_feedback():
    """View all feedback (admin only - add authentication later)"""
    # For now, just require debug mode
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
    
    # Sort by most recent
    all_feedback.sort(key=lambda x: x['feedback'].get('submitted_at', ''), reverse=True)
    
    return jsonify(all_feedback)

# ============================================================================
# STRIPE WEBHOOK (Keep for future, but not used during testing)
# ============================================================================

@app.route('/stripe-webhook', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhook events - kept for future use"""
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')
    
    # Not implementing during testing phase
    # Will activate when ready to charge
    
    return jsonify({'success': True}), 200

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
