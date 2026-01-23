"""
GIFTWISE MAIN APPLICATION
OAuth Integration + Multi-Platform Gift Recommendations

Platforms:
- Instagram (OAuth)
- Spotify (OAuth)
- Pinterest (OAuth)
- TikTok (Public scraping fallback)

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

# OAuth Configuration
INSTAGRAM_CLIENT_ID = os.environ.get('INSTAGRAM_CLIENT_ID')
INSTAGRAM_CLIENT_SECRET = os.environ.get('INSTAGRAM_CLIENT_SECRET')
INSTAGRAM_REDIRECT_URI = os.environ.get('INSTAGRAM_REDIRECT_URI', 'http://localhost:5000/oauth/instagram/callback')

SPOTIFY_CLIENT_ID = os.environ.get('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.environ.get('SPOTIFY_CLIENT_SECRET')
SPOTIFY_REDIRECT_URI = os.environ.get('SPOTIFY_REDIRECT_URI', 'http://localhost:5000/oauth/spotify/callback')

PINTEREST_CLIENT_ID = os.environ.get('PINTEREST_CLIENT_ID')
PINTEREST_CLIENT_SECRET = os.environ.get('PINTEREST_CLIENT_SECRET')
PINTEREST_REDIRECT_URI = os.environ.get('PINTEREST_REDIRECT_URI', 'http://localhost:5000/oauth/pinterest/callback')

APIFY_API_TOKEN = os.environ.get('APIFY_API_TOKEN')

# Initialize clients
stripe.api_key = STRIPE_SECRET_KEY
claude_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# OAuth Endpoints
INSTAGRAM_AUTH_URL = 'https://api.instagram.com/oauth/authorize'
INSTAGRAM_TOKEN_URL = 'https://api.instagram.com/oauth/access_token'
INSTAGRAM_API_URL = 'https://graph.instagram.com/me'

SPOTIFY_AUTH_URL = 'https://accounts.spotify.com/authorize'
SPOTIFY_TOKEN_URL = 'https://accounts.spotify.com/api/token'
SPOTIFY_API_URL = 'https://api.spotify.com/v1'

PINTEREST_AUTH_URL = 'https://www.pinterest.com/oauth/'
PINTEREST_TOKEN_URL = 'https://api.pinterest.com/v5/oauth/token'
PINTEREST_API_URL = 'https://api.pinterest.com/v5'

# ============================================================================
# FEATURE FLAGS (Enable/disable features without deploying)
# ============================================================================

FEATURE_FLAGS = {
    'youtube_integration': os.environ.get('FEATURE_YOUTUBE', 'False') == 'True',
    'goodreads_integration': os.environ.get('FEATURE_GOODREADS', 'False') == 'True',
    'friend_network': os.environ.get('FEATURE_FRIENDS', 'False') == 'True',
    'gift_emergency': os.environ.get('FEATURE_GIFT_EMERGENCY', 'False') == 'True',
}

# ============================================================================
# TIER LIMITS (FREE vs PRO)
# ============================================================================

TIER_LIMITS = {
    'free': {
        'max_platforms': 2,                   # Only Instagram + Spotify
        'max_recommendations': 5,              # Half the recommendations
        'allowed_platforms': ['instagram', 'spotify'],  # Limited choices
        'monthly_updates': False,              # One-time only
        'shareable_profile': False,            # No public profile
        'friend_network': False,               # No friend features
        'price': 0
    },
    'pro': {
        'max_platforms': 999,                  # Unlimited
        'max_recommendations': 10,             # Full recommendations
        'allowed_platforms': 'all',            # All platforms
        'monthly_updates': True,               # Regenerate monthly
        'shareable_profile': True,             # Public profile
        'friend_network': True,                # Friend features
        'price': 4.99
    }
}

# ============================================================================
# DATABASE HELPERS (Simple JSON storage - upgrade to PostgreSQL for production)
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
# TIER MANAGEMENT FUNCTIONS
# ============================================================================

def get_user_tier(user):
    """
    Check if user is free or pro
    
    Returns:
        'pro' if user has active subscription
        'free' if no subscription
    """
    if not user:
        return 'free'
    
    # Check if user has Stripe subscription
    if user.get('stripe_subscription_id'):
        # In production, verify with Stripe API
        # For now, trust the database
        return 'pro'
    
    # Check for promotional/legacy pro access
    if user.get('pro_access') == True:
        return 'pro'
    
    return 'free'

def get_tier_limits(tier):
    """Get feature limits for user tier"""
    return TIER_LIMITS.get(tier, TIER_LIMITS['free'])

def check_platform_allowed(platform, user_tier):
    """Check if platform is allowed for user's tier"""
    limits = get_tier_limits(user_tier)
    allowed = limits['allowed_platforms']
    
    if allowed == 'all':
        return True
    
    return platform in allowed

def needs_upgrade(user, feature):
    """
    Check if user needs to upgrade for a feature
    
    Args:
        user: User dict
        feature: Feature name (e.g., 'shareable_profile', 'monthly_updates')
    
    Returns:
        True if upgrade needed, False if has access
    """
    tier = get_user_tier(user)
    limits = get_tier_limits(tier)
    
    return not limits.get(feature, False)

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

# ============================================================================
# ROUTES - User Onboarding
# ============================================================================

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """User signup flow"""
    if request.method == 'POST':
        email = request.form.get('email')
        referrer = request.form.get('referrer')  # From hidden field
        
        # Create user in database
        user_id = email  # Simple user ID for MVP
        save_user(user_id, {
            'email': email,
            'created_at': datetime.now().isoformat(),
            'platforms': {},
            'referred_by': referrer if referrer else None
        })
        
        # Set session
        session['user_id'] = user_id
        
        # Redirect to platform connection
        return redirect('/connect-platforms')
    
    # Get referrer from URL parameter
    referrer = request.args.get('ref')
    
    return render_template('signup.html', referrer=referrer)

@app.route('/connect-platforms')
def connect_platforms():
    """Platform connection page"""
    user = get_session_user()
    if not user:
        return redirect('/signup')
    
    # Get user's tier and limits
    tier = get_user_tier(user)
    limits = get_tier_limits(tier)
    
    # Check which platforms are allowed
    platform_access = {
        'instagram': check_platform_allowed('instagram', tier),
        'spotify': check_platform_allowed('spotify', tier),
        'pinterest': check_platform_allowed('pinterest', tier),
        'tiktok': check_platform_allowed('tiktok', tier)
    }
    
    return render_template('connect_platforms.html', 
                         user=user,
                         tier=tier,
                         limits=limits,
                         platform_access=platform_access)

# ============================================================================
# OAUTH - Instagram
# ============================================================================

@app.route('/oauth/instagram/start')
def instagram_oauth_start():
    """Initiate Instagram OAuth flow"""
    instagram = OAuth2Session(
        INSTAGRAM_CLIENT_ID,
        redirect_uri=INSTAGRAM_REDIRECT_URI,
        scope=['user_profile', 'user_media']
    )
    
    authorization_url, state = instagram.authorization_url(INSTAGRAM_AUTH_URL)
    
    # Store state for CSRF protection
    session['oauth_state'] = state
    
    return redirect(authorization_url)

@app.route('/oauth/instagram/callback')
def instagram_oauth_callback():
    """Handle Instagram OAuth callback"""
    user = get_session_user()
    if not user:
        return redirect('/signup')
    
    code = request.args.get('code')
    
    # Exchange code for access token
    response = requests.post(INSTAGRAM_TOKEN_URL, data={
        'client_id': INSTAGRAM_CLIENT_ID,
        'client_secret': INSTAGRAM_CLIENT_SECRET,
        'grant_type': 'authorization_code',
        'redirect_uri': INSTAGRAM_REDIRECT_URI,
        'code': code
    })
    
    if response.status_code == 200:
        token_data = response.json()
        
        # Save token to user
        save_user(session['user_id'], {
            'platforms': {
                **user.get('platforms', {}),
                'instagram': {
                    'access_token': token_data['access_token'],
                    'user_id': token_data['user_id'],
                    'connected_at': datetime.now().isoformat()
                }
            }
        })
        
        return redirect('/connect-platforms?success=instagram')
    
    return redirect('/connect-platforms?error=instagram')

# ============================================================================
# OAUTH - Spotify
# ============================================================================

@app.route('/oauth/spotify/start')
def spotify_oauth_start():
    """Initiate Spotify OAuth flow"""
    scope = 'user-read-private user-read-email user-top-read user-library-read playlist-read-private'
    
    spotify = OAuth2Session(
        SPOTIFY_CLIENT_ID,
        redirect_uri=SPOTIFY_REDIRECT_URI,
        scope=scope.split()
    )
    
    authorization_url, state = spotify.authorization_url(SPOTIFY_AUTH_URL)
    session['oauth_state'] = state
    
    return redirect(authorization_url)

@app.route('/oauth/spotify/callback')
def spotify_oauth_callback():
    """Handle Spotify OAuth callback"""
    user = get_session_user()
    if not user:
        return redirect('/signup')
    
    code = request.args.get('code')
    
    # Exchange code for token
    import base64
    auth_str = f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}"
    auth_bytes = auth_str.encode('ascii')
    auth_base64 = base64.b64encode(auth_bytes).decode('ascii')
    
    response = requests.post(SPOTIFY_TOKEN_URL, data={
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': SPOTIFY_REDIRECT_URI
    }, headers={
        'Authorization': f'Basic {auth_base64}'
    })
    
    if response.status_code == 200:
        token_data = response.json()
        
        save_user(session['user_id'], {
            'platforms': {
                **user.get('platforms', {}),
                'spotify': {
                    'access_token': token_data['access_token'],
                    'refresh_token': token_data.get('refresh_token'),
                    'expires_at': (datetime.now() + timedelta(seconds=token_data['expires_in'])).isoformat(),
                    'connected_at': datetime.now().isoformat()
                }
            }
        })
        
        return redirect('/connect-platforms?success=spotify')
    
    return redirect('/connect-platforms?error=spotify')

# ============================================================================
# OAUTH - Pinterest
# ============================================================================

@app.route('/oauth/pinterest/start')
def pinterest_oauth_start():
    """Initiate Pinterest OAuth flow"""
    scope = 'boards:read pins:read user_accounts:read'
    
    pinterest = OAuth2Session(
        PINTEREST_CLIENT_ID,
        redirect_uri=PINTEREST_REDIRECT_URI,
        scope=scope.split(',')
    )
    
    authorization_url, state = pinterest.authorization_url(
        PINTEREST_AUTH_URL,
        scope=scope
    )
    
    session['oauth_state'] = state
    return redirect(authorization_url)

@app.route('/oauth/pinterest/callback')
def pinterest_oauth_callback():
    """Handle Pinterest OAuth callback"""
    user = get_session_user()
    if not user:
        return redirect('/signup')
    
    code = request.args.get('code')
    
    response = requests.post(PINTEREST_TOKEN_URL, data={
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': PINTEREST_REDIRECT_URI
    }, auth=(PINTEREST_CLIENT_ID, PINTEREST_CLIENT_SECRET))
    
    if response.status_code == 200:
        token_data = response.json()
        
        save_user(session['user_id'], {
            'platforms': {
                **user.get('platforms', {}),
                'pinterest': {
                    'access_token': token_data['access_token'],
                    'refresh_token': token_data.get('refresh_token'),
                    'connected_at': datetime.now().isoformat()
                }
            }
        })
        
        return redirect('/connect-platforms?success=pinterest')
    
    return redirect('/connect-platforms?error=pinterest')

# ============================================================================
# TIKTOK - Public Scraping (No OAuth)
# ============================================================================

@app.route('/connect/tiktok', methods=['POST'])
def connect_tiktok():
    """Connect TikTok via username (public scraping)"""
    user = get_session_user()
    if not user:
        return jsonify({'error': 'Not logged in'}), 401
    
    username = request.form.get('username', '').strip().lstrip('@')
    
    if not username:
        return jsonify({'error': 'Username required'}), 400
    
    # Save TikTok username (we'll scrape later when generating recs)
    save_user(session['user_id'], {
        'platforms': {
            **user.get('platforms', {}),
            'tiktok': {
                'username': username,
                'method': 'public_scraping',
                'connected_at': datetime.now().isoformat()
            }
        }
    })
    
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
        # Check user tier and limits
        tier = get_user_tier(user)
        limits = get_tier_limits(tier)
        
        # Import platform-specific data fetchers
        from platform_integrations import (
            fetch_instagram_data,
            fetch_spotify_data,
            fetch_pinterest_data,
            fetch_tiktok_data
        )
        from recommendation_engine import generate_multi_platform_recommendations
        
        platforms = user.get('platforms', {})
        all_data = {}
        
        # Fetch data from each connected platform (respecting tier limits)
        if 'instagram' in platforms and check_platform_allowed('instagram', tier):
            all_data['instagram'] = fetch_instagram_data(platforms['instagram'])
        
        if 'spotify' in platforms and check_platform_allowed('spotify', tier):
            all_data['spotify'] = fetch_spotify_data(platforms['spotify'])
        
        if 'pinterest' in platforms and check_platform_allowed('pinterest', tier):
            all_data['pinterest'] = fetch_pinterest_data(platforms['pinterest'])
        
        if 'tiktok' in platforms and check_platform_allowed('tiktok', tier):
            all_data['tiktok'] = fetch_tiktok_data(platforms['tiktok'], APIFY_API_TOKEN)
        
        # Generate recommendations with tier limits
        recommendations = generate_multi_platform_recommendations(
            all_data,
            user.get('email', 'user'),
            claude_client,
            max_recommendations=limits['max_recommendations']  # Apply limit
        )
        
        # Save recommendations to user
        save_user(session['user_id'], {
            'recommendations': recommendations,
            'last_generated': datetime.now().isoformat(),
            'tier_at_generation': tier  # Track what tier they had
        })
        
        return jsonify({
            'success': True,
            'recommendations': recommendations,
            'tier': tier,
            'can_upgrade': tier == 'free'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/recommendations')
def view_recommendations():
    """View generated recommendations"""
    user = get_session_user()
    if not user:
        return redirect('/signup')
    
    recommendations = user.get('recommendations', [])
    if not recommendations:
        return redirect('/generate-recommendations')
    
    # Get user tier and limits
    tier = get_user_tier(user)
    limits = get_tier_limits(tier)
    
    # Generate shareable profile URL (only for pro users)
    profile_url = None
    if limits['shareable_profile']:
        import re
        username = re.sub(r'[^a-z0-9]', '', user.get('email', '').split('@')[0].lower())
        profile_url = f"{request.host_url}u/{username}"
    
    return render_template('recommendations.html', 
                         recommendations=recommendations,
                         user=user,
                         tier=tier,
                         limits=limits,
                         profile_url=profile_url,
                         can_upgrade=(tier == 'free'))

# ============================================================================
# PUBLIC SHAREABLE PROFILES (VIRAL GROWTH)
# ============================================================================

@app.route('/u/<username>')
def public_profile(username):
    """Public shareable gift profile - anyone can view without login (PRO FEATURE)"""
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
    
    # Check if user has pro tier (shareable profiles are pro-only)
    user_tier = get_user_tier(user_found)
    if user_tier != 'pro':
        # User exists but doesn't have pro - show upgrade message
        return render_template('profile_requires_pro.html', 
                             username=username,
                             display_name=user_found.get('email', '').split('@')[0].title())
    
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
# UPGRADE / PRICING
# ============================================================================

@app.route('/upgrade')
def upgrade():
    """Show upgrade to Pro page"""
    user = get_session_user()
    current_tier = get_user_tier(user) if user else 'free'
    
    return render_template('upgrade.html',
                         current_tier=current_tier,
                         tier_limits=TIER_LIMITS)

# ============================================================================
# STRIPE INTEGRATION
# ============================================================================

@app.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    """Create Stripe checkout session for Pro subscription"""
    try:
        user = get_session_user()
        if not user:
            return redirect('/signup')
        
        # Check if already pro
        if get_user_tier(user) == 'pro':
            return redirect('/dashboard?error=already_pro')
        
        checkout_session = stripe.checkout.Session.create(
            customer_email=user.get('email'),
            payment_method_types=['card'],
            line_items=[{
                'price': STRIPE_PRICE_ID,
                'quantity': 1,
            }],
            mode='subscription',
            success_url=url_for('upgrade_success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=url_for('upgrade', _external=True),
            metadata={
                'user_id': user.get('email')
            }
        )
        
        return redirect(checkout_session.url, code=303)
    
    except Exception as e:
        return str(e), 403


@app.route('/upgrade-success')
def upgrade_success():
    """Handle successful upgrade"""
    session_id = request.args.get('session_id')
    
    if session_id:
        try:
            # Retrieve the session from Stripe
            checkout_session = stripe.checkout.Session.retrieve(session_id)
            
            # Get subscription ID
            subscription_id = checkout_session.subscription
            
            # Update user in database
            user = get_session_user()
            if user:
                save_user(session.get('user_id'), {
                    'stripe_subscription_id': subscription_id,
                    'stripe_subscription_status': 'active',
                    'upgraded_at': datetime.now().isoformat()
                })
        except Exception as e:
            print(f"Error updating subscription: {e}")
    
    return redirect('/connect-platforms?success=upgrade')


@app.route('/stripe-webhook', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhook events"""
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')
    
    # In production, verify webhook signature
    # For now, just process the event
    
    try:
        event = json.loads(payload)
        
        if event['type'] == 'customer.subscription.deleted':
            # Handle subscription cancellation
            subscription = event['data']['object']
            subscription_id = subscription['id']
            
            # Find and update user
            with shelve.open('giftwise_db') as db:
                for key in db.keys():
                    if key.startswith('user_'):
                        user_data = db[key]
                        if user_data.get('stripe_subscription_id') == subscription_id:
                            user_data['stripe_subscription_status'] = 'canceled'
                            user_data['downgraded_at'] = datetime.now().isoformat()
                            db[key] = user_data
                            break
        
        elif event['type'] == 'customer.subscription.updated':
            # Handle subscription status changes
            subscription = event['data']['object']
            subscription_id = subscription['id']
            status = subscription['status']
            
            with shelve.open('giftwise_db') as db:
                for key in db.keys():
                    if key.startswith('user_'):
                        user_data = db[key]
                        if user_data.get('stripe_subscription_id') == subscription_id:
                            user_data['stripe_subscription_status'] = status
                            db[key] = user_data
                            break
        
        return jsonify({'success': True}), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 400

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

@app.route('/privacy')
def privacy_policy():
    return render_template('privacy.html')

# ============================================================================
# RUN APPLICATION
# ============================================================================

if __name__ == '__main__':
    app.run(debug=True, port=5000)
