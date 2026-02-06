"""
RAPIDAPI AMAZON PRODUCT SEARCHER (STUB)
Fallback when Etsy/ShareASale are not enough.

Replace this stub with a real RapidAPI Amazon implementation when you have:
- RAPIDAPI_KEY set in Railway
- Real-time Amazon Data API or similar from RapidAPI

Until then, returns empty list so multi_retailer_searcher continues without crashing.
"""

import logging

logger = logging.getLogger(__name__)


def search_products_rapidapi_amazon(profile, api_key, target_count=20):
    """
    Search Amazon via RapidAPI (stub).

    Returns empty list until you implement or plug in a real RapidAPI Amazon searcher.
    """
    if not api_key:
        logger.warning("RapidAPI key not configured - skipping Amazon search")
        return []

    logger.warning(
        "rapidapi_amazon_searcher is a stub - returning no products. "
        "Add a real RapidAPI Amazon implementation for Phase 1 Amazon-only."
    )
    return []
