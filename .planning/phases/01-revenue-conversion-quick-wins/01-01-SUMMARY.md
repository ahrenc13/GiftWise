---
phase: "01"
plan: "01"
subsystem: tracking-and-catalog
tags: [tracking, analytics, catalog-sync, affiliate, awin]
dependency_graph:
  requires: []
  provides: [clean-guide-tracking, home-theater-sync-terms, body-jewelry-sync-terms]
  affects: [site_stats, catalog_sync, guide_funnel_analytics]
tech_stack:
  added: []
  patterns: [per-slug event tracking, INTEREST_CATEGORIES expansion]
key_files:
  modified:
    - giftwise_app.py
    - catalog_sync.py
decisions:
  - "Removed generic track_event('guide_hit') from guide route — per-slug version provides a superset of the data"
  - "Removed misclassified track_event('guide_hit') from blog route — blog posts should use blog_hit:slug, not guide_hit"
  - "Added home_theater_av category at priority 2 — covers AWOL Vision (Awin 98169) projector products"
  - "Added body_jewelry_piercing category at priority 2 — covers OUFER Body Jewelry (Awin 91941) products"
metrics:
  duration: "< 5 minutes"
  completed: "2026-04-01T23:49:41Z"
  tasks_completed: 2
  files_modified: 2
---

# Phase 01 Plan 01: Tracking Fix and Catalog Term Expansion Summary

**One-liner:** Removed duplicate/misclassified guide_hit tracking events and wired AWOL Vision + OUFER Body Jewelry into nightly catalog sync via 31 new interest terms.

## Tasks Completed

### Task 1: Fix guide and blog tracking event calls (giftwise_app.py)

**What changed:**

The `gift_guide_detail` route had two consecutive `track_event` calls:
- `track_event('guide_hit')` — generic, non-actionable (removed)
- `track_event(f'guide_hit:{slug}')` — per-slug, retained

The `blog_post` route had a misclassified call that used `guide_hit` instead of a blog-specific event:
- `track_event('guide_hit')` — wrong event type for blog posts (removed)
- `track_event(f'blog_hit:{slug}')` — correct per-slug blog event, retained

**Verification:**
```
grep -n "track_event('guide_hit')" giftwise_app.py
```
Returns zero lines — confirmed.

**Impact:** The admin dashboard `guide_hit` counter will no longer be inflated by blog post views. Blog traffic is now tracked under `blog_hit:slug` exclusively. Guide analytics are clean per-slug only.

### Task 2: Add home theater/projector and body jewelry sync terms (catalog_sync.py)

Two new categories added to `INTEREST_CATEGORIES`, both at priority 2 (weekly full sync):

**`home_theater_av`** — 13 terms covering projectors and home cinema equipment. Targets AWOL Vision (Awin ID 98169), an Awin-approved merchant selling 4K/laser projectors.

**`body_jewelry_piercing`** — 18 terms covering piercing jewelry types and materials. Targets OUFER Body Jewelry (Awin ID 91941), an Awin-approved merchant.

**Verification output:**
```
Projector/theater terms: ['4K projector', 'home projector', 'home theater', 'laser projector',
  'mini projector', 'outdoor projector', 'portable projector', 'projector', 'projector screen']
Body jewelry terms: ['body jewelry', 'body piercing jewelry', 'daith piercing jewelry',
  'piercing jewelry set', 'septum jewelry', 'septum ring', 'titanium body jewelry']
PASS
```

Both merchants are NOT in `_AWIN_SYNC_BLOCKED_ADVERTISER_NAMES` — confirmed products will sync.

## Files Modified

| File | Change |
|------|--------|
| `giftwise_app.py` | Removed 2 lines (lines 1762 and 1786 in original) |
| `catalog_sync.py` | Added 35 lines — two new INTEREST_CATEGORIES entries |

## Commit

`68ab416` — fix(01-01): remove redundant guide_hit event, add home theater + body jewelry sync terms

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- `giftwise_app.py` modified: confirmed (2 deletions)
- `catalog_sync.py` modified: confirmed (35 insertions)
- Commit `68ab416` exists: confirmed
- `grep track_event('guide_hit') giftwise_app.py` returns zero lines: confirmed
- Python verification script returned PASS: confirmed
