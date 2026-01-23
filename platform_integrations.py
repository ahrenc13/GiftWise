"""
PLATFORM INTEGRATIONS
Data fetching from Instagram, Spotify, Pinterest, TikTok

Each function returns standardized data structure for recommendation engine
"""

import requests
import time
from collections import Counter

# ============================================================================
# INSTAGRAM DATA FETCHER
# ============================================================================

def fetch_instagram_data(platform_config):
    """Fetch data from Instagram via OAuth"""
    access_token = platform_config['access_token']
    
    try:
        # Get user profile
        profile_url = f"https://graph.instagram.com/me?fields=id,username&access_token={access_token}"
        profile_response = requests.get(profile_url)
        profile = profile_response.json()
        
        # Get media (posts) - can get up to 10,000 with pagination
        media = []
        media_url = f"https://graph.instagram.com/me/media?fields=id,caption,media_type,timestamp&limit=200&access_token={access_token}"
        
        while media_url and len(media) < 500:  # Limit to 500 posts
            response = requests.get(media_url)
            data = response.json()
            
            media.extend(data.get('data', []))
            media_url = data.get('paging', {}).get('next')
        
        # Extract hashtags from captions
        hashtags = []
        for post in media:
            caption = post.get('caption', '')
            if caption:
                # Simple hashtag extraction
                words = caption.split()
                hashtags.extend([w for w in words if w.startswith('#')])
        
        hashtag_counts = Counter(hashtags)
        
        return {
            'platform': 'instagram',
            'method': 'oauth',
            'username': profile.get('username'),
            'total_posts': len(media),
            'top_hashtags': dict(hashtag_counts.most_common(50)),
            'recent_captions': [p.get('caption', '')[:200] for p in media[:20]],
            'collected_at': time.time()
        }
    
    except Exception as e:
        print(f"Instagram fetch error: {e}")
        return {
            'platform': 'instagram',
            'error': str(e)
        }

# ============================================================================
# SPOTIFY DATA FETCHER
# ============================================================================

def fetch_spotify_data(platform_config):
    """Fetch data from Spotify via OAuth"""
    access_token = platform_config['access_token']
    headers = {'Authorization': f'Bearer {access_token}'}
    
    try:
        # Get top artists (medium term = last 6 months)
        top_artists = requests.get(
            'https://api.spotify.com/v1/me/top/artists?time_range=medium_term&limit=50',
            headers=headers
        ).json()
        
        # Get top tracks
        top_tracks = requests.get(
            'https://api.spotify.com/v1/me/top/tracks?time_range=medium_term&limit=50',
            headers=headers
        ).json()
        
        # Get user's playlists
        playlists = requests.get(
            'https://api.spotify.com/v1/me/playlists?limit=20',
            headers=headers
        ).json()
        
        # Extract data
        artists = []
        genres = []
        for artist in top_artists.get('items', []):
            artists.append(artist['name'])
            genres.extend(artist.get('genres', []))
        
        genre_counts = Counter(genres)
        
        tracks = [
            {
                'name': track['name'],
                'artist': track['artists'][0]['name']
            }
            for track in top_tracks.get('items', [])
        ]
        
        playlist_names = [p['name'] for p in playlists.get('items', [])]
        
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
        print(f"Spotify fetch error: {e}")
        return {
            'platform': 'spotify',
            'error': str(e)
        }

# ============================================================================
# PINTEREST DATA FETCHER
# ============================================================================

def fetch_pinterest_data(platform_config):
    """Fetch data from Pinterest via OAuth"""
    access_token = platform_config['access_token']
    headers = {'Authorization': f'Bearer {access_token}'}
    
    try:
        # Get user's boards
        boards_response = requests.get(
            'https://api.pinterest.com/v5/boards',
            headers=headers
        ).json()
        
        all_boards = []
        all_pins = []
        
        for board in boards_response.get('items', []):
            board_id = board['id']
            
            # Get pins from this board
            pins_response = requests.get(
                f'https://api.pinterest.com/v5/boards/{board_id}/pins',
                headers=headers
            ).json()
            
            pins = []
            for pin in pins_response.get('items', [])[:30]:  # Limit pins per board
                pins.append({
                    'title': pin.get('title'),
                    'description': pin.get('description'),
                    'link': pin.get('link')
                })
            
            all_pins.extend(pins)
            
            all_boards.append({
                'name': board.get('name'),
                'description': board.get('description'),
                'pin_count': board.get('pin_count'),
                'pins': pins
            })
        
        # Extract keywords from pins
        keywords = []
        for pin in all_pins:
            if pin['title']:
                keywords.extend(pin['title'].lower().split())
            if pin['description']:
                keywords.extend(pin['description'].lower().split())
        
        # Remove common words
        common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for'}
        keywords = [k for k in keywords if k not in common_words and len(k) > 3]
        keyword_counts = Counter(keywords)
        
        return {
            'platform': 'pinterest',
            'method': 'oauth',
            'total_boards': len(all_boards),
            'total_pins': len(all_pins),
            'boards': all_boards,
            'top_keywords': dict(keyword_counts.most_common(30)),
            'collected_at': time.time()
        }
    
    except Exception as e:
        print(f"Pinterest fetch error: {e}")
        return {
            'platform': 'pinterest',
            'error': str(e)
        }

# ============================================================================
# TIKTOK DATA FETCHER (Public Scraping)
# ============================================================================

def fetch_tiktok_data(platform_config, apify_token):
    """Fetch TikTok data via public scraping (Apify)"""
    username = platform_config['username']
    
    try:
        # Start Apify actor
        url = "https://api.apify.com/v2/acts/clockworks~tiktok-profile-scraper/runs"
        headers = {"Content-Type": "application/json"}
        params = {"token": apify_token}
        
        payload = {
            "profiles": [username],
            "resultsPerPage": 100
        }
        
        response = requests.post(url, json=payload, headers=headers, params=params)
        
        if response.status_code not in [200, 201]:
            return {
                'platform': 'tiktok',
                'error': 'Failed to start scraper'
            }
        
        run_data = response.json()["data"]
        run_id = run_data["id"]
        dataset_id = run_data["defaultDatasetId"]
        
        # Poll for completion (wait up to 2 minutes)
        status_url = f"https://api.apify.com/v2/acts/clockworks~tiktok-profile-scraper/runs/{run_id}"
        
        for _ in range(24):  # 24 * 5s = 2 minutes
            time.sleep(5)
            
            status_response = requests.get(status_url, params=params)
            status = status_response.json()["data"]["status"]
            
            if status == "SUCCEEDED":
                # Get results
                dataset_url = f"https://api.apify.com/v2/datasets/{dataset_id}/items"
                posts_response = requests.get(dataset_url, params=params)
                posts = posts_response.json()
                
                if not posts:
                    return {
                        'platform': 'tiktok',
                        'error': 'No data returned'
                    }
                
                # Extract hashtags and music
                hashtags = []
                music_tracks = []
                
                for post in posts:
                    # Handle hashtags (can be list of dicts or list of strings)
                    post_hashtags = post.get('hashtags', [])
                    for tag in post_hashtags:
                        if isinstance(tag, dict):
                            hashtags.append(tag.get('name', ''))
                        else:
                            hashtags.append(str(tag))
                    
                    # Music info
                    music = post.get('musicMeta', {})
                    if music:
                        music_tracks.append(music.get('musicName', ''))
                
                hashtag_counts = Counter([h for h in hashtags if h])
                music_counts = Counter([m for m in music_tracks if m])
                
                return {
                    'platform': 'tiktok',
                    'method': 'public_scraping',
                    'username': username,
                    'total_posts': len(posts),
                    'top_hashtags': dict(hashtag_counts.most_common(30)),
                    'top_music': dict(music_counts.most_common(20)),
                    'collected_at': time.time()
                }
            
            elif status in ["FAILED", "ABORTED"]:
                return {
                    'platform': 'tiktok',
                    'error': f'Scraper {status.lower()}'
                }
        
        # Timeout
        return {
            'platform': 'tiktok',
            'error': 'Timeout waiting for results'
        }
    
    except Exception as e:
        print(f"TikTok fetch error: {e}")
        return {
            'platform': 'tiktok',
            'error': str(e)
        }
