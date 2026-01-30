"""
OAUTH INTEGRATIONS - FIXED
Complete OAuth implementations for Pinterest, Spotify, Etsy, YouTube

FIXES:
- Added environment variable definitions (CRITICAL BUG FIX)
- Removed duplicate definitions
- Better error handling
- Added logging
"""

import os
import requests
from urllib.parse import urlencode
import logging
import time

logger = logging.getLogger('giftwise')

# ============================================================================
# ENVIRONMENT VARIABLES - LOAD ONCE AT MODULE LEVEL
# ============================================================================

# Pinterest OAuth
PINTEREST_CLIENT_ID = os.environ.get('PINTEREST_CLIENT_ID')
PINTEREST_CLIENT_SECRET = os.environ.get('PINTEREST_CLIENT_SECRET')
PINTEREST_REDIRECT_URI = os.environ.get('PINTEREST_REDIRECT_URI', 'http://localhost:5000/oauth/pinterest/callback')

# Spotify OAuth
SPOTIFY_CLIENT_ID = os.environ.get('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.environ.get('SPOTIFY_CLIENT_SECRET')
SPOTIFY_REDIRECT_URI = os.environ.get('SPOTIFY_REDIRECT_URI', 'http://localhost:5000/oauth/spotify/callback')

# Etsy OAuth
ETSY_CLIENT_ID = os.environ.get('ETSY_CLIENT_ID')
ETSY_CLIENT_SECRET = os.environ.get('ETSY_CLIENT_SECRET')
ETSY_REDIRECT_URI = os.environ.get('ETSY_REDIRECT_URI', 'http://localhost:5000/oauth/etsy/callback')

# Google OAuth (YouTube)
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
GOOGLE_REDIRECT_URI = os.environ.get('GOOGLE_REDIRECT_URI', 'http://localhost:5000/oauth/google/callback')

# ============================================================================
# PINTEREST OAUTH
# ============================================================================

def get_pinterest_authorization_url():
    """Generate Pinterest OAuth authorization URL"""
    if not PINTEREST_CLIENT_ID:
        logger.error("Pinterest OAuth not configured - missing PINTEREST_CLIENT_ID")
        return None
    
    scopes = ['boards:read', 'pins:read']
    params = {
        'client_id': PINTEREST_CLIENT_ID,
        'redirect_uri': PINTEREST_REDIRECT_URI,
        'response_type': 'code',
        'scope': ' '.join(scopes),
        'state': 'pinterest_auth'
    }
    
    auth_url = f"https://www.pinterest.com/oauth/?{urlencode(params)}"
    logger.info(f"Generated Pinterest OAuth URL")
    return auth_url


def exchange_pinterest_code(code):
    """Exchange Pinterest authorization code for access token"""
    if not PINTEREST_CLIENT_ID or not PINTEREST_CLIENT_SECRET:
        logger.error("Pinterest OAuth not configured")
        return None
    
    try:
        token_url = 'https://api.pinterest.com/v5/oauth/token'
        
        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': PINTEREST_REDIRECT_URI
        }
        
        auth = (PINTEREST_CLIENT_ID, PINTEREST_CLIENT_SECRET)
        
        response = requests.post(token_url, data=data, auth=auth, timeout=10)
        
        if response.status_code == 200:
            token_data = response.json()
            logger.info("Pinterest token exchange successful")
            return {
                'access_token': token_data.get('access_token'),
                'refresh_token': token_data.get('refresh_token'),
                'expires_in': token_data.get('expires_in'),
                'token_type': token_data.get('token_type', 'bearer')
            }
        else:
            logger.error(f"Pinterest token exchange failed: {response.status_code} - {response.text}")
            return None
    
    except Exception as e:
        logger.error(f"Pinterest token exchange error: {e}")
        return None


def fetch_pinterest_data(access_token):
    """Fetch Pinterest boards and pins via OAuth"""
    if not access_token:
        logger.error("No Pinterest access token provided")
        return None
    
    try:
        headers = {
            'Authorization': f'Bearer {access_token}'
        }
        
        # Get boards
        boards_url = 'https://api.pinterest.com/v5/boards'
        boards_response = requests.get(boards_url, headers=headers, timeout=10)
        
        boards = []
        if boards_response.status_code == 200:
            boards_data = boards_response.json().get('items', [])
            
            for board in boards_data[:20]:  # Limit to 20 boards
                board_id = board.get('id')
                board_name = board.get('name', '')
                
                # Get pins for this board
                pins_url = f'https://api.pinterest.com/v5/boards/{board_id}/pins'
                pins_response = requests.get(pins_url, headers=headers, timeout=10)
                
                pins = []
                if pins_response.status_code == 200:
                    pins_data = pins_response.json().get('items', [])
                    for pin in pins_data[:30]:  # Limit to 30 pins per board
                        pins.append({
                            'title': pin.get('title', ''),
                            'description': pin.get('description', ''),
                            'link': pin.get('link', ''),
                            'image_url': pin.get('media', {}).get('images', {}).get('originals', {}).get('url', '')
                        })
                
                boards.append({
                    'id': board_id,
                    'name': board_name,
                    'description': board.get('description', ''),
                    'pin_count': len(pins),
                    'pins': pins
                })
        
        logger.info(f"Fetched Pinterest data: {len(boards)} boards")
        return {
            'platform': 'pinterest',
            'method': 'oauth',
            'boards': boards,
            'total_boards': len(boards),
            'total_pins': sum(len(b['pins']) for b in boards),
            'collected_at': time.time()
        }
    
    except Exception as e:
        logger.error(f"Pinterest data fetch error: {e}")
        return None

# ============================================================================
# SPOTIFY OAUTH
# ============================================================================

def get_spotify_authorization_url():
    """Generate Spotify OAuth authorization URL"""
    if not SPOTIFY_CLIENT_ID:
        logger.error("Spotify OAuth not configured - missing SPOTIFY_CLIENT_ID")
        return None
    
    scopes = [
        'user-top-read',
        'user-read-recently-played',
        'playlist-read-private',
        'user-library-read'
    ]
    
    params = {
        'client_id': SPOTIFY_CLIENT_ID,
        'redirect_uri': SPOTIFY_REDIRECT_URI,
        'response_type': 'code',
        'scope': ' '.join(scopes),
        'state': 'spotify_auth'
    }
    
    auth_url = f"https://accounts.spotify.com/authorize?{urlencode(params)}"
    logger.info("Generated Spotify OAuth URL")
    return auth_url


def exchange_spotify_code(code):
    """Exchange Spotify authorization code for access token"""
    if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
        logger.error("Spotify OAuth not configured")
        return None
    
    try:
        token_url = 'https://accounts.spotify.com/api/token'
        
        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': SPOTIFY_REDIRECT_URI
        }
        
        auth = (SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET)
        
        response = requests.post(token_url, data=data, auth=auth, timeout=10)
        
        if response.status_code == 200:
            token_data = response.json()
            logger.info("Spotify token exchange successful")
            return {
                'access_token': token_data.get('access_token'),
                'refresh_token': token_data.get('refresh_token'),
                'expires_in': token_data.get('expires_in'),
                'token_type': token_data.get('token_type', 'bearer')
            }
        else:
            logger.error(f"Spotify token exchange failed: {response.status_code} - {response.text}")
            return None
    
    except Exception as e:
        logger.error(f"Spotify token exchange error: {e}")
        return None


def fetch_spotify_data(access_token):
    """Fetch Spotify listening data via OAuth"""
    if not access_token:
        logger.error("No Spotify access token provided")
        return None
    
    try:
        headers = {'Authorization': f'Bearer {access_token}'}
        
        # Get top artists (medium term = last 6 months)
        top_artists_response = requests.get(
            'https://api.spotify.com/v1/me/top/artists?time_range=medium_term&limit=50',
            headers=headers,
            timeout=10
        )
        
        # Get top tracks
        top_tracks_response = requests.get(
            'https://api.spotify.com/v1/me/top/tracks?time_range=medium_term&limit=50',
            headers=headers,
            timeout=10
        )
        
        # Get playlists
        playlists_response = requests.get(
            'https://api.spotify.com/v1/me/playlists?limit=20',
            headers=headers,
            timeout=10
        )
        
        if top_artists_response.status_code != 200:
            logger.error(f"Spotify API error: {top_artists_response.status_code}")
            return None
        
        top_artists = top_artists_response.json()
        top_tracks = top_tracks_response.json()
        playlists = playlists_response.json()
        
        # Extract data
        artists = []
        genres = []
        for artist in top_artists.get('items', []):
            artists.append(artist['name'])
            genres.extend(artist.get('genres', []))
        
        from collections import Counter
        genre_counts = Counter(genres)
        
        tracks = [
            {
                'name': track['name'],
                'artist': track['artists'][0]['name']
            }
            for track in top_tracks.get('items', [])
        ]
        
        playlist_names = [p['name'] for p in playlists.get('items', [])]
        
        logger.info(f"Fetched Spotify data: {len(artists)} artists, {len(tracks)} tracks")
        return {
            'platform': 'spotify',
            'method': 'oauth',
            'top_artists': artists[:20],
            'top_genres': dict(genre_counts.most_common(15)),
            'top_tracks': tracks[:20],
            'playlists': playlist_names,
            'collected_at': time.time()
        }
    
    except Exception as e:
        logger.error(f"Spotify data fetch error: {e}")
        return None

# ============================================================================
# ETSY OAUTH
# ============================================================================

def get_etsy_authorization_url():
    """Generate Etsy OAuth authorization URL"""
    if not ETSY_CLIENT_ID:
        logger.error("Etsy OAuth not configured - missing ETSY_CLIENT_ID")
        return None
    
    scopes = ['favorites_r']
    
    params = {
        'client_id': ETSY_CLIENT_ID,
        'redirect_uri': ETSY_REDIRECT_URI,
        'response_type': 'code',
        'scope': ' '.join(scopes),
        'state': 'etsy_auth'
    }
    
    auth_url = f"https://www.etsy.com/oauth/connect?{urlencode(params)}"
    logger.info("Generated Etsy OAuth URL")
    return auth_url


def exchange_etsy_code(code):
    """Exchange Etsy authorization code for access token"""
    if not ETSY_CLIENT_ID or not ETSY_CLIENT_SECRET:
        logger.error("Etsy OAuth not configured")
        return None
    
    try:
        token_url = 'https://api.etsy.com/v3/public/oauth/token'
        
        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': ETSY_REDIRECT_URI,
            'client_id': ETSY_CLIENT_ID
        }
        
        auth = (ETSY_CLIENT_ID, ETSY_CLIENT_SECRET)
        
        response = requests.post(token_url, data=data, auth=auth, timeout=10)
        
        if response.status_code == 200:
            token_data = response.json()
            logger.info("Etsy token exchange successful")
            return {
                'access_token': token_data.get('access_token'),
                'refresh_token': token_data.get('refresh_token'),
                'expires_in': token_data.get('expires_in'),
                'token_type': token_data.get('token_type', 'bearer')
            }
        else:
            logger.error(f"Etsy token exchange failed: {response.status_code} - {response.text}")
            return None
    
    except Exception as e:
        logger.error(f"Etsy token exchange error: {e}")
        return None


def fetch_etsy_favorites(access_token):
    """Fetch Etsy favorites/wishlist via OAuth"""
    if not access_token:
        logger.error("No Etsy access token provided")
        return None
    
    try:
        headers = {
            'Authorization': f'Bearer {access_token}',
            'x-api-key': ETSY_CLIENT_ID
        }
        
        # Get user's favorite listings
        favorites_url = 'https://openapi.etsy.com/v3/application/users/me/favorites/listings'
        response = requests.get(favorites_url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            logger.error(f"Etsy favorites fetch failed: {response.status_code}")
            return None
        
        data = response.json()
        favorites = []
        
        for listing in data.get('results', []):
            favorites.append({
                'name': listing.get('title', ''),
                'price': float(listing.get('price', {}).get('amount', 0)) / 100,
                'currency': listing.get('price', {}).get('currency_code', 'USD'),
                'url': listing.get('url', ''),
                'shop_name': listing.get('shop_name', ''),
                'category': listing.get('taxonomy_path', [''])[0] if listing.get('taxonomy_path') else '',
                'image_url': listing.get('images', [{}])[0].get('url', '') if listing.get('images') else ''
            })
        
        logger.info(f"Fetched Etsy favorites: {len(favorites)} items")
        return {
            'platform': 'etsy',
            'method': 'oauth',
            'items': favorites,
            'total_items': len(favorites),
            'collected_at': time.time()
        }
    
    except Exception as e:
        logger.error(f"Etsy favorites fetch error: {e}")
        return None

# ============================================================================
# GOOGLE OAUTH (YouTube)
# ============================================================================

def get_google_authorization_url():
    """Generate Google OAuth authorization URL (for YouTube)"""
    if not GOOGLE_CLIENT_ID:
        logger.error("Google OAuth not configured - missing GOOGLE_CLIENT_ID")
        return None
    
    scopes = ['https://www.googleapis.com/auth/youtube.readonly']
    
    params = {
        'client_id': GOOGLE_CLIENT_ID,
        'redirect_uri': GOOGLE_REDIRECT_URI,
        'response_type': 'code',
        'scope': ' '.join(scopes),
        'access_type': 'offline',
        'prompt': 'consent',
        'state': 'google_auth'
    }
    
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    logger.info("Generated Google OAuth URL")
    return auth_url


def exchange_google_code(code):
    """Exchange Google authorization code for access token"""
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        logger.error("Google OAuth not configured")
        return None
    
    try:
        token_url = 'https://oauth2.googleapis.com/token'
        
        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': GOOGLE_REDIRECT_URI,
            'client_id': GOOGLE_CLIENT_ID,
            'client_secret': GOOGLE_CLIENT_SECRET
        }
        
        response = requests.post(token_url, data=data, timeout=10)
        
        if response.status_code == 200:
            token_data = response.json()
            logger.info("Google token exchange successful")
            return {
                'access_token': token_data.get('access_token'),
                'refresh_token': token_data.get('refresh_token'),
                'expires_in': token_data.get('expires_in'),
                'token_type': token_data.get('token_type', 'bearer')
            }
        else:
            logger.error(f"Google token exchange failed: {response.status_code} - {response.text}")
            return None
    
    except Exception as e:
        logger.error(f"Google token exchange error: {e}")
        return None


def fetch_youtube_subscriptions(access_token):
    """Fetch YouTube subscriptions (channels they follow) via OAuth"""
    if not access_token:
        logger.error("No YouTube access token provided")
        return None
    
    try:
        headers = {'Authorization': f'Bearer {access_token}'}
        
        # Get subscriptions
        subs_url = 'https://www.googleapis.com/youtube/v3/subscriptions?part=snippet&mine=true&maxResults=50'
        response = requests.get(subs_url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            logger.error(f"YouTube subscriptions fetch failed: {response.status_code}")
            return None
        
        subscriptions_data = response.json().get('items', [])
        
        channels = []
        categories = []
        
        for sub in subscriptions_data:
            snippet = sub.get('snippet', {})
            title = snippet.get('title', '')
            description = snippet.get('description', '')
            
            channels.append({
                'title': title,
                'description': description[:200],
                'channel_id': snippet.get('resourceId', {}).get('channelId', '')
            })
            
            # Extract categories from description
            if description:
                words = description.lower().split()
                youtube_categories = ['gaming', 'music', 'tech', 'cooking', 'travel', 'fitness', 'education', 'comedy', 'beauty', 'fashion']
                for cat in youtube_categories:
                    if cat in words:
                        categories.append(cat)
        
        from collections import Counter
        category_counts = Counter(categories)
        
        logger.info(f"Fetched YouTube subscriptions: {len(channels)} channels")
        return {
            'platform': 'youtube',
            'method': 'oauth',
            'subscriptions': channels[:30],
            'total_subscriptions': len(channels),
            'categories': dict(category_counts.most_common(10)),
            'collected_at': time.time()
        }
    
    except Exception as e:
        logger.error(f"YouTube subscriptions fetch error: {e}")
        return None
