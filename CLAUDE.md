# GiftWise — Project Intelligence

AI-powered gift recommendation engine. User pastes a social handle → Flask scrapes → Claude analyzes → multi-retailer search → Claude curates → programmatic cleanup → display with affiliate links. Live at **giftwise.fit**. Revenue from affiliate commissions.

---

## 🔄 Session Handoff — April 22, 2026

**Active branch:** `claude/fix-splurge-durability-gate` (1 commit ahead of main, pushed).

**Just shipped:** Splurge durability gate — `passionate + rising → light` in `signal_weight`, and the splurge section of `_IDEATOR_PROMPT` now prohibits rising signals categorically. Root cause of the NASA-travel-concept bug: the ladder granted `moderate` signals a hedge-and-proceed option at splurge price points, giving the model a rationalization path.

**This session:** Rewriting CLAUDE.md using context engineering principles. Target: ~30-40% of prior length, first 20% = everything Claude needs to start working.

**Pre-existing (not blocking):**
- Session cookie overflow: 4400+ bytes vs 4093 limit — browsers may silently discard.
- Duplicate in-flight profile analysis calls when two workers hit the same profile hash.

---

## Start-of-session protocol

1. Read the session handoff above and the **READY** items in Current Priorities.
2. If the user hasn't named a task, surface the top 3 READY items.
3. For any debug task, read **Debugging Approach** before touching code.
4. For any code change, follow **Fix Verification Protocol** — no exceptions.

---

## Debugging Approach (read before every debug session)

This codebase is complex enough that locking onto one layer wastes hours. The generation-POST bug is the canonical example: looked like threads, then service workers, then sessions — actual cause was a single apostrophe in a template.

**1. Vary the layer before going deep.** Name at least two layers before digging: client (JS, DOM, console) vs server (route, session, worker) vs network (request never sent, redirect, CORS) vs build/deploy (stale asset, wrong branch, env var). Ask: "What's the smallest thing that could explain this?" Often it's one character in a template.

**2. Ask for the highest-leverage signal first.** Don't ask for a full log dump. Ask the one question that rules out a category:
- "DevTools → Console. Any red errors? Exact first line?"
- "Network tab — does the request to `/api/...` appear at all?"
- "When did it last work? Last commit touching this flow?"

**3. Cheap, broad checks before deep ones.** Order: console errors → Network tab → JS parse errors → session/cookie state → worker/thread → architecture. Don't reverse.

**4. If stuck, change the search strategy.** Server-side not paying off after 2-3 cycles? Switch to client parse error, cached script, redirect. Focused on one file? Check the template/caller that embeds it.

**5. Templates that emit JS are a hidden risk surface.** Jinja variables inside `<script>` blocks break the entire script with one character. Single-quoted strings containing apostrophes (`'We're'`, `'don't'`) are the classic failure — the apostrophe ends the string, the rest is parsed as an identifier, script never runs. Ask for the **first line in the browser Console** when a script silently does nothing. Prefer `tojson` or `data-*` attributes over inline Jinja substitutions inside JS.

**6. Record what you checked, in what order.** One line in the fix note trains the next session.

---

## Fix Verification Protocol (required for every code change)

Claude's failure mode: pattern-matching symptoms to plausible causes and presenting fixes that don't work or regress other paths.

1. **Prove the bug before fixing.** Show the exact line and trace real data through it: "This input → this function → this output, here's why that's wrong." If you can't, say you're guessing.
2. **Reproduce the failure.** Test case, trace, or concrete example with real values.
3. **One fix per commit, tested individually.** Don't bundle three fixes; when one regresses you won't know which.
4. **"What could this break?"** List callers and downstream consumers. Trace the impact.
5. **Dry-run with real data.** Log diffs beat code review. Simulate: "For msmollygmartin's 'fly fishing', old produces [X], new produces [Y]."
6. **Flag uncertainty honestly.** "Plausible cause" unless you've completed 1-2. Reserve "root cause" for verified fixes.
7. **Verify after deploy.** Check logs, run the flow, confirm the symptom is gone.

---

## Pipeline

```
Social handle → Scrape (Instagram/TikTok)
  → Claude call #1: profile_analyzer.py (interests, ownership signals, aesthetic)
  → interest_ontology.py enrichment (zero cost, pre-LLM)
  → multi_retailer_searcher.py (Amazon, eBay, CJ, Awin)
  → revenue_optimizer.py scoring
  → Claude call #2: gift_curator.py + gift_ideator.py (14 items: 10 regular + 1 splurge + 3 experiences)
  → post_curation_cleanup.py (trim, enforce diversity)
  → Display with affiliate links
```

Two Claude API calls per session. ~$0.10 on Sonnet, ~$0.25-0.50 on Opus.

## Key Files

| File | Purpose |
|------|---------|
| `giftwise_app.py` | Flask app, routes, orchestration |
| `recommendation_service.py` | Pipeline orchestrator |
| `profile_analyzer.py` | Claude call #1: social → structured profile |
| `gift_curator.py` | Claude call #2: profile + inventory → curated gifts |
| `gift_ideator.py` | Evidence-based ideator (concepts, splurge, amalgam, portrait) |
| `post_curation_cleanup.py` | Diversity enforcement (brand, category, interest, source) |
| `interest_ontology.py` | Pre-LLM thematic enrichment |
| `multi_retailer_searcher.py` | Orchestrates retailer searches |
| `cj_searcher.py` | CJ Affiliate GraphQL + static partners |
| `awin_searcher.py` | Awin feed + static partners |
| `smart_filters.py` | Work exclusion, passive/active, obsolete format filtering |
| `search_query_utils.py` | Query building, 5-word cap, category suffixes |
| `database.py` | SQLite catalog, click tracking |
| `storage_service.py` | Shelve-backed KV store |
| `catalog_sync.py` | Nightly CJ/Awin sync into DB |
| `site_stats.py` | Admin dashboard event counter |

---

## Three-Layer Intelligence Architecture

**Understand this before modifying any recommendation logic.**

| Layer | Files | Role | Cost |
|-------|-------|------|------|
| Pre-LLM code | `interest_ontology.py`, `enrichment_engine.py`, `revenue_optimizer.py`, `search_query_utils.py` | Enrichment, scoring, query building | Free |
| LLM prompts | `profile_analyzer.py`, `gift_curator.py`, `gift_ideator.py` | Taste, judgment, reasoning | ~$0.10/session |
| Post-LLM code | `post_curation_cleanup.py`, `smart_filters.py` | Rules, guarantees, diversity enforcement | Free |

**Key balances:**
- **Prompts for taste, code for rules.** The curator prompt guides judgment. Code enforces guarantees (no duplicate brands in same category, max 2 per interest). Never flip this.
- **Ontology enriches, never filters.** It adds context to the curator prompt; it never removes products.
- **Brand dedup is relaxed intentionally.** Same brand CAN appear twice if categories differ.
- **Search queries capped at 5 words.** Prevents eBay 400 errors.
- **Ownership signals flow end-to-end.** Profile analyzer detects → profile dict carries → curator prompt shows → curator avoids duplicates.

## Opus-Only Zones

Files marked `⚠️ OPUS-ONLY ZONE` in code. Non-Opus sessions: add a `# SONNET-FLAG:` comment and move on.

| File | Protected sections |
|------|-------------------|
| `interest_ontology.py` | Theme clustering thresholds, gift philosophy inference, curator_briefing format |
| `gift_curator.py` | Gift reasoning framework, selection principle, synthesis, ownership section |
| `gift_ideator.py` | Signal-weight ladder, durability gate, splurge rules, concept prompts |
| `profile_analyzer.py` | Ownership signals schema, aesthetic_summary, interest type taxonomy |
| `post_curation_cleanup.py` | Brand relaxation rules, uncategorized near-dedup, source diversity caps |

**Safe for any session:** Bug fixes, template/CSS, API response handling, adding category/brand patterns, adding INTEREST_ATTRIBUTES entries, logging.

---

## Development Rules

**Do:**
- Wire everything end-to-end. New template → add the route. New module → wire imports.
- Resolve images programmatically from inventory, never from curator LLM output.
- Interleave products by source before the curator sees them (no positional bias).
- Prioritize high-commission sources (CJ, Awin, eBay) over Amazon (1-4%).
- Curator gets 14 candidates, cleanup trims to 10 (+1 splurge +3 experiences).
- Check token budget before adding prompt instructions (~255 tokens ≈ $0.0008).

**Don't:**
- Route structured data (URLs, images, prices) through LLM prompts — they corrupt it.
- Add "CRITICAL" to every prompt instruction.
- Hard-filter products before curation (kills diversity). Prefer soft prompt guidance + post-curation cleanup.
- Build features that only work for one retailer.
- Add code filters for taste problems. Bad judgment calls → fix the prompt.
- Build campaign-specific code.

---

## Environment & Deployment

- **Git is installed and working.** Do not prompt the user to install tooling.
- **Python/Flask.** Run with `python giftwise_app.py`. No special build step.
- **Branch:** `git branch` before changes. **Merges to `main` happen via GitHub PR** — Railway watches `main` for auto-deploy.
- **Domain:** giftwise.fit (NOT .me, .app, .com).
- **Platform:** Railway.app. Config in `railway.json`. Start command uses Gunicorn sync, 3 workers, 600s timeout.
- **Storage:** Railway Pro with a **50GB permanent volume** — SQLite and shelve persist across deploys. **Do NOT suggest ephemeral filesystem as a cause of data loss.**
- **Model env vars:** `CLAUDE_PROFILE_MODEL`, `CLAUDE_CURATOR_MODEL` (defaults Sonnet).
- **Admin dashboard:** `/admin/stats?key=ADMIN_DASHBOARD_KEY`.

**Test locally:**
```
python giftwise_app.py
# http://localhost:5000/demo               — fake data
# http://localhost:5000/demo?admin=true    — real pipeline (@chadahren)
```

**Test a branch without touching production:** Railway → Deployments → Deploy from branch → use the temp URL. Rollback: Deployments → Redeploy an earlier version.

**Always test locally or in a Railway preview first** when changing routes, the search/curation pipeline, database/storage, or environment variables. Template text, prompt tweaks, and static guide/blog changes are safe to merge directly.

---

## Non-Goals

Do not build, suggest, or scope-creep into:
- Mobile app (web-only)
- Nonprofit/charity features
- International currency
- Automated social posting
- Video generation
- Campaign-specific promo code (Valentine's lesson — 884 lines deleted)
- Skimlinks (defunct)
- Spotify OAuth (removed — caused infinite waits/403s)
- Paywall enforcement (not until thresholds met — see `docs/BUSINESS_STRATEGY.md`)

---

## Current Priorities (Apr 22, 2026)

### READY — execute now

| # | Task | Notes |
|---|------|-------|
| 1 | **Merge `claude/fix-splurge-durability-gate` to main** | Splurge gate fix. Open PR when ready. |
| 2 | **Take down 3 placeholder Etsy guides** | `guide_etsy_home_decor.html`, `guide_etsy_jewelry.html`, `guide_etsy_under_50.html`. Add 301s → `/guides/gifts-for-her` or `/guides`. Remove from sitemap. |
| 3 | **Drop Russell Stover + GameFly from CJ sync** | Exclusion list in `catalog_sync.py`. |
| 4 | **Block King Koil in Awin** | Exclusion list in `awin_searcher.py`. |
| 5 | **Reddit Wave 2** | Manual DMs/comments on r/GiftIdeas and r/gifts. API credentials still pending. |
| 6 | **14-Item Phase 2 (Sonnet-safe)** | Splurge-tile UI in `recommendations.html`; eBay niche-only scoping in `multi_retailer_searcher.py` (use `per_interest_counts` to target weak-coverage interests only). |
| 7 | **Catalog-First Phase 2** | Remove live CJ/Awin from session-time paths; retune source diversity caps. See `docs/ARCHITECTURE.md`. |

### BLOCKED — waiting on external party

| Task | Blocker |
|------|---------|
| Reddit scout automation | Reddit API credentials |
| OG default image | User to create 1200×630 `static/images/og-default.png` |
| Awin approvals | ~35 applications pending since Feb 25 |
| FlexOffers / Impact.com / Rakuten | Approvals / account issues — see `docs/AFFILIATE_STATUS.md` |

### NEXT — ready after one prerequisite

| Task | Prerequisite |
|------|--------------|
| Splurge curator prompt (14-item Phase 2) | Opus session in `gift_curator.py` / `gift_ideator.py` |
| Experience booking link monetization | Awin/CJ approvals (Sur La Table, ClassPass, Viator) |
| Load test & harden | ~15 sessions/day. Opus prompt in `docs/ARCHITECTURE.md`. |

### MONITOR — no action, just watch

| Signal | Where |
|--------|-------|
| Session count | Railway Metrics → Requests ÷ 7 |
| Affiliate clicks | `/admin/stats` retailer breakdown |
| Source diversity | Logs → "Product source breakdown:" (any source > 40% warrants investigation) |
| Duplicate in-flight Claude calls | Logs → duplicate profile hash |

---

## Retailer Status

| Retailer | Status |
|----------|--------|
| Amazon (RapidAPI) | Active |
| eBay (Browse API + EPN) | Active |
| CJ Affiliate | Active (GraphQL + 15 static partners) |
| Awin | Active, 13 confirmed, ~35 pending |
| Etsy | **Blocked** — dev credentials rejected, 403 on all queries |
| Skimlinks | **Defunct** — dead code, remove when convenient |
| Impact.com | Blocked — account type issue |
| FlexOffers | Applied, status unknown |
| Rakuten | Account active, need brand applications |

Detailed partner lists, commissions, applications → `docs/AFFILIATE_STATUS.md`.

---

## 14-Item Output (current state)

Output: 10 regular gifts + 1 splurge + 3 experiences = 14 items.

**Phase 1 done:** MECE product-form taxonomy (37 categories, 8 form classes); DB write-back removed from eBay/Amazon; category populated at sync time; price tiers restructured (`SPLURGE_PRICE_MIN=200`, `SPLURGE_PRICE_MAX=1500`); form-diverse DB query (`search_products_diverse()`).

**Phase 2 open:** Curator prompt `rec_count` 10 → 11; splurge-tile UI; eBay niche-only scoping; experience booking provider monetization (zero approved partners today). Splurge ceiling informed by profile `budget_category`: budget $300, moderate $500, premium $1000, luxury $1500, unknown $500.

---

## Reference Docs

Don't load these every session. Read only when the task requires it.

| Doc | When to read |
|-----|--------------|
| `docs/AFFILIATE_STATUS.md` | Affiliate integrations, adding partners |
| `docs/ARCHITECTURE.md` | Deep technical work, load testing, Opus audit prompt |
| `docs/TESTING.md` | Running tests, pre-deploy verification |
| `docs/BUSINESS_STRATEGY.md` | Paywall decisions, revenue model, subscription tiers |
| `docs/OPUS_AUDIT.md` | Quality review, audit item status |
| `docs/VOICE.md` | Writing guide/blog content, Reddit outreach, any copy |
| `docs/AFFILIATE_APPLICATIONS_TRACKER.md` | Application status across networks |
| `docs/AWIN_APPLICATIONS_FEB25.md` | Awin tiers, EPC, post-approval wiring |
| `docs/AFFILIATE_NETWORK_RESEARCH.md` | Brand-to-network mapping |
| `docs/RAILWAY_DEBUG_GUIDE.md` | Railway deployment debugging |

Older session artifacts are in `docs/archive/` — historical, don't load unless investigating a past decision.
