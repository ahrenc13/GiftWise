# Phase 3: 14-Item Output (Sonnet Portions) — Context

**Gathered:** 2026-04-02
**Status:** Ready for planning
**Source:** discuss-phase

<domain>
## Phase Boundary

Wire the splurge slot through the pipeline infrastructure and display it in the UI. The curator prompt changes (how Claude picks the splurge) are Opus-only — this phase does everything Sonnet can touch and leaves a ready-to-paste Opus prompt.

**What's already done (do NOT re-implement):**
- `search_products_diverse()` already returns `splurge_candidates` list ✓
- `multi_retailer_searcher.py` already reads `splurge_candidates` from DB results ✓
- `gift_curator.py` already has `is_splurge` in the prompt — Claude already designates one product as splurge ✓
- `recommendation_service.py` already passes `is_splurge` through at line ~868 ✓
- `templates/recommendations.html` already has gold badge CSS (`.badge.splurge`, `.splurge-label`), `data-splurge` attribute, and "SPLURGE PICK" label overlay ✓

**What's actually missing (scope of this phase):**
1. `splurge_candidates` not passed as a SEPARATE list to the curator — currently mixed into the regular pool. Opus needs them as a distinct list to reference explicitly in the prompt.
2. `splurge_ceiling` not computed or passed anywhere — derived from `price_signals.budget_category`, needed by the curator and the template.
3. Price ceiling not shown in the splurge tile.
4. Splurge tile not visually differentiated beyond the badge (no border).
5. `# SONNET-FLAG:` comment with the complete Opus prompt not yet in `gift_curator.py`.

</domain>

<decisions>
## Implementation Decisions

### Splurge Tile Visual Treatment
- **Decision: Gold border (option B).** Add a gold border to the splurge tile card — `border: 2px solid #d97706` (matches the existing gold badge color). Do NOT change card size or add a separate section header.
- The existing `.splurge-label` overlay and `.badge.splurge` badge are already correct — keep them.
- CSS target: `.recommendation-card[data-splurge="true"]` — add the border there.

### Price Ceiling Display
- **Decision: "Splurge Pick · up to $[ceiling]" in the badge (option B).** Update the badge text dynamically using `splurge_ceiling` from template context.
- Badge text: `Splurge Pick · up to ${{ splurge_ceiling }}` where splurge_ceiling is an integer (no decimals).
- Also update the `.splurge-label` overlay text to match.
- Ceiling mapping (compute in `giftwise_app.py` before passing to template):
  - `budget` → 300
  - `moderate` → 500
  - `premium` → 1000
  - `luxury` → 1500
  - `unknown` or missing → 500

### Splurge Candidates — Separate List Threading
- **Decision: Pass `splurge_candidates` as a separate field through the pipeline.**
- `multi_retailer_searcher.py`: Return `splurge_candidates` as a separate key in the return dict (alongside `all_products`). Currently they are mixed into `all_products` — keep them in the pool AND expose separately.
- `recommendation_service.py`: Extract `splurge_candidates` from the searcher return and pass to `curate_gifts()` as a new keyword arg.
- `gift_curator.py`: Accept `splurge_candidates=[]` parameter. Add them to the inventory block passed to Claude under a "SPLURGE CANDIDATES" header — even if the current prompt doesn't use them yet. Opus will add the instructions.
- The existing `is_splurge` logic in the prompt stays untouched — it's in the Opus-only zone.

### splurge_ceiling Computation
- Compute in `giftwise_app.py` in the route that passes recommendations to the template.
- Read from `profile.get('price_signals', {}).get('budget_category', 'unknown')`.
- Pass as `splurge_ceiling` to the template context.
- If profile is None or price_signals is missing, default to 500.

### SONNET-FLAG Comment
- Add to `gift_curator.py` immediately after the `rec_count` parameter definition (line ~31) and before the prompt construction.
- Use the exact Opus prompt from ROADMAP.md Phase 3 notes — do not paraphrase or shorten it.
- Comment prefix: `# SONNET-FLAG: Opus implements the splurge slot changes below.`

### Claude's Discretion
- Exact placement of `splurge_candidates` in the inventory block (before or after regular products)
- Whether `splurge_candidates` header in the curator prompt is labeled "SPLURGE CANDIDATES ($200–$1500):" or similar
- Whether to guard `splurge_ceiling` display with `{% if rec.is_splurge %}` (it should be — only show on splurge tiles)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Files to modify
- `multi_retailer_searcher.py` — Return `splurge_candidates` as a separate key in the return dict
- `recommendation_service.py` — Extract and thread `splurge_candidates` to `curate_gifts()`
- `gift_curator.py` — Add `splurge_candidates=[]` parameter; add to inventory block; add SONNET-FLAG comment
- `giftwise_app.py` — Compute `splurge_ceiling` from `budget_category`; pass to template
- `templates/recommendations.html` — Add gold border CSS; update badge text to include ceiling

### Do NOT modify (Opus-only zones)
- `gift_curator.py` curator prompt body (the reasoning framework, selection principles, ownership section)
- `profile_analyzer.py`
- `interest_ontology.py`
- `post_curation_cleanup.py` (brand relaxation, source diversity caps)

### Key code locations (read files to verify exact line numbers)
- `gift_curator.py` line ~31: `def curate_gifts(...)` — add `splurge_candidates=[]` param here
- `gift_curator.py` line ~220: `prompt = f"""` — splurge candidates should be added to the inventory block BEFORE this prompt, or as a section within it, above the SPLURGE PICK instruction (line ~247)
- `gift_curator.py` line ~247: existing `SPLURGE PICK:` instruction — DO NOT touch
- `recommendation_service.py` line ~868: `'is_splurge': gift.get('is_splurge', False)` — pipeline already threads this
- `multi_retailer_searcher.py` lines ~139–167: DB result extraction — `splurge_candidates` already read, add to return dict
- `templates/recommendations.html` line ~256: `.badge.splurge` CSS — add border to `.recommendation-card[data-splurge="true"]`
- `templates/recommendations.html` line ~698: `data-splurge="{{ 'true' if rec.is_splurge else 'false' }}"` — already correct
- `templates/recommendations.html` line ~772: `<span class="badge splurge">Splurge Pick</span>` — update text to include ceiling

### Architecture context
- `search_products_diverse()` in `database.py` already returns `{'regular': [...], 'splurge_candidates': [...], 'per_interest_counts': {...}}`
- `splurge_candidates` are products priced $200–$1500, capped at 20 items
- `is_splurge` already flows from curator → `recommendation_service.py` → template
- `price_signals.budget_category` values: `budget`, `moderate`, `premium`, `luxury`, `unknown`

</canonical_refs>

<specifics>
## Specific Requirements

- Gold border color: `#d97706` (matches existing badge gradient endpoint — keep consistent)
- Border spec: `2px solid #d97706`
- Badge text format: `Splurge Pick · up to ${{ splurge_ceiling }}`
- `splurge_ceiling` is always an integer (no decimals, no commas for <10000)
- Budget ceiling map: `{'budget': 300, 'moderate': 500, 'premium': 1000, 'luxury': 1500, 'unknown': 500}`
- Default ceiling when `budget_category` missing or unrecognized: 500
- SONNET-FLAG: use the exact Opus prompt from ROADMAP.md Phase 3 implementation notes (do not paraphrase)
- Do NOT add a separate section header or change card layout — gold border + badge text is the only visual change

</specifics>

<deferred>
## Deferred Ideas

None raised during discussion.

</deferred>

---

*Phase: 03-14-item-output-sonnet-portions*
*Context gathered: 2026-04-02 via discuss-phase*
