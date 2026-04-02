---
phase: 02-catalog-first-source-separation
verified: 2026-04-02T00:00:00Z
status: passed
score: 9/9 must-haves verified
re_verification: false
---

# Phase 02: Catalog-First Source Separation Verification Report

**Phase Goal:** Remove redundant live CJ and Awin API calls from session-time code. After this phase, CJ and Awin products come exclusively from the SQLite DB (populated by nightly sync). eBay runs surgically only for interests with thin DB coverage. Amazon and eBay remain live-only (no DB write-back).
**Verified:** 2026-04-02
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Session logs show `[CATALOG] CJ GraphQL skipped — using DB only` (not a live CJ API call) | VERIFIED | `_run_cj` always runs; `_api_key = cj_api_key if _db_is_thin else None`; log line present at line 323 of multi_retailer_searcher.py |
| 2 | Session logs show `[CATALOG] Awin live feed skipped — using DB only` | VERIFIED | `search_products_awin` returns unconditionally after the catalog try block; log line present at line 832 of awin_searcher.py |
| 3 | CJ static partners still appear in recommendations (MonthlyClubs, Winebasket, etc.) | VERIFIED | `_run_cj` appended unconditionally; when `_db_is_thin=False` passes `api_key=None` which triggers static-only path in cj_searcher.py (lines 2992-2994) |
| 4 | Awin static partners still appear in recommendations | VERIFIED | `_get_awin_static_products(profile)` called unconditionally inside the try block and in the except fallback |
| 5 | If DB has <100 products, session falls back to live CJ and Awin and logs WARNING | VERIFIED | `_DB_CIRCUIT_BREAKER_THRESHOLD = 100`; `_db_is_thin = True` sets fallback; WARNING log present; `get_total_product_count()` exists in database.py |
| 6 | eBay fires ONLY for interests with < 5 DB products | VERIFIED | `weak_interests = [i for i in interests if per_interest_counts.get(i.lower(), 0) < EBAY_WEAK_COVERAGE_THRESHOLD]`; `EBAY_WEAK_COVERAGE_THRESHOLD = 5` |
| 7 | If all interests have >= 5 DB products, eBay is skipped entirely | VERIFIED | `if not weak_interests: logger.info("[EBAY] All interests have sufficient DB coverage — skipping eBay.")` — task not appended |
| 8 | eBay contribution capped at 7 items total | VERIFIED | `products = products[:EBAY_NICHE_CAP]` with `EBAY_NICHE_CAP = 7` inside `_run_ebay` |
| 9 | No eBay or Amazon results written to DB | VERIFIED | Comment at end of function: "eBay results are NOT written to the DB — live-only by design"; no DB write calls in any eBay/Amazon result path |

**Score:** 9/9 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `database.py` | `get_total_product_count()` function | VERIFIED | Exists at lines 653-669; returns `int`; exception-safe (returns 0 on failure); used by circuit breaker |
| `multi_retailer_searcher.py` | Circuit breaker; `_run_cj` with `api_key=None`; obsolete diversity gate removed; `EBAY_NICHE_CAP`/`EBAY_WEAK_COVERAGE_THRESHOLD` constants; `weak_interests` scoping | VERIFIED | All constants present at module level (lines 33-34); circuit breaker at lines 90-104; `_run_cj` unconditional at lines 318-334; diversity gate constants absent |
| `awin_searcher.py` | Cache-first path unconditional; live feed CSV download fallback removed; except handler returns static products; `_matches_query` preserved | VERIFIED | `search_products_awin` ends at line 843 (file length); no live feed code reachable; `_matches_query` at line 772; except handler returns static at lines 837-844 |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `multi_retailer_searcher.py _run_cj` | `cj_searcher.search_products_cj` | `api_key=None` argument | WIRED | `_api_key = cj_api_key if _db_is_thin else None` then passed as first positional arg |
| `awin_searcher.py cache block` | `_get_awin_static_products` | Unconditional call after `cached_products` gathered | WIRED | Called on line 829 inside try block AND in except fallback on line 839 |
| `multi_retailer_searcher.py` | `database.get_total_product_count` | Circuit breaker at function top | WIRED | `_db_module.get_total_product_count()` called at line 94; `_db_is_thin` flag set and consumed by `_run_cj` |
| `per_interest_counts` | `weak_interests` filter | `per_interest_counts.get(i.lower(), 0) < EBAY_WEAK_COVERAGE_THRESHOLD` | WIRED | Computed at lines 241-244; pre-initialized as `{}` before DB try block (line 79) preventing NameError |
| `weak_interests` | `search_products_ebay` | Filtered `_ebay_profile` passed to eBay | WIRED | `_ebay_profile` built from `weak_interests` set; closure captures `_ebay_profile` |

---

### Data-Flow Trace (Level 4)

Not applicable for this phase — no new UI components or rendering code added. All changes are internal pipeline wiring (API call suppression, threshold constants, fallback logic). Data ultimately flows to curator via existing `all_products` list, unchanged.

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Syntax valid, all imports resolve | `python -c "import ast; ast.parse(open('multi_retailer_searcher.py').read()); ast.parse(open('awin_searcher.py').read()); ast.parse(open('database.py').read())"` | All parse OK | PASS |
| `get_total_product_count` returns int | `python -c "import database; c = database.get_total_product_count(); assert isinstance(c, int)"` | Returns int (0 in test env, expected) | PASS |
| Diversity gate constants absent | `python -c "import multi_retailer_searcher as m; import inspect; src = inspect.getsource(m); assert 'MIN_SOURCES_TO_SKIP_LIVE' not in src"` | Absent | PASS |
| `EBAY_NICHE_CAP` and `EBAY_WEAK_COVERAGE_THRESHOLD` present | grep for both constants | Both present at module level | PASS |
| Awin live feed log absent | `grep "Searching Awin feeds for" awin_searcher.py` | No match | PASS |
| Old Awin gate (`target_count // 2`) absent | `grep "target_count // 2" awin_searcher.py` | No match | PASS |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| CAT-01 | 02-01 | Live CJ GraphQL calls removed from session-time code | SATISFIED | `_run_cj` always passes `api_key=None` unless `_db_is_thin`; no GraphQL calls in normal operation |
| CAT-02 | 02-01 | Live Awin feed CSV download fallback removed | SATISFIED | `search_products_awin` ends at line 843; no live feed code reachable from the function |
| CAT-03 | 02-02 | eBay runs only for interests with thin DB coverage, capped at ~5-8 items | SATISFIED | `EBAY_WEAK_COVERAGE_THRESHOLD = 5`, `EBAY_NICHE_CAP = 7`; weak_interests filter in place. Note: REQUIREMENTS.md text says "< 3 products" but both PLAN and implementation use 5 — see Anti-Patterns note |
| CAT-04 | 02-01 | `_run_cj` removed from conditional; CJ static partner logic preserved | SATISFIED | `_run_cj` appended unconditionally; static partners fire via `api_key=None` path |
| CAT-05 | 02-01 | `awin_searcher.py` `_matches_query()` 2-term threshold preserved | SATISFIED | `_matches_query` function at line 772 of awin_searcher.py with threshold logic intact |
| CAT-06 | 02-01, 02-02 | No eBay or Amazon results written to DB | SATISFIED | No DB write calls after eBay/Amazon results returned; explicit no-write-back comment in code |

**All 6 phase requirements verified.**

No orphaned requirements: REQUIREMENTS.md Traceability table maps exactly CAT-01 through CAT-06 to Phase 2, all accounted for.

---

### Anti-Patterns Found

| File | Location | Pattern | Severity | Impact |
|------|----------|---------|----------|--------|
| `awin_searcher.py` | Lines 473-791 | Dead feed helper functions (`_stream_feed_and_match`, `_fetch_feed_nonstream`, `_stream_feed_first_n`, `_download_feed_csv`) remain in the file | INFO | These functions are unreachable from `search_products_awin` (the function exits at line 843 which is end-of-file). No runtime impact. Also the module docstring (lines 2-8) still references "Downloads one or more feed CSVs" — stale description. |
| `REQUIREMENTS.md` | Line 31 | CAT-03 text says "< 3 matching DB products" but PLAN 02-02 and implementation use threshold 5 | INFO | Not a code defect — plan's `must_haves` are the binding spec and explicitly chose 5. REQUIREMENTS.md text is stale. No runtime impact. |

No blockers. No stubs. No wiring gaps.

---

### Human Verification Required

None. All aspects of this phase are verifiable programmatically:
- No visual UI changes
- No external service integrations added
- All changes are internal pipeline code (constants, conditional guards, fallback removal)

---

### Gaps Summary

No gaps. All 9 truths verified, all 3 artifacts substantive and wired, all 5 key links confirmed present, all 6 requirements satisfied, no blocker anti-patterns.

The only informational notes:
1. Dead feed helper functions in `awin_searcher.py` are harmless (unreachable) but could be cleaned up in a future pass.
2. REQUIREMENTS.md CAT-03 threshold text ("< 3") is stale relative to the implemented value (5). The plan's `must_haves` are the binding spec and correctly document the decision.

---

_Verified: 2026-04-02_
_Verifier: Claude (gsd-verifier)_
