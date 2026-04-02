# Phase 2: Catalog-First Source Separation — Context

**Gathered:** 2026-04-02
**Status:** Ready for planning
**Source:** discuss-phase

<domain>
## Phase Boundary

Remove redundant live CJ and Awin API calls from session-time code. After this phase, CJ and Awin products come exclusively from the SQLite DB (populated by nightly sync). eBay runs surgically only for interests with thin DB coverage. Amazon and eBay remain live-only (no DB write-back).

</domain>

<decisions>
## Implementation Decisions

### Safety Net / Circuit Breaker
- **Decision: Add a circuit breaker.** If the DB has fewer than 100 total products at session time (sync failure, fresh environment), re-enable live CJ and Awin calls for that session as fallback.
- Under normal operation (DB has 11,000+ products), the circuit breaker never triggers.
- Log a WARNING when it triggers: `[CATALOG] DB thin (<100 products) — falling back to live CJ/Awin for this session`
- Threshold: 100 products total (not per-interest). Query `SELECT COUNT(*) FROM products` once at the top of the search flow.

### eBay Coverage Threshold
- **Decision: threshold = 5.** eBay fires for an interest if `per_interest_counts[interest] < 5`.
- `per_interest_counts` is already returned by `search_products_diverse()` — use it directly.
- If an interest is absent from `per_interest_counts` entirely, treat it as 0 (fire eBay for it).
- eBay contribution capped at 7 items total across all weak-coverage interests (`EBAY_NICHE_CAP = 7`).
- If all interests have 5+ DB products, skip eBay entirely for that session.
- Log weak-coverage interests before firing eBay: `[EBAY] Weak-coverage interests (< 5 DB products): {list}. Calling eBay for {N} interests.`
- If eBay skipped entirely: `[EBAY] All interests have sufficient DB coverage — skipping eBay.`

### CJ Session-Time Removal
- Remove `_run_cj` from the parallel retailer task list in `multi_retailer_searcher.py`.
- Keep `_run_cj_static` (or equivalent static partner logic) — MonthlyClubs, Winebasket, zChocolat, etc. These are cheap, additive, and not redundant with DB.
- Do NOT delete `cj_searcher.py` — still used by `catalog_sync.py` for nightly sync.
- Add log: `[CATALOG] CJ GraphQL skipped — using DB only`

### Awin Session-Time Removal
- Remove the live feed CSV download fallback from `awin_searcher.py`.
- The cache-first path (lines ~811–831) already works correctly — make it unconditional (remove the `>= target_count // 2` gate and the fallback branch below it).
- Static Awin partners (`_get_awin_static_products`) still run — do NOT remove.
- Do NOT remove or weaken `_matches_query()` 2-term threshold.
- Add log: `[CATALOG] Awin live feed skipped — using DB only`

### No DB Write-Back (Preserve Existing)
- eBay and Amazon results must NOT be written to the DB. This is already enforced — add a comment to document it explicitly so future sessions don't accidentally re-add it.

### Claude's Discretion
- Exact placement of circuit breaker check (top of `search_products_multi_retailer()` or inside the DB query block)
- Whether to consolidate the existing diversity gate conditions (MIN_SOURCES_TO_SKIP_LIVE, MAX_SINGLE_SOURCE_PCT, MIN_INTEREST_COVERAGE_PCT) or remove them now that DB-only is unconditional — planner decides based on code reading
- Exact logging format and log level (INFO vs DEBUG for individual items)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Core files to modify
- `multi_retailer_searcher.py` — Remove `_run_cj` from parallel tasks; add eBay niche scoping using `per_interest_counts`; add circuit breaker
- `awin_searcher.py` — Remove live feed download fallback (lines ~826–860); make cache-first path unconditional

### Do NOT modify
- `cj_searcher.py` — Used by nightly sync (`catalog_sync.py`); do not touch session-time removal here
- `gift_curator.py` — Opus-only zone
- `profile_analyzer.py` — Opus-only zone
- `interest_ontology.py` — Opus-only zone
- `post_curation_cleanup.py` — Opus-only zone (brand relaxation rules, source diversity caps)
- `awin_searcher.py` `_matches_query()` — 2-term threshold must not be removed or weakened

### Key code locations (verify line numbers by reading file)
- `multi_retailer_searcher.py` ~line 293: `_run_cj` definition and `retailer_tasks.append(_run_cj)`
- `multi_retailer_searcher.py` ~line 109: `search_products_diverse()` call returning `per_interest_counts`
- `multi_retailer_searcher.py` ~line 234: `_run_awin` definition
- `awin_searcher.py` ~line 811: cache-first block; ~line 826: `if len(cached_products) >= target_count // 2` gate to remove
- `awin_searcher.py` ~line 827: `_get_awin_static_products(profile)` — KEEP this call

### Architecture context
- `database.py` `search_products_diverse()` returns `{'regular': [...], 'splurge_candidates': [...], 'per_interest_counts': {...}}`
- `per_interest_counts` keys are lowercased interest names; missing key = 0 products
- eBay search: `search_products_ebay()` in `multi_retailer_searcher.py` — currently called for all interests
- Nightly sync populates DB with 589 terms via `catalog_sync.py`

</canonical_refs>

<specifics>
## Specific Requirements

- Circuit breaker threshold: 100 total DB products (not per-interest)
- eBay weak-coverage threshold: 5 products per interest
- eBay cap constant: `EBAY_NICHE_CAP = 7`
- Log line format when circuit breaker fires: `[CATALOG] DB thin (<100 products) — falling back to live CJ/Awin for this session`
- Log line format for eBay: `[EBAY] Weak-coverage interests (< 5 DB products): {list}. Calling eBay for {N} interests.`
- Log line when eBay skipped: `[EBAY] All interests have sufficient DB coverage — skipping eBay.`

</specifics>

<deferred>
## Deferred Ideas

None raised during discussion.

</deferred>

---

*Phase: 02-catalog-first-source-separation*
*Context gathered: 2026-04-02 via discuss-phase*
