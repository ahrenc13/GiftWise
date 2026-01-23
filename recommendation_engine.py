"""
MULTI-PLATFORM RECOMMENDATION ENGINE
Generates gift recommendations from Instagram, Spotify, Pinterest, TikTok data

Uses Claude to analyze cross-platform signals and generate ultra-specific recommendations
"""

import json

def generate_multi_platform_recommendations(platform_data, user_email, claude_client, max_recommendations=10):
    """
    Generate gift recommendations from multi-platform data
    
    Args:
        platform_data: Dict with keys like 'instagram', 'spotify', 'pinterest', 'tiktok'
        user_email: User identifier
        claude_client: Anthropic client instance
        max_recommendations: Maximum number of recommendations to generate (5 for free, 10 for pro)
    
    Returns:
        List of recommendation dicts
    """
    
    # Build context from all platforms
    context = build_context(platform_data)
    platforms_connected = list(platform_data.keys())
    
    # Calculate distribution based on max recommendations
    if max_recommendations == 5:
        # FREE TIER: 3 safe, 2 balanced
        safe_count = 3
        balanced_count = 2
        stretch_count = 0
    else:
        # PRO TIER: 4 safe, 4 balanced, 2 stretch
        safe_count = 4
        balanced_count = 4
        stretch_count = 2
    
    # Generate prompt for Claude
    prompt = f"""{context}

CONNECTED PLATFORMS: {', '.join([p.upper() for p in platforms_connected])}

Generate {max_recommendations} ULTRA-SPECIFIC gift recommendations using ALL available platform data.

CRITICAL RULES:

1. **CROSS-PLATFORM VALIDATION**
   - Interest appears on 3+ platforms → 95% match (safe confidence)
   - Interest on 2 platforms → 80% match (balanced confidence)
   - Single platform strong signal → 70% match (stretch confidence)

2. **BE ULTRA-SPECIFIC** - Include brand names, models, specific editions
   ❌ "Vintage Band T-Shirt"
   ✅ "Original 1989 Depeche Mode Violator Tour T-Shirt, Size Large"
   ❌ "Music equipment"
   ✅ "Focusrite Scarlett Solo USB Audio Interface (3rd Gen)"

3. **IDENTIFY EXISTING INVESTMENTS**
   - Look for frequent mentions, hashtags, or patterns
   - Don't suggest more of what they already have
   - Suggest ADJACENT/COMPLEMENTARY items instead
   
   Examples:
   - Frequent concert posts → Suggest: Band biography book (NOT more tickets)
   - Heavy Spotify usage → Suggest: Vinyl of favorite album (NOT Spotify gift card)
   - Pinterest boards on running → Suggest: GPS watch (NOT running shoes they probably have)

4. **PLATFORM-SPECIFIC INSIGHTS**
   - **Pinterest = HIGHEST INTENT**: They're literally pinning what they want!
   - **Spotify**: Music taste → Concert tickets, vinyl, artist merch, music gear
   - **Instagram**: Lifestyle, aesthetics, experiences they value
   - **TikTok**: Current trends, active interests right now

5. **MATCH PERCENTAGE SCORING**
   - safe (85-95%): Cross-platform validation + specific + NOT duplicate
   - balanced (72-84%): Strong signal + specific + complementary
   - stretch (60-71%): Creative connection + fills a gap

6. **NO CATEGORIES, ONLY PRODUCTS**
   - "Marshall Acton III Bluetooth Speaker in Black" ✓
   - "High-quality Bluetooth speaker" ✗

Generate {max_recommendations} gifts:
- {safe_count} "safe": Cross-platform validated + specific + adjacent (85-95% match)
- {balanced_count} "balanced": Strong single platform + specific + complementary (72-84% match)
{f'- {stretch_count} "stretch": Creative connection + unique (60-71% match)' if stretch_count > 0 else ''}

Format as JSON:
[
  {{
    "name": "Specific product with brand/model/edition",
    "price": "$X",
    "match": X,
    "confidence": "safe/balanced/stretch",
    "reason": "Which platforms + why THIS specific item + why not duplicate",
    "platforms": ["instagram", "spotify"]
  }}
]

Return ONLY the JSON array, no other text."""

    # Call Claude
    response = claude_client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}]
    )
    
    # Parse response
    text = response.content[0].text
    
    # Extract JSON
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]
    
    recommendations = json.loads(text.strip())
    
    # Add Amazon affiliate links (placeholder - implement later)
    for rec in recommendations:
        rec['amazon_search_url'] = create_amazon_search_url(rec['name'])
    
    return recommendations


def build_context(platform_data):
    """Build detailed context string from all platform data"""
    
    context = "USER INTEREST PROFILE\n\n"
    
    # Instagram data
    if 'instagram' in platform_data and 'error' not in platform_data['instagram']:
        ig = platform_data['instagram']
        context += f"""INSTAGRAM (Full OAuth Access):
Username: @{ig.get('username', 'unknown')}
Posts Analyzed: {ig.get('total_posts', 0)}

Top Hashtags:
{format_dict(ig.get('top_hashtags', {}), limit=20)}

Recent Caption Samples:
{format_list(ig.get('recent_captions', []), limit=5)}

---

"""
    
    # Spotify data
    if 'spotify' in platform_data and 'error' not in platform_data['spotify']:
        sp = platform_data['spotify']
        context += f"""SPOTIFY (Full OAuth Access):

Top Artists (Last 6 Months):
{format_list(sp.get('top_artists', []), limit=15)}

Top Genres:
{format_dict(sp.get('top_genres', {}), limit=10)}

Top Tracks:
{format_track_list(sp.get('top_tracks', []), limit=10)}

Playlists:
{format_list(sp.get('playlists', []), limit=8)}

---

"""
    
    # Pinterest data
    if 'pinterest' in platform_data and 'error' not in platform_data['pinterest']:
        pin = platform_data['pinterest']
        context += f"""PINTEREST (Full OAuth Access) - HIGHEST INTENT DATA:
Total Boards: {pin.get('total_boards', 0)}
Total Pins: {pin.get('total_pins', 0)}

Boards:
{format_pinterest_boards(pin.get('boards', []), limit=10)}

Top Keywords from Pins:
{format_dict(pin.get('top_keywords', {}), limit=25)}

⚠️ PINTEREST = WISHLIST DATA - These are things they're actively wanting!

---

"""
    
    # TikTok data
    if 'tiktok' in platform_data and 'error' not in platform_data['tiktok']:
        tt = platform_data['tiktok']
        context += f"""TIKTOK (Public Profile):
Username: @{tt.get('username', 'unknown')}
Posts Analyzed: {tt.get('total_posts', 0)}

Top Hashtags:
{format_dict(tt.get('top_hashtags', {}), limit=20)}

Top Music/Sounds:
{format_dict(tt.get('top_music', {}), limit=15)}

Note: Limited to public content only (OAuth coming soon for full access)

---

"""
    
    return context


def format_dict(data_dict, limit=10):
    """Format dictionary as readable list"""
    if not data_dict:
        return "None"
    
    items = sorted(data_dict.items(), key=lambda x: x[1], reverse=True)[:limit]
    return '\n'.join([f"- {k}: {v}x" for k, v in items])


def format_list(data_list, limit=10):
    """Format list as readable bullet points"""
    if not data_list:
        return "None"
    
    items = data_list[:limit]
    return '\n'.join([f"- {item}" for item in items if item])


def format_track_list(tracks, limit=10):
    """Format Spotify tracks"""
    if not tracks:
        return "None"
    
    return '\n'.join([
        f"- \"{track['name']}\" by {track['artist']}"
        for track in tracks[:limit]
    ])


def format_pinterest_boards(boards, limit=10):
    """Format Pinterest boards with pin info"""
    if not boards:
        return "None"
    
    output = []
    for board in boards[:limit]:
        output.append(f"- {board['name']} ({board.get('pin_count', 0)} pins)")
        if board.get('description'):
            output.append(f"  Description: {board['description'][:100]}")
        
        # Sample pins
        pins = board.get('pins', [])[:3]
        for pin in pins:
            if pin.get('title'):
                output.append(f"  • {pin['title']}")
    
    return '\n'.join(output)


def create_amazon_search_url(product_name):
    """Create Amazon search URL (will add affiliate tag later)"""
    import urllib.parse
    query = urllib.parse.quote_plus(product_name)
    return f"https://www.amazon.com/s?k={query}"


def add_affiliate_links(recommendations, associate_id="giftwise-20"):
    """
    Add Amazon affiliate links to recommendations
    This is a placeholder - implement actual product matching later
    
    For MVP: Just create search URLs with affiliate tag
    Later: Use Amazon Product API to get actual product links
    """
    for rec in recommendations:
        import urllib.parse
        query = urllib.parse.quote_plus(rec['name'])
        rec['amazon_affiliate_url'] = f"https://www.amazon.com/s?k={query}&tag={associate_id}"
    
    return recommendations
