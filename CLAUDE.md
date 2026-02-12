# GiftWise — Project Intelligence

## Environment Notes
- **Git is installed and working.** Do not prompt the user to install git, git for windows, or any other tooling. The repo is active with full commit history. Just use it.
- **Python/Flask app.** Run with `python giftwise_app.py` or via deployment. No special build step.
- **Branch:** Primary dev branch is `claude/debug-awin-links-Tq5On`. Check `git branch` before making changes. **Merges to `main` must happen via GitHub PR** — the deployment platform watches `main`.
- **Domain:** giftwise.fit (NOT giftwise.me, NOT giftwise.app, NOT giftwise.com)
- **Deployment:** Render.com. Deploys from `main` branch automatically on merge.

## What This Is
AI-powered gift recommendation app. Flask pipeline: scrape social media → Claude analyzes profile → enrich with static data → search retailers → Claude curates gifts → programmatic cleanup → display.

## Current State (Feb 9, 2026)

### What's working
- Full recommendation pipeline: Instagram + TikTok scraping → profile analysis → multi-retailer search → curation → cleanup → display
- Two Claude API calls per session: `profile_analyzer.py` (call #1), `gift_curator.py` (call #2)
- Model toggle via env vars: `CLAUDE_PROFILE_MODEL`, `CLAUDE_CURATOR_MODEL` (default Sonnet for both)
- Smart filters: work exclusion, passive/active filtering, obsolete media filter (respects retro/vinyl interests), low-effort item filter
- Post-curation cleanup: brand dedup, category dedup (23 patterns), interest spread (max 2), source diversity cap
- Experience providers: 13 categories mapped to real booking platforms (Ticketmaster, Cozymeal, Viator, etc.)
- Search query cleaning: `_clean_interest_for_search()` strips filler from interest names, category-specific suffixes
- Material matching: word-overlap scoring with expanded stopwords and 40% threshold
- Sharing: `/api/share` creates shareable links, `shared_recommendations.html` with viral CTA
- Valentine's Day: `/valentine` landing page with countdown, urgency banner on recommendations page
- Admin dashboard: `/admin/stats?key=ADMIN_DASHBOARD_KEY` — tracks signups, rec runs, shares, errors
- Referral system: `referral_system.py` generates codes, tracks referrals
- Share image generator: `share_generator.py` creates SVG cards (no Pillow dependency)
- 6 editorial gift guides at `/guides/<slug>` for Skimlinks approval
- Privacy, terms pages, affiliate disclosure in footer
- Skimlinks JS snippet in all 26+ templates (publisher ID: 298548X178612)

### What's NOT working / pending
- **Etsy:** 403 on all queries — awaiting developer credentials approval
- **Awin:** Code works but 0 joined advertisers — returns [] immediately. Need to join at https://www.awin.com/us/search/advertiser-directory (priority: Etsy, UGG, Lululemon, Portland Leather)
- **Skimlinks:** Code complete, awaiting publisher approval (up to 3 business days from Feb 9)
- **Inventory is thin:** Only Amazon (RapidAPI) + eBay (Browse API) active. ~30 products per run. This affects recommendation quality significantly.
- **Impact.com:** User accidentally signed up as brand instead of publisher. Ticket submitted.
- **CJ Affiliate:** Application submitted
- **Rakuten:** Signed up, need to apply to individual brands
- **Walmart Creator:** Application submitted

### Affiliate network applications status
| Network | Status | Brands Covered |
|---------|--------|---------------|
| Skimlinks | Pending approval | ~48,500 merchants (blanket access) |
| CJ Affiliate | Application submitted | Macy's, Nike, AE/Aerie, J.Crew, Columbia, North Face |
| Impact | Wrong account type, ticket open | Target, Ulta, Kohl's, Gap, Home Depot, Adidas, Dyson |
| Rakuten | Signed up, need brand apps | Sephora, Nordstrom, Anthropologie, Free People, Coach |
| Walmart Creator | Application submitted | Walmart |
| Awin | Active, need to join advertisers | Etsy, UGG, Lululemon, Portland Leather |

## Opus Audit Checklist (CRITICAL — read OPUS_AUDIT.md for full details)

**These are the prioritized items for the next quality review session. Read `OPUS_AUDIT.md` for file/line references and detailed fix suggestions.**

### Critical (Revenue & Retention)
1. **`why_perfect` is hidden on default card view** — the #1 differentiator is buried behind a click. Show truncated version on compact card. (`templates/recommendations.html` ~line 390)
2. **Curator selects boring practical items** — travel adapters, medicine kits, cable organizers are "needs" not gifts. Add rejection guidance to curator prompt. (`gift_curator.py` prompt section)
3. **Experience material links mostly unmatched** — 7/9 hit "Search Amazon" fallback in last test. Improve UX framing + consider targeted mini-searches for unmatched materials. (`giftwise_app.py` ~line 2687)

### High (Quality)
4. **Image placeholder rate not tracked as metric** — 23% placeholders in last run. Need structured logging. (`image_fetcher.py`, `site_stats.py`)
5. **Search queries still too verbose for eBay** — long interest names cause 400 errors. Cap query length after cleaning. (`ebay_searcher.py`, `rapidapi_amazon_searcher.py`)
6. **No "boring practical item" guidance in curator prompt** — don't build a code filter for this; it's a taste/judgment problem for the prompt. Prompts for taste, code for rules.

### Medium (Edge Cases)
7. **Material matching stopwords too aggressive** — "portable," "travel," "home" carry meaning but are stripped. Split into noise vs context tiers. (`giftwise_app.py` ~line 2700)
8. **Category dedup misses uncategorized duplicates** — two products sharing 3+ title words but matching no category pattern both pass. (`post_curation_cleanup.py`)
9. **Brand dedup blocks Taylor Swift poster + Taylor Swift notebook** — same brand, different categories, arguably both good picks for a Swiftie. Consider relaxing when categories differ.
10. **Shared recommendations page needs more personality** — explain HOW picks were made, not just show them. (`templates/shared_recommendations.html`)
11. **Experience cards don't distinguish bookable vs DIY** — add visual badge. (`templates/recommendations.html`)
12. **Rec count subtitle says "13 gifts" but includes experiences** — should say "10 picks + 3 experiences." (`templates/recommendations.html` ~line 624)

### Meta-Principle for the Audit
**Do NOT make piecemeal fixes.** Previous sessions added features without wiring them together — `sharing_section.html` was built but never included, `share_generator.py` and `referral_system.py` were imported but never created, `valentines_landing.html` existed with no route. Every change must be fully wired end-to-end: code → route → template → tested. If you build it, connect it.

## Technical Architecture Notes

### Key Files
- `giftwise_app.py` — Main app (~3000+ lines), orchestrates the full pipeline
- `profile_analyzer.py` — Claude call #1: social data → structured profile. Model via `CLAUDE_PROFILE_MODEL` env var.
- `gift_curator.py` — Claude call #2: profile + inventory → curated recommendations. Model via `CLAUDE_CURATOR_MODEL` env var.
- `post_curation_cleanup.py` — Programmatic enforcement of diversity rules (brand, category, interest, source). 23 category patterns.
- `enrichment_engine.py` — Static intelligence layer (do_buy/dont_buy per interest, demographics, trending)
- `multi_retailer_searcher.py` — Orchestrates all retailer searches, merges inventory pool. Order: Etsy → Awin → eBay → ShareASale → Skimlinks → Amazon
- `rapidapi_amazon_searcher.py` — Amazon search + shared query cleaning functions (`_clean_interest_for_search`, `_categorize_interest`, `_QUERY_SUFFIXES`)
- `ebay_searcher.py` — eBay search (imports query cleaning from amazon searcher)
- `etsy_searcher.py`, `awin_searcher.py`, `skimlinks_searcher.py` — Per-retailer search modules
- `smart_filters.py` — Work exclusion, passive/active filtering, `ObsoleteFormatFilter` (respects retro interests), low-effort item filter
- `image_fetcher.py` — Thumbnail validation and fallback chain
- `relationship_rules.py` — Relationship-appropriate gift guidance (soft curator guidance, not hard filter)
- `experience_providers.py` — Maps 13 experience categories to real booking platforms (Ticketmaster, Cozymeal, Viator, etc.)
- `site_stats.py` — Lightweight event counter for admin dashboard (shelve-backed)
- `share_manager.py` — Share link generation and storage (shelve-backed, 30-day expiry)
- `share_generator.py` — SVG share card generator (no Pillow dependency)
- `referral_system.py` — Referral codes, tracking, Valentine's Day bonus
- `social_conversion.py` — Urgency messaging, growth loops, share tracking classes (partially wired)
- `OPUS_AUDIT.md` — Detailed audit checklist with file/line references for quality review

### Searcher module pattern
Each searcher exports a `search_products_<source>()` function returning a list of product dicts with keys: `title`, `link`, `snippet`, `image`, `thumbnail`, `image_url`, `source_domain`, `search_query`, `interest_match`, `priority`, `price`, `product_id`. The multi_retailer_searcher orchestrates them all and merges into an inventory pool.

### Env vars for model toggle (A/B testing Opus vs Sonnet)
- `CLAUDE_PROFILE_MODEL` — default `claude-sonnet-4-20250514`. Profile analysis (structured extraction — Sonnet is fine here).
- `CLAUDE_CURATOR_MODEL` — default `claude-sonnet-4-20250514`. Gift curation (taste/judgment — Opus may improve quality). Set to `claude-opus-4-20250514` to test.
- Both log which model is used at startup and per-call.

### Admin dashboard
- Route: `/admin/stats?key=ADMIN_DASHBOARD_KEY`
- Env var: `ADMIN_DASHBOARD_KEY` (set in Render, any secret string)
- Tracks: signups, rec_run, share_create, share_view, valentine_hit, guide_hit, error
- Mobile-friendly dark UI, today/week/7-day breakdown, "What to do" trigger rules

### Patterns to Follow
- Images are resolved programmatically from inventory, never from curator LLM output
- Products are interleaved by source before the curator sees them (no positional bias)
- post_curation_cleanup.py is the enforcement layer — if a rule must be guaranteed, enforce it there, not in the prompt
- **Prompts are for quality and judgment. Code is for rules and guarantees.** Never rely on a prompt to do what code can enforce. Never build a code filter for what is fundamentally a taste problem.
- Snippets must describe the product, not just the seller. "Carbon steel wok, 14-inch, flat bottom" beats "From ThaiKitchenStore".
- Curator gets 14 candidates, cleanup trims to 10. This gives cleanup room to enforce diversity without falling short.
- **Wire everything end-to-end.** If you create a template, add the route. If you create a module, wire the imports. If you add a feature, test the full flow. No orphaned code.

### Patterns to Avoid
- Don't route structured data (URLs, image links, prices) through LLM prompts — they corrupt it
- Don't add "CRITICAL" to every prompt instruction — when everything is critical, nothing is
- Don't add API calls without considering per-session cost (~$0.10/session on Sonnet)
- Don't hard-filter products before curation unless absolutely necessary (kills diversity). Prefer soft guidance in the prompt + programmatic cleanup after.
- Don't build features that only work for one retailer. Every feature should degrade gracefully when a source is unavailable.
- **Don't make piecemeal fixes.** Think holistically. Read `OPUS_AUDIT.md` before adding new features.
- **Don't add code filters for taste problems.** "Boring practical items" should be handled by curator prompt, not by `BoringPracticalFilter`. If the curator is making bad judgment calls, fix the prompt.

### Current Status of Retailer Integrations
- Amazon (RapidAPI): Active, working (~20 products per run)
- eBay (Browse API): Active, working (~12 products per run, some 400s on verbose queries)
- Etsy (v3 API): Awaiting developer credentials (all queries return 403)
- Awin (Data Feed API): Code working, but gated — returns [] until advertisers are joined
- Skimlinks (Product Key API v2): Code complete, awaiting publisher approval
- ShareASale: Migrated to Awin (Oct 2025). Legacy code still present but not active.

### Valentine's Day Infrastructure
- `/valentine` and `/valentines` routes serve `valentines_landing.html`
- Countdown timer to Feb 14, 2026, pricing tiers, urgency messaging
- Valentine's urgency banner on recommendations page (auto-shows within 14 days)
- `sharing_section.html` is Valentine-themed but NOT included in any active page (standalone component)
- `social_conversion.py` has `ConversionNudges.get_valentines_urgency()` — partially wired
- Share flow works: recommendations page → "Share My Picks" button → generates share link → copy/tweet

### Gift Guide Pages (for Skimlinks approval)
Six editorial guides deployed at `/guides/<slug>`:
- `guide_beauty.html` (beauty-lover), `guide_music.html` (music-fan), `guide_home.html` (homebody)
- `guide_travel.html` (travel-obsessed), `guide_dog.html` (dog-parent), `guide_tech.html` (tech-nerd)
- No couples/romantic guide yet (opportunity for Valentine's content)

## Brand-to-Network Mapping (Family's Wishlist, ~70 Brands)

**Impact:** Target, Ulta, Kohl's, Gap/Old Navy/Banana Republic, Home Depot, Lowe's, Adidas, Shark, Crate & Barrel, Spanx, Petco, PetSmart, Dick's, Dyson, EverEve

**CJ Affiliate:** Macy's, Nike (US), American Eagle/Aerie, J.Crew, Madewell, Columbia, North Face, Kiehl's, Lowe's

**Rakuten:** Sephora, Nordstrom, Anthropologie, Free People, Urban Outfitters, Coach, ASOS, West Elm, H&M

**Awin:** Etsy, UGG, Lululemon, H&M (EU), Portland Leather

**Pepperjam/Partnerize:** Apple, Everlane, BaubleBar (20% commission!), Bombas (10%), Quince, David Yurman, Aeropostale

**AvantLink:** REI, Patagonia

**In-house/Other:** Walmart (own program + Walmart Creator), Zara (Captiv8 only), Bath & Body Works (CPX Advertising), Victoria's Secret (Skimlinks/DCMnetwork)

**No affiliate program:** Brandy Melville, Aritzia, IKEA (no US program), Gymshark (closed — invite-only athletes now)

**Too niche for major networks (Skimlinks best shot):** Garage, Pink Palm Puff, Dandy Worldwide, Custom Collective, Comfrt, Way of Wade

## Business Model & Revenue Architecture

### Revenue Streams (Priority Order)

**1. Affiliate Revenue (Primary — optimize relentlessly)**
Every product recommendation is an affiliate link opportunity. Revenue per click varies by source:
- Amazon Associates: 1-4% commission (lowest, but highest conversion)
- Etsy Affiliates (via Awin): ~4-5% commission
- Skimlinks merchants: varies, but 25% cut to Skimlinks
- Awin merchants: 5-10% depending on advertiser
- eBay Partner Network: 1-4%

**Key insight: Multi-retailer diversity is a revenue multiplier.** Etsy/Awin products earn 2-5x the commission of Amazon per sale. Never optimize for one retailer — the system should surface the best gift from the best source.

**2. Subscription Tiers (Secondary — not yet enforced)**
- Free tier currently unlimited. Paywall not active.
- Paywall trigger: when API costs from free users exceed affiliate revenue (~10+ sessions/day consistently)
- Pricing: $5-10/mo or $30-50/year planned

**3. Corporate/B2B (Future)**
- Corporate gifting is a $300B+ market. Not current focus.

### Revenue-Aware Development Principles
- Thumbnails directly impact CTR. Placeholder images = lost revenue.
- `why_perfect` drives purchase intent. Generic descriptions don't convert.
- Dead links are lost revenue. Every 404 is a bounced buyer.
- More Etsy/Awin/eBay = higher average commission per click
- Session cost ~$0.10 on Sonnet, ~$0.25-0.50 on Opus. Revenue must exceed cost.

## Recent Commit History (branch: claude/debug-awin-links-Tq5On)

```
34b5b20 Add Opus audit checklist for UX and curation quality review
60beca6 Add admin stats dashboard and fix category dedup
c20ee69 Wire up sharing, Valentine's landing, and viral loop
a4a4aea Add Claude model toggle for A/B testing Opus vs Sonnet
d9f9057 Add curated experience provider links instead of generic Google searches
8b6e3d1 Improve search query quality: clean interest names, category-specific suffixes
9dfdc78 Fix material matching false positives: expand stopwords, raise threshold
c2d56bb Refine obsolete media filter: respect retro/vinyl interests
ecb6978 Add obsolete media and low-effort product filter
59a1d61 Add Skimlinks JS snippet to all 26 HTML templates
883a3a6 Add 5 remaining gift guide articles and wire all routes
e30bab6 Add gift guide pages and routes for Skimlinks approval
746a8aa Add Skimlinks searcher module and gate Awin behind joined feeds
```

## What the User Wants Next

1. **Monitor and iterate on quality** — admin dashboard is built, user travels this week, needs phone-checkable metrics
2. **Couples/Valentine's gift guide** — not yet built, would help Valentine's strategy
3. **TikTok launch strategy** — user's kid has a viral post (150k likes). Plan: kid posts follow-up linking to `/valentine` once inventory quality is good enough (waiting on Skimlinks/retailer approvals). Soft bump, not hardcore launch.
4. **Paywall timing** — monitor engagement via admin dashboard, flip paywall when sessions consistently generate more API cost than affiliate revenue
5. **Opus A/B test** — run same profile through Sonnet and Opus curation, compare gift taste, evidence quality, diversity. Toggle via `CLAUDE_CURATOR_MODEL` env var.
6. **Mother's Day (May 11)** — the real money holiday for a gift app. Valentine's is practice.
