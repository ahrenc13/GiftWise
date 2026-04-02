---
phase: 03-14-item-output-sonnet-portions
plan: "02"
subsystem: frontend-ui
tags: [splurge, ui, css, curator, sonnet-flag]
dependency_graph:
  requires: ["03-01"]
  provides: ["splurge-gold-border", "dynamic-badge-text", "curator-opus-flag"]
  affects: ["templates/recommendations.html", "gift_curator.py"]
tech_stack:
  added: []
  patterns: ["CSS attribute selector targeting", "Jinja2 template variable in badge text"]
key_files:
  created: []
  modified:
    - templates/recommendations.html
    - gift_curator.py
decisions:
  - "Used CSS attribute selector .recommendation-card[data-splurge='true'] for gold border to avoid affecting non-splurge tiles"
  - "Replaced brief SONNET-FLAG with complete Opus prompt since existing flag lacked required verification content"
metrics:
  duration: "5 minutes"
  completed: "2026-04-02"
  tasks_completed: 2
  files_modified: 2
---

# Phase 03 Plan 02: Splurge Tile Gold Border + Dynamic Badge Text Summary

Gold border CSS on the splurge tile and budget-ceiling-aware badge text using `splurge_ceiling` Jinja2 variable, plus complete Opus implementation prompt in gift_curator.py.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Gold border CSS + dynamic badge text | a8cefbc | templates/recommendations.html |
| 2 | Complete SONNET-FLAG with Opus prompt | a8cefbc | gift_curator.py |

## What Was Built

### Task 1: Splurge Tile Visual Differentiation

Added three changes to `templates/recommendations.html`:

1. **Gold border CSS rule** (line 281-283): `.recommendation-card[data-splurge="true"] { border: 2px solid #d97706; }` — placed after the existing `.splurge-label` display rule. The `#d97706` amber color matches the existing badge gradient endpoint, creating visual consistency.

2. **Overlay label updated** (line 708): Changed from hardcoded `SPLURGE PICK` to `Splurge Pick · up to ${{ splurge_ceiling }}` — shows budget-derived ceiling (e.g., "Splurge Pick · up to $500").

3. **Badge text updated** (line 776): Changed from hardcoded `Splurge Pick` to `Splurge Pick · up to ${{ splurge_ceiling }}` — same dynamic ceiling in the card badge.

The `splurge_ceiling` variable is passed from `giftwise_app.py` (wired in plan 03-01) with a default of 500. Non-splurge tiles are unaffected — the gold border CSS uses the `data-splurge="true"` attribute selector.

### Task 2: Complete SONNET-FLAG in gift_curator.py

The existing SONNET-FLAG from plan 03-01 was a brief 4-line note. The plan's verification criteria required a complete Opus prompt with:
- `OPUS PROMPT:` header
- `rec_count from 10` instruction
- `splurge_candidates` wiring steps
- `budget_category` ceiling mapping
- `if money were no object` phrasing
- `Do NOT touch the gift reasoning framework` constraint

Replaced the brief comment with the full verbatim Opus prompt at lines 32-61. The original SPLURGE PICK instruction at line ~284 (`SPLURGE PICK: Designate exactly ONE product...`) is untouched.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Replaced incomplete SONNET-FLAG**
- **Found during:** Task 2 pre-check
- **Issue:** The SONNET-FLAG added by 03-01 was 4 lines and lacked the complete Opus prompt. The plan's verification criteria (`OPUS PROMPT:`, `rec_count from 10`, `if money were no object`, `Do NOT touch the gift reasoning framework`) would have failed.
- **Fix:** Replaced brief comment with the complete verbatim Opus prompt from the plan specification.
- **Files modified:** gift_curator.py
- **Commit:** a8cefbc

## Known Stubs

None — both badge locations now use the dynamic `splurge_ceiling` variable. The Opus curator prompt changes (rec_count 10→11, splurge slot parsing) are intentionally deferred to Opus and documented via SONNET-FLAG.

## Self-Check: PASSED

- `templates/recommendations.html` exists and contains `border: 2px solid #d97706` at line 283
- `templates/recommendations.html` contains 2 references to `splurge_ceiling` (lines 708, 776)
- `gift_curator.py` contains `SONNET-FLAG` with complete Opus prompt
- `gift_curator.py` original `SPLURGE PICK: Designate exactly ONE product` instruction preserved
- Commit a8cefbc exists in git log
