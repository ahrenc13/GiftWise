---
phase: 02-catalog-first-source-separation
plan: 01
subsystem: search-pipeline
tags: [catalog-first, session-latency, circuit-breaker, cj, awin]
dependency_graph:
  requires: []
  provides: [catalog-only-cj, catalog-only-awin, circuit-breaker]
  affects: [multi_retailer_searcher.py, awin_searcher.py, database.py]
tech_stack:
  added: []
  patterns: [circuit-breaker, catalog-first-with-fallback]
key_files:
  created: []
  modified:
    - database.py
    - multi_retailer_searcher.py
    - awin_searcher.py
decisions:
  - Circuit breaker threshold set at 100 products -- below that, live CJ/Awin APIs fire as fallback
  - CJ static partners (17 merchants) always run regardless of DB health via api_key=None path
  - Awin except handler returns static products only (not empty list) for graceful degradation
metrics:
  duration: ~2min
  completed: 2026-04-02
  tasks_completed: 3
  tasks_total: 3
  files_modified: 3
requirements:
  - CAT-01
  - CAT-02
  - CAT-04
  - CAT-05
  - CAT-06
---

# Phase 02 Plan 01: Remove Live CJ/Awin Session Calls Summary

Eliminated redundant live CJ GraphQL and Awin CSV feed download calls from session-time code, replacing them with catalog-only DB reads plus a circuit breaker that re-enables live calls when the DB is thin (<100 products).

## What Was Done

### Task 1: Add get_total_product_count() to database.py
- Added lightweight `get_total_product_count()` function after `get_database_stats()`
- Returns count of active, in-stock products via single COUNT(*) query
- Exception-safe: returns 0 on failure
- **Commit:** `01dfdbb`

### Task 2: Rewrite _run_cj and add circuit breaker to multi_retailer_searcher.py
- Added `_DB_CIRCUIT_BREAKER_THRESHOLD = 100` and `_db_is_thin` flag before DB query block
- Replaced conditional `if cj_api_key:` block with unconditional `_run_cj` that passes `api_key=None` when DB is healthy (returns only static partners, zero GraphQL calls)
- Removed obsolete diversity gate: `MIN_SOURCES_TO_SKIP_LIVE`, `MAX_SINGLE_SOURCE_PCT`, `MIN_INTEREST_COVERAGE_PCT` constants and the entire early-return if/else block
- Preserved per-source capping block (30% cap per source domain)
- Updated write-back comment to reference Phase 2
- **Commit:** `e1edd0e`

### Task 3: Make Awin cache-first path unconditional, remove live feed fallback
- Removed `>= target_count // 2` gate -- cache block now always returns `(cached_products + static)[:target_count]`
- Deleted entire live feed CSV download block (~250 lines): feed scoring, streaming, non-stream fallback, price filtering, domain blocking
- Except handler now returns static products only (graceful degradation) instead of falling through to live download
- `_matches_query()` function preserved (used by static partner filtering)
- **Commit:** `b7062c5`

## Deviations from Plan

None -- plan executed exactly as written. Tasks 1 and 2 were partially completed by a prior session; this execution verified their correctness and committed the remaining uncommitted work.

## Decisions Made

1. **Circuit breaker at 100 products**: Conservative threshold -- normal DB has 11,000+ products. Only triggers on sync failure or fresh environment.
2. **Static partners always run**: CJ's 17 static partner lists and Awin's static products inject regardless of DB state, providing baseline product diversity.
3. **Graceful Awin degradation**: If catalog lookup fails, static products return instead of empty list.

## Known Stubs

None. All code paths are fully wired.

## Verification Results

All 8 success criteria passed:
1. `database.get_total_product_count()` returns int (0 in worktree, expected -- no DB data)
2. `MIN_SOURCES_TO_SKIP_LIVE` absent from multi_retailer_searcher.py
3. `_run_cj` appended unconditionally, uses `api_key=None` when DB healthy
4. Circuit breaker sets `_db_is_thin = True` and logs WARNING when count < 100
5. Awin returns unconditionally (no `>= target_count // 2` gate)
6. No live feed CSV download code remains (no "Searching Awin feeds for" log)
7. Awin except handler returns static products
8. All three files parse without syntax errors

## Self-Check: PASSED

All files exist, all commits verified.
