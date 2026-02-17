"""
SPOTIFY INPUT PARSER
Handles any Spotify input: URLs, artist names, mixed text, or garbage

Gracefully extracts artist/track names from:
- Plain text: "Taylor Swift, The Weeknd, Billie Eilish"
- Spotify URLs: https://open.spotify.com/artist/06HL4z0CvFAxyc27GXpf02
- Wrapped narrative: "Your top artist was Taylor Swift with 500 minutes"
- Mixed: URLs + names + narrative

If input is unparseable → returns None with helpful error message

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


def extract_spotify_urls(text: str) -> Dict[str, List[str]]:
    """
    Extract Spotify URLs from text

    Returns:
        Dict with 'artists', 'tracks', 'albums' keys (lists of IDs)
    """
    return {
        'artists': re.findall(SPOTIFY_ARTIST_URL_PATTERN, text),
        'tracks': re.findall(SPOTIFY_TRACK_URL_PATTERN, text),
        'albums': re.findall(SPOTIFY_ALBUM_URL_PATTERN, text)
    }


def fetch_spotify_metadata(entity_type: str, entity_id: str, access_token: str) -> Optional[str]:
    """
    Fetch entity name from Spotify API

    Args:
        entity_type: 'artist', 'track', or 'album'
        entity_id: Spotify ID
        access_token: Spotify API access token

    Returns:
        Entity name (e.g., "Taylor Swift") or None if fetch fails
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
                # For tracks, return "Artist - Track Name"
                artist_names = [a.get('name', '') for a in data.get('artists', [])]
                track_name = data.get('name', '')
                if artist_names and track_name:
                    return f"{', '.join(artist_names)} - {track_name}"
                return track_name
            elif entity_type == 'album':
                # For albums, return "Artist - Album Name"
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


def get_spotify_api_token(client_id: str, client_secret: str) -> Optional[str]:
    """
    Get Spotify API access token using client credentials flow

    Returns:
        Access token or None if auth fails
    """
    try:
        auth_url = 'https://accounts.spotify.com/api/token'
        auth_data = {'grant_type': 'client_credentials'}
        auth = (client_id, client_secret)

        response = requests.post(auth_url, data=auth_data, auth=auth, timeout=10)

        if response.status_code == 200:
            token_data = response.json()
            return token_data.get('access_token')
        else:
            logger.error(f"Spotify token fetch failed: {response.status_code}")
            return None

    except Exception as e:
        logger.error(f"Error getting Spotify API token: {e}")
        return None


def extract_artist_names_from_text(text: str) -> List[str]:
    """
    Extract artist names from plain text (non-URL)

    Handles:
    - Comma-separated: "Taylor Swift, The Weeknd, Billie Eilish"
    - Newline-separated: "Taylor Swift\nThe Weeknd\nBillie Eilish"
    - Narrative: "Your top artist was Taylor Swift with 500 minutes"

    Returns:
        List of artist names (cleaned, deduplicated)
    """
    # Remove Spotify URLs first (so we only parse plain text)
    text_no_urls = re.sub(r'https?://\S+', '', text)

    # Remove stats patterns first (before removing narrative phrases)
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

    # Clean and filter
    artist_names = []
    for name in potential_names:
        cleaned = name.strip()
        # Filter out noise (numbers only, very short, common words)
        if len(cleaned) < 2:
            continue
        if cleaned.lower() in ['and', 'the', 'with', 'was', 'were', 'is', 'are', 'listened']:
            continue
        if cleaned.isdigit():
            continue
        # Skip fragments that are just numbers and words
        if re.match(r'^\d+\s*\w+$', cleaned):  # "500 minutes"
            continue
        # Skip mostly non-alphanumeric (garbage like "!@#$%^&*()")
        alpha_chars = sum(c.isalpha() for c in cleaned)
        if alpha_chars < 2:  # Need at least 2 letters to be valid
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
    Parse any Spotify input (URLs, names, mixed text)

    Args:
        text: User-provided Spotify data
        client_id: Spotify API client ID (optional, needed for URL parsing)
        client_secret: Spotify API client secret (optional, needed for URL parsing)

    Returns:
        {
            'success': bool,
            'artists': List[str],  # Artist names
            'error': Optional[str],  # Error message if failed
            'method': str  # 'urls', 'text', 'mixed', or 'failed'
        }
    """
    if not text or not text.strip():
        return {
            'success': False,
            'artists': [],
            'error': 'No Spotify data provided',
            'method': 'failed'
        }

    text = text.strip()

    # Extract Spotify URLs
    spotify_urls = extract_spotify_urls(text)
    total_urls = len(spotify_urls['artists']) + len(spotify_urls['tracks']) + len(spotify_urls['albums'])

    artists_from_urls = []
    artists_from_text = []

    # If URLs found, try to fetch metadata
    if total_urls > 0:
        logger.info(f"Found {total_urls} Spotify URLs in input")

        # Need API credentials to fetch metadata
        if client_id and client_secret:
            access_token = get_spotify_api_token(client_id, client_secret)

            if access_token:
                # Fetch artist names from URLs
                for artist_id in spotify_urls['artists'][:20]:  # Limit to 20 to avoid rate limits
                    name = fetch_spotify_metadata('artist', artist_id, access_token)
                    if name:
                        artists_from_urls.append(name)

                # Fetch track artists from URLs
                for track_id in spotify_urls['tracks'][:10]:  # Limit to 10
                    track_info = fetch_spotify_metadata('track', track_id, access_token)
                    if track_info:
                        artists_from_urls.append(track_info)

                # Fetch album artists from URLs
                for album_id in spotify_urls['albums'][:10]:  # Limit to 10
                    album_info = fetch_spotify_metadata('album', album_id, access_token)
                    if album_info:
                        artists_from_urls.append(album_info)

                logger.info(f"Fetched {len(artists_from_urls)} names from Spotify URLs")
            else:
                logger.warning("Could not get Spotify API token - URLs won't be parsed")
        else:
            logger.warning("Spotify API credentials not provided - URLs won't be parsed")

    # Extract artist names from plain text (non-URL)
    artists_from_text = extract_artist_names_from_text(text)
    logger.info(f"Extracted {len(artists_from_text)} names from plain text")

    # Combine results
    all_artists = artists_from_urls + artists_from_text

    # Deduplicate
    seen = set()
    unique_artists = []
    for artist in all_artists:
        if artist.lower() not in seen:
            seen.add(artist.lower())
            unique_artists.append(artist)

    # Determine method
    if len(artists_from_urls) > 0 and len(artists_from_text) > 0:
        method = 'mixed'
    elif len(artists_from_urls) > 0:
        method = 'urls'
    elif len(artists_from_text) > 0:
        method = 'text'
    else:
        method = 'failed'

    # Validate results
    if len(unique_artists) == 0:
        # Check if input was mostly URLs but we couldn't parse them
        if total_urls > 0 and not (client_id and client_secret):
            return {
                'success': False,
                'artists': [],
                'error': 'Found Spotify URLs but API credentials not configured. Please paste artist names instead of URLs.',
                'method': 'failed'
            }
        elif total_urls > 0:
            return {
                'success': False,
                'artists': [],
                'error': 'Could not parse Spotify URLs. Please try pasting artist names instead.',
                'method': 'failed'
            }
        else:
            return {
                'success': False,
                'artists': [],
                'error': 'Could not extract artist names from input. Please paste artist names (e.g., "Taylor Swift, The Weeknd") or Spotify URLs.',
                'method': 'failed'
            }

    return {
        'success': True,
        'artists': unique_artists,
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
    print(f"   Result: {result1['artists']}")
    print(f"   Method: {result1['method']}")
    assert result1['success'] == True
    assert len(result1['artists']) == 3
    print("   ✓ Passed")

    # Test 2: Wrapped narrative
    print("\n2. Wrapped narrative:")
    text2 = "Your top artist was Taylor Swift with 500 minutes listened"
    result2 = parse_spotify_input(text2)
    print(f"   Input: {text2}")
    print(f"   Result: {result2['artists']}")
    assert result2['success'] == True
    assert 'Taylor Swift' in result2['artists']
    print("   ✓ Passed")

    # Test 3: Newline-separated
    print("\n3. Newline-separated:")
    text3 = "Taylor Swift\nThe Weeknd\nBillie Eilish"
    result3 = parse_spotify_input(text3)
    print(f"   Input: {text3.replace(chr(10), ' / ')}")
    print(f"   Result: {result3['artists']}")
    assert result3['success'] == True
    assert len(result3['artists']) == 3
    print("   ✓ Passed")

    # Test 4: URLs without credentials (should fail gracefully)
    print("\n4. URLs without API credentials:")
    text4 = "https://open.spotify.com/artist/06HL4z0CvFAxyc27GXpf02"
    result4 = parse_spotify_input(text4)
    print(f"   Input: {text4}")
    print(f"   Result: {result4}")
    assert result4['success'] == False
    assert 'API credentials' in result4['error']
    print("   ✓ Passed (graceful failure)")

    # Test 5: Empty input
    print("\n5. Empty input:")
    text5 = ""
    result5 = parse_spotify_input(text5)
    print(f"   Input: (empty)")
    print(f"   Result: {result5}")
    assert result5['success'] == False
    print("   ✓ Passed (graceful failure)")

    # Test 6: Garbage input
    print("\n6. Garbage input:")
    text6 = "123456789 !@#$%^&*()"
    result6 = parse_spotify_input(text6)
    print(f"   Input: {text6}")
    print(f"   Result: {result6}")
    assert result6['success'] == False
    print("   ✓ Passed (graceful failure)")

    # Test 7: Mixed URLs and text (without credentials)
    print("\n7. Mixed URLs and text:")
    text7 = "Taylor Swift, The Weeknd, https://open.spotify.com/artist/xyz"
    result7 = parse_spotify_input(text7)
    print(f"   Input: {text7}")
    print(f"   Result: {result7['artists']}")
    assert result7['success'] == True  # Should succeed with text parsing
    assert 'Taylor Swift' in result7['artists']
    assert 'The Weeknd' in result7['artists']
    print("   ✓ Passed")

    print("\n" + "=" * 50)
    print("✅ All tests passed!")
    print("\nNote: URL parsing requires Spotify API credentials.")
    print("Set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET to test URL parsing.")
