"""
PROFILE ANALYZER - Deep Analysis of Social Media Data
Extracts comprehensive recipient profile for gift curation

Author: Chad + Claude
Date: February 2026
"""

import json
import logging
from collections import Counter
from datetime import datetime

logger = logging.getLogger(__name__)

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


def build_recipient_profile(platforms, recipient_type, relationship, claude_client, model=None):
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
            # Generate hash from platform data for cache lookup
            cache_data = {
                'instagram': platforms.get('instagram', {}).get('data', {}),
                'tiktok': platforms.get('tiktok', {}).get('data', {}),
                'pinterest': platforms.get('pinterest', {}).get('data', {}),
                'spotify': platforms.get('spotify', {}).get('data', {}),
                'spotify_wrapped': platforms.get('spotify_wrapped', {}).get('wrapped_text', ''),
                'relationship': relationship,
            }
            cache_str = json.dumps(cache_data, sort_keys=True)
            profile_hash = hashlib.sha256(cache_str.encode()).hexdigest()

            # Check cache for existing profile
            cached_profile = database.get_cached_profile(profile_hash)
            if cached_profile:
                logger.info(f"Profile found in cache (hash: {profile_hash[:8]}...), skipping Claude call")
                return cached_profile

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

        # Extract captions, hashtags, locations
        captions = [p.get('caption', '')[:200] for p in priority_posts if p.get('caption')]
        hashtags_all = []
        locations = []
        for p in priority_posts:
            hashtags_all.extend(p.get('hashtags', []))
            if p.get('location'):
                locations.append(p.get('location'))

        top_hashtags = [tag for tag, count in Counter(hashtags_all).most_common(INSTAGRAM_TOP_HASHTAGS)]

        # Bio section - direct self-description is high-value signal
        bio_section = ""
        if bio:
            bio_section = f"\nBIO (self-described identity - strong signal): {bio}"

        # Follower context
        follower_section = ""
        if followers and followers > 0:
            follower_section = f"\n- Followers: {followers:,}"

        data_summary.append(f"""
INSTAGRAM PROFILE (@{username} - {len(posts)} posts analyzed):{bio_section}

HIGH ENGAGEMENT POSTS ({len(high_engagement)} posts with 50+ engagement):
{chr(10).join(['- ' + c for c in captions[:INSTAGRAM_CAPTIONS_IN_SUMMARY]])}

TOP HASHTAGS: {', '.join(top_hashtags)}

LOCATIONS MENTIONED: {', '.join(set(locations[:15]))}

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

        data_summary.append(f"""
TIKTOK PROFILE (@{username} - {len(videos)} videos, {len(reposts)} reposts):

OWN VIDEO CONTENT (What they POST - use this for current interests and variety):
{chr(10).join(['- ' + d for d in own_descriptions[:n_own]]) if own_descriptions else '(no captions)'}

VIDEO HASHTAGS (all videos): {', '.join(top_video_hashtags) if top_video_hashtags else 'none'}
{music_section}
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
        lines.append(f"Top artists: {', '.join(spotify_artists[:20])}")

        if spotify_genres:
            lines.append(f"Genres: {', '.join(spotify_genres[:20])}")

        if spotify_tracks:
            # Sample tracks give a taste/vibe signal beyond just artist names
            # Tracks may be dicts {'name': ..., 'artist': ...} (OAuth) or plain strings (manual)
            track_labels = [
                f"{t['name']} - {t['artist']}" if isinstance(t, dict) else str(t)
                for t in spotify_tracks[:15]
            ]
            lines.append(f"Sample tracks: {', '.join(track_labels)}")

        # When Spotify is the ONLY signal, give the analyzer much more specific guidance
        if spotify_is_only_source:
            spotify_guidance = """
THIS IS THE ONLY DATA SOURCE. You must mine it deeply — every artist, genre, and track is a signal.

CRITICAL RULES FOR SPOTIFY-ONLY PROFILES:
1. **Extract SPECIFIC artist names as interests** — "The Misfits" or "Billie Eilish" are interests, not "horror punk music". Use the artist name as the interest name so search queries find merch, vinyl, and fan gear for THAT artist.
2. **Infer lifestyle/aesthetic from genre clusters** — e.g., rockabilly + psychobilly → vintage/retro aesthetic, leather jackets, pomade; indie folk + Americana → cabin vibes, outdoors, flannel, craft beer; Broadway + jazz → cultural experiences, art deco, cocktail culture.
3. **Map eras and sensibilities** — if most artists are from the 50s-60s, that's a vintage/retro sensibility. If they mix 80s new wave with modern synth, that's a retro-futurist aesthetic. These map to home decor, fashion, and experience gifts.
4. **Identify specific giftable categories from the music** — vinyl records (if genres suggest collector), concert tickets (for active touring artists), band merch, music books, instruments/accessories, music-themed home decor, fashion that matches the aesthetic.
5. **Do NOT produce generic genre labels like "Christmas music and holiday traditions" as interest names.** Instead: name the top 2-3 artists as separate interests, plus 3-4 lifestyle/aesthetic interests inferred from the genre mix, plus 2-3 specific gift category interests (e.g., "vinyl record collecting", "live jazz experiences", "retro fashion").
6. **Each interest should be SEARCHABLE as a product query** — "Tiger Army" finds merch; "rockabilly fashion" finds clothes; "vinyl records jazz" finds records. "Rockabilly and psychobilly music" finds nothing useful.
7. **Diverse interest types** — aim for a mix: 2-3 specific artists, 2-3 aesthetic/lifestyle interests, 2-3 experience interests, 1-2 hobby interests inferred from the music taste.
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
                lines = [f"Top artists: {', '.join(parse_result['artists'][:20])}"]
                if parse_result.get('genres'):
                    lines.append(f"Genres: {', '.join(parse_result['genres'][:20])}")
                if parse_result.get('tracks'):
                    lines.append(f"Sample tracks: {', '.join(parse_result['tracks'][:15])}")
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

            if enhanced_sections:
                data_summary.append(f"""
CROSS-PLATFORM INTELLIGENCE (extracted patterns across all platforms):

{chr(10).join(enhanced_sections)}

Use these signals to inform style preferences, brand affinities, and interest intensity.
""")
        except Exception as e:
            logger.warning(f"Enhanced data extraction failed (continuing without): {e}")

    # Build the analysis prompt
    relationship_context = ""
    if recipient_type == 'someone_else' and relationship:
        relationship_context = f"\nRELATIONSHIP TYPE: {relationship}\nThis affects what kinds of gifts are appropriate (e.g., romantic vs. friendly vs. professional)."
    
    prompt = f"""Analyze this person's social media data and build a comprehensive profile for gift curation.

{chr(10).join(data_summary)}{relationship_context}

Extract and structure the following information:

1. **SPECIFIC INTERESTS** (not generic categories - specific, evidence-based interests):
   - List 8-12 specific interests with concrete evidence. When the person has many posts/videos (e.g. 50+), you MUST extract multiple distinct interests—do NOT collapse everything into one or two themes.
   - For each interest: name, evidence from posts, intensity (casual/moderate/passionate), type (aspirational|current)
   - **is_work**: true ONLY if this is clearly their job/profession (e.g. "paramedic", "works at venue"); false for hobbies
   - **activity_type**: "passive" if they mainly watch/collect/consume (e.g. anime fan, book reader); "active" if they do it (cooking, sports); "both" if unclear
   - Example: "Thai cooking (passionate, current, active) - Posted pad thai 5x, tagged #thaifood 8x"

2. **LOCATION CONTEXT**:
   - Where they live/are based (city, region) - ONLY if you have clear evidence (posts, venues, bio)
   - If city_region is unknown, do NOT invent a city; leave null
   - Specific places they frequent (restaurants, venues, neighborhoods)
   - Geographic constraints for experiences
   - If no clear location, state "Unknown - location-based recommendations not possible"

3. **STYLE & AESTHETIC PREFERENCES**:
   - Visual style (minimalist, maximalist, vintage, modern, etc.)
   - Color preferences
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
      "activity_type": "passive|active|both"
    }}
  ],
  "location_context": {{
    "city_region": "where they live or null if unknown - do NOT invent",
    "specific_places": ["specific venue/restaurant names"],
    "geographic_constraints": "description of location limitations"
  }},
  "style_preferences": {{
    "visual_style": "description",
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
- Only include information you have CLEAR evidence for
- If something is unknown, mark it as null or empty array
- Location: if city_region is unknown, do NOT invent a city; leave null. Only include places with concrete evidence.
- Price signals are for matching gifts to their lifestyle, not judging affordability
- Distinguish aspirational (wants) from current (has) clearly. Populate gaps with 2-5 concrete desires and evidence.
- Interest names must be SHORT and SEARCHABLE as product queries. Bad: "Christmas music and holiday traditions". Good: "Michael Bublé" or "holiday vinyl records". Each name should return useful results when typed into Amazon or Etsy search.
{'''
SPOTIFY-ONLY CRITICAL: Since music is the ONLY data source, you MUST:
- Use 2-3 specific ARTIST NAMES as interest names (e.g., "Misfits" not "horror punk music")
- Infer 3-4 concrete lifestyle/aesthetic interests from the genre mix (e.g., "vintage fashion", "vinyl collecting", "cocktail culture")
- Include 2-3 experience interests (e.g., "live jazz shows", "Broadway tickets", "music festivals")
- NEVER use a genre description as an interest name — always translate to something searchable/giftable
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

        return profile
        
    except Exception as e:
        logger.error(f"Error building recipient profile: {e}", exc_info=True)
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
