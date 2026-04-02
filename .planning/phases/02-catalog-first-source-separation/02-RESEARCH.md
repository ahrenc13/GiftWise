# Phase 2 Research: Catalog-First Source Separation

**Researched:** 2026-04-02
**Domain:** multi_retailer_searcher.py, awin_searcher.py, database.py
**Confidence:** HIGH — all findings verified against actual source lines

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Circuit breaker threshold:** 100 total DB products. Query `SELECT COUNT(*) FROM products` once. Log WARNING: `[CATALOG] DB thin (<100 products) — falling back to live CJ/Awin for this session`
- **eBay weak-coverage threshold:** 5 products per interest (`per_interest_counts[interest] < 5`). Missing key = 0.
- **eBay cap constant:** `EBAY_NICHE_CAP = 7` (max 7 items total across all weak-coverage interests)
- **CJ session-time removal:** Remove `_run_cj` from the parallel task list. Keep static partner logic (MonthlyClubs, Winebasket, etc.). Do NOT delete `cj_searcher.py`.
- **Awin session-time removal:** Remove the live feed CSV download fallback. Make cache-first path unconditional. Static Awin partners (`_get_awin_static_products`) still run.
- **No DB write-back:** Preserve the existing "no write-back" behavior. Add a comment documenting it.
- **`_matches_query()` 2-term threshold:** Must not be touched.
- **Files not to modify:** `cj_searcher.py`, `gift_curator.py`, `profile_analyzer.py`, `interest_ontology.py`, `post_curation_cleanup.py`

### Claude's Discretion
- Exact placement of circuit breaker check (top of `search_products_multi_retailer()` or inside the DB query block)
- Whether to consolidate/remove the existing diversity gate conditions (MIN_SOURCES_TO_SKIP_LIVE, MAX_SINGLE_SOURCE_PCT, MIN_INTEREST_COVERAGE_PCT) — planner decides based on code reading
- Exact logging format and log level (INFO vs DEBUG for individual items)

### Deferred Ideas
None raised during discussion.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CAT-01 | Live CJ GraphQL calls removed from session-time code — CJ products come from DB only | `_run_cj` at lines 293-306 of multi_retailer_searcher.py; static partners survive via cj_searcher.py |
| CAT-02 | Live Awin feed CSV download fallback removed from awin_searcher.py — static partners still run | Cache-first block at lines 811-831 of awin_searcher.py; `_get_awin_static_products` at line 827 |
| CAT-03 | eBay runs ONLY for interests with < 3 matching DB products (REQUIREMENTS.md says < 3; CONTEXT.md says < 5 — see note below) | `per_interest_counts` available at line 114 of multi_retailer_searcher.py |
| CAT-04 | `_run_cj` removed from parallel retailer tasks; CJ static partners preserved | Static partner logic is INSIDE `cj_searcher.search_products_cj()` — see Q1 below |
| CAT-05 | `_matches_query()` 2-term threshold preserved | Confirmed at awin_searcher.py line 790; not touched by this phase |
| CAT-06 | No eBay or Amazon results written to DB — verify and document | Comment already at multi_retailer_searcher.py lines 378-383; no write-back code present |
</phase_requirements>

---

## Q1: CJ Removal

### `_run_cj` definition and task append

**Lines 292-308** of `multi_retailer_searcher.py`:

```
292: if cj_api_key:
293:     def _run_cj():
294:         from cj_searcher import search_products_cj
295:         _notify('CJ Affiliate', searching=True)
296:         products = search_products_cj(
297:             profile, cj_api_key,
298:             company_id=cj_company_id,
299:             publisher_id=cj_publisher_id,
300:             target_count=per_vendor_target,
301:             enhanced_search_terms=enhanced_search_terms,
302:             joined_only=False,
303:         )
304:         _notify('CJ Affiliate', count=len(products), done=True)
305:         return 'CJ Affiliate', products
306: retailer_tasks.append(_run_cj)
307: else:
308:     logger.info("CJ Affiliate credentials not set - skipping CJ")
```

**The `_run_cj` task runs both the CJ GraphQL API AND the static partners.** There is no separate `_run_cj_static` in `multi_retailer_searcher.py`.

Static CJ partners (Peet's, illy, MonthlyClubs, SoccerGarage, TechForLess, Tenergy, Trinity Road, zChocolat, Winebasket, FlowersFast, FragranceShop, GameFly, GreaterGood, GroundLuxe, Russell Stover, Ghirardelli, SilverRushStyle) live INSIDE `cj_searcher.search_products_cj()` at lines 2965-2990 of `cj_searcher.py`. They are collected unconditionally before the `if not api_key` guard — meaning they run even when CJ_API_KEY is absent.

**Consequence for Phase 2:** Simply removing `_run_cj` from `retailer_tasks` will ALSO remove all 17 static CJ partners. The planner must choose one of two approaches:

**Option A (recommended):** Keep calling `search_products_cj()` but with `api_key=None`. The function returns static products only when `api_key` is falsy (see line 2992-2994 of cj_searcher.py: `if not api_key: return static_products`). This preserves static partners with zero API calls. The `_run_cj` closure just needs to pass `api_key=None` (or not pass it at all, since the env var fallback inside cj_searcher would also be absent).

**Option B:** Extract static partner logic into a direct call. More surgical but requires touching `cj_searcher.py`, which CONTEXT.md says not to modify.

**Option A is the right approach.** The `_run_cj` task should be changed to call `search_products_cj(profile, api_key=None, ...)` unconditionally (removing the `if cj_api_key:` guard and passing None). This skips GraphQL but preserves all 17 static partner getters.

---

## Q2: Awin Removal

### Cache-first block and the gate to remove

**Lines 811-833** of `awin_searcher.py`:

```
811: # --- Cache-first: check SQLite catalog before downloading any feeds ---
812: try:
813:     from catalog_sync import get_cached_awin_products_for_interest
814:     interests = profile.get("interests", [])
815:     cached_products = []
816:     seen_ids = set()
817:     for interest in interests:
818:         name = interest.get("name", "")
819:         if not name or interest.get("is_work", False):
820:             continue
821:         for p in get_cached_awin_products_for_interest(name, limit=20):
822:             pid = p.get("product_id", "")
823:             if pid and pid not in seen_ids:
824:                 seen_ids.add(pid)
825:                 cached_products.append(p)
826:     if len(cached_products) >= target_count // 2:   <-- GATE TO REMOVE
827:         static = _get_awin_static_products(profile)
828:         result = (cached_products + static)[:target_count]
829:         logger.info("Awin: returning %d products from catalog cache (skipping live download)",
830:                     len(result))
831:         return result
832: except Exception as e:
833:     logger.debug("Awin cache check failed, falling back to live: %s", e)
```

**The gate is the `if len(cached_products) >= target_count // 2` condition on line 826.** To make the cache-first path unconditional:
- Remove the `if` condition — make the `static = ...` / `return result` block run regardless of `len(cached_products)`.
- The `except` handler on line 833 currently falls through to the live download. After the change, the except handler should return `[]` (or just the static products) rather than proceeding to the live download block.

### `_get_awin_static_products` placement

`_get_awin_static_products(profile)` is called at **two locations**:
1. **Line 827** — inside the cache-first return path (the block we're making unconditional). This call WILL survive the change.
2. **Line 1081** — at the end of the live feed download flow (inside the block being removed). This second call will be eliminated when the live fallback is removed, but that's fine — static products are already injected at line 827.

**Static Awin partners survive.** The call at line 827 is inside the cache-first block which is being made unconditional. After the change, static products always get injected.

### Live fallback code range

The live download fallback starts immediately after `except Exception as e: logger.debug(...)` at line 833 and runs to approximately line 1085. This entire block (lines 835-1085) is the code to remove/bypass.

---

## Q3: eBay Scoping

### Where eBay is called currently

**Lines 248-260** of `multi_retailer_searcher.py`:

```
248: if ebay_client_id and ebay_client_secret:
249:     def _run_ebay():
250:         from ebay_searcher import search_products_ebay
251:         _notify('eBay', searching=True)
252:         products = search_products_ebay(
253:             profile, ebay_client_id, ebay_client_secret,
254:             target_count=per_vendor_target,
255:         )
256:         _notify('eBay', done=True, count=len(products))
257:         return 'eBay', products
258:     retailer_tasks.append(_run_ebay)
```

eBay currently receives the **full profile** (line 253). It does not receive a filtered interest list. `search_products_ebay()` internally extracts interests from the profile.

### Where `per_interest_counts` is available

**Line 114** of `multi_retailer_searcher.py`:
```
114: per_interest_counts = db_result.get('per_interest_counts', {})
```

This is set inside the `if interests:` block within the database query try/except (around line 105). It is in scope for all subsequent code in the same function.

### Injection point for eBay filtering

The cleanest injection is at the `_run_ebay` definition (lines 248-258). Instead of passing `profile` directly to `search_products_ebay()`, compute `weak_interests` before defining `_run_ebay` (using `per_interest_counts` from line 114) and pass a modified profile or an explicit interest filter.

**Challenge:** `per_interest_counts` is set inside the `try:` block starting around line 76, but `_run_ebay` is defined after the `try/except` block ends (after line 204). The variable is defined only if the DB query succeeded AND `interests` was non-empty. If the DB block failed or was skipped, `per_interest_counts` would be undefined.

**Solution:** Initialize `per_interest_counts = {}` before the DB try block (e.g., alongside `all_products = []` at line 70). Then the eBay scoping logic at line 248 can safely reference it whether or not the DB query ran.

### eBay scoping logic

Before defining `_run_ebay`, compute:
```python
weak_interests = [i for i in interests if per_interest_counts.get(i.lower(), 0) < 5]
```
If `weak_interests` is empty, skip eBay entirely. Otherwise build a modified profile containing only `weak_interests` and pass it to `search_products_ebay()`. Cap eBay results at `EBAY_NICHE_CAP = 7` after the call returns.

---

## Q4: Circuit Breaker

### Existing total-count infrastructure

`database.get_database_stats()` at line 598-648 already runs `SELECT COUNT(*) FROM products WHERE removed_at IS NULL AND in_stock = 1` (line 604). However, `get_database_stats()` is a heavier function that also queries by_retailer, added_today, stale_count, top_brands — too expensive to run at session time.

**No dedicated `get_total_product_count()` function exists.** One must be added to `database.py` or the check must be inlined.

**Simplest inline query:**
```python
with database.get_db_connection() as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM products WHERE removed_at IS NULL AND in_stock = 1")
    total = cursor.fetchone()[0]
```

A new exported function `get_total_product_count()` in `database.py` would be cleaner and avoids exposing raw DB access in `multi_retailer_searcher.py`.

### Where to place the circuit breaker

The circuit breaker must run before `retailer_tasks` is built (i.e., before line 220 where `retailer_tasks = []` is assigned). Two viable placements:

**Option A (top of function, outside the DB query block):** Check total count before the existing DB query block. If thin, set a flag (`db_is_thin = True`) and skip the DB query entirely, proceeding directly to full live API calls. This is the cleanest placement since it avoids entering the DB query block at all.

**Option B (inside the DB query block, early exit):** After the DB import succeeds (line 77), check total count before calling `search_products_diverse()`. If thin, log WARNING and `return None` (use a sentinel) to fall through to live APIs.

**Option A is cleaner** because it separates concerns — thin DB check is distinct from the "did we get enough products" check.

---

## Q5: Diversity Gate

### Current conditions (lines 141-196)

```python
MIN_SOURCES_TO_SKIP_LIVE = 3        # line 141
MAX_SINGLE_SOURCE_PCT = 0.40        # line 142
MIN_INTEREST_COVERAGE_PCT = 0.50    # line 164

if (num_sources >= MIN_SOURCES_TO_SKIP_LIVE
        and top_source_pct <= MAX_SINGLE_SOURCE_PCT
        and interest_coverage_pct >= MIN_INTEREST_COVERAGE_PCT):
    return all_products[:MAX_INVENTORY_SIZE]  # Skip live APIs
else:
    # Log reason, proceed with live API calls
```

### After Phase 2: what happens to this logic?

After Phase 2, the only live APIs remaining are:
- eBay (niche-only, already scoped via `weak_interests`)
- Amazon (if key present — live-only by design)
- Etsy (if key present — currently 403, effectively skipped)
- ShareASale / Skimlinks (legacy, essentially no-op)

The diversity gate currently enables/disables ALL live APIs including CJ and Awin. After removing CJ and Awin from the live task list, the gate only affects eBay/Amazon.

**Recommendation:** Remove the gate entirely. It is no longer the right mechanism — eBay triggering is now controlled by `weak_interests` logic, not by source diversity counts. Keeping the gate would make eBay conditionally skip even for weak-coverage interests if the DB happens to return 3+ sources, which contradicts the intent.

**What would break if removed:** Nothing in the current phase. The per-source capping logic (lines 146-160) runs BEFORE the gate and should be preserved — it caps overrepresented sources regardless of whether live APIs run. Only the early-return gate (lines 169-196) should be removed.

**Safe removal plan:** Delete lines 169-196 (the `if len(all_products) >= target_count:` block containing the three conditions and early return). Keep lines 141-160 (per-source capping). The code then falls through to the retailer_tasks block unconditionally, where eBay niche-scoping takes over.

---

## Q6: eBay Write-Back

### Confirmed: no eBay write-back exists

`multi_retailer_searcher.py` lines 378-383 contain an explicit comment:
```
# NOTE: DB write-back of live API results was removed (Mar 2026).
# The product DB should only contain nightly-synced CJ/Awin inventory
# from catalog_sync.py. Writing eBay/Amazon results back polluted the
# curated catalog with marketplace listings that go stale quickly and
# lack affiliate tracking from our approved networks.
```

There is no `database.upsert_product()`, `database.insert_product()`, or similar call in `multi_retailer_searcher.py` for eBay or Amazon results. No write-back code exists anywhere in the file. The comment can be extended to reference Phase 2 to make the no-write-back intent explicit for future sessions.

---

## Threshold Conflict: CAT-03 vs CONTEXT.md

**REQUIREMENTS.md CAT-03 says:** `< 3 matching DB products`
**CONTEXT.md says:** `threshold = 5` and `EBAY_NICHE_CAP = 7`

CONTEXT.md was written after REQUIREMENTS.md and represents the actual decision from the discuss-phase session. **Use the CONTEXT.md values:** threshold = 5, cap = 7. The planner should note this discrepancy and use CONTEXT.md as authoritative.

---

## Planning Recommendations

1. **CJ static partners require calling `search_products_cj(profile, api_key=None, ...)` not skipping the call entirely.** Static partners (17 merchants) are gated inside `search_products_cj()` and cannot be extracted without touching `cj_searcher.py`. The right change in `multi_retailer_searcher.py` is to remove the `if cj_api_key:` guard and make the `_run_cj` task always run with `api_key=None` (or no api_key arg), which triggers the static-only path at cj_searcher.py line 2992.

2. **Initialize `per_interest_counts = {}` before the DB try block.** The variable is needed by the eBay scoping logic (defined after the try/except ends). Without pre-initialization, the eBay block will raise `NameError` if the DB query block was skipped or failed. Set it alongside `all_products = []` at the top of the function.

3. **Add `get_total_product_count()` to database.py.** The circuit breaker needs a cheap single-query function. Inlining the query in `multi_retailer_searcher.py` works but is better as an exported function — keeps DB access centralized and makes the function easily testable.

4. **The Awin except handler (line 833) needs updating.** Currently it falls through to the live download on any exception from the cache check. After removing the live download, the except handler must explicitly return static products (or `[]`) rather than silently proceeding to deleted code. Failure to update this will cause an error when the cache check throws (e.g., `catalog_sync` not importable in a fresh environment).

5. **Remove the diversity gate early-return (lines 169-196) as part of this phase.** The gate was designed to skip live CJ/Awin calls when DB was good. After those calls are removed, the gate serves no purpose and its conditions (MIN_SOURCES_TO_SKIP_LIVE, etc.) no longer correspond to any decision point. Removing it reduces confusion for future sessions. Keep the per-source capping block (lines 146-160) — it is independently useful.

---

## Sources

- `multi_retailer_searcher.py` — read in full (385 lines)
- `awin_searcher.py` — read lines 1-200, 319-420, 780-935 (cache-first block, static products, live fallback start)
- `database.py` — read lines 1-50, 408-519 (search_products_diverse), 598-648 (get_database_stats)
- `cj_searcher.py` — grep for search_products_cj definition and static partner logic (lines 2947-2994)
- `.planning/phases/02-catalog-first-source-separation/02-CONTEXT.md` — locked decisions
- `.planning/REQUIREMENTS.md` — CAT-01 through CAT-06

**Confidence:** HIGH — all line numbers verified against actual file content.
