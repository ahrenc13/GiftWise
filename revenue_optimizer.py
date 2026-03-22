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
import json
import re
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
    'peets.com': 0.10,   # 10% — highest rate in stack (45-day cookie, no gift cards)
}


def score_product_for_profile(product: Dict, profile: Dict, relationship: str):
    """
    Score a product's suitability for a profile
    Returns 0.0-1.0 score (higher = better fit)

    Uses local intelligence to pre-filter before expensive Claude call
    """
    try:
        import database
    except ImportError:
        logger.warning("Database not available, skipping intelligent pre-filtering")
        return 0.5, ["no_db"]

    score = 0.0
    reasons = []

    product_id = product.get('product_id', '')
    retailer = product.get('source_domain', '') or product.get('retailer', '')

    # Factor 1: Gift suitability score (20% weight)
    # Pre-computed at sync time — available on all DB products. Clusters around 0.4–0.5
    # for most products, so contributes ~0.08–0.10 uniformly. This is intentional:
    # gift_score is a weak baseline; interest relevance (Factor 2) is the differentiator.
    gs = product.get('gift_score')
    intel = None
    if gs is not None:
        try:
            gs = float(gs)
            score += gs * 0.2
            reasons.append(f"gift_score={gs:.2f}")
        except (ValueError, TypeError):
            gs = None

    if gs is None:
        intel = database.get_product_intelligence(product_id, retailer)
        if intel:
            igscore = intel.get('gift_worthiness_score', 0.5)
            score += igscore * 0.2
            reasons.append(f"intel_gift_score={igscore:.2f}")
    else:
        intel = database.get_product_intelligence(product_id, retailer)

    if intel:
        ctr = intel.get('click_through_rate', 0.0)
        if ctr > 0.05:
            score += 0.15
            reasons.append(f"high_ctr={ctr:.1%}")
        elif ctr > 0:
            score += ctr * 2
            reasons.append(f"ctr={ctr:.1%}")

    # Factor 2: Interest matching (PRIMARY DIFFERENTIATOR — up to 50% of score)
    # Scores accumulate across ALL profile interests, not just the first match.
    # A product matching 3 interests should clearly outscore one matching 1.
    interests = profile.get('interests') or []
    product_title = product.get('title', '').lower()
    product_snippet = product.get('snippet', '').lower()
    raw_tags = product.get('interest_tags', '')

    # Parse interest_tags as JSON array for proper membership checking.
    # Previously did substring matching on the JSON string, causing false positives:
    # "wine tasting" in '["wine", "tasting", "gardening"]' → False (lucky)
    # "music" in '["80s music", "vinyl"]' → True (wrong: substring of "80s music")
    parsed_tags = []
    if isinstance(raw_tags, str) and raw_tags:
        try:
            parsed_tags = [t.lower().strip() for t in json.loads(raw_tags) if isinstance(t, str)]
        except (json.JSONDecodeError, TypeError):
            parsed_tags = []
    elif isinstance(raw_tags, list):
        parsed_tags = [str(t).lower().strip() for t in raw_tags]

    # Build word sets for word-boundary matching (not substring matching).
    # "jim" in "jimmy's guitar shop" is a substring match (bad).
    # "jim" as a whole word in the title is a word match (still loose but better).
    title_words = set(re.findall(r'\b\w+\b', product_title))
    snippet_words = set(re.findall(r'\b\w+\b', product_snippet))
    all_tag_text = ' '.join(parsed_tags)
    tag_words = set(re.findall(r'\b\w+\b', all_tag_text))
    all_words = title_words | snippet_words | tag_words

    interest_score = 0.0
    interests_matched = 0
    interest_reasons = []

    for interest in interests:
        interest_name = interest.get('name', '').lower() if isinstance(interest, dict) else str(interest).lower()
        this_interest_matched = False

        interest_intel = database.get_interest_intelligence(interest_name)

        if interest_intel:
            # do_buy: strong positive signal for this interest
            do_buy = interest_intel.get('do_buy') or []
            for good_item in do_buy:
                if good_item.lower() in product_title:
                    interest_score += 0.20
                    interest_reasons.append(f"do_buy[{interest_name}]")
                    this_interest_matched = True
                    break

            # dont_buy: penalty regardless of other matches
            dont_buy = interest_intel.get('dont_buy') or []
            for bad_item in dont_buy:
                if bad_item.lower() in product_title:
                    score -= 0.3
                    reasons.append(f"AVOID:dont_buy[{interest_name}]")
                    break

        # Interest matching: prefer exact tag membership over scattered keyword match.
        # Use parsed JSON array for proper matching instead of substring on JSON string.
        if not this_interest_matched:
            # First: check if the full interest phrase is an exact tag (strongest signal)
            if interest_name in parsed_tags:
                interest_score += 0.20
                interest_reasons.append(f"tag_match[{interest_name}]")
                this_interest_matched = True
            else:
                # Check if interest phrase appears within any tag, but only if the tag
                # is closely related (not a mega-tag with 10+ interests crammed in).
                # A tag like "jim henson" containing interest "jim henson" is fine.
                # A tag like "jim henson muppets fraggle rock wine tasting gardening"
                # containing "jim henson" is too loose — the product was multi-labeled
                # during sync and the match is coincidental. Require the interest to be
                # at least 40% of the tag length to count as a real substring match.
                for tag in parsed_tags:
                    if interest_name in tag and len(interest_name) >= len(tag) * 0.4:
                        interest_score += 0.15
                        interest_reasons.append(f"tag_substr[{interest_name}]")
                        this_interest_matched = True
                        break

        if not this_interest_matched:
            # Fall back to keyword matching with word boundaries
            keywords = database._interest_to_keywords(interest_name)
            if keywords:
                # Use word-set matching instead of substring matching.
                # "jim" must be a whole word, not a substring of "jimmy".
                tag_kw_matches = sum(1 for kw in keywords if kw in tag_words)
                title_kw_matches = sum(1 for kw in keywords if kw in title_words)
                total_kw_matches = sum(1 for kw in keywords if kw in all_words)

                if total_kw_matches >= len(keywords) and tag_kw_matches >= len(keywords):
                    # All keywords found as whole words in tags — strong signal
                    interest_score += 0.15
                    interest_reasons.append(f"full_match[{interest_name}]")
                    this_interest_matched = True
                elif total_kw_matches >= len(keywords) and tag_kw_matches > 0:
                    # All keywords found overall, at least one in tags — moderate
                    interest_score += 0.10
                    interest_reasons.append(f"mixed_match[{interest_name}]")
                    this_interest_matched = True
                elif total_kw_matches >= len(keywords) and len(keywords) >= 2:
                    # All keywords in title/snippet but NONE in tags — weak
                    interest_score += 0.03
                    interest_reasons.append(f"title_only[{interest_name}]")
                elif total_kw_matches >= 2 and len(keywords) >= 3:
                    # Partial match: 2+ of 3+ keywords. Reduce score for 3+ kw interests
                    # since scattered keyword matches are more likely false positives.
                    partial = 0.04 * (total_kw_matches / len(keywords))
                    interest_score += partial
                    interest_reasons.append(f"partial[{interest_name}:{total_kw_matches}/{len(keywords)}]")
                    this_interest_matched = True
                elif total_kw_matches >= len(keywords) and len(keywords) == 1:
                    # Single keyword fully matched — moderate signal
                    interest_score += 0.08
                    interest_reasons.append(f"single_kw[{interest_name}]")
                    this_interest_matched = True

        if this_interest_matched:
            interests_matched += 1

    # Multi-interest bonus: product fitting 2+ profile interests is a strong signal
    if interests_matched >= 3:
        interest_score += 0.15
        interest_reasons.append("multi_interest(3+)")
    elif interests_matched == 2:
        interest_score += 0.08
        interest_reasons.append("multi_interest(2)")

    # Cap interest contribution at 0.50 to keep score in 0–1 range
    interest_score = min(interest_score, 0.50)
    score += interest_score
    reasons.extend(interest_reasons[:4])

    # Factor 3: Commission rate (10% weight — tiebreaker, not primary signal)
    # Reduced from 20% to prevent high-commission irrelevant products from
    # outscoring low-commission relevant ones.
    commission_rate = COMMISSION_RATES.get(retailer.lower(), 0.01)
    if intel:
        commission_rate = intel.get('commission_rate', commission_rate)

    score += commission_rate * 2  # 5% commission = +0.10 score
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
            elif price < low * 0.5:
                score -= 0.05
                reasons.append("price_too_low")
            elif price > high * 2:
                score -= 0.10
                reasons.append("price_too_high")
        except:
            pass

    # Factor 5: Relationship appropriateness (10% weight)
    if intel:
        best_relationships = intel.get('best_for_relationship') or []
        if isinstance(best_relationships, list) and relationship in best_relationships:
            score += 0.10
            reasons.append(f"good_for_{relationship}")

    # Clamp score to 0.0-1.0
    score = max(0.0, min(1.0, score))

    return score, reasons


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
        score, reasons = score_product_for_profile(product, profile, relationship)
        scored_products.append((score, reasons, product))

    scored_products.sort(reverse=True, key=lambda x: x[0])
    filtered = [product for score, reasons, product in scored_products[:target_count]]

    if scored_products:
        top_score = scored_products[0][0]
        cutoff_idx = min(len(scored_products) - 1, target_count - 1)
        bottom_score = scored_products[cutoff_idx][0]
        logger.info(f"Pre-filtered to {len(filtered)} products by relevance score (range {bottom_score:.2f}–{top_score:.2f})")

        # Log top 5 and bottom 5 so we can verify differentiation in production
        logger.info("Pre-filter TOP 5:")
        for score, reasons, product in scored_products[:5]:
            logger.info(f"  {score:.2f} | {(product.get('title') or '')[:50]} | {', '.join(reasons[:3])}")
        if len(scored_products) > 5:
            logger.info("Pre-filter BOTTOM 5:")
            for score, reasons, product in scored_products[-5:]:
                logger.info(f"  {score:.2f} | {(product.get('title') or '')[:50]} | {', '.join(reasons[:3])}")

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

        for interest in profile.get('interests') or []:
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
