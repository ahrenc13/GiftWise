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

## Fix Verification Protocol (Required for Every Code Change)

**Claude's failure mode:** Confidently pattern-matching symptoms to plausible causes and presenting fixes that either don't work or create downstream regressions. This protocol is mandatory for every bug fix and every feature change. No exceptions.

**1. Prove the bug before fixing it.**
Show the exact line where the problem occurs. Trace real data through it: "This input → this function → this output, and here's why that's wrong." If you can't show the specific broken path with real values, you're guessing. Say so.

**2. Write a test case (or trace) that reproduces the failure.**
Before writing fix code, demonstrate the failure. For pipeline code: show what a real query/product/profile produces through the broken path. For UI code: describe the exact reproduction steps. If you can't reproduce it, you don't understand it yet.

**3. One fix per commit, tested individually.**
Don't bundle 3 fixes into one change. Fix one issue, verify it works, commit. If the second fix breaks something, you know exactly where. This also prevents the "I fixed 3 things and 2 of them were wrong" pattern.

**4. Answer "what could this break?" before committing.**
For every changed function, list its callers and downstream consumers. Trace the impact: "This function is called by X and Y. X will now get [different behavior]. Y depends on [this property] which is preserved." If you can't list the callers, read the code until you can.

**5. Dry-run with real data when possible.**
For pipeline code, the most valuable check is running the pipeline and comparing before/after. Log diffs beat code review. When you can't run the pipeline, simulate with concrete examples: "For msmollygmartin's interest 'fly fishing', the old code produces [X], the new code produces [Y]."

**6. Flag uncertainty honestly.**
If a fix is speculative, say "I believe this is the cause but I'm not certain because [reason]." Never use "root cause" unless you've completed steps 1-2. "Plausible cause" is fine. Confident language should be reserved for verified fixes.

**7. After deploying, verify the fix worked.**
Check logs, run the flow, confirm the symptom is gone. A fix isn't done until it's verified in the environment where the bug was observed.

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

### [PARTIAL] Catalog-First Architecture: Interest Inventory Expansion & Source Separation

**Phase 1 DONE (Mar 21, 2026 — Opus):** Term expansion and CJ multi-label tagging.

- **Sync terms expanded 252 → 589** across 19 categories (was 12). Added: music_genres, spirituality_astrology, travel_adventure, reading_literature, sustainability_lifestyle, dance_performance, specific_artists_brands. Priority 1 (nightly): 366 terms. Priority 2 (weekly full): 223 terms. Refresh subset: 56 terms.
- **CJ multi-label tagging implemented.** CJ products now tagged with ALL matching catalog terms via `_tag_awin_product_with_interests()`, matching Awin's existing behavior. Previously CJ products got only the single search term that found them.
- **CJ upsert merges tags on conflict.** Previously `interest_tags` was not updated on conflict — new tags were silently dropped. Now reads existing tags and merges (union, new-first order).
- **Coverage gaps addressed:** Added terms for Broadway/Hamilton, Jim Henson/Muppets, specific music artists (Stevie Nicks, Fleetwood Mac, Beatles, etc.), retro/nostalgia, Formula 1, D&D/tabletop RPG, astrology/tarot, dance, sustainability, reading accessories — all gaps observed in real user sessions.

**Phase 2 REMAINING — Source Separation (safe for Sonnet):**

These tasks enforce the catalog-first / live-fallback split. Phase 1 (term expansion + CJ multi-label tagging) is done; the DB should now have much richer coverage after a full sync. These are code-level pipeline changes — no prompt or ontology modifications needed.

**Task 1: Remove live CJ API calls from session-time code** (`multi_retailer_searcher.py`, `cj_searcher.py`)
- CJ products should come from the DB only (via `search_products_by_interests`). The nightly sync populates 589 terms × 100 products each. Live CJ GraphQL calls during sessions are redundant and slow (~1.5s per term, sequential).
- Remove `_run_cj` from the parallel retailer tasks in `multi_retailer_searcher.py`. Keep the CJ static partner logic (MonthlyClubs, Winebasket, etc.) — those are cheap and additive.
- **Do NOT delete `cj_searcher.py`** — it's still used by `catalog_sync.py` for sync.

**Task 2: Remove live Awin feed download from session-time code** (`awin_searcher.py`)
- The cache-first path (line ~732) already skips the live download when the DB has ≥ 50% of target_count. Make this the ONLY path — remove the live CSV download fallback entirely. Static Awin partners (from `_get_awin_static_products`) should still run.
- **Do NOT remove or weaken the Awin `_matches_query()` 2-term threshold** (prevents the $800 scooter problem).

**Task 3: Wire eBay niche-only scoping** (`multi_retailer_searcher.py`)
- Use `per_interest_counts` from `search_products_diverse()` to identify interests with < 3 DB products.
- Run eBay ONLY for those 2-3 weak-coverage interests, not for all profile interests.
- Cap eBay contribution at ~5-8 items.
- eBay and Amazon remain live-only (no DB write-back — already enforced).

**Task 4: Improve DB query scoring** (`database.py`)
- `search_products_by_interests()` uses simple LIKE matching on `interest_tags`. With richer multi-label tags, score by number of matching interests, prefer higher `gift_score`, ensure source diversity in results.
- Consider using `search_products_diverse()` (already built, has form-diverse windowing) as the primary session-time query.

**Task 5: Retune source diversity cap** (`post_curation_cleanup.py`)
- With CJ/Awin as catalog-only and eBay/Amazon as live-only, `MAX_PER_SOURCE_PCT` (currently 0.4) may need separate caps: max 30% from any single retailer, but catalog sources (CJ+Awin combined) can be up to 60%.
- Preserve interleaving: products from DB and live APIs must be interleaved by source before the curator sees them.

**Constraints for all Phase 2 tasks:**
- Do NOT touch the curator prompt (`gift_curator.py`) or profile analyzer (`profile_analyzer.py`) — those are Opus zones.
- Do NOT remove or weaken the Awin `_matches_query()` 2-term threshold.
- Nightly refresh (56 terms) must stay fast (~3 min). Full sync (~589 terms) can run ~1 hour weekly.

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

**Current status (Apr 2026): Paywall is NOT enforced. All users get full free access. Focus is on catalog depth and rec quality before adding any friction.**

### The Economics

- Claude API cost per session: ~$0.10 (Sonnet, both profile + curator calls)
- Affiliate revenue per session: ~$0.00–$0.05 (most visitors don't buy; commissions only on purchases)
- Railway hosting: ~$5–20/month (fixed, doesn't scale with sessions)

**Implication:** Every session is subsidized. That's intentional at this stage — but affiliate revenue alone may never cover costs if users are treating recs as ideas and not clicking through. Subscription/per-use fees are the more reliable path to covering API costs. See Future Revenue Models section.

### The Free Tier Design (When Ready to Implement)

**1 run per week free, not 1 per day.** One per day is too easy to game — users just come back tomorrow and stay free indefinitely. One per week creates real scarcity without feeling punitive for the core use case (shopping for one person).

**Progressive degradation, not a hard wall.** Showing people what they're missing converts better than blocking them entirely. The curve:

| Run # (within 7-day window) | What they see |
|---|---|
| **Run 1** | Full output — all picks, all links, fully clickable. This is the "wow" moment. Don't compromise it. |
| **Run 2** | 3 picks shown and clickable. Remaining tiles visible but fuzzed — product shape visible, details obscured. |
| **Run 3+** | All tiles fuzzed. Oblique copy describing the kinds of things they'd see ("a subscription that fits how they actually spend their weekends", "something under $60 they'd never buy themselves"). Upgrade CTA. |

**Why this works better than a hard cutoff:** Run 1 earns trust. Run 2 creates desire — they can see there's more and they want it. Run 3+ creates pressure — they know exactly what they're giving up. A hard wall at run 2 skips the desire phase entirely.

**Do not implement until:**
1. Rec quality is consistently strong — paywalling mediocre output is a conversion disaster
2. The $2.99 gift emergency one-time fee is live and tested (this is the proof that anyone will pay at all)
3. Traffic is above 5 sessions/day sustained — below that, friction costs more in word-of-mouth than it earns

### Paywall Trigger Thresholds

| Threshold | Meaning | Action |
|-----------|---------|--------|
| **< 5 sessions/day avg** | Growth phase — API cost ~$15/mo, negligible | Keep fully free. Do not restrict anything. |
| **5–15 sessions/day** | Early traction | Test $2.99 gift emergency. Watch conversion rate. |
| **15–30 sessions/day sustained** | Real traffic | Implement 1-run/week free tier with progressive degradation. |
| **30+ sessions/day AND affiliate revenue not catching up** | Paywall decision point | Soft paywall: require free account (just email) to get first run. |
| **Paying users exist** | Only then | Full subscription tiers with Stripe. |

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

1. **Rec quality first.** Paywalling thin or inconsistent results is a conversion disaster. This is the current priority.
2. **TikTok moment:** If the kid posts and traffic spikes, do NOT paywall during that window. Let people run it free, collect emails, build the waitlist. Monetize the warm audience later.
3. **Test willingness to pay cheaply first:** The $2.99 gift emergency (already in code, not yet wired) is the canary. If people won't pay $2.99 for a second run, the subscription model needs rethinking.
4. **1-run/week is the free tier, not 1/day.** Document this clearly before implementation so it doesn't get built wrong.

### What the Subscription Tiers Are (Not Yet Enforced)

The code has tier infrastructure built (see `giftwise_app.py` lines ~634+). Planned tiers:
- **Free:** 1 full run per week, progressive degradation on subsequent runs
- **Pro ($4.99–$7.99/month):** Multiple profiles, monthly refresh, shareable profile links
- **Gift Emergency ($2.99 one-time):** Bypass the weekly limit, no account needed — impulse buyer capture

These are NOT enforced yet. The Stripe integration (`/subscribe` route) exists but isn't wired to gatekeeping. Do not wire the paywall until quality and traffic thresholds above are met.

### North Star: Why Subscription Beats Affiliate Long-Term

Affiliate revenue depends on brand recognition in the catalog — if users treat recs as ideas and don't click through, every session is a net loss. Subscription/per-use fees generate revenue based on service quality regardless of whether MonthlyClubs or Sephora is in the catalog. The chicken-and-egg problem with premium brands (need traffic to get Yeti/Sephora approval, need Yeti/Sephora to drive conversions) doesn't affect subscription revenue at all.

Flip priority from affiliate to subscription when: API costs are consistently exceeding affiliate revenue, OR when 20+ paying users validate willingness to pay.

---

## Future Revenue Models (Do Not Build Yet)

These require a stronger catalog, proven recommendation quality, and real traffic before they're worth building. Document them here so they don't get lost.

**Prerequisites for both:**
- Consistent recommendation quality across a range of profile types (not just social-media-heavy users)
- Catalog deep enough that monthly re-runs surface genuinely different picks
- Paying users on the core product first — validate willingness to pay before building new surfaces

---

### Model 1: GiftWise for [Name] — Recurring Gift Intelligence

**What it is:** A subscription where you sign up on behalf of specific people you buy for. Every month (or quarter), GiftWise rescans their current social footprint and delivers a "here's what [Sarah] is into right now" email to you. 3–5 picks from catalog, fresh to this month's signals. You decide whether to buy any of them. We earn affiliate commission on clicks regardless.

**The core insight:** The rec engine already does this on demand. The subscription is the same pipeline on a schedule, with a presentation layer that justifies a recurring fee. You're not paying for the list — you're paying to not have to remember to do this, and to get caught before the occasion rather than the morning of.

**Revenue stack:** Subscription fee (~$4.99–$9.99/month) covers API cost and then some. Affiliate commission on clicks is upside on top of that. A subscriber tracking 3 people generates $15–30/month before any purchases.

**What it requires to build:**
- Scheduled re-analysis (run pipeline on the Nth of each month per subscriber)
- Profile memory so the same picks don't recur month after month
- Email delivery of curated output (SendGrid/Mailgun, ~$15/month fixed)
- Stripe subscription billing (already partially wired)
- "Manage my people" dashboard — add profiles, set occasions, set budget

**Hard problems:**
- Instagram scraping reliability: a paid service can't fail silently. Needs graceful degradation ("we couldn't reach Sarah's profile this month, here's what we found last month").
- Privacy framing matters more when it's recurring. "Stay thoughtful automatically" lands right. Anything that sounds like surveillance doesn't.
- Profile freshness: if someone's account goes private or changes handles, the service breaks for that slot.

**When to build:** After the first 20–30 paying users on the core product validate that people will pay for personalization. Not before.

---

### Model 2: B2B — Corporate and Concierge Gifting

**What it is:** The same rec engine sold as a service to businesses that gift at scale — HR departments buying employee gifts, sales teams gifting clients, executive assistants managing multiple relationships. The current corporate gifting market is almost entirely generic (Visa gift cards, branded swag, wine). GiftWise's value prop: scan the recipient's LinkedIn or social and send something that actually fits who they are.

**Three entry points:**

1. **Corporate gifting dashboard** — A company uploads a list of employees or clients (names + LinkedIn/social handles), sets a budget, and GiftWise generates a personalized gift list for each one. HR reviews and approves. Purchases go through existing affiliate links or a bulk order process.
   - Revenue: per-recipient fee ($5–15/recipient) + affiliate commission on purchases
   - Volume pricing for large companies

2. **Concierge/EA tool** — Personal assistants who manage gifting for executives already spend hours on this. GiftWise is a force multiplier. Pitch: "your client's LinkedIn tells us more than a generic gift catalog does."
   - Revenue: monthly SaaS fee per seat (~$49–99/month)

3. **White-label API** — A retailer (Nordstrom, Etsy, etc.) licenses the rec engine to power their own "find the perfect gift" feature. They bring the catalog; we bring the personalization intelligence.
   - Revenue: API licensing fee, negotiated per deal
   - Highest ceiling, longest sales cycle

**What makes B2B viable:**
- The consent/privacy issue flips: companies legitimately collect employee/client social data as part of their CRM. Processing it for gifting is within normal business relationship scope.
- The willingness-to-pay is already proven in corporate gifting — companies spend $258/employee/year on average. Getting 10% of that budget routed through a smarter tool is a real pitch.
- Sales cycle is longer than consumer, but contract sizes are much larger.

**Hard problems:**
- Sales motion is completely different from consumer. Requires outbound, demos, procurement approval cycles.
- Data privacy compliance (GDPR, CCPA) becomes a real concern when processing employee data at company request.
- Quality bar is higher — a bad recommendation to a corporate client damages a relationship the company cares about.

**When to build:** After the consumer product has demonstrated recommendation quality consistently. The B2B pitch depends entirely on "our recs are good" — if you can't prove that with consumer users first, the enterprise sale doesn't close.

---

### Relationship Between the Three Models

| Model | Who pays | Why they pay | Catalog dependency |
|-------|----------|-------------|-------------------|
| Affiliate (current) | Nobody directly — paid by vendors | Discovery + trust | Medium |
| Subscription (Model 1) | Gift-givers | Automation + recurring relevance | High — needs fresh picks monthly |
| B2B (Model 2) | Companies | Scale + personalization at volume | High — needs broad category coverage |

The affiliate model funds the catalog and quality work. Model 1 is the natural first expansion — same audience, same pipeline, just recurring. Model 2 is the larger bet that requires a proven track record first.

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

## Pre-LLM Signal Extraction Improvements (Mar 22, 2026)

**Four new structured signal types added to the profile analyzer data summary.**

The common insight: we were sending Claude raw text (captions, hashtags, tagged accounts) and asking it to infer things that the metadata already tells us directly. Timestamps, engagement ratios, music tracks, brand tags — these are structured signals that should be extracted in code (pre-LLM layer) and handed to Claude as facts.

### 1. Temporal Signals (Recency Weighting)
**Problem:** All posts weighted equally regardless of when posted. A hiking post from 8 months ago carried the same weight as a cooking post from yesterday.
**Fix:** `_extract_temporal_signals()` parses post timestamps and identifies momentum topics (rising in last 30 days) and fading topics (present in older posts but absent recently). Added for both Instagram and TikTok. Prompt tells Claude to prioritize rising interests.

### 2. Engagement Spike Detection
**Problem:** Engagement metrics used only for ranking which posts to send to Claude. Posts with 10x normal engagement (core identity content) treated the same as average posts.
**Fix:** `_extract_engagement_spikes()` identifies posts with 3x+ the account's average engagement. Labeled as "high-resonance" in the data summary. Both Instagram and TikTok.

### 3. TikTok Music Artist Extraction (Pre-LLM)
**Problem:** `top_music` only had track names, not artist names. Claude had to infer artist interests from track names.
**Fix:** Added `top_music_artists` counter to `parse_tiktok_data()`. `_extract_music_artists()` filters out "original sound" and requires 2+ uses. Passed to Claude as confirmed interests.

### 4. Instagram Brand-Tag Extraction
**Problem:** Tagged accounts passed as a flat list mixing brands and friends. Brand tags (@nike, @glossier) are much stronger ownership signals than friend tags.
**Fix:** `_classify_tagged_accounts()` separates likely-brand vs likely-personal using conservative heuristics (dots in name, brand suffixes, single-word handles). Brands get a prominent "BRAND AFFINITIES" section.

**Token cost:** ~130-240 extra input tokens per session (~$0.001). Negligible.
**Files changed:** `profile_analyzer.py`, `giftwise_app.py`
**Cache invalidation:** `_PROMPT_VERSION` bumped to `"2026-03-22-signals-v3"`

---

## End-to-End Quality Audit (Mar 22, 2026)

**Symptom:** Gift lists for msmollygmartin were nonsensical — camping chairs, weighted blankets, Christmas pullovers, cat toys. Fly fishing (brother's hobby) dominated the top-scored products. Results felt random despite multiple scoring fixes.

**Root causes found (three systemic issues, not just scoring):**

### 1. `search_products_diverse()` was never wired in
The form-diverse DB query (ROW_NUMBER OVER PARTITION BY category, max 4 per form, ordered by gift_score DESC) was implemented in `database.py` but **never called**. The pipeline still used `search_products_by_interests()` which returns products ordered by popularity with NO form diversity. Result: 15 candles, 12 mugs, whatever was popular — not what matched the profile.
**Fix:** Switched `multi_retailer_searcher.py` to call `search_products_diverse()`. Now enforces max 4 products per form, orders by gift_score, separates splurge candidates ($200-$1500).

### 2. DB query keyword matching was too loose
`_build_interest_conditions()` generated separate OR conditions for each keyword. "fly fishing" → `tags LIKE '%fly%' OR tags LIKE '%fishing%' OR title LIKE '%fly%' OR title LIKE '%fishing%'`. A product with "Zipper Fly" in its title matched the "fly" condition alone.
**Fix:** Multi-keyword interests now require ALL keywords to match together: `(tags LIKE '%fly%' AND tags LIKE '%fishing%')`. Single-keyword interests unchanged. This prevents "Zipper Fly" from matching "fly fishing".

### 3. Third-party interests leaked through confidence filter
Profile analyzer was told to skip low-confidence interests (fly fishing = brother's hobby). But Sonnet sometimes assigned medium confidence instead of low. The code filter only caught `confidence == 'low'`.
**Fix:** Added `_is_third_party_interest()` in `giftwise_app.py` that checks the interest's evidence text for third-person markers ("brother", "sister", "dad", "his hobby", etc.). Catches interests that Sonnet mislabeled as medium confidence.

**Files changed:** `multi_retailer_searcher.py`, `database.py`, `giftwise_app.py`, `revenue_optimizer.py`, `recommendation_service.py`, `models.py`

---

## Pre-Filter Scoring Fix (Mar 22, 2026)

**Symptom:** `Pre-filtered to 30 products by relevance score (range 0.14–0.16)`. Even after rebalancing weights, range only widened to 0.06–0.16. TOP 5 products were random junk (plant stand, medal hanger, star pillow) matching `partial[community tv show:1/2]` — the word "show" appeared in unrelated product descriptions.

**Root causes (three layers):**
1. **`to_curator_format()` stripped critical fields** (models.py) — `Product.from_db_row()` correctly reads `gift_score`, `interest_tags`, `product_id`, `brand`, `category` from DB. But `to_curator_format()` only returned title, link, snippet, image, source_domain, price. The pre-filter scorer got products with NO gift_score (Factor 1 = 0), NO interest_tags (Factor 2 could only match on title text), NO product_id (no intel lookup possible). **This was the primary cause.**
2. **`matched_interest` flag shared across loop** — once any interest matched, all subsequent interests skipped keyword matching. Only the first matching interest contributed to the score.
3. **`_interest_to_keywords()` produced generic words** — "community tv show" → ["community", "show"] ("tv" is 2 chars, filtered). The word "show" matched hundreds of product titles/descriptions. Combined with missing interest_tags, the scorer could only match on title text, where generic words cause massive false positives.

**Fixes:**
- **`to_curator_format()`** (models.py) now includes `gift_score`, `interest_tags`, `product_id`, `brand`, `category`, `retailer`. Product dataclass has new `gift_score` field, `from_db_row()` reads it.
- **Factor 2 accumulates across ALL interests** (removed shared flag, per-interest `this_interest_matched`).
- **Partial match threshold raised**: single keyword match from a 1-2 keyword interest now scores only 0.02 (was 0.04) and does NOT count toward multi-interest bonus.
- **`_interest_to_keywords()` GENERIC list expanded** (database.py): added "show", "style", "culture", "activities", "life", "home", "care", "world", "day" and other words that match too many product titles.
- Multi-interest bonus: +0.15 for 3+ matching interests, +0.08 for 2.
- Factor 1 weight: 0.3 → 0.2. Factor 3 (commission): `rate * 4` → `rate * 2`.
- Top 5 and bottom 5 scored products logged in production.

**Expected result:** With interest_tags now visible to the scorer, a product tagged with "80s music" will full-match that interest. A random plant stand with "show" in its title will barely score. Score range should widen significantly.

**Fly fishing in experiences:** The curator generated "West Virginia Fly Fishing Photography Workshop" by synthesizing "west virginia outdoor activities" + photography interests — not from a fly fishing interest (which was correctly filtered as low-confidence). This is a curator judgment issue in the Opus-only zone. Potential fix: pass excluded interests to the curator prompt so it avoids re-inventing them.

---

## Post-Deploy Quality Audit (Mar 21, 2026)

**Four bugs fixed from first live session after DB query fix (msmollygmartin @msmollygmartin):**

The DB query fix landed and returned 80 products from 80k cached, 16 sources. But the session exposed four quality issues:

### 1. Relevance Pre-Filter Uniform Scoring (all products scored 0.14)
**Symptom:** `Pre-filtered to 30 products by relevance score (range 0.14–0.14)`. Every product scored identically — curator got random inventory.
**Root cause:** `revenue_optimizer.py` `score_product_for_profile()` relied on `get_product_intelligence()` for gift quality scoring (30% weight). No intelligence exists for synced products — they come through `catalog_sync.py`, not the intelligence tables. Meanwhile, `gift_score` (0.0-1.0) was pre-computed at sync time and stored on every product row, but the scorer never read it. Interest matching (30% weight) used exact substring matching: `"pop culture" in product_title` — which never matches product titles like "Batman Batmobile Model Kit".
**Fix:** Factor 1 now reads `product.get('gift_score')` directly (available on all DB products). Factor 2 now uses keyword extraction via `database._interest_to_keywords()` — same approach as the DB query fix — so `"pop culture"` matches products containing "pop" or "culture" in title/tags. Partial matches score proportionally.

### 2. Materials Backfill Accepting Nonsensical Matches (score=0)
**Symptom:** `"Waterproof phone case" → "Philips True Wireless Sports Headphones" (score=0)`. Materials matched to completely unrelated products.
**Root cause:** Two bugs: (a) Stopword asymmetry — `_CONTEXT_WORDS` (containing "waterproof", "case", "portable", "bag") was stripped from product titles via `_STOPWORDS` but preserved in material names via `_MATERIAL_STOPWORDS`. The word overlap could never match on exactly the words that matter most. (b) DB fallback via `search_products_by_title()` accepted the first result without any quality check — `best_score` stayed 0.
**Fix:** (a) Title words in the overlap scorer now use `_MATERIAL_STOPWORDS` instead of `_STOPWORDS`, so context words like "waterproof" and "case" participate in matching on both sides. (b) DB fallback now scores matches using the same word overlap logic and requires `score >= 2` before accepting. Min overlap threshold raised from 35% to 50%.

### 3. Fly Fishing Interest Persisted Despite Attribution Fix
**Symptom:** `Deferred (3rd+ for interest 'fly fishing')` — msmollygmartin's brother's hobby still in profile.
**Root cause:** Two issues: (a) Profile cache hash was based only on scraped data + relationship. Adding interest attribution instructions to the prompt didn't change the hash, so the old cached profile (from before the fix) kept being served. (b) `multi_retailer_searcher.py` didn't filter interests by confidence level — it took ALL interest names regardless of the `"confidence": "low"` the analyzer assigned.
**Fix:** (a) Profile cache hash now includes `_PROMPT_VERSION` — bump this string whenever the analyzer prompt changes materially. Old caches auto-invalidate. (b) `multi_retailer_searcher.py` now skips interests with `confidence == "low"` before passing to the DB query. This is code-level enforcement that doesn't depend on the LLM following prompt instructions perfectly.

### 4. TikTok Shop Source Concentration (44% of DB results)
**Symptom:** `top source 'TikTok Shop US - Marketplaces' at 44%`. One CJ advertiser dominated.
**Root cause:** TikTok Shop products ARE legitimate CJ affiliate products (advertiser ID 7563286) — they earn commissions. But a single marketplace advertiser shouldn't dominate 44% of results. The diversity gate used `MAX_SINGLE_SOURCE_PCT = 0.50`, so 44% passed. The per-source capping (via `per_vendor_target`) only ran when diversity *failed*.
**Fix:** Per-source capping now runs unconditionally before the diversity check. Each source capped at min(`per_vendor_target`, 30% of target). `MAX_SINGLE_SOURCE_PCT` tightened from 50% to 40%. This ensures no single CJ advertiser, Awin merchant, or marketplace dominates the pool.

**Files changed:** `revenue_optimizer.py`, `giftwise_app.py`, `profile_analyzer.py`, `multi_retailer_searcher.py`

---

## Gift Selection Quality Fixes (Mar 21, 2026)

**Three bugs fixed from production log review of msmollygmartin and lstratz sessions:**

### 1. Replacement Diversity Bug — 4 Necklaces in lstratz Results
**Symptom:** lstratz got ~4 similar basketball pendant necklaces in final recommendations.
**Root cause:** `post_curation_cleanup.py` replacement loop (line ~782) re-checked URL and title dedup when adding replacements from the pool, but did NOT re-check category or brand diversity. The candidate list was built before any replacements were added, so `used_categories` grew stale.
**Fix:** Added `if category and category in used_categories: continue` and `if brand and brand in used_brands: continue` in the replacement-adding loop, after line 794.

### 2. `per_vendor_target` Unbound Variable
**Symptom:** `multi_retailer_searcher.py` logged `cannot access local variable 'per_vendor_target' where it is not associated with a value` during the msmollygmartin session. The DB diversity gate code that caps per-source products was completely broken.
**Root cause:** `per_vendor_target` was defined at line 150 (after the try/except) but referenced at line 128 (inside the try block). When the DB had products but insufficient diversity, the cap code crashed and fell through to the except handler, proceeding with all live APIs unnecessarily.
**Fix:** Moved `per_vendor_target` definition before the DB query block.

### 3. Interest Attribution — Brother's Fly Fishing in msmollygmartin
**Symptom:** msmollygmartin's profile included "fly fishing" as a top interest, but her posts were about her brother's fly fishing accomplishments, not her own.
**Root cause:** The profile analyzer prompt had no instruction to distinguish the account owner's interests from interests of people they post about. All content was treated as belonging to the account owner.
**Fix:** Added INTEREST ATTRIBUTION instructions to the prompt: "Extract ONLY the account owner's interests. When posts mention a family member's, friend's, or partner's hobby, do NOT extract that unless they also demonstrate personal engagement." Also added confidence scoring (high/medium/low) and engagement weighting to prioritize interests from high-engagement posts.

**Files changed:** `post_curation_cleanup.py`, `multi_retailer_searcher.py`, `profile_analyzer.py`

---

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

**Monitor after deploy:** Check `Product source breakdown:` in logs to verify Awin/CJ products appear more often.

**Architectural follow-up:** These fixes are stopgaps. The real fix is the Catalog-First Architecture task (see Pending Opus Tasks): expand sync terms from 252 to 500-800+, make CJ/Awin catalog-only (no live calls), make eBay/Amazon live-only (no DB write-back). This eliminates the cache pollution loop entirely.

---

## Production Log Review (Mar 18-19, 2026)

**Overall health: Good.** Startup clean, catalog sync completing daily (~2 min), recommendation pipeline working end-to-end. A real user session successfully generated 13 recommendations with 76% real image rate.

**Observations:**
- **Etsy API returns 403 Forbidden** on all search queries. Known/expected — Etsy has rejected dev credentials multiple times. Etsy searches are wasted API calls until credentials are approved.
- **Duplicate in-flight Claude API calls** — two concurrent profile analysis requests for the same profile hash (`3c6142ae`) because the caching layer doesn't prevent in-flight duplicates. Not critical at current volume, but will waste API spend under load. Consider adding an in-flight lock (e.g., a dict of pending profile hashes) so the second request waits for the first to finish and uses its cached result.
- **Railway severity mislabeling** — Gunicorn logs to stderr, so Railway tags all INFO-level logs as "error" severity in the dashboard. This is cosmetic; filter by message content, not severity badge.
- **405 Method Not Allowed** — escalating. Was a single cluster (Mar 17), now 6 incidents spread throughout Apr 10. Bot or persistent scanner. Real users unaffected. Added URL logging to 405 handler (READY #8) to identify which endpoint is being targeted.
- **Stripe not configured** — expected at current stage (paywall not enforced).
- **Catalog sync healthy** — CJ: ~3,995 products across 40 search terms. Awin: ~7,743 products across 26 joined feeds.
- **Claude model in use:** `claude-sonnet-4-20250514` for both profile analysis and curation.

---

## Mother's Day Push (May 10, 2026) — 4 Weeks Out

Mother's Day is the first real seasonal traffic test. The guide is live, the catalog has the right inventory (FlowersFast, MonthlyClubs flowers/chocolate, zChocolat, SilverRushStyle, FragranceShop, Peet's, GroundLuxe), and the rec engine works. This is about distribution and conversion, not building.

### The window

| Week | Dates | Focus |
|------|-------|-------|
| **Now** | Apr 9–15 | Foundation: deploy, Search Console, kill placeholder Etsy guides |
| **Consideration peak** | Apr 15–29 | Outreach: Reddit DMs targeting mom-gift posts, self-promo posts |
| **Last-minute window** | Apr 29–May 9 | Urgency: FlowersFast same-day angle, last-minute section in guide |
| **Day of** | May 10 | Watch dashboard. No changes. |

### READY actions (execute in order)

1. **Merge branch + deploy** — everything from this session needs to be live
2. **Google Search Console** — submit `giftwise.fit/sitemap.xml` now. The Mother's Day guide needs 2–3 weeks to index properly before search traffic peaks. This is the single highest-leverage 2-minute action.
3. **Kill the 3 Etsy placeholder guides** — `guide_etsy_home_decor.html`, `guide_etsy_jewelry.html`, `guide_etsy_under_50.html`. Thin content hurts domain authority right when we need it. Add 301 redirects and remove from sitemap.
4. **Reddit DMs** — `python scripts/reddit_scout.py --mode dms` once API credentials land. Mother's Day keyword boost already in the script. Target: r/GiftIdeas posters, r/Mommit, r/daddit, r/AskWomen.
5. **Self-promo posts** — r/SideProject, r/ChatGPT, r/InternetIsBeautiful. Mother's Day angle: "built a tool that reads someone's Instagram and builds a gift list — timing it for Mother's Day." One post per sub, spaced out.

### What to watch on the dashboard

- `guide_hit:mothers-day` — is organic search finding the guide?
- `referral_hit:reddit_*` — is outreach driving visits?
- `rec_run` — are guide visitors converting to the tool?
- `product_click:awin` + `product_click:cj` — are recs turning into clicks?

If `guide_hit` is climbing but `rec_run` is flat, the guide CTAs aren't converting — tighten the above-fold CTA copy. If `rec_run` is up but `product_click` is flat, rec quality needs attention.

### Revenue levers specific to Mother's Day

- **FlowersFast** (same-day delivery) is the strongest last-minute play — emphasize in the final week
- **zChocolat** and **MonthlyClubs** chocolate/flowers are the subscription upsell — one gift that arrives multiple times
- **SilverRushStyle** jewelry and **FragranceShop** are the "she wouldn't buy this for herself" angle
- The rec engine is the conversion multiplier — a personalized list converts better than a guide browse

### What NOT to do

- Do not add friction (rate limiting, paywall) during any traffic spike from this push
- Do not change the Mother's Day guide structure during the final 2 weeks — stability > optimization
- Do not submit new pages to Search Console mid-push — focus indexing credit on existing guide

---

## Reddit Outreach (Apr 2026)

**Primary goal:** Insert GiftWise into people's consciousness. Secondary: build reputation as a caring gift advisor.

**Status:** Wave 1 in progress (manual). Reddit API credentials still pending.

### Sub-specific strategy

| Sub | Approach | Notes |
|-----|----------|-------|
| r/GiftIdeas | **DMs only** | Comments are banned. DM posters who are genuinely stuck. |
| r/gifts | **Public comments** | Comments allowed. Public replies compound via search. |
| r/SideProject, r/ChatGPT, r/InternetIsBeautiful | Self-promo post | One post per sub, spaced out. Mother's Day angle. |
| r/Mommit, r/daddit, r/AskWomen | DMs | Target mom-gift posts once API credentials arrive. |

### Voice rules (short version)

Read `docs/VOICE.md` before drafting. Key rules:
- **Socratic over declarative.** "I wonder if..." not "you should..."
- **Never speak as authority on the recipient.** You don't know this person.
- **No adverbs.** "genuinely," "actually," "really," "just" — cut them.
- **No em dashes.** Use a period or comma instead.
- **No trailing period on the last line**
- **Typographic looseness.** Lowercase sentence starts.
- **3-5 sentences.** Two short paragraphs at most.
- **Lead with context, not the product name.**
- **Only drop GiftWise when no clear answer exists.** Dropping it into every reply reads as spam.

### Tool drop format

```
I found a tool at giftwise.fit where you paste their handle and it builds a list from what they post about. free as far as I can tell
```

With caveat if relevant: `I think it lets you specify budget but no idea how well it sticks to it`

- No `?ref=` in DMs — feels tracked in a one-to-one context
- `?ref=reddit` is fine in public comments

---

## Current Priorities (Updated Apr 11, 2026)

**Session start protocol:** Surface the top 3 READY items before doing anything else. If the user hasn't mentioned a specific task, start there.

---

### READY — no blockers, execute now

| # | Task | What to do |
|---|------|-----------|
| 1 | **Reddit Wave 1 (in progress)** | r/GiftIdeas: DMs only (comments banned). r/gifts: public comments. r/SideProject, r/ChatGPT, r/InternetIsBeautiful: one self-promo post per sub. See Reddit Outreach section above for voice rules and tool drop format. Ask Claude to draft pointing at `docs/VOICE.md`. |
| 2 | **Take down 3 placeholder Etsy guides** | `guide_etsy_home_decor.html`, `guide_etsy_jewelry.html`, `guide_etsy_under_50.html` have placeholder content — SEO liability. Add 301 redirects: home_decor → `/guides/gifts-for-her`, jewelry → `/guides/gifts-for-her`, under_50 → `/guides`. Remove from sitemap. |
| 3 | **Drop Russell Stover + GameFly from CJ sync** | Low-quality / irrelevant merchants in catalog. Add to exclusion list in `catalog_sync.py`. |
| 4 | **Block King Koil in Awin** | Add to merchant exclusion list in `awin_searcher.py`. |
| 5 | **14-Item Phase 2: Sonnet-safe tasks** | Template UI for splurge tile (`recommendations.html`) + eBay niche-only scoping (`multi_retailer_searcher.py`). Full spec in the 14-Item section below. |
| 6 | **Catalog-First Architecture Phase 2** | Tasks 1-3 + 5 (remove live CJ/Awin from session-time, wire eBay niche-only, retune diversity cap). Full spec in Pending Opus Tasks → Catalog-First section. |
| 7 | **Google Search Console sitemap** | Verification route already live at `/googlef18ce1baab96164b.html`. Go to Search Console → verify ownership → submit `giftwise.fit/sitemap.xml`. 2-minute user action. |
| 8 | **Add URL logging to 405 handler** | Add `request.url` + `request.method` to the 405 error handler in `giftwise_app.py`. 405s escalating — 6 incidents on Apr 10 spread throughout the day. Need to know which endpoint bots are hitting before this gets noisier. |

---

### BLOCKED — waiting on external party or user action

| Task | Blocker | Next step |
|------|---------|-----------|
| **Reddit scout automation** | Reddit API credentials pending approval | When credentials arrive: add to Railway env vars (`REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USERNAME`, `REDDIT_PASSWORD`), test `scripts/reddit_scout.py` |
| **OG default image** | User must create asset | Make `og-default.png` 1200×630 in Canva (cream bg, GiftWise logo, tagline). Add to `static/images/`. Until then social shares have no preview. |
| **Awin approvals** | ~35 applications pending since Feb 25 | Check Awin dashboard for new approvals; wire new merchants in `awin_searcher.py`. See `docs/AWIN_APPLICATIONS_FEB25.md`. |
| **FlexOffers** | Applied Feb 16, status unknown | Check FlexOffers dashboard. |
| **Impact.com** | Account type issue, ticket filed | Branch `claude/review-claude-docs-kEdui` has STAT tag + verification phrase — merge to main once Impact.com resolves. |
| **Rakuten** | Account active, no brand applications submitted | Apply to Sephora, Nordstrom, and others. See `docs/AFFILIATE_NETWORK_RESEARCH.md`. |

---

### NEXT UP — ready after one prerequisite

| Task | Prerequisite |
|------|-------------|
| **Reddit scout automation** | API credentials |
| **14-Item Phase 2: Splurge curator prompt** | Opus session — add to next Opus task queue (`gift_curator.py`) |
| **Experience booking link monetization** | Awin/CJ approvals (Sur La Table, ClassPass, Viator/Expedia) |
| **Load test & harden** | Warrants attention at ~15 sessions/day. See Opus prompt in `docs/ARCHITECTURE.md`. |

---

### MONITOR — no action, just watch

| Signal | Where to check | Threshold for action |
|--------|---------------|---------------------|
| **Session count** | Railway Metrics → Requests ÷ 7 | See paywall thresholds in Paywall Decision Framework |
| **Affiliate clicks** | Admin dashboard (`/admin/stats`) → retailer breakdown | Growing click rate = inventory is working |
| **Source diversity** | Railway logs → "Product source breakdown:" | Any source > 40% warrants investigation |
| **Facebook post traffic** | Admin dashboard rec_run count | Spike coming: do NOT paywall during it |
| **Duplicate in-flight Claude calls** | Railway logs → duplicate profile hash | Not critical now; fix before load testing |

---

## 14-Item Output Architecture (Mar 2026)

**Status: Phase 1 DONE (infrastructure). Phase 2 TODO (curator prompt + template UI).**

### Output Format

| Tier | Count | Source | Price Range | Visual |
|------|-------|--------|-------------|--------|
| **Regular gifts** | 10 | DB (CJ/Awin) + eBay for niche gaps | $15–250 | Standard tile |
| **Splurge** | 1 | DB (higher price tier) or premium experience | $200–1500 | Visually differentiated tile |
| **Experiences** | 3 | Curator-generated + booking provider links | Varies | Experience tile |

**Total: 14 items displayed.** Splurge can be either a premium physical gift OR an extravagant experience — curator decides based on what's strongest for the profile.

### What Changed (Phase 1 — Implemented)

1. **MECE Product Form Taxonomy** (`post_curation_cleanup.py`)
   - Expanded from 25 to 37 categories organized into form classes (Wearable, Decorative, Drinkware, Media, Equipment, Novelty, Craft, Subscription)
   - Split `mug` → `mug` + `bottle` (tumbler is not a mug)
   - Split `book` → `book` + `journal` (planner is not a novel)
   - Added: `hoodie`, `watch`, `figurine`, `plant`, `vinyl`, `headphones`, `speaker`, `subscription`, `phone-case`
   - MECE principle: no product fits two categories; every giftable product maps to a form or falls to uncategorized

2. **DB Write-Back Removed** (`multi_retailer_searcher.py`)
   - Live eBay/Amazon results no longer written back to the products DB
   - DB now contains ONLY nightly-synced CJ/Awin inventory from `catalog_sync.py`
   - Prevents marketplace pollution, stale listings, and affiliate tracking gaps

3. **Category Populated at Sync Time** (`catalog_sync.py`)
   - Both CJ and Awin upsert functions now call `detect_category()` and write to the `category` column
   - Enables form-diverse DB queries via window functions

4. **Price Tiers Restructured**
   - `AWIN_MAX_PRICE_USD`: raised from $200 → $1500 (both sync and live)
   - `AWIN_SYNC_MAX_PRICE_USD`: raised from $200 → $1500
   - Added `SPLURGE_PRICE_MIN = 200`, `SPLURGE_PRICE_MAX = 1500` in `catalog_sync.py`
   - `gift_score` no longer penalizes splurge-tier items — gives moderate +0.08 boost
   - Items > $1500 get strong penalty (-0.15)
   - `REPLACEMENT_PRICE_THRESHOLD` ($120) unchanged for regular slot backfill

5. **Form-Diverse DB Query** (`database.py`)
   - New `search_products_diverse()` function uses `ROW_NUMBER() OVER (PARTITION BY category)`
   - Returns at most `max_per_category` products per form (default 4)
   - Separates splurge candidates ($200-$1500) from regular pool
   - Returns `per_interest_counts` dict for eBay gap detection

### What Needs Building (Phase 2 — TODO)

#### Curator Prompt Changes (`gift_curator.py`)
- Change `rec_count` from 10 → 11 (10 regular + 1 splurge)
- Add splurge slot instructions: "Pick 1 SPLURGE item — the nicest version of something they love or an extravagant experience. Price $200-$1500. This should feel like a 'if money were no object' pick."
- Splurge price ceiling should be informed by profile `price_signals` and `budget_category`
- Wire the splurge candidates from `search_products_diverse()` into the inventory shown to the curator
- Keep 3 experiences unchanged

#### Template UI (`templates/recommendations.html`)
- Visually differentiate the splurge tile (larger? different border? "Splurge Pick" badge?)
- Position: after the 10 regular gifts, before the 3 experiences
- The splurge tile should feel aspirational, not garish

#### eBay Niche-Only Scoping (`multi_retailer_searcher.py`)
- Use `per_interest_counts` from `search_products_diverse()` to identify interests with weak DB coverage
- Run eBay ONLY for 2-3 interests with few/zero CJ/Awin matches
- Cap eBay contribution at ~5-8 items
- Do NOT write eBay results to DB

#### Experience Provider Monetization
**Critical finding:** ZERO experience providers in `experience_providers.py` are approved affiliate partners. Every link (Ticketmaster, Cozymeal, Viator, etc.) is an unmonetized utility link.

**Experience materials monetization (Phase 1 — DONE):**
- `_backfill_materials_links()` in `giftwise_app.py` now has a DB catalog search fallback
- When a material (e.g. "Bluetooth speaker" for a listening party) doesn't match the interest-fetched inventory, it searches the full CJ/Awin catalog via `search_products_by_title()` before falling back to Amazon search links
- This means experience materials are now matched against monetized inventory first
- New function `search_products_by_title()` in `database.py` does keyword-based title search against the product catalog

**Booking link monetization (NOT YET — requires affiliate approvals):**
- Check CJ/Awin dashboards for bookable experience advertisers (cooking classes, spa services, adventure activities)
- Viator is owned by Expedia — likely available through an Expedia affiliate program
- Airbnb has an affiliate program (check Rakuten/Impact)
- Sur La Table is in CJ but not yet approved — pursue
- ClassPass, Masterclass — check availability in affiliate networks
- Until real partners are wired in, experience links remain utility/service links
- DO NOT invent affiliate links or wire aspirational partners — that's hallucination

### Splurge Slot: Profile-Informed Price Ceiling

The profile analyzer already outputs `price_signals.estimated_range` and `price_signals.budget_category`. Use these to set the splurge ceiling:

| Budget Category | Splurge Ceiling | Rationale |
|----------------|-----------------|-----------|
| budget | $300 | Student/budget profiles — a $1500 item would feel absurd |
| moderate | $500 | Middle-income — stretch but not shocking |
| premium | $1000 | Shows luxury signals — high-end is appropriate |
| luxury | $1500 | Clearly affluent profile — full range |
| unknown | $500 | Default to moderate when signals are weak |

The curator prompt should include this ceiling. The `gift_score` function doesn't need to know — it scores all splurge-tier items equally; the curator makes the taste judgment.

---

## Content & SEO: Guide/Blog Strategy

**Key insight (Mar 2026):** Admin dashboard shows `guide_hit` significantly outpacing `rec_run`. Users land on guides via search but don't convert to the main tool.

**For all guide/blog content writing: read `docs/VOICE.md` first.** It captures Chad's writing style from real email samples, the brand positioning (tool not oracle, participant not recipient), gender/identity stance, and a kill list of AI writing tells. Do not write or rewrite guide content without reading it.

### What Was Fixed (Apr 2026)

| Fix | Status |
|-----|--------|
| Above-fold + mid-page CTAs in all guides | ✅ Done |
| All CTAs → `/demo?ref=guide` (not `/signup`) | ✅ Done |
| Per-slug tracking (`guide_hit:{slug}`) | ✅ Done |
| Per-retailer click tracking (`product_click:{retailer}`) | ✅ Done |
| Sitemap.xml route | ✅ Done |
| Robots.txt route | ✅ Done |
| Canonical tags in base.html | ✅ Done |
| OG/Twitter Card meta tags in base.html with per-guide overrides | ✅ Done |
| JSON-LD Article + BreadcrumbList schema on all guides | ✅ Done |
| FAQPage schema on Mother's Day + Father's Day + Graduation guides | ✅ Done |
| Google Search Console verification route | ✅ Done (`/googlef18ce1baab96164b.html`) |
| Homepage "Gift Guides by Occasion" section (was zero links to guides) | ✅ Done |
| Graduation guide (`/guides/graduation`) | ✅ Done |
| Admin dashboard: retailer breakdown + per-guide/blog hit tables | ✅ Done |
| Full voice pass on all 9 guides (3 passes total) | ✅ Done |

### Still Open

| Issue | Details |
|-------|---------|
| **3 Etsy guides incomplete** | `guide_etsy_home_decor.html`, `guide_etsy_jewelry.html`, `guide_etsy_under_50.html` have placeholder content. Populate or take down. |
| **Blog index CTA** | `/blog` page still has no mention of the tool. |
| **OG default image** | `static/images/og-default.png` (1200×630) referenced but doesn't exist. Create in Canva. |
| **`guide_to_tool` funnel event** | Not yet tracked — when someone navigates from a guide to the main tool. |

### Guide Inventory (9 guides as of Apr 2026)

| Slug | Title | Last Updated |
|------|-------|-------------|
| `/guides/mothers-day` | Mother's Day | April 2026 |
| `/guides/fathers-day` | Father's Day | April 2026 |
| `/guides/graduation` | Graduation | April 2026 |
| `/guides/gifts-for-her` | Gifts for Her | April 2026 |
| `/guides/gifts-for-him` | Gifts for Him | April 2026 |
| `/guides/chocolate-gourmet` | Gourmet Food Gifts | April 2026 |
| `/guides/coffee-tea` | Coffee & Tea Gifts | April 2026 |
| `/guides/subscription-boxes` | Subscription Boxes | April 2026 |
| `/guides/tech-gifts` | Tech Gifts | April 2026 |

### Keeping Guides Fresh

Current guides are static HTML with hardcoded products. They'll go stale. Options:
- **Manual refresh (quarterly):** Review each guide, swap out discontinued/seasonal products, update affiliate links. Low effort, low frequency.
- **Semi-automated:** Build a script that queries the same retailer APIs (CJ, Awin, eBay) for each guide's category and outputs updated product cards. Human reviews and pastes into template.
- **Dynamic guide sections:** Replace some hardcoded products with a server-side call that pulls top-rated products from the catalog DB for that category. Keep editorial intro/outro static.

Start with manual refresh — the 3 Etsy guides need it immediately since they're broken. Consider semi-automated once there are 15+ guides.

---

## Video / Social Content

### What shipped (Apr 2026)
- **Facebook (Apr 5):** iMovie screen recording of the full GiftWise experience, cut to 44 seconds with wait times removed. Posted to personal network. Authentic, self-deprecating tone. TikTok reel concept ("The Birthday") was built but not posted — pivoted to screen recording as faster/more authentic.
- **Reddit:** Posts drafted for 12 subreddits + situational comment templates. Wave 1 launching this week. Ask Claude to regenerate them pointing at `docs/VOICE.md` if needed.

### "The Birthday" Reel (Paused — Mar 2026)

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
