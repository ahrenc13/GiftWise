# Phase 3: 14-Item Output (Sonnet Portions) - Research

**Researched:** 2026-04-02
**Domain:** Flask pipeline wiring + Jinja2 template rendering
**Confidence:** HIGH

## Summary

Phase 3 wires splurge candidates through the existing pipeline and adds visual differentiation in the UI. The research shows that **most infrastructure is already built** -- `search_products_diverse()` already separates splurge candidates, the template already has splurge CSS and `data-splurge` attributes, and `is_splurge` already flows from curator output to the template. The gaps are narrow and well-defined: (1) splurge candidates are mixed into the regular pool instead of being threaded separately, (2) `curate_gifts()` has no `splurge_candidates` parameter, (3) `splurge_ceiling` is never computed or passed to the template, (4) no gold border CSS exists, and (5) no SONNET-FLAG comment exists in `gift_curator.py`.

**Primary recommendation:** This is a threading/plumbing phase -- follow the data flow from DB to template, add the missing connections at each layer, and avoid touching any Opus-only prompt logic.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Splurge tile visual:** Gold border `2px solid #d97706` on `.recommendation-card[data-splurge="true"]`. No card size change, no section header.
- **Price ceiling display:** Badge text `Splurge Pick · up to ${{ splurge_ceiling }}` -- also update `.splurge-label` overlay text.
- **Ceiling map:** `{'budget': 300, 'moderate': 500, 'premium': 1000, 'luxury': 1500, 'unknown': 500}`. Default 500.
- **splurge_candidates threading:** Pass as separate key through pipeline. Keep in regular pool AND expose separately.
- **splurge_ceiling computation:** In `giftwise_app.py` recommendations route, from `profile.get('price_signals', {}).get('budget_category', 'unknown')`.
- **SONNET-FLAG placement:** After `rec_count` parameter in `gift_curator.py` (~line 31). Use exact Opus prompt from ROADMAP.md.

### Claude's Discretion
- Placement of `splurge_candidates` in inventory block (before or after regular products)
- Header label for splurge candidates section in curator prompt
- Whether to guard `splurge_ceiling` display with `{% if rec.is_splurge %}`

### Deferred Ideas (OUT OF SCOPE)
None raised during discussion.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| OUT-01 | `search_products_diverse()` returns separate `splurge_candidates` list passed through pipeline | Already returns it (line 514). Gap: `multi_retailer_searcher.py` mixes them into `all_products` at line 156 instead of threading separately. |
| OUT-02 | Splurge candidates included in curator inventory payload | Gap: `curate_gifts()` has no `splurge_candidates` param. Need to add param + inventory section. |
| OUT-03 | Visually differentiated splurge tile in template | Partially done: badge, label, `data-splurge` attr exist. Gap: no gold border CSS rule. |
| OUT-04 | Splurge badge shows budget_category ceiling | Gap: badge text is hardcoded "Splurge Pick". `splurge_ceiling` not computed or passed to template. |
| OUT-05 | SONNET-FLAG comment in `gift_curator.py` with Opus prompt | Gap: does not exist yet. |
</phase_requirements>

## Detailed Code Analysis (Question-by-Question)

### Q1: What does `search_products_diverse()` return?

**File:** `database.py` lines 408-518
**Status:** ALREADY DONE

Returns a dict with three keys:
```python
return {
    'regular': regular[:limit],           # Products under $200
    'splurge_candidates': splurge[:20],    # Products $200-$1500, capped at 20
    'per_interest_counts': per_interest_counts,  # Dict of interest -> count
}
```

Separation logic (lines 509-512): products with `splurge_min <= price <= splurge_max` go to `splurge`, everything else to `regular`. Default thresholds: `splurge_min=200.0, splurge_max=1500.0`.

**No changes needed to `database.py`.**

### Q2: How does `multi_retailer_searcher.py` handle splurge candidates?

**File:** `multi_retailer_searcher.py` lines 140-167
**Status:** PARTIALLY DONE -- splurge candidates extracted but NOT threaded separately

Current code (lines 140-156):
```python
db_result = database.search_products_diverse(
    interests, limit=target_count * 2, max_per_category=4
)
db_products = db_result.get('regular', [])
splurge_candidates = db_result.get('splurge_candidates', [])
per_interest_counts = db_result.get('per_interest_counts', {})
# ...
# Combine regular + a few splurge candidates for the pool
all_db_rows = db_products + splurge_candidates[:5]
```

The `splurge_candidates` variable is extracted but then 5 of them are mixed into `all_db_rows` (line 156). The function signature returns a flat list (line 409): `return all_products`.

**What needs to change:**
1. Keep `splurge_candidates[:5]` in the regular pool (don't break existing behavior)
2. ALSO return `splurge_candidates` as a separate key
3. Change return type from `list` to `dict`: `{'products': all_products, 'splurge_candidates': splurge_candidates}`
4. Update the docstring (line 70: "Returns mixed list of products" -> update)
5. Initialize `splurge_candidates = []` at module scope alongside `per_interest_counts = {}` (line 79) so it survives if the DB block fails

**Caller impact:** `recommendation_service.py` line 342 calls this function and expects a list. Must update `_search_products()` (line 323) to unpack the dict.

### Q3: What does `gift_curator.py` have for splurge?

**File:** `gift_curator.py`
**Status:** PARTIALLY DONE -- prompt has splurge instructions but no separate candidates input

**Function signature** (line 30):
```python
def curate_gifts(profile, products, recipient_type, relationship, claude_client,
                 rec_count=10, enhanced_search_terms=None, enrichment_context=None,
                 model=None, ontology_briefing=None):
```
No `splurge_candidates` parameter exists.

**Existing splurge prompt instruction** (line 247):
```
- SPLURGE PICK: Designate exactly ONE product as the "splurge pick" — an aspirational gift
  that's above {pronoun_possessive} typical budget but perfectly matched to
  {pronoun_possessive} strongest interest. Set "is_splurge": true for that one product only,
  false for all others.
```
This instruction is part of the Opus-only prompt block. It tells the curator to pick one product from the regular pool and mark it `is_splurge: true`. This works today.

**JSON schema** (lines 261-272) already includes `"is_splurge": false` in the product_gifts schema.

**What needs to change:**
1. Add `splurge_candidates=None` parameter to `curate_gifts()` signature
2. If `splurge_candidates` is non-empty, append a "SPLURGE CANDIDATES" section to `products_summary` (the inventory block at line 208)
3. Add `# SONNET-FLAG:` comment with the complete Opus prompt from ROADMAP.md
4. Do NOT modify the existing SPLURGE PICK instruction at line 247 -- that is Opus-only zone

### Q4: How does `recommendation_service.py` call `curate_gifts()`?

**File:** `recommendation_service.py` lines 453-460
**Status:** NEEDS UPDATE

```python
curated = self.curate_gifts(
    profile_for_backend, products_for_curator, recipient_type, relationship,
    self.claude_client, rec_count=product_rec_count + 4,
    enhanced_search_terms=enhanced_search_terms,
    enrichment_context=enrichment_context,
    model=self.curator_model,
    ontology_briefing=ontology_briefing
)
```

No `splurge_candidates` argument is passed. `product_rec_count` is hardcoded to 10 (line 411).

**What needs to change:**
1. `_search_products()` (line 323) must unpack the new dict return from `search_products_multi_retailer`
2. Store `splurge_candidates` on `self` or pass through to `_curate_gifts()`
3. `_curate_gifts()` (line 407) must accept and forward `splurge_candidates` to `curate_gifts()`
4. Add `splurge_candidates=splurge_candidates` to the call at line 453

**Data flow path:**
```
_search_products() → returns (products, splurge_candidates)
  ↓
generate_recommendations() stores both
  ↓
_curate_gifts() receives splurge_candidates
  ↓
curate_gifts() gets splurge_candidates param
```

### Q5: How does `giftwise_app.py` pass data to recommendations template?

**File:** `giftwise_app.py` lines 3614-3691
**Status:** NEEDS UPDATE

The `view_recommendations()` function (line 3616) renders the template with:
```python
return render_template('recommendations.html',
                     recommendations=visible_recommendations,
                     data_quality=data_quality,
                     connected_count=connected_count,
                     user=user,
                     favorites=favorites,
                     position_number=position_number,
                     unlocked=unlocked,
                     total_count=total_count,
                     product_count=product_count,
                     experience_count=experience_count,
                     locked_count=locked_count)
```

No `splurge_ceiling` is passed. The profile IS available via `user.get('recipient_profile', {})` -- stored at line 3461 during generation.

**What needs to change:**
1. Before `render_template`, compute `splurge_ceiling`:
```python
profile = user.get('recipient_profile', {}) or {}
budget_cat = profile.get('price_signals', {}).get('budget_category', 'unknown')
CEILING_MAP = {'budget': 300, 'moderate': 500, 'premium': 1000, 'luxury': 1500}
splurge_ceiling = CEILING_MAP.get(budget_cat, 500)
```
2. Add `splurge_ceiling=splurge_ceiling` to the `render_template` call
3. Also update the other `render_template('recommendations.html', ...)` calls at lines 3896 and 3904 (favorites view) -- pass `splurge_ceiling=500` as default there
4. Also update line 3853 (shared recommendations) if needed

### Q6: What does `templates/recommendations.html` already have for splurge?

**File:** `templates/recommendations.html`
**Status:** MOSTLY DONE -- CSS and attributes exist, needs border + dynamic badge text

**CSS already exists (lines 256-280):**
```css
.badge.splurge {
    background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
    color: white;
    font-size: 0.8em;
}

.splurge-label {
    display: none;
    position: absolute;
    top: 10px;
    left: 10px;
    background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
    color: white;
    padding: 4px 10px;
    border-radius: 12px;
    font-size: 0.75em;
    font-weight: 700;
    letter-spacing: 0.5px;
    z-index: 2;
    box-shadow: 0 2px 6px rgba(217, 119, 6, 0.3);
}

.recommendation-card[data-splurge="true"] .splurge-label {
    display: block;
}
```

**HTML already exists:**
- Line 698: `data-splurge="{{ 'true' if rec.is_splurge else 'false' }}"` -- correct
- Line 704: `<span class="splurge-label">SPLURGE PICK</span>` -- hardcoded text, needs ceiling
- Line 771-772: `{% if rec.is_splurge %}<span class="badge splurge">Splurge Pick</span>` -- hardcoded text

**What needs to change:**
1. Add CSS rule: `.recommendation-card[data-splurge="true"] { border: 2px solid #d97706; }`
2. Update line 704: `SPLURGE PICK` -> `Splurge Pick · up to ${{ splurge_ceiling }}`
3. Update line 772: `Splurge Pick` -> `Splurge Pick · up to ${{ splurge_ceiling }}`
4. Guard ceiling display: `{% if splurge_ceiling %}` (template handles missing var gracefully with Jinja2 defaults)

### Q7: What is `price_signals` in the profile dict?

**File:** `profile_analyzer.py` lines 860-864
**Status:** ALREADY DONE -- Claude outputs this in every profile

JSON schema in the prompt:
```json
"price_signals": {
    "estimated_range": "$X-$Y",
    "budget_category": "budget|moderate|premium|luxury",
    "notes": "observations about price comfort"
}
```

Default on parse failure (line 972): `"price_signals": {}`

The `budget_category` values are: `budget`, `moderate`, `premium`, `luxury`. When the LLM fails to output it or the profile parse fails, the field will be empty dict or missing.

**No changes needed to `profile_analyzer.py`.**

## Architecture Patterns

### Data Flow (Current)
```
database.search_products_diverse()
  → returns {'regular': [...], 'splurge_candidates': [...], 'per_interest_counts': {...}}
  → multi_retailer_searcher: extracts splurge_candidates, mixes 5 into pool, DISCARDS rest
  → returns flat list (all_products)
  → recommendation_service._search_products(): receives flat list
  → recommendation_service._curate_gifts(): passes flat list to curator
  → gift_curator.curate_gifts(): receives flat list as `products`
  → curator output includes is_splurge=true on one product
  → recommendation_service._format_product_recommendations(): preserves is_splurge (line 868)
  → template: renders badge/label for is_splurge=true items
```

### Data Flow (After Phase 3)
```
database.search_products_diverse()
  → returns {'regular': [...], 'splurge_candidates': [...], 'per_interest_counts': {...}}
  → multi_retailer_searcher: extracts splurge_candidates, mixes 5 into pool, ALSO returns separately
  → returns {'products': all_products, 'splurge_candidates': splurge_candidates}
  → recommendation_service._search_products(): unpacks both
  → recommendation_service._curate_gifts(): forwards splurge_candidates
  → gift_curator.curate_gifts(): receives splurge_candidates param, appends to inventory block
  → [Opus later: prompt tells Claude to pick from splurge candidates]
  → curator output includes is_splurge=true on one product
  → template: renders gold border + dynamic badge with ceiling
```

### Key Concern: Return Type Change in `search_products_multi_retailer`

Changing from `return all_products` (list) to `return {'products': ..., 'splurge_candidates': ...}` (dict) is a breaking change. **Check all callers:**

1. `recommendation_service.py` line 342 -- the only production caller. Must update.
2. No other callers found in the codebase.

The change is safe as long as `_search_products()` in `recommendation_service.py` is updated in the same commit.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Budget ceiling mapping | Switch statement or complex logic | Simple dict lookup `CEILING_MAP.get(cat, 500)` | 5 values, dict is cleaner |
| Splurge tile ordering | Sorting/reordering recommendations | Existing tile order from pipeline | `is_splurge` items already render in order; the curator places them. No reordering needed. |

## Common Pitfalls

### Pitfall 1: Breaking the Return Type Without Updating Callers
**What goes wrong:** Changing `search_products_multi_retailer` to return a dict while `_search_products()` still expects a list causes `len(products)` to fail.
**How to avoid:** Update both files in the same plan/task. The caller is at `recommendation_service.py` line 342-367.

### Pitfall 2: Template Variable Not Passed to All render_template Calls
**What goes wrong:** `splurge_ceiling` passed in the main recommendations route but not in the favorites or shared routes, causing Jinja2 `UndefinedError`.
**How to avoid:** Search for ALL `render_template('recommendations.html'` calls (lines 3680, 3896, 3904). Add `splurge_ceiling` to each, defaulting to 500 when profile is unavailable.

### Pitfall 3: Modifying the Opus-Only Prompt
**What goes wrong:** Accidentally editing the SPLURGE PICK instruction at line 247 or any surrounding prompt text triggers the Opus-only rule.
**How to avoid:** The `splurge_candidates` section should be added to the inventory block (line 208 area) as data, NOT as prompt instructions. The SONNET-FLAG comment goes near the function signature.

### Pitfall 4: splurge_candidates Variable Scope in multi_retailer_searcher
**What goes wrong:** `splurge_candidates` is defined inside the `try` block (line 144). If the DB query fails, it's undefined when the function tries to return it.
**How to avoid:** Pre-initialize `splurge_candidates = []` at module/function scope (same pattern as `per_interest_counts = {}` at line 79).

### Pitfall 5: Missing recipient_profile on User Object
**What goes wrong:** User ran generation before Phase 3 deployed, so `user.get('recipient_profile')` returns `None`. `None.get('price_signals')` throws AttributeError.
**How to avoid:** Use `(user.get('recipient_profile') or {}).get('price_signals', {}).get('budget_category', 'unknown')`. The `or {}` handles `None`.

## Code Examples

### Ceiling Computation (giftwise_app.py)
```python
# Compute splurge ceiling from profile budget_category
_SPLURGE_CEILING_MAP = {
    'budget': 300,
    'moderate': 500,
    'premium': 1000,
    'luxury': 1500,
}

profile = (user.get('recipient_profile') or {})
budget_cat = profile.get('price_signals', {}).get('budget_category', 'unknown')
splurge_ceiling = _SPLURGE_CEILING_MAP.get(budget_cat, 500)
```

### Return Type Change (multi_retailer_searcher.py)
```python
# Line 79: Pre-initialize alongside per_interest_counts
splurge_candidates = []

# Line 409: Change return
return {'products': all_products, 'splurge_candidates': splurge_candidates}
```

### Splurge Candidates in Inventory Block (gift_curator.py)
```python
# After products_summary is built (line 208), before prompt construction:
if splurge_candidates:
    splurge_formatted = format_products(splurge_candidates)
    products_summary += f"\n\n━━━ SPLURGE CANDIDATES ($200-$1500) ━━━\n\n{splurge_formatted}\n\n━━━ END SPLURGE CANDIDATES ━━━"
```

### Gold Border CSS (recommendations.html)
```css
.recommendation-card[data-splurge="true"] {
    border: 2px solid #d97706;
}
```

### Dynamic Badge Text (recommendations.html)
```html
<!-- Line 704 -->
<span class="splurge-label">Splurge Pick · up to ${{ splurge_ceiling }}</span>

<!-- Line 772 -->
<span class="badge splurge">Splurge Pick · up to ${{ splurge_ceiling }}</span>
```

## Files to Modify (Complete List)

| File | Lines | Change | Risk |
|------|-------|--------|------|
| `multi_retailer_searcher.py` | 79, 156, 409 | Pre-init `splurge_candidates`, return as dict | Medium -- breaking return type |
| `recommendation_service.py` | 323-374, 407-460 | Unpack dict, thread `splurge_candidates` to curator | Low |
| `gift_curator.py` | 30, ~208 | Add param, add inventory section, add SONNET-FLAG | Low -- no prompt changes |
| `giftwise_app.py` | 3616-3691, 3896, 3904 | Compute `splurge_ceiling`, pass to template | Low |
| `templates/recommendations.html` | 256-280, 704, 772 | Gold border CSS, dynamic badge text | Low |

## Project Constraints (from CLAUDE.md)

- **Opus-only zones:** Do NOT modify `gift_curator.py` prompt text (reasoning framework, selection principle, ownership section). Adding a `splurge_candidates` parameter and appending data to the inventory block is safe. Adding a SONNET-FLAG comment is safe.
- **Route structured data around LLMs:** Splurge candidates go into the inventory block as data, not as prompt instructions.
- **Templates that emit JS are a risk surface:** The badge text changes are pure Jinja2 in HTML, not in `<script>` blocks, so no JS parse risk.
- **Fix verification protocol:** Each change should be testable independently. The return type change in `multi_retailer_searcher.py` MUST be paired with the caller update.
- **Branch workflow:** All work on feature branches, merge to `main` via PR.

## Sources

### Primary (HIGH confidence)
- `database.py` lines 408-518 -- `search_products_diverse()` return structure verified
- `multi_retailer_searcher.py` lines 37-409 -- return type and splurge handling verified
- `gift_curator.py` lines 1-300 -- function signature, prompt structure, is_splurge instruction verified
- `recommendation_service.py` lines 323-460 -- call chain verified
- `giftwise_app.py` lines 3395-3691 -- generation thread, profile storage, template rendering verified
- `templates/recommendations.html` lines 256-280, 698-784 -- existing CSS and HTML verified
- `profile_analyzer.py` lines 855-864 -- `price_signals` schema verified

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- this is internal Flask/Jinja2 plumbing, no external libraries needed
- Architecture: HIGH -- all code paths traced with exact line numbers
- Pitfalls: HIGH -- identified from real code analysis, not hypothetical

**Research date:** 2026-04-02
**Valid until:** 2026-05-02 (stable codebase, internal changes only)
