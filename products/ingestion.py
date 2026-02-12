"""
PRODUCT INGESTION & REFRESH
Daily refresh logic for populating product database

This module orchestrates product collection from all active retailer APIs.
Designed to run automatically via cron/GitHub Actions at 2am UTC daily.

Author: Chad + Claude
Date: February 2026
"""

import os
import sys
import logging
from typing import List, Dict, Optional
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
import database
from models import Product

# Retailer searcher modules
try:
    import rapidapi_amazon_searcher
except ImportError:
    rapidapi_amazon_searcher = None

try:
    import ebay_searcher
except ImportError:
    ebay_searcher = None

try:
    import etsy_searcher
except ImportError:
    etsy_searcher = None

try:
    import awin_searcher
except ImportError:
    awin_searcher = None

try:
    import skimlinks_searcher
except ImportError:
    skimlinks_searcher = None

try:
    import cj_searcher
except ImportError:
    cj_searcher = None

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format=config.LOG_FORMAT
)
logger = logging.getLogger(__name__)


# =============================================================================
# CORE INTEREST CATEGORIES FOR BROAD PRODUCT DISCOVERY
# =============================================================================

CORE_INTERESTS = [
    # Lifestyle & hobbies
    'yoga', 'fitness', 'running', 'cycling', 'hiking', 'camping',
    'cooking', 'baking', 'coffee', 'tea', 'wine',
    'gardening', 'plants', 'home decor', 'candles',
    'reading', 'books', 'writing', 'journaling',
    'photography', 'art', 'painting', 'crafts',

    # Fashion & beauty
    'jewelry', 'accessories', 'bags', 'shoes',
    'skincare', 'makeup', 'beauty', 'haircare',
    'fashion', 'clothing', 'athleisure',

    # Tech & gaming
    'tech gadgets', 'electronics', 'gaming', 'headphones',
    'smart home', 'phone accessories',

    # Music & entertainment
    'music', 'vinyl records', 'speakers', 'instruments',
    'movies', 'streaming', 'podcasts',

    # Travel & outdoors
    'travel', 'luggage', 'beach', 'outdoor gear',
    'backpacking', 'adventure',

    # Pets
    'dog', 'cat', 'pet accessories', 'pet toys',

    # Wellness
    'self-care', 'meditation', 'aromatherapy', 'spa',
    'wellness', 'mindfulness',

    # Food & drink
    'snacks', 'gourmet food', 'chocolate', 'candy',
    'cocktails', 'beer', 'spirits',

    # Home & living
    'kitchen', 'cookware', 'organization', 'storage',
    'bedding', 'blankets', 'pillows',
]


# =============================================================================
# PER-RETAILER REFRESH FUNCTIONS
# =============================================================================

def refresh_amazon(interests: List[str], max_products: int = 500) -> int:
    """
    Refresh Amazon products via RapidAPI

    Args:
        interests: List of interest keywords to search
        max_products: Maximum products to fetch

    Returns:
        Number of products upserted
    """
    if not rapidapi_amazon_searcher or not config.RAPIDAPI_KEY:
        logger.warning("Amazon searcher not available - skipping")
        return 0

    logger.info("Starting Amazon refresh...")
    products_added = 0

    # Create dummy profile for searcher
    dummy_profile = {
        'interests': [{'name': interest} for interest in interests],
        'price_signals': {'preferred_range': {'min': config.DEFAULT_MIN_PRICE, 'max': config.DEFAULT_MAX_PRICE}}
    }

    try:
        # Search Amazon for each interest
        for interest in interests[:20]:  # Limit to 20 to avoid rate limits
            if products_added >= max_products:
                break

            logger.info(f"  Searching Amazon for '{interest}'...")

            # Use existing searcher module
            results = rapidapi_amazon_searcher.search_products_amazon(
                dummy_profile,
                config.RAPIDAPI_KEY,
                target_count=25,
                enhanced_search_terms=[interest]
            )

            # Convert and upsert products
            for result in results:
                try:
                    product = Product.from_searcher_dict(result, retailer='amazon')
                    database.upsert_product(product.to_db_format())
                    products_added += 1
                except Exception as e:
                    logger.error(f"Failed to upsert Amazon product: {e}")

        logger.info(f"Amazon refresh complete: {products_added} products")
        return products_added

    except Exception as e:
        logger.error(f"Amazon refresh failed: {e}")
        return products_added


def refresh_ebay(interests: List[str], max_products: int = 500) -> int:
    """
    Refresh eBay products via Browse API

    Args:
        interests: List of interest keywords to search
        max_products: Maximum products to fetch

    Returns:
        Number of products upserted
    """
    if not ebay_searcher or not config.EBAY_APP_ID:
        logger.warning("eBay searcher not available - skipping")
        return 0

    logger.info("Starting eBay refresh...")
    products_added = 0

    dummy_profile = {
        'interests': [{'name': interest} for interest in interests],
        'price_signals': {'preferred_range': {'min': config.DEFAULT_MIN_PRICE, 'max': config.DEFAULT_MAX_PRICE}}
    }

    try:
        for interest in interests[:20]:
            if products_added >= max_products:
                break

            logger.info(f"  Searching eBay for '{interest}'...")

            results = ebay_searcher.search_products_ebay(
                dummy_profile,
                config.EBAY_APP_ID,
                target_count=25,
                enhanced_search_terms=[interest]
            )

            for result in results:
                try:
                    product = Product.from_searcher_dict(result, retailer='ebay')
                    database.upsert_product(product.to_db_format())
                    products_added += 1
                except Exception as e:
                    logger.error(f"Failed to upsert eBay product: {e}")

        logger.info(f"eBay refresh complete: {products_added} products")
        return products_added

    except Exception as e:
        logger.error(f"eBay refresh failed: {e}")
        return products_added


def refresh_etsy(interests: List[str], max_products: int = 500) -> int:
    """
    Refresh Etsy products via v3 API

    Args:
        interests: List of interest keywords to search
        max_products: Maximum products to fetch

    Returns:
        Number of products upserted
    """
    if not etsy_searcher or not config.ETSY_API_KEY:
        logger.warning("Etsy searcher not available - awaiting API credentials")
        return 0

    logger.info("Starting Etsy refresh...")
    products_added = 0

    dummy_profile = {
        'interests': [{'name': interest} for interest in interests],
        'price_signals': {'preferred_range': {'min': config.DEFAULT_MIN_PRICE, 'max': config.DEFAULT_MAX_PRICE}}
    }

    try:
        for interest in interests[:20]:
            if products_added >= max_products:
                break

            logger.info(f"  Searching Etsy for '{interest}'...")

            results = etsy_searcher.search_products_etsy(
                dummy_profile,
                config.ETSY_API_KEY,
                target_count=25,
                enhanced_search_terms=[interest]
            )

            for result in results:
                try:
                    product = Product.from_searcher_dict(result, retailer='etsy')
                    database.upsert_product(product.to_db_format())
                    products_added += 1
                except Exception as e:
                    logger.error(f"Failed to upsert Etsy product: {e}")

        logger.info(f"Etsy refresh complete: {products_added} products")
        return products_added

    except Exception as e:
        logger.error(f"Etsy refresh failed: {e}")
        return products_added


def refresh_awin(interests: List[str], max_products: int = 500) -> int:
    """
    Refresh Awin products via Data Feed API

    Args:
        interests: List of interest keywords to search
        max_products: Maximum products to fetch

    Returns:
        Number of products upserted
    """
    if not awin_searcher or not config.AWIN_API_TOKEN or not config.AWIN_PUBLISHER_ID:
        logger.warning("Awin searcher not available - awaiting joined advertisers")
        return 0

    logger.info("Starting Awin refresh...")
    products_added = 0

    dummy_profile = {
        'interests': [{'name': interest} for interest in interests],
        'price_signals': {'preferred_range': {'min': config.DEFAULT_MIN_PRICE, 'max': config.DEFAULT_MAX_PRICE}}
    }

    try:
        for interest in interests[:15]:  # Lower limit due to Awin rate limits
            if products_added >= max_products:
                break

            logger.info(f"  Searching Awin for '{interest}'...")

            results = awin_searcher.search_products_awin(
                dummy_profile,
                config.AWIN_API_TOKEN,
                config.AWIN_PUBLISHER_ID,
                target_count=20,
                enhanced_search_terms=[interest]
            )

            for result in results:
                try:
                    product = Product.from_searcher_dict(result, retailer='awin')
                    database.upsert_product(product.to_db_format())
                    products_added += 1
                except Exception as e:
                    logger.error(f"Failed to upsert Awin product: {e}")

        logger.info(f"Awin refresh complete: {products_added} products")
        return products_added

    except Exception as e:
        logger.error(f"Awin refresh failed: {e}")
        return products_added


def refresh_skimlinks(interests: List[str], max_products: int = 500) -> int:
    """
    Refresh Skimlinks products via Product Key API v2

    Args:
        interests: List of interest keywords to search
        max_products: Maximum products to fetch

    Returns:
        Number of products upserted
    """
    if not skimlinks_searcher or not config.SKIMLINKS_PUBLISHER_ID:
        logger.warning("Skimlinks searcher not available - awaiting approval")
        return 0

    logger.info("Starting Skimlinks refresh...")
    products_added = 0

    dummy_profile = {
        'interests': [{'name': interest} for interest in interests],
        'price_signals': {'preferred_range': {'min': config.DEFAULT_MIN_PRICE, 'max': config.DEFAULT_MAX_PRICE}}
    }

    try:
        for interest in interests[:20]:
            if products_added >= max_products:
                break

            logger.info(f"  Searching Skimlinks for '{interest}'...")

            results = skimlinks_searcher.search_products_skimlinks(
                dummy_profile,
                config.SKIMLINKS_PUBLISHER_ID,
                config.SKIMLINKS_CLIENT_ID,
                config.SKIMLINKS_CLIENT_SECRET,
                config.SKIMLINKS_PUBLISHER_DOMAIN_ID,
                target_count=25,
                enhanced_search_terms=[interest]
            )

            for result in results:
                try:
                    product = Product.from_searcher_dict(result, retailer='skimlinks')
                    database.upsert_product(product.to_db_format())
                    products_added += 1
                except Exception as e:
                    logger.error(f"Failed to upsert Skimlinks product: {e}")

        logger.info(f"Skimlinks refresh complete: {products_added} products")
        return products_added

    except Exception as e:
        logger.error(f"Skimlinks refresh failed: {e}")
        return products_added


def refresh_cj(interests: List[str], max_products: int = 500) -> int:
    """
    Refresh CJ Affiliate products via Product Catalog API

    Args:
        interests: List of interest keywords to search
        max_products: Maximum products to fetch

    Returns:
        Number of products upserted
    """
    if not cj_searcher or not config.CJ_API_KEY:
        logger.warning("CJ searcher not available - awaiting developer portal access")
        return 0

    logger.info("Starting CJ refresh...")
    products_added = 0

    dummy_profile = {
        'interests': [{'name': interest} for interest in interests],
        'price_signals': {'preferred_range': {'min': config.DEFAULT_MIN_PRICE, 'max': config.DEFAULT_MAX_PRICE}}
    }

    try:
        for interest in interests[:15]:  # Conservative limit
            if products_added >= max_products:
                break

            logger.info(f"  Searching CJ for '{interest}'...")

            results = cj_searcher.search_products_cj(
                dummy_profile,
                config.CJ_API_KEY,
                config.CJ_ACCOUNT_ID,
                config.CJ_WEBSITE_ID,
                target_count=20,
                enhanced_search_terms=[interest]
            )

            for result in results:
                try:
                    product = Product.from_searcher_dict(result, retailer='cj')
                    database.upsert_product(product.to_db_format())
                    products_added += 1
                except Exception as e:
                    logger.error(f"Failed to upsert CJ product: {e}")

        logger.info(f"CJ refresh complete: {products_added} products")
        return products_added

    except Exception as e:
        logger.error(f"CJ refresh failed: {e}")
        return products_added


# =============================================================================
# ORCHESTRATION
# =============================================================================

def refresh_retailer(retailer: str, interests: Optional[List[str]] = None, max_products: int = 500) -> int:
    """
    Refresh products from a specific retailer

    Args:
        retailer: 'amazon', 'ebay', 'etsy', 'awin', 'skimlinks', 'cj'
        interests: List of interests to search (uses CORE_INTERESTS if None)
        max_products: Maximum products to fetch

    Returns:
        Number of products upserted
    """
    if interests is None:
        interests = CORE_INTERESTS

    refresh_functions = {
        'amazon': refresh_amazon,
        'ebay': refresh_ebay,
        'etsy': refresh_etsy,
        'awin': refresh_awin,
        'skimlinks': refresh_skimlinks,
        'cj': refresh_cj,
    }

    refresh_fn = refresh_functions.get(retailer.lower())
    if not refresh_fn:
        logger.error(f"Unknown retailer: {retailer}")
        return 0

    return refresh_fn(interests, max_products)


def refresh_all_products(interests: Optional[List[str]] = None) -> Dict[str, int]:
    """
    Refresh products from all active retailers

    This is the main entry point for automated daily refresh.
    Designed to be called by cron job or GitHub Actions.

    Args:
        interests: List of interests to search (uses CORE_INTERESTS if None)

    Returns:
        Dict mapping retailer name to number of products added
    """
    if interests is None:
        interests = CORE_INTERESTS

    logger.info("="*60)
    logger.info("STARTING PRODUCT DATABASE REFRESH")
    logger.info(f"Time: {datetime.now().isoformat()}")
    logger.info(f"Interests: {len(interests)} categories")
    logger.info(f"Max per retailer: {config.REFRESH_CONFIG['max_products_per_retailer']}")
    logger.info("="*60)

    # Refresh each retailer
    max_per_retailer = config.REFRESH_CONFIG['max_products_per_retailer']

    results = {
        'amazon': refresh_retailer('amazon', interests, max_per_retailer),
        'ebay': refresh_retailer('ebay', interests, max_per_retailer),
        'etsy': refresh_retailer('etsy', interests, max_per_retailer),
        'awin': refresh_retailer('awin', interests, max_per_retailer),
        'skimlinks': refresh_retailer('skimlinks', interests, max_per_retailer),
        'cj': refresh_retailer('cj', interests, max_per_retailer),
    }

    # Mark stale products
    stale_count = database.mark_stale_products(
        days=config.REFRESH_CONFIG['stale_threshold_days']
    )

    # Clean expired profile caches
    expired_profiles = database.clean_expired_profiles()

    # Update metadata
    database.set_metadata('last_refresh', datetime.now().isoformat())
    database.set_metadata('last_refresh_results', str(results))

    # Summary
    total_added = sum(results.values())
    logger.info("="*60)
    logger.info("REFRESH COMPLETE")
    logger.info(f"Total products added/updated: {total_added}")
    logger.info(f"  Amazon: {results['amazon']}")
    logger.info(f"  eBay: {results['ebay']}")
    logger.info(f"  Etsy: {results['etsy']}")
    logger.info(f"  Awin: {results['awin']}")
    logger.info(f"  Skimlinks: {results['skimlinks']}")
    logger.info(f"  CJ: {results['cj']}")
    logger.info(f"Stale products marked: {stale_count}")
    logger.info(f"Expired profiles cleaned: {expired_profiles}")
    logger.info("="*60)

    return results


# =============================================================================
# COMMAND LINE INTERFACE
# =============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Refresh product database from retailers')
    parser.add_argument(
        '--retailer',
        type=str,
        choices=['amazon', 'ebay', 'etsy', 'awin', 'skimlinks', 'cj', 'all'],
        default='all',
        help='Which retailer to refresh (default: all)'
    )
    parser.add_argument(
        '--max-products',
        type=int,
        default=500,
        help='Maximum products per retailer (default: 500)'
    )

    args = parser.parse_args()

    if args.retailer == 'all':
        refresh_all_products()
    else:
        count = refresh_retailer(args.retailer, max_products=args.max_products)
        print(f"{args.retailer}: {count} products added/updated")
