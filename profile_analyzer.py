"""
PROFILE ANALYZER - Deep Analysis of Social Media Data
Extracts comprehensive recipient profile for gift curation

⚠️  OPUS-ONLY ZONE (partial) — The extraction prompt in this file feeds the
entire downstream pipeline. Sonnet sessions must NOT modify:
  - Section 1b OWNERSHIP SIGNALS prompt wording (drives the curator's
    ownership check and "upgrade vs complement" reasoning)
  - The aesthetic_summary field in the JSON schema (curator uses it for
    thematic matching — changing format breaks gift_curator.py)
  - The interest type taxonomy (aspirational|current) — the curator's
    aspiration-gap philosophy depends on this exact distinction
Safe for any session: adding new extraction sections, fixing JSON parsing,
adjusting interest intensity thresholds, bug fixes.
If you're Sonnet and see a profile quality issue, add "# SONNET-FLAG:" and move on.

Author: Chad + Claude
Date: February 2026
"""

import json
import logging
import re
import threading
from collections import Counter, defaultdict
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# In-flight dedup: prevents duplicate Claude API calls when two concurrent
# requests arrive for the same profile hash before either writes to cache.
# Thread A computes hash, checks cache (miss), starts Claude call.
# Thread B computes same hash, checks cache (still miss), would start ANOTHER call.
# With this lock, Thread B waits for Thread A to finish and uses its cached result.
_inflight_profiles = {}  # hash -> threading.Event
_inflight_lock = threading.Lock()

try:
    from enhanced_data_extraction import combine_all_signals
    ENHANCED_EXTRACTION_AVAILABLE = True
except ImportError:
    ENHANCED_EXTRACTION_AVAILABLE = False

# How much scraped data we use for inference. Higher = more signal, less "on the nose" (tradeoff: prompt size/cost).
INSTAGRAM_POSTS_FOR_ANALYSIS = 40   # Use top 40 by engagement (was 20)
INSTAGRAM_CAPTIONS_IN_SUMMARY = 28  # Captions sent to Claude (was 15)
INSTAGRAM_TOP_HASHTAGS = 30
TIKTOK_REPOSTS_FOR_ANALYSIS = 35     # Reposts are strong aspirational signals
TIKTOK_REPOST_DESCRIPTIONS_IN_SUMMARY = 25
TIKTOK_OWN_VIDEO_DESCRIPTIONS = 30    # Own video captions = what they actually post about (critical when reposts are few)
TIKTOK_FAVORITE_CREATORS = 12
PINTEREST_BOARDS_SAMPLED = 15
PINTEREST_PINS_PER_BOARD = 8
PINTEREST_PIN_DESCRIPTIONS_IN_SUMMARY = 35
PINTEREST_BOARD_NAMES = 20


# ---------------------------------------------------------------------------
# Pre-LLM signal extraction helpers (Items 1-4)
# These extract structured signals from raw platform data before sending to
# Claude, so the LLM receives facts rather than having to infer them from
# walls of captions.
# ---------------------------------------------------------------------------

def _parse_timestamp(ts_str):
    """Parse ISO-ish timestamp strings from Apify into a datetime (UTC).
    Returns None on failure — callers should skip posts with no valid timestamp."""
    if not ts_str:
        return None
    try:
        # Handle ISO format with or without timezone
        ts_str = str(ts_str).strip()
        # Remove trailing Z and treat as UTC
        if ts_str.endswith('Z'):
            ts_str = ts_str[:-1] + '+00:00'
        dt = datetime.fromisoformat(ts_str)
        # Normalize to UTC
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


def _extract_temporal_signals(posts, hashtag_key='hashtags', now=None):
    """Analyze post timestamps to detect recent vs dormant interests.

    Returns a dict with:
      - recent_hashtags: hashtags from last 30 days with counts
      - older_hashtags: hashtags from 30+ days ago with counts
      - recent_post_count / older_post_count
      - momentum_topics: hashtags that appear MORE in recent than older (rising)
      - fading_topics: hashtags that appear in older but NOT recent (declining)

    Designed to be additive — caller decides how to format for the prompt.
    """
    if now is None:
        now = datetime.now(timezone.utc)

    recent_hashtags = Counter()
    older_hashtags = Counter()
    recent_count = 0
    older_count = 0

    for p in posts:
        dt = _parse_timestamp(p.get('timestamp', ''))
        if dt is None:
            continue
        days_ago = (now - dt).days
        tags = p.get(hashtag_key, [])
        if days_ago <= 30:
            recent_count += 1
            recent_hashtags.update(tags)
        else:
            older_count += 1
            older_hashtags.update(tags)

    # Momentum: topics that are rising (more frequent recently, relative to post count)
    momentum = []
    fading = []
    if recent_count > 0 and older_count > 0:
        # Normalize rates per post
        for tag in set(list(recent_hashtags.keys()) + list(older_hashtags.keys())):
            recent_rate = recent_hashtags.get(tag, 0) / recent_count
            older_rate = older_hashtags.get(tag, 0) / older_count
            if recent_rate > older_rate * 1.5 and recent_hashtags.get(tag, 0) >= 2:
                momentum.append(tag)
            elif older_rate > 0 and recent_hashtags.get(tag, 0) == 0 and older_hashtags.get(tag, 0) >= 2:
                fading.append(tag)

    return {
        'recent_hashtags': recent_hashtags.most_common(15),
        'older_hashtags': older_hashtags.most_common(15),
        'recent_post_count': recent_count,
        'older_post_count': older_count,
        'momentum_topics': momentum[:10],
        'fading_topics': fading[:10],
    }


def _extract_engagement_spikes(posts, engagement_fn=None):
    """Find posts with 3x+ average engagement — high-resonance content.

    Returns list of (post, spike_ratio) tuples, sorted by ratio desc.
    """
    if not posts:
        return []

    if engagement_fn is None:
        engagement_fn = lambda p: p.get('likes', 0) + p.get('comments', 0) * 2

    engagements = [engagement_fn(p) for p in posts]
    avg = sum(engagements) / len(engagements) if engagements else 1

    spikes = []
    for p, eng in zip(posts, engagements):
        if avg > 0 and eng >= avg * 3:
            spikes.append((p, eng / avg))

    spikes.sort(key=lambda x: x[1], reverse=True)
    return spikes[:8]


def _extract_music_artists(tiktok_data):
    """Extract music artists used frequently in TikTok videos.

    Returns list of (artist, count) tuples for artists used 2+ times.
    These are concrete interest signals that don't need LLM inference.
    """
    top_artists = tiktok_data.get('top_music_artists', {})
    if not top_artists:
        # Fallback: iterate videos if top_music_artists wasn't aggregated
        artist_counts = Counter()
        for v in tiktok_data.get('videos', []):
            artist = v.get('music_artist', '')
            if artist and artist.lower() not in ('original sound', 'original audio',
                                                   'original', 'son original',
                                                   'som original'):
                artist_counts[artist] += 1
        top_artists = dict(artist_counts.most_common(10))

    # Filter: only artists used 2+ times (1x could be random/background)
    # Also filter out "original sound" variants
    _ORIGINAL_SOUND = {'original sound', 'original audio', 'original', 'son original', 'som original'}
    return [
        (artist, count)
        for artist, count in sorted(top_artists.items(), key=lambda x: x[1], reverse=True)
        if count >= 2 and artist.lower() not in _ORIGINAL_SOUND
    ]


# Known brand-indicator patterns for Instagram tagged accounts
_BRAND_SUFFIXES = {'official', 'hq', 'shop', 'store', 'brand', 'co', 'inc',
                   'boutique', 'studio', 'beauty', 'apparel', 'clothing',
                   'skincare', 'cosmetics', 'jewelry', 'jewellery', 'watches',
                   'coffee', 'brewing', 'fitness', 'athletics', 'outdoors'}

def _classify_tagged_accounts(tagged_counter):
    """Separate tagged Instagram accounts into likely-brand vs likely-personal.

    Heuristics (conservative — false negatives are fine, false positives hurt):
    - Contains a dot mid-name (e.g. free.people, glossier.official)
    - Ends with a brand suffix (e.g. nike_official, target_style)
    - Single word, no numbers, all lowercase (e.g. nike, glossier, sephora)

    Returns (brand_tags, personal_tags) as lists of (name, count).
    """
    brands = []
    personal = []

    for name, count in tagged_counter.most_common(30):
        name_lower = name.lower().strip('@')

        # Check for brand-indicator patterns
        is_brand = False

        # Dot in username (not at start/end) — very common for brands
        if '.' in name_lower and not name_lower.startswith('.') and not name_lower.endswith('.'):
            is_brand = True

        # Ends with a brand suffix after underscore or dot
        parts = re.split(r'[._]', name_lower)
        if len(parts) >= 2 and parts[-1] in _BRAND_SUFFIXES:
            is_brand = True

        # Single word, no numbers, 3+ chars — likely a brand handle (nike, sephora, target)
        if re.match(r'^[a-z]{3,20}$', name_lower) and count >= 2:
            is_brand = True

        if is_brand:
            brands.append((name, count))
        else:
            personal.append((name, count))

    return brands, personal


def build_recipient_profile(platforms, recipient_type, relationship, claude_client, model=None, gift_context=None):
    """
    Build comprehensive recipient profile from scraped social media data.

    Args:
        platforms: Dict of platform data (instagram, tiktok, pinterest)
        recipient_type: 'myself' or 'someone_else'
        relationship: Relationship type if someone_else
        claude_client: Anthropic client for AI analysis
        model: Claude model ID (default: claude-sonnet-4-20250514)

    Returns:
        Dict with structured profile data including:
        - interests: Specific interests with evidence
        - location_context: Where they live, places they frequent
        - style_preferences: Aesthetic, style signals
        - price_signals: Budget/price point indicators
        - aspirational_vs_current: What they want vs what they have
        - specific_venues: Actual places/venues mentioned
        - relationship_context: How relationship affects gifting
    """
    if not model:
        model = "claude-sonnet-4-20250514"

    logger.info("Building deep recipient profile...")

    # Profile caching (added Feb 2026 for cost reduction)
    profile_hash = None
    try:
        import config
        import database
        import hashlib

        if config.FEATURES.get('profile_caching', True):
            # Generate hash from platform data for cache lookup.
            # Include a prompt version so cache is invalidated when the
            # analysis prompt changes (e.g. interest attribution fix).
            _PROMPT_VERSION = "2026-04-18-signal-momentum-v1"
            cache_data = {
                'instagram': platforms.get('instagram', {}).get('data', {}),
                'tiktok': platforms.get('tiktok', {}).get('data', {}),
                'pinterest': platforms.get('pinterest', {}).get('data', {}),
                'spotify': platforms.get('spotify', {}).get('data', {}),
                'spotify_wrapped': platforms.get('spotify_wrapped', {}).get('wrapped_text', ''),
                'relationship': relationship,
                'gift_context': gift_context or '',
                '_prompt_version': _PROMPT_VERSION,
            }
            cache_str = json.dumps(cache_data, sort_keys=True)
            profile_hash = hashlib.sha256(cache_str.encode()).hexdigest()

            # Check cache for existing profile
            cached_profile = database.get_cached_profile(profile_hash)
            if cached_profile:
                logger.info(f"Profile found in cache (hash: {profile_hash[:8]}...), skipping Claude call")
                return cached_profile

            # In-flight dedup: if another thread is already analyzing this hash, wait for it
            with _inflight_lock:
                if profile_hash in _inflight_profiles:
                    logger.info(f"Profile {profile_hash[:8]}... already being analyzed by another thread, waiting...")
                    event = _inflight_profiles[profile_hash]
                else:
                    event = threading.Event()
                    _inflight_profiles[profile_hash] = event
                    event = None  # We're the first — proceed with analysis

            if event is not None:
                # Wait for the other thread to finish (max 120s)
                event.wait(timeout=120)
                # Now check cache again — the other thread should have written it
                cached_profile = database.get_cached_profile(profile_hash)
                if cached_profile:
                    logger.info(f"Profile available from parallel thread (hash: {profile_hash[:8]}...)")
                    return cached_profile
                logger.warning(f"Parallel thread didn't cache profile {profile_hash[:8]}..., proceeding with own analysis")

            logger.info(f"Profile not in cache (hash: {profile_hash[:8]}...), proceeding with Claude analysis")
    except ImportError:
        logger.info("Database/config not available, skipping profile caching")
    except Exception as e:
        logger.error(f"Profile cache lookup failed: {e}, proceeding with Claude call")

    # Extract raw data from platforms
    instagram_data = platforms.get('instagram', {}).get('data', {})
    tiktok_data = platforms.get('tiktok', {}).get('data', {})
    pinterest_data = platforms.get('pinterest', {}).get('data', {})
    
    # Build comprehensive data summary for Claude
    data_summary = []
    
    # Instagram analysis
    if instagram_data:
        posts = instagram_data.get('posts', [])
        username = instagram_data.get('username', 'unknown')
        bio = instagram_data.get('bio', '')
        followers = instagram_data.get('followers', 0)

        # Get high-engagement posts (strongest signals)
        sorted_posts = sorted(posts, key=lambda p: (p.get('likes', 0) + p.get('comments', 0) * 2), reverse=True)
        high_engagement = [p for p in sorted_posts if (p.get('likes', 0) + p.get('comments', 0) * 2) > 50]

        # Use top posts for analysis (more = better inference, less "on the nose")
        n_posts = min(INSTAGRAM_POSTS_FOR_ANALYSIS, len(sorted_posts))
        priority_posts = (high_engagement[:n_posts] if high_engagement else sorted_posts[:n_posts])

        # Extract captions, hashtags, locations, tagged users
        captions = [p.get('caption', '')[:200] for p in priority_posts if p.get('caption')]
        hashtags_all = []
        locations = []
        tagged_accounts = Counter()
        for p in priority_posts:
            hashtags_all.extend(p.get('hashtags', []))
            loc = p.get('location', '')
            if loc:
                locations.append(loc)
            for tagged in p.get('tagged_users', []):
                tag_name = tagged if isinstance(tagged, str) else tagged.get('username', '') or tagged.get('full_name', '')
                if tag_name:
                    tagged_accounts[tag_name] += 1

        top_hashtags = [tag for tag, count in Counter(hashtags_all).most_common(INSTAGRAM_TOP_HASHTAGS)]

        # Bio section - direct self-description is high-value signal
        bio_section = ""
        if bio:
            bio_section = f"\nBIO (self-described identity - strong signal): {bio}"

        # Follower context
        follower_section = ""
        if followers and followers > 0:
            follower_section = f"\n- Followers: {followers:,}"

        # [Item 4] Separate tagged accounts into brand vs personal
        tagged_section = ""
        brand_affinity_section = ""
        if tagged_accounts:
            brand_tags, personal_tags = _classify_tagged_accounts(tagged_accounts)
            if brand_tags:
                brand_affinity_section = (
                    "\nBRAND AFFINITIES (accounts tagged that appear to be brands — "
                    "direct ownership/loyalty signal, stronger than hashtags):\n" +
                    "\n".join(f"- @{t} ({c}x)" for t, c in brand_tags[:15])
                )
            # Keep personal tags in the existing format (less prominent)
            if personal_tags:
                tagged_section = f"\nTAGGED PEOPLE (friends, collaborators): {', '.join(f'@{t} ({c}x)' for t, c in personal_tags[:15])}"

        # Engagement relative to their own average (more meaningful than absolute)
        # [Item 2] Calculate average over ALL posts (not just priority_posts) for a true baseline
        all_engagements = [(p.get('likes', 0) + p.get('comments', 0) * 2) for p in posts]
        avg_engagement = sum(all_engagements) / len(all_engagements) if all_engagements else 1
        standout_posts = [p for p in priority_posts if (p.get('likes', 0) + p.get('comments', 0) * 2) > avg_engagement * 2]

        # [Item 2] True spikes (3x+ average across ALL posts) — high-resonance content
        ig_spikes = _extract_engagement_spikes(posts)
        spike_section = ""
        if ig_spikes:
            spike_lines = []
            for p, ratio in ig_spikes[:5]:
                caption = (p.get('caption', '') or '')[:120]
                spike_lines.append(f"- [{ratio:.1f}x avg] {caption}")
            spike_section = (
                f"\nHIGH-RESONANCE POSTS ({len(ig_spikes)} posts with 3x+ their normal engagement — "
                "these topics are core identity, not just passing content):\n" +
                "\n".join(spike_lines)
            )

        # [Item 1] Temporal signals — recent vs older interest patterns
        temporal_section = ""
        temporal = _extract_temporal_signals(posts)
        if temporal['recent_post_count'] > 0 and temporal['older_post_count'] > 0:
            parts = []
            if temporal['momentum_topics']:
                parts.append(f"Rising interests (more frequent recently): {', '.join(temporal['momentum_topics'][:8])}")
            if temporal['fading_topics']:
                parts.append(f"Fading interests (absent from recent posts): {', '.join(temporal['fading_topics'][:8])}")
            if temporal['recent_hashtags']:
                recent_tags = [f"{t} ({c}x)" for t, c in temporal['recent_hashtags'][:10]]
                parts.append(f"Last 30 days focus ({temporal['recent_post_count']} posts): {', '.join(recent_tags)}")
            if parts:
                temporal_section = "\nTEMPORAL SIGNALS (what's current vs fading — prioritize recent activity):\n" + "\n".join(f"- {p}" for p in parts)

        data_summary.append(f"""
INSTAGRAM PROFILE (@{username} - {len(posts)} posts analyzed):{bio_section}

HIGH ENGAGEMENT POSTS ({len(high_engagement)} posts with 50+ engagement):
{chr(10).join(['- ' + c for c in captions[:INSTAGRAM_CAPTIONS_IN_SUMMARY]])}

TOP HASHTAGS: {', '.join(top_hashtags)}

GEOTAGGED LOCATIONS (structured - these are real venue/place tags, not guesses): {', '.join(set(locations[:15])) if locations else 'none'}
{brand_affinity_section}{tagged_section}{spike_section}{temporal_section}
STANDOUT POSTS ({len(standout_posts)} posts with 2x+ their average engagement - these topics resonate MOST):
{chr(10).join(['- ' + (p.get('caption', '')[:150]) for p in standout_posts[:8]]) if standout_posts else '(none)'}

POST PATTERNS:
- Average likes: {sum(p.get('likes', 0) for p in priority_posts) / len(priority_posts) if priority_posts else 0:.0f}
- Average comments: {sum(p.get('comments', 0) for p in priority_posts) / len(priority_posts) if priority_posts else 0:.0f}
- Posting frequency: {len(posts)} posts in recent history{follower_section}
""")
    
    # TikTok analysis
    if tiktok_data:
        videos = tiktok_data.get('videos', [])
        reposts = tiktok_data.get('reposts', [])
        username = tiktok_data.get('username', 'unknown')
        
        # OWN VIDEO CONTENT: What they actually post about (critical when they "post a ton" but repost little)
        sorted_videos = sorted(videos, key=lambda v: (v.get('likes', 0) + v.get('comments', 0) * 2), reverse=True)
        own_descriptions = [v.get('description', '')[:150] for v in sorted_videos if v.get('description')]
        n_own = min(TIKTOK_OWN_VIDEO_DESCRIPTIONS, len(own_descriptions))
        # Hashtags from all videos (own + reposts) for full picture
        all_hashtags = []
        for v in videos:
            all_hashtags.extend(v.get('hashtags', []))
        top_video_hashtags = [tag for tag, count in Counter(all_hashtags).most_common(30)]
        
        # Reposts show aspirational interests
        n_reposts = min(TIKTOK_REPOSTS_FOR_ANALYSIS, len(reposts))
        repost_descriptions = [r.get('description', '')[:150] for r in reposts[:n_reposts] if r.get('description')]
        repost_hashtags = []
        for r in reposts[:n_reposts]:
            repost_hashtags.extend(r.get('hashtags', []))
        top_repost_hashtags = [tag for tag, count in Counter(repost_hashtags).most_common(30)]
        favorite_creators = tiktok_data.get('favorite_creators', [])
        top_music = tiktok_data.get('top_music', {})

        # Music taste section - strong signal for experiences and style
        music_section = ""
        if top_music:
            music_items = list(top_music.items())[:10]
            music_lines = [f"- {track} ({count}x)" for track, count in music_items]
            music_section = f"""
MUSIC TASTE (songs used in their videos - indicates music preferences, concert interests, aesthetic):
{chr(10).join(music_lines)}
"""

        # [Item 3] Music artist extraction — concrete interest signals without LLM inference.
        # If someone uses Fleetwood Mac in 4 videos, that's a direct interest.
        music_artist_section = ""
        music_artists = _extract_music_artists(tiktok_data)
        if music_artists:
            artist_lines = [f"- {artist} ({count} videos)" for artist, count in music_artists]
            music_artist_section = (
                "\nMUSIC ARTISTS (repeatedly used in videos — these are direct interest signals, "
                "treat each as a confirmed interest for merch, vinyl, concert tickets):\n" +
                "\n".join(artist_lines)
            )

        # [Item 2] Engagement spikes for TikTok (3x+ average)
        tt_engagement_fn = lambda v: v.get('likes', 0) + v.get('comments', 0) * 2 + v.get('shares', 0) * 3
        tt_spikes = _extract_engagement_spikes(videos, engagement_fn=tt_engagement_fn)
        tt_spike_section = ""
        if tt_spikes:
            spike_lines = []
            for v, ratio in tt_spikes[:5]:
                desc = (v.get('description', '') or '')[:120]
                spike_lines.append(f"- [{ratio:.1f}x avg] {desc}")
            tt_spike_section = (
                f"\nHIGH-RESONANCE VIDEOS ({len(tt_spikes)} videos with 3x+ their normal engagement — "
                "core identity content):\n" +
                "\n".join(spike_lines)
            )

        # [Item 1] Temporal signals for TikTok
        tt_temporal_section = ""
        tt_temporal = _extract_temporal_signals(videos)
        if tt_temporal['recent_post_count'] > 0 and tt_temporal['older_post_count'] > 0:
            parts = []
            if tt_temporal['momentum_topics']:
                parts.append(f"Rising interests (more frequent recently): {', '.join(tt_temporal['momentum_topics'][:8])}")
            if tt_temporal['fading_topics']:
                parts.append(f"Fading interests (absent from recent posts): {', '.join(tt_temporal['fading_topics'][:8])}")
            if tt_temporal['recent_hashtags']:
                recent_tags = [f"{t} ({c}x)" for t, c in tt_temporal['recent_hashtags'][:10]]
                parts.append(f"Last 30 days ({tt_temporal['recent_post_count']} videos): {', '.join(recent_tags)}")
            if parts:
                tt_temporal_section = "\nTEMPORAL SIGNALS (prioritize recent activity over older content):\n" + "\n".join(f"- {p}" for p in parts)

        data_summary.append(f"""
TIKTOK PROFILE (@{username} - {len(videos)} videos, {len(reposts)} reposts):

OWN VIDEO CONTENT (What they POST - use this for current interests and variety):
{chr(10).join(['- ' + d for d in own_descriptions[:n_own]]) if own_descriptions else '(no captions)'}

VIDEO HASHTAGS (all videos): {', '.join(top_video_hashtags) if top_video_hashtags else 'none'}
{music_section}{music_artist_section}{tt_spike_section}{tt_temporal_section}
ASPIRATIONAL CONTENT (REPOSTS - What they WANT):
{chr(10).join(['- ' + d for d in repost_descriptions[:TIKTOK_REPOST_DESCRIPTIONS_IN_SUMMARY]]) if repost_descriptions else '(no repost captions)'}

REPOST HASHTAGS: {', '.join(top_repost_hashtags)}

FAVORITE CREATORS (Aspirational aesthetics):
{chr(10).join([f"- @{creator[0]} ({creator[1]} reposts)" for creator in favorite_creators[:TIKTOK_FAVORITE_CREATORS]])}

CRITICAL: Own videos show what they do and care about; reposts show what they want. When there are many own-video captions, extract MULTIPLE distinct interests (8-12), not one theme.
""")
    
    # Pinterest analysis
    if pinterest_data:
        boards = pinterest_data.get('boards', [])
        
        # Extract board themes
        board_names = [b.get('name', '') for b in boards]
        
        # Sample pins from boards (more boards/pins = better wishlist signal)
        all_pins = []
        for board in boards[:PINTEREST_BOARDS_SAMPLED]:
            pins = board.get('pins', [])
            all_pins.extend(pins[:PINTEREST_PINS_PER_BOARD])
        
        pin_descriptions = [p.get('description', '')[:100] for p in all_pins if p.get('description')]
        
        data_summary.append(f"""
PINTEREST PROFILE ({len(boards)} boards):

BOARD THEMES: {', '.join(board_names[:PINTEREST_BOARD_NAMES])}

PIN DESCRIPTIONS (Explicit wishlist signals):
{chr(10).join(['- ' + d for d in pin_descriptions[:PINTEREST_PIN_DESCRIPTIONS_IN_SUMMARY]])}

CRITICAL NOTE: Pinterest boards are explicit wishlists - they're pinning exactly what they want.
""")

    # Spotify data — prefer OAuth (richer) over manual wrapped text
    # OAuth saves to platforms['spotify']['data'], manual saves to platforms['spotify_wrapped']
    spotify_oauth = platforms.get('spotify', {})
    spotify_wrapped = platforms.get('spotify_wrapped', {})

    if spotify_oauth.get('data'):
        # OAuth data: top_artists list, top_genres dict, top_tracks list
        oauth_data = spotify_oauth['data']
        spotify_artists = oauth_data.get('top_artists', [])
        spotify_genres = list(oauth_data.get('top_genres', {}).keys())
        spotify_tracks = oauth_data.get('top_tracks', [])
    else:
        # Manual entry or wrapped text fallback
        spotify_artists = spotify_wrapped.get('artists', [])
        spotify_tracks = spotify_wrapped.get('tracks', [])
        spotify_genres = spotify_wrapped.get('genres', [])

    # Detect if Spotify is the only data source (no social media posts)
    spotify_is_only_source = bool(spotify_artists) and not instagram_data and not tiktok_data and not pinterest_data

    if spotify_artists:
        # Build a rich music section — artists, genres, and sample tracks all carry signal
        lines = []
        lines.append(f"Top artists: {', '.join(spotify_artists)}")

        if spotify_genres:
            lines.append(f"Genres: {', '.join(spotify_genres)}")

        if spotify_tracks:
            # Sample tracks give a taste/vibe signal beyond just artist names
            # Tracks may be dicts {'name': ..., 'artist': ...} (OAuth) or plain strings (manual)
            track_labels = [
                f"{t['name']} - {t['artist']}" if isinstance(t, dict) else str(t)
                for t in spotify_tracks[:30]
            ]
            lines.append(f"Sample tracks: {', '.join(track_labels)}")

        # When Spotify is the ONLY signal, give the analyzer much more specific guidance
        if spotify_is_only_source:
            spotify_guidance = """
THIS IS THE ONLY DATA SOURCE. You must mine it deeply — every artist, genre, and track is a signal.

CRITICAL RULES FOR SPOTIFY-ONLY PROFILES:
1. **Extract SPECIFIC artist names as interests** — "The Misfits" or "Billie Eilish" are interests, not "horror punk music". Use the artist name so search queries find merch, vinyl, and fan gear for THAT artist.
2. **Stay grounded in what the music data actually shows.** Do NOT make multi-hop lifestyle inferences. "They listen to jazz" does NOT mean they drink craft cocktails or go to speakeasies — those are stereotypes, not evidence. Only infer what the data directly supports.
3. **Music-adjacent interests only** — the safe inferences from music data are: vinyl/record collecting (if genres suggest collector taste), band merch (for any artist), music books/biographies (for artists with strong cultural footprint), instruments/accessories (if multiple genre clusters suggest active musicianship), and concert tickets (only for artists who actively tour).
4. **Identify specific giftable PRODUCTS from the music** — band/artist merch, music books, instruments/accessories. These are what music data actually supports.
5. **Do NOT produce generic genre labels as interest names.** "Christmas music and holiday traditions" → bad. "Bing Crosby" (artist name) → good. Always translate to something searchable.
6. **VINYL IS A COLLECTOR IDENTITY SIGNAL, NOT A GENRE MODIFIER.** Treat it as a separate standalone interest:
   - RIGHT: "The Misfits" as one interest + "vinyl record collecting" as a separate interest
   - WRONG: "Horror punk vinyl" (too niche — searches return nothing useful)
   - WRONG: "Bing Crosby vinyl" (compound name — just use "Bing Crosby", the artist interest naturally surfaces their records)
   - If someone's listening history suggests a collector (indie/classic/varied catalog, genres known for vinyl culture), add "vinyl record collecting" as its own interest. It finds turntables, storage, cleaning kits, record sleeves — the whole collector lifestyle.
7. **Each interest should be SEARCHABLE as a product query** — "Tiger Army" finds merch; "vinyl record collecting" finds collector gear; "Broadway cast recording" finds albums. "Jazz culture" finds nothing useful. "Horror punk vinyl" finds nothing useful either.
8. **Aim for 8-10 interests total: 3-4 specific artists + 3-4 music-adjacent product interests + 1-2 genre/aesthetic interests with direct product evidence.** Skip "experience" interests entirely unless there's a specific touring artist where concert tickets make clear sense.
"""
        else:
            spotify_guidance = """
Use this to infer personality, aesthetic, and lifestyle — not just music gifts. A person who listens to indie folk likely has different taste from someone into hyperpop or country. Music genre and artist choices are strong signals for gift categories like fashion, home decor, experiences, and hobbies.
"""

        data_summary.append(f"""
SPOTIFY MUSIC PREFERENCES:

{chr(10).join(lines)}

{spotify_guidance}
""")
        logger.info(f"Including Spotify: {len(spotify_artists)} artists, {len(spotify_genres)} genres, {len(spotify_tracks)} tracks")
    elif spotify_wrapped.get('wrapped_text'):
        # Legacy fallback: old data format without parsed fields — try on-the-fly
        logger.warning("Spotify data in old format (no parsed artists) - attempting on-the-fly parsing")
        try:
            from spotify_parser import parse_spotify_input
            import os
            parse_result = parse_spotify_input(
                spotify_wrapped['wrapped_text'],
                client_id=os.environ.get('SPOTIFY_CLIENT_ID', ''),
                client_secret=os.environ.get('SPOTIFY_CLIENT_SECRET', '')
            )
            if parse_result['success'] and parse_result['artists']:
                lines = [f"Top artists: {', '.join(parse_result['artists'][:50])}"]
                if parse_result.get('genres'):
                    lines.append(f"Genres: {', '.join(parse_result['genres'][:20])}")
                if parse_result.get('tracks'):
                    lines.append(f"Sample tracks: {', '.join(parse_result['tracks'][:30])}")
                data_summary.append(f"""
SPOTIFY MUSIC PREFERENCES:

{chr(10).join(lines)}

Use this to infer personality, aesthetic, and lifestyle — not just music gifts.
""")
                logger.info(f"On-the-fly parsing succeeded: {len(parse_result['artists'])} artists")
            else:
                logger.warning(f"On-the-fly Spotify parsing failed: {parse_result.get('error', 'unknown error')}")
        except Exception as e:
            logger.error(f"Failed to parse legacy Spotify data: {e}")
    else:
        logger.debug("No Spotify data in platforms")

    # Enhanced signal extraction (brands, aesthetics, activities, engagement patterns)
    if ENHANCED_EXTRACTION_AVAILABLE:
        try:
            platform_bundle = {}
            if instagram_data:
                platform_bundle['instagram'] = instagram_data
            if tiktok_data:
                platform_bundle['tiktok'] = tiktok_data
            if pinterest_data:
                platform_bundle['pinterest'] = pinterest_data

            signals = combine_all_signals(platform_bundle)
            combined = signals.get('combined', {})

            enhanced_sections = []

            # Brand mentions across all platforms
            all_brands = combined.get('all_brands', {})
            if all_brands:
                brand_items = list(all_brands.items())[:12]
                enhanced_sections.append(
                    "BRAND MENTIONS (across all platforms): " +
                    ", ".join(f"{b} ({c}x)" for b, c in brand_items)
                )

            # Aesthetic/style keywords
            all_aesthetics = combined.get('all_aesthetics', {})
            if all_aesthetics:
                aes_items = list(all_aesthetics.items())[:10]
                enhanced_sections.append(
                    "AESTHETIC PREFERENCES: " +
                    ", ".join(f"{a} ({c}x)" for a, c in aes_items)
                )

            # Activity types
            all_activities = combined.get('all_activities', {})
            if all_activities:
                act_items = list(all_activities.items())[:12]
                enhanced_sections.append(
                    "ACTIVITY PATTERNS: " +
                    ", ".join(f"{a} ({c}x)" for a, c in act_items)
                )

            # High engagement topics
            high_engagement_topics = combined.get('high_engagement_topics', [])
            if high_engagement_topics:
                enhanced_sections.append(
                    "HIGH ENGAGEMENT TOPICS (what resonates most): " +
                    ", ".join(high_engagement_topics[:15])
                )

            # Aspirational vs current from cross-platform analysis
            aspirational = combined.get('aspirational_interests', [])
            current = combined.get('current_interests', [])
            if aspirational:
                enhanced_sections.append(
                    "CROSS-PLATFORM ASPIRATIONAL SIGNALS: " +
                    ", ".join(aspirational[:10])
                )
            if current:
                enhanced_sections.append(
                    "CROSS-PLATFORM CURRENT INTERESTS: " +
                    ", ".join(current[:10])
                )

            # Want signals — explicit purchase intent ("I need this", "someone buy me", etc.)
            want_signals = combined.get('want_signals', [])
            if want_signals:
                want_lines = [f"- \"{ws['text'][:100]}\" (from {ws.get('source', 'unknown')})" for ws in want_signals[:8]]
                enhanced_sections.append(
                    "EXPLICIT WANT SIGNALS (they literally said they want these — highest priority for gifts):\n" +
                    "\n".join(want_lines)
                )

            # Cross-platform confirmed interests
            cross_confirmed = combined.get('cross_platform_confirmed', [])
            if cross_confirmed:
                confirmed_lines = [f"{cc['interest']} ({cc['platforms']} platforms)" for cc in cross_confirmed[:8]]
                enhanced_sections.append(
                    "CROSS-PLATFORM CONFIRMED (these interests appear on multiple platforms — core identity, not passing fads): " +
                    ", ".join(confirmed_lines)
                )

            if enhanced_sections:
                data_summary.append(f"""
CROSS-PLATFORM INTELLIGENCE (extracted patterns across all platforms):

{chr(10).join(enhanced_sections)}

Use these signals to inform style preferences, brand affinities, and interest intensity.
PRIORITY: Want signals > cross-platform confirmed > high engagement > aspirational > everything else.
""")
        except Exception as e:
            logger.warning(f"Enhanced data extraction failed (continuing without): {e}")

    # Build the analysis prompt
    relationship_context = ""
    if recipient_type == 'someone_else' and relationship:
        relationship_context = f"\nRELATIONSHIP TYPE: {relationship}\nThis affects what kinds of gifts are appropriate (e.g., romantic vs. friendly vs. professional)."

    # Sanitize gift_context against prompt injection: wrap in explicit delimiters,
    # strip any closing delimiter sequences the user might try to inject.
    gift_context_section = ""
    if gift_context and gift_context.strip():
        safe_context = gift_context.strip().replace('---END GIFT-GIVER NOTE---', '').replace('</gift_context>', '')
        has_social_data = bool(data_summary)
        if has_social_data:
            gift_context_section = f"""

---GIFT-GIVER NOTE (first-hand knowledge — treat as high-confidence signal)---
{safe_context}
---END GIFT-GIVER NOTE---
If this note mentions a hobby, interest, life event, or product category not visible in the social data, add it as a confirmed interest with high confidence. The gift-giver knows this person directly."""
        else:
            gift_context_section = f"""

---PRIMARY INPUT (no social media — this description is your only signal)---
{safe_context}
---END PRIMARY INPUT---
There is no social media data. Build the entire profile from this description. Extract every interest, hobby, life stage clue, aesthetic preference, and price signal you can. Be generous — infer from context (e.g. "obsessed with his smoker" → passionate, active interest in BBQ/grilling/outdoor cooking). Aim for 4-8 interests minimum."""
        logger.info("Gift context injected into profile analyzer prompt (%d chars, has_social=%s)",
                    len(safe_context), has_social_data)

    prompt_intro = "Analyze this person's social media data and build a comprehensive profile for gift curation." if data_summary else "Build a gift-recipient profile from the description below."

    prompt = f"""{prompt_intro}

{chr(10).join(data_summary)}{relationship_context}{gift_context_section}

SIGNAL PRIORITY (use these to weight your analysis):
- **BRAND AFFINITIES**: Tagged brands are direct evidence of ownership/loyalty. Include the brand in style_preferences.brands.
- **MUSIC ARTISTS**: Artists listed under "MUSIC ARTISTS" are confirmed interests — treat each as a named interest (for merch, vinyl, concert tickets).
- **TEMPORAL SIGNALS**: Prioritize "rising" interests over "fading" ones. Set confidence to "low" for interests that appear only in older content.
- **HIGH-RESONANCE content** (3x+ engagement): These topics are core identity. Weight them higher than average posts.

Extract and structure the following information:

HUMAN vs PET DISAMBIGUATION (check this before interest extraction):
When a recurring name appears in the data (Harlow, Max, Lucy, Bella, Charlie, Cooper, Luna, Rocky, etc.), decide whether it refers to a human (child, partner, family member) or an animal using surrounding evidence.
- Human child cues: birthday cake + candles, age in years ("turned 3", "her first birthday"), school/daycare/preschool references, height/growth comments, photos with cribs/car seats/strollers, first steps/first words language, clothing sizes in toddler/kid terms.
- Dog/pet cues: "pup", "puppy", "walks", "good boy/girl", paw emoji, leash, vet visits, breed mentions ("golden retriever"), dog park references.
- DEFAULT WHEN AMBIGUOUS: treat as human child. A false-positive child produces better gifts than a false-positive dog.
- If the name refers to a human child (or any human), do NOT extract "dog ownership", "pet parent", or similar animal-care interests on the basis of posts about that person.

1. **SPECIFIC INTERESTS** (not generic categories - specific, evidence-based interests):
   - List 8-12 specific interests with concrete evidence. When the person has many posts/videos (e.g. 50+), you MUST extract multiple distinct interests—do NOT collapse everything into one or two themes.
   - For each interest: name, evidence from posts, intensity (casual/moderate/passionate), type (aspirational|current)
   - **is_work**: true ONLY if this is clearly their job/profession (e.g. "paramedic", "works at venue"); false for hobbies
   - **activity_type**: "passive" if they mainly watch/collect/consume (e.g. anime fan, book reader); "active" if they do it (cooking, sports); "both" if unclear
   - **INTEREST ATTRIBUTION — CRITICAL**: Extract ONLY the account owner's personal interests. NOT their family's, NOT their friends', NOT people they're proud of.
     COMMON TRAPS (you MUST check for these):
     - "My brother went fly fishing" → This is the BROTHER's interest, not the poster's. Do NOT include.
     - "So proud of my sister's marathon" → SISTER's hobby. Do NOT include.
     - "Took my dad golfing" → Only include if the poster ALSO golfs independently.
     - Reposting someone else's content with hashtags (#flyfishing, #catchandrelease) → REPOSTED content, NOT the poster's hobby. Do NOT include unless the poster is shown personally doing the activity.
     - Posting ABOUT someone's accomplishments ≠ personal interest. Cheering for a family member's hobby is family pride, not a hobby.
     HOW TO VERIFY: For each interest, ask "Does this person DO this activity themselves, or are they posting about someone else doing it?" If the evidence is ONLY about someone else, exclude it entirely — do not even include it as low confidence.
     HASHTAG TRAP: Hashtags alone (#flyfishing, #fishtok) are NOT sufficient evidence. The poster must be shown DOING the activity in first-person language ("I fish", "my catch", "I went fishing") or visible in photos doing it. Reposted content inherits the original creator's hashtags — those are NOT the reposter's interests.
     Look for first-person language ("I love", "my new", "I can't stop") vs. third-person ("my brother's", "her favorite", "he caught", "proud of him/her").
   - **ENGAGEMENT WEIGHTING**: Posts with significantly higher likes/views than the account's average signal core interests. A post with 5x the usual engagement reveals what resonates most. When the data includes engagement metrics, weight interests from high-engagement content higher than passing mentions.
   - **META-TRAIT BAN**: DO NOT extract personality attributes or meta-traits as interests. "Thoughtful gift giving", "being a good friend", "kindness", "caring for others" — these are personality descriptors, not shoppable interests. If you find yourself writing an interest that cannot be searched on Amazon or bought in a store, delete it.
   - **signal_quotes** (required, 0-3 per interest): Include up to 3 VERBATIM snippets from the raw data that support this interest — actual caption fragments, hashtags, tagged account names, artist names, place names, show titles, author names, or other specific entities mentioned. Keep each quote under 120 characters; truncate mid-phrase with an ellipsis if needed. Prefer concrete proper nouns over adjective-only fragments (e.g. "just finished Abundance by @ezraklein" beats "loves reading"). If the raw data does not contain a usable quote for this interest, return an empty list — DO NOT invent or paraphrase. These quotes drive downstream gift ideation — they are the difference between a generic "political activism" gift and one grounded in THIS person's actual signals.
   - **signal_momentum** (required): One of "rising" | "stable" | "fading". Use the TEMPORAL SIGNALS section above when available:
     • "rising" = interest appears in the rising/momentum list, OR clearly more frequent in recent posts than older ones, OR is tied to a current cultural moment (recent event, viral moment, recent news cycle) where the person's engagement may be ephemeral
     • "fading" = interest appears in the fading list, OR present in older content but absent recently
     • "stable" = the default. Established interest with sustained activity over time, OR interest where timing is unclear (no temporal signal). Most interests should be "stable" unless evidence pushes them otherwise.
     This drives the downstream durability gate: high-commitment gifts (travel, permanent installations, $300+) should NOT be built on "rising" interests, since those may be moments rather than identity. When in doubt, choose "stable" — it preserves more gift ideation latitude than "rising" does.
   - Example: "Thai cooking (passionate, current, active, momentum: stable) - Posted pad thai 5x, tagged #thaifood 8x over 18 months"

1b. **OWNERSHIP SIGNALS** (what they ALREADY HAVE — critical for avoiding duplicate gifts):
   - If they're holding, wearing, or standing in front of something in photos, they own it. Don't recommend it.
   - Note specific products/brands visible in their content (e.g., "has a Hydro Flask", "wears Nike frequently", "owns a Cricut machine")
   - This helps the gift curator recommend upgrades or complements rather than duplicates.

2. **LOCATION CONTEXT**:
   - Where they live/are based (city, region) - ONLY if you have clear evidence (posts, venues, bio)
   - If city_region is unknown, do NOT invent a city; leave null
   - Specific places they frequent (restaurants, venues, neighborhoods)
   - Geographic constraints for experiences
   - If no clear location, state "Unknown - location-based recommendations not possible"

3. **STYLE & AESTHETIC PREFERENCES**:
   - Visual style (minimalist, maximalist, vintage, modern, bohemian, industrial, coastal, cottagecore, etc.)
   - Color preferences
   - Overall aesthetic sensibility: Look at their photos holistically — are their spaces cluttered or sparse? Are their outfits coordinated or casual? Do they favor earth tones or bold colors? Describe in 1-2 sentences.
   - Brand preferences — be EXHAUSTIVE. List EVERY brand, company, team, artist, or creator they tag (@mentions), wear, use, hashtag, or reference. Include fashion brands (Zara, Lululemon), tech (Apple, Sony), food/drink (Starbucks, Nespresso), sports teams (Pacers, Colts), artists (Taylor Swift), creators, and niche brands. Aim for 5-15+ brands. More is better — we use this to personalize search results.
   - Quality level (budget, mid-range, premium, luxury)

4. **PRICE POINT SIGNALS**:
   - Estimated comfortable price range based on products they post about
   - Budget category: budget-conscious, moderate, premium, luxury
   - Note: This is for matching gifts to their lifestyle, not assuming affordability

5. **ASPIRATIONAL VS. CURRENT**:
   - Aspirational interests: Things they want/admire but don't have (from reposts, pins, "wish" language)
   - Current interests: Things they already do/have (from owned items, activities)
   - **Gaps**: List 2-5 concrete "gaps" - things they clearly want but don't have yet, with brief evidence. Critical for experience and thoughtful product ideas.

6. **SPECIFIC VENUES/EXPERIENCES**:
   - Name specific restaurants, bars, venues, events they've posted about
   - Activities they do regularly
   - Places they've expressed interest in but haven't been to
   - Only include if you have concrete evidence

7. **RELATIONSHIP-APPROPRIATE GIFTING**:
   - What kinds of gifts are appropriate for this relationship level?
   - What boundaries should be respected?
   - What level of personalization/intimacy is suitable?

Return ONLY a JSON object with this structure:
{{
  "interests": [
    {{
      "name": "specific interest name",
      "evidence": "concrete evidence from posts",
      "description": "same as evidence - short description for filtering",
      "intensity": "casual|moderate|passionate",
      "type": "aspirational|current",
      "is_work": false,
      "activity_type": "passive|active|both",
      "confidence": "high|medium|low",
      "signal_quotes": ["verbatim quote or entity from the data", "another verbatim quote", "third verbatim quote — up to 3, empty list if none are genuinely in the source data"],
      "signal_momentum": "rising|stable|fading"
    }}
  ],
  "location_context": {{
    "city_region": "where they live or null if unknown - do NOT invent",
    "specific_places": ["specific venue/restaurant names"],
    "geographic_constraints": "description of location limitations"
  }},
  "ownership_signals": ["specific items/products visible in their content that they already own — e.g., 'Hydro Flask', 'KitchenAid mixer', 'MacBook Pro'"],
  "style_preferences": {{
    "visual_style": "description",
    "aesthetic_summary": "1-2 sentence holistic description of their aesthetic sensibility",
    "colors": ["color preferences"],
    "brands": ["EVERY brand/company/artist they tag, mention, wear, use, or follow — be exhaustive, not conservative. Include clothing brands, tech brands, food/drink brands, sports teams, artists, creators. Aim for 5-15 brands."],
    "quality_level": "budget|mid-range|premium|luxury"
  }},
  "price_signals": {{
    "estimated_range": "$X-$Y",
    "budget_category": "budget|moderate|premium|luxury",
    "notes": "observations about price comfort"
  }},
  "aspirational_vs_current": {{
    "aspirational": ["things they want but don't have"],
    "current": ["things they already do/have"],
    "gaps": ["2-5 specific desires with brief evidence - what they want but don't have"]
  }},
  "gift_avoid": ["generic items", "things to avoid based on profile - e.g. work-related, already has many"],
  "specific_venues": [
    {{
      "name": "venue name",
      "type": "restaurant|bar|shop|venue|activity",
      "evidence": "why you identified this",
      "location": "where it is if known"
    }}
  ],
  "gift_relationship_guidance": {{
    "appropriate_types": ["types of gifts suitable for relationship"],
    "boundaries": "what to avoid or be careful about",
    "intimacy_level": "how personal gifts can be"
  }}
}}

CRITICAL REQUIREMENTS:
- Be specific - "interested in cooking" is bad, "passionate about Thai cooking" with evidence is good
- When there are many posts/videos with varied content, list 8-12 distinct interests (different topics, hobbies, aesthetics). Do not return only 1-2 interests when the data clearly shows variety.
- **confidence**: "high" = multiple posts showing personal engagement (they do it, own it, talk about it in first person). "medium" = some evidence but could be shared/adjacent (posts about an activity they attend with others). "low" = mentioned once or appears to belong to someone else in their life. Do NOT include interests with low confidence — skip them entirely.
- Only include information you have CLEAR evidence for
- If something is unknown, mark it as null or empty array
- Location: if city_region is unknown, do NOT invent a city; leave null. Only include places with concrete evidence.
- Price signals are for matching gifts to their lifestyle, not judging affordability
- Distinguish aspirational (wants) from current (has) clearly. Populate gaps with 2-5 concrete desires and evidence.
- Interest names must be SHORT and SEARCHABLE as product queries. Bad: "Christmas music and holiday traditions". Good: "Michael Bublé" or "vinyl record collecting". Each name should return useful results when typed into Amazon or Etsy search.
{'''
SPOTIFY-ONLY CRITICAL: Since music is the ONLY data source, you MUST:
- Use 3-4 specific ARTIST NAMES as interests (e.g., "Misfits" not "horror punk music")
- Translate genres to PRODUCT interests only — what would you search on Amazon/Etsy? (e.g., "vinyl record collecting", "Broadway cast recording", "jazz piano album")
- Do NOT infer lifestyle stereotypes from genres (no "cocktail culture" from jazz, no "craft beer" from Americana — these are ungrounded)
- NEVER use a genre description or lifestyle inference as an interest name — only use what directly yields giftable search results
- CRITICAL: Never combine genre + format (no "horror punk vinyl", no "jazz vinyl"). Artist names alone find vinyl naturally. "vinyl record collecting" is a standalone interest for the collector lifestyle (turntables, storage, cleaning gear).
''' if spotify_is_only_source else ''}
Return ONLY the JSON object, no markdown, no backticks, no explanation."""
    
    try:
        # Call Claude for deep analysis
        logger.info("Calling Claude API for profile analysis (model=%s)...", model)

        message = claude_client.messages.create(
            model=model,
            max_tokens=6000,
            messages=[{"role": "user", "content": prompt}],
            timeout=120.0
        )
        
        # Extract response
        response_text = ""
        for block in message.content:
            if block.type == "text":
                response_text += block.text
        
        response_text = response_text.strip()
        
        # Remove markdown if present
        if response_text.startswith('```'):
            response_text = response_text.split('```')[1]
            if response_text.startswith('json'):
                response_text = response_text[4:]
            response_text = response_text.strip()
        
        # Parse JSON
        profile = json.loads(response_text)

        logger.info(f"Profile built successfully: {len(profile.get('interests', []))} interests identified")

        # Cache profile for future use (added Feb 2026 for cost reduction)
        if profile_hash:
            try:
                import config
                import database

                if config.FEATURES.get('profile_caching', True):
                    profile_json = json.dumps(profile)
                    ttl_days = config.PROFILE_CACHE_TTL_DAYS
                    database.cache_profile(profile_hash, profile_json, ttl_days)
                    logger.info(f"Profile cached (hash: {profile_hash[:8]}..., TTL: {ttl_days} days)")
            except Exception as e:
                logger.error(f"Failed to cache profile: {e}")

            # Signal any waiting threads that this analysis is done
            with _inflight_lock:
                event = _inflight_profiles.pop(profile_hash, None)
                if event:
                    event.set()

        return profile

    except Exception as e:
        logger.error(f"Error building recipient profile: {e}", exc_info=True)
        # Signal any waiting threads even on failure
        if profile_hash:
            with _inflight_lock:
                event = _inflight_profiles.pop(profile_hash, None)
                if event:
                    event.set()
        # Return minimal profile
        return {
            "interests": [],
            "location_context": {"city_region": None, "specific_places": [], "geographic_constraints": "unknown"},
            "style_preferences": {},
            "price_signals": {},
            "aspirational_vs_current": {"aspirational": [], "current": [], "gaps": []},
            "gift_avoid": [],
            "specific_venues": [],
            "gift_relationship_guidance": {}
        }
