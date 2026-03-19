# GiftWise — Project Intelligence

**When the user asks you to debug something:** Read the "Debugging Approach" section below first. Follow it (vary the layer, ask for high-leverage signals, cheap checks before deep ones) before spending time on server-side theories.

---

## Debugging Approach (Read Before Every Debug Session)

This codebase is complex enough that locking onto one layer or one story wastes hours. The generation-POST bug is the canonical example: it looked like a thread issue, then a service worker issue, then a session issue — the actual cause was a single apostrophe in a template. Apply this discipline every time.

**1. Vary the layer before going deep.**
For any bug, explicitly name at least two layers before digging: client (JS, DOM, browser console) vs server (route, session, worker thread) vs network (request never sent, redirect, CORS) vs build/deploy (stale asset, wrong branch deployed, env var missing). Ask: "What's the smallest thing that could explain this?" Often it's one character in a template, not an architectural flaw.

**2. Ask for the highest-leverage signal first.**
Don't ask for a full log dump. Ask for the one thing that rules out an entire category:
- "Open DevTools → Console. Any red errors? What's the exact first line?"
- "In Network tab, does a request to `/api/...` appear at all?"
- "When did it last work? What was the last commit touching this flow?"
One precise answer is worth more than 200 lines of logs.

**3. Cheap, broad checks before deep ones.**
In order: console errors → Network tab → syntax/parse errors in emitted JS → session/cookie state → worker/thread → architectural issues. Don't reverse this order.

**4. If stuck, change the search strategy.**
If server-side reasoning isn't paying off after 2-3 cycles, switch: "Could this be a client parse error? A cached script? A redirect?" If focused on one file, check the thing that embeds it (template, caller). If the flow is long, find the first possible failure point and check that first.

**5. Templates that emit JS are a hidden risk surface.**
Jinja2 variables inside `<script>` blocks can break the entire script with one character (unescaped quote, None rendered as "None", etc.). **Single-quoted strings that contain apostrophes** (e.g. `'We're'`, `'don't'`, `'it's'`) are a common cause: the apostrophe ends the string early, the rest of the word is parsed as an identifier, and you get "Unexpected identifier 're'" (or similar). The whole script then fails to parse and never runs — so no fetch, no POST, no logs. When a script silently does nothing, ask for the **first line in the browser Console** (F12 → Console). If you see a syntax error, search the template for single-quoted strings with apostrophes and fix by using double quotes or escaping. Prefer passing data via `data-` attributes or a single `<script id="...">JSON.parse</script>` pattern over inline Jinja substitutions.

**6. After fixing, record what you checked and in what order.**
Add a one-line summary to the bug resolution note: "Checked server route first (no logs), then asked for console errors, found X." This trains future sessions and shortens the next debug.

**Paste at the start of any debug session:**
> "Vary the layer (client vs server vs network vs deploy). Ask for one high-leverage signal (console errors or Network tab). Cheap broad checks first. If stuck, change strategy."

---

## ✅ RESOLVED: Generation POST Never Reached Flask (Mar 2026)

**Symptom:** "Finding the Perfect Gifts…" / "Getting started…" spins forever. No `[ROUTE] /api/generate-recommendations` in server logs. No POST in Network tab.

**Root cause:** A **JavaScript syntax error** in `templates/generating.html`. The `funFacts` array used single-quoted strings. One string was `'We're searching stores most people never think to look.'` — the apostrophe in **We're** ended the string after `We`, so the parser saw the next token as the identifier **re** → **Uncaught SyntaxError: Unexpected identifier 're'**. The entire script block failed to parse, so nothing ran: no `startGeneration()`, no `fetch()`, no POST.

**Fix:** Use double quotes for those strings (e.g. `"We're searching..."`, `"words don't."`) so apostrophes don't break parsing.

**Lesson:** Multiple sessions focused on server-side (threads, service workers, session size, redirects). The fix was client-side. **Always ask for the browser Console (F12 → Console) and the first error line** before investing in server-side theories. Single-quoted strings containing apostrophes in templates that emit JS are a recurring pitfall — search for them when you see "Unexpected identifier" or a script that "does nothing."

**Also merged (from earlier sessions):** SQLite progress store (cross-worker), 90s retailer thread timeout, Awin catalog sync, parallel retailer search. The generating page now uses `recipient_type | tojson` for safe JS and console logs (`[GiftWise] Generating page script running` / `Sending POST to /api/generate-recommendations`) for future debugging.

---

## Pending Opus Tasks

Tasks flagged `# SONNET-FLAG:` in the codebase that require Opus to implement correctly.
Each entry below includes the Opus prompt to copy-paste.

### [OPEN] Load Testing & Architectural Stress Audit

**Opus prompt:**

> You are auditing GiftWise (a Flask/Gunicorn app on Railway.app) for architectural weaknesses that will cause failures or data loss under concurrent traffic. Traffic is coming — we don't know how much. Do not assume 150k TikTok views translates to X sessions; treat it as an unknown burst of real concurrent users.
>
> Read the full codebase — especially `giftwise_app.py`, `storage_service.py`, `site_stats.py`, `share_manager.py`, `database.py`, `recommendation_service.py`, and the Gunicorn config in `railway.json`. Then answer these questions precisely:
>
> 1. **Shelve concurrency.** `storage_service.py`, `site_stats.py`, and `share_manager.py` use Python shelve. Gunicorn runs 3 synchronous workers. Are there write races? Can shelve corrupt under concurrent writes from multiple workers? What is the actual failure mode?
>
> 2. **Worker exhaustion.** Claude API calls take 10–25 seconds each; there are 2 per session. With 3 Gunicorn sync workers and a burst of, say, 10 concurrent users, what happens to the 7th user? Is there a queue? Does it 502? What is the real concurrency ceiling, and what should we do about it (more workers, gevent, async, queue)?
>
> 3. **SQLite contention.** `database.py` uses SQLite. Under concurrent writes (click tracking, catalog sync), what breaks? Is WAL mode enabled? What's the failure mode?
>
> 4. **Rate limiting race.** Per-IP rate limiting is shelve-backed. With 3 workers, can two concurrent requests from the same IP both pass the rate limit check before either writes the block? Walk through the exact race condition if it exists.
>
> 5. ~~**Railway ephemeral filesystem.**~~ **NOT APPLICABLE — Railway Pro with 50GB permanent volume. Data is not lost on redeploy or restart. Skip this audit item.**
>
> 6. **Catalog sync conflict.** `catalog_sync.py` is triggered nightly by an external cron hitting `/admin/sync-catalog`. If a user session is mid-pipeline when sync runs, is there a conflict? Can sync corrupt the session cache?
>
> For each issue: rate it (Critical / High / Medium), describe the exact failure mode, and recommend the minimal fix that doesn't require a full infrastructure migration. Where Railway Postgres or Redis would be the right answer, say so clearly and estimate migration effort.
>
> After the audit, implement the Critical and High fixes. Add `# SONNET-FLAG:` comments for anything you defer. Update CLAUDE.md with findings.

### [DONE] Replacement backfill relevance gate — post_curation_cleanup.py

**Fixed Feb 25 2026 (Opus).** Three-layer fix for the $800 scooter incident:

1. **Awin `_matches_query()` tightened** — now requires 2 meaningful term matches for queries with 3+ meaningful words. Short queries (1-2 terms like "hiking" or "Taylor Swift") still match on 1. (`awin_searcher.py`)
2. **Upstream price cap** (Sonnet, Feb 25) — `AWIN_MAX_PRICE_USD = 200` in `awin_searcher.py`.
3. **Price × interest-relevance gate** (Opus, Feb 25) — `_is_query_relevant_to_product()` now rejects replacements where price > `REPLACEMENT_PRICE_THRESHOLD` ($120) AND zero meaningful words from `interest_match` appear in the product title. SONNET-FLAG comment removed. (`post_curation_cleanup.py`)

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
- **Storage:** Railway Pro plan with a **50GB permanent volume** mounted on the service. SQLite DB, shelve files, and all local state persist across deploys and container restarts. **Do NOT suggest ephemeral filesystem as a cause of data loss — it is not ephemeral.**
- **Model env vars:** `CLAUDE_PROFILE_MODEL` (default Sonnet), `CLAUDE_CURATOR_MODEL` (default Sonnet, set to Opus to test quality)
- **Admin dashboard:** `/admin/stats?key=ADMIN_DASHBOARD_KEY`

**Testing locally:**
```bash
python giftwise_app.py
# http://localhost:5000/demo          — fake data
# http://localhost:5000/demo?admin=true — real pipeline with @chadahren
```

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

1. **Inventory must be good first.** Paywalling thin results is a conversion disaster. Wait until Awin/CJ/FlexOffers inventory is robust.
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

---

## What This Is

AI-powered gift recommendation engine. Users paste a social media handle → Flask scrapes their profile → Claude analyzes interests → searches multiple retailers → Claude curates gifts → programmatic cleanup → display with affiliate links.

Live at **giftwise.fit**. Revenue comes from affiliate commissions on product clicks.

## Non-Goals

Do not build, suggest, or scope-creep into:
- Mobile app (web-only)
- Nonprofit/charity fundraising features
- International currency support
- Automated social media posting
- Video content generation
- Campaign-specific promo code (Valentine's lesson — 884 lines deleted)
- Skimlinks integration (service is defunct)
- Spotify OAuth (removed — caused infinite waits/403s; text paste only now)
- Paywall enforcement (not until traffic thresholds are met — see `docs/BUSINESS_STRATEGY.md`)

## Pipeline

```
Social handle → Scrape (Instagram/TikTok)
  → Claude call #1: profile_analyzer.py (interests, ownership signals, aesthetic)
  → interest_ontology.py enrichment (zero cost, pre-LLM)
  → multi_retailer_searcher.py (Amazon, eBay, CJ, Awin, Etsy)
  → revenue_optimizer.py scoring
  → Claude call #2: gift_curator.py (14 candidates)
  → post_curation_cleanup.py (trim to 10, enforce diversity)
  → Display with affiliate links
```

Two Claude API calls per session. ~$0.10 on Sonnet, ~$0.25-0.50 on Opus.

## Key Files

| File | Purpose |
|------|---------|
| `giftwise_app.py` | Main Flask app, routes, orchestration |
| `recommendation_service.py` | Pipeline orchestrator (profile → search → curate) |
| `profile_analyzer.py` | Claude call #1: social data → structured profile |
| `gift_curator.py` | Claude call #2: profile + inventory → curated gifts |
| `post_curation_cleanup.py` | Programmatic diversity enforcement (brand, category, interest, source) |
| `interest_ontology.py` | Pre-LLM thematic enrichment (zero API cost) |
| `multi_retailer_searcher.py` | Orchestrates all retailer searches |
| `cj_searcher.py` | CJ Affiliate GraphQL + 15+ static partner lists |
| `awin_searcher.py` | Awin feed search + static partner lists |
| `smart_filters.py` | Work exclusion, passive/active, obsolete format filtering |
| `search_query_utils.py` | Query building, 5-word cap, category suffixes |
| `database.py` | SQLite product catalog, click tracking |
| `storage_service.py` | Shelve-backed key-value store |
| `site_stats.py` | Admin dashboard event counter |

## Three-Layer Intelligence Architecture

**Understand this before modifying any recommendation logic.**

| Layer | Files | Role | Cost |
|-------|-------|------|------|
| Pre-LLM code | `interest_ontology.py`, `enrichment_engine.py`, `revenue_optimizer.py`, `search_query_utils.py` | Enrichment, scoring, query building | Free |
| LLM prompts | `profile_analyzer.py`, `gift_curator.py` | Taste, judgment, reasoning | ~$0.10/session |
| Post-LLM code | `post_curation_cleanup.py`, `smart_filters.py` | Rules, guarantees, diversity enforcement | Free |

**Key balances:**
- **Prompts for taste, code for rules.** The curator prompt guides judgment. Code enforces guarantees (no duplicate brands in same category, max 2 per interest). Never flip this.
- **Ontology enriches, never filters.** It adds context to the curator prompt. It never removes products.
- **Brand dedup is relaxed intentionally.** Same brand CAN appear twice if categories differ (e.g., Taylor Swift poster + enamel pin).
- **Search queries capped at 5 words.** Prevents eBay 400 errors.
- **Ownership signals flow end-to-end.** Profile analyzer detects → profile dict carries → curator prompt shows → curator avoids duplicates.

## Opus-Only Zones

Files marked `⚠️ OPUS-ONLY ZONE` in code. Non-Opus sessions: add a `# SONNET-FLAG:` comment and move on.

| File | Protected Sections |
|------|--------------------|
| `interest_ontology.py` | Theme clustering thresholds, gift philosophy inference, curator_briefing format |
| `gift_curator.py` | Gift reasoning framework, selection principle, synthesis, ownership section |
| `profile_analyzer.py` | Ownership signals schema, aesthetic_summary, interest type taxonomy |
| `post_curation_cleanup.py` | Brand relaxation rules, uncategorized near-dedup, source diversity caps |

**Safe for any session:** Bug fixes, template/CSS, API response handling, adding new category/brand patterns, adding entries to INTEREST_ATTRIBUTES, logging.

## Development Rules

**Do:**
- Wire everything end-to-end. If you create a template, add the route. If you add a module, wire imports.
- Images resolved programmatically from inventory, never from curator LLM output.
- Products interleaved by source before curator sees them (no positional bias).
- Prioritize high-commission sources (CJ, Awin, eBay) over Amazon (1-4%).
- Curator gets 14 candidates, cleanup trims to 10.
- Check token budget before adding prompt instructions (~255 tokens = ~$0.0008). Don't add 500+ without trimming elsewhere.

**Don't:**
- Route structured data (URLs, images, prices) through LLM prompts — they corrupt it.
- Add "CRITICAL" to every prompt instruction.
- Hard-filter products before curation (kills diversity). Prefer soft prompt guidance + post-curation cleanup.
- Build features that only work for one retailer.
- Add code filters for taste problems. If curator makes bad judgment calls, fix the prompt.
- Build campaign-specific code.

## eBay Source Starvation Fix (Mar 19, 2026)

**Problem:** eBay dominated recommendation results (~60%+ of final recs), crowding out CJ and Awin advertisers. This was NOT just test profiles — it was structural.

**Root causes identified:**
1. **Database-first shortcut** (`multi_retailer_searcher.py:102`) skipped live API calls once the cache had enough products, regardless of source diversity. eBay floods the cache → Awin/CJ feeds never queried again.
2. **60% source cap** (`post_curation_cleanup.py:544`) allowed one source to fill 6/10 final slots.
3. **Awin matching is stricter than eBay** (by design, to avoid bad matches), so eBay returns more products per query and dominates the pool.

**Fixes applied:**
1. **Database diversity gate** — DB cache only skips live APIs if results have 3+ sources AND no single source > 50%. Otherwise, caps DB products per source to `per_vendor_target` and proceeds with live API calls to diversify.
2. **Source cap tightened** — `MAX_PER_SOURCE_PCT` lowered from 0.6 (60%) to 0.4 (40%). Max 4/10 from one source instead of 6/10.

**Files changed:** `multi_retailer_searcher.py`, `post_curation_cleanup.py`

**Monitor after deploy:** Check `Product source breakdown:` in logs to verify Awin/CJ products appear more often. If Awin matching is still too strict for certain interest profiles, consider relaxing the 2-term threshold in `awin_searcher.py:710`.

---

## Production Log Review (Mar 18-19, 2026)

**Overall health: Good.** Startup clean, catalog sync completing daily (~2 min), recommendation pipeline working end-to-end. A real user session successfully generated 13 recommendations with 76% real image rate.

**Observations:**
- **Etsy API returns 403 Forbidden** on all search queries. Known/expected — Etsy has rejected dev credentials multiple times. Etsy searches are wasted API calls until credentials are approved.
- **Duplicate in-flight Claude API calls** — two concurrent profile analysis requests for the same profile hash (`3c6142ae`) because the caching layer doesn't prevent in-flight duplicates. Not critical at current volume, but will waste API spend under load. Consider adding an in-flight lock (e.g., a dict of pending profile hashes) so the second request waits for the first to finish and uses its cached result.
- **Railway severity mislabeling** — Gunicorn logs to stderr, so Railway tags all INFO-level logs as "error" severity in the dashboard. This is cosmetic; filter by message content, not severity badge.
- **405 Method Not Allowed** (one-off, Mar 17) — likely a bot or misconfigured client hitting a route with wrong HTTP method. No action needed unless it recurs.
- **Stripe not configured** — expected at current stage (paywall not enforced).
- **Catalog sync healthy** — CJ: ~3,995 products across 40 search terms. Awin: ~7,743 products across 26 joined feeds.
- **Claude model in use:** `claude-sonnet-4-20250514` for both profile analysis and curation.

---

## Current Priorities (Updated Mar 2026)

1. **Guide → tool conversion funnel** — Guides get significantly more traffic than the main tool (guide_hit >> rec_run in admin stats). Fix the funnel: add above-fold and mid-page CTAs, fix the 3 incomplete Etsy guides, add CTA to blog index. See "Content & SEO: Guide/Blog Strategy" section below.
2. **TikTok launch content** — "The Birthday" reel in progress (Midjourney + CapCut). Frames 4-5 done, Frames 1-3 (character emoting) still need generation. See "TikTok Reel Production" section below.
3. **Awin approvals** — ~35 applications from Feb 25 pending. Check dashboard for new approvals.
4. **FlexOffers** — Applied Feb 16, status unknown. Check dashboard.
5. **Impact.com** — Account type issue, second ticket filed. STAT tag + verification phrase on branch `claude/review-claude-docs-kEdui` (merge to main to activate).
6. **Load test & harden** — Shelve concurrency, Gunicorn worker exhaustion, SQLite write contention under concurrent load. See Opus prompt in `docs/ARCHITECTURE.md`.
7. **Monitor quality** — Admin dashboard, watch rec_run and affiliate click events.

---

## Content & SEO: Guide/Blog Strategy

**Key insight (Mar 2026):** Admin dashboard shows `guide_hit` significantly outpacing `rec_run`. Users land on guides via search but don't convert to the main tool. This is the highest-leverage growth fix available.

### Current CTA Problems

| Issue | Details |
|-------|---------|
| **Bottom-only CTAs** | All guide/blog CTAs are at the very end of the page. Users who bounce mid-read never see them. |
| **3 Etsy guides incomplete** | `guide_etsy_home_decor.html`, `guide_etsy_jewelry.html`, `guide_etsy_under_50.html` have placeholder content (`[Add product image URL]`, `[ETSY AFFILIATE LINK]`) and NO CTA to the main tool. |
| **Blog index has no CTA** | `/blog` page is pure navigation — no mention of the tool at all. |
| **All CTAs → /signup** | No option to go directly to `/demo` for a frictionless try. Users must create an account first. |
| **No per-guide tracking** | All guides and blog posts aggregate into one `guide_hit` counter. Can't see which guide drives traffic. |

### What to Fix (in priority order)

1. **Add above-fold CTA** to every guide — a subtle banner or inline callout near the top: "Want gifts personalized to a specific person? Try GiftWise free →" linking to `/demo` (not `/signup`).
2. **Add mid-page CTA** after 3-4 product recommendations in each guide — contextual, like "These are great general picks. For gifts matched to *their* actual interests, try GiftWise →"
3. **Fix or remove the 3 incomplete Etsy guides** — they're live pages with broken placeholder content. Either populate them or take them down.
4. **Add CTA to blog index** (`/blog`) and guide index (`/guides`) — both need a prominent tool callout.
5. **Add per-slug tracking** — change `track_event('guide_hit')` to `track_event('guide_hit:beauty')` (or add a second event) so you can see which content drives traffic.
6. **Add `guide_to_tool` funnel event** — track when someone navigates from a guide/blog to the main tool entry point.

### Keeping Guides Fresh

Current guides are static HTML with hardcoded products. They'll go stale. Options:
- **Manual refresh (quarterly):** Review each guide, swap out discontinued/seasonal products, update affiliate links. Low effort, low frequency.
- **Semi-automated:** Build a script that queries the same retailer APIs (CJ, Awin, eBay) for each guide's category and outputs updated product cards. Human reviews and pastes into template.
- **Dynamic guide sections:** Replace some hardcoded products with a server-side call that pulls top-rated products from the catalog DB for that category. Keep editorial intro/outro static.

Start with manual refresh — the 3 Etsy guides need it immediately since they're broken. Consider semi-automated once there are 15+ guides.

---

## TikTok Reel Production

### Video 3: "The Birthday" (In Progress — Mar 2026)

**Concept:** 5-frame Midjourney sequence + end card in Canva, assembled in CapCut. Story: woman panics about birthday gift → bad ideas → discovers GiftWise → sees results → group chat celebration.

**Style:** Photorealistic for phone-screen frames (4-5), editorial illustration (Anna Bond / Rifle Paper Co style) for character frames (1-3). Palette: cream, sage green, dusty coral, dark navy.

**Frame status:**

| Frame | Shot | Status | Notes |
|-------|------|--------|-------|
| 1 | Group chat panic — woman slumped on couch, phone glow | Not started | This is the `--sref` source image. Use `--no anime, cartoon, manga, 3d render, photorealistic, big eyes, exaggerated features, chibi, pixar`. Name "Anna Bond for Rifle Paper Co" for stronger style anchor. |
| 2 | Drowning in bad ideas — hunched forward, hand on forehead | Not started | Use `--sref IMAGE_URL` (not `--cref`; v7 doesn't support `--cw`). Completely different body position from F1. Crossed-out generic gifts (candle, gift card, socks) floating above. |
| 3 | Lightbulb moment — sitting upright on edge of couch, big smile | Not started | Brightest frame. "Eyebrows raised high and mouth open in a surprised smile." Room feels brighter than F1-F2. |
| 4 | Results screen — close-up hands holding phone | Done | Photorealistic. Went with "extreme close-up" approach — phone fills frame, sage sweater cuff at wrist, scrollable gift cards with coral heart icons. |
| 5 | Group chat payoff — macro close-up of phone chat | Done | Photorealistic. "Macro close-up, phone filling 90% of frame." Chat bubbles in coral pink and soft blue, celebration emojis, confetti bursting from screen. |
| 6 | End card | Not started | Make in Canva: cream #FFF8F0 bg, "GiftWise" in Playfair Display Bold navy, tagline in Montserrat, "giftwise.fit", coral gift box icon. |

**Key Midjourney lessons learned:**
- `--cref` with `--cw 100` locks face too tight — no emotional range. Use `--sref` (style reference) instead in v7, which keeps palette/linework but allows expression changes.
- Adjective-only emotion changes ("stressed" vs "curious") are too subtle. Use **dramatic body position changes** (slumped → hunched → upright) and **lighting/mood shifts** (dim → defeat → bright).
- Midjourney goes anime/cartoon easily. Counter with: "Anna Bond for Rifle Paper Co" (name the artist), "gouache texture, flat color, visible brushstrokes", long `--no` list, `--stylize 200` or lower.
- Phone-screen frames work better photorealistic — it reads as "real app" which sells the product. Mixing styles across frames is fine since each is on screen 1-2 seconds in CapCut.
- Don't use product names on screen (Midjourney can't render readable text). Use "horizontal lines representing text" and visual shapes (rounded cards, thumbnails, heart icons).

**Next steps:** Generate Frames 1-3 character illustrations. Frame 1 is the anchor — get her face/style right, then use that as `--sref` for 2-3. Frame 6 end card is quick Canva work. Then assemble all 6 in CapCut with transitions and audio.

---

## Retailer Status

| Retailer | Status |
|----------|--------|
| Amazon (RapidAPI) | Active |
| eBay (Browse API + EPN) | Active |
| CJ Affiliate (GraphQL + 15 static partners) | Active |
| Awin (13 confirmed merchants, ~35 pending) | Active, expanding |
| Etsy (v3 API) | Blocked — dev credentials rejected multiple times, API returns 403 on all queries |
| Skimlinks | DEFUNCT — dead code, remove when convenient |
| Impact.com | Blocked — account type issue |
| FlexOffers | Applied, status unknown |
| Rakuten | Account active, need to apply to brands |

For detailed affiliate partner lists, commissions, and application status, see `docs/AFFILIATE_STATUS.md`.

## Reference Docs

Don't load these every session. Read only when the task requires it.

| Doc | When to read |
|-----|-------------|
| `docs/AFFILIATE_STATUS.md` | Working on affiliate integrations, adding partners |
| `docs/ARCHITECTURE.md` | Deep technical work, load testing, the Opus audit prompt |
| `docs/TESTING.md` | Running tests, pre-deploy verification |
| `docs/BUSINESS_STRATEGY.md` | Paywall decisions, revenue model, subscription tiers |
| `docs/OPUS_AUDIT.md` | Quality review, checking audit item status |
| `docs/AFFILIATE_APPLICATIONS_TRACKER.md` | Checking application status across all networks |
| `docs/AWIN_APPLICATIONS_FEB25.md` | Awin application details, tiers, EPC, what to do when approvals arrive |
| `docs/AFFILIATE_NETWORK_RESEARCH.md` | Brand-to-network mapping (~70 brands) |
| `docs/RAILWAY_DEBUG_GUIDE.md` | Railway deployment debugging |

62 older session artifacts (handoffs, setup guides, session summaries) are in `docs/archive/`. These are historical — don't load them unless investigating how a past decision was made.
