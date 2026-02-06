# GiftWise – Comprehensive Handoff for Claude

Use this document when continuing work on GiftWise so the user has to do as little re-explaining as possible.

---

## 1. Project overview

**GiftWise** is a web app that generates highly personalized gift recommendations from scraped social profiles (Instagram, TikTok, Pinterest). The flow is: connect platforms → scrape → build a deep recipient profile → pull product inventory from multiple retailers → curate product and experience gifts with Claude → show recommendations.

- **Stack:** Python 3.11, Flask, Gunicorn. Optional: enrichment_engine, experience_architect, payment_model.
- **Deploy:** Railway, Nixpacks (`railway.json`, `nixpacks.toml`). Main app: `giftwise_app.py`.

---

## 2. End-to-end flow (recommendation run)

1. **Profile**  
   User connects platforms; we scrape (e.g. Instagram, TikTok, Pinterest). `build_recipient_profile()` (profile_analyzer.py) uses Claude to turn raw data into a structured profile: interests (name, evidence, intensity, **is_work**), location_context, style_preferences, price_signals, aspirational_vs_current, gift_avoid, specific_venues.

2. **Work filtering for backend**  
   We keep work interests **visible on the profile page** but **exclude them from search and curation**.  
   - `profile_for_search_and_curation(profile)` returns a deep copy of profile with `interests` filtered to `[i for i in profile['interests'] if not i.get('is_work')]`.  
   - **Used for:** enrichment (interest names), `search_products_multi_retailer(profile_for_backend, ...)`, `curate_gifts(profile_for_backend, ...)`.  
   - **Full profile** is still used for: smart_filters (work exclusion), `filter_workplace_experiences`, `filter_work_themed_experiences`, and UI display.

3. **Enrichment (optional)**  
   If the intelligence layer is available, `enrich_profile_simple()` runs on **non-work interest names only** and produces `enhanced_search_terms` and `quality_filters`. These are passed into the multi-retailer search and used for filtering.

4. **Inventory (multi-retailer)**  
   `search_products_multi_retailer(profile_for_backend, ..., target_count=10, enhanced_search_terms=...)` is called.  
   - **Strategy:** Request up to `target_count` (capped by `MAX_INVENTORY_SIZE // 5`) from **each** vendor and **merge** into one pool. We call **every** vendor that has credentials (no “fill then stop”). Order: Etsy → Awin → eBay → ShareASale → Amazon.  
   - **Return value is INVENTORY ONLY.** The caller must never use this list as the final recommendations. Final list comes only from the curator.  
   - Pool is capped at `MAX_INVENTORY_SIZE` (100) so the curator prompt stays manageable.

5. **Quality and smart filters**  
   - Intelligence `quality_filters` remove inappropriate products (e.g. adult content).  
   - `apply_smart_filters(products, profile)` uses the **full profile** to remove work-related gifts and misaligned active/passive products.

6. **Curation**  
   `curate_gifts(profile_for_backend, products, recipient_type, relationship, claude_client, rec_count=10)` is called with the **full filtered inventory**.  
   - Claude returns `product_gifts` (list of ~10) and `experience_gifts` (list; we ask for **exactly 3**, at least 2 required).  
   - **Product gifts** must be from the inventory (exact product_url from the list). No invented products.  
   - **Experience gifts** must be personal/leisure only (not work-themed); we later filter workplace and work-themed experiences.

7. **Post-process**  
   - `filter_workplace_experiences(experience_gifts, profile)` removes experiences at the recipient’s workplace.  
   - `filter_work_themed_experiences(experience_gifts, profile)` removes experiences themed on work (IndyCar, EMS, nursing, etc.).  
   - Final recommendations are built **only** from `product_gifts` and (filtered) `experience_gifts`. Each product gift’s `product_url` is validated against the inventory; invalid or invented URLs are dropped.  
   - Images: `process_recommendation_images(all_recommendations)` (product page extraction → validate feed/backfill → Google CSE → placeholder).

8. **Output**  
   `all_recommendations` (product + experience gifts) is what the user sees. No vendor mix is forced; if all 10 product gifts are from one vendor because they’re the best fit, that’s acceptable.

---

## 3. Critical design rules

- **Final recommendations come ONLY from the curator.** The multi-retailer searcher returns an inventory pool. We never assign `product_gifts = products` or slice inventory and use it as the final list. Comments and an assert in giftwise_app enforce this.
- **No forced vendor mix in the output.** We want a large, diverse pool so the curator has choice; we do **not** require the final 10 to span multiple vendors.
- **Work interests are excluded from search and curation** but remain on the profile for display and for filtering (work-related products, workplace/work-themed experiences).
- **Experiences:** We ask the curator for **exactly 3** experience gifts and require at least 2. After filtering (workplace + work-themed), we typically still have at least 2 bespoke experiences.

---

## 4. Key files and roles

| File | Role |
|------|------|
| **giftwise_app.py** | Flask app, routes, recommendation flow. Calls profile build, enrichment, multi-retailer search, smart filters, curator, experience filters, image pipeline. Defines `profile_for_search_and_curation()`, `/debug/awin-test`. |
| **profile_analyzer.py** | Builds recipient profile from scraped platform data (Claude). Outputs interests (with is_work), location_context, style_preferences, etc. |
| **multi_retailer_searcher.py** | Orchestrates product search: Etsy, Awin, eBay, ShareASale, Amazon. Requests from each vendor and merges into one pool. Returns inventory only; never final recommendations. `MAX_INVENTORY_SIZE = 100`. |
| **gift_curator.py** | Curates product and experience gifts via Claude. Takes profile (non-work), products (inventory), recipient_type, relationship. Returns `product_gifts` (from inventory only) and `experience_gifts` (3 requested, ≥2 required). Prompt enforces source priority (prefer Etsy/Awin/eBay/ShareASale over Amazon), diversity (max 2 per interest, 5+ interests), long why_perfect, and non-work experiences. |
| **awin_searcher.py** | Awin data feed API: feed list → stream or non-stream feed CSV → match by query/primary_term. Has `_stream_feed_and_match`, `_fetch_feed_nonstream` (fallback when stream fails with "I/O operation on closed file"), `_stream_feed_first_n` (fallback when no matches). Sets `r.raw.decode_content = True` for gzip. Still seeing stream parse failures in production; non-stream fallback used when stream yields 0. |
| **ebay_searcher.py** | eBay Browse API: OAuth client credentials, item_summary/search. Builds queries from non-work interests. Product dict includes `image`, `thumbnail`, `image_url` (eBay returns stable imageUrl → high “feed validated” thumbnails). |
| **rapidapi_amazon_searcher.py** | RapidAPI “Real-Time Amazon Data”: search by interest queries. Cap of 2 products per query so results span interests. Maps multiple image keys; sets `image`, `thumbnail`, `image_url`. |
| **etsy_searcher.py** | Etsy API: listings search. Currently returns 403 (awaiting approval). |
| **smart_filters.py** | Work exclusion (work-related products), passive/active filter. `filter_workplace_experiences`, `filter_work_themed_experiences` (IndyCar, EMS, nursing, etc.). Uses full profile. |
| **image_fetcher.py** | Product image resolution: product page extraction (longer timeout for Amazon) → validate feed/backfill → Google CSE → placeholder. `get_product_image` uses `image_url` or `image`. |
| **enrichment_engine.py** | Optional: enriches profile with search terms and quality filters. Used with non-work interests only. |

---

## 5. Vendors: status and env vars

| Vendor | Status | Env vars | Notes |
|--------|--------|----------|--------|
| **Etsy** | 403 Forbidden | `ETSY_API_KEY` | Awaiting API approval. |
| **Awin** | Stream parse fails in prod | `AWIN_DATA_FEED_API_KEY` | Feed list works (607 feeds). Stream: "I/O operation on closed file"; non-stream fallback when stream yields 0. `/debug/awin-test` available for diagnosis. |
| **eBay** | Working | `EBAY_CLIENT_ID`, `EBAY_CLIENT_SECRET` | Browse API; 100% thumbnails from feed when used. |
| **ShareASale** | Not configured | `SHAREASALE_AFFILIATE_ID`, `SHAREASALE_API_TOKEN`, `SHAREASALE_API_SECRET` | Optional. |
| **Amazon** | Working | `RAPIDAPI_KEY` | RapidAPI Real-Time Amazon Data. |

Other: `ANTHROPIC_API_KEY` (profile + curator). Optional: `GOOGLE_CSE_API_KEY`, `GOOGLE_CUSTOM_SEARCH_ENGINE_ID` (image search).

---

## 6. Work and experience handling

- **Profile:** Work interests (`is_work=True`) are shown on the profile page but removed for search/curation via `profile_for_search_and_curation(profile)`.
- **Products:** Smart filters (full profile) remove work-related products. Curator never sees work interests.
- **Experiences:** Prompt says experiences must be personal/leisure only (never work). After curation we run `filter_workplace_experiences` (venue at workplace) and `filter_work_themed_experiences` (keywords: IndyCar, EMS, nursing, etc.). We ask for **3** experiences and require **at least 2** so that after filtering we usually still have ≥2.

---

## 7. Images

- **eBay:** API returns `image.imageUrl`; we set `image`, `thumbnail`, `image_url` on each product. These validate well → “feed validated” in image_fetcher.
- **Amazon (RapidAPI):** We map several image keys and set `image`, `thumbnail`, `image_url`. Product-page extraction has a longer timeout for Amazon URLs. Many placeholders if API doesn’t return good URLs.
- **Awin:** `_row_to_product` sets `image`, `thumbnail`, `image_url`. When Awin returns products, they can be validated the same way.
- **Pipeline:** `get_product_image` uses `image_url` or `image`; product_url_to_image in giftwise_app backfills from inventory; then process_recommendation_images runs (extract → validate → Google → placeholder).

---

## 8. Debug and testing

- **`/debug/awin-test`** (giftwise_app.py): Diagnostic for Awin. Fetches feed list, tests direct download (no stream), then streaming with `decode_content=True`. User can hit the URL and paste output to diagnose "I/O operation on closed file" or other Awin issues.
- **Logs:** Railway runtime logs show: Multi-retailer “Product source breakdown”, “Total products in pool”, curator “Curated X products + Y experiences”, “After workplace/work-themed experience filter”, image “Feed/backfill thumbnail validated” vs placeholders.
- **Local:** Run app locally; recommendation flow uses same code path. Env vars in `.env` (see env.template).

---

## 9. Known issues and next steps

- **Awin:** Stream still fails in production (“I/O operation on closed file”). Non-stream fallback helps when it yields 0; if fallback also fails (e.g. auth, HTML error page), use `/debug/awin-test` output to fix.
- **Etsy:** 403 until API approval; no code change until then.
- **Unified criteria (future):** See `UNIFIED_CRITERIA_DESIGN.md`. Goal: one “gift criteria” spec from profile → pass to all APIs → curator evaluates across sources. Current behavior: large merged pool, no forced vendor mix in output.

---

## 10. Checklist for changes

- If you change **multi_retailer_searcher:** keep returning an inventory pool only; never return “final” recommendations. Caller must pass pool to curator.
- If you change **giftwise_app** recommendation flow: final list must come only from `curated.get('product_gifts')` and filtered `experience_gifts`; never from `products` (inventory) directly.
- If you change **curator:** keep “at least 2 experience gifts” (we ask for 3), inventory-only product_gifts, and non-work experiences.
- If you add a new vendor searcher: return same product dict shape (`title`, `link`, `image`, `thumbnail`, `image_url`, `source_domain`, `product_id`, etc.) and add to multi_retailer_searcher with the same “request from each and merge” pattern.

---

*Last updated to reflect: large inventory from all vendors, no per-vendor cap, no forced vendor mix in output, curator-only final list, exactly 3 experiences requested (≥2 required), Awin non-stream fallback, eBay/Amazon/Awin image fields, work filtering and experience filters, and /debug/awin-test.*
