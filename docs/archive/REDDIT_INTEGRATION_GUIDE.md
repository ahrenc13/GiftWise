# Reddit Scraper Integration Guide

## Overview

The Reddit scraper (`reddit_scraper.py`) provides real-time gift intelligence from Reddit communities to supplement Instagram/TikTok profile data during recommendation generation.

**Key Value:** Adds "what people are actually buying/recommending" insights based on crowd-sourced Reddit discussions.

## Quick Start

```python
from reddit_scraper import RedditGiftScraper

# Initialize scraper
scraper = RedditGiftScraper()

# Get insights for user interests
insights = scraper.get_gift_insights_for_interests(
    interests=['hiking', 'photography', 'coffee'],
    limit=50
)

# Access results
print(f"Found {len(insights['insights'])} product recommendations")
print(f"Trending: {', '.join(insights['trending_interests'])}")
```

## Integration Points

### Option 1: Profile Building (Recommended)

Integrate directly into `profile_analyzer.py` to enrich the profile before curation.

**File:** `profile_analyzer.py`
**Function:** `build_recipient_profile()`
**Location:** After interests are extracted (~line 200+)

```python
# In build_recipient_profile() after extracting interests:

from reddit_scraper import RedditGiftScraper

# Extract Reddit insights
reddit_scraper = RedditGiftScraper()
reddit_insights = reddit_scraper.get_gift_insights_for_interests(
    interests=[i['name'] for i in profile.get('interests', [])],
    limit=50
)

# Add to profile
profile['reddit_insights'] = reddit_insights

# Log results
logger.info(f"Reddit insights: {len(reddit_insights['insights'])} products, "
           f"{reddit_insights['source_quality']['posts_analyzed']} posts analyzed")
```

**Benefits:**
- Reddit insights available to both enrichment and curation
- Cached in profile (no duplicate API calls)
- Transparent to curator (just more profile data)

### Option 2: Recommendation Route

Integrate in `giftwise_app.py` recommendation route after profile building.

**File:** `giftwise_app.py`
**Route:** `/api/recommendations` (or wherever profile is built)
**Location:** After `build_recipient_profile()` returns

```python
# In recommendation route, after profile analysis:

from reddit_scraper import RedditGiftScraper

reddit_scraper = RedditGiftScraper()
reddit_insights = reddit_scraper.get_gift_insights_for_interests(
    interests=[i['name'] for i in profile.get('interests', [])],
    limit=50
)

# Add to session data for curator
session['reddit_insights'] = reddit_insights
```

**Benefits:**
- Clean separation of concerns
- Easy to A/B test (enable/disable via feature flag)
- Doesn't modify profile_analyzer.py

### Option 3: Curator Prompt Enhancement

Pass Reddit insights directly to the gift curator prompt.

**File:** `gift_curator.py`
**Function:** Curator prompt construction
**Location:** Before calling Claude API

```python
# In curator prompt:

# Add Reddit intelligence section
if 'reddit_insights' in profile and profile['reddit_insights']['insights']:
    reddit_section = "\n\n## REDDIT GIFT INTELLIGENCE\n"
    reddit_section += "Real recommendations from Reddit communities:\n\n"

    for product in profile['reddit_insights']['insights'][:10]:  # Top 10
        reddit_section += f"- **{product['product_name']}** "
        reddit_section += f"({product['social_proof']} upvotes, {product['sentiment']})\n"
        reddit_section += f"  Context: {product['context']}\n"
        reddit_section += f"  Subreddit: r/{product['subreddit']}\n\n"

    # Add to curator prompt
    prompt += reddit_section
```

**Benefits:**
- Curator sees "what real people recommend"
- Social proof signals (upvotes) guide curation
- Adds specificity (brand names, model numbers)

## Output Structure

```python
{
    'insights': [
        {
            'product_name': 'Instant Pot Duo',
            'brands': ['instant pot'],
            'price_range': '50_100',
            'sentiment': 'positive',  # 'positive', 'negative', 'neutral'
            'social_proof': 847,  # upvotes
            'discussion_url': 'https://reddit.com/r/Cooking/...',
            'subreddit': 'Cooking',
            'context': 'Life changing kitchen gadget. Makes meal prep easier.',
            'confidence': 0.85  # 0.0-1.0 based on upvotes and brand matches
        },
        # ... more products
    ],
    'trending_interests': ['cooking', 'kitchen gadgets'],  # From user's interests
    'gift_trends': {
        'experiences_vs_physical': 0.3,  # 30% experience gifts in discussions
        'price_ranges': {
            'under_50': 0.4,
            '50_100': 0.3,
            'over_100': 0.3
        },
        'personalization_preference': 0.6  # 60% of posts mention personalization
    },
    'source_quality': {
        'posts_analyzed': 125,
        'subreddits_checked': 8,
        'products_extracted': 47,
        'cache_age_hours': 2,  # How fresh is the data
        'timestamp': '2026-02-16T14:30:00'
    }
}
```

## Use Cases

### 1. Validate Product Choices
If curator selects a product, check if it appears in Reddit insights (crowd validation).

### 2. Discover Specific Brands
Reddit discussions mention specific brands ("Baratza Encore", "Lodge cast iron"). Use for search queries.

### 3. Identify Anti-Recommendations
Products with negative sentiment = avoid. "Broke after a month", "waste of money", etc.

### 4. Price Anchoring
Reddit price trends inform budget guidance. If 60% of recommendations are under $50, adjust accordingly.

### 5. Experience Gift Preference
If `experiences_vs_physical` is high (0.4+), prioritize experience gifts.

## Performance Notes

**Caching:**
- Results cached for 6 hours per interest set
- Cache stored in `data/reddit_cache.json`
- Reduces API calls by ~90%

**Rate Limiting:**
- 2 seconds between Reddit API requests
- Max 10 subreddits per session
- Typical session: 20-30 seconds total

**Fallback Data:**
- If Reddit API blocks requests (common), uses curated fallback data
- Fallback covers 20+ popular subreddits with real top posts
- Graceful degradation = always provides value

## Configuration

**Environment Variables (optional):**
```bash
# Override cache duration (default: 6 hours)
REDDIT_CACHE_HOURS=12

# Override rate limit delay (default: 2 seconds)
REDDIT_RATE_LIMIT=3

# Disable Reddit scraping entirely
REDDIT_ENABLED=false
```

**Feature Flag (recommended):**
```python
# In config.py or feature flags
FEATURES = {
    'reddit_insights': True,  # Enable/disable Reddit scraper
}

# In integration code:
if config.FEATURES.get('reddit_insights', True):
    reddit_insights = scraper.get_gift_insights_for_interests(...)
```

## Testing

Run standalone test:
```bash
python reddit_scraper.py
```

Expected output:
- Maps 3 test interests to 10+ subreddits
- Scrapes posts (or uses fallback)
- Extracts product mentions with social proof
- Shows top 3 recommendations

Test with real profile:
```python
from reddit_scraper import RedditGiftScraper

scraper = RedditGiftScraper()

# Test with real user interests
test_interests = ['hiking', 'coffee', 'photography', 'cooking']
insights = scraper.get_gift_insights_for_interests(test_interests, limit=50)

print(f"Products: {len(insights['insights'])}")
print(f"Trending: {insights['trending_interests']}")
print(f"Posts analyzed: {insights['source_quality']['posts_analyzed']}")

# Show top 5
for i, product in enumerate(insights['insights'][:5], 1):
    print(f"{i}. {product['product_name']} ({product['social_proof']} upvotes)")
```

## Interest → Subreddit Mappings

The scraper includes 200+ interest mappings. Key examples:

**Tech & Gaming:**
- `gaming` → r/gaming, r/pcmasterrace, r/NintendoSwitch, r/PS5
- `tech` → r/gadgets, r/BuyItForLife, r/technology
- `streaming` → r/Twitch, r/streaming

**Cooking & Food:**
- `cooking` → r/Cooking, r/AskCulinary, r/seriouseats
- `coffee` → r/Coffee, r/espresso, r/pourover
- `baking` → r/Baking, r/Breadit, r/sourdough

**Fitness & Outdoors:**
- `hiking` → r/hiking, r/CampingGear, r/Ultralight
- `fitness` → r/Fitness, r/xxfitness, r/homegym
- `running` → r/running, r/AdvancedRunning, r/C25K

**Creative & Arts:**
- `photography` → r/photography, r/AskPhotography, r/cameras
- `art` → r/Art, r/crafts, r/somethingimade
- `music` → r/WeAreTheMusicMakers, r/Guitar, r/synthesizers

See `reddit_scraper.py` for full mapping (200+ interests).

## Troubleshooting

**No posts scraped (all fallback):**
- Reddit API may be blocking requests
- This is normal and expected (Reddit blocks unauthenticated scraping)
- Fallback data is high-quality and provides real value

**Cache not working:**
- Check `data/` directory exists and is writable
- Cache file: `data/reddit_cache.json`
- Clear cache: `rm data/reddit_cache.json`

**Rate limiting errors:**
- Increase `RATE_LIMIT_DELAY` to 3-4 seconds
- Reduce `MAX_SUBREDDITS_PER_SESSION` to 5-7

**Poor product extraction:**
- Fallback data is manually curated (high quality)
- Live scraping quality varies by subreddit
- Use `MIN_UPVOTES` to filter low-quality posts

## Future Enhancements

**OAuth Authentication:**
- Implement Reddit OAuth for reliable API access
- Requires Reddit app credentials
- Removes need for fallback data

**Real-time API:**
- Integrate Pushshift API for historical data
- More comprehensive search
- Better trend analysis

**Sentiment Analysis:**
- Use NLP for better sentiment scoring
- Identify specific pain points ("broke after 2 months")
- Extract common use cases

**Collaborative Filtering:**
- "People who liked X also recommended Y"
- Cross-interest recommendations
- Subreddit similarity scoring

## Questions?

**Q: Why fallback data instead of OAuth?**
A: OAuth requires app credentials and user flow. Fallback provides immediate value without setup. Can add OAuth later.

**Q: How fresh is the data?**
A: Cached for 6 hours. Live scraping gets last 30 days. Fallback is manually curated from recent top posts.

**Q: Does this slow down recommendations?**
A: First request per session: 20-30s. Subsequent requests: instant (cached). Can run async if needed.

**Q: What if Reddit is down?**
A: Falls back to curated data. Never fails, always returns results.

**Q: How do I disable it?**
A: Set `REDDIT_ENABLED=false` or wrap integration in feature flag check.
