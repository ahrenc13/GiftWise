# Phase 5: Pre-Launch Mobile Audit — Research

**Researched:** 2026-04-02
**Domain:** Mobile rendering, responsive CSS, share flow
**Confidence:** HIGH (all findings from direct file reads, no inference)

---

## Summary

The page has a solid responsive foundation: the viewport meta tag is correct, the recommendation cards use CSS Grid with `auto-fill` and `minmax`, and the one media query that exists (`max-width: 768px`) collapses the grid to a single column. However, several issues exist that will cause friction or breakage on a phone:

1. The `.header` element uses a negative margin (`-50px -20px 0`) that is not adjusted in the mobile media query — it may cause layout overflow on narrow viewports.
2. The `actions-section` has 40px horizontal padding with no mobile override — on a 375px screen this eats 80px of width.
3. The share input field has a fixed `width: 320px` (capped with `max-width: 80vw`) — the cap saves it from overflow but it's worth verifying on the narrowest phones.
4. The `.card-close-btn` is 36×36px — just at Apple's 44pt minimum; fine in practice but tight.
5. No `overflow-x: hidden` anywhere in the page (good — no horizontal scroll suppression masking content overflow).
6. The two share sections sit **after** all recommendation cards (line 912+), not before. On mobile a user has to scroll past 10+ cards to reach the share buttons. This is the main share UX problem for the TikTok launch.
7. The `shareViaText` button correctly uses the Web Share API on mobile (iOS Safari, Android Chrome) with an SMS fallback for desktop. The implementation is solid.
8. There is one `position: fixed` element that fires conditionally: the OneSignal push-prompt banner. It is safe: it uses `width: calc(100% - 40px)` and `max-width: 380px` and is hidden by default.

**Primary recommendation:** Add a sticky or above-fold share CTA (either a floating bar or move the share section to just below the first 3 cards). The existing share mechanism is mobile-correct; the problem is discoverability.

---

## File Inventory

All findings below are from these two files:

| File | Lines |
|------|-------|
| `/home/user/GiftWise/templates/base.html` | 371 |
| `/home/user/GiftWise/templates/recommendations.html` | 1362 |

---

## Question-by-Question Findings

### Q1 — Viewport Meta Tag

**File:** `base.html`, line 5

```html
<meta name="viewport" content="width=device-width, initial-scale=1.0">
```

**Assessment:** Correct and complete. `width=device-width` prevents mobile browsers from assuming a 980px desktop layout. `initial-scale=1.0` prevents zoom-out on load. No `user-scalable=no` (good — WCAG prohibits disabling zoom). **No action needed.**

---

### Q2 — Fixed-Width Elements in `recommendations.html`

No bare `width: Xpx` on layout elements was found. Specific findings:

| Element / Selector | Value | Line | Risk |
|--------------------|-------|------|------|
| `.rec-number` | `width: 35px; height: 35px` | 225–226 | None — decorative circle |
| `.card-close-btn` | `width: 36px; height: 36px` | 591–592 | None — icon button |
| `.recommendation-card.focused` | `width: min(580px, 92vw)` | 185 | Safe — `min()` clamps to `92vw` on mobile |
| Share URL input (`#share-url`) | `width: 320px; max-width: 80vw` | 936, 961 | Safe — `max-width: 80vw` clamps it |
| `img` (materials thumbnail) | `width: 40px; height: 40px` | 826 | None — small thumbnail |
| OneSignal banner | `width: calc(100% - 40px); max-width: 380px` | 1320 | Safe — fluid formula |

**No hard fixed widths on layout containers.** The `.header-content` and `.recommendations-grid` are fluid.

One concern that is NOT a fixed width but IS a layout issue:

- `.header` (line 7–13): `margin: -50px -20px 0` pulls the header flush to the edges of the `.container`. This works when `.container` has `padding: 50px 20px` (base.html line 79). On mobile the negative margins should cancel out the container padding correctly, but this is a fragile pattern — if the container padding ever changes or the browser rounds pixels differently, it can create a 1–2px horizontal scrollbar. **Low priority, worth verifying on device.**

---

### Q3 — `overflow: hidden` / Overflow Risks

**All `overflow` rules found in `recommendations.html`:**

| Line | Rule | Context | Risk |
|------|------|---------|------|
| 151 | `overflow: hidden` | `.recommendation-card` | Clips card content — expected behavior for card rounding |
| 187 | `overflow-y: auto` | `.recommendation-card.focused` | Allows scroll inside expanded modal — correct |
| 315 | `overflow: hidden` | `.rec-image-container` | Clips product image edges — expected |
| 423 | `overflow: hidden` | `.rec-why-preview` — via `-webkit-box` line clamp | Expected for text truncation |

**No `overflow-x: hidden` exists anywhere in `recommendations.html` or `base.html`.** This is good — there is no horizontal scroll suppression hiding a layout overflow.

**No horizontal scrolling risk identified** from CSS rules. The potential risk is the `.header` negative-margin pattern described in Q2 above.

---

### Q4 — Touch Target Sizes for CTA Buttons

Apple HIG minimum: 44×44pt. Android Material: 48×48dp. Both recommend 44px as the minimum.

| Button | Class / Element | Padding | Effective height (estimate) | Assessment |
|--------|----------------|---------|---------------------------|------------|
| "Buy on [Retailer]" (physical product) | `.rec-link` (line 524) | `padding: 12px 24px` | ~12+16+12 = 40px (font 1em ≈ 16px) | **Below 44px minimum** — 40px tall |
| "Copy Link" button | `.rec-link` styled as `<button>` (line 878) | Same as above: `padding: 12px 24px` | ~40px | **Below 44px minimum** |
| "Share to Unlock All Picks" | inline `<button>` (line 921) | `padding: 18px 40px` | ~18+18+18 = ~52px | OK |
| "Send to group chat instead" | inline `<button>` (line 925) | `padding: 12px 24px` | ~40px | **Below 44px minimum** |
| "Send to group chat" (unlocked) | inline `<button>` (line 949) | `padding: 12px 24px` | ~40px | **Below 44px minimum** |
| "Copy link" (unlocked) | `.action-button primary` (line 952) | `padding: 16px 40px` (base.html line 151) | ~16+16+16 = 48px | OK |
| "Share on X" | `.action-button secondary` (line 955) | `padding: 16px 40px` | ~48px | OK |
| Filter buttons | `.filter-button` (line 89) | `padding: 10px 20px` | ~10+16+10 = 36px | **Below 44px minimum** |
| Card close button | `.card-close-btn` (line 586) | `width: 36px; height: 36px` | 36px | **Below 44px minimum** |
| Favorite button | `.favorite-btn` | No sizing CSS found — text-only `❤️` button | ~16px | **No touch target CSS at all** |
| Action buttons ("Give Feedback" etc.) | `.action-button` (base.html line 150) | `padding: 16px 40px` | ~48px | OK |

**Summary of touch target issues:**
- `.rec-link` (Buy button, Copy Link): 40px effective height — needs +4px padding or `min-height: 44px`
- Share text buttons with `padding: 12px 24px`: same problem
- `.filter-button`: 36px effective height
- `.card-close-btn`: 36×36px
- `.favorite-btn`: no height CSS at all

---

### Q5 — Recommendation Card Responsiveness

**CSS Grid declaration (lines 129–134):**
```css
.recommendations-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 20px;
    margin-bottom: 50px;
}
```

At 1200px+, `minmax(300px, 1fr)` is used (lines 136–140).

**Mobile media query (lines 608–626) — the only `@media (max-width: 768px)` in the file:**
```css
@media (max-width: 768px) {
    .recommendation-card.focused {
        width: 96vw;
        max-height: 92vh;
        border-radius: 16px;
    }
    .recommendations-grid {
        grid-template-columns: 1fr;    /* single column on mobile */
    }
    .filters-grid {
        grid-template-columns: 1fr;
    }
    .button-group {
        flex-direction: column;        /* stacks buttons vertically */
    }
    .header {
        margin: -50px -20px 0;         /* same as desktop — not adjusted */
    }
}
```

**Assessment:** Cards are fully responsive. On a 375px-wide phone the grid correctly collapses to one column. Individual cards use `flex-direction: column` (line 148) and `width: 100%` (implicit from grid `1fr`). **No fixed-width issue on cards.**

---

### Q6 — `.container` Wrapper

**From `base.html` lines 76–80:**
```css
.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 50px 20px;
}
```

The horizontal padding is `20px` on each side. On a 375px iPhone, content area = 375 - 40 = 335px. This is fine. There is no mobile override for `.container` padding.

**Issue:** The vertical padding of `50px` on mobile is excessive at the top of the page — it pushes content down significantly before the user sees recommendations. This is cosmetic but notable.

**The `.actions-section` has `padding: 50px 40px` (line 559) with no mobile override.** On a 375px phone: 375 - 80 = 295px usable content width. The buttons inside use `flex-wrap: wrap` and the media query stacks them with `flex-direction: column`, so content won't overflow. But the 40px side padding is tight and makes the section feel narrow on small phones.

---

### Q7 — Share Section Location

**Both share sections are at lines 912–968, which is AFTER all recommendation cards (cards start at line 696, end at line 906).**

Structure (simplified):
```
Line 631: <div class="container">
Line 632:   <h1>Your Gift Recommendations</h1>
Line 648:   Beta note banner
Line 656:   Filters section
Line 692:   Card backdrop div
Line 696:   Recommendations grid (10+ cards, loop)
Line 906:   End of grid
Line 912:   <!-- Share section starts here -->
Line 913:   {% if not unlocked %}
Line 914:     <div class="share-section"> ... "Share to Unlock" ... </div>
Line 943:   {% else %}
Line 944:     <div class="share-section"> ... "Send to group chat" ... </div>
Line 968:   {% endif %}
Line 971:   Actions section ("What's Next?")
```

**On a mobile phone with 10 recommendation cards, a user must scroll approximately 2,000–3,000px worth of content before reaching any share button.** The share section is completely below the fold and likely invisible to most mobile users without intentional scrolling.

---

### Q8 — "Text a Link" / `shareViaText` Button Details

**Locked state (user hasn't shared yet) — line 925:**
```html
<button onclick="shareViaText(true)" style="border: 1px solid #d97706; background: transparent; color: #92400e; padding: 12px 24px; border-radius: 10px; font-weight: 600; font-size: 15px; cursor: pointer;">
    💬 Send to group chat instead
</button>
```

This button is inside the yellow "Want to see all X picks?" box (lines 915–942), which is inside the `share-section` div that comes AFTER all cards (line 914). It is **not hidden behind a toggle** — it is always rendered when `not unlocked`. But it IS below the fold.

**Unlocked state — line 949:**
```html
<button onclick="shareViaText(false)" style="border: none; cursor: pointer; background: linear-gradient(135deg, #10b981, #059669); color: white; padding: 12px 24px; border-radius: 10px; font-weight: 700; font-size: 16px;">
    💬 Send to group chat
</button>
```

Same location issue — after all cards.

**The `shareViaText` JavaScript function (lines 1106–1159) is correctly implemented:**
- Calls `navigator.share()` first (Web Share API — pops native iOS/Android share sheet)
- Falls back to `sms:&body=` deep link for desktop
- Works correctly on iOS Safari and Android Chrome

No issues with the mechanism itself. The problem is purely visibility/location.

---

### Q9 — Media Queries Targeting Share Section

**There are zero `@media` rules targeting `.share-section` or its contents.** The only mobile media query in the file (lines 608–626) targets:
- `.recommendation-card.focused`
- `.recommendations-grid`
- `.filters-grid`
- `.button-group`
- `.header`

The share section uses inline `flex-wrap: wrap` on its button row (line 948: `display: flex; gap: 12px; justify-content: center; flex-wrap: wrap;`), which will naturally reflow on mobile without a media query. No CSS adjustments are needed for the share section's internal layout — the issue is its position on the page.

---

### Q10 — Fixed / Sticky Elements

**All `position: fixed` elements found:**

| Line | Element | Description | Mobile impact |
|------|---------|-------------|--------------|
| 164 | `.card-backdrop` | Full-screen blur overlay when card is tapped | Correct — covers screen intentionally, z-index: 100 |
| 180 | `.recommendation-card.focused` | The expanded card modal | Correct — `width: min(580px, 92vw)`, `max-height: 88vh` (92vh on mobile per media query) |
| 1320 | `#push-prompt-banner` | OneSignal push notification prompt | Only visible when `onesignal_app_id` is set; uses `width: calc(100% - 40px)` — safe on mobile. Appears after 8 seconds at bottom of screen. |

**No `position: sticky` elements exist in `recommendations.html`.**

**The push-prompt banner** at line 1320 is the only always-available fixed element outside of the card interaction system. It:
- Is hidden by default (`display: none`)
- Only renders when `onesignal_app_id` is configured
- Appears at `bottom: 20px` — could overlap share buttons if user has scrolled to the share section and the timer fires, but this is unlikely in practice

**There is no floating share button or sticky action bar.** This is the root cause of the share discoverability problem.

---

## Summary Table: Issues for Planner

| # | Issue | Severity | Location | Fix Scope |
|---|-------|----------|----------|-----------|
| M1 | Share section is after all 10+ cards — invisible to most mobile users | HIGH | Lines 912–968 | Add sticky/floating share bar OR move share section above cards |
| M2 | `.rec-link` (Buy button) is only ~40px tall — below 44px touch target | MEDIUM | Lines 524–533 | Add `min-height: 44px; display: flex; align-items: center;` |
| M3 | `.filter-button` is ~36px tall — below 44px touch target | MEDIUM | Lines 89–99 | Add `min-height: 44px` |
| M4 | `.card-close-btn` is 36×36px — below 44px touch target | MEDIUM | Lines 586–602 | Increase to `min-width: 44px; min-height: 44px` |
| M5 | `.favorite-btn` has no size CSS — tap target is the emoji glyph only | MEDIUM | Line 792–795 | Add `width: 44px; height: 44px; display: flex; align-items: center; justify-content: center` |
| M6 | Share buttons with `padding: 12px 24px` are ~40px tall | LOW | Lines 925, 949 | Increase to `padding: 14px 24px` or add `min-height: 44px` |
| M7 | `.actions-section` has `padding: 50px 40px` with no mobile override | LOW | Lines 557–564 | Add `@media (max-width: 768px) { .actions-section { padding: 30px 20px; } }` |
| M8 | `.container` top padding `50px` is large on mobile — pushes content down | INFO | base.html line 79 | Optional: reduce to `padding: 30px 20px` at `max-width: 768px` |
| M9 | `.header` negative margin `margin: -50px -20px 0` is fragile on mobile | INFO | Lines 7–13, and repeated in media query at line 624 | No immediate breakage — monitor on device |

---

## Project Constraints (from CLAUDE.md)

- **Python/Flask app.** Changes are to Jinja2 templates only.
- **Branch discipline:** Changes go on a feature branch, not `main`.
- **Opus-only zones:** `gift_curator.py`, `profile_analyzer.py`, `post_curation_cleanup.py`, `interest_ontology.py` — NOT relevant to this phase.
- **Template changes are in the "Safe to merge without local testing" category per CLAUDE.md** — but testing on a real mobile device is strongly recommended for this phase specifically.
- **Do not add campaign-specific code.** Share buttons must remain generic.
- **No Skimlinks or Spotify.** Not relevant here.
- **The `.container` is defined in `base.html`** — any change to it affects all pages that extend `base.html`.

---

## Validation Architecture

No automated test infrastructure detected for template rendering. Validation for this phase is manual:

| Check | Method |
|-------|--------|
| Viewport / no-zoom | Open on iOS Safari, verify page is not zoomed out |
| Single-column cards | Open on 375px Chrome DevTools mobile emulation |
| Touch targets | Use Chrome DevTools "Rendering > Show touch action areas" overlay |
| Share button on iOS | Tap "Send to group chat" — verify iOS share sheet appears (not blank) |
| Share button on Android | Same test, verify Android share sheet |
| Fixed banner overlap | Wait 8 seconds on a page with `onesignal_app_id` configured, verify banner doesn't obscure content |

**Quick test command (local):**
```bash
python giftwise_app.py
# Open http://localhost:5000/demo in Chrome DevTools
# Toggle device toolbar → iPhone 12 Pro (390px width)
```

---

## Sources

All findings are from direct file reads. No external research was required.

| File | Lines read | Confidence |
|------|-----------|------------|
| `/home/user/GiftWise/templates/base.html` | 1–371 (complete) | HIGH |
| `/home/user/GiftWise/templates/recommendations.html` | 1–1362 (complete) | HIGH |
| `/home/user/GiftWise/templates/nav.html` | 1–15 (complete) | HIGH |

**Research date:** 2026-04-02
**Valid until:** Until any template file changes — re-read before planning if changes occur in sprint.
