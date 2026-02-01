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


def build_recipient_profile(platforms, recipient_type, relationship, claude_client):
    """
    Build comprehensive recipient profile from scraped social media data.
    
    Args:
        platforms: Dict of platform data (instagram, tiktok, pinterest)
        recipient_type: 'myself' or 'someone_else'
        relationship: Relationship type if someone_else
        claude_client: Anthropic client for AI analysis
    
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
    
    logger.info("Building deep recipient profile...")
    
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
        
        # Get high-engagement posts (strongest signals)
        sorted_posts = sorted(posts, key=lambda p: (p.get('likes', 0) + p.get('comments', 0) * 2), reverse=True)
        high_engagement = [p for p in sorted_posts if (p.get('likes', 0) + p.get('comments', 0) * 2) > 50]
        
        # Use top posts for analysis
        priority_posts = high_engagement[:20] if high_engagement else sorted_posts[:20]
        
        # Extract captions, hashtags, locations
        captions = [p.get('caption', '')[:200] for p in priority_posts if p.get('caption')]
        hashtags_all = []
        locations = []
        for p in priority_posts:
            hashtags_all.extend(p.get('hashtags', []))
            if p.get('location'):
                locations.append(p.get('location'))
        
        top_hashtags = [tag for tag, count in Counter(hashtags_all).most_common(20)]
        
        data_summary.append(f"""
INSTAGRAM PROFILE (@{username} - {len(posts)} posts analyzed):

HIGH ENGAGEMENT POSTS ({len(high_engagement)} posts with 50+ engagement):
{chr(10).join(['- ' + c for c in captions[:15]])}

TOP HASHTAGS: {', '.join(top_hashtags)}

LOCATIONS MENTIONED: {', '.join(set(locations[:10]))}

POST PATTERNS:
- Average likes: {sum(p.get('likes', 0) for p in priority_posts) / len(priority_posts) if priority_posts else 0:.0f}
- Average comments: {sum(p.get('comments', 0) for p in priority_posts) / len(priority_posts) if priority_posts else 0:.0f}
- Posting frequency: {len(posts)} posts in recent history
""")
    
    # TikTok analysis
    if tiktok_data:
        videos = tiktok_data.get('videos', [])
        reposts = tiktok_data.get('reposts', [])
        username = tiktok_data.get('username', 'unknown')
        
        # CRITICAL: Reposts show aspirational interests
        repost_descriptions = [r.get('description', '')[:150] for r in reposts[:20] if r.get('description')]
        
        # Extract hashtags from reposts
        repost_hashtags = []
        for r in reposts[:30]:
            repost_hashtags.extend(r.get('hashtags', []))
        top_repost_hashtags = [tag for tag, count in Counter(repost_hashtags).most_common(20)]
        
        # Favorite creators
        favorite_creators = tiktok_data.get('favorite_creators', [])
        
        data_summary.append(f"""
TIKTOK PROFILE (@{username} - {len(videos)} videos, {len(reposts)} reposts):

ASPIRATIONAL CONTENT (REPOSTS - What they WANT):
{chr(10).join(['- ' + d for d in repost_descriptions[:15]])}

REPOST HASHTAGS: {', '.join(top_repost_hashtags)}

FAVORITE CREATORS (Aspirational aesthetics):
{chr(10).join([f"- @{creator[0]} ({creator[1]} reposts)" for creator in favorite_creators[:8]])}

CRITICAL NOTE: Reposts reveal aspirational interests - these are things they admire and want but don't currently have.
""")
    
    # Pinterest analysis
    if pinterest_data:
        boards = pinterest_data.get('boards', [])
        
        # Extract board themes
        board_names = [b.get('name', '') for b in boards]
        
        # Sample pins from boards
        all_pins = []
        for board in boards[:10]:
            pins = board.get('pins', [])
            all_pins.extend(pins[:5])
        
        pin_descriptions = [p.get('description', '')[:100] for p in all_pins if p.get('description')]
        
        data_summary.append(f"""
PINTEREST PROFILE ({len(boards)} boards):

BOARD THEMES: {', '.join(board_names[:15])}

PIN DESCRIPTIONS (Explicit wishlist signals):
{chr(10).join(['- ' + d for d in pin_descriptions[:20]])}

CRITICAL NOTE: Pinterest boards are explicit wishlists - they're pinning exactly what they want.
""")
    
    # Build the analysis prompt
    relationship_context = ""
    if recipient_type == 'someone_else' and relationship:
        relationship_context = f"\nRELATIONSHIP TYPE: {relationship}\nThis affects what kinds of gifts are appropriate (e.g., romantic vs. friendly vs. professional)."
    
    prompt = f"""Analyze this person's social media data and build a comprehensive profile for gift curation.

{chr(10).join(data_summary)}{relationship_context}

Extract and structure the following information:

1. **SPECIFIC INTERESTS** (not generic categories - specific, evidence-based interests):
   - List 8-12 specific interests with concrete evidence
   - For each interest, note: what it is, evidence from posts, and intensity level (casual/moderate/passionate)
   - Example: "Thai cooking (passionate) - Posted pad thai 5x, tagged #thaifood 8x, follows 3 Thai cooking creators"

2. **LOCATION CONTEXT**:
   - Where they live/are based (city, region)
   - Specific places they frequent (restaurants, venues, neighborhoods)
   - Geographic constraints for experiences
   - If no clear location, state "Unknown - location-based recommendations not possible"

3. **STYLE & AESTHETIC PREFERENCES**:
   - Visual style (minimalist, maximalist, vintage, modern, etc.)
   - Color preferences
   - Brand preferences (specific brands they mention/tag)
   - Quality level (budget, mid-range, premium, luxury)

4. **PRICE POINT SIGNALS**:
   - Estimated comfortable price range based on products they post about
   - Budget category: budget-conscious, moderate, premium, luxury
   - Note: This is for matching gifts to their lifestyle, not assuming affordability

5. **ASPIRATIONAL VS. CURRENT**:
   - Aspirational interests: Things they want/admire but don't have (from reposts, pins, "wish" language)
   - Current interests: Things they already do/have (from owned items, activities)
   - Gap analysis: What's missing that they clearly want?

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
      "intensity": "casual|moderate|passionate",
      "type": "aspirational|current"
    }}
  ],
  "location_context": {{
    "city_region": "where they live or null if unknown",
    "specific_places": ["specific venue/restaurant names"],
    "geographic_constraints": "description of location limitations"
  }},
  "style_preferences": {{
    "visual_style": "description",
    "colors": ["color preferences"],
    "brands": ["specific brands they mention"],
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
    "gaps": ["specific desires evident from data"]
  }},
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
- Only include information you have CLEAR evidence for
- If something is unknown, mark it as null or empty array
- Location context is CRITICAL for experience gifts - only include places with concrete evidence
- Price signals are for matching gifts to their lifestyle, not judging affordability
- Distinguish aspirational (wants) from current (has) clearly

Return ONLY the JSON object, no markdown, no backticks, no explanation."""
    
    try:
        # Call Claude for deep analysis
        logger.info("Calling Claude API for profile analysis...")
        
        message = claude_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
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
            "specific_venues": [],
            "gift_relationship_guidance": {}
        }
