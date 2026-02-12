# GiftWise — Project Intelligence

## Environment Notes
- **Git is installed and working.** Do not prompt the user to install git, git for windows, or any other tooling. The repo is active with full commit history. Just use it.
- **Python/Flask app.** Run with `python giftwise_app.py` or via deployment. No special build step.
- **Branch:** Check `git branch` for the current working branch before making changes.

## What This Is
AI-powered gift recommendation app. Flask pipeline: scrape social media → Claude analyzes profile → enrich with static data → search retailers → Claude curates gifts → programmatic cleanup → display.

## Current Sprint: Affiliate Network Buildout (Feb 2026)

### What just happened (branch: `claude/debug-awin-links-Tq5On`)

**Awin fixes (commit d65a230):**
- Awin was returning garbage — AliExpress PL, Dutch adult stores, closed German merchants
- Root cause: all 607 feeds were "Not Joined", no region filtering, no content filtering
- Fixed: hard-filter closed/adult feeds, -15 penalty for non-English regions, regex-based source_domain extraction
- Fixed: experience material fallback links now include Amazon affiliate tag

**Awin gated behind joined feeds (commit 746a8aa):**
- If 0 joined advertisers → return [] immediately (was wasting ~30s downloading random feeds)
- Created `skimlinks_searcher.py` — full Product Key API v2 integration, wired into multi_retailer_searcher.py as step 5

**Gift guides for Skimlinks approval (commits e30bab6, 883a3a6):**
- 6 editorial gift guide pages at `/guides/<slug>`: beauty-lover, music-fan, homebody, travel-obsessed, dog-parent, tech-nerd
- `/privacy` and `/terms` routes added
- Footer updated with affiliate disclosure + guides link
- Purpose: Skimlinks has ~3% acceptance rate — these pages demonstrate editorial quality

### Immediate next steps (in priority order)

**1. Apply to Skimlinks — this is the fastest path to broad coverage**
- Site is ready: 6 guide articles, affiliate disclosures, privacy/terms pages
- One acceptance = blanket access to ~48,500 merchants (no per-brand applications)
- Trade-off: 25% revenue share (you keep 75% of commissions)
- Gift guides are deployed and ready for reviewer inspection

**2. Apply to Impact and CJ Affiliate networks**
- These two networks cover the most brands from the family's wishlist (see brand mapping below)
- Impact: Target, Ulta, Kohl's, Gap/Old Navy/BR, Home Depot, Adidas, Shark, Crate & Barrel, Spanx, Petco, PetSmart, Dick's, Dyson, EverEve, Lowe's
- CJ: Macy's, Nike (US), American Eagle/Aerie, J.Crew, Madewell, Columbia, North Face, Kiehl's

**3. Continue Rakuten applications**
- Already signed up. Brands on Rakuten: Sephora, Nordstrom, Anthropologie, Free People, Urban Outfitters, Coach, ASOS, West Elm, H&M
- Known issue: Sephora US doesn't show up (only Sephora BR). This is a confirmed platform-wide bug reported by many publishers. Workaround: email `uspubsupport@rakuten.com` or try Sephora's own "My Sephora Storefront" (via Motom) program at 15%.

**4. Spotify — not currently integrated, but worth watching**
- Spotify announced (Feb 6, 2026) severe restrictions on Development Mode: Premium required, 1 Client ID per dev, max 5 authorized users
- We don't use Spotify yet. If we add it later, we'll need Extended Quota Mode approval. Not urgent.

**5. Future searcher modules to build**
- `rakuten_searcher.py` — once API credentials are available (Product Search API at `https://api.rakutenmarketing.com/productsearch/1.0`, Bearer token auth, XML response)
- `impact_searcher.py` — once Impact account is approved
- `cj_searcher.py` — once CJ account is approved

### Brand-to-network mapping (family's wishlist, ~70 brands)

**Impact:** Target, Ulta, Kohl's, Gap/Old Navy/Banana Republic, Home Depot, Lowe's, Adidas, Shark, Crate & Barrel, Spanx, Petco, PetSmart, Dick's, Dyson, EverEve

**CJ Affiliate:** Macy's, Nike (US), American Eagle/Aerie, J.Crew, Madewell, Columbia, North Face, Kiehl's, Lowe's

**Rakuten:** Sephora, Nordstrom, Anthropologie, Free People, Urban Outfitters, Coach, ASOS, West Elm, H&M

**Awin:** Etsy, UGG, Lululemon, H&M (EU), Portland Leather

**Pepperjam/Partnerize:** Apple, Everlane, BaubleBar (20% commission!), Bombas (10%), Quince, David Yurman, Aeropostale

**AvantLink:** REI, Patagonia

**In-house/Other:** Walmart (own program + Walmart Creator), Zara (Captiv8 only), Bath & Body Works (CPX Advertising), Victoria's Secret (Skimlinks/DCMnetwork)

**No affiliate program:** Brandy Melville, Aritzia, IKEA (no US program), Gymshark (closed — invite-only athletes now)

**Too niche for major networks (Skimlinks best shot):** Garage, Pink Palm Puff, Dandy Worldwide, Custom Collective, Comfrt, Way of Wade

## Business Model & Revenue Architecture

### Revenue Streams (Priority Order)

**1. Affiliate Revenue (Primary — optimize relentlessly)**
Every product recommendation is an affiliate link opportunity. Revenue per click varies by source:
- Amazon Associates: 1-4% commission (lowest, but highest conversion)
- Etsy Affiliates (via Awin): ~4-5% commission
- Skimlinks merchants: varies, but 25% cut to Skimlinks
- Awin merchants: 5-10% depending on advertiser
- eBay Partner Network: 1-4%

**Key insight: Multi-retailer diversity is a revenue multiplier.** Etsy/Awin products earn 2-5x the commission of Amazon per sale. Every architectural decision that improves non-Amazon representation directly increases revenue. Never optimize for one retailer — the system should surface the best gift from the best source, which naturally favors higher-commission retailers for niche/personalized products.

**Affiliate implementation rules:**
- All product URLs must pass through affiliate link wrapping before display
- Track click-through rate and conversion rate per source_domain — this data drives retailer prioritization
- If a retailer's API breaks (Etsy 403, Awin 500), treat it as a revenue emergency, not just a feature bug
- Never let affiliate optimization override gift quality — users who get bad recommendations don't come back, and retention is worth more than any single commission

**2. Subscription Tiers (Secondary — builds recurring revenue)**
- Free tier: 1-2 profiles/month, Amazon-only results
- Paid tier ($5-10/mo or $30-50/year): Unlimited profiles, multi-retailer (Etsy, eBay, Awin), saved profiles, refresh reminders
- Anchor annual pricing to gifting seasons (Christmas, Valentine's, Mother's/Father's Day)
- The profile is the retention asset — saved profiles with "refresh before their birthday" notifications create repeat usage

**3. Corporate/B2B (Future — highest ceiling)**
- Corporate gifting is a $300B+ market with terrible personalization
- A version ingesting LinkedIn + social signals for corporate-appropriate recommendations
- relationship_rules.py already handles "coworker" and "acquaintance" appropriateness tiers
- This is a separate product, not a feature of the consumer app

### Revenue-Aware Development Principles

When making any architectural decision, apply this framework:

**Does this change affect click-through rate?**
- Thumbnails directly impact CTR. A product with a real image gets 3-5x more clicks than a placeholder. Thumbnail fixes are revenue fixes.
- Product descriptions (why_perfect) drive purchase intent. Generic "they'll love this" descriptions don't convert. Evidence-based descriptions ("Based on their 47 Taylor Swift TikToks...") create confidence to click and buy.
- Dead links are lost revenue. Every 404 is a user who was ready to buy and bounced.

**Does this change affect source diversity?**
- More Etsy/Awin/eBay in the output = higher average commission per click
- Amazon should be a quality fallback, not the default — it has the lowest commission rate
- Source diversity also improves perceived value for paying subscribers ("I can't find these on Amazon myself")

**Does this change affect retention?**
- Saved profiles are the retention flywheel. Features that make profiles more useful over time (refresh, comparison, history) increase lifetime value.
- Recommendation quality is the #1 retention driver. One "how did it know?!" moment creates a repeat customer. One set of generic gifts creates a churned user.
- Session cost matters: two Claude Sonnet calls + retailer APIs = ~$0.05-0.10 per session. Affiliate or subscription revenue must exceed this. Don't add API calls without considering unit economics.

### Metrics That Matter (When Analytics Are Implemented)
- **Affiliate CTR**: % of displayed products that get clicked → target >25%
- **Source diversity ratio**: % of final recommendations that are non-Amazon → target >40%
- **Thumbnail success rate**: % of products with real images (not placeholders) → target >85%
- **Profile reuse rate**: % of users who run recommendations for a saved profile again → retention signal
- **Session cost**: Total API spend per recommendation session → keep under $0.15

## Technical Architecture Notes

### Key Files
- `giftwise_app.py` — Main app (~2800 lines), orchestrates the full pipeline
- `profile_analyzer.py` — Claude call #1: social data → structured profile
- `gift_curator.py` — Claude call #2: profile + inventory → curated recommendations
- `post_curation_cleanup.py` — Programmatic enforcement of diversity rules (brand, category, interest, source)
- `enrichment_engine.py` — Static intelligence layer (do_buy/dont_buy per interest, demographics, trending)
- `multi_retailer_searcher.py` — Orchestrates all retailer searches, merges inventory pool. Order: Database → Etsy → Awin → eBay → ShareASale → Skimlinks → Amazon
- `rapidapi_amazon_searcher.py`, `ebay_searcher.py`, `etsy_searcher.py`, `awin_searcher.py`, `skimlinks_searcher.py`, `cj_searcher.py` — Per-retailer search modules
- `smart_filters.py` — Work exclusion, passive/active filtering
- `image_fetcher.py` — Thumbnail validation and fallback chain
- `relationship_rules.py` — Relationship-appropriate gift guidance (disabled as hard filter, used as soft curator guidance)
- **`database.py`** — SQLite product catalog with CRUD operations, profile caching, stats
- **`config.py`** — Centralized configuration (API credentials, refresh settings, feature flags, pricing tiers)
- **`models.py`** — Product and Profile dataclasses for type safety
- **`products/ingestion.py`** — Product database refresh logic for all retailers
- **`products/refresh.py`** — CLI entry point for automated daily refresh

### Searcher module pattern
Each searcher exports a `search_products_<source>()` function returning a list of product dicts with keys: `title`, `link`, `snippet`, `image`, `thumbnail`, `image_url`, `source_domain`, `search_query`, `interest_match`, `priority`, `price`, `product_id`. The multi_retailer_searcher orchestrates them all and merges into an inventory pool.

### Patterns to Follow
- Images are resolved programmatically from inventory, never from curator LLM output
- Products are interleaved by source before the curator sees them (no positional bias)
- post_curation_cleanup.py is the enforcement layer — if a rule must be guaranteed, enforce it there, not in the prompt
- Prompts are for quality and judgment. Code is for rules and guarantees. Never rely on a prompt to do what code can enforce.
- Snippets must describe the product, not just the seller. "Carbon steel wok, 14-inch, flat bottom" beats "From ThaiKitchenStore".
- Curator gets 14 candidates, cleanup trims to 10. This gives cleanup room to enforce diversity without falling short.

### Patterns to Avoid
- Don't route structured data (URLs, image links, prices) through LLM prompts — they corrupt it
- Don't add "CRITICAL" to every prompt instruction — when everything is critical, nothing is
- Don't add API calls without considering per-session cost
- Don't hard-filter products before curation unless absolutely necessary (kills diversity). Prefer soft guidance in the prompt + programmatic cleanup after.
- Don't build features that only work for one retailer. Every feature should degrade gracefully when a source is unavailable.

### Current Status of Retailer Integrations
- Amazon (RapidAPI): Active, working
- eBay (Browse API): Active, working
- Etsy (v3 API): Awaiting developer credentials
- Awin (Data Feed API): Code working, but gated — returns [] until advertisers are joined. Join at https://www.awin.com/us/search/advertiser-directory. Priority joins: Etsy, UGG, Lululemon, Portland Leather
- Skimlinks (Product Key API v2): Code complete (`skimlinks_searcher.py`), awaiting Skimlinks publisher approval. Env vars: SKIMLINKS_PUBLISHER_ID, SKIMLINKS_CLIENT_ID, SKIMLINKS_CLIENT_SECRET, SKIMLINKS_PUBLISHER_DOMAIN_ID
- ShareASale: Migrated to Awin (Oct 2025). Legacy code still present but not active.

### Gift Guide Pages (for Skimlinks approval)
Six editorial guides deployed at `/guides/<slug>`:
- `guide_beauty.html` (beauty-lover) — 15 products, links to Sephora/Nordstrom/Anthropologie/Dyson/Amazon
- `guide_music.html` (music-fan) — 12 products, links to Amazon/Etsy/Uncommon Goods/Vinyl Me Please
- `guide_home.html` (homebody) — 14 products, links to Nordstrom/Amazon/Anthropologie/Bloomingdale's/Dyson
- `guide_travel.html` (travel-obsessed) — 13 products, links to Amazon/Nordstrom/Away/REI
- `guide_dog.html` (dog-parent) — 11 products, links to Etsy/Amazon/BarkBox
- `guide_tech.html` (tech-nerd) — 12 products, links to Amazon/Best Buy/Analogue/Flipper Devices

Also added: `/privacy`, `/terms` routes and affiliate disclosure in footer.

### Product Database & Caching (Added Feb 2026)

**Problem:** Live API calls for every recommendation session creates cost risk. If site goes viral, Claude API costs could hit $3,000/month before any revenue.

**Solution:** SQLite product database refreshed nightly to cache products from all retailers. Profile caching saves 50% of Claude costs on repeat users.

**Architecture:**

1. **Database (`database.py`)**
   - SQLite at `/home/user/GiftWise/data/products.db`
   - Tables: `products` (retailer inventory), `cached_profiles` (analyzed profiles), `database_metadata` (refresh tracking)
   - Indexes on: interest_tags, retailer, in_stock, brand, category, popularity_score
   - Functions: `upsert_product()`, `search_products_by_interests()`, `cache_profile()`, `get_database_stats()`

2. **Product Ingestion (`products/ingestion.py`)**
   - Searches 50+ core interest categories across all active retailers
   - Per-retailer functions: `refresh_amazon()`, `refresh_ebay()`, `refresh_etsy()`, `refresh_awin()`, `refresh_skimlinks()`, `refresh_cj()`
   - Max 500 products per retailer to prevent runaway storage
   - Marks products stale if not seen in 7+ days
   - Cleans expired profile caches

3. **Automated Refresh**
   - **GitHub Actions:** `.github/workflows/refresh-products.yml` runs daily at 2:00 AM UTC
   - **Manual trigger:** Actions tab → "Daily Product Database Refresh" → Run workflow
   - **CLI:** `python products/refresh.py [retailer]` or `python products/refresh.py all`
   - Commits updated database back to repo after each run

4. **Admin Dashboard**
   - Route: `/admin/stats`
   - Shows: Total products, products by retailer, recently added, stale count, last refresh time, top brands
   - Template: `templates/admin_stats.html`
   - Auto-refreshes every 60 seconds

5. **Query Flow**
   - `multi_retailer_searcher.py` queries database FIRST before hitting live APIs
   - Database returns cached products matching interests
   - Live APIs fill gaps if database doesn't have enough matches
   - This reduces API calls by ~80% for common interests

6. **Profile Caching**
   - Analyzed profiles stored in `cached_profiles` table for 7 days
   - Hash-based deduplication (same social data = same profile = reuse)
   - `profile_analyzer.py` checks cache before calling Claude
   - Cuts Claude costs in half for users who regenerate recommendations

7. **Configuration (`config.py`)**
   - `REFRESH_CONFIG`: Schedule (daily), time (02:00 UTC), stale threshold (7 days), max per retailer (500)
   - `PROFILE_CACHE_TTL_DAYS`: 7 days default
   - `FEATURES['database_first']`: Query database before live APIs (default: True)
   - `FEATURES['profile_caching']`: Enable profile caching (default: True)

**Maintenance:**
- Database self-maintains via nightly GitHub Actions workflow
- No manual intervention needed
- Stale products automatically marked after 7 days
- Expired profile caches automatically cleaned
- Database size stays under control via 500-product cap per retailer

**Cost Impact:**
- Before: $0.05-0.10 per session (2 Claude calls + live APIs)
- After: $0.02-0.05 per session (50% profile cache hit rate + database queries)
- Viral scenario: $1,500/month instead of $3,000/month at 10K sessions/day

**GitHub Secrets Required:**
For automated refresh to work, set these in repository Settings → Secrets:
- `RAPIDAPI_KEY`, `RAPIDAPI_HOST` (Amazon)
- `EBAY_APP_ID`, `EBAY_CAMPAIGN_ID` (eBay)
- `ETSY_API_KEY` (Etsy - when approved)
- `AWIN_API_TOKEN`, `AWIN_PUBLISHER_ID` (Awin)
- `SKIMLINKS_PUBLISHER_ID`, `SKIMLINKS_CLIENT_ID`, `SKIMLINKS_CLIENT_SECRET`, `SKIMLINKS_PUBLISHER_DOMAIN_ID` (Skimlinks - when approved)
- `CJ_ACCOUNT_ID`, `CJ_API_KEY`, `CJ_WEBSITE_ID` (CJ - when approved)
- `ANTHROPIC_API_KEY` (Required for any Claude calls during refresh, though not used by ingestion itself)
