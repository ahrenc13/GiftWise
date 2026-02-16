"""
Test script to verify Awin integration and Promeed feed availability.
Run this on Railway to test the integration.
"""
import os
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_awin_promeed():
    """Test Awin API and check for Promeed feed."""

    # Check API key
    api_key = os.getenv('AWIN_DATA_FEED_API_KEY', '')
    if not api_key:
        print("❌ AWIN_DATA_FEED_API_KEY not set")
        return False

    print(f"✓ AWIN_DATA_FEED_API_KEY found: {api_key[:10]}...")
    print()

    # Import Awin searcher
    try:
        from awin_searcher import _get_feed_list
    except ImportError as e:
        print(f"❌ Failed to import awin_searcher: {e}")
        return False

    # Fetch feed list
    print("Fetching Awin feed list...")
    try:
        feeds = _get_feed_list(api_key)
        print(f"✓ Found {len(feeds)} Awin feeds")
        print()
    except Exception as e:
        print(f"❌ Failed to fetch feed list: {e}")
        return False

    # Show all advertisers
    print("=" * 60)
    print("AVAILABLE ADVERTISERS:")
    print("=" * 60)

    promeed_found = False
    for i, feed in enumerate(feeds, 1):
        advertiser_name = feed.get('advertiser_name', 'Unknown')
        feed_id = feed.get('feed_id', '?')
        status = feed.get('membership_status', '?')

        # Highlight Promeed
        if 'promeed' in advertiser_name.lower():
            print(f"\n🎯 {i}. {advertiser_name} (Feed ID: {feed_id}) - Status: {status} 🎯")
            promeed_found = True
        else:
            print(f"{i}. {advertiser_name} (Feed ID: {feed_id}) - Status: {status}")

    print("=" * 60)
    print()

    # Check if Promeed was found
    if promeed_found:
        print("✅ SUCCESS: Promeed feed is available!")
        print()
        print("Next steps:")
        print("1. Promeed products will be included in gift searches")
        print("2. Commission: 12-25% (vs Amazon's 1-4%)")
        print("3. Product categories: silk pillowcases, cooling comforters, bedding")
        print("4. Matches: beauty, wellness, sleep, home interests")
        return True
    else:
        print("⚠️  Promeed not found in feed list")
        print()
        print("Possible reasons:")
        print("1. Promeed approval is still processing (can take 24-48 hours)")
        print("2. Check Awin dashboard to confirm Promeed status is 'Joined'")
        print("3. Feed may take time to appear after approval")
        return False

if __name__ == '__main__':
    success = test_awin_promeed()
    sys.exit(0 if success else 1)
