---
phase: 05-pre-launch-mobile-audit
plan: "02"
subsystem: frontend
tags: [mobile, ux, share, sticky-bar, css]
dependency_graph:
  requires: []
  provides: [mobile-sticky-share-bar]
  affects: [templates/recommendations.html]
tech_stack:
  added: []
  patterns: [fixed-positioning, safe-area-inset, backdrop-filter, css-media-query]
key_files:
  created: []
  modified:
    - templates/recommendations.html
decisions:
  - "z-index: 50 — below card modal (z-index 100+) so card expansion still works"
  - "bottom: 0 — flush at bottom, avoids overlapping OneSignal banner at bottom: 20px"
  - "env(safe-area-inset-bottom) in padding — handles iPhone home indicator automatically"
  - "display: none at desktop level — invisible on anything wider than 768px"
  - "shareViaText(false) — matches unlocked state; works for both locked and unlocked users"
metrics:
  duration: "~5 minutes"
  completed: "2026-04-03"
  tasks_completed: 2
  files_modified: 1
---

# Phase 05 Plan 02: Mobile Sticky Share Bar Summary

Floating sticky share bar added to the bottom of the recommendations page, visible on mobile only (display: none on desktop), so TikTok visitors who don't scroll the full 2,000-3,000px to reach the share section still see a prominent share prompt.

## What Was Built

A fixed-position `.mobile-share-bar` div with a single "Text this list" button wired to the existing `shareViaText(false)` function. The bar is:
- Hidden on desktop (`display: none` at the root level)
- Visible on mobile (`@media (max-width: 768px)` → `display: flex; position: fixed; bottom: 0`)
- Safe for iPhone home indicator (`padding-bottom: calc(12px + env(safe-area-inset-bottom))`)
- Below card modal overlays (`z-index: 50` vs card's `z-index: 100+`)
- Not conflicting with OneSignal banner (`bottom: 0` vs OneSignal's `bottom: 20px`)

## Where Changes Were Made

### HTML (Task 1)
Inserted after line 1045 (closing `</div>` of the main `.container` div) and before `{% endblock %}` at line 1054:

```html
<!-- Floating share bar: mobile only, always visible -->
<div class="mobile-share-bar" id="mobile-share-bar">
    <button class="mobile-share-btn" onclick="shareViaText(false)">
        📱 Text this list
    </button>
</div>
```

### CSS (Tasks 1 + 2)
Added after the existing `@media (max-width: 768px)` block (line 647) and before `{% endblock %}` at line 689 in the `{% block extra_css %}` section:

- `.mobile-share-bar { display: none; }` — desktop hide rule
- New `@media (max-width: 768px)` block containing:
  - `body { padding-bottom: 80px; }` — prevents last recommendation card from being hidden behind the bar
  - `.mobile-share-bar { display: flex; position: fixed; ... }` — mobile show rule with frosted glass effect
  - `.mobile-share-btn { ... }` — green gradient button matching existing unlocked share button

## Existing Share Section Unchanged

The share section at lines 917-972 (locked + unlocked states) was not modified. Verified:
- `shareViaText(true)` (locked state) still present
- `shareViaText(false)` (unlocked state) still present on original button
- `share-section` div structure intact

## Jinja2 Parse Check

```
Template parses OK
```

## Verification Results

```
grep mobile-share-bar|mobile-share-btn:
650:.mobile-share-bar {         ← CSS display:none desktop rule
659:    .mobile-share-bar {     ← @media override display:flex
675:    .mobile-share-btn {     ← button styles
1048:<div class="mobile-share-bar" ...>  ← HTML element
1049:    <button class="mobile-share-btn" ...>  ← HTML button
```

5 hits — all expected elements present.

## Known Stubs

None. The button calls the existing `shareViaText(false)` function which is fully implemented and tested on iOS Safari and Android Chrome.

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- `templates/recommendations.html` modified: FOUND
- CSS `.mobile-share-bar { display: none }` present: FOUND (line 650)
- CSS `@media` `.mobile-share-bar { display: flex }` present: FOUND (line 659)
- CSS `body { padding-bottom: 80px }` inside media query: FOUND (line 656)
- HTML div with `class="mobile-share-bar"`: FOUND (line 1048)
- HTML button with `onclick="shareViaText(false)"`: FOUND (line 1049)
- Template parse: PASSED
