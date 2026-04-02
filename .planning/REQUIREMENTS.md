# Requirements: GiftWise

**Defined:** 2026-04-01
**Core Value:** Show the right gift for THIS specific person — grounded in their actual interests, posts, and aesthetic.

---

## v1 Requirements

### Conversion Funnel

- [ ] **CONV-01**: Every guide page has an above-fold CTA linking to `/demo` (not `/signup`)
- [ ] **CONV-02**: Every guide page has a mid-page CTA after the 3rd–4th product recommendation
- [ ] **CONV-03**: Blog index (`/blog`) and guide index (`/guides`) have prominent tool callouts
- [ ] **CONV-04**: All existing CTAs that point to `/signup` are updated to point to `/demo`
- [ ] **CONV-05**: Each guide/blog slug fires a per-slug tracking event (e.g., `guide_hit:beauty`) instead of the generic `guide_hit`
- [ ] **CONV-06**: The 3 broken Etsy guides are either fully populated or taken down (no placeholder content live)

### Retailer Inventory

- [ ] **RET-01**: AWOL Vision (Awin ID 98169) products sync nightly via catalog_sync.py with interest tags `["home theater", "movies", "tech", "entertainment", "projector"]`
- [ ] **RET-02**: OUFER Body Jewelry (Awin ID 91941) products sync nightly via catalog_sync.py with interest tags `["body jewelry", "piercing", "alternative fashion", "edgy style", "Gen Z"]`
- [ ] **RET-03**: youngelectricbikes (Awin ID 120209) has 3–5 static hero products in awin_searcher.py with interest tags `["cycling", "outdoor adventure", "fitness", "electric bikes"]` — surfaced for splurge slot
- [ ] **RET-04**: Tayst Coffee (Awin ID 90529) has 2–3 static products in awin_searcher.py with interest tags `["coffee", "sustainability", "eco-friendly", "subscription"]`
- [ ] **RET-05**: VitaJuwel and VSGO placeholder URLs in awin_searcher.py replaced with real Awin deep links

### Catalog-First Architecture (Source Separation)

- [x] **CAT-01**: Live CJ GraphQL calls removed from session-time code (`multi_retailer_searcher.py`) — CJ products come from DB only
- [x] **CAT-02**: Live Awin feed CSV download fallback removed from `awin_searcher.py` — Awin products come from DB only; static Awin partners still run
- [x] **CAT-03**: eBay runs ONLY for interests with < 5 matching DB products (identified via `per_interest_counts` from `search_products_diverse()`), capped at 7 items total (EBAY_NICHE_CAP=7)
- [x] **CAT-04**: `_run_cj` removed from parallel retailer tasks in `multi_retailer_searcher.py`; CJ static partner logic (MonthlyClubs, Winebasket, etc.) preserved
- [x] **CAT-05**: `awin_searcher.py` Awin `_matches_query()` 2-term threshold preserved and not weakened
- [x] **CAT-06**: No eBay or Amazon results written to DB (already enforced — verify and document)

### 14-Item Output (Sonnet Portions)

- [x] **OUT-01**: `search_products_diverse()` returns a separate `splurge_candidates` list ($200–$1500) passed through the pipeline to the curator
- [x] **OUT-02**: Splurge candidates are included in the inventory payload shown to the curator (alongside regular candidates)
- [ ] **OUT-03**: Recommendations template (`templates/recommendations.html`) renders a visually differentiated splurge tile — positioned after the 10 regular gifts, before the 3 experiences
- [ ] **OUT-04**: Splurge tile includes a "Splurge Pick" badge and uses the profile's `budget_category` to set the price ceiling shown (budget→$300, moderate→$500, premium→$1000, luxury→$1500)
- [ ] **OUT-05**: `# SONNET-FLAG:` comment added to `gift_curator.py` at the rec_count and splurge slot instruction location, with a complete Opus prompt ready to paste (see ROADMAP Phase 3 notes)

### Infrastructure

- [ ] **INF-01**: `skimlinks_searcher.py` deleted (dead code — service defunct)
- [ ] **INF-02**: Skimlinks JS snippet removed from all templates
- [ ] **INF-03**: In-flight duplicate prevention: a dict of pending profile hashes prevents two concurrent Claude API calls for the same profile
- [ ] **INF-04**: Rate limits confirmed backed by SQLite `rate_limits` table (not shelve) — verify current implementation

---

## v2 Requirements

### Affiliate Network Expansion

- **AFF-01**: Apply to Uncommon Goods, Personalization Mall, Things Remembered, Oriental Trading, HomeWetBar on Awin (ShareASale migration)
- **AFF-02**: FlexOffers integration wired if/when approved
- **AFF-03**: Rakuten brands applied to (Sephora, Nordstrom, Anthropologie, Free People, Coach)
- **AFF-04**: Impact.com resolved and integrated (Target, Ulta, Kohl's, Dyson, Adidas)
- **AFF-05**: Experience booking providers monetized (Viator/Expedia, Airbnb, ClassPass)

### Quality & Intelligence

- **QUAL-01**: Excluded interests passed to curator prompt so it doesn't re-invent them (fly fishing re-synthesis problem)
- **QUAL-02**: Per-guide traffic source tracking wired to admin dashboard
- **QUAL-03**: `product_intelligence` table populated from curator selections over time (feedback loop)

### Load Hardening

- **LOAD-01**: Shelve concurrency for `storage_service.py`, `site_stats.py`, `share_manager.py` audited and fixed if racy under 3+ Gunicorn workers
- **LOAD-02**: Gunicorn worker exhaustion strategy documented and implemented if sessions/day > 10
- **LOAD-03**: In-flight lock for concurrent same-profile requests (v1 has basic dedup, v2 has proper lock)

### 14-Item Output (Opus Portions)

- **OPUS-01**: `gift_curator.py` prompt updated: rec_count 10 → 11, splurge slot instructions added, profile budget_category ceiling wired — **OPUS ONLY**
- **OPUS-02**: Profile `price_signals.budget_category` passed through to curator context — **OPUS ONLY**

---

## Out of Scope

| Feature | Reason |
|---------|--------|
| Paywall enforcement | Not until 15+ sessions/day sustained — see BUSINESS_STRATEGY.md |
| Stripe gatekeeping | Stripe route exists but must not be wired to access control yet |
| Mobile app | Web-only by design |
| Etsy live API | Dev credentials rejected; 403 on all queries |
| Spotify OAuth | Removed — caused infinite waits/403s |
| Skimlinks | Service defunct — remove dead code, do not re-add |
| International currency | US market only |
| Campaign-specific promo codes | 884 lines deleted Feb 2026, do not re-add |
| Hard-filtering products before curation | Kills diversity — use soft guidance + post-curation cleanup only |
| Routing URLs/images/prices through LLM prompts | LLMs corrupt structured data |
| Automated social media posting | Not a product feature |
| Video content generation | Not a product feature |

---

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| CONV-01 | Phase 1 | Pending |
| CONV-02 | Phase 1 | Pending |
| CONV-03 | Phase 1 | Pending |
| CONV-04 | Phase 1 | Pending |
| CONV-05 | Phase 1 | Pending |
| CONV-06 | Phase 1 | Pending |
| RET-01 | Phase 1 | Pending |
| RET-02 | Phase 1 | Pending |
| RET-03 | Phase 1 | Pending |
| RET-04 | Phase 1 | Pending |
| RET-05 | Phase 1 | Pending |
| CAT-01 | Phase 2 | Complete |
| CAT-02 | Phase 2 | Complete |
| CAT-03 | Phase 2 | Complete |
| CAT-04 | Phase 2 | Complete |
| CAT-05 | Phase 2 | Complete |
| CAT-06 | Phase 2 | Complete |
| OUT-01 | Phase 3 | Complete |
| OUT-02 | Phase 3 | Complete |
| OUT-03 | Phase 3 | Pending |
| OUT-04 | Phase 3 | Pending |
| OUT-05 | Phase 3 | Pending |
| INF-01 | Phase 4 | Pending |
| INF-02 | Phase 4 | Pending |
| INF-03 | Phase 4 | Pending |
| INF-04 | Phase 4 | Pending |

**Coverage:**
- v1 requirements: 25 total
- Mapped to phases: 25
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-01*
*Last updated: 2026-04-01 after GSD project initialization*
