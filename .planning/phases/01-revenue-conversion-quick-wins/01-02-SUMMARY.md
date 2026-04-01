---
phase: "01"
plan: "02"
subsystem: awin-static-products
tags: [affiliate, awin, static-products, deep-links]
dependency_graph:
  requires: []
  provides: [youngelectricbikes-static-products, tayst-coffee-static-products, vitajuwel-awin-links, vsgo-awin-links]
  affects: [awin_searcher._get_awin_static_products]
tech_stack:
  added: []
  patterns: [awin-deep-link-format]
key_files:
  created: []
  modified:
    - awin_searcher.py
decisions:
  - "Used !!id!! publisher ID placeholder consistent with existing Awin deep link convention"
  - "Young Electric Bikes triggers overlap with OUTFITR triggers by design — both brands benefit from cycling/e-bike interest matches"
metrics:
  duration: "~5 minutes"
  completed: "2026-04-01"
  tasks_completed: 2
  files_modified: 1
---

# Phase 01 Plan 02: Add youngelectricbikes + Tayst Static Products, Fix VitaJuwel + VSGO Awin Links Summary

**One-liner:** Added Young Electric Bikes (3 e-bike products, awinmid=120209) and Tayst Coffee (3 sustainable coffee products, awinmid=90529) static product lists to awin_searcher.py, and replaced 5 placeholder direct-site URLs in VitaJuwel and VSGO entries with proper Awin deep links.

## Tasks Completed

### Task 1: Add youngelectricbikes and Tayst Coffee static product lists

Added two new module-level constants and corresponding trigger blocks in `_get_awin_static_products()`:

**`_YOUNG_ELECTRIC_BIKES_ALL_PRODUCTS`** — 3 products (awinmid=120209):
- E-Scout Pro Electric Mountain Bike ($1,499)
- E-Cross Pro Electric Commuter Bike ($1,299)
- E-Scout Standard Electric Mountain Bike ($999)
- Triggers: cycling, biking, bike, bicycle, cyclist, e-bike, ebike, electric bike, mountain bike, trail, outdoor adventure, commuting

**`_TAYST_COFFEE_ALL_PRODUCTS`** — 3 products (awinmid=90529):
- 6-Month Prepaid Subscription ($89)
- Gift Box Sampler 3 Roasts ($29)
- Monthly Subscription ($19)
- Triggers: coffee, espresso, cappuccino, latte, morning routine, sustainability, sustainable, eco, eco-friendly, environment, environmentalist, zero waste, compost, subscription box

Both sets of constants placed after `_OUTFITR_ALL_PRODUCTS` and before `_get_awin_static_products()`. Trigger blocks placed inside the function after the OUTFITR block and before `return results`.

### Task 2: Fix VitaJuwel and VSGO placeholder links

**VitaJuwel (awinmid=97077)** — 3 products updated:
- `via-indian-summer`: replaced `https://www.vitajuwel.us/products/via-indian-summer` with proper Awin deep link
- `via-wellness`: replaced `https://www.vitajuwel.us/products/via-wellness` with proper Awin deep link
- `era-wellness`: replaced `https://www.vitajuwel.us/products/era-wellness` with proper Awin deep link
- Removed `# Replace with Awin deep link` comment from each entry

**VSGO (awinmid=120898)** — 2 products updated:
- Black Snipe Camera Backpack: replaced `/collections/bags` with product-specific deep link to `/products/black-snipe-camera-backpack`
- Pocket Ranger Camera Sling Bag: replaced `/collections/bags` with product-specific deep link to `/products/pocket-ranger-camera-sling-bag`
- Removed `# Replace with Awin deep link to specific SKU` comment from each entry

## Files Modified

- `/home/user/GiftWise/awin_searcher.py` — 84 insertions, 5 deletions

## Verification Results

```
python3 verification script → PASS
```

All assertions passed:
- `_YOUNG_ELECTRIC_BIKES_ALL_PRODUCTS` exists with 3 entries, all containing `awinmid=120209`
- `_TAYST_COFFEE_ALL_PRODUCTS` exists with 3 entries, all containing `awinmid=90529`
- All `_VITAJUWEL_ALL_PRODUCTS` entries contain `awinmid=97077`
- All `_VSGO_ALL_PRODUCTS` entries contain `awinmid=120898` and no longer reference `/collections/bags`

## Commit

`cff0475` — feat(01-02): add youngelectricbikes + Tayst static products, fix VitaJuwel + VSGO Awin links

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. All products have proper Awin deep links. `image_url` is intentionally empty (`""`) — consistent with existing static product convention where images are resolved programmatically from inventory rather than hardcoded.

## Self-Check: PASSED

- `/home/user/GiftWise/awin_searcher.py` — modified and committed
- `.planning/phases/01-revenue-conversion-quick-wins/01-02-SUMMARY.md` — this file
- Commit `cff0475` verified present in git log
