"""
REVENUE OPTIMIZER - Maximize value per Claude API call

This module implements intelligent pre-filtering of products BEFORE they go to the curator.
Goal: Send 30 high-quality products instead of 100 random ones.

Benefits:
1. Curator gets better input → better output → higher CTR
2. Fewer tokens sent to Claude → lower cost
3. Prioritize high-commission products → higher revenue per click

Author: Chad + Claude
Date: February 2026
"""

import logging
from typing import List, Dict, Optional
from collections import defaultdict

logger = logging.getLogger('giftwise')

# Commission rates by retailer (approximate)
COMMISSION_RATES = {
    'etsy': 0.04,        # 4% via Awin
    'amazon': 0.02,      # 1-4%, use conservative 2%
    'ebay': 0.03,        # 1-4%, use 3%
    'awin': 0.05,        # Varies, use 5% average
    'skimlinks': 0.04,   # Varies, ~4% average after Skimlinks cut
}


def score_product_for_profile(product: Dict, profile: Dict, relationship: str) -> float:
    """
    Score a product's suitability for a profile
    Returns 0.0-1.0 score (higher = better fit)

    Uses local intelligence to pre-filter before expensive Claude call
    """
    try:
        import database
    except ImportError:
        logger.warning("Database not available, skipping intelligent pre-filtering")
        return 0.5  # Neutral score if no intelligence available

    score = 0.0
    reasons = []

    # Factor 1: Product intelligence from past performance (30% weight)
    product_id = product.get('product_id', '')
    retailer = product.get('source_domain', '') or product.get('retailer', '')

    intel = database.get_product_intelligence(product_id, retailer)
    if intel:
        gift_score = intel.get('gift_worthiness_score', 0.5)
        score += gift_score * 0.3
        reasons.append(f"gift_score={gift_score:.2f}")

        # CTR boost (proven products get priority)
        ctr = intel.get('click_through_rate', 0.0)
        if ctr > 0.05:  # 5%+ CTR is good
            score += 0.15
            reasons.append(f"high_ctr={ctr:.1%}")
        elif ctr > 0:
            score += ctr * 2  # Scale CTR to 0-0.10 bonus
            reasons.append(f"ctr={ctr:.1%}")

    # Factor 2: Interest matching using intelligence (30% weight)
    interests = profile.get('interests', [])
    product_title = product.get('title', '').lower()
    product_snippet = product.get('snippet', '').lower()

    for interest in interests:
        interest_name = interest.get('name', '').lower()

        # Get interest intelligence
        interest_intel = database.get_interest_intelligence(interest_name)

        if interest_intel:
            # Check do_buy list (strong positive signal)
            do_buy = interest_intel.get('do_buy', [])
            for good_item in do_buy:
                if good_item.lower() in product_title or good_item.lower() in product_snippet:
                    score += 0.15
                    reasons.append(f"matches_do_buy[{interest_name}]")
                    break

            # Check dont_buy list (strong negative signal)
            dont_buy = interest_intel.get('dont_buy', [])
            for bad_item in dont_buy:
                if bad_item.lower() in product_title or bad_item.lower() in product_snippet:
                    score -= 0.3  # Heavy penalty
                    reasons.append(f"AVOID:matches_dont_buy[{interest_name}]")
                    break
        else:
            # No intelligence yet, do simple keyword matching
            if interest_name in product_title or interest_name in product_snippet:
                score += 0.10
                reasons.append(f"keyword_match[{interest_name}]")

    # Factor 3: Commission rate (20% weight) - REVENUE-AWARE
    commission_rate = COMMISSION_RATES.get(retailer.lower(), 0.01)
    if intel:
        commission_rate = intel.get('commission_rate', commission_rate)

    score += commission_rate * 4  # 5% commission = +0.20 score
    if commission_rate >= 0.04:
        reasons.append(f"high_commission={commission_rate:.1%}")

    # Factor 4: Price appropriateness (10% weight)
    price = product.get('price', 0)
    if isinstance(price, str):
        try:
            price = float(price.replace('$', '').replace(',', ''))
        except:
            price = 0

    price_range = profile.get('price_signals', {}).get('estimated_range', '')
    if price_range and '-' in price_range:
        try:
            low, high = price_range.replace('$', '').split('-')
            low, high = float(low), float(high)
            if low <= price <= high:
                score += 0.10
                reasons.append("price_in_range")
            elif price < low * 0.5:  # Too cheap (might seem low-quality)
                score -= 0.05
                reasons.append("price_too_low")
            elif price > high * 2:  # Too expensive
                score -= 0.10
                reasons.append("price_too_high")
        except:
            pass

    # Factor 5: Relationship appropriateness (10% weight)
    if intel:
        best_relationships = intel.get('best_for_relationship', [])
        if isinstance(best_relationships, list) and relationship in best_relationships:
            score += 0.10
            reasons.append(f"good_for_{relationship}")

    # Clamp score to 0.0-1.0
    score = max(0.0, min(1.0, score))

    if score > 0.6:
        logger.debug(f"High-score product: {product.get('title', '')[:50]} = {score:.2f} ({', '.join(reasons[:3])})")
    elif score < 0.2:
        logger.debug(f"Low-score product (filtered): {product.get('title', '')[:50]} = {score:.2f} ({', '.join(reasons[:3])})")

    return score


def intelligent_product_filter(products: List[Dict], profile: Dict, relationship: str, target_count: int = 30) -> List[Dict]:
    """
    Reduce product pool to high-quality candidates using local intelligence

    Args:
        products: Full product pool (e.g., 100 products)
        profile: User's recipient profile
        relationship: Relationship type (friend, partner, family, myself)
        target_count: How many products to return (default: 30)

    Returns:
        Filtered list of top products

    This saves API tokens and improves curator output quality
    """
    logger.info(f"Intelligent pre-filtering: {len(products)} products → target {target_count}")

    # Score all products
    scored_products = []
    for product in products:
        score = score_product_for_profile(product, profile, relationship)
        scored_products.append((score, product))

    # Sort by score (highest first)
    scored_products.sort(reverse=True, key=lambda x: x[0])

    # Take top N with score > threshold
    min_score = 0.25  # Don't send junk to curator
    filtered = [product for score, product in scored_products if score >= min_score][:target_count]

    logger.info(f"Filtered to {len(filtered)} high-quality products (scores {scored_products[0][0]:.2f}-{scored_products[min(len(scored_products)-1, target_count-1)][0]:.2f})")

    # Fallback: if we filtered too aggressively, take top N regardless of score
    if len(filtered) < target_count // 2:
        logger.warning(f"Aggressive filtering left only {len(filtered)} products, relaxing threshold")
        filtered = [product for score, product in scored_products[:target_count]]

    return filtered


def track_curation_outcome(product: Dict, action: str):
    """
    Track when a product is recommended, clicked, or favorited
    Builds intelligence over time

    Args:
        product: Product dict with product_id, retailer
        action: 'recommended', 'clicked', 'favorited'
    """
    try:
        import database

        product_id = product.get('product_id', '')
        retailer = product.get('source_domain', '') or product.get('retailer', '')

        if not product_id or not retailer:
            return

        if action == 'recommended':
            database.track_product_recommended(product_id, retailer)
        elif action == 'clicked':
            database.track_product_clicked(product_id, retailer)
        elif action == 'favorited':
            database.track_product_favorited(product_id, retailer)

        logger.debug(f"Tracked {action} for {product_id} ({retailer})")

    except Exception as e:
        logger.error(f"Failed to track curation outcome: {e}")


def track_profile_interests(profile: Dict):
    """
    Track which interests we've seen
    Helps prioritize which interests to pre-cache products for
    """
    try:
        import database

        for interest in profile.get('interests', []):
            interest_name = interest.get('name', '')
            if interest_name:
                database.increment_interest_seen(interest_name)

    except Exception as e:
        logger.error(f"Failed to track profile interests: {e}")


def populate_interest_intelligence_from_enrichment():
    """
    One-time migration: Import static intelligence from enrichment_data.py
    into the interest_intelligence database table

    Run this once to seed the database with existing knowledge
    """
    try:
        import database
        from enrichment_data import GIFT_INTELLIGENCE

        count = 0
        for interest_name, data in GIFT_INTELLIGENCE.items():
            # Determine trending level from trending_2026 field
            trending_level = 'trending' if data.get('trending_2026') else 'evergreen'

            database.upsert_interest_intelligence(interest_name, {
                'do_buy': data.get('do_buy', []),
                'dont_buy': data.get('dont_buy', []),
                'demographics': '',  # Not in GIFT_INTELLIGENCE structure
                'trending_level': trending_level,
                'avg_price_point': 0.0,  # Will be learned from sessions
            })
            count += 1

        logger.info(f"Populated {count} interests from enrichment_data.py")
        return count

    except ImportError as e:
        logger.warning(f"enrichment_data.py not available: {e}")
        return 0
    except Exception as e:
        logger.error(f"Failed to populate interest intelligence: {e}")
        import traceback
        traceback.print_exc()
        return 0


if __name__ == "__main__":
    # Test script: populate interest intelligence from enrichment_data.py
    print("Revenue Optimizer - Database Seeding")
    print("=" * 60)

    count = populate_interest_intelligence_from_enrichment()
    print(f"✅ Populated {count} interests into database")

    # Show sample
    try:
        import database
        sample = database.get_interest_intelligence('taylor-swift')
        if sample:
            print(f"\nSample intelligence for 'taylor-swift':")
            print(f"  Do buy: {sample.get('do_buy', [])[:5]}")
            print(f"  Don't buy: {sample.get('dont_buy', [])[:5]}")
        else:
            print("\nNo sample data found (enrichment_data.py may not have 'taylor-swift')")
    except Exception as e:
        print(f"\nCouldn't fetch sample: {e}")
