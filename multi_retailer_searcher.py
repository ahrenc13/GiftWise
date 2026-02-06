"""
MULTI-RETAILER PRODUCT ORCHESTRATOR
Combines Etsy + Awin + eBay + ShareASale + Amazon fallback

Priority order:
1. Etsy (handmade/personalized)
2. Awin (product feeds; use AWIN_DATA_FEED_API_KEY)
3. eBay (Browse API; use EBAY_CLIENT_ID + EBAY_CLIENT_SECRET)
4. ShareASale (legacy brand products)
5. Amazon (fallback if others fail)

Returns diverse product mix from multiple sources.
Graceful degradation: works with any combination of available APIs.
"""

import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


def search_products_multi_retailer(
    profile,
    etsy_key=None,
    awin_data_feed_api_key=None,
    ebay_client_id=None,
    ebay_client_secret=None,
    shareasale_id=None,
    shareasale_token=None,
    shareasale_secret=None,
    amazon_key=None,
    target_count=20,
    enhanced_search_terms=None,
):
    """
    Search across multiple retailers.

    Strategy:
    - Try Etsy first (best for personalized gifts)
    - Add Awin products (feed-based)
    - Add eBay products (Browse API)
    - Add ShareASale products (brand names, legacy)
    - Use Amazon as fallback if needed

    Returns mixed list of products from all sources.
    If an API key is missing, that source is skipped (no crash).
    """
    logger.info(f"Multi-retailer search: target {target_count} products")
    logger.info(
        f"Available: Etsy={bool(etsy_key)}, Awin={bool(awin_data_feed_api_key)}, eBay={bool(ebay_client_id and ebay_client_secret)}, ShareASale={bool(shareasale_id)}, Amazon={bool(amazon_key)}"
    )

    all_products = []

    # 1. Etsy (aim for ~60% of target)
    etsy_target = max(int(target_count * 0.6), 5)
    if etsy_key:
        try:
            from etsy_searcher import search_products_etsy

            logger.info(f"Searching Etsy for {etsy_target} products...")
            etsy_products = search_products_etsy(
                profile, etsy_key, target_count=etsy_target
            )
            all_products.extend(etsy_products)
            logger.info(f"Got {len(etsy_products)} products from Etsy")
        except ImportError as e:
            logger.warning(f"etsy_searcher not available: {e}")
        except Exception as e:
            logger.error(f"Etsy search failed: {e}")
    else:
        logger.info("Etsy API key not set - skipping Etsy")

    # 2. Awin (product feeds)
    remaining = target_count - len(all_products)
    if remaining > 0 and awin_data_feed_api_key:
        try:
            from awin_searcher import search_products_awin

            logger.info(f"Searching Awin for {remaining} products...")
            awin_products = search_products_awin(
                profile,
                awin_data_feed_api_key,
                target_count=remaining,
                enhanced_search_terms=enhanced_search_terms,
            )
            all_products.extend(awin_products)
            logger.info(f"Got {len(awin_products)} products from Awin")
        except ImportError as e:
            logger.warning(f"awin_searcher not available: {e}")
        except Exception as e:
            logger.error(f"Awin search failed: {e}")
    elif remaining > 0:
        logger.info("Awin data feed API key not set - skipping Awin")

    # 3. ShareASale (fill remaining)
    remaining = target_count - len(all_products)
    if remaining > 0 and all([shareasale_id, shareasale_token, shareasale_secret]):
        try:
            from affiliate_searcher import search_products_shareasale

            logger.info(f"Searching ShareASale for {remaining} products...")
            shareasale_products = search_products_shareasale(
                profile,
                shareasale_id,
                shareasale_token,
                shareasale_secret,
                target_count=remaining,
            )
            all_products.extend(shareasale_products)
            logger.info(f"Got {len(shareasale_products)} products from ShareASale")
        except ImportError as e:
            logger.warning(f"affiliate_searcher not available: {e}")
        except Exception as e:
            logger.error(f"ShareASale search failed: {e}")
    elif remaining > 0:
        logger.info("ShareASale credentials not set - skipping ShareASale")

    # 5. Amazon fill-in only when meaningfully short (deprioritized vs Etsy/Awin/eBay/ShareASale)
    remaining = target_count - len(all_products)
    amazon_min_remaining = min(5, max(1, target_count // 2))  # only fetch Amazon if we need at least this many
    if remaining >= amazon_min_remaining and amazon_key:
        try:
            from rapidapi_amazon_searcher import search_products_rapidapi_amazon

            logger.info(f"Using Amazon fill-in for {remaining} products (other sources short)...")
            amazon_products = search_products_rapidapi_amazon(
                profile, amazon_key, target_count=remaining
            )
            all_products.extend(amazon_products)
            logger.info(f"Got {len(amazon_products)} products from Amazon")
        except ImportError:
            logger.warning("rapidapi_amazon_searcher not found - Amazon fill-in skipped")
        except Exception as e:
            logger.error(f"Amazon fill-in failed: {e}")
    elif remaining > 0 and amazon_key:
        logger.info("Amazon fill-in skipped - enough from other sources (remaining=%s < threshold %s)", remaining, amazon_min_remaining)
    elif remaining > 0:
        logger.info("Amazon key not set - skipping Amazon fill-in")

    # Log source breakdown
    source_counts = defaultdict(int)
    for p in all_products:
        source_counts[p.get("source_domain", "unknown")] += 1

    logger.info(f"Product source breakdown: {dict(source_counts)}")
    logger.info(f"Total products found: {len(all_products)}")

    return all_products
