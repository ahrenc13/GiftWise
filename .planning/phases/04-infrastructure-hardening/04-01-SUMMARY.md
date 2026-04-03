---
phase: 04-infrastructure-hardening
plan: "01"
subsystem: codebase-cleanup
tags: [dead-code-removal, skimlinks, infrastructure]
dependency_graph:
  requires: []
  provides: [INF-01, INF-02]
  affects: [multi_retailer_searcher, recommendation_service, products/ingestion]
tech_stack:
  added: []
  patterns: [dead-code-removal]
key_files:
  created: []
  modified:
    - templates/base.html
    - giftwise_app.py
    - multi_retailer_searcher.py
    - recommendation_service.py
    - revenue_optimizer.py
    - image_fetcher.py
    - product_schema.py
    - models.py
    - config.py
    - config_service.py
    - config/settings.py
    - products/ingestion.py
  deleted:
    - skimlinks_searcher.py
decisions:
  - "Skimlinks code removed entirely — defunct service, no env vars set in production, API non-functional"
  - "scripts/convert_templates.py and scripts/verify_templates.py left untouched — contain regex patterns for migration utilities, not live code"
metrics:
  duration: "5 minutes"
  completed_date: "2026-04-02"
  tasks_completed: 2
  files_changed: 13
  lines_removed: 484
---

# Phase 04 Plan 01: Remove Skimlinks Dead Code Summary

**One-liner:** Deleted `skimlinks_searcher.py` and purged all Skimlinks constants, functions, and references from 12 Python files and `base.html`, eliminating a defunct service that fired a broken network request on every page load.

## What Was Removed

### Files Deleted
- `skimlinks_searcher.py` — entire Skimlinks Product API integration module

### HTML Changes
- `templates/base.html` — removed Skimlinks JS async loader (publisher ID 298548X178612, 11 lines)

### Python Changes

| File | What Was Removed |
|------|-----------------|
| `giftwise_app.py` | `SKIMLINKS_PUBLISHER_ID` module constant; URL-wrapping block in `_apply_affiliate_tag()` |
| `multi_retailer_searcher.py` | `_run_skimlinks` closure block (14 lines); `Skimlinks=...` in availability log line |
| `recommendation_service.py` | `self.skimlinks_publisher_id` init var; 4 Skimlinks kwargs passed to `search_all_retailers()`; URL-wrapping block in `_apply_affiliate_tag()` |
| `products/ingestion.py` | `try/except import skimlinks_searcher` block; entire `refresh_skimlinks()` function (54 lines); `'skimlinks'` from retailer dict, results dict, logger line, CLI choices |
| `revenue_optimizer.py` | `'skimlinks': 0.04` from commission rates dict |
| `image_fetcher.py` | `'skimlinks'` from platform list; `'skimlinks': _extract_skimlinks_image` from dispatcher dict; entire `_extract_skimlinks_image()` function (14 lines) |
| `product_schema.py` | `'skimlinks': 0.03` from commission rates dict; entire `Product.from_skimlinks()` classmethod (47 lines); `'skimlinks': Product.from_skimlinks` from dispatcher dict; `'skimlinks'` from platform docstring |
| `models.py` | `'skimlinks'` from retailer type annotation comment |
| `config.py` | 4 Skimlinks env var constants; priority weight entry; product limit entry; warning log block; status print line |
| `config_service.py` | 4 Skimlinks fields from `AffiliateConfig` dataclass; 4 Skimlinks env var reads in `from_env()`; `'skimlinks'` from `get_retailer_availability()` dict |
| `config/settings.py` | 4 Skimlinks fields from `RetailerSettings` dataclass; `'skimlinks'` from `get_available_retailers()` dict |

### Intentionally Left Untouched
- `scripts/convert_templates.py` — contains regex patterns to strip Skimlinks JS during template migration. Migration utility, not live code. Contains `skimlinks`/`298548X178612` in regex strings only.
- `scripts/verify_templates.py` — contains a check for Skimlinks in template content. Verification utility, not live code.

## Verification Output

```
grep -rn "skimlinks|skimresources|SKIMLINKS|298548X178612" . \
  --include="*.py" --include="*.html" --exclude-dir=.git \
  | grep -v "scripts/convert_templates.py" \
  | grep -v "scripts/verify_templates.py"

(no output — zero matches)
```

All 10 modified Python files pass `ast.parse()` syntax check.

## Deviations from Plan

None — plan executed exactly as written.

**Note on Task 1 pre-state:** When execution began, `skimlinks_searcher.py` was already deleted, `giftwise_app.py` already had the Skimlinks constant and URL-wrapping removed, and `templates/base.html` already had the JS snippet removed. These were pre-existing edits in the working tree (unstaged). Task 1 is documented as complete since all its conditions were already met; the changes were staged and committed as part of the single commit for this plan.

## Self-Check: PASSED

- `skimlinks_searcher.py` does not exist: CONFIRMED
- Zero `skimlinks`/`skimresources`/`SKIMLINKS` in any `.py` or `.html` file (excluding harmless scripts): CONFIRMED
- All modified Python files pass syntax check: CONFIRMED
- 13 files changed, 484 lines deleted in commit `1050156`
