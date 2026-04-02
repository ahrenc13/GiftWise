---
phase: 02-catalog-first-source-separation
plan: 02
subsystem: search-pipeline
tags: [ebay-scoping, niche-only, session-latency, catalog-first]
dependency_graph:
  requires: [catalog-only-cj, catalog-only-awin, circuit-breaker]
  provides: [ebay-niche-scoping, ebay-cap]
  affects: [multi_retailer_searcher.py]
tech_stack:
  added: []
  patterns: [weak-coverage-threshold, niche-cap, filtered-profile-closure]
key_files:
  created: []
  modified:
    - multi_retailer_searcher.py
decisions:
  - EBAY_WEAK_COVERAGE_THRESHOLD set to 5 products -- interests with fewer DB products trigger eBay
  - EBAY_NICHE_CAP set to 7 -- max total eBay products per session across all weak interests
  - per_interest_counts pre-initialized as {} before DB try block -- DB failure triggers eBay for all interests (safe fallback)
metrics:
  duration: ~1min
  completed: 2026-04-02
  tasks_completed: 2
  tasks_total: 2
  files_modified: 1
requirements:
  - CAT-03
  - CAT-06
---

# Phase 02 Plan 02: eBay Niche-Only Scoping Summary

Scoped eBay searches to only fire for interests with thin DB coverage (<5 products), capped total eBay contribution at 7 items, and pre-initialized per_interest_counts to prevent NameError on DB failure.

## What Was Done

### Task 1: Pre-initialize per_interest_counts before DB try block
- Added `per_interest_counts = {}` and `interests = []` before the DB try block, alongside `all_products = []`
- Prevents NameError if the DB try block fails -- eBay scoping reads per_interest_counts after the try/except
- When DB fails, empty dict means all interests treated as weak-coverage (eBay fires for all -- safe fallback)
- **Commit:** `7a80489`

### Task 2: Add EBAY_NICHE_CAP constant and weak-interest eBay scoping
- Added module-level constants: `EBAY_WEAK_COVERAGE_THRESHOLD = 5`, `EBAY_NICHE_CAP = 7`
- `weak_interests` computed from `per_interest_counts` after DB try block -- interests with <5 DB products
- When all interests have sufficient coverage: eBay task NOT appended, logs "All interests have sufficient DB coverage"
- When weak interests exist: builds filtered `_ebay_profile` with only weak-coverage interests, passes to `search_products_ebay()`
- eBay results capped at `EBAY_NICHE_CAP` (7) via `products[:EBAY_NICHE_CAP]` before return
- Closure captures `_ebay_profile` (not full `profile`) so eBay only searches weak interests
- **Commit:** `6ef51b8`

## Deviations from Plan

None -- plan executed exactly as written.

## Decisions Made

1. **Threshold of 5 products**: Interests with fewer than 5 DB products are considered weak-coverage. With 11,000+ products in the catalog, most interests will have sufficient coverage.
2. **Cap of 7 items**: Limits total eBay contribution to prevent marketplace listings from dominating the pool. Low enough to keep eBay as supplement, high enough to fill real gaps.
3. **Pre-initialized defaults**: `per_interest_counts = {}` and `interests = []` before the try block ensures safe fallback behavior on DB failure (eBay fires for everything, same as before this change).

## Known Stubs

None. All code paths are fully wired.

## Verification Results

All success criteria passed:
1. `per_interest_counts = {}` initialized before DB try block -- NameError impossible
2. `EBAY_NICHE_CAP = 7` and `EBAY_WEAK_COVERAGE_THRESHOLD = 5` present as module-level constants
3. `weak_interests` computed from `per_interest_counts` before `_run_ebay`
4. eBay skipped when all interests have >= 5 products (log line present)
5. eBay called with `_ebay_profile` (filtered) when weak interests exist (log line present)
6. eBay results capped at EBAY_NICHE_CAP before return
7. No eBay results written to DB (comment preserved)
8. `multi_retailer_searcher.py` parses without syntax errors
9. Phase 02-01 invariants preserved (circuit breaker, no diversity gate)

## Self-Check: PASSED

All files exist, all commits verified.
