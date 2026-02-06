# Claude → Cursor: Multi-Retailer Product Integration Handoff

**Saved:** February 5, 2026  
**Status:** Reference – not yet implemented in codebase

This file is a **reference copy** of Claude’s full handoff for moving from search proxies (SerpAPI / Google CSE) to direct multi-retailer APIs (Etsy → ShareASale/Awin → Amazon fallback). The full handoff text is in the user’s message; below is a short index and current-state note for Claude.

**Update (Feb 2026):** ShareASale was acquired by **Awin** (awin.com); ShareASale platform closed October 2025. For new affiliate signups use Awin. See **AFFILIATE_NETWORK_GUIDANCE.md**.

---

## Handoff contents (from Claude’s message)

1. **Current state & problem** – SerpAPI/Google CSE return generic/category pages; need real products from Etsy, ShareASale/Awin (brands), Amazon.
2. **Solution** – Etsy API (primary), ShareASale/Awin (brands; use Awin for new signups), Amazon Product Advertising / RapidAPI (fallback).
3. **Phased rollout** – Phase 1: RapidAPI Amazon only → Phase 2: Etsy + Amazon → Phase 3: Etsy + ShareASale + Amazon.
4. **New files to add** – `etsy_searcher.py`, `affiliate_searcher.py`, `multi_retailer_searcher.py`.
5. **Updates** – `giftwise_app.py`: switch product search to `search_products_multi_retailer(...)` with env vars for Etsy, ShareASale, RapidAPI/Amazon.
6. **Do not change** – `smart_filters.py`, `gift_curator.py`, `experience_architect.py`; work filtering and smart filters must stay.
7. **Full code** – Etsy searcher, ShareASale searcher, and multi-retailer orchestrator code are in Claude’s message.
8. **Env vars** – `ETSY_API_KEY`, `SHAREASALE_*`, `RAPIDAPI_KEY` (or Amazon PA-API); phased by phase.
9. **UI** – Retailer attribution line under recommendations (e.g. “Powered by Etsy & Amazon • more coming soon!”).

---

## Current codebase state (as of Cursor session Feb 5)

- **Product search in use:** `giftwise_app.py` calls `search_products_google_cse()` (from `google_cse_searcher.py`) with `GOOGLE_CSE_API_KEY` and `GOOGLE_CUSTOM_SEARCH_ENGINE_ID`.  
  (Elsewhere there is also `product_searcher.search_real_products()` used for SerpAPI; Cursor’s recent work was on that path for rate limiting and scaling.)
- **No `rapidapi_amazon_searcher.py`** in the repo – only `AMAZON_ASSOCIATES_GUIDE.md`. Phase 1 (Amazon-only) will need this module added (stub or real RapidAPI/Amazon implementation).
- **No `etsy_searcher.py` or `affiliate_searcher.py` or `multi_retailer_searcher.py`** yet.

---

## Next steps for Claude (or Cursor) to implement

1. Add the three modules using the code from Claude’s handoff:
   - `etsy_searcher.py`
   - `affiliate_searcher.py`
   - `multi_retailer_searcher.py`
2. Add or implement **`rapidapi_amazon_searcher.py`** so Phase 1 (Amazon-only) works when `RAPIDAPI_KEY` is set; otherwise multi_retailer can skip Amazon and still run.
3. In **`giftwise_app.py`**:
   - Replace the `google_cse_searcher` import with `multi_retailer_searcher`.
   - Replace the `search_products_google_cse(...)` call with `search_products_multi_retailer(..., etsy_key=..., shareasale_*=..., amazon_key=...)` using the env vars from the handoff.
4. Set Railway env vars per phase (Etsy, ShareASale, RAPIDAPI_KEY as described in the handoff).
5. Add the retailer attribution UI snippet to the recommendations template as in the handoff.

---

## Cursor session summary (for Claude)

- **CURSOR_SESSION_SUMMARY_FEB5.md** – Cursor’s work: SerpAPI global rate limiter, scrape concurrency cap, `import os` / `global _serpapi_last_call` fixes, operations logging, and **OPERATIONS_AND_SCALING.md** for Chad. Chad asked for “steps only” when he reports back (no “check the MD”).
- Product search **currently** goes through Google CSE in the main rec flow; multi-retailer is the intended replacement once the above steps are done.

Use this file plus **CURSOR_SESSION_SUMMARY_FEB5.md** and Claude’s original handoff message to continue implementation or hand back to Cursor with clear tasks.
