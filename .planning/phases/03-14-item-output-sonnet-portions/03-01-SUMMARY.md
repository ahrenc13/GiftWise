---
phase: 03-14-item-output-sonnet-portions
plan: "01"
subsystem: pipeline-wiring
tags: [splurge, curator, pipeline, giftwise_app, recommendation_service]
dependency_graph:
  requires: []
  provides: [splurge_candidates-pipeline, splurge_ceiling-template]
  affects: [gift_curator.py, recommendation_service.py, multi_retailer_searcher.py, giftwise_app.py]
tech_stack:
  added: []
  patterns: [dict-return-type-wiring, budget-ceiling-map]
key_files:
  created: []
  modified:
    - multi_retailer_searcher.py
    - recommendation_service.py
    - gift_curator.py
    - giftwise_app.py
decisions:
  - "splurge_candidates[:5] kept in regular pool AND exposed separately in dict return"
  - "SONNET-FLAG comment added to gift_curator.py for Opus follow-up on rec_count + splurge prompt"
  - "splurge_ceiling defaults to 500 in favorites views where profile is unavailable"
metrics:
  duration: "5 minutes"
  completed: "2026-04-02T02:59:03Z"
  tasks_completed: 2
  files_modified: 4
---

# Phase 3 Plan 01: Splurge Pipeline Wiring Summary

Thread `splurge_candidates` as a separate list from DB through searcher, recommendation_service, and curator inventory block; compute `splurge_ceiling` int from `budget_category` for template badge text.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Thread splurge_candidates through searcher and recommendation_service | f7f2355 | recommendation_service.py |
| 2 | Add splurge_candidates to curator inventory + compute splurge_ceiling | f7f2355 | gift_curator.py, giftwise_app.py |

Note: `multi_retailer_searcher.py` dict return and `recommendation_service._search_products()` unpack were already implemented before this plan executed. This plan completed the remaining gaps.

## What Was Built

### multi_retailer_searcher.py (already done)
- Pre-initializes `splurge_candidates = []` before DB try block (line 84)
- Returns `{'products': all_products, 'splurge_candidates': splurge_candidates}` dict (line 413)
- Keeps `splurge_candidates[:5]` mixed into regular pool AND exposes full list separately

### recommendation_service.py
- `_search_products()` already unpacked dict return with isinstance guard
- `_curate_gifts()` signature extended: `enriched_profile: Optional[Dict], splurge_candidates=None` (line 421)
- `curate_gifts()` call at line 465 now passes `splurge_candidates=splurge_candidates`
- `generate_recommendations()` already called `_curate_gifts(..., splurge_candidates=splurge_candidates)`

### gift_curator.py
- `curate_gifts()` signature: added `splurge_candidates=None` after `ontology_briefing=None`
- SONNET-FLAG comment added at line 32 for Opus task (update rec_count 10→11, update SPLURGE PICK instruction to prefer from splurge candidates section)
- After `products_summary` is built, appends `"━━━ SPLURGE CANDIDATES ($200-$1500) ━━━"` section if `splurge_candidates` is non-empty
- No Opus-only prompt text modified (SPLURGE PICK instruction at line ~247 untouched)

### giftwise_app.py
- `_SPLURGE_CEILING_MAP = {'budget': 300, 'moderate': 500, 'premium': 1000, 'luxury': 1500}` added near config constants (line ~501)
- `view_recommendations()`: computes `splurge_ceiling` from `(user.get('recipient_profile') or {}).get('price_signals', {}).get('budget_category', 'unknown')`, defaults to 500
- All 3 `render_template('recommendations.html', ...)` calls now pass `splurge_ceiling`
  - Main recommendations view: dynamic ceiling from budget_category
  - Favorites view (empty): `splurge_ceiling=500` default
  - Favorites view (with items): `splurge_ceiling=500` default

## Deviations from Plan

None — plan executed exactly as written. All 4 files modified as specified. The multi_retailer_searcher.py and the _search_products() unpack portion were already in place from prior work; only the gaps were filled.

## Known Stubs

None. All wiring is complete end-to-end. The splurge tile visual (gold border CSS, dynamic badge text in recommendations.html) and the curator prompt update (rec_count 10→11, SPLURGE PICK preference instruction) are deferred to Plans 02 and later per ROADMAP.md Phase 2 TODO. These are intentional per-plan boundaries, not stubs blocking this plan's goal.

## Self-Check: PASSED

Files modified exist and contain expected content:
- `splurge_candidates` in curate_gifts() signature: confirmed
- `SPLURGE CANDIDATES` section in inventory block: confirmed
- `_SPLURGE_CEILING_MAP` in giftwise_app.py: confirmed
- `splurge_ceiling` passed to all 3 recommendations.html render calls: confirmed
- Commit f7f2355 exists: confirmed
