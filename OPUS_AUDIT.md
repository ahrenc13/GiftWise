# GiftWise — Opus UX & Quality Audit

**Purpose:** This document is a comprehensive audit checklist for a high-quality review of GiftWise's recommendation pipeline. It identifies specific code locations, UX issues, and curation quality gaps. The reviewer (Opus or future session) should treat this as a prioritized punch list, not a feature request backlog. Each item has a clear problem, a file/line location, and a suggested fix.

**Context:** As of Feb 2026, the site runs on Amazon (RapidAPI) + eBay. Etsy (403), Awin (0 joined), and Skimlinks (pending approval) are not contributing inventory yet. The curator currently uses Sonnet. Toggle to Opus via `CLAUDE_CURATOR_MODEL=claude-opus-4-20250514` in Railway env vars (Settings → Variables).

---

## STRATEGIC ROADMAP — Revised Feb 17, 2026 (Opus Review)

**The Core Question:** Should we wait for more inventory or launch now?

**Answer: LAUNCH NOW. Iterate with real data. Waiting is the biggest risk.**

### Why the Previous Roadmap Was Wrong

The Feb 17 Sonnet roadmap said "wait for 50+ products before launch (March 1)." This was wrong for three reasons:

1. **You can't accelerate affiliate approvals by coding.** Skimlinks, CJ, and FlexOffers approve on their timeline. Whether you have users or not doesn't change when they approve. Waiting = wasted time.
2. **30 products is enough for 10 curated picks.** The curator selects the best 10 from available inventory. More bad products don't improve selection quality — better products do. Quality > quantity.
3. **The TikTok viral window is closing.** The 150k-like post creates a 2-4 week follow-up window before the algorithm stops surfacing it. Every day of delay burns organic reach that can't be recovered.

### The Real Blocking Issue: Unit Economics

**Pure affiliate math at current scale doesn't work.** This is the uncomfortable truth:

| Scenario | Sessions/day | Revenue/day | API Cost/day | Net/day |
|----------|-------------|-------------|-------------|---------|
| Optimistic (25% CTR, 5% conversion, 5% commission) | 100 | $3.13 | $10.00 | -$6.87 |
| Realistic (15% CTR, 3% conversion, 3.5% commission) | 100 | $0.79 | $10.00 | -$9.21 |
| Break-even (pure affiliate) | ~1,200 | $10.00 | $120.00 | $0.00 |
| $1,000/month profit | ~4,000 | $163 | $400.00 | $33/day |

**At $0.10/session API cost, you need ~1,200 sessions/day just to break even on pure affiliate.** This means either: (a) you need a subscription/paywall component, or (b) you need to dramatically reduce per-session cost (caching, pre-computed recommendations), or (c) you need 4,000+ daily sessions before affiliate alone is profitable.

**Action item:** Validate the actual per-session cost (Claude API + Apify scraping + retailer API calls). If it's truly $1.00/session (not $0.10), the math is 10x worse and subscription pricing is mandatory from day one.

### Retailer Inventory Status (Feb 17)

- ✅ Amazon: ~10-15 products/session (2% commission)
- ✅ eBay: ~8-12 products/session (3% commission)
- ✅ CJ Affiliate: ~6-10 products/session (MonthlyClubs.com approved, 8-15% commission)
- ⏳ Skimlinks: Pending approval (submitted Feb 9, expected Feb 18-20) — **biggest unlock: 48,500 merchants**
- ⏳ FlexOffers: Pending approval (submitted Feb 16)
- ❌ Etsy: 403 (awaiting developer credentials)
- ❌ Awin feeds: Need to join merchants manually

### CJ Brand Priority for REVENUE (Not Product Count)

Prioritized by (commission % x typical gift AOV x gift-relevance):

**Priority A — Chase these approvals actively:**
1. Blue Nile / James Allen (5-10% on $300-2000 jewelry = $15-200/sale)
2. 1-800-Flowers / ProFlowers / FTD (15% on $60-100 = $9-15/sale)
3. Harry & David / Edible Arrangements (8-15% on $50-80 = $4-12/sale)
4. Kay / Zales / Jared / Helzberg (5-8% on $150-500 = $8-40/sale)
5. Shutterfly / Snapfish (10-15% on $40-60 = $4-9/sale)

**Priority B — Good but lower impact:**
6. Things Remembered / Personalization Mall (10-15% on $30-60)
7. Williams Sonoma / Sur La Table (5-8% on $80-150)
8. Macy's (4-8% on $75+)

**Deprioritize:** Dick's Sporting Goods, Foot Locker, Shoe Carnival (low gift-relevance), Vistaprint (not gifts), JCPenney/Belk/Dillard's (low commission + low AOV for gifts). These add product count but not revenue.

---

### Priority Tiers (Revised — Launch-First)

#### **TIER 1 — LAUNCH THIS WEEK (Feb 17-23)**
**Goal:** Get real users, real data, real feedback. Stop building in the dark.

1. ✅ **Fix Amazon/eBay bugs** (DONE Feb 17)
2. 🔧 **Show `why_perfect` on compact cards** (OPUS_AUDIT item #1)
   - This is the #1 conversion differentiator. It's currently hidden behind a click.
   - Even a 1-line truncated version on the card: "Matches: Taylor Swift + concert style"
   - Directly affects whether people click affiliate links → directly affects revenue.
3. 🔧 **Add boring-item rejection guidance to curator prompt** (OPUS_AUDIT item #2)
   - Travel adapters and medicine kits are not gifts. Tell the curator what to reject.
4. 🚀 **Launch soft beta** — post TikTok follow-up, share with friends/family
   - 30 products is enough. The curator's job is selection, not volume.
   - Don't wait for 50+. Waiting teaches you nothing.
5. ⏳ **Monitor affiliate approvals** (CJ, FlexOffers, Skimlinks) — check daily
6. 🔧 **Join Awin advertisers manually** — Uncommon Goods, Personalization Mall, etc.

**Success metric:** 50+ real users in first week. Track: sessions, CTR, drop-off points.

---

#### **TIER 2 — LEARN & MONETIZE (Feb 24 - Mar 9)**
**Goal:** Understand conversion funnel, validate revenue model

1. **Instrument everything:** Where do users drop off? How many click products? Which retailers get clicks? Do they buy?
2. **Integrate newly approved retailers** (CJ brands, FlexOffers if approved)
3. **Build FlexOffers searcher** (once approved — straightforward, follows existing pattern)
4. **Test subscription model:** Add "premium picks" paywall ($4.99/recommendation set)
   - At 7 paid sessions/day = $1,048/month profit with minimal API cost
   - This is the fastest path to $1,000/month — not more affiliate volume
5. **Scale SEO content:** Write 2-3 gift guides/week targeting long-tail keywords
   - "Best gifts for hikers under $50," "personalized gifts for dog lovers," etc.
   - Zero per-session API cost — pure affiliate margin
   - Compounds over time (SEO is the only sustainable free traffic channel)
6. **Evaluate share-to-unlock gate:** Consider making sharing incentive-based ("share to unlock 3 bonus picks") rather than gate-based. Forced sharing gates typically reduce total engagement.

**Success metric:** Conversion rate data on 200+ sessions. At least one validated revenue stream.

---

#### **TIER 3 — OPTIMIZE (Mar 10 - Apr 15)**
**Goal:** Fix bottlenecks revealed by real user data

**Only pursue these AFTER you have data showing what the actual bottleneck is:**

1. **If profiles are too generic** → Gmail OAuth, Pinterest OAuth (add data sources)
2. **If users don't return** → Calendar integration (birthday/anniversary reminders)
3. **If products are low quality** → More retailer integrations, better revenue optimizer tuning
4. **If traffic is the problem** → More TikTok content, SEO scaling, consider paid ads
5. **If conversion is high but volume is low** → Scale what's working (more of the same)

**Do NOT build any of these pre-emptively.** You don't know which is the bottleneck until you have real users.

---

#### **TIER 4 — SCALE (Apr 15 - May 2026)**
**Goal:** Build sustainable growth engine before Mother's Day (May 11)

1. **Browser extension** — Only if you have 1,000+ monthly users (otherwise, adoption will be near zero)
2. **Corporate/B2B gifting** — Different market, only pursue if consumer model is validated
3. **Opus A/B test** — Only worthwhile at scale where you can measure conversion lift
4. **Retention features** — Wishlists, price drop alerts, repeat recommendations

---

### Explicitly OFF THE TABLE
- ❌ **Spotify Wrapped scraping / text-paste** — Too fragile, parsing Spotify screenshots/exports is unreliable and ToS-grey. The OAuth flow is the correct path.
- ✅ **Spotify OAuth** — This is ACTIVE and working. The "Violates ToS" note was incorrect. Spotify's Developer ToS explicitly allows OAuth for user-consented data access in apps. This is the primary Spotify integration.
- ❌ **CSV uploads** — Too much friction, not mobile-friendly
- ❌ **Wearable listening device** — 6-9 month hardware cycle, premature
- ❌ **Phone microphone listening** — Legal liability, two-party consent laws
- ❌ **Gmail OAuth (before launch)** — Premature optimization. Launch first.
- ❌ **Browser extension (before 1,000 users)** — Adoption requires existing user base

---

### The Revised Coherence Test

**Before adding ANY new feature, ask:**

1. **Have you launched?** → If no, stop building features and launch.
2. **Do you have 200+ sessions of conversion data?** → If no, you're guessing. Get data first.
3. **Is this the actual bottleneck?** → Not "could this help?" but "is this THE thing blocking growth right now?"
4. **Does this make money or save money?** → If neither, defer.
5. **Is there a frictionless mobile path?** → If no, reconsider (60% of traffic is mobile).

**The Rule:** Launch first. Measure second. Optimize third. Never optimize what you haven't measured. Never measure what you haven't shipped.

---

### Risk Register

| Risk | Severity | Mitigation |
|------|----------|------------|
| **Unit economics (API cost > revenue)** | HIGH | Test subscription pricing by week 3. Track actual per-session cost. |
| **Apify/scraping breaks** | HIGH | Build a "manual input" fallback (user types interests). Don't depend 100% on scraping. |
| **Privacy backlash** | MEDIUM | Prepare a clear privacy narrative before any viral moment. "Your friend asked us to help find you a gift" framing. |
| **TikTok window closes** | MEDIUM | Launch this week, not March 1. Post follow-up content immediately. |
| **Affiliate approvals slow** | LOW | Can't control. Monitor daily. 30 products is enough to launch. |
| **No retention (single-session product)** | MEDIUM | Calendar integration in Tier 3. But validate product-market fit before optimizing retention. |
| **SEO incumbents (Wirecutter etc.)** | LOW (short term) | Differentiate on personalization. Wirecutter gives generic lists; you give profile-specific picks. |

---

### Fastest Path to $1,000/Month Revenue

**Option A: Freemium subscription (recommended — fastest)**
- 1 free recommendation set → $4.99 for additional sets
- Need ~200 free users/day converting at 3.5% = 7 paid users/day
- Revenue: 7 x $4.99 = $34.93/day = $1,048/month
- API cost: ~$0.70/day (paid sessions only run pipeline)
- Plus any affiliate revenue as bonus

**Option B: SEO content affiliate (slow but compounding)**
- Scale to 100+ gift guide pages targeting long-tail keywords
- 50,000 monthly pageviews x 3% CTR x 2% purchase x $3.50 commission = $105/month
- Zero per-session API cost — pure margin
- Compounds over 6-12 months

**Option C: Hybrid (recommended long-term)**
- Subscription for immediate revenue + cover API costs
- SEO content for long-term organic traffic at zero marginal cost
- Affiliate revenue grows as retailer network expands
- Target: $500/month subscription + $500/month affiliate by month 3-4

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

### 9a. Experience thumbnails for non-concert categories still show emoji
**File:** `recommendation_service.py` (`_format_experience_recommendations()`), `templates/recommendations.html`
**Problem:** The thumbnail waterfall now handles concerts (Spotify artist photo) and DIY (first material thumbnail). But bookable experiences without a music angle — cooking class, spa, wine tasting, dining, outdoor adventure — still show an emoji placeholder. Emoji feels low-effort compared to a real photo.
**Fix options (in order of preference):**
1. **Unsplash API** (free tier: 50 req/hr, 5,000/month) — `GET https://api.unsplash.com/photos/random?query=cooking+class&client_id=...` returns a high-quality, licensed photo by keyword. One call per unique experience category per session. Cache the URL in the experience object.
2. **Curated static set** — Pick one beautiful Unsplash photo per category, download it, host in `/static/images/experiences/`, reference by category key. Zero latency, zero API, one-time effort. 13 categories = 13 photos.
3. **Keep emoji but style it better** — Larger, more artistic presentation in a gradient card. Lowest effort, lowest improvement.
**Recommendation:** Curated static set (option 2) is the right call pre-launch. No API dependency, no latency, and a thoughtfully picked photo per category beats a generic API random image anyway.

### 9. Experience URL validation checks status but not content
**File:** `giftwise_app.py` (~line 2519-2551)
**Problem:** Curator hallucinates plausible venue URLs. Validation does a HEAD request and accepts any 200. But a 200 from a redirected homepage isn't the same as a confirmed venue page.
**Fix:** For now, the experience_providers.py approach (curated provider links) is the right workaround. Don't over-invest in URL validation — the providers system replaces it. Focus validation effort on product URLs only.

### 10. Brand dedup catches Taylor Swift poster AND Taylor Swift notebook
**File:** `post_curation_cleanup.py` (~line 235-239)
**Problem:** If curator picks a Taylor Swift poster and a Taylor Swift notebook, brand dedup sees "taylor swift" twice and defers one. But poster and notebook are genuinely different categories — both could be good picks for a Swiftie.
**Current behavior:** Category dedup runs separately, so if categories differ, brand still catches it first. Brand rule wins.
**Recommendation:** Consider relaxing brand dedup when categories are different. A Taylor Swift poster and a Taylor Swift enamel pin are legitimately different gifts. This requires a one-line change: check `if brand in used_brands AND category in used_categories`.

### 9b. Spotify-only: no validation that Claude followed the interest extraction rules
**File:** `profile_analyzer.py` (post-Claude response, ~line 592)
**Problem:** The prompt gives Claude specific rules for Spotify-only profiles ("Extract specific artist names, not genre labels. 'Tiger Army' not 'horror punk culture'"). But there's no post-hoc check that Claude followed them. If Claude returns "jazz culture" instead of "Bill Evans vinyl," the search pipeline fails silently — the interest fires, Amazon/eBay find nothing useful, and those search slots are wasted.
**Fix:** After profile is returned, run a lightweight validation pass on Spotify-only profiles:
- Flag any interest with fewer than 2 words that matches a known generic genre label (jazz, pop, rock, classical, country, hip hop, folk, blues, indie, metal, punk)
- Log a warning: `SPOTIFY_ONLY: generic interest '{interest}' may produce poor search results`
- Optionally: append a note to the interest (`'jazz culture' → 'jazz vinyl records'`) using a small mapping dict
**Scope:** This is a quality guard, not a hard filter. The goal is visibility into when the profile analyzer drifts from the rules, not to block anything.

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

## PARTNER PRODUCT WIRING — Active CJ Partners Not Yet Wired

### illy caffè (CJ, approved Feb 17)
**Status:** Approved but zero product code. Currently depends on CJ GraphQL returning illy products when "espresso/coffee" is in the top 5 interests — fragile and not guaranteed.
**What to do:**
1. Log in to CJ dashboard → Advertisers → illy caffè → Links → Get Links
2. Find "evergreen" link IDs for: flagship espresso set, iperEspresso capsule gift set, espresso machine
3. Add static products to `cj_searcher.py` exactly like Peet's (`_ILLY_ALL_PRODUCTS`, `get_illy_products_for_profile()`, trigger at line ~536)
4. Trigger interests: `coffee`, `espresso`, `italian culture`, `gourmet`, `foodie`, `cafe culture`, `cooking`
5. T&C: Do NOT use discount language — illy ToS prohibits it
**Commission:** 6% new customers / 4% existing. AOV ~$125. Better than Amazon (2%) and Peet's (10% but lower AOV). An espresso machine rec could earn $7-30/sale.
**Why this matters over Amazon:** Amazon returns generic "espresso gift set" results. illy returns the category-defining brand that an espresso person actually wants. And we earn 3x the commission.

### MonthlyClubs.com (CJ, approved Feb 16)
**Status:** Approved. Gift subscriptions (beer/wine/cheese/chocolate/flowers). These are high-AOV, occasion-appropriate, and recurring revenue (subscriber buys monthly).
**What to do:**
1. CJ dashboard → Advertisers → MonthlyClubs → Links → Get evergreen links for top clubs
2. Add static products for: Beer of the Month Club, Wine of the Month Club, Cheese of the Month Club, Chocolate of the Month Club
3. Trigger interests: `beer`, `wine`, `craft beer`, `cheese`, `chocolate`, `foodie`, `gourmet`, `cooking`, `baking`, `entertaining`
4. Estimated commission: 8-15% per CLAUDE.md

### CJ GraphQL `joined_only=False` — earning zero on non-joined advertisers
**File:** `multi_retailer_searcher.py` line 262, `cj_searcher.py` line 412
**Problem:** `joined_only=False` means the GraphQL search returns products from ALL CJ advertisers — including ones we haven't joined and earn 0% commission on. We're potentially recommending products that generate no revenue.
**Fix:** Change to `joined_only=True` once we've joined enough advertisers to have meaningful coverage (after MonthlyClubs, illy, and any additional approvals). This ensures every CJ product in results has a commission attached.
**Timing:** Switch after FlexOffers approval comes in (same-day to 48h) to fill any gaps.

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
