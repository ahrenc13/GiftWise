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
- **Start command:** `gunicorn giftwise_app:app --bind 0.0.0.0:$PORT --workers 3 --timeout 600 --graceful-timeout 120 --worker-class sync --log-level info`
- **Environment variables:** Set in Railway dashboard → Settings → Variables (see RAILWAY_DEBUG_GUIDE.md for required vars)
- **Logs:** Railway dashboard → Deployments → View Logs (or `railway logs` via CLI)
- **Database:** Uses shelve (ephemeral filesystem) — consider migrating to Railway Postgres for persistence across deploys

## How to Test Changes Before Going Live (Beginner Guide)

The golden rule: **main branch = production = real users see it.** Every other branch is safe to experiment on.

### The Safe Workflow (Do This Every Time)

```
1. Claude makes changes on a feature branch (e.g. claude/fix-something)
2. Push to that branch — only affects GitHub, NOT production
3. Test it:
   - Option A (best): Run locally on your machine → python giftwise_app.py → open http://localhost:5000
   - Option B (easy): In Railway dashboard → your project → click "New Deployment" → deploy from branch
     This creates a separate live URL (like abc-branch.up.railway.app) — real internet, not production
   - Option C (risky, only for tiny safe changes): Merge directly to main
4. If it looks good → create a GitHub Pull Request from the feature branch → merge to main
5. Railway sees main changed → auto-deploys to giftwise.fit
```

### What Can Break vs. What's Safe

**Safe to merge without local testing:**
- Text/copy changes in templates
- Adding a new guide or blog post page
- Adjusting a prompt in gift_curator.py or profile_analyzer.py
- Adding a new static affiliate product (Peet's, illy, etc.)
- Changing log messages

**Always test locally or in Railway preview first:**
- Any change to giftwise_app.py routes
- Any change to search/curation pipeline
- New imports or new Python files
- Changes to database.py or storage_service.py
- Anything involving API keys or environment variables

### How to Run Locally (One-Time Setup)

```bash
# In the GiftWise folder:
python giftwise_app.py

# Then open browser to:
http://localhost:5000/demo          # Test without real social data
http://localhost:5000/demo?admin=true   # Test with real pipeline (@chadahren)
```

Your local machine uses a .env file (or exported shell variables) for API keys. Railway uses its own Variables dashboard. They're separate — changing one doesn't affect the other.

### How to Test in Railway Without Touching Production

1. Go to railway.app → your GiftWise project
2. Click your service → "Deployments" tab
3. Click "Deploy" → choose "Deploy from branch" → pick your feature branch
4. Railway gives you a temporary URL for that deploy
5. Test it at that URL
6. If good: merge your branch to main on GitHub → production updates automatically

### The Nuclear Option (If Something Breaks on Production)

In Railway → Deployments → find the last working deployment → click "Redeploy". This rolls back to the previous version in about 60 seconds. No code changes needed.

---

## Paywall Decision Framework

**Current status (Feb 2026): Paywall is NOT enforced. All users get full free access.**

### The Economics

- Claude API cost per session: ~$0.10 (Sonnet, both profile + curator calls)
- Affiliate revenue per session: ~$0.00–$0.05 (most visitors don't buy; commissions only on purchases)
- Railway hosting: ~$5–20/month (fixed, doesn't scale with sessions)

**Implication:** You are currently subsidizing every user's session. That's intentional — you need traffic before you can monetize.

### Paywall Trigger Thresholds

These are the specific signals to watch in the Railway logs and admin dashboard (`/admin/stats?key=ADMIN_DASHBOARD_KEY`):

| Threshold | Meaning | Action |
|-----------|---------|--------|
| **< 5 sessions/day avg** | Growth phase — API cost ~$15/mo, negligible | Keep fully free. Do not restrict anything. |
| **5–15 sessions/day** | Early traction | Add 1 run/day rate limiting per IP. Still free. Watch whether affiliate clicks are growing. |
| **15–30 sessions/day sustained** | Real traffic | Calculate: (sessions × $0.10) vs affiliate revenue in Railway affiliate click logs. If cost >> revenue for 2+ weeks, add account requirement. |
| **30+ sessions/day AND affiliate revenue not catching up** | Paywall decision point | Soft paywall: require free account creation (just email) to run the full pipeline. No charge yet. |
| **Paying users exist** | Only then | Hard paywall with Stripe. A paywall with zero paying customers is just a conversion-killer. |

### How to Check Your Session Count

```
Railway dashboard → your project → Metrics tab
→ Look at "Requests" over the past 7 days
→ Divide by 7 = avg sessions/day

OR:
Admin dashboard: /admin/stats?key=YOUR_KEY
→ "rec_run" events = sessions that ran the full pipeline
```

### Before You Ever Flip a Paywall

1. **Inventory must be good first.** Paywalling thin results (Amazon + eBay only, ~30 products) is a conversion disaster. Wait until Skimlinks/Awin/CJ are live.
2. **TikTok moment:** If the kid posts and traffic spikes, do NOT paywall during that window. Let people run it free, collect emails, build the waitlist. Monetize the warm audience later.
3. **First paywall should be soft:** Require account creation (free, just email), not payment. This gives you email addresses, lets you track users, and creates a "you're in" feeling without friction.
4. **Rate limiting before paywalling:** 1 run per IP per day stops abuse while keeping the product free. Implement this before any payment requirement.

### What the Subscription Tiers Are (Not Yet Enforced)

The code has tier infrastructure built (see `giftwise_app.py` lines ~634+). Planned tiers:
- **Free:** Full access, 1 run/day rate limit
- **Pro ($4.99–$7.99/month):** Multiple profiles, monthly refresh, shareable profile links
- **Gift Emergency ($2.99 one-time):** 10 recs, no account needed — impulse buyer capture

These are NOT enforced yet. The Stripe integration (`/subscribe` route) exists but isn't wired to gatekeeping. Do not wire the paywall until inventory and traffic thresholds above are met.

### North Star: Affiliate vs. Subscription Priority

Right now affiliate revenue is the right focus because:
1. It requires no payment friction — users just click links
2. Every approved affiliate network multiplies revenue without code changes
3. Subscription requires enough volume to justify the conversion funnel overhead

Flip this priority when: monthly affiliate revenue is steady but clearly lower than what a 5% subscription conversion rate would generate at your traffic level.

## What This Is
AI-powered gift recommendation app. Flask pipeline: scrape social media → Claude analyzes profile → enrich with static data → search retailers → Claude curates gifts → programmatic cleanup → display.

**Current State (TL;DR):** App is live and polished. CJ Affiliate is now the primary inventory driver with 15+ wired static partners. Amazon + eBay active. Skimlinks pending (submitted 2/9, still waiting as of 2/25). Awin: applied to ~35 new Gifts & Flowers merchants Feb 25, awaiting approvals. Impact.com: STAT tag + domain verification phrase added, awaiting support resolution. Per-IP rate limiting active. 3 Gunicorn workers. TikTok launch-ready. 10 gift guides + 4 blog posts live for SEO.

## Current State (Feb 25, 2026)

### Major Changes Since Feb 16
1. **CJ Affiliate fully wired** — GraphQL product search integrated, filtering non-joined advertisers, 15+ static partners active
2. **15+ new CJ static partners added** — MonthlyClubs, SoccerGarage, TechForLess, Tenergy, TrinityRoad/Catholic Company, zChocolat (20% — highest commission!), Winebasket/BabyBasket/Capalbo's, plus all previously listed partners
3. **catalog_sync.py added** — CJ product catalog pre-scorer and session cache for discovered CJ products
4. **Per-IP rate limiting live** — 1 run/day per IP (implemented for TikTok launch)
5. **3 Gunicorn workers** — Upgraded from 1 worker to 3 for launch traffic handling
6. **Share-to-unlock gate disabled** — All recommendations shown free (removed friction for launch)
7. **Spotify OAuth removed** — Simplified back to text-only paste at `/connect/spotify-wrapped` (OAuth was causing infinite waits/403s)
8. **Group chat sharing added** — Share recs directly to group chats (Gen Z engagement)
9. **OneSignal web push added** — Opt-in push notifications (activated via `ONESIGNAL_APP_ID` env var in Railway)
10. **Experience quality overhaul** — Bookable vs DIY badges, concert realism fixes, experience synthesis improvements
11. **Curation quality improvements** — Synthesis principle, poster flood fix, dedup bug fixed, anti-trope guidance in curator prompt
12. **AI/algorithm language removed** — Copy shifted to warm "we" voice throughout
13. **eBay affiliate tracking fixed** — EPN campaign params now appended to all links

### What's working
- **Full recommendation pipeline:** Instagram + TikTok scraping → profile analysis → multi-retailer search → curation → cleanup → display
- **Two Claude API calls per session:** `profile_analyzer.py` (call #1), `gift_curator.py` (call #2)
- **Model toggle via env vars:** `CLAUDE_PROFILE_MODEL`, `CLAUDE_CURATOR_MODEL` (default Sonnet for both)
- **Smart filters:** work exclusion, passive/active filtering, obsolete media filter (respects retro/vinyl interests), low-effort item filter
- **Post-curation cleanup:** brand dedup, category dedup (23 patterns), interest spread (max 2), source diversity cap
- **Experience providers:** 13 categories mapped to real booking platforms (Ticketmaster, Cozymeal, Viator, etc.). Bookable vs DIY badges visible on cards.
- **Search query cleaning:** `_clean_interest_for_search()` strips filler from interest names, category-specific suffixes
- **Material matching:** word-overlap scoring with expanded stopwords and 40% threshold
- **Sharing infrastructure:** `/api/share` creates shareable links, `shared_recommendations.html`, `share_generator.py` SVG cards, group chat sharing
- **Referral system:** `referral_system.py` generates codes, tracks referrals (generic, no promo-specific bonuses)
- **Admin dashboard:** `/admin/stats?key=ADMIN_DASHBOARD_KEY` — tracks signups, rec_run, share_create, share_view, guide_hit, error
- **10 editorial gift guides** at `/guides/<slug>` for affiliate approval (6 general + 3 Etsy-focused + 1 Mother's Day)
- **Blog architecture:** `/blog` landing + 4 SEO-optimized articles (cash vs physical gifts, gift mistakes, gifts for people who have everything, last-minute gifts)
- **Demo/skip mode:** `/demo` bypasses social handle requirement. Admin variant (`?admin=true`) pre-fills @chadahren for real pipeline testing.
- **Waitlist system:** `/waitlist` for handle-based early access (Gen Z engagement)
- **Spotify Wrapped integration:** `/connect/spotify-wrapped` accepts text paste of Spotify data for music preference analysis (OAuth removed — text-only)
- **Revenue optimization:** `revenue_optimizer.py` smart pre-filtering scores products before curator sees them (prioritizes high-commission sources)
- **Product database:** SQLite catalog (`database.py`) caches products, tracks click analytics, enables learning loop
- **CJ GraphQL product search:** `cj_searcher.py` queries CJ product feeds for joined advertisers, filters non-joined ones
- **Catalog sync:** `catalog_sync.py` pre-scores discovered CJ products and maintains session cache
- **Affiliate click tracking:** `track_affiliate_click()` logs every product click for performance analysis
- **Per-IP rate limiting:** 1 run/day per IP (active, shown on `rate_limited.html` template)
- **OneSignal push notifications:** Opt-in, activated via `ONESIGNAL_APP_ID` Railway env var. Service worker at `/OneSignalSDKWorker.js`.
- **Privacy, terms, affiliate disclosure** in footer
- **Skimlinks JS snippet** in all templates (publisher ID: 298548X178612)

### What's NOT working / pending
- **Etsy:** 403 on all queries — awaiting developer credentials approval (still pending as of Feb 23)
- **Awin:** Code works but 0 joined advertisers — returns [] immediately. Need to join at https://www.awin.com/us/search/advertiser-directory (priority: Etsy, UGG, Lululemon, Portland Leather)
- **Skimlinks:** Code complete, awaiting publisher approval (submitted Feb 9, still pending as of Feb 23 — well past expected 7-business-day window)
- **Impact.com:** User accidentally signed up as brand instead of publisher. Ticket submitted, no response yet.
- **Rakuten:** Signed up, need to apply to individual brands
- **Walmart Creator:** Application submitted
- **FlexOffers:** Application submitted 2/16, approval status unknown

### Affiliate network applications status (Updated Feb 23)
**See `AFFILIATE_APPLICATIONS_TRACKER.md` for detailed tracking.**

| Network | Status | Brands Covered |
|---------|--------|---------------|
| Skimlinks | ⏳ Still pending (submitted 2/9 — past expected window, follow up) | ~48,500 merchants (blanket access) |
| CJ Affiliate | ✅ Active. GraphQL search wired + 15+ static partners live. See partner rows below. | Subscription clubs, flowers, jewelry, fragrances, gaming, wellness, chocolates, artisan jewelry, charity shopping, coffee, soccer, refurb electronics, batteries, religious gifts, wine/gourmet baskets |
| FlexOffers | ⏳ Application submitted 2/16, status unknown | 12,000+ advertisers, niche brands |
| Awin | ✅ Account active. Feb 25: applied to ~35 Gifts & Flowers merchants (see tiers below). Still need to join: Uncommon Goods, Personalization Mall, Things Remembered, Oriental Trading, HomeWetBar. | Quilling Card, Twisted Lily, LoveIsARose, Limoges Jewelry, Anthemion Flowers, Field Company, CanvasChamp, Sugarwish, Name Stories, Maison Balzac, Formulary 55, Miss to Mrs Box, Enjoy The Wood, La Boîte, Alice Mushrooms, BroBasket, Scribble, Crown and Paw, Palais des Thés, Farmgirl Flowers, Matr Boomie, Cosmos Within, Pacific Resources Intl, Grill Masters Club, Sports Box Co., KOW Steaks, Jasper Hill Farm, Dylan's Candy Bar, Woven Woven, VitaJuwel, Big Night, DEMDACO, Kosterina, Outdoor Fellow, Swanky Badger |
| Impact | ⏳ Ticket open for wrong account type. STAT tag added to base.html (Feb 25). "Hi, Impact" domain verification phrase added to /about (Feb 25, branch `claude/review-claude-docs-kEdui` — merge to main to activate). Awaiting support response. | Target, Ulta, Kohl's, Gap, Home Depot, Adidas, Dyson |
| Rakuten | Account active, need to apply to individual brands | Sephora, Nordstrom, Anthropologie, Free People, Coach |
| Walmart Creator | Application submitted | Walmart |
| Etsy Direct | Developer credentials pending | Etsy (would bypass Awin if approved) |
| Amazon Associates | ✅ Active | Amazon |
| eBay Partner Network | ✅ Active (EPN campaign params wired to all links Feb 23) | eBay |
| illy caffè (via CJ) | ✅ Wired — static products in `_ILLY_ALL_PRODUCTS`. Evergreen link 15734901. | **6% new / 4% existing**, 45-day cookie, ~$125 AOV. Trigger: coffee/espresso interests. Do NOT use discount language — terms prohibit it. ADV_CID: 2184930. |
| Peet's Coffee (via CJ) | ✅ Wired — static products in `_PEETS_ALL_PRODUCTS` | **10% commission**, 45-day cookie. Coupons: NEWSUB30 (30% off first sub), WEBFRIEND5 (5% sitewide). Trigger: coffee/espresso/tea/gourmet/craft culture. Non-commissionable: Gift Cards. |
| MonthlyClubs (via CJ) | ✅ Wired — static products in `_MONTHLYCLUBS_ALL_PRODUCTS`. 6 clubs (beer, wine, cheese, flowers, chocolate, coffee). | Commission varies by club. Trigger: subscription gifting, foodies, alcohol, coffee. |
| Macorner (via CJ) | ✅ Approved — category links only, no product feed. Do NOT add to recommendation pipeline. Only valid if profile explicitly signals sentimental/memory-keeping interest. | Photo pillows, custom mugs, engraved keychains — "polite smile" gift tier |
| FlowersFast (via CJ) | ✅ Wired — static products in `_FLOWERSFAST_ALL_PRODUCTS` | **20% commission**, 45-day cookie, $74 EPC, ~$65 AOV. Same-day flower delivery. Trigger: flowers, romance, anniversaries, birthdays. T&C: Do NOT use "FTD" or "Teleflora" trademarks. ADV_CID: 231679. |
| FragranceShop (via CJ) | ✅ Wired — static products in `_FRAGRANCESHOP_ALL_PRODUCTS` | **5% commission**, 45-day cookie. Trigger: perfume, cologne, fragrance, grooming, beauty, fashion. ADV_CID: 7287203. |
| GameFly (via CJ) | ✅ Wired — static products in `_GAMEFLY_ALL_PRODUCTS` | **$5/lead** (subscription), **10%** used games/accessories. 0% on new games/consoles. Trigger: gaming, video games. ADV_CID: 1132500. |
| GreaterGood (via CJ) | ✅ Wired — static products in `_GREATERGOOD_ALL_PRODUCTS` | **2–15% commission**. Charity-linked shopping. Trigger: pets, animals, philanthropy. Max 1 product returned. ADV_CID: 4046728. |
| GroundLuxe (via CJ) | ✅ Wired — static products in `_GROUNDLUXE_ALL_PRODUCTS` | **10% commission**, $150–221 EPC (highest EPC in stack). Luxury grounding sheets. Trigger: wellness, sleep, yoga, biohacking. No medical claims. ADV_CID: 7681501. |
| Russell Stover (via CJ) | ✅ Wired — static products in `_RUSSELLSTOVER_ALL_PRODUCTS` | **5% commission**, **5-day cookie** (very short). Classic boxed chocolates. Trigger: chocolate, sweets, candy, dessert. ADV_CID: 4441453. |
| SilverRushStyle (via CJ) | ✅ Wired — static products in `_SILVERRUSHSTYLE_ALL_PRODUCTS` | **15% commission**, 60-day cookie, up to $147 EPC. Artisan silver gemstone jewelry. Trigger: jewelry, gemstones, crystals, bohemian, witchy. ADV_CID: 3874186. |
| SoccerGarage (via CJ) | ✅ Wired — static products in `_SOCCERGARAGE_ALL_PRODUCTS` | **7% commission** (scales to 10% at $7.5K/mo), 60-day cookie, ~$125 AOV. Soccer cleats, gear, apparel. Trigger: soccer, football. ADV_CID: 2061630. |
| TechForLess (via CJ) | ✅ Wired — static products in `_TFL_ALL_PRODUCTS` | **5% commission**, 14-day cookie, ~$185 AOV. Refurb/open-box electronics. Trigger: tech, gadgets, laptops. Deep-link enabled (Evergreen ID 15733604). ADV_CID: 3297514. |
| Tenergy (via CJ) | ✅ Wired — static products in `_TENERGY_ALL_PRODUCTS` | **8% commission**, 30-day cookie, $11–13 EPC. Rechargeable batteries, solar, home appliances. Trigger: eco, sustainability, tech accessories. Deep-link enabled. ADV_CID: 1826017. |
| TrinityRoad / Catholic Company (via CJ) | ✅ Wired — static products in `_TRINITYROAD_ALL_PRODUCTS` | **8% commission**, 30–45 day cookie. 6 sites incl. catholiccompany.com, rosary.com. Trigger: Catholic faith milestones (Confirmation, Communion, Baptism, Christmas). Deep-link enabled. ADV_CID: 2871603. |
| zChocolat (via CJ) | ✅ Wired — static products in `_ZCHOCOLAT_ALL_PRODUCTS` | **20% commission** (highest of any partner), 45-day cookie, ~$120 AOV, $75–367 EPC. World-champion French chocolatier, ships to 244 countries. Trigger: chocolate, gourmet, luxury gifts. Deep-link enabled. ADV_CID: 1124214. |
| Winebasket / BabyBasket / Capalbo's (via CJ) | ✅ Wired — static products in `_WINEBASKET_ALL_PRODUCTS` | **7% commission**, 15-day cookie, ~$110 AOV, $52–66 EPC. Wine baskets, baby gift baskets, gourmet food baskets. Trigger: wine, new baby, gourmet food, celebrations. Deep-link enabled. ADV_CID: 2387081. |

**IMPORTANT:** ShareASale migrated to Awin in Oct 2025. All ShareASale merchants are now accessible through Awin.

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

## Opus Audit Checklist (Updated Feb 24 — most items addressed)

**Session `claude/audit-giftwise-codebase-OqSXB` (Feb 24) addressed items 1-9, 11-12. See OPUS_AUDIT.md for original file/line references.**

### Critical (Revenue & Retention) — ALL ADDRESSED
1. ~~`why_perfect` hidden on default card~~ — **FIXED Feb 23-24.** Preview now has green highlight, border-left, italic styling. Visible on every compact card. (`recommendations.html` `.rec-why-preview`)
2. ~~Curator selects boring practical items~~ — **FIXED Feb 23-24.** Anti-trope guidance (Feb 23) + gift reasoning framework with ownership check, adjacency reasoning, identity signal matching, "never buy themselves" test (Feb 24). (`gift_curator.py` lines 203-207)
3. ~~Experience material links mostly unmatched~~ — **EVALUATED Feb 24.** Matching logic already well-built with word overlap scoring (35% threshold, Amazon search fallback). No changes needed.

### High (Quality) — ALL ADDRESSED
4. ~~Image placeholder rate not tracked~~ — **FIXED Feb 24.** `IMAGE_QUALITY` structured log line + `low_image_quality` event in site_stats. (`recommendation_service.py`)
5. ~~Search queries too verbose for eBay~~ — **FIXED Feb 24.** 5-word cap in `clean_interest_for_search`. (`search_query_utils.py`)
6. ~~No boring practical item guidance~~ — **FIXED Feb 23-24.** Handled via anti-trope guidance + gift reasoning framework in curator prompt (taste problem, not code problem).

### Medium (Edge Cases) — MOSTLY ADDRESSED
7. ~~Material matching stopwords too aggressive~~ — **ALREADY FIXED** before audit. Split into `_NOISE_STOPWORDS` and `_CONTEXT_WORDS` at `giftwise_app.py:3024-3049`.
8. ~~Category dedup misses uncategorized dupes~~ — **FIXED Feb 23-24.** Duplicate replacement fix (Feb 23) + Rule 4b title word overlap for uncategorized products (Feb 24). (`post_curation_cleanup.py`)
9. ~~Brand dedup blocks same-brand different-category~~ — **FIXED Feb 24.** Relaxed: same brand allowed across different categories. (`post_curation_cleanup.py`)
10. **Shared recommendations page needs more personality** — DEFERRED. Needs UX design decisions. Trigger: when share_view events show low engagement.
11. ~~Experience bookable vs DIY badges~~ — **FIXED Feb 23-24.** Badges on expanded (Feb 23) + compact cards (Feb 24). (`recommendations.html`)
12. ~~Rec count subtitle~~ — **ALREADY FIXED** before audit. Template distinguishes "X gifts + Y experiences".

### Meta-Principle for the Audit
**Do NOT make piecemeal fixes.** Previous sessions added features without wiring them together — `sharing_section.html` was built but never included, `share_generator.py` and `referral_system.py` were imported but never created, `valentines_landing.html` existed with no route. Every change must be fully wired end-to-end: code → route → template → tested. If you build it, connect it.

## Technical Architecture Notes

### Key Files
- `giftwise_app.py` — Main app, orchestrates the full pipeline
- `profile_analyzer.py` — Claude call #1: social data → structured profile. Model via `CLAUDE_PROFILE_MODEL` env var.
- `gift_curator.py` — Claude call #2: profile + inventory → curated recommendations. Model via `CLAUDE_CURATOR_MODEL` env var.
- `post_curation_cleanup.py` — Programmatic enforcement of diversity rules (brand, category, interest, source). 23 category patterns.
- `interest_ontology.py` — Pre-LLM thematic enrichment: maps interests to attribute clusters, clusters into themes, infers gift philosophy, generates adjacency hints. Zero API cost. Feeds curator prompt.
- `enrichment_engine.py` — Static intelligence layer (do_buy/dont_buy per interest, demographics, trending)
- `multi_retailer_searcher.py` — Orchestrates all retailer searches, merges inventory pool. Order: Etsy → Awin → CJ → eBay → Skimlinks → Amazon
- `rapidapi_amazon_searcher.py` — Amazon search + shared query cleaning functions (`_clean_interest_for_search`, `_categorize_interest`, `_QUERY_SUFFIXES`)
- `ebay_searcher.py` — eBay search with EPN campaign params on all links
- `etsy_searcher.py`, `awin_searcher.py`, `skimlinks_searcher.py`, `cj_searcher.py` — Per-retailer search modules
- `cj_searcher.py` — CJ Affiliate: GraphQL product search + 15+ static partner product lists. All `_*_ALL_PRODUCTS` lists live here.
- `catalog_sync.py` — CJ product catalog pre-scorer and session cache for discovered CJ products
- `spotify_parser.py` — Spotify Wrapped text parser (text-only; OAuth was removed)
- `smart_filters.py` — Work exclusion, passive/active filtering, `ObsoleteFormatFilter` (respects retro interests), low-effort item filter
- `image_fetcher.py` — Thumbnail validation and fallback chain
- `relationship_rules.py` — Relationship-appropriate gift guidance (soft curator guidance, not hard filter)
- `experience_providers.py` — Maps 13 experience categories to real booking platforms (Ticketmaster, Cozymeal, Viator, etc.)
- `experience_architect.py` — Builds bookable vs DIY experience packages with cost breakdowns
- `revenue_optimizer.py` — Smart pre-filtering: scores products by commission rate, past performance, interest match before sending to curator
- `database.py` — SQLite product catalog for caching, click tracking, learning loop
- `oauth_integrations.py` — OAuth flows for Pinterest, Etsy, Google/YouTube. (Spotify OAuth removed — text paste only now)
- `site_stats.py` — Lightweight event counter for admin dashboard (shelve-backed)
- `share_manager.py` — Share link generation and storage (shelve-backed, 30-day expiry)
- `share_generator.py` — SVG share card generator (generic, no campaign-specific code)
- `referral_system.py` — Referral codes, tracking (generic, no promo-specific bonuses)
- `social_conversion.py` — Generic urgency messaging, growth loops (campaign-specific code removed)
- `OPUS_AUDIT.md` — Detailed audit checklist with file/line references for quality review
- `AFFILIATE_APPLICATIONS_TRACKER.md` — Detailed affiliate network status tracker
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
- Pinterest OAuth for visual taste analysis
- Etsy OAuth for favorites (when approved)
- Google OAuth for YouTube subscriptions
- NOTE: Spotify OAuth was added then removed (caused infinite waits/403s). Now text-only paste via `spotify_parser.py` at `/connect/spotify-wrapped`.

**Interest Ontology (`interest_ontology.py`) — Added Feb 24:**
- Pre-LLM enrichment layer. Runs BEFORE the curator call. Zero API cost.
- Maps ~100 interests to attribute clusters (era, ethos, format, aesthetic, domain, mindset, social, intensity)
- Clusters interests sharing 2+ attributes into themes (e.g., "yoga + hiking + meditation" → "active wellness and mindfulness")
- Infers gift philosophy: object vs experience person, collector vs consumer, signaler vs private, upgrader vs explorer
- Generates adjacency hints: domain-specific "one step beyond the obvious" suggestions
- Output is a `curator_briefing` text block prepended to the curator prompt
- Wired in `recommendation_service.py` → `_curate_gifts()` → passed as `ontology_briefing` param to `curate_gifts()`
- **IMPORTANT: This module is deterministic code, not an LLM call. The INTEREST_ATTRIBUTES dict and KEYWORD_HEURISTICS can be expanded over time. Architecture matters more than completeness of the initial mapping.**

### Intelligence Layer Architecture (CRITICAL — read before modifying prompts)

The recommendation pipeline has a carefully balanced three-layer intelligence architecture. **Do NOT modify one layer without understanding how it interacts with the others.**

**Layer 1: Pre-LLM Code (zero cost)**
- `interest_ontology.py` — Thematic enrichment (themes, philosophy, adjacency hints)
- `enrichment_engine.py` — Static do_buy/dont_buy, demographics, trending
- `revenue_optimizer.py` — Commission-rate scoring, click-history scoring
- `search_query_utils.py` — Query building (5-word cap, category suffixes)

**Layer 2: LLM Prompts (taste & judgment)**
- `profile_analyzer.py` — Extracts interests, ownership signals, aesthetic summary, gaps
- `gift_curator.py` — Gift reasoning framework (ownership check, adjacency, identity signals, "never buy themselves" test)
- The curator prompt includes ontology briefing, ownership signals, and the full reasoning framework
- **Token budget: ~$0.10-0.15/session on Sonnet. Current additions are ~255 tokens (~$0.0008). Do NOT add 500+ tokens without trimming elsewhere.**

**Layer 3: Post-LLM Code (rules & guarantees)**
- `post_curation_cleanup.py` — Brand dedup (relaxed for different categories), category dedup, uncategorized near-dedup, interest spread, source diversity
- `smart_filters.py` — Work exclusion, passive/active, obsolete format, low-effort
- `giftwise_app.py` `_backfill_materials_links()` — Material matching with word overlap scoring

**Key balances to preserve:**
1. **Prompts for taste, code for rules.** The curator prompt guides judgment (adjacency reasoning, identity signals). Code enforces guarantees (no duplicate brands in same category, max 2 per interest). Never flip this — a `BoringPracticalFilter` in code would be wrong; boring-item rejection belongs in the prompt.
2. **Ontology enriches, it doesn't filter.** The ontology adds context to the curator prompt (themes, philosophy, hints). It never removes products or interests. It's additive.
3. **Brand dedup is relaxed intentionally.** Same brand CAN appear twice if categories differ (Taylor Swift poster + Taylor Swift enamel pin). This was an audit fix — don't tighten it back.
4. **Search queries are capped at 5 words.** This prevents eBay 400 errors. Don't remove this cap.
5. **Ownership signals flow through the whole pipeline.** Profile analyzer detects them → profile dict carries them → curator prompt shows them in ALREADY OWNS section → curator avoids duplicates. If you modify the profile schema, ensure ownership_signals still flows.

### ⚠️ Opus-Only Zones — Sonnet Must Not Modify

The files below contain in-code `⚠️ OPUS-ONLY ZONE` markers. These protect the recommendation engine's taste and quality layer. **Sonnet sessions: if you encounter a quality/taste issue in these areas, add a `# SONNET-FLAG:` comment describing the problem and move on. Do not attempt the fix.**

| File | Protected Sections | Why |
|------|--------------------|-----|
| `interest_ontology.py` | Theme clustering thresholds, gift philosophy inference, curator_briefing format, keyword heuristics | Threshold changes produce garbage themes or bloated token costs. Adding interests to INTEREST_ATTRIBUTES is safe. |
| `gift_curator.py` | GIFT REASONING FRAMEWORK, SELECTION PRINCIPLE, SYNTHESIS OVER CHECKLIST, ownership_section, pronoun/warm-language instructions, aesthetic_summary wiring | This is the taste engine. Rewording, reordering, or adding prompt instructions changes recommendation quality in subtle ways that are hard to test. |
| `profile_analyzer.py` | Section 1b OWNERSHIP SIGNALS, aesthetic_summary schema field, interest type taxonomy (aspirational\|current) | Downstream pipeline depends on exact field names and the aspirational/current distinction. |
| `post_curation_cleanup.py` | Rule 3 brand relaxation, Rule 4b uncategorized near-dedup, MAX_PER_SOURCE_PCT, deferred→replacement backfill | These relaxations are intentional. Tightening kills good picks; loosening causes duplicates. Adding new category/brand patterns is safe. |

**What IS safe for Sonnet:** Bug fixes (crashes, missing fields, import errors), template rendering, CSS, API response handling, adding new category/brand patterns, adding entries to INTEREST_ATTRIBUTES, logging, and any code that doesn't touch prompt wording or rule thresholds.

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
- eBay (Browse API): Active, working (~12 products per run). EPN campaign params wired to all links.
- CJ Affiliate (GraphQL): Active — searches product feeds for joined advertisers, skips non-joined. 15+ static partner lists as fallback/supplement.
- Etsy (v3 API): Awaiting developer credentials (all queries return 403)
- Awin (Data Feed API): Code working, but gated — returns [] until advertisers are joined
- Skimlinks (Product Key API v2): Code complete, awaiting publisher approval (submitted 2/9, still pending 2/23)
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

## Testing Strategy (Feb 16, 2026 - Post-Refactoring)

**Major architectural improvement:** After Phase 3 refactoring (Feb 16), the codebase is now highly testable with isolated services, comprehensive test suites, and clear testing patterns.

### Testing Philosophy

**Test what matters:**
1. **Service modules** - Isolated, comprehensive unit tests (built-in test suites)
2. **Integration points** - End-to-end pipeline tests (profile → search → curate → display)
3. **User-facing features** - Browser testing for key flows
4. **Deployment safety** - Pre-deploy checklist ensures no breaking changes

**Don't over-test:**
- Templates (if they render, they work - use browser testing)
- Simple utility functions (if they're used in tested code, they're validated)
- External APIs (mock them - we can't control eBay/Amazon uptime)

---

### Built-In Test Suites (Run These First)

All service modules have comprehensive `if __name__ == "__main__"` test suites. **Run these before committing any changes:**

```bash
# Core services (78 total tests)
python3 storage_service.py          # 10 tests - shelve operations, TTL, thread safety
python3 search_query_utils.py       # 17 tests - query building, categorization
python3 config_service.py           # 10 tests - env loading, validation
python3 product_schema.py           # 10 tests - product parsing, validation
python3 api_client.py               # 8 tests  - retry logic, error handling
python3 auth_service.py             # 10 tests - token caching, refresh
python3 base_searcher.py            # 6 tests  - searcher patterns
python3 image_fetcher.py            # 7 tests  - image extraction (enhanced)

# Intelligence modules
python3 reddit_scraper.py           # Standalone test with fallback data
python3 yelp_trending.py            # Standalone test with fallback data
python3 regional_culture.py         # 4 tests  - region/city context
python3 seasonal_experiences.py     # 5 tests  - seasonal filtering
python3 local_events.py             # 3 tests  - event calendar

# Run all at once (if all pass, you're good to commit)
for module in storage_service.py search_query_utils.py config_service.py product_schema.py api_client.py auth_service.py base_searcher.py image_fetcher.py; do
    echo "Testing $module..."
    python3 $module || exit 1
done
echo "✅ All service tests passed"
```

**Expected output:** All tests should pass with "✅" indicators. Any failures indicate breaking changes.

---

### Integration Testing (End-to-End Pipeline)

**Test the full recommendation pipeline** to ensure services work together:

#### Quick Integration Test (Local Development)

```bash
# 1. Start Flask app locally
python3 giftwise_app.py

# 2. Visit in browser
open http://localhost:5000

# 3. Test key flows:
#    - Homepage loads
#    - /demo works (bypasses social scraping)
#    - /demo?admin=true pre-fills @chadahren
#    - Recommendations render
#    - Templates inherit from base.html (check nav/footer appear)
#    - Skimlinks snippet loads (DevTools → Network → search for "298548X178612")

# 4. Check logs for errors
#    Should see: "Regional intelligence loaded", "Config loaded", etc.
```

#### Full Pipeline Test (With Real Data)

```bash
# Test with real Instagram/TikTok scraping
# Uses @chadahren (owner account) to test full pipeline

# 1. Visit /demo?admin=true
# 2. Should see profile analysis progress
# 3. Should see product search (Amazon, eBay, etc.)
# 4. Should see gift curation (Claude API call)
# 5. Should see recommendations with regional context
# 6. Check that experiences include neighborhood data (if applicable)
```

**What to verify:**
- ✅ Profile built successfully (interests extracted)
- ✅ Products found from multiple retailers
- ✅ Gifts curated with `why_perfect` descriptions
- ✅ Regional context appears in experiences (e.g., "East Austin vibe")
- ✅ Material links work (not all "Find on Amazon")
- ✅ Images load (not all placeholders)

---

### Service Testing Patterns

#### Testing Storage Service

```python
from storage_service import StorageService
import tempfile

# Create test database
with tempfile.NamedTemporaryFile(delete=False) as tmp:
    test_db = tmp.name

storage = StorageService(test_db)

# Test basic operations
storage.set('test_key', 'test_value')
assert storage.get('test_key') == 'test_value'

# Test TTL cleanup
import time
storage.set('old', {'created_at': time.time() - 200, 'data': 'old'})
storage.set('new', {'created_at': time.time(), 'data': 'new'})
deleted = storage.cleanup_expired(ttl_field='created_at', max_age_seconds=100)
assert deleted == 1
assert not storage.exists('old')

# Cleanup
import os
os.remove(test_db)
```

#### Testing Config Service

```python
from config_service import get_config

# Load config (validates required env vars)
config = get_config()

# Check availability
assert config.claude.api_key  # Should be set
print(f"Using model: {config.claude.curator_model}")

# Check retailer availability
from config_service import is_retailer_available
if is_retailer_available('amazon'):
    print("✓ Amazon searcher enabled")
if is_retailer_available('ebay'):
    print("✓ eBay searcher enabled")
```

#### Testing Product Schema

```python
from product_schema import Product, build_product_list

# Test Amazon product parsing
amazon_item = {
    'product_title': 'Wireless Headphones',
    'product_url': 'https://amazon.com/...',
    'product_photo': 'https://m.media-amazon.com/...',
    'product_price': '$49.99',
    'asin': 'B08ABC123'
}

product = Product.from_amazon(amazon_item, query='headphones', interest='music')
assert product.title == 'Wireless Headphones'
assert product.source_domain == 'amazon.com'
assert product.commission_rate == 0.02  # 2% for Amazon

# Convert to curator format
product_dict = product.to_dict()
assert 'title' in product_dict
assert 'link' in product_dict
```

#### Testing Search Query Utils

```python
from search_query_utils import build_search_query, clean_interest_for_search

# Test query cleaning
cleaned = clean_interest_for_search("Taylor Swift fandom and concert merch")
assert cleaned == "Taylor Swift concert merch"  # "fandom" removed

# Test query building
query = build_search_query("hiking", intensity='strong')
assert "hiking" in query.lower()
assert "equipment" in query.lower() or "gear" in query.lower()  # Suffix added

# Test batch building
from search_query_utils import build_queries_from_profile
profile = {
    'interests': [
        {'name': 'hiking', 'strength': 'strong'},
        {'name': 'coffee', 'strength': 'medium'}
    ]
}
queries = build_queries_from_profile(profile, max_queries=5)
assert len(queries) <= 5
assert queries[0]['interest'] == 'hiking'
```

---

### Browser Testing (Manual QA Checklist)

**Run this checklist before deploying to production:**

#### Homepage & Navigation
- [ ] Homepage loads at giftwise.fit
- [ ] Navigation appears on all pages (from base.html)
- [ ] Footer appears on all pages (from base.html)
- [ ] All nav links work (Guides, Blog, Get Started)
- [ ] Skimlinks loads (DevTools → Network → "298548X178612")

#### Demo/Test Mode
- [ ] `/demo` loads and bypasses social handle requirement
- [ ] `/demo?admin=true` pre-fills @chadahren for testing
- [ ] Fake recommendations render correctly in demo mode
- [ ] Real pipeline runs successfully in admin mode

#### Recommendation Flow
- [ ] Social handle input validates correctly
- [ ] Profile analysis shows progress updates
- [ ] Recommendations render with images
- [ ] "Why it's perfect" descriptions appear
- [ ] Material links work (experiences with shopping lists)
- [ ] Experience cards show "📅 Book" or "🛠️ Plan" badges
- [ ] Regional context appears in experience descriptions
- [ ] Sharing works (creates shareable link)

#### Gift Guides & Blog
- [ ] `/guides` landing page lists all 10 guides
- [ ] Individual guide pages render correctly
- [ ] `/blog` landing page lists all 4 posts
- [ ] Blog posts render correctly
- [ ] All pages have Skimlinks snippet

#### Admin Dashboard
- [ ] `/admin/stats?key=ADMIN_DASHBOARD_KEY` loads
- [ ] Stats display correctly (signups, rec_run, shares, etc.)
- [ ] Today/week/7-day breakdowns work

---

### Pre-Deployment Checklist

**Before pushing to `main` (triggers Railway auto-deploy):**

1. **Run all service tests:**
   ```bash
   python3 storage_service.py && \
   python3 config_service.py && \
   python3 product_schema.py && \
   python3 search_query_utils.py && \
   echo "✅ Core services passing"
   ```

2. **Syntax check critical files:**
   ```bash
   python3 -m py_compile giftwise_app.py recommendation_service.py
   ```

3. **Test locally:**
   ```bash
   python3 giftwise_app.py
   # Visit http://localhost:5000/demo
   # Verify homepage, demo mode, at least 1 guide, 1 blog post
   ```

4. **Check Railway env vars are set:**
   - `ANTHROPIC_API_KEY` (required)
   - `AMAZON_AFFILIATE_TAG` (for affiliate revenue)
   - `EBAY_CLIENT_ID`, `EBAY_CLIENT_SECRET` (for eBay search)
   - Other retailer credentials as needed

5. **Review commit message:**
   - Clear description of changes
   - Link to Claude.ai session if complex refactoring

6. **Push to branch first, test on Railway preview:**
   ```bash
   git push origin feature-branch
   # Railway creates preview deployment
   # Test on preview URL before merging to main
   ```

7. **Merge to main only after preview testing:**
   ```bash
   # Via GitHub PR (preferred) or direct push
   git checkout main
   git merge feature-branch
   git push origin main
   # Railway auto-deploys to production
   ```

---

### Testing After Deployment

**Verify production deployment at giftwise.fit:**

1. **Smoke test (5 min):**
   - [ ] Homepage loads
   - [ ] `/demo` works
   - [ ] 1 gift guide loads
   - [ ] 1 blog post loads
   - [ ] No 500 errors in Railway logs

2. **Full test (15 min):**
   - [ ] Run full demo flow
   - [ ] Check recommendations render
   - [ ] Verify Skimlinks loads
   - [ ] Test sharing link creation
   - [ ] Check admin dashboard stats

3. **Monitor Railway logs for errors:**
   ```bash
   railway logs --tail 100
   # Look for Python errors, API failures, etc.
   ```

---

### Common Testing Patterns

#### Mocking External APIs

When testing code that calls external APIs (Amazon, eBay, Yelp), mock the responses:

```python
from unittest.mock import Mock, patch

# Mock API client
with patch('api_client.APIClient.get') as mock_get:
    mock_get.return_value = {'data': [{'product_title': 'Test Product'}]}

    # Test searcher with mocked API
    from base_searcher import AmazonSearcher
    searcher = AmazonSearcher(api_key='test_key')
    products = searcher.search(profile, target_count=5)

    assert len(products) > 0
    assert products[0].title == 'Test Product'
```

#### Testing Template Rendering

```python
# Test that templates inherit from base.html correctly
from flask import Flask
app = Flask(__name__)

with app.app_context():
    from flask import render_template

    # Render a page
    html = render_template('index.html')

    # Check for base.html elements
    assert '<nav class="nav">' in html  # From nav.html include
    assert '<footer class="footer">' in html  # From footer.html include
    assert '298548X178612' in html  # Skimlinks from base.html
```

#### Testing Regional Intelligence

```python
from regional_culture import get_regional_context

# Test NYC neighborhood granularity
williamsburg = get_regional_context(
    city='New York',
    state='NY',
    neighborhood='Williamsburg',
    age=28,
    gender='F'
)

assert 'neighborhood_data' in williamsburg
assert williamsburg['neighborhood_data']['vibe'] == 'hipster_central_artisan'

# Test fallback for cities without neighborhood data
indy = get_regional_context(city='Indianapolis', state='IN', age=28, gender='F')
assert 'city_vibe' in indy
assert 'neighborhood_data' not in indy  # Indianapolis treated as single city
```

---

### Debugging Failed Tests

**If a test fails:**

1. **Read the error message carefully** - it usually tells you exactly what's wrong
2. **Check recent changes** - did you modify a file that breaks the test?
3. **Run the test in isolation** - `python3 module_name.py` to see full output
4. **Check imports** - are all required modules available?
5. **Verify environment** - are required env vars set?
6. **Check Railway logs** - production failures often show up in logs first

**Common failure modes:**
- **Import errors:** Missing module (check if file was renamed/moved)
- **Env var errors:** `ANTHROPIC_API_KEY not set` (check Railway dashboard)
- **API errors:** External API down (check status pages, use fallback data)
- **Template errors:** Jinja2 syntax error (check template inheritance)

---

### Performance Testing

**Monitor these metrics after major changes:**

1. **API call count per session:**
   - Profile analysis: 1 Claude API call
   - Gift curation: 1 Claude API call
   - Retailer searches: 2-5 API calls (Amazon, eBay, etc.)
   - **Target: < 10 total API calls per session**

2. **Session cost:**
   - Sonnet profile + curator: ~$0.10/session
   - Opus curator (if enabled): ~$0.25-0.50/session
   - **Target: < $0.15/session on Sonnet**

3. **Response time:**
   - Profile analysis: 10-20 seconds
   - Product search: 15-30 seconds
   - Gift curation: 15-25 seconds
   - **Total: 40-75 seconds end-to-end**

4. **Cache hit rates (when implemented):**
   - Product database cache: Target 30-40% hit rate
   - Reddit cache: Target 80%+ hit rate (6-hour TTL)
   - Yelp cache: Target 90%+ hit rate (30-min TTL)

---

### Continuous Testing (Future)

**Not yet implemented, but recommended for future:**

1. **GitHub Actions CI/CD:**
   - Run all service tests on every commit
   - Block PRs if tests fail
   - Auto-deploy to Railway preview on PR creation

2. **Pytest migration:**
   - Convert `if __name__ == "__main__"` tests to pytest
   - Add test coverage reporting
   - Organize tests in `tests/` directory

3. **Integration test suite:**
   - Dedicated `tests/integration/` directory
   - Mock all external APIs
   - Test full pipeline with fake data

4. **Load testing:**
   - Simulate 100 concurrent sessions
   - Identify bottlenecks (database, API rate limits)
   - Ensure Gunicorn workers scale properly

---

### Testing Best Practices (From Experience)

**Do:**
- ✅ Run service tests before committing
- ✅ Test locally before pushing to Railway
- ✅ Use `/demo?admin=true` to test real pipeline without rate limits
- ✅ Check Railway logs after deployment
- ✅ Test on multiple browsers (Chrome, Safari, Firefox)
- ✅ Verify mobile rendering (responsive design)

**Don't:**
- ❌ Push directly to `main` without testing
- ❌ Skip service tests ("it compiles, ship it")
- ❌ Test only on localhost (production has different env vars)
- ❌ Ignore Railway logs (errors often show up there first)
- ❌ Assume templates work without browser testing
- ❌ Test with production API keys in local dev (use separate keys)

**Remember:**
- Templates are tested by rendering in browser, not unit tests
- External APIs should be mocked for reliable testing
- Service modules are the core of testing strategy (78 tests total)
- Integration testing validates that services work together
- Browser testing catches UX issues that unit tests miss

**When in doubt, run this:**
```bash
python3 storage_service.py && \
python3 config_service.py && \
python3 product_schema.py && \
python3 giftwise_app.py &
sleep 2 && curl http://localhost:5000/demo && \
echo "✅ Basic tests passed"
```

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

## Recent Commit History (Last 20, as of Feb 23)

```
7cd33d5 Remove AI/algorithm language, shift to warm "we" voice
57279e1 Fix catalog queries excluding TikTok Shop products
2221fbd Improve curation quality: synthesis principle, poster flood fix, dedup bug
f0c46f9 Improve generating page: merge CJ into Specialty Brands, hide zero-result retailers
c8fec4b Improve experience gift quality: bookable vs DIY, concert realism, routing fix
fbfb21c Block holiday-themed interest replacements with no thematic title match
2fb993b Fix duplicate replacement products in post-curation cleanup
f51c437 Document deferred "Also on Amazon" dual-link idea with constraints
e5f7f61 Fix audit findings: crash safety, thread safety, DB concurrency
5616784 Add catalog_sync.py: CJ product catalog pre-scorer and session cache
052bea4 Tighten gifting trope triggers and add curator anti-trope guidance
9594968 Add zChocolat and Winebasket/BabyBasket/Capalbo's as CJ static partners
37095e8 Add Trinity Road / Catholic Company as CJ static partner
d142e83 Add SoccerGarage, Tech For Less, and Tenergy as CJ static partners
7779173 Remove Spotify OAuth, simplify music input to text-only
99e101c Prep for TikTok launch: 3 workers + per-IP rate limiting
70000e5 Add group chat sharing and OneSignal web push for Gen Z re-engagement
29b553d Fix static partner injection (Peet's/illy/MonthlyClubs survive CJ API outage)
8d51c63 Fix eBay affiliate tracking — append EPN campaign params to all links
0a87c5c Add FlowersFast and FragranceShop static CJ affiliate partners
```

Key themes: CJ fully wired (GraphQL + 15 static partners), launch hardening (3 workers, rate limiting), experience quality, curation quality, Spotify OAuth removed.

## Current Development Focus

**Immediate Priority: Unlock More Inventory**
CJ is live with 15+ static partners. Now need to expand further:

1. **Skimlinks** (highest remaining impact) — Blanket access to ~48,500 merchants. Submitted Feb 9, still pending Feb 23. Follow up directly.
2. **Awin** (high impact) — Account active. Need to join former ShareASale merchants: Uncommon Goods, Personalization Mall, Things Remembered, Oriental Trading, HomeWetBar.
3. **FlexOffers** (high impact) — Applied Feb 16. Status unknown — check dashboard.
4. **Impact.com** (fix account type) — Accidentally signed up as brand not publisher. Ticket open, no response.
5. **Rakuten** — Account active, need to apply to individual brands (Sephora, Nordstrom, etc.)

**Secondary: Quality & Conversion**
- Curation quality improved (synthesis principle, anti-trope guidance)
- Experience pipeline overhauled (bookable vs DIY)
- AI/algorithm language removed, warm "we" voice throughout
- Watch admin dashboard for CTR and affiliate click patterns

**Ready: TikTok Launch**
App is in good shape. 3 workers, rate limiting, all recs shown free. Per CLAUDE.md paywall guidance — keep fully free until 15+ sessions/day.

## What the User Wants Next (Updated Feb 25)

1. **Follow up on Skimlinks** — Past the 7-business-day window. Contact publisher support directly.
2. **Awin — await approvals** — Applied Feb 25 to ~35 Gifts & Flowers merchants (see affiliate table). Still need to join: Uncommon Goods, Personalization Mall, Things Remembered, Oriental Trading, HomeWetBar. Auto-approvals expected 24-48h; manual 3-7 days.
3. **Check FlexOffers status** — Applied Feb 16, status unknown
4. **Fix Impact account** — Ticket open. STAT tag + "Hi, Impact" verification phrase live on branch `claude/review-claude-docs-kEdui`. **Merge that branch to main** to activate the verification. Once Impact confirms, remove the "Hi, Impact" phrase from `/about`.
5. **Monitor quality** — admin dashboard at `/admin/stats?key=ADMIN_DASHBOARD_KEY`. Watch rec_run, affiliate click events.
6. **TikTok launch** — App is launch-ready. User's kid has viral post (150k+ likes). Inventory much better now with CJ partners live.
7. **Paywall timing** — monitor engagement via admin dashboard per the paywall thresholds above
8. **Opus A/B test** — run same profile through Sonnet and Opus curation (now viable with better inventory)
9. **Mother's Day (May 11)** — Guide built, start promoting in late March/early April
10. **Apple Music** — Not feasible. No "Wrapped" equivalent for easy user export; OAuth approach already failed with Spotify. Recommend free-text "favorite artists/genres" field instead — works for all music platforms.
10. **"Also on Amazon" dual-link (deferred)** — For products where we can cleanly verify an *identical* item on the vendor's own Amazon storefront (not just a similar product), surface a secondary "Also on Amazon →" link below the primary CTA. No routing by preference, no comparative framing — just a second link for Prime users. **Hard requirement:** must be the same SKU via the brand's Amazon storefront, not a look-alike. Build only after multi-retailer inventory is live and click data shows demand. See OPUS_AUDIT.md for implementation notes.

**See `AFFILIATE_APPLICATIONS_TRACKER.md` for detailed affiliate network status.**
