# Roadmap: GiftWise

## Overview

GiftWise is a live, revenue-generating product. These phases address the gap between what's built and what's needed to grow: more affiliate inventory, better conversion from the guide traffic that already exists, a cleaner recommendation pipeline, and a UI that supports the 14-item output format. Phases are ordered by revenue impact. Phase 4 is maintenance/hardening — do it last.

**Opus-only constraint applies across ALL phases.** Never modify `gift_curator.py` prompt logic, `profile_analyzer.py` prompt/schema, `interest_ontology.py` clustering logic, or `post_curation_cleanup.py` brand/source caps. Add `# SONNET-FLAG:` and stop.

---

## Phases

- [ ] **Phase 1: Revenue & Conversion Quick Wins** — Guide CTAs + 4 new retailers wired into sync
- [ ] **Phase 2: Catalog-First Source Separation** — Remove live CJ/Awin from session code, eBay niche scoping
- [ ] **Phase 3: 14-Item Output (Sonnet Portions)** — Splurge pipeline + UI; Opus prompt flagged with ready-to-paste instructions
- [ ] **Phase 4: Infrastructure Hardening** — Remove dead code, fix in-flight duplicates, verify rate limits

---

## Phase Details

### Phase 1: Revenue & Conversion Quick Wins
**Goal**: Fix the one remaining tracking issue with guide analytics, and add 4 new monetized retailers to the codebase/nightly sync.

**Depends on**: Nothing (first phase)

**Requirements**: CONV-05, RET-01, RET-02, RET-03, RET-04, RET-05

**Note**: CONV-01 through CONV-04 and CONV-06 are already complete — all guide templates have above-fold and mid-page CTAs linking to `/demo`, and the 3 Etsy guides never existed (no routes). The `/blog` and `/guides` indexes already have CTAs.

**Success Criteria** (what must be TRUE after this phase):
1. `track_event('guide_hit')` (bare, redundant) removed from guide route; only `track_event(f'guide_hit:{slug}')` fires
2. `track_event('guide_hit')` (misclassified) removed from blog route; only `track_event(f'blog_hit:{slug}')` fires
3. AWOL Vision and OUFER Body Jewelry products receive matching interest tags at nightly sync once joined in Awin dashboard
4. youngelectricbikes and Tayst Coffee have static product entries in `awin_searcher.py`
5. VitaJuwel and VSGO placeholder URLs replaced with real Awin deep links

**Plans**: 2 plans

Plans:
- [x] 01-01-PLAN.md — Tracking fix (remove redundant `guide_hit` event) + catalog sync terms for AWOL Vision and OUFER Body Jewelry
- [ ] 01-02-PLAN.md — Static products for youngelectricbikes + Tayst Coffee; fix VitaJuwel + VSGO Awin links

---

### Phase 2: Catalog-First Source Separation
**Goal**: Make the recommendation pipeline faster and cleaner by removing redundant live API calls during sessions. CJ and Awin products come from the DB only. eBay runs surgically for weak-coverage interests only.

**Depends on**: Phase 1 (DB needs new retailers wired before removing live fallbacks)

**Requirements**: CAT-01, CAT-02, CAT-03, CAT-04, CAT-05, CAT-06

**Success Criteria** (what must be TRUE after this phase):
1. Session logs show NO CJ GraphQL API calls during recommendation generation
2. Session logs show NO Awin feed CSV download during recommendation generation
3. eBay is called only for interests with < 5 DB products (per CONTEXT.md decision); threshold `EBAY_WEAK_COVERAGE_THRESHOLD = 5`
4. Total eBay contribution is capped at 7 items (`EBAY_NICHE_CAP = 7`)
5. CJ static partners (MonthlyClubs, Winebasket, zChocolat, etc.) still appear in recommendations
6. Awin static partners still appear in recommendations
7. No eBay or Amazon products written to the DB
8. Circuit breaker re-enables live CJ/Awin if DB has < 100 total products

**Plans**: 2 plans

Plans:
- [x] 02-01-PLAN.md — Remove live CJ GraphQL + Awin feed from session code; add `get_total_product_count()` + circuit breaker; remove obsolete diversity gate
- [x] 02-02-PLAN.md — eBay niche-only scoping using `per_interest_counts`; `EBAY_NICHE_CAP = 7`; pre-initialize `per_interest_counts` before DB try block

---

**Implementation notes for plan-phase:**

**02-01 (Remove live CJ + Awin session calls):**
- `database.py`: Add `get_total_product_count()` — single-query `SELECT COUNT(*)` for circuit breaker
- `multi_retailer_searcher.py`:
  - Add circuit breaker before DB query block: if DB < 100 products, set `_db_is_thin = True` and log WARNING
  - Replace `if cj_api_key: _run_cj()` guard with unconditional `_run_cj` that passes `api_key=None` when DB is healthy
  - `api_key=None` triggers cj_searcher.py line 2992-2994 static-only return (17 merchants preserved)
  - Remove obsolete diversity gate constants (MIN_SOURCES_TO_SKIP_LIVE, MAX_SINGLE_SOURCE_PCT, MIN_INTEREST_COVERAGE_PCT) and the early-return if/else block — keep per-source capping block
  - Update no-write-back comment to reference Phase 2
- `awin_searcher.py`:
  - Remove `if len(cached_products) >= target_count // 2:` gate (line 826) — make cache-first block unconditional
  - Update except handler to return static products only (not fall through to deleted live code)
  - Delete lines 835–1087 (live feed CSV download flow)
  - Add `[CATALOG] Awin live feed skipped — using DB only` log line

**02-02 (eBay niche-only scoping):**
- `multi_retailer_searcher.py`:
  - Pre-initialize `per_interest_counts = {}` before DB try block (prevents NameError if DB fails)
  - Add `EBAY_NICHE_CAP = 7` and `EBAY_WEAK_COVERAGE_THRESHOLD = 5` as module-level constants
  - Before `_run_ebay` definition, compute `weak_interests` using `per_interest_counts.get(i.lower(), 0) < 5`
  - If `weak_interests` is empty, skip eBay entirely and log `[EBAY] All interests have sufficient DB coverage`
  - If non-empty, build `_ebay_profile` (shallow copy with only weak-coverage interests) and pass to `search_products_ebay`
  - Cap eBay results at `EBAY_NICHE_CAP` inside `_run_ebay`

---

### Phase 3: 14-Item Output (Sonnet Portions)
**Goal**: Wire the splurge slot through the pipeline infrastructure and display it in the UI. The curator prompt changes that tell Claude *how* to pick a splurge item are Opus-only — this phase preps everything Sonnet can touch and leaves a ready-to-paste Opus prompt.

**Depends on**: Phase 2 (DB query changes are stable before wiring splurge)

**Requirements**: OUT-01, OUT-02, OUT-03, OUT-04, OUT-05

**Success Criteria** (what must be TRUE after this phase):
1. `search_products_diverse()` returns `splurge_candidates` (products $200–$1500) as a separate list from the regular pool
2. The splurge candidates list flows through `multi_retailer_searcher.py` → `recommendation_service.py` → `gift_curator.py` input (even if the curator ignores it until Opus updates the prompt)
3. `templates/recommendations.html` renders a splurge tile that is visually distinct from regular tiles
4. The splurge tile has a "Splurge Pick" badge and correct price ceiling label based on `budget_category`
5. A `# SONNET-FLAG:` comment in `gift_curator.py` contains a complete, copy-paste-ready Opus prompt for the splurge slot changes (see Opus prompt template below)
6. No existing recommendations functionality is broken (10 regular gifts + 3 experiences still render correctly)

**Plans**: 2 plans

Plans:
- [ ] 03-01-PLAN.md — Pipeline wiring — splurge_candidates from DB through to curator input
- [ ] 03-02-PLAN.md — Splurge tile UI in recommendations.html + SONNET-FLAG with Opus prompt

---

**Implementation notes for plan-phase:**

**03-01 (Pipeline wiring):**
- `database.py` → `search_products_diverse()`: already has splurge separation per Mar 2026 changes. Verify it returns `{"regular": [...], "splurge": [...], "per_interest_counts": {...}}` or add this structure.
- `multi_retailer_searcher.py`: thread `splurge_candidates` through the return value alongside regular products
- `models.py`: ensure `to_curator_format()` includes all fields needed (gift_score, interest_tags already added Mar 2026)
- `recommendation_service.py`: pass splurge_candidates separately to the curator function
- `gift_curator.py`: add splurge_candidates to the `inventory` block passed to Claude (even if prompt doesn't use them yet — data must flow). Mark with `# SONNET-FLAG: Opus adds splurge slot instructions here`
- Budget ceiling: read `profile.get('price_signals', {}).get('budget_category', 'moderate')` and map: budget→300, moderate→500, premium→1000, luxury→1500, unknown→500. Store as `splurge_ceiling` in the session context dict.

**03-02 (Splurge tile UI):**
- `templates/recommendations.html`: After the 10 regular gift tiles and before the 3 experience tiles, add a splurge tile section. Only render if `splurge_item` is present in template context.
- Splurge tile design: larger or bordered differently from regular tiles. Add badge: `<span class="splurge-badge">Splurge Pick</span>`. Show price ceiling context: `"The 'if money were no object' pick — up to $[ceiling]"`
- Keep styling consistent with existing tile aesthetic (read current CSS before writing new styles)
- Do NOT hardcode price ceiling — read from `splurge_ceiling` in template context

**SONNET-FLAG Opus prompt for gift_curator.py (paste into the flag comment):**
```
# SONNET-FLAG: Opus implements this section.
#
# OPUS PROMPT:
# You are updating gift_curator.py to add a splurge slot to the recommendation output.
#
# Context:
# - The curator currently outputs 10 regular gifts + 3 experiences (rec_count=10)
# - We want to add 1 SPLURGE item: the nicest possible gift, $200–$1500 range
# - splurge_candidates (list of products $200–$1500 from the DB) are now passed in the inventory
# - The profile dict contains price_signals.budget_category; map to ceiling:
#     budget→$300, moderate→$500, premium→$1000, luxury→$1500, unknown→$500
# - The splurge slot is SEPARATE from the 10 regular gifts — it goes after them
# - Splurge can be a physical item OR an extravagant experience — curator decides based on what's strongest
#
# What to implement:
# 1. Change rec_count from 10 → 11 (10 regular + 1 splurge)
# 2. Add splurge_candidates to the inventory section shown to Claude
# 3. Add splurge slot instructions to the curator prompt:
#    "Pick 1 SPLURGE item — the nicest version of something they love OR an extravagant experience.
#     Price $[ceiling] max. This should feel like the 'if money were no object' pick.
#     Pull from the SPLURGE CANDIDATES list if one fits. Label it SPLURGE in your output."
# 4. Parse the SPLURGE item out of the curator response into a separate field
# 5. Pass it to the template as splurge_item (template rendering already done by Sonnet in Phase 3)
#
# Constraints:
# - Do NOT touch the gift reasoning framework, selection principle, or ownership section
# - Do NOT route image URLs or affiliate links through the prompt
# - Do NOT increase the experiences count (stays at 3)
# - The splurge ceiling comes from price_signals.budget_category — DO wire this in
```

---

### Phase 4: Infrastructure Hardening
**Goal**: Remove dead code that creates confusion, fix a known API waste issue, and verify the rate limiting infrastructure is sound.

**Depends on**: Phase 3

**Requirements**: INF-01, INF-02, INF-03, INF-04

**Success Criteria** (what must be TRUE after this phase):
1. `skimlinks_searcher.py` is deleted
2. No Skimlinks JS snippet appears in any template (`publisher_id=298548X178612` not present in any HTML)
3. Two concurrent requests for the same profile hash result in one Claude API call, not two
4. Rate limiting is confirmed to use the SQLite `rate_limits` table (not shelve)

**Plans**: 2 plans

Plans:
- [ ] 04-01-PLAN.md — Remove Skimlinks dead code (file + JS snippets in templates)
- [ ] 04-02-PLAN.md — In-flight duplicate prevention + rate limit verification

---

**Implementation notes for plan-phase:**

**04-01 (Remove Skimlinks):**
- Delete `skimlinks_searcher.py`
- Search all templates for `skimlinks`, `publisher_id=298548X178612`, `skimresources`, `skimlinks.com` — remove any `<script>` tags that load Skimlinks JS
- Search `giftwise_app.py` for any import or reference to `skimlinks_searcher` — remove
- Verify no other file imports from `skimlinks_searcher`

**04-02 (In-flight duplicate prevention):**
- `giftwise_app.py` or `recommendation_service.py`: Add a module-level dict `_in_flight_profiles: dict = {}`
- Before calling Claude for profile analysis: check if `profile_hash` is in `_in_flight_profiles`
  - If yes: wait (use threading.Event or just re-check cache after a short sleep) then return cached result
  - If no: add to dict, run Claude call, cache result, remove from dict
- This is a within-process lock only (doesn't span Gunicorn workers) — document this limitation with a comment
- Rate limits: read `giftwise_app.py` rate limit check code — verify it queries `database.rate_limits` table, not `storage_service.py` shelve. If it uses shelve, migrate to the SQLite table (schema already exists in `database.py`)

---

## Progress

**Execution Order:** 1 → 2 → 3 → 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Revenue & Conversion Quick Wins | 1/2 | In Progress|  |
| 2. Catalog-First Source Separation | 0/2 | Planned | - |
| 3. 14-Item Output (Sonnet Portions) | 0/2 | Not started | - |
| 4. Infrastructure Hardening | 0/2 | Not started | - |

---

## Opus Work Items (Not in Roadmap — Separate Sessions)

These require Opus and cannot be executed by Sonnet. They are tracked here so they don't get lost.

### [OPEN] Splurge Slot Curator Prompt — `gift_curator.py`
**When to run:** After Phase 3 completes (pipeline infrastructure + UI ready)
**Prompt:** See the `# SONNET-FLAG:` comment added to `gift_curator.py` in Phase 3, Plan 03-02. Copy-paste that prompt to Opus.

### [OPEN] Load Testing & Architectural Stress Audit
**Prompt:** See `docs/ARCHITECTURE.md` — the full Opus audit prompt is there. Covers: shelve concurrency, worker exhaustion, SQLite contention, rate limiting race conditions.

### [OPEN] Catalog-First Phase 2 — DB Query Scoring Improvement (Task 4)
Per CLAUDE.md: `search_products_by_interests()` scoring improvement using multi-label tags. Safe for Sonnet actually, but flagged as Opus in CLAUDE.md. Revisit.

---
*Roadmap created: 2026-04-01*
*Last updated: 2026-04-02 — Phase 2 plans written (02-01, 02-02); success criteria updated to reflect CONTEXT.md threshold=5 decision*
