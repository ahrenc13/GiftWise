#!/usr/bin/env python3
"""
Test multi-retailer search with CJ + Amazon + eBay to validate:
1. Source interleaving (CJ doesn't dominate)
2. Post-curation cleanup (diversity rules work)
3. Full pipeline with real mix

Run: python3 test_multi_retailer_mix.py
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from multi_retailer_searcher import search_products_multi_retailer
from config_service import get_config
import json
import os
from collections import Counter

def test_multi_retailer_mix():
    """Test full pipeline with Amazon + eBay + CJ"""

    print("\n" + "="*80)
    print("MULTI-RETAILER MIX TEST (Amazon + eBay + CJ)")
    print("="*80)

    # Test profile - generic interests that all retailers can serve
    test_profile = {
        'interests': [
            {'name': 'coffee culture', 'strength': 'strong', 'context': 'Pour-over enthusiast, buys single-origin beans'},
            {'name': 'hiking', 'strength': 'medium', 'context': 'Weekend day hikes, Pacific Northwest trails'},
            {'name': 'cooking', 'strength': 'medium', 'context': 'Experiments with new recipes, loves kitchen gadgets'}
        ],
        'age_range': '25-34',
        'gender': 'F',
        'relationship': 'friend',
        'budget': 'medium'
    }

    print(f"\n📋 Test Profile:")
    print(f"   Interests: {[i['name'] for i in test_profile['interests']]}")
    print(f"   Relationship: {test_profile['relationship']}")
    print(f"   Budget: {test_profile['budget']}")

    # Get config to verify what's available
    try:
        config = get_config()
    except:
        print("⚠️  Config validation failed (expected in test env)")
        config = None

    print(f"\n🔧 Retailer Status:")
    if config:
        print(f"   Amazon: {'✅' if config.affiliate.rapidapi_key else '❌'}")
        print(f"   eBay: {'✅' if config.affiliate.ebay_client_id else '❌'}")
        print(f"   CJ: {'✅' if config.affiliate.cj_api_token else '❌'}")
        print(f"   Awin: {'✅' if config.affiliate.awin_api_token else '❌'}")
        print(f"   Etsy: {'✅' if config.affiliate.etsy_api_key else '❌'}")
    else:
        print("   (Checking via env vars)")
        print(f"   Amazon: {'✅' if os.getenv('RAPIDAPI_KEY') else '❌'}")
        print(f"   eBay: {'✅' if os.getenv('EBAY_CLIENT_ID') else '❌'}")
        print(f"   CJ: {'✅' if os.getenv('CJ_API_TOKEN') else '❌'}")
        print(f"   Awin: {'✅' if os.getenv('AWIN_API_TOKEN') else '❌'}")
        print(f"   Etsy: {'✅' if os.getenv('ETSY_API_KEY') else '❌'}")

    # Search all retailers - pass credentials explicitly
    print(f"\n🔍 Searching all retailers...")
    products = search_products_multi_retailer(
        test_profile,
        amazon_key=os.getenv('RAPIDAPI_KEY'),
        ebay_client_id=os.getenv('EBAY_CLIENT_ID'),
        ebay_client_secret=os.getenv('EBAY_CLIENT_SECRET'),
        cj_api_key=os.getenv('CJ_API_TOKEN'),
        cj_company_id=os.getenv('CJ_COMPANY_ID'),
        cj_publisher_id=os.getenv('CJ_PUBLISHER_ID', '5416819'),  # Default to known value
        awin_data_feed_api_key=os.getenv('AWIN_API_TOKEN'),
        etsy_key=os.getenv('ETSY_API_KEY'),
        target_count=30
    )

    if not products:
        print("\n❌ No products found")
        print("\n💡 This test requires retailer credentials to be set.")
        print("   Run this in Railway (credentials set in dashboard) or set env vars:")
        print("   - RAPIDAPI_KEY (Amazon)")
        print("   - EBAY_CLIENT_ID + EBAY_CLIENT_SECRET (eBay)")
        print("   - CJ_API_TOKEN + CJ_COMPANY_ID (CJ Affiliate)")
        print("   - AWIN_API_TOKEN (Awin - for Promeed advertiser)")
        return

    print(f"\n✅ Found {len(products)} products")

    # Analyze source distribution
    source_counts = {}
    for p in products:
        source = p.get('source_domain', 'unknown')
        source_counts[source] = source_counts.get(source, 0) + 1

    print(f"\n📊 Source Distribution:")
    for source, count in sorted(source_counts.items(), key=lambda x: x[1], reverse=True):
        pct = (count / len(products)) * 100
        print(f"   {source}: {count} products ({pct:.1f}%)")

    # Check for Awin and CJ specifically (user wants both)
    awin_count = sum(1 for p in products if 'awin' in p.get('source_domain', '').lower())
    cj_count = sum(1 for p in products if any(x in p.get('link', '') for x in ['anrdoezrs.net', 'jdoqocy.com', 'dpbolvw.net', 'apmebf.com', 'tkqlhce.com']))

    print(f"\n🎯 Affiliate Network Breakdown:")
    print(f"   Awin products (incl. Promeed): {awin_count}")
    print(f"   CJ Affiliate products: {cj_count}")
    if awin_count > 0 and cj_count > 0:
        print(f"   ✅ Getting products from BOTH Awin and CJ")
    elif awin_count > 0:
        print(f"   ⚠️  Only getting Awin products (CJ may not be approved yet)")
    elif cj_count > 0:
        print(f"   ⚠️  Only getting CJ products (Awin advertisers may not be joined)")
    else:
        print(f"   ℹ️  No Awin or CJ products found (check credentials/approvals)")

    # Show interleaving pattern (first 20 products)
    print(f"\n🔀 Interleaving Pattern (First 20):")
    for i, p in enumerate(products[:20], 1):
        source = p.get('source_domain', 'unknown')
        title = p.get('title', 'No title')[:50]
        interest = p.get('interest_match', 'unknown')
        print(f"   {i:2d}. [{source:20s}] {title} ({interest})")

    # Analyze brand distribution
    brand_counts = {}
    for p in products:
        # Extract brand from snippet or title
        snippet = p.get('snippet', '')
        # Simple brand extraction (first word before "—" or "by")
        brand = snippet.split('—')[0].split(' by ')[0].strip() if snippet else 'Unknown'
        brand_counts[brand] = brand_counts.get(brand, 0) + 1

    print(f"\n🏷️  Brand Distribution:")
    top_brands = sorted(brand_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    for brand, count in top_brands:
        if count > 1:  # Only show duplicates
            print(f"   {brand}: {count} products")

    # Interest distribution
    interest_counts = Counter(p.get('interest_match', 'unknown') for p in products)
    print(f"\n🎯 Interest Distribution:")
    for interest, count in interest_counts.most_common():
        pct = (count / len(products)) * 100
        print(f"   {interest}: {count} products ({pct:.1f}%)")

    # Check for consecutive runs from same source (anti-pattern)
    print(f"\n🔍 Checking for source clumping...")
    max_consecutive = 1
    current_source = None
    current_run = 0
    for p in products:
        source = p.get('source_domain', 'unknown')
        if source == current_source:
            current_run += 1
            max_consecutive = max(max_consecutive, current_run)
        else:
            current_source = source
            current_run = 1

    if max_consecutive > 5:
        print(f"   ⚠️  Found {max_consecutive} consecutive products from same source (should be ≤5)")
    else:
        print(f"   ✅ Max consecutive run: {max_consecutive} (good interleaving)")

    # Show all products with details
    print(f"\n🎁 All Products:")
    for i, p in enumerate(products, 1):
        source = p.get('source_domain', 'unknown')
        title = p.get('title', 'No title')[:60]
        interest = p.get('interest_match', 'unknown')
        price = p.get('price', 'N/A')
        print(f"   {i:2d}. [{source:15s}] ${price:6s} {title} ({interest})")

    print(f"\n{'='*80}")
    print(f"✅ TEST COMPLETE")
    print(f"{'='*80}\n")

if __name__ == '__main__':
    test_multi_retailer_mix()
