# GiftWise — Opus UX & Quality Audit

**Purpose:** This document is a comprehensive audit checklist for a high-quality review of GiftWise's recommendation pipeline. It identifies specific code locations, UX issues, and curation quality gaps. The reviewer (Opus or future session) should treat this as a prioritized punch list, not a feature request backlog. Each item has a clear problem, a file/line location, and a suggested fix.

**Context:** As of Feb 2026, the site runs on Amazon (RapidAPI) + eBay. Etsy (403), Awin (0 joined), and Skimlinks (pending approval) are not contributing inventory yet. The curator currently uses Sonnet. Toggle to Opus via `CLAUDE_CURATOR_MODEL=claude-opus-4-20250514` in Railway env vars (Settings → Variables).

---

## CRITICAL — Revenue & Retention Impact

### 1. "Why it's perfect" is hidden on the default card view
**File:** `templates/recommendations.html` (~line 390-404)
**Problem:** The `why_perfect` text — the entire reason this app exists and isn't just Amazon search — is display:none on the compact card. Users see title + image + price + "View Product." That's indistinguishable from any shopping site. The personalization evidence ("Based on their 47 Taylor Swift TikToks") is buried behind a click.
**Fix:** Show a 1-2 line truncated `why_perfect` on the compact card. This is the #1 conversion differentiator. Even something like "Matches: Taylor Swift + concert style" in small text below the title would work.

### 2. Curator selects boring practical items as "gifts"
**File:** `gift_curator.py` (~line 183-277, the prompt)
**Problem:** Curator treats a travel adapter the same as a thoughtful gift. It selected TWO adapters for the same person. Travel kits, medicine packs, generic organizers — these are things you buy yourself at the airport, not gifts that make someone feel seen. The prompt says "prioritize unique, surprising, thoughtful" but never says what to REJECT.
**Fix:** Add explicit rejection guidance to the curator prompt:
```
REJECT these as gifts — they are practical necessities, not gifts:
- Power adapters, converters, chargers, extension cords
- First aid kits, medicine organizers, pill cases
- Luggage tags, packing cubes, toiletry bags (unless luxury/designer)
- Cable organizers, phone stands, generic tech accessories
- Bulk packs, multi-packs, "essentials kits"
A good gift makes someone say "you GET me." A travel adapter makes them say "thanks, I needed that."
```
**Note:** This is a judgment call best handled by the curator prompt, not a hard code filter. The curator should understand the VIBE, not just the rules.

### 3. Experience material links don't resolve to real products
**File:** `giftwise_app.py` (~line 2687-2767, `_backfill_materials_links`)
**Problem:** 7 of 9 materials hit "Search Amazon" fallback in the last test. "Danish pastries," "Irish tea," "Polaroid camera" — none matched the 29-product inventory. Users see "Search Amazon" links that feel like "go figure it out yourself."
**Fix (two-part):**
- **Short term:** When materials don't match inventory, the fallback should be a pre-built Amazon search URL with the material name (already happening), but the UX should frame it as "Find on Amazon" not just a generic search icon.
- **Long term (when more retailers online):** Run a targeted mini-search for each unmatched material (e.g., search Amazon API for "Polaroid camera" specifically). This is a per-material API call, so watch cost — only do it for the top 3 unmatched materials per experience.

---

## HIGH — Quality & Metrics

### 4. No "boring item" filter in the programmatic pipeline
**File:** `smart_filters.py`
**Problem:** `ObsoleteFormatFilter` catches DVDs and `LOW_EFFORT_KEYWORDS` catches lanyards/bumper stickers, but there's no filter for boring-practical items. These slip through because they technically match an interest ("travel" → travel adapter).
**Recommendation:** Do NOT build a `BoringPracticalFilter` in code. This is the curator's job. If the curator prompt is good (see #2), this handles itself. Adding another hardcoded filter creates more piecemeal rules that conflict with prompt judgment. Prompts for taste, code for rules.

### 5. Image placeholder rate not visible
**File:** `image_fetcher.py` (~line 378), `giftwise_app.py` (image validation section)
**Problem:** The last run had 3 placeholders out of 13 recommendations (23%). Placeholder images kill click-through rate — a product with a real image gets 3-5x more clicks. But there's no metric tracking this over time.
**Fix:** Log placeholder rate as a single line: `IMAGE_QUALITY: 10/13 real (77%)`. Already partially logged at line ~3130 but not in a structured/searchable format. Add to `site_stats.py` tracking.

### 6. Search queries still too verbose for eBay
**File:** `ebay_searcher.py`, `rapidapi_amazon_searcher.py`
**Problem:** "Home renovation and interior design organizer" and "Wisconsin and Upper Michigan recreation lover gift" caused eBay 400 errors. The `_clean_interest_for_search()` function strips some filler but doesn't cap total query length.
**Fix:** After cleaning, truncate to the first 4-5 meaningful words. "Home renovation interior design" → "home renovation gift" (3 words + suffix). eBay's search works better with shorter, more focused queries.

---

## MEDIUM — Edge Cases & Robustness

### 7. Material matching stopwords are too aggressive
**File:** `giftwise_app.py` (~line 2700-2720)
**Problem:** Words like "portable," "travel," "home," "bag," "case" are stopwords, but they carry meaning for materials. "Portable bluetooth speaker" loses "portable" — now it matches any speaker. "Travel yoga mat" loses "travel" — now it matches any yoga mat.
**Fix:** Split stopwords into two tiers: true noise (the, a, an, for, of, with) and context words (portable, travel, home). Only strip true noise for material matching. Context words should count toward overlap.

### 8. Category dedup allows same-type items if both are uncategorized
**File:** `post_curation_cleanup.py` (~line 83-115)
**Problem:** `CATEGORY_PATTERNS` now has 23 patterns (after adding adapter/kit/glass/hook). But any product that doesn't match a pattern gets empty string and bypasses dedup entirely. Two "cruise door decorations" could slip through if "decoration" isn't in the pattern list.
**Fix:** Add a catch-all similarity check for uncategorized items — if two uncategorized products share 3+ title words, flag as potential duplicate.

### 9. Experience URL validation checks status but not content
**File:** `giftwise_app.py` (~line 2519-2551)
**Problem:** Curator hallucinates plausible venue URLs. Validation does a HEAD request and accepts any 200. But a 200 from a redirected homepage isn't the same as a confirmed venue page.
**Fix:** For now, the experience_providers.py approach (curated provider links) is the right workaround. Don't over-invest in URL validation — the providers system replaces it. Focus validation effort on product URLs only.

### 10. Brand dedup catches Taylor Swift poster AND Taylor Swift notebook
**File:** `post_curation_cleanup.py` (~line 235-239)
**Problem:** If curator picks a Taylor Swift poster and a Taylor Swift notebook, brand dedup sees "taylor swift" twice and defers one. But poster and notebook are genuinely different categories — both could be good picks for a Swiftie.
**Current behavior:** Category dedup runs separately, so if categories differ, brand still catches it first. Brand rule wins.
**Recommendation:** Consider relaxing brand dedup when categories are different. A Taylor Swift poster and a Taylor Swift enamel pin are legitimately different gifts. This requires a one-line change: check `if brand in used_brands AND category in used_categories`.

---

## UX POLISH — For Final Pre-Ship Review

### 11. Shared recommendations page needs more personality
**File:** `templates/shared_recommendations.html`
**Problem:** Someone receives a shared link and sees a list of products with a generic header. It doesn't explain HOW the picks were made or WHY they're personalized. The CTA at the bottom ("Get Your Own Picks — Free") is good but the page itself doesn't sell the magic.
**Fix:** Add a brief intro: "These gifts were picked by AI after analyzing [their] social media. Each one matches something specific about them." Don't reveal whose social media — that's the gift-giver's secret.

### 12. Experience cards don't distinguish "bookable" from "DIY"
**File:** `templates/recommendations.html` (experience card section), `templates/experience_detail.html`
**Problem:** A "cooking class at Sur La Table" (bookable, has a link) and a "backyard movie night" (DIY, no link) look the same in the UI. Users don't know whether they need to book something or plan it themselves until they click through.
**Fix:** Add a visual indicator on the card: "Book this" badge for experiences with provider links, "Plan this" badge for DIY experiences with materials lists.

### 13. Recommendation count mismatch in page subtitle
**File:** `templates/recommendations.html` (~line 624)
**Problem:** Subtitle says "{{ recommendations|length }} gifts found" but this includes experiences. "13 gifts found" when there are 10 products + 3 experiences is confusing.
**Fix:** "10 gift ideas + 3 experiences" or just "13 personalized picks."

---

## ROLE OF OPUS IN THE REVIEW

When running an Opus A/B test:

1. **Toggle:** Set `CLAUDE_CURATOR_MODEL=claude-opus-4-20250514` in Railway env vars (Settings → Variables)
2. **Test:** Run the same profile through both Sonnet and Opus curation
3. **Compare on:**
   - Does Opus avoid boring practical items without being told to? (gift taste)
   - Does Opus write better `why_perfect` evidence? (personalization depth)
   - Does Opus spread across more interests? (diversity without being forced)
   - Does Opus avoid hallucinating material URLs? (instruction following)
   - Does the total session time increase meaningfully? (cost consideration)
4. **Decision:** If Opus shows clear improvement on items 1-3 above, keep it for curation. Profile analysis should stay on Sonnet (structured extraction, no taste needed).

The question is whether Opus's better judgment on curation is worth ~5x the API cost. At $0.05-0.10/session on Sonnet vs $0.25-0.50 on Opus, you need the quality improvement to drive enough additional affiliate clicks to cover the delta. This is measurable once you have traffic.

---

## FILES REFERENCED

| File | What It Does | Key Lines |
|------|-------------|-----------|
| `gift_curator.py` | Claude call #2: selects gifts from inventory | Prompt: 183-277, API call: 283-288 |
| `post_curation_cleanup.py` | Programmatic diversity enforcement | Categories: 83-115, Rules: 215-270 |
| `smart_filters.py` | Pre-curation inventory filters | Obsolete: 181-294, Low-effort: 205-209 |
| `giftwise_app.py` | Main app, material matching, experience wiring | Materials: 2687-2767, Images: 3100-3150 |
| `profile_analyzer.py` | Claude call #1: social data → profile | Prompt: 281-387, API call: 393-398 |
| `multi_retailer_searcher.py` | Orchestrates all retailer searches | Search dispatch, merge logic |
| `rapidapi_amazon_searcher.py` | Query cleaning, Amazon search | `_clean_interest_for_search()` |
| `ebay_searcher.py` | eBay search (imports query cleaning) | Uses shared cleaning functions |
| `experience_providers.py` | Maps 13 experience categories to booking platforms | `get_experience_providers()` |
| `templates/recommendations.html` | Main recommendations page | Cards, share button, filters |
| `templates/shared_recommendations.html` | Shared link view + viral CTA | CTA at bottom |
| `templates/experience_detail.html` | Experience deep-dive page | Materials list, provider buttons |
