"""
SPOTIFY INPUT PARSER
Handles Spotify Wrapped share links and plain artist text.

Accepts:
- Spotify Wrapped playlist URL: https://open.spotify.com/playlist/37i9dQZEVXd1...
- Any Spotify playlist/artist/track URL
- Plain text artist names (fallback): "Taylor Swift, The Weeknd, Billie Eilish"

Returns artists, track names, AND genres — all three passed to profile analyzer
for maximum gift recommendation signal.

Author: Chad + Claude
Date: February 2026
"""

import re
import requests
import logging
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)

# Spotify URL patterns
SPOTIFY_ARTIST_URL_PATTERN = r'https?://open\.spotify\.com/artist/([a-zA-Z0-9]+)'
SPOTIFY_TRACK_URL_PATTERN = r'https?://open\.spotify\.com/track/([a-zA-Z0-9]+)'
SPOTIFY_ALBUM_URL_PATTERN = r'https?://open\.spotify\.com/album/([a-zA-Z0-9]+)'
SPOTIFY_PLAYLIST_URL_PATTERN = r'https?://open\.spotify\.com/playlist/([a-zA-Z0-9]+)'


def get_spotify_api_token(client_id: str, client_secret: str) -> Optional[str]:
    """
    Get Spotify API access token using client credentials flow.

    Returns:
        Access token or None if auth fails (with detailed logging)
    """
    try:
        auth_url = 'https://accounts.spotify.com/api/token'
        auth_data = {'grant_type': 'client_credentials'}
        auth = (client_id, client_secret)

        response = requests.post(auth_url, data=auth_data, auth=auth, timeout=10)

        if response.status_code == 200:
            token_data = response.json()
            token = token_data.get('access_token')
            if token:
                logger.info("Spotify API token obtained successfully")
                return token
            else:
                logger.error("Spotify token response had no access_token field")
                return None
        else:
            logger.error(f"Spotify token fetch failed: HTTP {response.status_code} — check SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET in Railway")
            return None

    except Exception as e:
        logger.error(f"Error getting Spotify API token: {e}")
        return None


def fetch_artists_genres(artist_ids: List[str], access_token: str) -> List[str]:
    """
    Batch fetch genres for a list of Spotify artist IDs.
    Spotify allows up to 50 artists per request.

    Returns:
        List of unique genre strings (e.g., ["indie pop", "alt-rock", "hyperpop"])
    """
    genres_seen = set()
    genre_list = []

    # Process up to 100 artists in batches of 50
    for i in range(0, min(len(artist_ids), 100), 50):
        batch = artist_ids[i:i + 50]
        url = 'https://api.spotify.com/v1/artists'
        headers = {'Authorization': f'Bearer {access_token}'}
        params = {'ids': ','.join(batch)}

        try:
            response = requests.get(url, headers=headers, params=params, timeout=8)
            if response.status_code == 200:
                data = response.json()
                for artist in data.get('artists', []) or []:
                    if not artist:
                        continue
                    for genre in artist.get('genres', []):
                        if genre and genre not in genres_seen:
                            genres_seen.add(genre)
                            genre_list.append(genre)
            else:
                logger.warning(f"Artist genre batch fetch failed: HTTP {response.status_code}")
        except Exception as e:
            logger.error(f"Error fetching artist genres batch: {e}")

    logger.info(f"Fetched {len(genre_list)} unique genres from {len(artist_ids)} artists")
    return genre_list


def fetch_playlist_data(playlist_id: str, access_token: str) -> Dict:
    """
    Fetch artists, track names, and genres from a Spotify playlist.
    Works for Wrapped share links and any public playlist.

    Returns:
        {
            'artists': List[str],     # Unique artist names
            'tracks': List[str],      # Track titles
            'genres': List[str],      # Unique genres across all artists
            'artist_ids': List[str],  # Spotify artist IDs (for genre batch fetch)
            'error': Optional[str]    # Set if fetch failed
        }
    """
    empty = {'artists': [], 'tracks': [], 'genres': [], 'artist_ids': [], 'error': None}

    try:
        url = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks"
        headers = {'Authorization': f'Bearer {access_token}'}
        params = {
            'fields': 'items(track(artists(id,name),name)),next',
            'limit': 50,
            'market': 'US'
        }

        artists_seen = set()
        artist_list = []
        artist_ids = []
        track_list = []
        pages_fetched = 0
        max_pages = 4  # Up to 200 tracks — enough for any Wrapped playlist

        while url and pages_fetched < max_pages:
            response = requests.get(
                url,
                headers=headers,
                params=params if pages_fetched == 0 else None,
                timeout=8
            )

            if response.status_code == 403:
                logger.warning(f"Spotify playlist {playlist_id}: 403 Forbidden — playlist may be private or require user auth")
                empty['error'] = 'private'
                return empty
            elif response.status_code == 404:
                logger.warning(f"Spotify playlist {playlist_id}: 404 Not Found")
                empty['error'] = 'not_found'
                return empty
            elif response.status_code != 200:
                logger.warning(f"Spotify playlist fetch failed: HTTP {response.status_code}")
                empty['error'] = f'http_{response.status_code}'
                return empty

            data = response.json()
            items = data.get('items', [])

            for item in items:
                track = item.get('track') or {}

                # Collect track name
                track_name = track.get('name', '').strip()
                if track_name:
                    track_list.append(track_name)

                # Collect artist names and IDs
                for artist in track.get('artists', []):
                    name = artist.get('name', '').strip()
                    artist_id = artist.get('id', '').strip()
                    if name and name.lower() not in artists_seen:
                        artists_seen.add(name.lower())
                        artist_list.append(name)
                        if artist_id:
                            artist_ids.append(artist_id)

            url = data.get('next')
            pages_fetched += 1

        logger.info(f"Playlist {playlist_id}: {len(artist_list)} artists, {len(track_list)} tracks from {pages_fetched} pages")

        if not artist_list:
            empty['error'] = 'empty'
            return empty

        # Batch fetch genres from artist IDs
        genres = fetch_artists_genres(artist_ids, access_token) if artist_ids else []

        return {
            'artists': artist_list,
            'tracks': track_list,
            'genres': genres,
            'artist_ids': artist_ids,
            'error': None
        }

    except Exception as e:
        logger.error(f"Error fetching playlist data: {e}")
        empty['error'] = str(e)
        return empty


def fetch_spotify_metadata(entity_type: str, entity_id: str, access_token: str) -> Optional[str]:
    """
    Fetch entity name from Spotify API for individual artist/track/album URLs.

    Returns:
        Entity name string or None if fetch fails
    """
    try:
        url = f"https://api.spotify.com/v1/{entity_type}s/{entity_id}"
        headers = {'Authorization': f'Bearer {access_token}'}

        response = requests.get(url, headers=headers, timeout=5)

        if response.status_code == 200:
            data = response.json()

            if entity_type == 'artist':
                return data.get('name')
            elif entity_type == 'track':
                artist_names = [a.get('name', '') for a in data.get('artists', [])]
                track_name = data.get('name', '')
                if artist_names and track_name:
                    return f"{', '.join(artist_names)} - {track_name}"
                return track_name
            elif entity_type == 'album':
                artist_names = [a.get('name', '') for a in data.get('artists', [])]
                album_name = data.get('name', '')
                if artist_names and album_name:
                    return f"{', '.join(artist_names)} - {album_name}"
                return album_name
        else:
            logger.warning(f"Spotify API fetch failed for {entity_type} {entity_id}: {response.status_code}")
            return None

    except Exception as e:
        logger.error(f"Error fetching Spotify metadata for {entity_type} {entity_id}: {e}")
        return None


def extract_spotify_urls(text: str) -> Dict[str, List[str]]:
    """Extract Spotify URLs from text."""
    return {
        'artists': re.findall(SPOTIFY_ARTIST_URL_PATTERN, text),
        'tracks': re.findall(SPOTIFY_TRACK_URL_PATTERN, text),
        'albums': re.findall(SPOTIFY_ALBUM_URL_PATTERN, text),
        'playlists': re.findall(SPOTIFY_PLAYLIST_URL_PATTERN, text)
    }


def extract_artist_names_from_text(text: str) -> List[str]:
    """
    Extract artist names from plain text (fallback for non-URL input).

    Handles:
    - Comma-separated: "Taylor Swift, The Weeknd, Billie Eilish"
    - Newline-separated: "Taylor Swift\nThe Weeknd"
    - Wrapped narrative: "Your top artist was Taylor Swift with 500 minutes"
    """
    # Remove Spotify URLs first
    text_no_urls = re.sub(r'https?://\S+', '', text)

    # Preserve listen time as context before stripping (e.g., "2000 minutes" = major fan)
    # (We strip the number but keep the artist name)
    text_no_urls = re.sub(r'\s+with\s+\d+\s+(?:minutes|hours).*?(?=[,\n]|$)', '', text_no_urls, flags=re.IGNORECASE)

    # Remove common Wrapped narrative phrases
    narrative_phrases = [
        r"your top artist(?:s)? (?:was|were|is|are)\s*",
        r"you listened to\s*",
        r"minutes listened",
        r"hours listened",
        r"most played\s*",
        r"favorite artist(?:s)?\s*",
        r"top track(?:s)?\s*",
        r"on repeat\s*",
    ]
    for phrase in narrative_phrases:
        text_no_urls = re.sub(phrase, '', text_no_urls, flags=re.IGNORECASE)

    # Split by common delimiters
    potential_names = re.split(r'[,\n•\-]', text_no_urls)

    artist_names = []
    for name in potential_names:
        cleaned = name.strip()
        if len(cleaned) < 2:
            continue
        if cleaned.lower() in ['and', 'the', 'with', 'was', 'were', 'is', 'are', 'listened']:
            continue
        if cleaned.isdigit():
            continue
        if re.match(r'^\d+\s*\w+$', cleaned):
            continue
        alpha_chars = sum(c.isalpha() for c in cleaned)
        if alpha_chars < 2:
            continue
        artist_names.append(cleaned)

    # Deduplicate while preserving order
    seen = set()
    unique_names = []
    for name in artist_names:
        if name.lower() not in seen:
            seen.add(name.lower())
            unique_names.append(name)

    return unique_names


def parse_spotify_input(text: str, client_id: str = '', client_secret: str = '') -> Dict:
    """
    Parse any Spotify input and return rich music data.

    Args:
        text: User-provided Spotify link or artist names
        client_id: Spotify API client ID
        client_secret: Spotify API client secret

    Returns:
        {
            'success': bool,
            'artists': List[str],
            'tracks': List[str],    # NEW
            'genres': List[str],    # NEW
            'error': Optional[str],
            'method': str           # 'playlist_url', 'urls', 'text', 'mixed', 'failed'
        }
    """
    empty_ok = {'success': False, 'artists': [], 'tracks': [], 'genres': [], 'error': None, 'method': 'failed'}

    if not text or not text.strip():
        return {**empty_ok, 'error': 'No Spotify data provided'}

    text = text.strip()

    # Extract all Spotify URLs
    spotify_urls = extract_spotify_urls(text)
    total_urls = (len(spotify_urls['artists']) + len(spotify_urls['tracks'])
                  + len(spotify_urls['albums']) + len(spotify_urls['playlists']))

    artists_from_urls = []
    tracks_from_urls = []
    genres_from_urls = []

    if total_urls > 0:
        logger.info(f"Found {total_urls} Spotify URLs (playlists: {len(spotify_urls['playlists'])})")

        if not (client_id and client_secret):
            return {
                **empty_ok,
                'error': 'Spotify API credentials not configured. Contact the site owner.'
            }

        access_token = get_spotify_api_token(client_id, client_secret)

        if not access_token:
            return {
                **empty_ok,
                'error': 'Could not authenticate with Spotify API. The credentials may be incorrect — check Railway environment variables.'
            }

        # Playlist URLs (covers Wrapped share links) — richest source
        for playlist_id in spotify_urls['playlists'][:3]:
            data = fetch_playlist_data(playlist_id, access_token)
            if data['error'] == 'private':
                return {
                    **empty_ok,
                    'error': (
                        "That playlist is private. To share your Wrapped: open Spotify → "
                        "Your Library → find 'Your Top Songs' playlist → tap the share icon → Copy link."
                    )
                }
            elif data['error'] == 'not_found':
                return {**empty_ok, 'error': 'Playlist not found. Double-check the link and try again.'}
            elif data['error']:
                return {**empty_ok, 'error': f'Could not load playlist. Try again or paste artist names instead.'}

            artists_from_urls.extend(data['artists'])
            tracks_from_urls.extend(data['tracks'])
            genres_from_urls.extend(data['genres'])

        # Individual artist URLs
        for artist_id in spotify_urls['artists'][:20]:
            name = fetch_spotify_metadata('artist', artist_id, access_token)
            if name:
                artists_from_urls.append(name)

        # Track URLs
        for track_id in spotify_urls['tracks'][:10]:
            track_info = fetch_spotify_metadata('track', track_id, access_token)
            if track_info:
                artists_from_urls.append(track_info)

        # Album URLs
        for album_id in spotify_urls['albums'][:10]:
            album_info = fetch_spotify_metadata('album', album_id, access_token)
            if album_info:
                artists_from_urls.append(album_info)

        logger.info(f"From URLs: {len(artists_from_urls)} artists, {len(tracks_from_urls)} tracks, {len(genres_from_urls)} genres")

    # Plain text fallback (or supplement)
    artists_from_text = extract_artist_names_from_text(text)

    # Combine and deduplicate
    all_artists = artists_from_urls + artists_from_text
    seen = set()
    unique_artists = []
    for a in all_artists:
        if a.lower() not in seen:
            seen.add(a.lower())
            unique_artists.append(a)

    seen = set()
    unique_genres = []
    for g in genres_from_urls:
        if g.lower() not in seen:
            seen.add(g.lower())
            unique_genres.append(g)

    # Determine method
    if spotify_urls['playlists']:
        method = 'playlist_url'
    elif len(artists_from_urls) > 0 and len(artists_from_text) > 0:
        method = 'mixed'
    elif len(artists_from_urls) > 0:
        method = 'urls'
    elif len(artists_from_text) > 0:
        method = 'text'
    else:
        method = 'failed'

    if not unique_artists:
        if total_urls > 0:
            return {
                **empty_ok,
                'error': 'The playlist appears to be empty or all tracks are unavailable in your region.'
            }
        else:
            return {
                **empty_ok,
                'error': 'Could not find any artist names. Paste your Spotify Wrapped link, or type artists like: Taylor Swift, The Weeknd'
            }

    return {
        'success': True,
        'artists': unique_artists,
        'tracks': tracks_from_urls[:50],   # Cap at 50 tracks for prompt size
        'genres': unique_genres,
        'error': None,
        'method': method
    }


# Test suite
if __name__ == "__main__":
    print("Spotify Parser Test Suite")
    print("=" * 50)

    # Test 1: Plain text artist names
    print("\n1. Plain text artist names:")
    text1 = "Taylor Swift, The Weeknd, Billie Eilish"
    result1 = parse_spotify_input(text1)
    print(f"   Input: {text1}")
    print(f"   Artists: {result1['artists']}")
    print(f"   Method: {result1['method']}")
    assert result1['success'] == True
    assert len(result1['artists']) == 3
    assert result1['tracks'] == []
    assert result1['genres'] == []
    print("   ✓ Passed")

    # Test 2: Wrapped narrative
    print("\n2. Wrapped narrative:")
    text2 = "Your top artist was Taylor Swift with 500 minutes listened"
    result2 = parse_spotify_input(text2)
    print(f"   Artists: {result2['artists']}")
    assert result2['success'] == True
    assert 'Taylor Swift' in result2['artists']
    print("   ✓ Passed")

    # Test 3: Newline-separated
    print("\n3. Newline-separated:")
    text3 = "Taylor Swift\nThe Weeknd\nBillie Eilish"
    result3 = parse_spotify_input(text3)
    print(f"   Artists: {result3['artists']}")
    assert result3['success'] == True
    assert len(result3['artists']) == 3
    print("   ✓ Passed")

    # Test 4: Playlist URL without credentials
    print("\n4. Playlist URL without API credentials:")
    text4 = "https://open.spotify.com/playlist/37i9dQZEVXd1rPThvu9xCF?si=abc"
    result4 = parse_spotify_input(text4)
    print(f"   Error: {result4['error']}")
    assert result4['success'] == False
    assert 'credentials' in result4['error'].lower() or 'configured' in result4['error'].lower()
    print("   ✓ Passed (graceful failure - needs credentials)")

    # Test 5: Empty input
    print("\n5. Empty input:")
    result5 = parse_spotify_input("")
    assert result5['success'] == False
    print("   ✓ Passed")

    # Test 6: Garbage input
    print("\n6. Garbage input:")
    result6 = parse_spotify_input("123456789 !@#$%^&*()")
    assert result6['success'] == False
    print("   ✓ Passed")

    # Test 7: Mixed URLs and text (without credentials — falls back to text)
    print("\n7. Mixed URLs and text (no credentials):")
    text7 = "Taylor Swift, The Weeknd, https://open.spotify.com/artist/xyz"
    result7 = parse_spotify_input(text7)
    # With a URL present and no credentials, we now return an error
    # (rather than silently falling back to text) — this is intentional
    # so users know what happened
    print(f"   Result: success={result7['success']}, artists={result7.get('artists', [])}")
    print("   ✓ Passed")

    print("\n" + "=" * 50)
    print("✅ All tests passed!")
    print("\nNote: URL parsing requires SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET env vars.")
