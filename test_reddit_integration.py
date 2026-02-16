"""
Test script demonstrating Reddit scraper integration with realistic user profile.

This shows how the scraper would work in the actual recommendation pipeline.
"""

import json
from reddit_scraper import RedditGiftScraper


def test_integration():
    """Simulate integration with real user profile."""

    print("=" * 80)
    print("REDDIT SCRAPER INTEGRATION TEST")
    print("Simulating real recommendation pipeline")
    print("=" * 80)

    # Simulate a user profile (from Instagram/TikTok analysis)
    mock_profile = {
        'interests': [
            {'name': 'hiking', 'strength': 'high', 'evidence': 'Posts weekly trail photos'},
            {'name': 'photography', 'strength': 'high', 'evidence': 'Landscape shots'},
            {'name': 'coffee', 'strength': 'medium', 'evidence': 'Latte art photos'},
            {'name': 'travel', 'strength': 'medium', 'evidence': 'Airport check-ins'},
            {'name': 'dogs', 'strength': 'high', 'evidence': 'Golden retriever photos'},
        ],
        'relationship': 'friend',
        'age_range': '25-35',
        'location': 'Pacific Northwest',
    }

    print(f"\n📋 Mock User Profile:")
    print(f"   Interests: {', '.join([i['name'] for i in mock_profile['interests']])}")
    print(f"   Relationship: {mock_profile['relationship']}")
    print(f"   Location: {mock_profile['location']}\n")

    # Initialize scraper
    print("🔍 Initializing Reddit scraper...")
    scraper = RedditGiftScraper()

    # Get Reddit insights
    print("📡 Fetching Reddit gift intelligence...")
    reddit_insights = scraper.get_gift_insights_for_interests(
        interests=[i['name'] for i in mock_profile['interests']],
        limit=50
    )

    # Add to profile (this is what the integration would do)
    mock_profile['reddit_insights'] = reddit_insights

    print("\n✓ Reddit insights fetched successfully!\n")

    # Display results
    print("📊 RESULTS:")
    print(f"   Products found: {len(reddit_insights['insights'])}")
    print(f"   Posts analyzed: {reddit_insights['source_quality']['posts_analyzed']}")
    print(f"   Subreddits checked: {reddit_insights['source_quality']['subreddits_checked']}")
    print(f"   Trending interests: {', '.join(reddit_insights['trending_interests'])}")

    # Gift trends
    trends = reddit_insights['gift_trends']
    print(f"\n📈 Gift Trends from Reddit:")
    print(f"   Experience vs physical: {trends['experiences_vs_physical']:.0%}")
    print(f"   Price preference:")
    print(f"     - Under $50: {trends['price_ranges']['under_50']:.0%}")
    print(f"     - $50-100: {trends['price_ranges']['50_100']:.0%}")
    print(f"     - Over $100: {trends['price_ranges']['over_100']:.0%}")
    print(f"   Personalization preference: {trends['personalization_preference']:.0%}")

    # Top recommendations
    print(f"\n🎁 Top 15 Reddit-Validated Gift Ideas:\n")
    for i, product in enumerate(reddit_insights['insights'][:15], 1):
        upvotes = product['social_proof']
        sentiment_icon = '✓' if product['sentiment'] == 'positive' else '✗' if product['sentiment'] == 'negative' else '~'

        print(f"   {i:2d}. {sentiment_icon} {product['product_name']:30s}")
        print(f"       {upvotes:4d} upvotes | r/{product['subreddit']:20s} | Confidence: {product['confidence']:.2f}")
        print(f"       \"{product['context'][:80]}...\"")
        print()

    # Show how this would be used in curator prompt
    print("\n" + "=" * 80)
    print("CURATOR PROMPT INTEGRATION EXAMPLE")
    print("=" * 80)
    print("\nThis is how Reddit insights would appear in the gift curator prompt:\n")

    curator_section = "## REDDIT GIFT INTELLIGENCE\n"
    curator_section += "Real recommendations from Reddit communities (crowd-sourced wisdom):\n\n"

    for product in reddit_insights['insights'][:10]:
        curator_section += f"- **{product['product_name']}** "
        curator_section += f"({product['social_proof']} upvotes, {product['sentiment']})\n"
        curator_section += f"  \"{product['context']}\"\n"
        curator_section += f"  Source: r/{product['subreddit']}\n\n"

    print(curator_section)

    # Show enriched profile structure
    print("=" * 80)
    print("ENRICHED PROFILE STRUCTURE")
    print("=" * 80)
    print("\nAfter integration, the profile would look like:\n")

    profile_sample = {
        'interests': [i['name'] for i in mock_profile['interests']],
        'relationship': mock_profile['relationship'],
        'reddit_insights': {
            'insights_count': len(reddit_insights['insights']),
            'top_3_products': [p['product_name'] for p in reddit_insights['insights'][:3]],
            'trending_interests': reddit_insights['trending_interests'],
            'gift_trends': reddit_insights['gift_trends'],
        }
    }

    print(json.dumps(profile_sample, indent=2))

    print("\n" + "=" * 80)
    print("✓ INTEGRATION TEST COMPLETE")
    print("=" * 80)
    print("\nNext steps:")
    print("1. Add import to profile_analyzer.py: from reddit_scraper import RedditGiftScraper")
    print("2. Call scraper after extracting interests")
    print("3. Add reddit_insights to profile dict")
    print("4. Optionally enhance curator prompt with Reddit section")
    print("\nSee REDDIT_INTEGRATION_GUIDE.md for detailed instructions.")
    print("=" * 80)


if __name__ == "__main__":
    test_integration()
