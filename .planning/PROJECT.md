# GiftWise

## What This Is

AI-powered gift recommendation engine. User pastes a social media handle → Flask scrapes the profile → Claude analyzes interests → searches multiple retailers → Claude curates gifts → programmatic cleanup → display with affiliate links. Live at giftwise.fit. Revenue comes from affiliate commissions on product clicks.

## Core Value

Show the right gift for THIS specific person — not a generic list — by grounding recommendations in their actual interests, posts, and aesthetic.

## Requirements

### Validated

- ✓ End-to-end pipeline: social handle → scrape → profile analysis → search → curation → display — Phase 0 (shipped)
- ✓ Three-layer intelligence: pre-LLM enrichment (ontology) + LLM taste (profile/curator) + post-LLM rules (cleanup) — Phase 0
- ✓ Multi-retailer search: Amazon, eBay, CJ Affiliate, Awin — Phase 0
- ✓ Affiliate link tracking: CJ GraphQL + Awin feeds + EPN + Amazon Associates — Phase 0
- ✓ SQLite product catalog with nightly sync (catalog_sync.py) — Phase 0
- ✓ Form-diverse DB query (search_products_diverse) — Mar 2026
- ✓ Interest attribution: third-party interest filtering, confidence scoring — Mar 2026
- ✓ Pre-filter scoring: gift_score, interest_tags, multi-interest bonus — Mar 2026
- ✓ Source diversity enforcement: 40% cap per source — Mar 2026
- ✓ CJ multi-label tagging + sync term expansion (252 → 589 terms) — Mar 2026
- ✓ Temporal signals + engagement spike detection in profile analysis — Mar 2026

### Active

- [ ] 14-item output: splurge slot wired through pipeline and displayed in UI (Sonnet portions)
- [ ] Infrastructure: remove Skimlinks dead code, fix in-flight duplicate Claude calls

### Validated in Phase 01 (2026-04-02)

- ✓ New retailer wiring: youngelectricbikes, Tayst Coffee static products added to awin_searcher.py
- ✓ VitaJuwel + VSGO placeholder links replaced with real Awin deep links (awinmid params)
- ✓ AWOL Vision + OUFER Body Jewelry catalog sync terms added (catalog_sync.py)
- ✓ Tracking fixed: per-slug guide_hit events (guide_hit:{slug}, blog_hit:{slug})

### Validated in Phase 02 (2026-04-02)

- ✓ Catalog-First source separation: live CJ GraphQL and Awin feed CSV download removed from session-time code
- ✓ eBay niche-only scoping: fires only for interests with < 5 DB products (EBAY_WEAK_COVERAGE_THRESHOLD=5, EBAY_NICHE_CAP=7)
- ✓ Circuit breaker: DB < 100 products → re-enable live CJ/Awin fallback
- ✓ CJ static partners (MonthlyClubs, Winebasket, etc.) preserved via api_key=None path
- ✓ Awin _matches_query() 2-term threshold preserved
- ✓ No eBay/Amazon DB write-back (documented in code)

### Out of Scope

- Mobile app — web-only by design
- Paywall enforcement — not until 15+ sessions/day sustained (see BUSINESS_STRATEGY.md)
- Spotify OAuth — removed, caused infinite waits/403s; text paste only
- Skimlinks — service defunct, remove dead code
- International currency — US market only for now
- Stripe wiring to gatekeeping — Stripe exists but is not enforced; leave disconnected
- Video content generation — not a product feature
- Campaign-specific promo codes — deleted 884 lines Feb 2026, do not re-add
- Etsy live API — dev credentials rejected repeatedly, returns 403 on all queries

## Context

### Pipeline Architecture

```
Social handle → Scrape (Instagram/TikTok)
  → Claude call #1: profile_analyzer.py (interests, ownership signals, aesthetic)
  → interest_ontology.py enrichment (zero cost, pre-LLM)
  → multi_retailer_searcher.py (Amazon, eBay, CJ from DB, Awin from DB)
  → revenue_optimizer.py scoring
  → Claude call #2: gift_curator.py (14 candidates → 10 + splurge + 3 experiences)
  → post_curation_cleanup.py (enforce diversity, trim to final count)
  → Display with affiliate links
```

Two Claude API calls per session (~$0.10 on Sonnet). Railway.app on permanent 50GB volume.

### Opus-Only Zones — HARD CONSTRAINT

These files/sections must NOT be modified by Sonnet. Add `# SONNET-FLAG:` and move on.

| File | Protected Sections |
|------|--------------------|
| `interest_ontology.py` | Theme clustering thresholds, gift philosophy inference, curator_briefing format |
| `gift_curator.py` | Gift reasoning framework, selection principle, synthesis, ownership section |
| `profile_analyzer.py` | Ownership signals schema, aesthetic_summary, interest type taxonomy |
| `post_curation_cleanup.py` | Brand relaxation rules, uncategorized near-dedup, source diversity caps |

Safe for Sonnet: bug fixes, template/CSS, API response handling, adding category/brand patterns, adding entries to INTEREST_ATTRIBUTES, logging, adding new static retailer product lists, adding advertiser IDs to catalog sync.

### Key Files

| File | Purpose |
|------|---------|
| `giftwise_app.py` | Main Flask app, routes, orchestration |
| `recommendation_service.py` | Pipeline orchestrator |
| `profile_analyzer.py` | Claude call #1 — OPUS ZONE for prompt |
| `gift_curator.py` | Claude call #2 — OPUS ZONE for prompt |
| `post_curation_cleanup.py` | Programmatic diversity enforcement — OPUS ZONE for brand/source caps |
| `interest_ontology.py` | Pre-LLM thematic enrichment — OPUS ZONE |
| `multi_retailer_searcher.py` | Orchestrates all retailer searches |
| `cj_searcher.py` | CJ Affiliate GraphQL + 15+ static partner lists |
| `awin_searcher.py` | Awin feed search + static partner lists |
| `catalog_sync.py` | Nightly sync: CJ + Awin → SQLite DB |
| `database.py` | SQLite product catalog, click tracking, search functions |
| `revenue_optimizer.py` | Pre-filter scoring (gift_score + interest matching) |
| `models.py` | Product dataclass, to_curator_format() |
| `smart_filters.py` | Work exclusion, passive/active, obsolete format filtering |

### Retailer Status

| Retailer | Type | Commission | Notes |
|----------|------|-----------|-------|
| Amazon | Live-only (no DB) | 1-4% | ~20 products/run |
| eBay | Live-only (no DB) | 1-4% | ~12 products/run, EPN campaign params |
| CJ Affiliate | DB (nightly sync) | varies | 589 sync terms, GraphQL, 15+ static partners |
| Awin | DB (nightly sync) | varies | 20 confirmed merchants, 13 with feeds |
| Etsy | BLOCKED | — | 403 on all queries, do not call |
| Skimlinks | DEFUNCT | — | Dead code, remove when possible |

**Active Awin feed merchants (advertiser IDs):** Crown and Paw (57823), LoveIsARose (96879), Formulary 55 (86831), Dylan's Candy Bar (61247), Matr Boomie (96117), Maison Balzac (100137), Promeed, Prosto Concept, King Koil, Nextrition Pet, Ravin Crossbows

**Pending Awin wiring (approved but not yet in sync):** AWOL Vision (98169), OUFER Body Jewelry (91941)

**Awin static (no feed):** youngelectricbikes (120209), Tayst Coffee (90529), VitaJuwel (97077), VSGO, Woven Woven, Gourmet Gift Basket Store, Goldia.com, OUTFITR

**Still need to apply:** Uncommon Goods, Personalization Mall, Things Remembered, Oriental Trading, HomeWetBar (all on Awin via ShareASale migration)

### Deployment

- **Platform:** Railway.app, permanent 50GB volume (data persists across deploys)
- **Auto-deploy:** pushes to `main` trigger Railway deployment
- **Start:** `gunicorn giftwise_app:app --bind 0.0.0.0:$PORT --workers 3 --timeout 600`
- **Admin dashboard:** `/admin/stats?key=ADMIN_DASHBOARD_KEY`
- **Models:** `CLAUDE_PROFILE_MODEL` (default Sonnet), `CLAUDE_CURATOR_MODEL` (default Sonnet, set Opus to test quality)
- **Domain:** giftwise.fit (NOT giftwise.me, NOT giftwise.app)

### Known Issues / Technical Debt

- Live CJ GraphQL calls still fire during sessions (redundant — DB has 589 sync terms)
- Live Awin feed downloads still fire as fallback during sessions (redundant — DB is populated)
- eBay runs for ALL interests, not just those with weak DB coverage
- Skimlinks JS snippet still in templates (defunct service)
- `skimlinks_searcher.py` is dead code
- In-flight duplicate Claude API calls — same profile hash can fire two concurrent Claude requests
- 3 Etsy guide templates have placeholder content (`[Add product image URL]`, `[ETSY AFFILIATE LINK]`)
- All guide CTAs point to `/signup` — should point to `/demo` for lower friction
- No per-guide event tracking (all aggregate into one `guide_hit` counter)
- VitaJuwel and VSGO have placeholder Awin URLs, not real deep links

### Traffic & Revenue Context

- Current: likely < 5 sessions/day (growth phase — full free access)
- Paywall trigger: 15+ sessions/day sustained
- Affiliate revenue: $0.00-$0.05/session (most visitors don't convert; commissions only on purchases)
- Claude cost: ~$0.10/session on Sonnet
- Guide traffic significantly outpaces tool usage (`guide_hit >> rec_run` in admin stats)

## Constraints

- **Opus-only zones:** Prompt files (gift_curator.py, profile_analyzer.py) and specific logic in interest_ontology.py and post_curation_cleanup.py — Sonnet must not modify these sections
- **No hard filtering before curation:** Products must not be filtered before the curator sees them; use soft guidance + post-curation cleanup
- **Route structured data (URLs, images, prices) around LLMs**, not through them — LLMs corrupt structured data
- **Search queries capped at 5 words** — prevents eBay 400 errors (enforced in search_query_utils.py)
- **Awin `_matches_query()` 2-term threshold must not be removed or weakened** — prevents $800 scooter incidents
- **REPLACEMENT_PRICE_THRESHOLD $120 unchanged** — post-curation backfill gate
- **main branch = production** — all work on feature branches, merge via GitHub PR
- **No eBay/Amazon DB write-back** — these are live-only sources; only CJ/Awin go in the DB

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Catalog-first architecture (CJ/Awin from DB, eBay/Amazon live) | Eliminates cache pollution, enables nightly sync, reduces session latency | ✓ Good — Phase 2 of implementation in progress |
| Two-Claude-call pipeline (profile + curator) | Separation of concerns: profiling vs. taste judgment | ✓ Good — ~$0.10/session on Sonnet |
| SQLite on Railway permanent volume | Simple, no infra overhead, persists across deploys | ✓ Good — WAL mode enabled |
| Opus-only zones for prompt logic | Prevents quality regressions from Sonnet modifying judgment prompts | ✓ Good |
| No paywall until 15+/day | Need traffic before monetization; affiliate revenue doesn't require friction | — Pending validation |
| Curator gets 14 candidates, cleanup trims to final count | Gives curator room to choose; programmatic rules enforce guarantees | ✓ Good |
| Ownership signals flow end-to-end | Profile detects → dict carries → curator sees → avoids duplicate gifts | ✓ Good |
| eBay/Amazon not written to DB | Prevents marketplace product pollution and stale listing tracking | ✓ Good |
| guide_hit CTAs → /demo not /signup | Lower friction; collect users at tool not at registration wall | — Pending implementation |

---
*Last updated: 2026-04-01 after GSD project initialization*
