"""
ETSY API PRODUCT SEARCHER
Direct integration with Etsy's listings API
Returns real Etsy products with images

Key Etsy endpoints:
- /v3/application/listings/active (search listings)
- Includes: images, price, title, URL, seller info
"""

import requests
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


def search_products_etsy(profile, etsy_api_key, target_count=20):
    """
    Search Etsy for gift products.

    Etsy API v3 endpoint: GET /v3/application/listings/active
    Query params:
    - keywords: search terms
    - limit: results per page (max 100)
    - includes: Images,Shop (to get images and shop info)

    Returns list of products with:
    - title, link, snippet, image, price, source_domain
    """
    logger.info(f"Searching Etsy for {target_count} products")

    if not etsy_api_key:
        logger.warning("Etsy API key not configured - skipping Etsy search")
        return []

    interests = profile.get("interests", [])
    if not interests:
        return []

    # Build search queries (SKIP WORK INTERESTS)
    search_queries = []
    for interest in interests:
        name = interest.get("name", "")
        if not name:
            continue
        if interest.get("is_work", False):
            logger.info(f"Skipping work interest: {name}")
            continue

        # Gift-oriented queries
        name_lower = name.lower()
        if any(term in name_lower for term in ["musician", "singer", "band", "artist"]):
            query = f"{name} fan gift"
        elif any(term in name_lower for term in ["sports", "team", "basketball"]):
            query = f"{name} fan merchandise"
        else:
            query = f"{name} personalized gift"

        search_queries.append({
            "query": query,
            "interest": name,
            "priority": "high" if interest.get("intensity") == "passionate" else "medium",
        })

    search_queries = search_queries[:10]  # Max 10 searches
    logger.info(f"Running {len(search_queries)} Etsy searches")

    all_products = []

    for query_info in search_queries:
        query = query_info["query"]
        interest = query_info["interest"]

        try:
            response = requests.get(
                "https://openapi.etsy.com/v3/application/listings/active",
                headers={"x-api-key": etsy_api_key},
                params={
                    "keywords": query,
                    "limit": 10,
                    "includes": "Images,Shop",
                },
                timeout=10,
            )

            response.raise_for_status()
            data = response.json()

            listings = data.get("results", [])

            for listing in listings:
                listing_id = listing.get("listing_id")
                title = listing.get("title", "").strip()

                if not listing_id or not title:
                    continue

                lid = str(listing_id)

                # Build Etsy product URL
                link = f"https://www.etsy.com/listing/{listing_id}"

                # Get image
                images = listing.get("images", [])
                image = images[0].get("url_570xN", "") if images else ""

                # Get price
                price_data = listing.get("price", {})
                amount = price_data.get("amount", 0)
                divisor = price_data.get("divisor", 100) or 100
                price = f"${amount / divisor:.2f}" if divisor else ""

                # Get shop name for snippet
                description = (listing.get("description") or "").strip()
                tags = listing.get("tags") or []
                shop = listing.get("shop", {}) or {}
                shop_name = shop.get("shop_name", "")
                if description:
                    snippet = description[:150]
                elif tags:
                    snippet = "Tags: " + ", ".join(tags[:6])
                elif shop_name:
                    snippet = f"Handmade by {shop_name}"
                else:
                    snippet = title[:120]

                product = {
                    "title": title,
                    "link": link,
                    "snippet": snippet,
                    "image": image,
                    "thumbnail": image,
                    "image_url": image,
                    "source_domain": "etsy.com",
                    "search_query": query,
                    "interest_match": interest,
                    "priority": query_info["priority"],
                    "price": price,
                    "listing_id": lid,
                }

                if not any(p.get("listing_id") == lid for p in all_products):
                    all_products.append(product)
                    if len(all_products) <= 3:
                        logger.info(f"Collected Etsy product: {title[:50]}")

            count_this_interest = len([p for p in all_products if p["interest_match"] == interest])
            logger.info(f"Added {count_this_interest} Etsy products for '{interest}'")

        except requests.exceptions.RequestException as e:
            logger.error(f"Etsy API request failed for '{query}': {e}")
        except Exception as e:
            logger.error(f"Etsy API error for '{query}': {e}")

    logger.info(f"Found {len(all_products)} Etsy products")
    return all_products[:target_count]
