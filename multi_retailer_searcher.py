"""
MULTI-RETAILER PRODUCT ORCHESTRATOR
Combines Etsy + Awin + eBay + ShareASale + Amazon + Skimlinks + CJ

Strategy:
- Build a large inventory from every available vendor (request target_count from each
  and merge). We want hundreds of choices across many sellers so the curator has
  real options.
- Returns INVENTORY POOL ONLY. The caller must pass this list to the curator; the
  final recommendations come ONLY from curator output. Never use this return value
  as the final list—no bypass, no "if one vendor filled the pool use it as-is."
- Curator picks the best N from that pool—no forced vendor mix. If all 10 best fits
  are from Amazon (or one vendor), that's fine.
- Retailer searches run in PARALLEL via ThreadPoolExecutor. Total search time equals
  the slowest single retailer, not their sum. Each retailer failure is isolated.
"""

import concurrent.futures
import logging
import threading
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
    cj_api_key=None,
    cj_company_id=None,
    cj_publisher_id=None,
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
    - Add Skimlinks products (48,500+ merchants)
    - Add CJ Affiliate products (approved advertisers only)
    - Use Amazon as fallback if needed

    Returns mixed list of products from all sources.
    If an API key is missing, that source is skipped (no crash).
    """
    logger.info(f"Multi-retailer search: target {target_count} products")
    logger.info(
        f"Available: Etsy={bool(etsy_key)}, Awin={bool(awin_data_feed_api_key)}, eBay={bool(ebay_client_id and ebay_client_secret)}, ShareASale={bool(shareasale_id)}, Skimlinks={bool(skimlinks_publisher_id)}, CJ={bool(cj_api_key)}, Amazon={bool(amazon_key)}"
    )

    all_products = []

    # Per-vendor target: used both for DB source capping and live API calls.
    per_vendor_target = min(target_count, MAX_INVENTORY_SIZE // 5)  # so 5 vendors don't exceed MAX

    # 0. Query database FIRST (added Feb 2026 for cost reduction)
    try:
        import config
        import database
        from models import Product

        if config.FEATURES.get('database_first', True):
            logger.info("Querying product database for cached products...")

            # Extract interests from profile, filtering out low-confidence ones.
            # The profile analyzer assigns confidence (high/medium/low) to each interest.
            # Low-confidence interests are often someone else's hobby (e.g. "fly fishing"
            # from a post about the user's brother). Code-level enforcement here prevents
            # low-confidence interests from polluting the product search even if the LLM
            # didn't fully follow the "skip low confidence" prompt instruction.
            interests = []
            if isinstance(profile.get('interests'), list):
                for i in profile.get('interests', []):
                    if isinstance(i, dict):
                        confidence = i.get('confidence', 'high')
                        if confidence == 'low':
                            logger.info(f"Skipping low-confidence interest: {i.get('name', '?')}")
                            continue
                        interests.append(i.get('name', ''))
                    else:
                        interests.append(str(i))
                interests = [n for n in interests if n]  # remove empty strings

            if interests:
                # Query database for products matching interests
                db_products = database.search_products_by_interests(interests, limit=target_count * 2)

                if db_products:
                    # Convert database rows to product dicts
                    for row in db_products:
                        try:
                            product = Product.from_db_row(row)
                            all_products.append(product.to_curator_format())
                        except Exception as e:
                            logger.error(f"Error converting database product: {e}")

                    logger.info(f"Got {len(all_products)} products from database cache")

                    # Only skip live APIs if we have enough products AND source diversity.
                    # Without this check, once eBay floods the cache, Awin/CJ feeds are
                    # never queried again — starving the advertisers we've been accumulating.
                    MIN_SOURCES_TO_SKIP_LIVE = 3
                    MAX_SINGLE_SOURCE_PCT = 0.40  # No source > 40% of cached results (was 50%)

                    # Always cap per-source products first. This prevents a single CJ
                    # marketplace advertiser (e.g. TikTok Shop at 44%) from dominating.
                    # Cap = 30% of target or per_vendor_target, whichever is smaller.
                    max_per_source = min(per_vendor_target, int(target_count * 0.30))
                    source_counts_pre = defaultdict(int)
                    capped_products = []
                    for p in all_products:
                        src = p.get("source_domain", "unknown")
                        if source_counts_pre[src] < max_per_source:
                            capped_products.append(p)
                            source_counts_pre[src] += 1
                    if len(capped_products) < len(all_products):
                        logger.info(
                            f"Per-source cap ({max_per_source}): trimmed {len(all_products) - len(capped_products)} "
                            f"excess products from overrepresented sources"
                        )
                    all_products = capped_products

                    if len(all_products) >= target_count:
                        db_source_counts = defaultdict(int)
                        for p in all_products:
                            db_source_counts[p.get("source_domain", "unknown")] += 1
                        num_sources = len(db_source_counts)
                        top_source_pct = max(db_source_counts.values()) / len(all_products) if all_products else 1.0
                        top_source_name = max(db_source_counts, key=db_source_counts.get) if db_source_counts else "unknown"

                        if num_sources >= MIN_SOURCES_TO_SKIP_LIVE and top_source_pct <= MAX_SINGLE_SOURCE_PCT:
                            logger.info(
                                f"Database provided enough diverse products ({len(all_products)} >= {target_count}, "
                                f"{num_sources} sources, top source '{top_source_name}' at {top_source_pct:.0%}), "
                                f"skipping live API calls"
                            )
                            return all_products[:MAX_INVENTORY_SIZE]
                        else:
                            logger.info(
                                f"Database has {len(all_products)} products but insufficient diversity "
                                f"({num_sources} sources, top source '{top_source_name}' at {top_source_pct:.0%}). "
                                f"Proceeding with live API calls to diversify."
                            )
                else:
                    logger.info("No products found in database for these interests")
            else:
                logger.warning("No interests in profile, skipping database query")
    except ImportError:
        logger.info("Database module not available, proceeding with live APIs only")
    except Exception as e:
        logger.error(f"Database query failed: {e}, proceeding with live APIs")

    # Request target_count from each vendor and merge into one large pool (no per-vendor cap).
    # Curator will pick the best N; if they're all from one vendor, that's fine.

    # _notify is called from worker threads — keep it lightweight and exception-safe.
    def _notify(retailer, count=None, searching=False, done=False, skipped=False):
        if progress_callback:
            try:
                progress_callback(retailer=retailer, count=count, searching=searching, done=done, skipped=skipped)
            except Exception:
                pass

    # Build the list of (name, callable) pairs for each enabled retailer.
    # Each callable captures its credentials via closure and returns a product list.
    # Failures are isolated — one retailer timing out doesn't block the others.
    retailer_tasks = []

    if etsy_key:
        def _run_etsy():
            from etsy_searcher import search_products_etsy
            _notify('Etsy', searching=True)
            products = search_products_etsy(profile, etsy_key, target_count=per_vendor_target)
            _notify('Etsy', count=len(products), done=True)
            return 'Etsy', products
        retailer_tasks.append(_run_etsy)
    else:
        logger.info("Etsy API key not set - skipping Etsy")

    if awin_data_feed_api_key:
        def _run_awin():
            from awin_searcher import search_products_awin
            _notify('Awin', searching=True)
            products = search_products_awin(
                profile, awin_data_feed_api_key,
                target_count=per_vendor_target,
                enhanced_search_terms=enhanced_search_terms,
            )
            _notify('Awin', count=len(products), done=True)
            return 'Awin', products
        retailer_tasks.append(_run_awin)
    else:
        logger.info("Awin data feed API key not set - skipping Awin")

    if ebay_client_id and ebay_client_secret:
        def _run_ebay():
            from ebay_searcher import search_products_ebay
            _notify('eBay', searching=True)
            products = search_products_ebay(
                profile, ebay_client_id, ebay_client_secret,
                target_count=per_vendor_target,
            )
            _notify('eBay', count=len(products), done=True)
            return 'eBay', products
        retailer_tasks.append(_run_ebay)
    else:
        logger.info("eBay credentials not set - skipping eBay")

    if all([shareasale_id, shareasale_token, shareasale_secret]):
        def _run_shareasale():
            from affiliate_searcher import search_products_shareasale
            _notify('ShareASale', searching=True)
            products = search_products_shareasale(
                profile, shareasale_id, shareasale_token, shareasale_secret,
                target_count=per_vendor_target,
            )
            _notify('ShareASale', count=len(products), done=True)
            return 'ShareASale', products
        retailer_tasks.append(_run_shareasale)
    else:
        logger.info("ShareASale credentials not set - skipping ShareASale")

    if skimlinks_publisher_id:
        def _run_skimlinks():
            from skimlinks_searcher import search_products_skimlinks
            _notify('Skimlinks', searching=True)
            products = search_products_skimlinks(
                profile, skimlinks_publisher_id,
                skimlinks_client_id, skimlinks_client_secret, skimlinks_domain_id,
                target_count=per_vendor_target,
                enhanced_search_terms=enhanced_search_terms,
            )
            _notify('Skimlinks', count=len(products), done=True)
            return 'Skimlinks', products
        retailer_tasks.append(_run_skimlinks)
    else:
        logger.info("Skimlinks credentials not set - skipping Skimlinks")

    if cj_api_key:
        def _run_cj():
            from cj_searcher import search_products_cj
            _notify('CJ Affiliate', searching=True)
            products = search_products_cj(
                profile, cj_api_key,
                company_id=cj_company_id,
                publisher_id=cj_publisher_id,
                target_count=per_vendor_target,
                enhanced_search_terms=enhanced_search_terms,
                joined_only=False,
            )
            _notify('CJ Affiliate', count=len(products), done=True)
            return 'CJ Affiliate', products
        retailer_tasks.append(_run_cj)
    else:
        logger.info("CJ Affiliate credentials not set - skipping CJ")

    if amazon_key:
        def _run_amazon():
            from rapidapi_amazon_searcher import search_products_rapidapi_amazon
            _notify('Amazon', searching=True)
            products = search_products_rapidapi_amazon(profile, amazon_key, target_count=per_vendor_target)
            _notify('Amazon', count=len(products), done=True)
            return 'Amazon', products
        retailer_tasks.append(_run_amazon)
    else:
        logger.info("Amazon key not set - skipping Amazon")

    # Run all retailer searches in parallel. Total wall-clock time = slowest single
    # retailer rather than the sum of all retailers. Each is independently isolated:
    # a timeout or exception in one does not affect the others.
    #
    # IMPORTANT: Do NOT use `with ThreadPoolExecutor(...)` here. Python's context
    # manager calls shutdown(wait=True) on __exit__, which blocks until ALL threads
    # finish — even after as_completed(timeout=90) fires. Awin downloads up to 12
    # product-feed CSVs sequentially, each with a 90s HTTP timeout, so one slow Awin
    # run can block here for 10+ minutes despite the 90s timeout. We call
    # shutdown(wait=False) ourselves so hung threads are abandoned immediately.
    if retailer_tasks:
        logger.info(f"Launching {len(retailer_tasks)} retailer searches in parallel")
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=len(retailer_tasks))
        futures = {executor.submit(task): task.__name__ for task in retailer_tasks}
        try:
            for future in concurrent.futures.as_completed(futures, timeout=90):
                task_name = futures[future]
                try:
                    retailer_name, products = future.result()
                    all_products.extend(products)
                    logger.info(f"Got {len(products)} products from {retailer_name}")
                except ImportError as e:
                    logger.warning(f"{task_name} module not available: {e}")
                except Exception as e:
                    logger.error(f"{task_name} failed: {e}")
        except concurrent.futures.TimeoutError:
            pending = [name for f, name in futures.items() if not f.done()]
            logger.error(f"Retailer search timeout after 90s — abandoning slow threads: {pending}. Proceeding with partial results.")
        finally:
            executor.shutdown(wait=False)  # Never block on slow/hung retailer threads

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

    # NOTE: DB write-back of live API results was removed (Mar 2026).
    # The product DB should only contain nightly-synced CJ/Awin inventory
    # from catalog_sync.py. Writing eBay/Amazon results back polluted the
    # curated catalog with marketplace listings that go stale quickly and
    # lack affiliate tracking from our approved networks.

    return all_products
