"""
MULTI-RETAILER PRODUCT ORCHESTRATOR
Combines Etsy + Awin + eBay + ShareASale + Amazon

Strategy:
- Build a large inventory from every available vendor (request target_count from each
  and merge). We want hundreds of choices across many sellers so the curator has
  real options.
- Returns INVENTORY POOL ONLY. The caller must pass this list to the curator; the
  final recommendations come ONLY from curator output. Never use this return value
  as the final list—no bypass, no "if one vendor filled the pool use it as-is."
- Curator picks the best N from that pool—no forced vendor mix. If all 10 best fits
  are from Amazon (or one vendor), that's fine.
Order: Etsy → Awin → eBay → ShareASale → Amazon.
"""

import logging
from collections import defaultdict

logger = logging.getLogger(__name__)

# Max products in the merged inventory (so curator prompt stays manageable)
MAX_INVENTORY_SIZE = 100


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
    skimlinks_publisher_id=None,
    skimlinks_client_id=None,
    skimlinks_client_secret=None,
    skimlinks_domain_id=None,
    target_count=20,
    enhanced_search_terms=None,
    progress_callback=None,
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
        f"Available: Etsy={bool(etsy_key)}, Awin={bool(awin_data_feed_api_key)}, eBay={bool(ebay_client_id and ebay_client_secret)}, ShareASale={bool(shareasale_id)}, Skimlinks={bool(skimlinks_publisher_id)}, Amazon={bool(amazon_key)}"
    )

    all_products = []
    # Request target_count from each vendor and merge into one large pool (no per-vendor cap).
    # Curator will pick the best N; if they're all from one vendor, that's fine.
    per_vendor_target = min(target_count, MAX_INVENTORY_SIZE // 5)  # so 5 vendors don't exceed MAX

    def _notify(retailer, count=None, searching=False, done=False, skipped=False):
        if progress_callback:
            try:
                progress_callback(retailer=retailer, count=count, searching=searching, done=done, skipped=skipped)
            except Exception:
                pass

    # 1. Etsy
    if etsy_key:
        try:
            from etsy_searcher import search_products_etsy

            _notify('Etsy', searching=True)
            logger.info(f"Searching Etsy for {per_vendor_target} products...")
            etsy_products = search_products_etsy(
                profile, etsy_key, target_count=per_vendor_target
            )
            all_products.extend(etsy_products)
            logger.info(f"Got {len(etsy_products)} products from Etsy")
            _notify('Etsy', count=len(etsy_products), done=True)
        except ImportError as e:
            logger.warning(f"etsy_searcher not available: {e}")
            _notify('Etsy', skipped=True)
        except Exception as e:
            logger.error(f"Etsy search failed: {e}")
            _notify('Etsy', count=0, done=True)
    else:
        logger.info("Etsy API key not set - skipping Etsy")

    # 2. Awin
    if awin_data_feed_api_key:
        try:
            from awin_searcher import search_products_awin

            _notify('Awin', searching=True)
            logger.info(f"Searching Awin for {per_vendor_target} products...")
            awin_products = search_products_awin(
                profile,
                awin_data_feed_api_key,
                target_count=per_vendor_target,
                enhanced_search_terms=enhanced_search_terms,
            )
            all_products.extend(awin_products)
            logger.info(f"Got {len(awin_products)} products from Awin")
            _notify('Awin', count=len(awin_products), done=True)
        except ImportError as e:
            logger.warning(f"awin_searcher not available: {e}")
            _notify('Awin', skipped=True)
        except Exception as e:
            logger.error(f"Awin search failed: {e}")
            _notify('Awin', count=0, done=True)
    else:
        logger.info("Awin data feed API key not set - skipping Awin")

    # 3. eBay
    if ebay_client_id and ebay_client_secret:
        try:
            from ebay_searcher import search_products_ebay

            _notify('eBay', searching=True)
            logger.info(f"Searching eBay for {per_vendor_target} products...")
            ebay_products = search_products_ebay(
                profile,
                ebay_client_id,
                ebay_client_secret,
                target_count=per_vendor_target,
            )
            all_products.extend(ebay_products)
            logger.info(f"Got {len(ebay_products)} products from eBay")
            _notify('eBay', count=len(ebay_products), done=True)
        except ImportError as e:
            logger.warning(f"ebay_searcher not available: {e}")
            _notify('eBay', skipped=True)
        except Exception as e:
            logger.error(f"eBay search failed: {e}")
            _notify('eBay', count=0, done=True)
    else:
        logger.info("eBay credentials not set - skipping eBay")

    # 4. ShareASale
    if all([shareasale_id, shareasale_token, shareasale_secret]):
        try:
            from affiliate_searcher import search_products_shareasale

            _notify('ShareASale', searching=True)
            logger.info(f"Searching ShareASale for {per_vendor_target} products...")
            shareasale_products = search_products_shareasale(
                profile,
                shareasale_id,
                shareasale_token,
                shareasale_secret,
                target_count=per_vendor_target,
            )
            all_products.extend(shareasale_products)
            logger.info(f"Got {len(shareasale_products)} products from ShareASale")
            _notify('ShareASale', count=len(shareasale_products), done=True)
        except ImportError as e:
            logger.warning(f"affiliate_searcher not available: {e}")
            _notify('ShareASale', skipped=True)
        except Exception as e:
            logger.error(f"ShareASale search failed: {e}")
            _notify('ShareASale', count=0, done=True)
    else:
        logger.info("ShareASale credentials not set - skipping ShareASale")

    # 5. Skimlinks (aggregated: 48,500+ merchants across 50+ affiliate networks)
    if skimlinks_publisher_id:
        try:
            from skimlinks_searcher import search_products_skimlinks

            _notify('Skimlinks', searching=True)
            logger.info(f"Searching Skimlinks for {per_vendor_target} products...")
            skimlinks_products = search_products_skimlinks(
                profile,
                skimlinks_publisher_id,
                skimlinks_client_id,
                skimlinks_client_secret,
                skimlinks_domain_id,
                target_count=per_vendor_target,
                enhanced_search_terms=enhanced_search_terms,
            )
            all_products.extend(skimlinks_products)
            logger.info(f"Got {len(skimlinks_products)} products from Skimlinks")
            _notify('Skimlinks', count=len(skimlinks_products), done=True)
        except ImportError as e:
            logger.warning(f"skimlinks_searcher not available: {e}")
            _notify('Skimlinks', skipped=True)
        except Exception as e:
            logger.error(f"Skimlinks search failed: {e}")
            _notify('Skimlinks', count=0, done=True)
    else:
        logger.info("Skimlinks credentials not set - skipping Skimlinks")

    # 6. Amazon
    if amazon_key:
        try:
            from rapidapi_amazon_searcher import search_products_rapidapi_amazon

            _notify('Amazon', searching=True)
            logger.info(f"Searching Amazon for {per_vendor_target} products...")
            amazon_products = search_products_rapidapi_amazon(
                profile, amazon_key, target_count=per_vendor_target
            )
            all_products.extend(amazon_products)
            logger.info(f"Got {len(amazon_products)} products from Amazon")
            _notify('Amazon', count=len(amazon_products), done=True)
        except ImportError:
            logger.warning("rapidapi_amazon_searcher not found - Amazon skipped")
            _notify('Amazon', skipped=True)
        except Exception as e:
            logger.error(f"Amazon search failed: {e}")
            _notify('Amazon', count=0, done=True)
    else:
        logger.info("Amazon key not set - skipping Amazon")

    # Interleave products by source so no single vendor dominates early positions
    if len(all_products) > 1:
        by_source = defaultdict(list)
        for p in all_products:
            by_source[p.get("source_domain", "unknown")].append(p)
        interleaved = []
        source_lists = list(by_source.values())
        max_len = max(len(lst) for lst in source_lists) if source_lists else 0
        for i in range(max_len):
            for lst in source_lists:
                if i < len(lst):
                    interleaved.append(lst[i])
        all_products = interleaved

    # Cap total inventory size so curator prompt stays manageable
    if len(all_products) > MAX_INVENTORY_SIZE:
        all_products = all_products[:MAX_INVENTORY_SIZE]
        logger.info(f"Inventory capped at {MAX_INVENTORY_SIZE} for curation")

    source_counts = defaultdict(int)
    for p in all_products:
        source_counts[p.get("source_domain", "unknown")] += 1

    logger.info(f"Product source breakdown: {dict(source_counts)}")
    logger.info(f"Total products in pool: {len(all_products)}")

    return all_products
