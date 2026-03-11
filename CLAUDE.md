# GiftWise

## What This Is

AI-powered gift recommendation engine. Users paste a social media handle → Flask scrapes their profile → Claude analyzes interests → searches multiple retailers → Claude curates gifts → programmatic cleanup → display with affiliate links.

Live at **giftwise.fit**. Revenue comes from affiliate commissions on product clicks.

## Non-Goals

Do not build, suggest, or scope-creep into:
- Mobile app (web-only)
- Nonprofit/charity fundraising features
- International currency support
- Automated social media posting
- Video content generation
- Campaign-specific promo code (Valentine's lesson — 884 lines deleted)
- Skimlinks integration (service is defunct)
- Spotify OAuth (removed — caused infinite waits/403s; text paste only now)
- Paywall enforcement (not until traffic thresholds are met — see `docs/BUSINESS_STRATEGY.md`)

## Pipeline

```
Social handle → Scrape (Instagram/TikTok)
  → Claude call #1: profile_analyzer.py (interests, ownership signals, aesthetic)
  → interest_ontology.py enrichment (zero cost, pre-LLM)
  → multi_retailer_searcher.py (Amazon, eBay, CJ, Awin, Etsy)
  → revenue_optimizer.py scoring
  → Claude call #2: gift_curator.py (14 candidates)
  → post_curation_cleanup.py (trim to 10, enforce diversity)
  → Display with affiliate links
```

Two Claude API calls per session. ~$0.10 on Sonnet, ~$0.25-0.50 on Opus.

## Key Files

| File | Purpose |
|------|---------|
| `giftwise_app.py` | Main Flask app, routes, orchestration |
| `recommendation_service.py` | Pipeline orchestrator (profile → search → curate) |
| `profile_analyzer.py` | Claude call #1: social data → structured profile |
| `gift_curator.py` | Claude call #2: profile + inventory → curated gifts |
| `post_curation_cleanup.py` | Programmatic diversity enforcement (brand, category, interest, source) |
| `interest_ontology.py` | Pre-LLM thematic enrichment (zero API cost) |
| `multi_retailer_searcher.py` | Orchestrates all retailer searches |
| `cj_searcher.py` | CJ Affiliate GraphQL + 15+ static partner lists |
| `awin_searcher.py` | Awin feed search + static partner lists |
| `smart_filters.py` | Work exclusion, passive/active, obsolete format filtering |
| `search_query_utils.py` | Query building, 5-word cap, category suffixes |
| `database.py` | SQLite product catalog, click tracking |
| `storage_service.py` | Shelve-backed key-value store |
| `site_stats.py` | Admin dashboard event counter |

## Three-Layer Intelligence Architecture

**Understand this before modifying any recommendation logic.**

| Layer | Files | Role | Cost |
|-------|-------|------|------|
| Pre-LLM code | `interest_ontology.py`, `enrichment_engine.py`, `revenue_optimizer.py`, `search_query_utils.py` | Enrichment, scoring, query building | Free |
| LLM prompts | `profile_analyzer.py`, `gift_curator.py` | Taste, judgment, reasoning | ~$0.10/session |
| Post-LLM code | `post_curation_cleanup.py`, `smart_filters.py` | Rules, guarantees, diversity enforcement | Free |

**Key balances:**
- **Prompts for taste, code for rules.** The curator prompt guides judgment. Code enforces guarantees (no duplicate brands in same category, max 2 per interest). Never flip this.
- **Ontology enriches, never filters.** It adds context to the curator prompt. It never removes products.
- **Brand dedup is relaxed intentionally.** Same brand CAN appear twice if categories differ (e.g., Taylor Swift poster + enamel pin).
- **Search queries capped at 5 words.** Prevents eBay 400 errors.
- **Ownership signals flow end-to-end.** Profile analyzer detects → profile dict carries → curator prompt shows → curator avoids duplicates.

## Opus-Only Zones

Files marked `⚠️ OPUS-ONLY ZONE` in code. Non-Opus sessions: add a `# SONNET-FLAG:` comment and move on.

| File | Protected Sections |
|------|--------------------|
| `interest_ontology.py` | Theme clustering thresholds, gift philosophy inference, curator_briefing format |
| `gift_curator.py` | Gift reasoning framework, selection principle, synthesis, ownership section |
| `profile_analyzer.py` | Ownership signals schema, aesthetic_summary, interest type taxonomy |
| `post_curation_cleanup.py` | Brand relaxation rules, uncategorized near-dedup, source diversity caps |

**Safe for any session:** Bug fixes, template/CSS, API response handling, adding new category/brand patterns, adding entries to INTEREST_ATTRIBUTES, logging.

## Development Rules

**Do:**
- Wire everything end-to-end. If you create a template, add the route. If you add a module, wire imports.
- Images resolved programmatically from inventory, never from curator LLM output.
- Products interleaved by source before curator sees them (no positional bias).
- Prioritize high-commission sources (CJ, Awin, eBay) over Amazon (1-4%).
- Curator gets 14 candidates, cleanup trims to 10.
- Check token budget before adding prompt instructions (~255 tokens = ~$0.0008). Don't add 500+ without trimming elsewhere.

**Don't:**
- Route structured data (URLs, images, prices) through LLM prompts — they corrupt it.
- Add "CRITICAL" to every prompt instruction.
- Hard-filter products before curation (kills diversity). Prefer soft prompt guidance + post-curation cleanup.
- Build features that only work for one retailer.
- Add code filters for taste problems. If curator makes bad judgment calls, fix the prompt.
- Build campaign-specific code.

## Environment & Deployment

- **Platform:** Railway.app (NOT Render, NOT Heroku)
- **Auto-deploy:** Pushes to `main` trigger deployment. **Merges to main must happen via GitHub PR.**
- **Storage:** Railway Pro, 50GB permanent volume. Data persists across deploys. NOT ephemeral.
- **Workers:** 3 Gunicorn sync workers, 600s timeout
- **Config:** `railway.json` (Nixpacks builder)
- **Start:** `gunicorn giftwise_app:app --bind 0.0.0.0:$PORT --workers 3 --timeout 600 --graceful-timeout 120 --worker-class sync --log-level info`
- **Domain:** giftwise.fit
- **Git is installed and working.** Do not prompt to install tooling.

**Model env vars:**
- `CLAUDE_PROFILE_MODEL` — default Sonnet
- `CLAUDE_CURATOR_MODEL` — default Sonnet (set to Opus to test quality)

**Testing locally:**
```bash
python giftwise_app.py
# http://localhost:5000/demo          — fake data
# http://localhost:5000/demo?admin=true — real pipeline with @chadahren
```

**Admin dashboard:** `/admin/stats?key=ADMIN_DASHBOARD_KEY`

## Debugging Approach

> Vary the layer (client vs server vs network vs deploy). Ask for one high-leverage signal (console errors or Network tab). Cheap broad checks first. If stuck, change strategy.

1. Name at least two layers before digging deep.
2. Console errors → Network tab → emitted JS → session state → workers → architecture.
3. Templates that emit JS are a hidden risk surface (Jinja2 inside `<script>` blocks).
4. After fixing, record what you checked and in what order.

## Current Priorities (Updated Mar 2026)

1. **Awin approvals** — ~35 applications from Feb 25 pending. Check dashboard for new approvals.
2. **FlexOffers** — Applied Feb 16, status unknown. Check dashboard.
3. **Impact.com** — Account type issue, second ticket filed. STAT tag + verification phrase on branch `claude/review-claude-docs-kEdui` (merge to main to activate).
4. **Load test & harden** — Shelve concurrency, Gunicorn worker exhaustion, SQLite write contention under concurrent load. See Opus prompt in `docs/ARCHITECTURE.md`.
5. **Monitor quality** — Admin dashboard, watch rec_run and affiliate click events.
6. **TikTok launch content** — Video in progress (CapCut).

## Retailer Status

| Retailer | Status |
|----------|--------|
| Amazon (RapidAPI) | Active |
| eBay (Browse API + EPN) | Active |
| CJ Affiliate (GraphQL + 15 static partners) | Active |
| Awin (13 confirmed merchants, ~35 pending) | Active, expanding |
| Etsy (v3 API) | Blocked — awaiting dev credentials |
| Skimlinks | DEFUNCT — dead code, remove when convenient |
| Impact.com | Blocked — account type issue |
| FlexOffers | Applied, status unknown |
| Rakuten | Account active, need to apply to brands |

For detailed affiliate partner lists, commissions, and application status, see `docs/AFFILIATE_STATUS.md`.

## Reference Docs

Don't load these every session. Read only when the task requires it.

| Doc | When to read |
|-----|-------------|
| `docs/AFFILIATE_STATUS.md` | Working on affiliate integrations, adding partners |
| `docs/ARCHITECTURE.md` | Deep technical work, load testing, the Opus audit prompt |
| `docs/TESTING.md` | Running tests, pre-deploy verification |
| `docs/BUSINESS_STRATEGY.md` | Paywall decisions, revenue model, subscription tiers |
| `OPUS_AUDIT.md` | Quality review, checking audit item status |
