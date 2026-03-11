# GiftWise Session Handoff — Feb 17, 2026

## Branch
`claude/update-claude-docs-hrHnn` — all recent work committed here. Do NOT push to main without PR.

## What Was Done This Session

### Spotify-only pathway fixes (commit 8e9f6ab)
- **post_curation_cleanup.py**: `_normalize_title_for_dedup()` + title-based dedup in replacement pool. Same product was added 3x as replacement ("Christmas Necktie Holiday Traditions").
- **smart_filters.py**: Fixed WorkExclusionFilter crash — `city_region: null` caused `.lower()` on NoneType. Fixed with `(x or '').lower()`.
- **revenue_optimizer.py**: Fixed `do_buy`/`dont_buy` NoneType crash — DB stores explicit None, `get('key', [])` returns None. Fixed with `get('key') or []`.
- **etsy_searcher.py**: Replaced naive `f"{name} personalized gift"` with `search_query_utils.build_search_query()`, 60-char max.
- **cj_searcher.py**: Now calls `clean_interest_for_search()` before CJ GraphQL.
- **search_query_utils.py**: Added music-specific filler patterns ("and holiday traditions", "music curation", "and alternative aesthetics").
- **profile_analyzer.py**: `spotify_is_only_source` flag — when Spotify is ONLY data source, prompt tells Claude to use specific ARTIST NAMES as interests (not genre labels), infer lifestyle/aesthetic from genres, produce searchable interest names.

### Database auto-seeding (commit fa0e05b)
- **database.py**: `init_database()` now calls `_seed_interest_intelligence_if_empty()` on every cold start. Railway's ephemeral storage wipes DB on each deploy — this seeds 42 interests from enrichment_data.py automatically.
- DB is operational: 6 tables exist, interest_intelligence auto-seeds to 42 rows on cold start.

### Sovrn Commerce snippet (commit 4e1f641)
- Commented-out Sovrn snippet in base.html with `<!-- TODO: replace SOVRN_PUBLISHER_KEY -->`.
- Sovrn = Skimlinks alternative, 40k+ merchants, same 25% cut. Sign up at sovrn.com/commerce, need JS live + 1 real click before review.

## Interrupted Task: Wire Peet's Coffee

User just shared Peet's Coffee CJ affiliate CSV (approved). Session ran long before we could build it.

### Key links from the CSV:
- **Evergreen Link** (ID `15734720`, US only, deep-link enabled): `https://www.kqzyfj.com/click-101660899-15734720` — use this as base for deep links to peets.com product pages
- **Deeplink** (ID `13495394`, mobile-optimized): `https://www.tkqlhce.com/click-101660899-13495394`
- **NEWSUB30 coupon**: 30% off first coffee subscription shipment, valid thru Dec 2029 (link IDs 13970947 / 17180550 / 17180554)
- **WEBFRIEND5 coupon**: 5% off sitewide, affiliate exclusive, valid thru Dec 2026 (link ID 17125210)

### What to build:
Peet's has NO product feed via CJ — dynamic CJ GraphQL search won't reliably surface them. Need a curated static approach:

1. **Add Peet's to `enrichment_data.py`** under `coffee` interest `do_buy` list:
   - "Peet's Coffee subscription", "Peet's Major Dickason's blend", "specialty coffee gift set"

2. **Add a `peets_products` list to `cj_searcher.py`** (or new `peets_searcher.py`) with hardcoded curated products using deep links off the Evergreen link base. Key products:
   - Major Dickason's Blend (iconic dark roast)
   - Single Origin Series Subscription (premium gift)
   - Mighty Leaf Tea Collection (covers tea lovers)
   - Gift Bundles (20% off, link 15596392)
   - Frequent Brewer Subscription (recurring revenue)

3. **Trigger logic**: surface Peet's when profile has coffee, espresso, tea, gourmet food, or aesthetic signals that pair with coffee (indie folk, craft culture, Broadway crowd).

4. **T&C note**: Do NOT use discount language in descriptions beyond the stated coupons. NEWSUB30 and WEBFRIEND5 are legitimate to promote.

5. **Add to CLAUDE.md** under approved CJ partners: "Peet's Coffee (via CJ) ✅ Approved Feb 17 — Evergreen link ID 15734720, NEWSUB30 30% off first sub, WEBFRIEND5 5% sitewide. Trigger: coffee/espresso/tea/gourmet interests."

## Affiliate Status (Feb 17)

| Network | Status |
|---------|--------|
| Amazon | ✅ Active |
| eBay | ✅ Active |
| CJ: MonthlyClubs | ✅ Active |
| CJ: illy caffè | ✅ Active (6% commission, no discount language) |
| CJ: **Peet's Coffee** | ✅ Just approved — needs to be wired |
| CJ: ~68 others | Pending (rolling approvals) |
| Skimlinks | Pending (submitted 2/9, expected 2/18-20) |
| FlexOffers | Submitted 2/16 |
| Awin | Account active, need to JOIN merchants |
| Impact | Wrong account type, ticket open |
| Etsy | Developer credentials pending |
| Sovrn Commerce | Not yet applied |

## Key File Map
- `cj_searcher.py` — CJ GraphQL dynamic search
- `enrichment_data.py` — static do_buy/dont_buy intelligence (42 interests)
- `post_curation_cleanup.py` — programmatic diversity enforcement
- `profile_analyzer.py` — Claude call #1, Spotify-only mode
- `gift_curator.py` — Claude call #2
- `database.py` — SQLite, auto-seeds interest_intelligence on import
- `search_query_utils.py` — centralized query cleaning/building
- `AFFILIATE_APPLICATIONS_TRACKER.md` — affiliate status detail
- `OPUS_AUDIT.md` — quality audit checklist

## Open Quality Issues (OPUS_AUDIT.md)
1. `why_perfect` hidden on default card — show truncated version on compact card
2. Curator picks boring practical items — needs prompt guidance (not code filter)
3. Material matching fails ~70% — 5/5 unmatched in Spotify run
4. 4/13 placeholders in Spotify run — high placeholder rate
