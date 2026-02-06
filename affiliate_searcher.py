"""
AFFILIATE PRODUCT SEARCHER (ShareASale / Awin)

ShareASale was acquired by Awin (awin.com). The ShareASale platform closed October 2025;
publishers were migrated to Awin. This module still uses the legacy ShareASale API endpoint.
For new integrations, use Awin's API (see AFFILIATE_NETWORK_GUIDANCE.md).

Legacy ShareASale Product Search API:
- Endpoint: https://api.shareasale.com/w.cfm
- Env vars: SHAREASALE_AFFILIATE_ID, SHAREASALE_API_TOKEN, SHAREASALE_API_SECRET
"""

import requests
import logging
import hashlib
import time

logger = logging.getLogger(__name__)


def generate_shareasale_signature(affiliate_id, token, secret, timestamp):
    """Generate API signature for ShareASale."""
    sig_string = f"{token}:{timestamp}:{secret}"
    return hashlib.sha256(sig_string.encode()).hexdigest()


def search_products_shareasale(
    profile, affiliate_id, api_token, api_secret, target_count=20
):
    """
    Search ShareASale merchant product feeds.

    Note: Requires merchants to be approved first.
    Focus on fashion/jewelry/gift merchants.
    """
    logger.info(f"Searching ShareASale for {target_count} products")

    if not all([affiliate_id, api_token, api_secret]):
        logger.warning("ShareASale credentials not fully configured - skipping ShareASale search")
        return []

    interests = profile.get("interests", [])
    if not interests:
        return []

    # Build queries (skip work)
    search_queries = []
    for interest in interests:
        name = interest.get("name", "")
        if not name:
            continue
        if interest.get("is_work", False):
            logger.info(f"Skipping work interest: {name}")
            continue

        search_queries.append({
            "query": f"{name} gift",
            "interest": name,
            "priority": "high" if interest.get("intensity") == "passionate" else "medium",
        })

    search_queries = search_queries[:10]
    logger.info(f"Running {len(search_queries)} ShareASale searches")

    all_products = []

    for query_info in search_queries:
        query = query_info["query"]
        interest = query_info["interest"]

        try:
            timestamp = str(int(time.time()))
            signature = generate_shareasale_signature(
                affiliate_id, api_token, api_secret, timestamp
            )

            response = requests.get(
                "https://api.shareasale.com/w.cfm",
                params={
                    "affiliateId": affiliate_id,
                    "token": api_token,
                    "signature": signature,
                    "timestamp": timestamp,
                    "action": "productsearch",
                    "keyword": query,
                    "resultsPerPage": 10,
                },
                timeout=10,
            )

            response.raise_for_status()

            # ShareASale may return XML; try JSON first
            ct = response.headers.get("content-type", "")
            if "application/json" in ct:
                data = response.json()
                products_list = data.get("products", []) or data.get("results", [])
            else:
                logger.debug(f"ShareASale returned non-JSON for '{query}' - skipping")
                continue

            for item in products_list:
                product_id = item.get("productId") or item.get("sku") or item.get("id")
                title = (item.get("productName") or item.get("name", "") or "").strip()

                if not product_id or not title:
                    continue

                pid = str(product_id)
                link = item.get("productUrl", "") or item.get("buyUrl", "") or item.get("link", "")
                image = item.get("productImage", "") or item.get("thumbUrl", "") or item.get("image", "")
                price = item.get("productPrice", "") or item.get("price", "")
                merchant = item.get("merchantName", "") or item.get("merchant", "")

                snippet = f"From {merchant}" if merchant else title[:100]
                source_domain = (
                    merchant.lower().replace(" ", "").replace("-", "") + ".com"
                    if merchant
                    else "shareasale.com"
                )

                product = {
                    "title": title,
                    "link": link,
                    "snippet": snippet,
                    "image": image,
                    "source_domain": source_domain,
                    "search_query": query,
                    "interest_match": interest,
                    "priority": query_info["priority"],
                    "price": str(price) if price else "",
                    "product_id": pid,
                }

                if not any(p.get("product_id") == pid for p in all_products):
                    all_products.append(product)
                    if len(all_products) <= 3:
                        logger.info(f"Collected ShareASale product: {title[:50]} from {merchant}")

            count_this = len([p for p in all_products if p["interest_match"] == interest])
            logger.info(f"Added {count_this} ShareASale products for '{interest}'")

        except requests.exceptions.RequestException as e:
            logger.error(f"ShareASale API request failed for '{query}': {e}")
        except Exception as e:
            logger.error(f"ShareASale API error for '{query}': {e}")

    logger.info(f"Found {len(all_products)} ShareASale products")
    return all_products[:target_count]
