"""
ENHANCED RECOMMENDATION ENGINE
Makes recommendations EXCELLENT - better than ChatGPT

Key Improvements:
- Enhanced signal extraction
- Wishlist integration
- Duplicate detection
- Engagement weighting
- Aspirational vs current interests
- Evidence-based recommendations
"""

import json
from collections import Counter
from datetime import datetime, timedelta

def extract_deep_signals(platform_data):
    """
    Extract nuanced signals that generic AI can't see
    """
    signals = {
        'aspirational_interests': [],
        'current_interests': [],
        'high_engagement_topics': [],
        'gaps_in_collections': [],
        'price_preferences': {},
        'brand_preferences': [],
        'style_aesthetics': [],
        'lifestyle_patterns': []
    }
    
    # Instagram analysis
    if 'instagram' in platform_data:
        ig_data = platform_data['instagram'].get('data', {})
        posts = ig_data.get('posts', [])
        
        # Engagement analysis
        high_engagement_posts = []
        for post in posts:
            likes = post.get('likes', 0)
            comments = post.get('comments', 0)
            engagement = likes + (comments * 2)  # Comments weighted more
            
            if engagement > 50:  # High engagement threshold
                high_engagement_posts.append({
                    'caption': post.get('caption', ''),
                    'hashtags': post.get('hashtags', []),
                    'engagement': engagement
                })
        
        # Extract high-engagement topics
        for post in high_engagement_posts:
            hashtags = post.get('hashtags', [])
            signals['high_engagement_topics'].extend(hashtags)
        
        # Brand mentions
        for post in posts:
            caption = post.get('caption', '').lower()
            # Extract brand mentions (common brands)
            brands = extract_brands_from_text(caption)
            signals['brand_preferences'].extend(brands)
    
    # TikTok repost analysis (aspirational)
    if 'tiktok' in platform_data:
        tt_data = platform_data['tiktok'].get('data', {})
        reposts = tt_data.get('reposts', [])
        favorite_creators = tt_data.get('favorite_creators', [])
        
        # Reposts = aspirational content
        for repost in reposts:
            description = repost.get('description', '')
            hashtags = repost.get('hashtags', [])
            signals['aspirational_interests'].extend(hashtags)
            signals['aspirational_interests'].append(description[:100])
        
        # Favorite creators = aspirational aesthetics
        for creator, count in favorite_creators[:5]:
            signals['aspirational_interests'].append(f"creator_style:{creator}")
    
    # Pinterest = explicit aspirational
    if 'pinterest' in platform_data:
        pinterest = platform_data['pinterest']
        boards = pinterest.get('boards', [])
        
        for board in boards:
            board_name = board.get('name', '').lower()
            signals['aspirational_interests'].append(f"board:{board_name}")
            
            pins = board.get('pins', [])
            for pin in pins[:10]:  # Top 10 pins per board
                title = pin.get('title', '')
                signals['aspirational_interests'].append(title[:100])
    
    # Count frequencies
    signals['high_engagement_topics'] = dict(Counter(signals['high_engagement_topics']).most_common(20))
    signals['aspirational_interests'] = list(set(signals['aspirational_interests']))[:30]
    signals['brand_preferences'] = dict(Counter(signals['brand_preferences']).most_common(10))
    
    return signals

def extract_brands_from_text(text):
    """Extract brand mentions from text"""
    # Common brands to look for
    common_brands = [
        'nike', 'adidas', 'apple', 'sony', 'canon', 'lego', 'disney',
        'starbucks', 'target', 'amazon', 'etsy', 'patagonia', 'north face',
        'tesla', 'bmw', 'mercedes', 'taylor swift', 'harry styles'
    ]
    
    found_brands = []
    text_lower = text.lower()
    
    for brand in common_brands:
        if brand in text_lower:
            found_brands.append(brand)
    
    return found_brands

def integrate_wishlist_data(wishlist_data, platform_data):
    """
    Use wishlist data to identify explicit wants and avoid duplicates
    """
    if not wishlist_data:
        return {
            'explicit_wants': [],
            'avoid_items': [],
            'price_range': None,
            'categories': []
        }
    
    explicit_wants = []
    prices = []
    categories = []
    avoid_keywords = []
    
    for wishlist in wishlist_data:
        for item in wishlist.get('items', []):
            explicit_wants.append({
                'name': item.get('name', ''),
                'category': item.get('category', ''),
                'price': item.get('price', 0),
                'platform': wishlist.get('platform', 'unknown')
            })
            
            if item.get('price'):
                prices.append(item['price'])
            
            if item.get('category'):
                categories.append(item['category'])
            
            # Extract keywords to avoid
            name_words = item.get('name', '').lower().split()
            avoid_keywords.extend([w for w in name_words if len(w) > 4])
    
    # Calculate price range
    price_range = None
    if prices:
        price_range = {
            'min': min(prices),
            'max': max(prices),
            'avg': sum(prices) / len(prices)
        }
    
    return {
        'explicit_wants': explicit_wants,
        'avoid_items': list(set(avoid_keywords)),
        'price_range': price_range,
        'categories': list(set(categories))
    }

def detect_duplicates(platform_data, wishlist_data):
    """
    Find what they already own or want (to avoid recommending)
    """
    owned_items = []
    wanted_items = []
    
    # Check posts for ownership signals
    if 'instagram' in platform_data:
        posts = platform_data['instagram'].get('data', {}).get('posts', [])
        for post in posts:
            caption = post.get('caption', '').lower()
            # Ownership indicators
            ownership_words = ['just got', 'new', 'bought', 'my new', 'just bought', 
                             'arrived', 'unboxing', 'finally got', 'picked up']
            
            if any(word in caption for word in ownership_words):
                # Extract item mentions
                hashtags = post.get('hashtags', [])
                owned_items.extend(hashtags)
    
    # Check wishlist
    if wishlist_data:
        for wishlist in wishlist_data:
            for item in wishlist.get('items', []):
                wanted_items.append(item.get('name', '').lower())
    
    return {
        'owned': list(set(owned_items)),
        'wanted': wanted_items,
        'avoid': list(set(owned_items + wanted_items))
    }

def build_enhanced_prompt(platform_data, wishlist_data, signals, relationship_context, 
                         recipient_type, quality, rec_count):
    """
    Build a superior prompt that generates EXCELLENT recommendations
    """
    
    # Format platform insights with engagement data
    platform_insights = []
    
    if 'instagram' in platform_data:
        ig_data = platform_data['instagram'].get('data', {})
        posts = ig_data.get('posts', [])
        
        # High engagement posts
        high_engagement = [p for p in posts if (p.get('likes', 0) + p.get('comments', 0)) > 50]
        
        platform_insights.append(f"""
INSTAGRAM DATA ({len(posts)} posts analyzed):
- Username: @{ig_data.get('username', 'unknown')}
- High Engagement Posts: {len(high_engagement)} posts with 50+ engagement
- Top Hashtags: {', '.join(list(signals['high_engagement_topics'].keys())[:15])}
- Brand Preferences: {', '.join(list(signals['brand_preferences'].keys())[:10])}
- Recent Captions: {'; '.join([p['caption'][:150] for p in posts[:10] if p.get('caption')])}
""")
    
    if 'tiktok' in platform_data:
        tt_data = platform_data['tiktok'].get('data', {})
        repost_patterns = tt_data.get('repost_patterns', {})
        favorite_creators = tt_data.get('favorite_creators', [])
        
        creator_list = [f"@{c[0]} ({c[1]} reposts)" for c in favorite_creators[:5]]
        
        platform_insights.append(f"""
TIKTOK DATA ({tt_data.get('total_videos', 0)} videos analyzed):
- Username: @{tt_data.get('username', 'unknown')}
- Repost Behavior: {repost_patterns.get('total_reposts', 0)} reposts ({repost_patterns.get('repost_percentage', 0):.1f}%)
- Frequently Reposts From: {', '.join(creator_list)}
- CRITICAL: Reposts reveal ASPIRATIONAL interests - what they want but don't have
- Top Hashtags: {', '.join(list(tt_data.get('top_hashtags', {}).keys())[:10])}
""")
    
    if 'pinterest' in platform_data:
        pinterest = platform_data['pinterest']
        boards = pinterest.get('boards', [])
        board_names = [b['name'] for b in boards[:10]]
        
        platform_insights.append(f"""
PINTEREST DATA ({len(boards)} boards):
- Board Names: {', '.join(board_names)}
- CRITICAL: Pinterest = EXPLICIT WISHLIST - they're pinning what they want
- Aspirational Content: {len(signals['aspirational_interests'])} unique interests identified
""")
    
    # Format wishlist data
    wishlist_context = ""
    if wishlist_data and wishlist_data.get('explicit_wants'):
        wants = wishlist_data['explicit_wants'][:10]
        want_names = [w['name'] for w in wants]
        wishlist_context = f"""
WISHLIST DATA (EXPLICIT WANTS):
- Items Already Wanted: {', '.join(want_names)}
- CRITICAL: DO NOT recommend these items (they'll buy them themselves)
- Instead: Suggest COMPLEMENTARY items, UPGRADES, or VARIATIONS
- Price Range: ${wishlist_data.get('price_range', {}).get('min', 0)}-${wishlist_data.get('price_range', {}).get('max', 0)}
"""
    
    # Avoid items
    avoid_context = ""
    if wishlist_data and wishlist_data.get('avoid_items'):
        avoid_context = f"""
ITEMS TO AVOID:
- Already Owned/Wanted: {', '.join(wishlist_data['avoid_items'][:20])}
- CRITICAL: Never recommend these exact items
"""
    
    # Build prompt
    prompt = f"""You are an expert gift curator with access to deep social media intelligence. Your recommendations must be SO SPECIFIC and EVIDENCE-BASED that generic AI assistants cannot match them.

=== USER PROFILE ===

PLATFORM DATA:
{chr(10).join(platform_insights)}

{wishlist_context}

{avoid_context}

DEEP SIGNALS:
- High Engagement Topics: {', '.join(list(signals['high_engagement_topics'].keys())[:15])}
- Aspirational Interests: {', '.join(signals['aspirational_interests'][:20])}
- Brand Preferences: {', '.join(list(signals['brand_preferences'].keys())[:10])}

{relationship_context}

=== CRITICAL RULES ===

1. **EVIDENCE-BASED SPECIFICITY**
   - Every recommendation MUST cite specific evidence
   - Include: Post count, hashtag frequency, creator names, engagement metrics
   - Example: "Based on 3 posts about Tokyo (#tokyo appears 8x) and reposts from @tokyotravel"
   - NOT: "They like travel, so here's a travel gift"

2. **AVOID DUPLICATES**
   - NEVER recommend items already on wishlist
   - NEVER recommend items they already own
   - If similar item exists, suggest UPGRADE or VARIATION
   - Example: They have AirPods → Suggest AirPods Pro (upgrade)
   - Example: They have basic LEGO → Suggest Architecture series (variation)

3. **ENGAGEMENT-WEIGHTED INTERESTS**
   - Prioritize topics with HIGH engagement (50+ likes/comments)
   - High engagement = stronger interest signal
   - Use engagement data to rank recommendations

4. **ASPIRATIONAL VS CURRENT**
   - Aspirational (Pinterest, reposts) = What they WANT
   - Current (their posts) = What they HAVE
   - Prioritize aspirational for gifts (they want it but don't have it)

5. **PRICE INTELLIGENCE**
   - Match their spending patterns from wishlist
   - If wishlist items are $50-100 → Recommend in that range
   - Consider relationship context for price appropriateness

6. **CROSS-PLATFORM VALIDATION**
   - Interest on 3+ platforms = 95% confidence (SAFE BET)
   - Interest on 2 platforms = 80% confidence (BALANCED)
   - Single platform strong signal = 70% confidence (STRETCH)

7. **COLLECTIBLE INTELLIGENCE**
   - Identify collections (LEGO, Funko, vinyl, sneakers, etc.)
   - Find what they DON'T have (gap analysis)
   - Suggest next item in series
   - Consider: Recency, rarity, completion, personal relevance

8. **RETAILER DIVERSITY & ACCESSIBILITY**
   - Prioritize UNIQUE items from independent makers, artisan shops, specialty retailers
   - BUT: Ensure retailers are ACCESSIBLE and RELIABLE
   - Avoid: Overseas sellers with 6-month shipping, unreliable micromerchants
   - Prefer: Etsy shops with good reviews, UncommonGoods, specialty retailers, brand direct sites
   - Amazon: Use ONLY if it's the perfect gift or as fallback
   - Goal: Feel like we "scoured the earth" but practical and accessible
   - Check: Shipping times, seller ratings, return policies (when possible)
   - Examples:
     * ✅ "Handmade leather journal from [Etsy shop with 500+ reviews, ships in 3-5 days]"
     * ✅ "Unique [product] from UncommonGoods"
     * ✅ "Limited edition [item] from [brand].com"
     * ✅ Amazon: Only if perfect match or no better option
     * ❌ "Item from overseas seller, ships in 2-3 months"
     * ❌ "Unknown seller with no reviews"

9. **EVIDENCE CITATION**
   - Each recommendation MUST include:
     * Which platforms showed this interest
     * Specific posts/hashtags/creators
     * Engagement metrics
     * Why THIS specific item (not category)

=== OUTPUT FORMAT ===

Return EXACTLY {rec_count} recommendations as JSON array:

[
  {{
    "name": "EXACT product name with brand/model (e.g., 'LEGO Architecture Tokyo Skyline Set 21051')",
    "description": "2-3 sentences describing what this is and why it's special",
    "why_perfect": "DETAILED explanation with SPECIFIC evidence:
      - Platform signals: Instagram (3 posts about Tokyo, #tokyo 8x), TikTok (reposts from @tokyotravel)
      - Engagement: High (avg 150 likes on travel posts)
      - Gap analysis: They collect LEGO Architecture but don't have Tokyo set
      - Aspirational signal: Reposts travel content frequently
      - Price match: Wishlist items average $60, this fits range
      - Not duplicate: Not on wishlist, not owned",
    "price_range": "$55-65",
    "where_to_buy": "Specific retailer name (Etsy shop name, UncommonGoods, brand.com, Amazon as fallback)",
    "product_url": "https://specific-url.com (prefer Etsy, specialty retailers, brand sites over Amazon)",
    "retailer_type": "etsy" or "specialty" or "brand_direct" or "amazon",
    "shipping_info": "Ships in X days" (if known, helps user decide),
    "gift_type": "physical",
    "confidence_level": "safe_bet",
    "evidence": {{
      "platforms": ["instagram", "tiktok"],
      "post_count": 3,
      "hashtag_frequency": {{"tokyo": 8, "travel": 12}},
      "engagement_rate": 0.15,
      "repost_creators": ["@tokyotravel"],
      "wishlist_overlap": false
    }}
  }}
]

=== QUALITY STANDARDS ===

Each recommendation must be:
- SPECIFIC (exact product, not category)
- EVIDENCE-BASED (cites specific data)
- UNIQUE (not generic)
- THOUGHTFUL (shows understanding)
- ACTIONABLE (real product, real URL)
- AVOID DUPLICATES (not on wishlist, not owned)

Return ONLY the JSON array, no markdown, no backticks, no explanatory text.
"""
    
    return prompt

def validate_recommendations(recommendations, avoid_items, signals):
    """
    Post-process recommendations to ensure quality
    """
    validated = []
    
    for rec in recommendations:
        # Check 1: Not a duplicate
        rec_name_lower = rec.get('name', '').lower()
        if any(avoid_item.lower() in rec_name_lower for avoid_item in avoid_items[:20]):
            continue  # Skip duplicates
        
        # Check 2: Has evidence
        if not rec.get('why_perfect') or len(rec['why_perfect']) < 50:
            continue  # Skip if no detailed evidence
        
        # Check 3: Specific enough (at least 4 words)
        if len(rec.get('name', '').split()) < 4:
            continue
        
        # Check 4: Has URL
        if not rec.get('product_url'):
            continue
        
        # Check 5: Price in reasonable range
        price_range = rec.get('price_range', '')
        if signals.get('price_preferences') and price_range:
            try:
                # Extract max price
                max_price_str = price_range.split('-')[-1].replace('$', '').replace(',', '')
                max_price = float(max_price_str)
                
                wishlist_max = signals['price_preferences'].get('max', 200)
                if max_price > wishlist_max * 2:  # Too expensive
                    continue
            except:
                pass  # Skip price check if can't parse
        
        validated.append(rec)
    
    return validated
