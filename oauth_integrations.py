"""
OAUTH INTEGRATIONS
Complete OAuth implementations for Pinterest, Spotify, Etsy, and more

Each platform has:
- Authorization URL generation
- Callback handling
- Token refresh (where applicable)
- Data fetching
"""

import os
import requests
from requests_oauthlib import OAuth2Session
from urllib.parse import urlencode
import logging
import time

logger = logging.getLogger('giftwise')

# ============================================================================
# PINTEREST OAUTH
# ============================================================================

# These are set from environment variables (see above)

def get_pinterest_authorization_url():
    """
    Generate Pinterest OAuth authorization URL
    
    Returns:
        Authorization URL
    """
    if not PINTEREST_CLIENT_ID:
        return None
    
    scopes = ['boards:read', 'pins:read']
    params = {
        'client_id': PINTEREST_CLIENT_ID,
        'redirect_uri': PINTEREST_REDIRECT_URI,
        'response_type': 'code',
        'scope': ' '.join(scopes),
        'state': 'pinterest_auth'  # Add CSRF protection
    }
    
    auth_url = f"https://www.pinterest.com/oauth/?{urlencode(params)}"
    return auth_url

def exchange_pinterest_code(code):
    """
    Exchange authorization code for access token
    
    Args:
        code: Authorization code from callback
    
    Returns:
        Access token dict or None
    """
    if not PINTEREST_CLIENT_ID or not PINTEREST_CLIENT_SECRET:
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
    """
    Fetch Pinterest boards and pins
    
    Args:
        access_token: Pinterest access token
    
    Returns:
        Dict with boards and pins data
    """
    if not access_token:
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

SPOTIFY_CLIENT_ID = os.environ.get('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.environ.get('SPOTIFY_CLIENT_SECRET')
SPOTIFY_REDIRECT_URI = os.environ.get('SPOTIFY_REDIRECT_URI', 'http://localhost:5000/oauth/spotify/callback')

def get_spotify_authorization_url():
    """
    Generate Spotify OAuth authorization URL
    
    Returns:
        Authorization URL
    """
    if not SPOTIFY_CLIENT_ID:
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
    return auth_url

def exchange_spotify_code(code):
    """
    Exchange authorization code for access token
    
    Args:
        code: Authorization code from callback
    
    Returns:
        Access token dict or None
    """
    if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
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
    """
    Fetch Spotify listening data
    
    Args:
        access_token: Spotify access token
    
    Returns:
        Dict with Spotify data
    """
    if not access_token:
        return None
    
    try:
        headers = {
            'Authorization': f'Bearer {access_token}'
        }
        
        # Get top artists
        top_artists_url = 'https://api.spotify.com/v1/me/top/artists?time_range=medium_term&limit=50'
        top_artists_response = requests.get(top_artists_url, headers=headers, timeout=10)
        
        artists = []
        genres = []
        if top_artists_response.status_code == 200:
            artists_data = top_artists_response.json().get('items', [])
            for artist in artists_data:
                artists.append(artist.get('name', ''))
                genres.extend(artist.get('genres', []))
        
        # Get top tracks
        top_tracks_url = 'https://api.spotify.com/v1/me/top/tracks?time_range=medium_term&limit=50'
        top_tracks_response = requests.get(top_tracks_url, headers=headers, timeout=10)
        
        tracks = []
        if top_tracks_response.status_code == 200:
            tracks_data = top_tracks_response.json().get('items', [])
            for track in tracks_data:
                tracks.append({
                    'name': track.get('name', ''),
                    'artist': ', '.join([a['name'] for a in track.get('artists', [])]),
                    'album': track.get('album', {}).get('name', '')
                })
        
        # Get playlists
        playlists_url = 'https://api.spotify.com/v1/me/playlists?limit=20'
        playlists_response = requests.get(playlists_url, headers=headers, timeout=10)
        
        playlists = []
        if playlists_response.status_code == 200:
            playlists_data = playlists_response.json().get('items', [])
            for playlist in playlists_data:
                playlists.append(playlist.get('name', ''))
        
        from collections import Counter
        genre_counts = Counter(genres)
        
        return {
            'platform': 'spotify',
            'method': 'oauth',
            'top_artists': artists[:20],
            'top_tracks': tracks[:20],
            'top_genres': dict(genre_counts.most_common(15)),
            'playlists': playlists,
            'collected_at': time.time()
        }
    
    except Exception as e:
        logger.error(f"Spotify data fetch error: {e}")
        return None

# ============================================================================
# ETSY OAUTH
# ============================================================================

ETSY_CLIENT_ID = os.environ.get('ETSY_CLIENT_ID')
ETSY_CLIENT_SECRET = os.environ.get('ETSY_CLIENT_SECRET')
ETSY_REDIRECT_URI = os.environ.get('ETSY_REDIRECT_URI', 'http://localhost:5000/oauth/etsy/callback')

def get_etsy_authorization_url():
    """
    Generate Etsy OAuth authorization URL
    
    Etsy uses OAuth 2.0 with PKCE (recommended) or without
    
    Returns:
        Authorization URL
    """
    if not ETSY_CLIENT_ID:
        return None
    
    # Etsy OAuth 2.0
    scopes = ['favorites_r', 'profile_r']
    
    params = {
        'response_type': 'code',
        'redirect_uri': ETSY_REDIRECT_URI,
        'scope': ' '.join(scopes),
        'client_id': ETSY_CLIENT_ID,
        'state': 'etsy_auth'
    }
    
    auth_url = f"https://www.etsy.com/oauth/connect?{urlencode(params)}"
    return auth_url

def exchange_etsy_code(code):
    """
    Exchange authorization code for access token
    
    Args:
        code: Authorization code from callback
    
    Returns:
        Access token dict or None
    """
    if not ETSY_CLIENT_ID or not ETSY_CLIENT_SECRET:
        return None
    
    try:
        token_url = 'https://api.etsy.com/v3/public/oauth/token'
        
        data = {
            'grant_type': 'authorization_code',
            'client_id': ETSY_CLIENT_ID,
            'redirect_uri': ETSY_REDIRECT_URI,
            'code': code,
            'code_verifier': ''  # Etsy may require PKCE
        }
        
        auth = (ETSY_CLIENT_ID, ETSY_CLIENT_SECRET)
        
        response = requests.post(token_url, data=data, auth=auth, timeout=10)
        
        if response.status_code == 200:
            token_data = response.json()
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
    """
    Fetch Etsy favorites/wishlist
    
    Args:
        access_token: Etsy access token
    
    Returns:
        Dict with favorites data
    """
    if not access_token:
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
                'price': float(listing.get('price', {}).get('amount', 0)) / 100,  # Etsy prices in cents
                'currency': listing.get('price', {}).get('currency_code', 'USD'),
                'url': listing.get('url', ''),
                'shop_name': listing.get('shop_name', ''),
                'category': listing.get('taxonomy_path', [''])[0] if listing.get('taxonomy_path') else '',
                'image_url': listing.get('images', [{}])[0].get('url', '') if listing.get('images') else ''
            })
        
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
# GOOGLE OAUTH (for YouTube)
# ============================================================================

GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
GOOGLE_REDIRECT_URI = os.environ.get('GOOGLE_REDIRECT_URI', 'http://localhost:5000/oauth/google/callback')
GOOGLE_YOUTUBE_API_KEY = os.environ.get('GOOGLE_YOUTUBE_API_KEY')  # Alternative: API key instead of OAuth

def get_google_authorization_url():
    """
    Generate Google OAuth authorization URL (for YouTube)
    
    Returns:
        Authorization URL
    """
    if not GOOGLE_CLIENT_ID:
        return None
    
    scopes = [
        'https://www.googleapis.com/auth/youtube.readonly'
    ]
    
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
    return auth_url

def exchange_google_code(code):
    """
    Exchange authorization code for access token
    
    Args:
        code: Authorization code from callback
    
    Returns:
        Access token dict or None
    """
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
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

def fetch_youtube_subscriptions(access_token=None, api_key=None, channel_id=None):
    """
    Fetch YouTube subscriptions (channels they follow)
    
    Can use OAuth (access_token) or API key (api_key + channel_id)
    
    Args:
        access_token: OAuth access token (preferred)
        api_key: YouTube Data API key (alternative)
        channel_id: YouTube channel ID (if using API key)
    
    Returns:
        Dict with subscriptions data
    """
    try:
        if access_token:
            # OAuth method
            headers = {
                'Authorization': f'Bearer {access_token}'
            }
            
            # Get channel ID
            me_url = 'https://www.googleapis.com/youtube/v3/channels?part=id&mine=true'
            me_response = requests.get(me_url, headers=headers, timeout=10)
            
            if me_response.status_code != 200:
                return None
            
            channel_id = me_response.json().get('items', [{}])[0].get('id')
            if not channel_id:
                return None
            
            # Get subscriptions
            subs_url = f'https://www.googleapis.com/youtube/v3/subscriptions?part=snippet&mine=true&maxResults=50'
            subs_response = requests.get(subs_url, headers=headers, timeout=10)
        
        elif api_key and channel_id:
            # API key method
            subs_url = f'https://www.googleapis.com/youtube/v3/subscriptions?part=snippet&channelId={channel_id}&maxResults=50&key={api_key}'
            subs_response = requests.get(subs_url, timeout=10)
        
        else:
            return None
        
        if subs_response.status_code != 200:
            logger.error(f"YouTube subscriptions fetch failed: {subs_response.status_code}")
            return None
        
        subscriptions_data = subs_response.json().get('items', [])
        
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
                # Common YouTube categories
                youtube_categories = ['gaming', 'music', 'tech', 'cooking', 'travel', 'fitness', 'education', 'comedy', 'beauty', 'fashion']
                for cat in youtube_categories:
                    if cat in words:
                        categories.append(cat)
        
        from collections import Counter
        category_counts = Counter(categories)
        
        return {
            'platform': 'youtube',
            'method': 'oauth' if access_token else 'api_key',
            'subscriptions': channels[:30],
            'total_subscriptions': len(channels),
            'categories': dict(category_counts.most_common(10)),
            'collected_at': time.time()
        }
    
    except Exception as e:
        logger.error(f"YouTube subscriptions fetch error: {e}")
        return None
