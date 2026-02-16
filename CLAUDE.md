# GiftWise — Project Intelligence

## Environment Notes
- **Git is installed and working.** Do not prompt the user to install git, git for windows, or any other tooling. The repo is active with full commit history. Just use it.
- **Python/Flask app.** Run with `python giftwise_app.py` or via deployment. No special build step.
- **Branch:** Check `git branch` before making changes. **Merges to `main` must happen via GitHub PR** — Railway watches `main` for auto-deploy.
- **Domain:** giftwise.fit (NOT giftwise.me, NOT giftwise.app, NOT giftwise.com)

## Deployment (Railway.app)
- **Platform:** Railway.app (NOT Render, NOT Heroku)
- **Auto-deploy branch:** `main` (pushes to `main` trigger automatic deployment)
- **Config file:** `railway.json` (Nixpacks builder, Gunicorn start command)
- **Start command:** `gunicorn giftwise_app:app --bind 0.0.0.0:$PORT --workers 1 --timeout 600`
- **Environment variables:** Set in Railway dashboard → Settings → Variables (see RAILWAY_DEBUG_GUIDE.md for required vars)
- **Logs:** Railway dashboard → Deployments → View Logs (or `railway logs` via CLI)
- **Database:** Uses shelve (ephemeral filesystem) — consider migrating to Railway Postgres for persistence across deploys

## What This Is
AI-powered gift recommendation app. Flask pipeline: scrape social media → Claude analyzes profile → enrich with static data → search retailers → Claude curates gifts → programmatic cleanup → display.

**Current State (TL;DR):** App is feature-complete and polished, but inventory is bottlenecked. Only Amazon + eBay active (~30 products/session). Waiting on affiliate network approvals: Skimlinks (submitted 2/9), CJ Affiliate (~70 brands submitted 2/15), Awin (need to join advertisers), Impact (account type issue). Valentine's removed (2/15), Mother's Day ready (guide built). TikTok launch on hold until inventory improves. Demo mode ready for testing. 10 gift guides + 4 blog posts deployed for SEO and network approval. 4754-line Flask app with SQLite product DB, revenue optimizer, and click tracking.

## Current State (Feb 16, 2026)

### Major Changes Since Feb 9
1. **Valentine's Day completely removed** (Feb 15) — All V-Day routes, templates, messaging, and promo-specific code deleted. Sharing/referral infrastructure preserved as generic features.
2. **Mother's Day guide added** (Feb 14) — `/guides/mothers-day` ready for May 11 promotion
3. **Blog architecture launched** (Feb 15) — 4 SEO-optimized blog posts for organic traffic and affiliate approval
4. **3 Etsy gift guides added** (Feb 14) — etsy-home-decor, etsy-jewelry, etsy-under-50 (total now 10 guides)
5. **Demo/skip mode** (Feb 13) — `/demo` bypasses social handle requirement. Admin mode (`?admin=true`) pre-fills @chadahren for real testing.
6. **Revenue optimizer** (Feb 11) — `revenue_optimizer.py` scores products by commission rate + interest match before curator sees them
7. **Product database** (Feb 11) — SQLite catalog caches products, tracks clicks, enables learning loop
8. **Waitlist system** (Feb 10) — `/waitlist` for handle-based early access (Gen Z engagement)
9. **Spotify Wrapped integration** (Feb 10) — Text paste alternative to OAuth for music preferences
10. **CJ Affiliate strategy** (Feb 15) — Batch applications to ~70 brands, T&C analysis, revenue projections added to docs

### What's working
- **Full recommendation pipeline:** Instagram + TikTok scraping → profile analysis → multi-retailer search → curation → cleanup → display
- **Two Claude API calls per session:** `profile_analyzer.py` (call #1), `gift_curator.py` (call #2)
- **Model toggle via env vars:** `CLAUDE_PROFILE_MODEL`, `CLAUDE_CURATOR_MODEL` (default Sonnet for both)
- **Smart filters:** work exclusion, passive/active filtering, obsolete media filter (respects retro/vinyl interests), low-effort item filter
- **Post-curation cleanup:** brand dedup, category dedup (23 patterns), interest spread (max 2), source diversity cap
- **Experience providers:** 13 categories mapped to real booking platforms (Ticketmaster, Cozymeal, Viator, etc.)
- **Search query cleaning:** `_clean_interest_for_search()` strips filler from interest names, category-specific suffixes
- **Material matching:** word-overlap scoring with expanded stopwords and 40% threshold
- **Sharing infrastructure:** `/api/share` creates shareable links, `shared_recommendations.html`, `share_generator.py` SVG cards (generic, no campaign-specific code)
- **Referral system:** `referral_system.py` generates codes, tracks referrals (generic, no promo-specific bonuses)
- **Admin dashboard:** `/admin/stats?key=ADMIN_DASHBOARD_KEY` — tracks signups, rec_run, share_create, share_view, guide_hit, error
- **10 editorial gift guides** at `/guides/<slug>` for affiliate approval (6 general + 3 Etsy-focused + 1 Mother's Day)
- **Blog architecture:** `/blog` landing + 4 SEO-optimized articles (cash vs physical gifts, gift mistakes, gifts for people who have everything, last-minute gifts)
- **Demo/skip mode:** `/demo` bypasses social handle requirement. Admin variant (`?admin=true`) pre-fills @chadahren for real pipeline testing.
- **Waitlist system:** `/waitlist` for handle-based early access (Gen Z engagement)
- **Spotify Wrapped integration:** `/connect/spotify-wrapped` accepts text paste of Spotify data for music preference analysis
- **Revenue optimization:** `revenue_optimizer.py` smart pre-filtering scores products before curator sees them (prioritizes high-commission sources)
- **Product database:** SQLite catalog (`database.py`) caches products, tracks click analytics, enables learning loop
- **Affiliate click tracking:** `track_affiliate_click()` logs every product click for performance analysis
- **Privacy, terms, affiliate disclosure** in footer
- **Skimlinks JS snippet** in all 40 templates (publisher ID: 298548X178612)

### What's NOT working / pending
- **Etsy:** 403 on all queries — awaiting developer credentials approval (still pending as of Feb 16)
- **Awin:** Code works but 0 joined advertisers — returns [] immediately. Need to join at https://www.awin.com/us/search/advertiser-directory (priority: Etsy, UGG, Lululemon, Portland Leather). User was trying to research which partners to join but Awin's interface is difficult.
- **Skimlinks:** Code complete, awaiting publisher approval (submitted Feb 9, still pending as of Feb 16 — can take up to 7 business days)
- **Inventory is thin:** Only Amazon (RapidAPI) + eBay (Browse API) active. ~30 products per run. This affects recommendation quality significantly.
- **Impact.com:** User accidentally signed up as brand instead of publisher. Ticket submitted, no response yet.
- **CJ Affiliate:** Batch applications to ~70 brands submitted Feb 15. Awaiting responses (auto-approve in 24-48h or manual review 3-7 days).
- **Rakuten:** Signed up, need to apply to individual brands
- **Walmart Creator:** Application submitted

### Affiliate network applications status (Updated Feb 16)
**See `AFFILIATE_APPLICATIONS_TRACKER.md` for detailed tracking.**

| Network | Status | Brands Covered |
|---------|--------|---------------|
| Skimlinks | Pending approval (submitted 2/9, expected by 2/18-20) | ~48,500 merchants (blanket access) |
| CJ Affiliate | ~70 brand applications submitted 2/15, awaiting responses | Flowers, jewelry, apparel, home, gourmet, personalization |
| ShareASale | Application submitted 2/16, awaiting approval (1-3 days) | Uncommon Goods, personalization shops, unique gifts |
| FlexOffers | Application submitted 2/16, awaiting approval (same-day to 48h) | 12,000+ advertisers, niche brands |
| Impact | Wrong account type (signed up as brand not publisher), ticket submitted, no response | Target, Ulta, Kohl's, Gap, Home Depot, Adidas, Dyson |
| Rakuten | Account active, need to apply to individual brands | Sephora, Nordstrom, Anthropologie, Free People, Coach |
| Walmart Creator | Application submitted | Walmart |
| Awin | Account active, only Portland Leather found (Feb 16 research) | Portland Leather only |
| Etsy Direct | Developer credentials pending | Etsy (would bypass Awin if approved) |
| Amazon Associates | ✅ Active (tag added to Railway Feb 16) | Amazon |
| eBay Partner Network | ✅ Active | eBay |

## CJ Affiliate Partnership Strategy (Feb 15, 2026)

**UPDATE Feb 15:** Batch applications to all ~70 brands submitted. Awaiting auto-approvals (24-48h) and manual reviews (3-7 days).

### Optimized Publisher Profile
**Description:** Gift recommendation publisher, editorial gift guides, high-intent traffic, AI-powered personalization
**Promotional Methods:** Content/Niche Site, SEO/SEM, Social Media, Blog/Review Site
**Tags (25 core):** gift recommendations, gift guides, high intent traffic, purchase-ready audience, gift shopping, Mother's Day gifts, Father's Day gifts, Valentine's Day gifts, holiday gifts, birthday gifts, curated gifts, personalized gifts, women 25-45, millennial shoppers, female audience, gift blog, editorial content, buying guides, AI-powered recommendations, SEO optimized, seasonal content, evergreen content, content marketing, United States, growing audience

### Batch Application List (~70 Brands, Feb 15 2026)

**TIER 1: Gift-Obvious (25 brands)**
- Flowers/Gourmet: ProFlowers, 1-800-Flowers, FTD, Teleflora, Harry & David, Edible Arrangements, Mrs. Fields, Cheryl's Cookies, Popcornopolis, 1-800-Baskets
- Jewelry: Kay Jewelers, Zales, Jared, Helzberg Diamonds, Blue Nile, James Allen
- Books: Barnes & Noble
- Personalization: Things Remembered, Personalization Mall, Shutterfly, Snapfish
- Baby/Kids: Carter's, OshKosh B'Gosh

**TIER 2: Family Wishlist Brands (15 brands)**
- Apparel: Macy's, American Eagle, Aerie, J.Crew, Madewell, Nike, Columbia Sportswear, The North Face, Eddie Bauer, L.L.Bean, Lands' End
- Beauty: Kiehl's, Dermstore, SkinStore
- Shoes: DSW

**TIER 3: Lifestyle & Home (20 brands)**
- Home/Kitchen: Sur La Table, Williams Sonoma, Pottery Barn, West Elm, Crate & Barrel, Wayfair, Overstock
- Department: JCPenney, Belk, Dillard's, Nordstrom Rack
- Sports/Outdoors: Dick's Sporting Goods, Moosejaw, Backcountry, Finish Line, Foot Locker, Shoe Carnival
- Pet: Chewy, BarkBox, Petco

**TIER 4: Specialty (10 brands)**
- Vistaprint, UncommonGoods, ModCloth, Vineyard Vines, Huckberry, MeUndies, Parachute Home, Brooklinen

### Key CJ T&C Learnings

**ProFlowers/FTD Restrictions (applies to most flower brands):**
- Must remove expired promotional links immediately or risk commission reversal
- Only promote deals/codes provided through CJ interface (no scraping other coupon sites)
- Cannot promote Groupon/AARP/USAA/LivingSocial deals without approval
- **Strategy:** Focus on evergreen product links, not time-sensitive deals. Link to specific bouquets/products rather than sales.

**General CJ Best Practices:**
- Search marketing restrictions irrelevant (we're SEO/content, not PPC)
- Email marketing requires brand approval (future consideration)
- Most brands reverse commissions on returns/cancellations (standard)
- Cookie duration varies by brand (typically 7-30 days)

### Expected Approval Timeline
- Auto-approvals: 24-48 hours (brands with open programs)
- Manual review: 3-7 days (brands vetting new publishers)
- Rejections: Common for new sites without traffic stats — reapply in 3-6 months with metrics

### Revenue Impact by Category
- **Flowers (15% commission):** ProFlowers, 1-800-Flowers, FTD — seasonal spikes (Valentine's, Mother's Day)
- **Jewelry (5-10% commission):** Kay, Zales, Blue Nile — high AOV, milestone occasions
- **Gourmet (8-15% commission):** Harry & David, Edible — corporate gifting crossover
- **Apparel (4-8% commission):** AE, J.Crew, Columbia — high volume, lower margins
- **Personalization (10-15% commission):** Things Remembered, Shutterfly — high intent, gift-specific

### Next Actions After Approvals Start Coming In
1. **Create retailer-specific gift guides:** "Best Flower Delivery Services 2026," "Personalized Gift Ideas," "Jewelry Gifts for Milestones"
2. **Add CJ brands to AI curation pool:** Integrate approved merchants into multi-retailer search (when product feeds available)
3. **Track performance by brand:** Use CJ reporting to identify top converters, feature them more prominently
4. **Seasonal content planning:** Mother's Day (May 11), Father's Day (Jun 15), Graduation (May-Jun), Christmas (Nov-Dec)

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
- `giftwise_app.py` — Main app (4754 lines as of Feb 16), orchestrates the full pipeline
- `profile_analyzer.py` — Claude call #1: social data → structured profile. Model via `CLAUDE_PROFILE_MODEL` env var.
- `gift_curator.py` — Claude call #2: profile + inventory → curated recommendations. Model via `CLAUDE_CURATOR_MODEL` env var.
- `post_curation_cleanup.py` — Programmatic enforcement of diversity rules (brand, category, interest, source). 23 category patterns.
- `enrichment_engine.py` — Static intelligence layer (do_buy/dont_buy per interest, demographics, trending)
- `multi_retailer_searcher.py` — Orchestrates all retailer searches, merges inventory pool. Order: Etsy → Awin → eBay → ShareASale → Skimlinks → Amazon
- `rapidapi_amazon_searcher.py` — Amazon search + shared query cleaning functions (`_clean_interest_for_search`, `_categorize_interest`, `_QUERY_SUFFIXES`)
- `ebay_searcher.py` — eBay search (imports query cleaning from amazon searcher)
- `etsy_searcher.py`, `awin_searcher.py`, `skimlinks_searcher.py`, `cj_searcher.py` — Per-retailer search modules
- `smart_filters.py` — Work exclusion, passive/active filtering, `ObsoleteFormatFilter` (respects retro interests), low-effort item filter
- `image_fetcher.py` — Thumbnail validation and fallback chain
- `relationship_rules.py` — Relationship-appropriate gift guidance (soft curator guidance, not hard filter)
- `experience_providers.py` — Maps 13 experience categories to real booking platforms (Ticketmaster, Cozymeal, Viator, etc.)
- `revenue_optimizer.py` — Smart pre-filtering: scores products by commission rate, past performance, interest match before sending to curator
- `database.py` — SQLite product catalog for caching, click tracking, learning loop
- `oauth_integrations.py` — OAuth flows for Pinterest, Spotify, Etsy, Google/YouTube (supplements scraping)
- `site_stats.py` — Lightweight event counter for admin dashboard (shelve-backed)
- `share_manager.py` — Share link generation and storage (shelve-backed, 30-day expiry)
- `share_generator.py` — SVG share card generator (generic, no campaign-specific code)
- `referral_system.py` — Referral codes, tracking (generic, no promo-specific bonuses)
- `social_conversion.py` — Generic urgency messaging, growth loops (campaign-specific code removed)
- `OPUS_AUDIT.md` — Detailed audit checklist with file/line references for quality review
- `AFFILIATE_NETWORK_RESEARCH.md` — Brand-to-network mapping for ~70 brands from family wishlist

### Searcher module pattern
Each searcher exports a `search_products_<source>()` function returning a list of product dicts with keys: `title`, `link`, `snippet`, `image`, `thumbnail`, `image_url`, `source_domain`, `search_query`, `interest_match`, `priority`, `price`, `product_id`. The multi_retailer_searcher orchestrates them all and merges into an inventory pool.

### Env vars for model toggle (A/B testing Opus vs Sonnet)
- `CLAUDE_PROFILE_MODEL` — default `claude-sonnet-4-20250514`. Profile analysis (structured extraction — Sonnet is fine here).
- `CLAUDE_CURATOR_MODEL` — default `claude-sonnet-4-20250514`. Gift curation (taste/judgment — Opus may improve quality). Set to `claude-opus-4-20250514` to test.
- Both log which model is used at startup and per-call.

### Admin dashboard & testing
**Admin Dashboard:**
- Route: `/admin/stats?key=ADMIN_DASHBOARD_KEY`
- Env var: `ADMIN_DASHBOARD_KEY` (set in Railway dashboard → Settings → Variables)
- Tracks: signups, rec_run, share_create, share_view, guide_hit, error
- Mobile-friendly dark UI, today/week/7-day breakdown, "What to do" trigger rules

**Testing Routes:**
- `/demo` — Public demo mode, bypasses social handle requirement, shows fake recommendations
- `/demo?admin=true` — Admin test mode, pre-fills @chadahren and runs real pipeline (requires owner to be logged in or bypasses validation)
- Admin can bypass share-to-unlock gates and other viral friction for testing

### New Infrastructure (Added Feb 10-16)

**Revenue Optimizer (`revenue_optimizer.py`):**
- Scores products BEFORE they go to the curator using local intelligence
- Factors: commission rate (Etsy/Awin earn 2-5x vs Amazon), past click performance, interest match
- Goal: Send curator 30 high-quality products instead of 100 random ones → better output + lower token cost
- `score_product_for_profile(product, profile, relationship)` returns 0.0-1.0 score

**Product Database (`database.py`):**
- SQLite catalog at `/home/user/GiftWise/data/products.db`
- Caches products from retailers (reduces API calls)
- Tracks click analytics for learning loop: which products get clicked, which retailers convert
- `track_affiliate_click(product_id, retailer, user_id)` logs every product click
- Enables smart pre-filtering based on historical performance

**OAuth Integrations (`oauth_integrations.py`):**
- Spotify OAuth + Spotify Wrapped text paste for music preferences
- Pinterest OAuth for visual taste analysis
- Etsy OAuth for favorites (when approved)
- Google OAuth for YouTube subscriptions
- Supplements scraping with first-party data (better quality, no rate limits)

### Patterns to Follow
- Images are resolved programmatically from inventory, never from curator LLM output
- Products are interleaved by source before the curator sees them (no positional bias)
- post_curation_cleanup.py is the enforcement layer — if a rule must be guaranteed, enforce it there, not in the prompt
- **Prompts are for quality and judgment. Code is for rules and guarantees.** Never rely on a prompt to do what code can enforce. Never build a code filter for what is fundamentally a taste problem.
- Snippets must describe the product, not just the seller. "Carbon steel wok, 14-inch, flat bottom" beats "From ThaiKitchenStore".
- Curator gets 14 candidates, cleanup trims to 10. This gives cleanup room to enforce diversity without falling short.
- **Wire everything end-to-end.** If you create a template, add the route. If you create a module, wire the imports. If you add a feature, test the full flow. No orphaned code.
- **Revenue optimization matters.** Prioritize high-commission sources (Etsy, Awin, eBay) over low-commission (Amazon). Use `revenue_optimizer.py` to score products before sending to curator.

### Patterns to Avoid
- Don't route structured data (URLs, image links, prices) through LLM prompts — they corrupt it
- Don't add "CRITICAL" to every prompt instruction — when everything is critical, nothing is
- Don't add API calls without considering per-session cost (~$0.10/session on Sonnet)
- Don't hard-filter products before curation unless absolutely necessary (kills diversity). Prefer soft guidance in the prompt + programmatic cleanup after.
- Don't build features that only work for one retailer. Every feature should degrade gracefully when a source is unavailable.
- **Don't make piecemeal fixes.** Think holistically. Read `OPUS_AUDIT.md` before adding new features.
- **Don't add code filters for taste problems.** "Boring practical items" should be handled by curator prompt, not by `BoringPracticalFilter`. If the curator is making bad judgment calls, fix the prompt.
- **Don't build campaign-specific code.** Valentine's Day taught this lesson — had to delete 884 lines of promo-specific code. Build generic infrastructure (sharing, referrals, urgency) that works for any campaign.
- **Don't assume affiliate networks will approve quickly.** Skimlinks submitted Feb 9, still waiting Feb 16. Plan for 7+ business days.
- **Don't optimize for Amazon.** Amazon has lowest commission (1-4%). Prioritize Etsy (4%), Awin (5%), eBay (3%) for revenue.

### Current Status of Retailer Integrations
- Amazon (RapidAPI): Active, working (~20 products per run)
- eBay (Browse API): Active, working (~12 products per run, some 400s on verbose queries)
- Etsy (v3 API): Awaiting developer credentials (all queries return 403)
- Awin (Data Feed API): Code working, but gated — returns [] until advertisers are joined
- Skimlinks (Product Key API v2): Code complete, awaiting publisher approval
- ShareASale: Migrated to Awin (Oct 2025). Legacy code still present but not active.

### Editorial Content (for Affiliate Network Approval)

**Gift Guides (10 total):**
- `/guides` — landing page listing all guides
- `/guides/<slug>` — individual guide pages
- General guides (6): beauty-lover, music-fan, homebody, travel-obsessed, dog-parent, tech-nerd
- Etsy-focused guides (3): etsy-home-decor, etsy-jewelry, etsy-under-50
- Seasonal guides (1): mothers-day

**Blog Posts (4 total):**
- `/blog` — landing page listing all posts
- `/blog/<slug>` — individual post pages
- Posts: cash-vs-physical-gift, gift-giving-mistakes, gifts-for-someone-who-has-everything, last-minute-gifts
- SEO-optimized, evergreen content for organic traffic

All guides and blog posts include Skimlinks snippet and affiliate disclosure.

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

## Recent Commit History (Last 20, since Feb 9)

```
e0a41d7 Merge pull request #39 from ahrenc13/claude/review-documentation-zban7
1add50a Add CJ Affiliate partnership strategy to project documentation
17f9062 Add blog architecture and publisher pages for affiliate network approval
ff06454 Add Mother's Day 2026 gift guide
296b34f Wire up 3 existing Etsy gift guides
323b149 Remove all Valentine's Day code while preserving sharing infrastructure
9cf3520 Fix demo route and remove friction from testing flow
f3d9681 Disable username validation for owner testing
3efd0ce Add admin test route to run real pipeline with owner's Instagram
c7fb9c0 Make home page CTA go directly to demo (zero friction)
e34ecca Add Skip/Demo mode to bypass social handle requirement
a197578 Add admin bypass for share-to-unlock viral gates
056208c Add share-to-unlock viral growth mechanics for TikTok campaign
d68c08a Rewrite beta messaging with warmth and genuine apology
815bc57 Add honest beta messaging for thin inventory state
fb13fde Fix experience cards: Add validation for materials/links like products
ef325ab Revenue optimization: Smart pre-filtering & learning loop
210631c Phase 1 refactoring: Repository pattern, auth middleware, config management
ae4ea43 Add monetization infrastructure: affiliate tracking, click analytics, email capture
f1a0df3 Add complete waitlist system for TikTok viral campaign
```

Key themes: Valentine's removed, Mother's Day added, friction reduction, revenue optimization, waitlist/viral mechanics, CJ Affiliate strategy.

## Current Development Focus

**Immediate Priority: Unlock Inventory**
The app's #1 bottleneck is thin inventory (Amazon + eBay only, ~30 products per session). Everything else is blocked on getting more affiliate networks approved:

1. **Skimlinks** (highest impact) — Blanket access to ~48,500 merchants if approved. Submitted Feb 9, expecting response by Feb 18-20.
2. **ShareASale** (high impact) — Applied Feb 16. Approval typically 1-3 days. Unique gift merchants, personalization shops.
3. **FlexOffers** (high impact) — Applied Feb 16. Many auto-approve programs, often same-day approval.
4. **CJ Affiliate** (~70 brands) — Batch applications submitted Feb 15. Auto-approvals should start coming in 24-48h, manual reviews 3-7 days.
5. **Impact.com** (fix account type) — Accidentally signed up as brand not publisher. Ticket submitted, waiting for support.

**Secondary: Content & Traffic**
- 10 gift guides deployed (6 general + 3 Etsy + 1 Mother's Day)
- 4 blog posts live for SEO
- Waitlist system ready for viral growth
- Demo mode eliminates friction for testing/sharing

**Holding Pattern: TikTok Launch**
User's kid has viral post (150k+ likes) but waiting to post follow-up until inventory improves. Don't want to drive traffic to a thin product catalog.

## What the User Wants Next (Updated Feb 16)

1. **Monitor affiliate approvals** — ShareASale (1-3 days), FlexOffers (same-day to 48h), CJ (~70 brands, rolling approvals), Skimlinks (by Feb 18-20)
2. **Build ShareASale searcher** — `shareasale_searcher.py` module once approved
3. **Build FlexOffers searcher** — `flexoffers_searcher.py` module once approved
4. **Fix Impact account** — Ticket open for account type issue
5. **Monitor and iterate on quality** — admin dashboard at `/admin/stats?key=ADMIN_DASHBOARD_KEY`
6. **TikTok soft launch** — User's kid has viral post (150k+ likes). Waiting for inventory to improve before posting follow-up.
7. **Paywall timing** — monitor engagement via admin dashboard, flip paywall when sessions consistently generate more API cost than affiliate revenue
8. **Opus A/B test** — run same profile through Sonnet and Opus curation with improved inventory (200+ products)
9. **Mother's Day (May 11)** — Guide built, promote once inventory is better

**See `AFFILIATE_APPLICATIONS_TRACKER.md` for detailed affiliate network status.**
