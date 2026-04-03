---
gsd_state_version: 1.0
milestone: v1.1
milestone_name: — The TikTok Launch
status: planning
last_updated: "2026-04-03T01:10:57.834Z"
last_activity: 2026-04-02
progress:
  total_phases: 7
  completed_phases: 5
  total_plans: 10
  completed_plans: 10
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md
See: .planning/ROADMAP.md (v1.1 section — phases 5-7)

**Core value:** Show the right gift for THIS specific person — grounded in their actual interests, posts, and aesthetic.
**Current focus:** v1.1 — The TikTok Launch. North star: 50 real `rec_run` events from strangers.

**v1.0 status:** COMPLETE (phases 1-4, 2026-04-02)

## Current Position

Milestone: v1.1
Phase: 5 (not started — plan-phase 5 is next)
Status: Ready to plan
Last activity: 2026-04-02

Progress: [░░░░░░░░░░] 0%

## v1.1 Phase Status

| Phase | Description | Status |
|-------|-------------|--------|
| 5 | Pre-Launch Mobile Audit | Not started |
| 6 | Distribution Gate (non-code) | Not started |
| 7 | Admin Visibility | Not started |

## Exit Criterion

**EXIT-01:** 50 `rec_run` events from non-admin IPs. Milestone is NOT complete until this is met — even if all phases are "done."

## Accumulated Context

### Decisions

- 2026-04-01: Accepted AWOL Vision (98169) and OUFER Body Jewelry (91941) as feed-enabled Awin merchants to wire into nightly sync
- 2026-04-01: Accepted youngelectricbikes (120209) and Tayst Coffee (90529) as static-only Awin partners
- 2026-04-01: Rejected MOJAWA (risk level 4), AIPI (no data), Mars by GHC (218-day payment), Simple Project (toilets), Adoreshome (no data) from Awin invite batch
- 2026-04-01: Joyrealtoys deferred — amber payment, no metrics, come back once they have track record
- [Phase 01]: Removed generic guide_hit event; per-slug tracking is sufficient and keeps analytics clean
- [Phase 01]: Added home_theater_av and body_jewelry_piercing to INTEREST_CATEGORIES at priority 2 for AWOL Vision (98169) and OUFER Body Jewelry (91941)
- [Phase 02]: Circuit breaker threshold at 100 products for live CJ/Awin fallback
- [Phase 02]: CJ static partners always run via api_key=None; Awin degrades to static on catalog failure
- [Phase 02]: EBAY_WEAK_COVERAGE_THRESHOLD=5, EBAY_NICHE_CAP=7 for niche-only eBay scoping
- [Phase 03]: splurge_candidates kept in regular pool AND exposed separately in dict return from searcher
- [Phase 03]: splurge_ceiling defaults to 500 in favorites/shared views where profile unavailable
- [Phase 04-infrastructure-hardening]: Removed all Skimlinks dead code: deleted skimlinks_searcher.py and purged references from 12 Python files and base.html
- [Phase 04]: INF-03 VERIFIED — In-flight profile dedup implemented in profile_analyzer.py (threading.Event, within-process lock). Two concurrent requests for same profile hash result in one Claude call.
- [Phase 04]: INF-04 VERIFIED — Rate limiting uses SQLite rate_limits table via check_and_record_pipeline_run() in database.py. WAL mode enabled. No shelve usage in rate-limit path.

### Pending Todos

- Apply to Uncommon Goods, Personalization Mall, Things Remembered, Oriental Trading, HomeWetBar on Awin (ShareASale migration — not yet applied)
- Check FlexOffers status (applied Feb 16, no response logged)
- Check Rakuten brand applications
- Monitor Joyrealtoys metrics — apply once they have track record
- Verify which of the 35 Feb 25 Awin applications have been approved/declined
