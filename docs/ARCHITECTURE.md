# GiftWise — Architecture Deep Dive

Read this when doing deep technical work, load testing, or the architectural stress audit.

## Searcher Module Pattern

Each searcher exports a `search_products_<source>()` function returning a list of product dicts:
`title`, `link`, `snippet`, `image`, `thumbnail`, `image_url`, `source_domain`, `search_query`, `interest_match`, `priority`, `price`, `product_id`.

`multi_retailer_searcher.py` orchestrates them all. Search order: Etsy → Awin → CJ → eBay → Amazon.

## All Python Modules

**Core pipeline:** `giftwise_app.py`, `recommendation_service.py`, `profile_analyzer.py`, `gift_curator.py`, `post_curation_cleanup.py`

**Search:** `multi_retailer_searcher.py`, `rapidapi_amazon_searcher.py`, `ebay_searcher.py`, `etsy_searcher.py`, `awin_searcher.py`, `cj_searcher.py`, `base_searcher.py`, `affiliate_searcher.py`

**Intelligence:** `interest_ontology.py`, `enrichment_engine.py`, `revenue_optimizer.py`, `smart_filters.py`, `search_query_utils.py`, `relationship_rules.py`

**Experience:** `experience_architect.py`, `experience_providers.py` (13 categories → Ticketmaster, Cozymeal, Viator, etc.), `experience_synthesis.py`

**Data/Storage:** `database.py` (SQLite), `storage_service.py` (shelve), `progress_store.py`, `site_stats.py`, `share_manager.py`, `catalog_sync.py`, `awin_catalog_sync.py`

**User-facing:** `spotify_parser.py` (text paste only), `reddit_scraper.py`, `oauth_integrations.py` (Pinterest, Etsy, Google — NOT Spotify), `social_conversion.py`, `referral_system.py`, `share_generator.py`

**Utilities:** `image_fetcher.py`, `link_validation.py`, `url_utils.py`, `api_client.py`, `auth_service.py`, `product_schema.py`, `config_service.py`

**Dead code:** `skimlinks_searcher.py` (Skimlinks defunct)

## Known Architectural Pressure Points

These are the items that need load testing before real traffic arrives.

### 1. Shelve Concurrency
`storage_service.py`, `site_stats.py`, `share_manager.py` use Python shelve. Gunicorn runs 3 sync workers. Shelve is NOT safe for concurrent writes from multiple processes. Potential corruption under load.

### 2. Worker Exhaustion
Claude API calls take 10-25 seconds each (2 per session). With 3 sync workers, the 4th concurrent user gets a 502. Real concurrency ceiling is ~3 simultaneous sessions.

### 3. SQLite Write Contention
`database.py` uses SQLite. Concurrent writes (click tracking, catalog sync) can hit lock contention. WAL mode status unknown.

### 4. Rate Limiting Race
Per-IP rate limiting is shelve-backed. With 3 workers, two concurrent requests from the same IP could both pass the check before either writes the block.

### 5. Catalog Sync Conflict
`catalog_sync.py` runs nightly via external cron hitting `/admin/sync-catalog`. If a user session is mid-pipeline when sync runs, potential conflict.

## Opus Load Test Prompt

Copy-paste this for the architectural stress audit:

> You are auditing GiftWise (a Flask/Gunicorn app on Railway.app) for architectural weaknesses under concurrent traffic. Read the full codebase — especially `giftwise_app.py`, `storage_service.py`, `site_stats.py`, `share_manager.py`, `database.py`, `recommendation_service.py`, and `railway.json`. Then:
>
> 1. **Shelve concurrency.** Are there write races with 3 Gunicorn workers? Failure mode?
> 2. **Worker exhaustion.** With 10 concurrent users and 3 sync workers, what happens? Concurrency ceiling?
> 3. **SQLite contention.** Concurrent writes — what breaks? WAL mode?
> 4. **Rate limiting race.** Can two same-IP requests both pass the check?
> 5. **Catalog sync conflict.** Can nightly sync conflict with mid-pipeline sessions?
>
> For each: rate (Critical/High/Medium), describe failure mode, recommend minimal fix. Implement Critical and High fixes.

## Env Vars

**Required:** `ANTHROPIC_API_KEY`

**Retailer credentials:** `AMAZON_AFFILIATE_TAG`, `EBAY_CLIENT_ID`, `EBAY_CLIENT_SECRET`, `CJ_API_KEY`, `AWIN_API_KEY`

**Model toggle:** `CLAUDE_PROFILE_MODEL`, `CLAUDE_CURATOR_MODEL` (default Sonnet for both)

**Admin:** `ADMIN_DASHBOARD_KEY`

**Optional:** `ONESIGNAL_APP_ID` (web push)
