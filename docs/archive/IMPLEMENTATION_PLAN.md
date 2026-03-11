# GiftWise Implementation Plan — Architectural Fixes

## Context for the implementing agent

You are implementing fixes to GiftWise, an AI-powered gift recommendation app.
The pipeline is: scrape social media → Claude analyzes profile → enrich with static data → search retailers (eBay, Amazon active; Etsy and Awin coming soon) → Claude curates gifts → programmatic cleanup → display.

These changes were designed by an architecture audit. Each change is scoped to specific files with exact locations. **Do them in the order listed** — later changes depend on earlier ones.

**Rules:**
- Do NOT refactor surrounding code. Only touch what's specified.
- Do NOT add comments explaining the change unless specified.
- Do NOT rename existing variables or functions.
- Test that the app still starts after each file-level change before moving to the next.
- If a change feels ambiguous, pick the simpler interpretation.

---

## CHANGE 1: Remove image_url from curator responsibility (Thumbnail fix)

**Problem:** The curator (LLM) is asked to copy image URLs verbatim from a product list. It drops or corrupts them. Images are then missing at display time.

**Fix:** Stop asking the curator to return image_url. Always resolve images programmatically from the inventory after curation.

### File: gift_curator.py

**1a. In `format_products()` (~line 352-368), remove the Image line from the formatted output.**

Current (line 365-366):
```python
        image_url = p.get('image', '') or p.get('thumbnail', '')
        formatted.append(f"{idx}. {title}\n   Price: {price} | Domain: {domain} | Interest match: {interest}\n   Description: {snippet[:150]}\n   URL: {link}\n   Image: {image_url}")
```

Change to:
```python
        formatted.append(f"{idx}. {title}\n   Price: {price} | Domain: {domain} | Interest match: {interest}\n   Description: {snippet[:150]}\n   URL: {link}")
```

(Delete the `image_url = ...` line entirely. Remove `\n   Image: {image_url}` from the f-string.)

**1b. In the curator prompt JSON schema (~line 194), remove image_url from the product_gifts schema.**

Current:
```
      "product_url": "exact URL from list",
      "image_url": "exact image URL from list",
      "confidence_level": "safe_bet|adventurous",
```

Change to:
```
      "product_url": "exact URL from list",
      "confidence_level": "safe_bet|adventurous",
```

**1c. In the CRITICAL REQUIREMENTS section (~line 178 and ~221), remove references to image URLs.**

Line 178, current:
```
- Use exact URLs and image URLs from product list
```
Change to:
```
- Use exact URLs from product list
```

Line 221, current:
```
- Product gifts MUST be selected FROM THE INVENTORY ABOVE ONLY. Every product gift must be one of the {len(products)} listed products (use exact URLs and image URLs from that line). Never invent or reference a product not in the inventory.
```
Change to:
```
- Product gifts MUST be selected FROM THE INVENTORY ABOVE ONLY. Every product gift must be one of the {len(products)} listed products (use exact URLs from that line). Never invent or reference a product not in the inventory.
```

### File: giftwise_app.py

**1d. In the recommendation assembly loop (~line 2737-2766), never read image_url from curator output. Always resolve from inventory map.**

Current (lines 2743-2745):
```python
                image_url = (gift.get('image_url') or '').strip()
                if not image_url:
                    image_url = product_url_to_image.get(product_url, '') or product_url_to_image.get(_normalize_url_for_image(product_url), '')
```

Change to:
```python
                image_url = product_url_to_image.get(product_url, '') or product_url_to_image.get(_normalize_url_for_image(product_url), '')
```

(Remove the `image_url = (gift.get('image_url') or '').strip()` line and the `if not image_url:` conditional. Always resolve from the map.)

**1e. Strengthen the URL normalization function (~line 2708-2712) to handle more variation.**

Current:
```python
            def _normalize_url_for_image(u):
                if not u or not isinstance(u, str):
                    return ''
                u = u.strip().rstrip('/')
                return u or ''
```

Change to:
```python
            def _normalize_url_for_image(u):
                if not u or not isinstance(u, str):
                    return ''
                u = u.strip().rstrip('/')
                # Strip tracking query params that don't affect the product page
                if '?' in u:
                    base, _, qs = u.partition('?')
                    # Keep Amazon dp/ URLs clean; strip query from most URLs
                    if '/dp/' in base or '/listing/' in base or '/itm/' in base:
                        u = base
                return u or ''
```

---

## CHANGE 2: Fix eBay snippet (eBay selection fix)

**Problem:** eBay products have snippet = "From {seller_username}" which gives the curator no information about what the product is. The curator rationally skips them.

### File: ebay_searcher.py

**2a. Replace the snippet construction (~line 161-162).**

Current:
```python
            seller = item.get("seller") or {}
            seller_name = seller.get("username", "")
            snippet = f"From {seller_name}" if seller_name else title[:100]
```

Change to:
```python
            short_desc = (item.get("shortDescription") or "").strip()
            categories = item.get("categories") or []
            category_name = categories[0].get("categoryName", "") if categories else ""
            condition = (item.get("condition") or "").strip()
            snippet_parts = [s for s in [short_desc[:120], category_name, condition] if s]
            snippet = " | ".join(snippet_parts) if snippet_parts else title[:120]
```

---

## CHANGE 3: Fix Etsy snippet (prepping for Etsy launch)

**Problem:** Same as eBay — Etsy snippet is "By {shop_name}", which tells the curator nothing about the product.

### File: etsy_searcher.py

**3a. Replace the snippet construction (~line 115-117).**

Current:
```python
                shop = listing.get("shop", {}) or {}
                shop_name = shop.get("shop_name", "")
                snippet = f"By {shop_name}" if shop_name else title[:100]
```

Change to:
```python
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
```

**3b. Ensure `thumbnail` and `image_url` keys are set (for image backfill consistency).**

Current product dict (~line 119-130):
```python
                product = {
                    "title": title,
                    "link": link,
                    "snippet": snippet,
                    "image": image,
                    "source_domain": "etsy.com",
```

Change to:
```python
                product = {
                    "title": title,
                    "link": link,
                    "snippet": snippet,
                    "image": image,
                    "thumbnail": image,
                    "image_url": image,
                    "source_domain": "etsy.com",
```

---

## CHANGE 4: Fix Awin snippet (prepping for Awin launch)

**Problem:** Awin's `_row_to_product()` already has access to description/keywords in the feed row (used by `_product_text()`) but the snippet is "From {merchant_name}".

### File: awin_searcher.py

**4a. In `_row_to_product()` (~line 264-301), replace the snippet construction.**

Current (line 281):
```python
    snippet = f"From {merchant}" if merchant else title[:100]
```

Change to:
```python
    description = (
        row.get("product_short_description") or row.get("description")
        or row.get("Description") or row.get("product_description") or ""
    ).strip()
    snippet = description[:150] if description else (f"From {merchant}" if merchant else title[:120])
```

---

## CHANGE 5: Interleave products by source in the inventory pool

**Problem:** Products are appended sequentially by vendor. The prompt cap (50) can cut off entire sources. Also creates positional bias in the curator.

### File: multi_retailer_searcher.py

**5a. After the inventory cap (~line 162-165), add source interleaving.**

Current:
```python
    # Cap total inventory size so curator prompt stays manageable
    if len(all_products) > MAX_INVENTORY_SIZE:
        all_products = all_products[:MAX_INVENTORY_SIZE]
        logger.info(f"Inventory capped at {MAX_INVENTORY_SIZE} for curation")

    source_counts = defaultdict(int)
```

Change to:
```python
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
```

---

## CHANGE 6: Add source diversity rule to post-curation cleanup

**Problem:** Cleanup enforces brand, category, and interest diversity but not source diversity. Result can be 100% Amazon even when other sources are in the pool.

### File: post_curation_cleanup.py

**6a. Add source tracking alongside existing brand/category tracking (~line 193-196).**

Current:
```python
    used_urls = set()
    used_brands = set()
    used_categories = set()
    interest_counts = {}
```

Change to:
```python
    used_urls = set()
    used_brands = set()
    used_categories = set()
    interest_counts = {}
    source_counts = defaultdict(int)
    MAX_PER_SOURCE_PCT = 0.6  # No more than 60% from one source
```

Add `from collections import defaultdict` to the top-level imports (line 3 area) if not already present.

**6b. In the main loop where products pass checks (~line 249-256), track source and enforce cap.**

Current:
```python
        # Passed all checks
        used_urls.add(url)
        used_urls.add(normalized_url)
        if brand:
            used_brands.add(brand)
        if category:
            used_categories.add(category)
        cleaned.append(gift)
```

Change to:
```python
        # Rule 6: Source diversity — no more than 60% from one source
        inv_product = inventory_by_url.get(url) or inventory_by_url.get(normalized_url) or {}
        source = inv_product.get('source_domain', gift.get('where_to_buy', 'unknown')).lower()
        max_from_source = max(2, int(rec_count * MAX_PER_SOURCE_PCT))
        if source_counts[source] >= max_from_source:
            logger.info(f"CLEANUP: Deferred (source cap '{source}'): {name[:50]}")
            deferred.append(gift)
            continue

        # Passed all checks
        used_urls.add(url)
        used_urls.add(normalized_url)
        if brand:
            used_brands.add(brand)
        if category:
            used_categories.add(category)
        source_counts[source] += 1
        cleaned.append(gift)
```

**6c. In the replacement section (~line 261-314), also track source for replacements and prefer under-represented sources.**

In the scoring section (~line 274-282), add source scoring. Current:
```python
            # Prefer products that bring new brands and categories
            score = 0
            if brand and brand not in used_brands:
                score += 2
            if category and category not in used_categories:
                score += 2
            interest = (p.get('interest_match') or '').lower()
            if interest and interest_counts.get(interest, 0) < 2:
                score += 1
            candidates.append((score, p))
```

Change to:
```python
            # Prefer products that bring new brands, categories, and source diversity
            score = 0
            if brand and brand not in used_brands:
                score += 2
            if category and category not in used_categories:
                score += 2
            interest = (p.get('interest_match') or '').lower()
            if interest and interest_counts.get(interest, 0) < 2:
                score += 1
            p_source = p.get('source_domain', 'unknown').lower()
            if source_counts.get(p_source, 0) == 0:
                score += 3  # Strongly prefer unrepresented sources
            elif source_counts.get(p_source, 0) < max(2, int(rec_count * MAX_PER_SOURCE_PCT)):
                score += 1
            candidates.append((score, p))
```

In the replacement building section (~line 306-313), track source. After:
```python
            if interest:
                interest_counts[interest] = interest_counts.get(interest, 0) + 1
```

Add:
```python
            r_source = p.get('source_domain', 'unknown').lower()
            source_counts[r_source] = source_counts.get(r_source, 0) + 1
```

---

## CHANGE 7: Ask curator for 14 products, cleanup trims to 10

**Problem:** Curator returns exactly `rec_count` (10). After cleanup drops duplicates, you can end up with 7-8 products and replacements from inventory have weak why_perfect text.

### File: giftwise_app.py

**7a. Where `curate_gifts()` is called, pass a higher rec_count to the curator.**

Find the call to `curate_gifts()` (around line 2670-2677). It currently passes `rec_count=product_rec_count`. Change the call so the curator gets 14 but cleanup still trims to the original count.

Find the line like:
```python
            curated = curate_gifts(
```

In the arguments to that call, change the `rec_count` parameter from `product_rec_count` to `product_rec_count + 4`. Do NOT change any other arguments in that call.

---

## CHANGE 8: Pass enrichment do_buy/dont_buy to curator prompt

**Problem:** The enrichment engine computes per-interest do_buy and dont_buy lists that never reach the curator. These are the most actionable signals being dropped.

### File: giftwise_app.py

**8a. Where `enrichment_context` is built (~line 2668-2677), add enriched interest data.**

Find this block:
```python
            enrichment_context = {
                'demographics': enriched_profile.get('demographics', {}),
                'trending_items': enriched_profile.get('trending_items', []),
                'anti_recommendations': enriched_profile.get('anti_recommendations', []),
                'relationship_guidance': enriched_profile.get('relationship_guidance', {}),
                'price_guidance': enriched_profile.get('price_guidance', {}),
            }
```

Change to:
```python
            enrichment_context = {
                'demographics': enriched_profile.get('demographics', {}),
                'trending_items': enriched_profile.get('trending_items', []),
                'anti_recommendations': enriched_profile.get('anti_recommendations', []),
                'relationship_guidance': enriched_profile.get('relationship_guidance', {}),
                'price_guidance': enriched_profile.get('price_guidance', {}),
                'enriched_interests': enriched_profile.get('enriched_interests', []),
            }
```

### File: gift_curator.py

**8b. In the enrichment_section builder (~line 86-118), add do_buy/dont_buy rendering.**

Find the end of the enrichment section builder. After the `price_g` block (~line 114-115):
```python
        if price_g and price_g.get('guidance'):
            parts.append(f"💰 PRICE GUIDANCE: {price_g['guidance']}")
```

Add after it:
```python
        enriched_interests = enrichment_context.get('enriched_interests', [])
        if enriched_interests:
            interest_intel = []
            for ei in enriched_interests[:8]:
                name = ei.get('interest', '')
                do_buy = ei.get('do_buy', [])[:3]
                dont_buy = ei.get('dont_buy', [])[:3]
                if do_buy or dont_buy:
                    line = f"  {name}:"
                    if do_buy:
                        line += f" BUY [{', '.join(do_buy)}]"
                    if dont_buy:
                        line += f" AVOID [{', '.join(dont_buy)}]"
                    interest_intel.append(line)
            if interest_intel:
                parts.append("🎁 PER-INTEREST GUIDANCE:\n" + chr(10).join(interest_intel))
```

---

## CHANGE 9: Bump profile analyzer max_tokens to prevent truncation

**Problem:** 4000 max_tokens risks truncating complex profiles (12 interests with evidence). Truncated JSON silently falls back to empty profile, cascading into generic recommendations.

### File: profile_analyzer.py

**9a. Change max_tokens in the Claude API call (~line 393-398).**

Current:
```python
        message = claude_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
```

Change to:
```python
        message = claude_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=6000,
```

---

## CHANGE 10: Tighten Awin query matching (prep for Awin launch)

**Problem:** `_matches_query()` returns True if ANY single query term appears anywhere in product text. "Thai cooking gift" matches any product with "gift" in its name, producing irrelevant matches.

### File: awin_searcher.py

**10a. Replace `_matches_query()` (~line 317-327).**

Current:
```python
def _matches_query(row, query_terms):
    """True if product name/keywords/description contain any of the query terms (skip stopwords)."""
    text = _product_text(row)
    stopwords = {"and", "the", "or", "with", "from"}  # allow "gift" and "for" to match
    for term in query_terms:
        t = (term or "").strip().lower()
        if len(t) <= 1 or t in stopwords:
            continue
        if t in text:
            return True
    return False
```

Change to:
```python
def _matches_query(row, query_terms):
    """True if product text contains the primary interest term (not just generic words like 'gift')."""
    text = _product_text(row)
    generic_terms = {"and", "the", "or", "with", "from", "gift", "present", "idea", "unique", "personalized", "accessories", "lover", "fan"}
    meaningful_matches = 0
    for term in query_terms:
        t = (term or "").strip().lower()
        if len(t) <= 1 or t in generic_terms:
            continue
        if t in text:
            meaningful_matches += 1
    return meaningful_matches >= 1
```

---

## CHANGE 11: Delete unused enhanced_recommendation_engine.py

**Problem:** Legacy module that duplicates functionality now split across profile_analyzer.py, gift_curator.py, and post_curation_cleanup.py. Its presence creates confusion about which code path is active. It is imported but never called in the main flow.

### Action:
Delete the file `/home/user/GiftWise/enhanced_recommendation_engine.py`.

Then in `giftwise_app.py`, find and remove the import block (~lines 82-92):
```python
try:
    from enhanced_recommendation_engine import (
        extract_deep_signals,
        integrate_wishlist_data,
        detect_duplicates,
        build_enhanced_prompt,
        validate_recommendations
    )
    from enhanced_data_extraction import combine_all_signals
    ENHANCED_ENGINE_AVAILABLE = True
except ImportError:
    ENHANCED_ENGINE_AVAILABLE = False
```

Replace with:
```python
ENHANCED_ENGINE_AVAILABLE = False
```

Also search giftwise_app.py for any references to `ENHANCED_ENGINE_AVAILABLE` and verify they all handle the `False` case gracefully (they should already, since the try/except was there for exactly that reason).

---

## Verification

After all changes, verify:
1. `python -c "import giftwise_app"` — no import errors
2. `python -c "import gift_curator"` — no import errors
3. `python -c "import multi_retailer_searcher"` — no import errors
4. `python -c "import post_curation_cleanup"` — no import errors
5. `python -c "import ebay_searcher"` — no import errors
6. `python -c "import etsy_searcher"` — no import errors
7. `python -c "import awin_searcher"` — no import errors
8. `python -c "import profile_analyzer"` — no import errors
9. Confirm `enhanced_recommendation_engine.py` no longer exists

---

## What these changes accomplish (for the developer)

| Change | Fixes | User-visible improvement |
|--------|-------|--------------------------|
| 1 | Missing thumbnails | Products show real images instead of placeholder emoji |
| 2-4 | Curator ignoring non-Amazon | eBay/Etsy/Awin products become competitive in selection |
| 5 | Positional bias | Fair representation of all sources in curator's view |
| 6 | 100% Amazon output | Programmatic guarantee of source diversity |
| 7 | Fewer than 10 products after cleanup | Consistent delivery of full recommendation count |
| 8 | Wasted enrichment intelligence | Better category targeting per interest |
| 9 | Silent profile truncation | Fewer mystery failures with generic output |
| 10 | Irrelevant Awin matches | Higher quality Awin products when Awin goes live |
| 11 | Codebase confusion | Cleaner codebase, no dead code paths |
