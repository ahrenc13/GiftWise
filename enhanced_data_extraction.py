"""
ENHANCED DATA EXTRACTION
Mine ALL possible data from platforms for better recommendations

Key Improvements:
- Extract more signals from existing platforms
- Engagement patterns
- Temporal patterns (recent vs old interests)
- Sentiment analysis
- Visual analysis (if possible)
- More nuanced hashtag analysis
"""

from collections import Counter, defaultdict
from datetime import datetime, timedelta
import re

# --- Brand detection ---
# Large but not exhaustive list of brands people commonly reference on social media.
# Matches are case-insensitive against captions, hashtags, and @mentions.
_KNOWN_BRANDS = {
    # Apparel / Athleisure
    'nike', 'adidas', 'puma', 'reebok', 'new balance', 'asics', 'under armour',
    'lululemon', 'athleta', 'fabletics', 'gymshark', 'alo yoga', 'vuori',
    'patagonia', 'north face', 'columbia', 'arcteryx', "arc'teryx", 'rei',
    'hoka', 'on running', 'brooks', 'saucony', 'allbirds',
    # Fashion
    'zara', 'h&m', 'uniqlo', 'everlane', 'madewell', 'j crew', 'anthropologie',
    'free people', 'urban outfitters', 'aritzia', 'reformation', 'cos',
    'gucci', 'louis vuitton', 'chanel', 'prada', 'dior', 'hermes', 'burberry',
    'balenciaga', 'versace', 'fendi', 'coach', 'kate spade', 'michael kors',
    'tory burch', 'ralph lauren', 'calvin klein', 'tommy hilfiger',
    'carhartt', 'dickies', 'levis', "levi's",
    # Beauty / Skincare
    'glossier', 'fenty', 'rare beauty', 'charlotte tilbury', 'nars',
    'tatcha', 'drunk elephant', 'the ordinary', 'cerave', 'olaplex',
    'dyson', 'goop', 'supergoop', 'sol de janeiro', 'summer fridays',
    # Tech / Electronics
    'apple', 'samsung', 'sony', 'canon', 'nikon', 'fujifilm', 'gopro',
    'bose', 'sonos', 'jbl', 'marshall', 'beats', 'airpods',
    'nintendo', 'xbox', 'playstation', 'steam deck', 'oculus', 'meta quest',
    'tesla', 'rivian', 'peloton', 'whoop', 'garmin', 'fitbit', 'oura',
    # Home / Kitchen
    'le creuset', 'staub', 'yeti', 'stanley', 'hydroflask', 'ember',
    'kitchenaid', 'smeg', 'our place', 'always pan', 'ninja', 'instant pot',
    'dyson', 'roomba', 'nest', 'philips hue', 'sonos',
    'crate and barrel', 'cb2', 'west elm', 'pottery barn', 'restoration hardware',
    'ikea', 'article', 'floyd', 'maiden home',
    # Outdoor / Sports
    'yeti', 'hydroflask', 'osprey', 'deuter', 'kelty', 'thule',
    'traeger', 'weber', 'solo stove', 'big green egg', 'blackstone',
    'callaway', 'titleist', 'taylormade', 'ping',
    'trek', 'specialized', 'cannondale', 'giant',
    # Food / Beverage / Lifestyle
    'starbucks', 'nespresso', 'fellow', 'chemex', 'breville',
    'disney', 'lego', 'funko', 'crocs', 'birkenstock',
    'amazon', 'etsy', 'target', 'costco', 'trader joes', "trader joe's",
    # Entertainment / Media
    'netflix', 'spotify', 'hulu', 'disney plus', 'hbo',
    'taylor swift', 'harry styles', 'beyonce', 'bts', 'olivia rodrigo',
    # Pets
    'chewy', 'barkbox', 'kong', 'ruffwear',
    # Jewelry / Accessories
    'mejuri', 'gorjana', 'kendra scott', 'pandora', 'tiffany',
    'ray ban', 'oakley', 'warby parker',
}

# Words that look like @mentions but aren't brands (common personal/generic handles)
_NON_BRAND_HANDLES = {
    'me', 'self', 'my', 'repost', 'reels', 'explore', 'trending', 'viral',
    'fyp', 'foryou', 'foryoupage', 'photo', 'photography', 'instagood',
    'love', 'life', 'style', 'beauty', 'fitness', 'food', 'travel',
    'music', 'art', 'design', 'nature', 'fashion', 'home', 'family',
    'friends', 'fun', 'happy', 'beautiful', 'cute', 'goals', 'mood',
    'ootd', 'tbt', 'selfie', 'photooftheday', 'instadaily',
}

def extract_all_instagram_signals(ig_data):
    """
    Extract EVERYTHING possible from Instagram data
    """
    if not ig_data:
        return {}
    
    posts = ig_data.get('posts', [])
    if not posts:
        return {}
    
    signals = {
        'hashtags': Counter(),
        'mentions': Counter(),
        'locations': Counter(),
        'engagement_patterns': {},
        'temporal_interests': {},
        'visual_themes': [],
        'brand_mentions': Counter(),
        'product_mentions': Counter(),
        'activity_types': Counter(),
        'aesthetic_keywords': Counter(),
        'high_engagement_content': [],
        'low_engagement_content': [],
        'recent_interests': [],
        'declining_interests': []
    }
    
    # Analyze each post deeply
    for post in posts:
        caption = post.get('caption', '').lower()
        likes = post.get('likes', 0)
        comments = post.get('comments', 0)
        timestamp = post.get('timestamp', '')
        hashtags = post.get('hashtags', [])
        post_type = post.get('type', 'image')
        
        # Hashtags
        for tag in hashtags:
            signals['hashtags'][tag.lower()] += 1
        
        # Extract mentions (@username)
        mentions = re.findall(r'@(\w+)', caption)
        signals['mentions'].update(mentions)
        
        # Extract locations (common patterns)
        location_patterns = ['in', 'at', 'visiting', 'exploring']
        for pattern in location_patterns:
            if pattern in caption:
                # Try to extract location
                words = caption.split()
                idx = words.index(pattern) if pattern in words else -1
                if idx >= 0 and idx < len(words) - 1:
                    potential_location = words[idx + 1]
                    if len(potential_location) > 2:
                        signals['locations'][potential_location] += 1
        
        # Engagement analysis
        total_engagement = likes + (comments * 2)
        if total_engagement > 100:
            signals['high_engagement_content'].append({
                'caption': caption[:200],
                'hashtags': hashtags,
                'engagement': total_engagement,
                'type': post_type
            })
        elif total_engagement < 10:
            signals['low_engagement_content'].append({
                'caption': caption[:200],
                'hashtags': hashtags
            })
        
        # Extract brand mentions from caption text
        caption_lower = caption.lower()
        for brand in _KNOWN_BRANDS:
            if brand in caption_lower:
                signals['brand_mentions'][brand] += 1

        # @mentions are often brand handles — treat them as brand signals
        for mention in mentions:
            m_lower = mention.lower()
            if m_lower not in _NON_BRAND_HANDLES and len(m_lower) > 2:
                # Check if it matches a known brand (stripped underscores/dots)
                clean = m_lower.replace('_', ' ').replace('.', ' ').strip()
                if clean in _KNOWN_BRANDS:
                    signals['brand_mentions'][clean] += 1
                else:
                    # Unknown handle — still record it as a potential brand
                    # (Claude will decide if it's relevant)
                    signals['brand_mentions'][m_lower] += 1

        # Hashtags can be brand references (#Lululemon, #YetiCoolers)
        for tag in hashtags:
            tag_lower = tag.lower().replace('_', ' ')
            if tag_lower in _KNOWN_BRANDS:
                signals['brand_mentions'][tag_lower] += 1
        
        # Extract product mentions (common patterns)
        product_indicators = ['bought', 'got', 'new', 'just got', 'purchased', 'ordered']
        for indicator in product_indicators:
            if indicator in caption:
                # Extract surrounding words as potential product
                words = caption.split()
                idx = words.index(indicator) if indicator in words else -1
                if idx >= 0:
                    # Get next 2-3 words as potential product
                    product_words = words[idx+1:idx+4]
                    if product_words:
                        signals['product_mentions'][' '.join(product_words)] += 1
        
        # Activity types (from hashtags and captions)
        activity_keywords = [
            'travel', 'food', 'fitness', 'music', 'art', 'photography',
            'reading', 'gaming', 'cooking', 'hiking', 'running', 'yoga',
            'coffee', 'wine', 'beer', 'concert', 'festival', 'museum'
        ]
        for keyword in activity_keywords:
            if keyword in caption or any(keyword in tag.lower() for tag in hashtags):
                signals['activity_types'][keyword] += 1
        
        # Aesthetic keywords
        aesthetic_keywords = [
            'minimalist', 'vintage', 'aesthetic', 'cozy', 'modern', 'rustic',
            'boho', 'industrial', 'scandinavian', 'japanese', 'french',
            'colorful', 'monochrome', 'pastel', 'bold', 'elegant', 'casual'
        ]
        for keyword in aesthetic_keywords:
            if keyword in caption:
                signals['aesthetic_keywords'][keyword] += 1
        
        # Temporal analysis (if timestamp available)
        if timestamp:
            try:
                post_date = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                days_ago = (datetime.now(post_date.tzinfo) - post_date).days
                
                # Recent interests (last 30 days)
                if days_ago <= 30:
                    signals['recent_interests'].extend(hashtags)
                
                # Declining interests (old posts with high engagement, but no recent posts)
                # This would need comparison across posts
            except:
                pass
    
    # Convert counters to dicts
    signals['hashtags'] = dict(signals['hashtags'].most_common(50))
    signals['mentions'] = dict(signals['mentions'].most_common(20))
    signals['locations'] = dict(signals['locations'].most_common(15))
    signals['brand_mentions'] = dict(signals['brand_mentions'].most_common(15))
    signals['product_mentions'] = dict(signals['product_mentions'].most_common(20))
    signals['activity_types'] = dict(signals['activity_types'].most_common(20))
    signals['aesthetic_keywords'] = dict(signals['aesthetic_keywords'].most_common(15))
    
    # Recent interests (last 30 days)
    signals['recent_interests'] = list(set(signals['recent_interests']))[:20]
    
    return signals

def extract_all_tiktok_signals(tt_data):
    """
    Extract EVERYTHING possible from TikTok data
    """
    if not tt_data:
        return {}
    
    videos = tt_data.get('videos', [])
    reposts = tt_data.get('reposts', [])
    
    signals = {
        'hashtags': Counter(),
        'music_trends': Counter(),
        'video_types': Counter(),
        'brand_mentions': Counter(),
        'engagement_patterns': {},
        'repost_analysis': {},
        'creator_styles': [],
        'trending_topics': [],
        'aspirational_content': [],
        'current_interests': []
    }

    # Analyze videos
    for video in videos:
        description = video.get('description', '').lower()
        hashtags = video.get('hashtags', [])
        music = video.get('music', '')
        likes = video.get('likes', 0)
        comments = video.get('comments', 0)
        shares = video.get('shares', 0)

        # Hashtags
        signals['hashtags'].update([tag.lower() for tag in hashtags])

        # Brand mentions from description and hashtags
        for brand in _KNOWN_BRANDS:
            if brand in description:
                signals['brand_mentions'][brand] += 1
        for tag in hashtags:
            tag_lower = tag.lower().replace('_', ' ')
            if tag_lower in _KNOWN_BRANDS:
                signals['brand_mentions'][tag_lower] += 1
        # @mentions in TikTok descriptions
        tt_mentions = re.findall(r'@(\w+)', description)
        for m in tt_mentions:
            m_lower = m.lower()
            if m_lower not in _NON_BRAND_HANDLES and len(m_lower) > 2:
                clean = m_lower.replace('_', ' ')
                if clean in _KNOWN_BRANDS:
                    signals['brand_mentions'][clean] += 1
                else:
                    signals['brand_mentions'][m_lower] += 1

        # Music trends
        if music:
            signals['music_trends'][music.lower()] += 1

        # Engagement
        total_engagement = likes + comments + shares
        if total_engagement > 1000:
            signals['trending_topics'].extend(hashtags)
            signals['current_interests'].append(description[:100])
    
    # Analyze reposts (aspirational content)
    for repost in reposts:
        description = repost.get('description', '').lower()
        hashtags = repost.get('hashtags', [])
        signals['aspirational_content'].extend(hashtags)
        signals['aspirational_content'].append(description[:100])
    
    # Favorite creators analysis
    favorite_creators = tt_data.get('favorite_creators', [])
    for creator, count in favorite_creators[:10]:
        signals['creator_styles'].append({
            'creator': creator,
            'repost_count': count,
            'significance': 'high' if count > 5 else 'medium'
        })
    
    # Convert to dicts
    signals['hashtags'] = dict(signals['hashtags'].most_common(50))
    signals['music_trends'] = dict(signals['music_trends'].most_common(20))
    signals['brand_mentions'] = dict(signals['brand_mentions'].most_common(15))
    signals['trending_topics'] = list(set(signals['trending_topics']))[:20]
    signals['aspirational_content'] = list(set(signals['aspirational_content']))[:30]
    signals['current_interests'] = list(set(signals['current_interests']))[:20]

    return signals

def extract_all_pinterest_signals(pinterest_data):
    """
    Extract EVERYTHING possible from Pinterest data
    """
    if not pinterest_data:
        return {}
    
    boards = pinterest_data.get('boards', [])
    
    signals = {
        'board_themes': Counter(),
        'pin_keywords': Counter(),
        'aspirational_categories': [],
        'price_ranges': [],
        'style_preferences': Counter(),
        'planning_mindset': False,
        'specific_wants': []
    }
    
    for board in boards:
        board_name = board.get('name', '').lower()
        description = board.get('description', '').lower()
        pins = board.get('pins', [])
        
        # Board themes
        signals['board_themes'][board_name] = len(pins)
        
        # Analyze pins
        for pin in pins[:20]:  # Top 20 pins per board
            title = pin.get('title', '').lower()
            pin_description = pin.get('description', '').lower()
            
            # Extract keywords
            all_text = f"{title} {pin_description}"
            words = all_text.split()
            # Filter meaningful words (length > 3, not common words)
            meaningful_words = [w for w in words if len(w) > 3 and w not in ['that', 'this', 'with', 'from', 'have', 'been']]
            signals['pin_keywords'].update(meaningful_words)
            
            # Extract specific wants (product names, brands)
            if any(word in all_text for word in ['want', 'need', 'wish', 'love', 'dream']):
                signals['specific_wants'].append(title[:100])
            
            # Extract price mentions
            price_patterns = re.findall(r'\$(\d+)', all_text)
            signals['price_ranges'].extend([int(p) for p in price_patterns])
        
        # Planning mindset indicators
        planning_keywords = ['wedding', 'home', 'decor', 'renovation', 'party', 'event']
        if any(keyword in board_name or keyword in description for keyword in planning_keywords):
            signals['planning_mindset'] = True
    
    # Convert to dicts
    signals['board_themes'] = dict(signals['board_themes'].most_common(20))
    signals['pin_keywords'] = dict(signals['pin_keywords'].most_common(50))
    signals['aspirational_categories'] = list(set([b['name'] for b in boards]))[:15]
    
    # Price range analysis
    if signals['price_ranges']:
        signals['price_preferences'] = {
            'min': min(signals['price_ranges']),
            'max': max(signals['price_ranges']),
            'avg': sum(signals['price_ranges']) / len(signals['price_ranges'])
        }
    
    return signals

def combine_all_signals(platform_data):
    """
    Combine signals from all platforms for comprehensive analysis
    """
    all_signals = {
        'instagram': {},
        'tiktok': {},
        'pinterest': {},
        'combined': {}
    }
    
    # Extract from each platform
    if 'instagram' in platform_data:
        all_signals['instagram'] = extract_all_instagram_signals(
            platform_data['instagram'].get('data', {})
        )
    
    if 'tiktok' in platform_data:
        all_signals['tiktok'] = extract_all_tiktok_signals(
            platform_data['tiktok'].get('data', {})
        )
    
    if 'pinterest' in platform_data:
        all_signals['pinterest'] = extract_all_pinterest_signals(
            platform_data['pinterest']
        )
    
    # Combine signals
    combined = {
        'all_hashtags': Counter(),
        'all_brands': Counter(),
        'all_activities': Counter(),
        'all_aesthetics': Counter(),
        'aspirational_interests': [],
        'current_interests': [],
        'high_engagement_topics': [],
        'price_preferences': {}
    }
    
    # Combine hashtags
    if all_signals['instagram'].get('hashtags'):
        combined['all_hashtags'].update(all_signals['instagram']['hashtags'])
    if all_signals['tiktok'].get('hashtags'):
        combined['all_hashtags'].update(all_signals['tiktok']['hashtags'])
    
    # Combine brands (from all platforms)
    if all_signals['instagram'].get('brand_mentions'):
        combined['all_brands'].update(all_signals['instagram']['brand_mentions'])
    if all_signals['tiktok'].get('brand_mentions'):
        combined['all_brands'].update(all_signals['tiktok']['brand_mentions'])
    
    # Combine activities
    if all_signals['instagram'].get('activity_types'):
        combined['all_activities'].update(all_signals['instagram']['activity_types'])
    
    # Combine aesthetics
    if all_signals['instagram'].get('aesthetic_keywords'):
        combined['all_aesthetics'].update(all_signals['instagram']['aesthetic_keywords'])
    
    # Aspirational interests
    if all_signals['tiktok'].get('aspirational_content'):
        combined['aspirational_interests'].extend(all_signals['tiktok']['aspirational_content'])
    if all_signals['pinterest'].get('specific_wants'):
        combined['aspirational_interests'].extend(all_signals['pinterest']['specific_wants'])
    
    # Current interests
    if all_signals['tiktok'].get('current_interests'):
        combined['current_interests'].extend(all_signals['tiktok']['current_interests'])
    if all_signals['instagram'].get('recent_interests'):
        combined['current_interests'].extend(all_signals['instagram']['recent_interests'])
    
    # High engagement topics
    if all_signals['instagram'].get('high_engagement_content'):
        for content in all_signals['instagram']['high_engagement_content']:
            combined['high_engagement_topics'].extend(content.get('hashtags', []))
    
    # Price preferences
    if all_signals['pinterest'].get('price_preferences'):
        combined['price_preferences'] = all_signals['pinterest']['price_preferences']
    
    # Convert to dicts
    combined['all_hashtags'] = dict(combined['all_hashtags'].most_common(30))
    combined['all_brands'] = dict(combined['all_brands'].most_common(15))
    combined['all_activities'] = dict(combined['all_activities'].most_common(20))
    combined['all_aesthetics'] = dict(combined['all_aesthetics'].most_common(15))
    combined['aspirational_interests'] = list(set(combined['aspirational_interests']))[:30]
    combined['current_interests'] = list(set(combined['current_interests']))[:20]
    combined['high_engagement_topics'] = list(set(combined['high_engagement_topics']))[:20]
    
    all_signals['combined'] = combined
    
    return all_signals
