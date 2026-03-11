# GiftWise Revenue Optimization Plan

## Current Economics (Broken)

**Cost per session:** ~$0.10-0.20 (2 Claude API calls)
**Revenue per session:** Unknown, but LOW because:
- Thin inventory (30 products, mostly Amazon 1-4% commission)
- Re-analyzing same profiles repeatedly
- No product intelligence (sending bad products to Claude)
- Curator gets overwhelmed with low-quality products

**Wasted spend:**
- Profile caching is coded but broken (never fires)
- No product intelligence (curator sees junk products)
- No learning from successful recommendations

---

## Revenue-First Architecture (What We're Building)

### 1. **Fix Profile Caching** (Immediate 50% API cost reduction)

**Problem:** Lines 468-471 in profile_analyzer.py reference missing config
**Fix:** Wire up the existing database.cache_profile() / get_cached_profile()

**Impact:**
- First user with "Taylor Swift + hiking" profile: Pay $0.02 for analysis
- Next 100 users with similar profiles: $0.00 (cache hit)
- **Estimated savings: 50% of profile analysis costs**

---

### 2. **Product Intelligence Database** (Improve curator output)

**Current:** Send 100 random products to Claude, hope for the best
**Should be:** Send 30 HIGH-QUALITY products pre-filtered by local intelligence

**Schema to add:**
```sql
CREATE TABLE product_intelligence (
    product_id TEXT PRIMARY KEY,
    retailer TEXT,

    -- AI-generated intelligence (cached from curator)
    gift_worthiness_score REAL,  -- 0.0-1.0, how good as a gift
    best_for_interests TEXT,     -- JSON: ["taylor-swift", "music"]
    best_for_relationship TEXT,  -- "friend|partner|family|myself"
    avoid_reasons TEXT,          -- JSON: ["too generic", "low quality"]

    -- Performance metrics (learn what converts)
    times_recommended INTEGER DEFAULT 0,
    times_clicked INTEGER DEFAULT 0,
    times_favorited INTEGER DEFAULT 0,
    click_through_rate REAL,

    -- Commission tracking (prioritize high-commission products)
    commission_rate REAL,
    estimated_commission_per_sale REAL,

    last_updated TIMESTAMP
)
```

**Usage:**
```python
# Before curation: Filter product pool to high-quality candidates
products = get_all_available_products()  # 100 products

# Local intelligence pre-filter
products = [p for p in products if:
    p.get('gift_worthiness_score', 0.5) > 0.3  # Remove known junk
    and p.get('click_through_rate', 0) > 0.02   # Keep proven performers
    and p.get('commission_rate', 0.01) > 0      # Prioritize revenue
]

# Now we're sending 30 high-quality products to Claude instead of 100 random ones
```

**Impact:**
- Curator gets better input → better output
- Higher CTR → more revenue
- Fewer API tokens needed (30 products vs 100)

---

### 3. **Interest Intelligence Cache** (Reuse analysis)

**Current:** Every session, Claude figures out "Taylor Swift fans like Eras Tour merch"
**Should be:** Cache this once, reuse forever

**Schema:**
```sql
CREATE TABLE interest_intelligence (
    interest_name TEXT PRIMARY KEY,

    -- Static intelligence (from enrichment_data.py)
    do_buy TEXT,           -- JSON: ["concert tickets", "vinyl records"]
    dont_buy TEXT,         -- JSON: ["generic music player"]
    demographics TEXT,     -- Who has this interest
    trending_level TEXT,   -- "evergreen|trending|declining"

    -- Dynamic intelligence (learned from sessions)
    top_products TEXT,     -- JSON: product_ids that converted well
    top_brands TEXT,       -- JSON: brands that work for this interest
    avg_price_point REAL,  -- What people actually buy

    times_seen INTEGER,    -- How many profiles have this interest
    last_updated TIMESTAMP
)
```

**Pre-populate from enrichment_data.py:**
```python
# enrichment_data.py already has this structure!
interests = {
    "taylor-swift": {
        "do_buy": ["concert merchandise", "vinyl records", "collectible items"],
        "dont_buy": ["generic posters", "unofficial merch"],
        "demographics": "Gen Z/Millennial, mostly female",
        ...
    }
}

# Import this into interest_intelligence table on first run
```

**Usage:**
```python
# When searching for products for "Taylor Swift" interest:
intelligence = get_interest_intelligence("taylor-swift")

# Use do_buy/dont_buy to generate better search queries
search_queries = intelligence['do_buy']  # ["concert merchandise", "vinyl records"]

# Filter results using dont_buy
products = [p for p in products if not matches_dont_buy(p, intelligence['dont_buy'])]

# Claude never sees the junk products, focuses on quality
```

---

### 4. **Curation Memory** (Learn what converts)

Track which recommendations lead to clicks/favorites/shares:

**Schema:**
```sql
CREATE TABLE curation_outcomes (
    id INTEGER PRIMARY KEY,
    session_id TEXT,

    -- Context
    profile_interests TEXT,  -- JSON
    relationship_type TEXT,
    recipient_age_range TEXT,

    -- Recommendation
    product_id TEXT,
    retailer TEXT,
    matched_interest TEXT,

    -- Outcome
    was_clicked BOOLEAN,
    was_favorited BOOLEAN,
    was_shared BOOLEAN,

    -- Revenue
    commission_rate REAL,
    estimated_value REAL,

    created_at TIMESTAMP
)
```

**Usage:**
```python
# After curation, track which products were recommended
for rec in recommendations:
    log_curation_outcome(session_id, rec, profile)

# When user clicks a product
mark_clicked(product_id)

# Aggregate this data to improve product_intelligence
update_product_intelligence_from_outcomes()
```

**Impact:**
- Learn which products actually convert
- Prioritize high-converting products in future sessions
- Measure revenue per session

---

### 5. **Smart Pre-Filtering Pipeline**

**Before sending to Claude curator:**

```python
def intelligent_product_filter(products, profile, relationship):
    """
    Reduce 100 products → 30 high-quality candidates using local intelligence
    Saves API tokens, improves curator output quality
    """
    scored_products = []

    for product in products:
        score = 0.0

        # Factor 1: Product intelligence (from past performance)
        intel = get_product_intelligence(product['product_id'])
        if intel:
            score += intel['gift_worthiness_score'] * 0.3
            score += intel['click_through_rate'] * 100 * 0.2

        # Factor 2: Interest match (from interest_intelligence)
        for interest in profile['interests']:
            interest_intel = get_interest_intelligence(interest['name'])
            if matches_do_buy(product, interest_intel['do_buy']):
                score += 0.3
            if matches_dont_buy(product, interest_intel['dont_buy']):
                score -= 0.5  # Strong negative signal

        # Factor 3: Commission rate (revenue-aware)
        commission_rate = intel.get('commission_rate', 0.01) if intel else 0.01
        score += commission_rate * 5  # 5% commission = +0.25 score

        # Factor 4: Relationship appropriateness
        if intel and relationship in intel.get('best_for_relationship', ''):
            score += 0.2

        scored_products.append((score, product))

    # Sort by score, take top 30
    scored_products.sort(reverse=True, key=lambda x: x[0])
    top_products = [p for score, p in scored_products[:30] if score > 0.3]

    logger.info(f"Filtered {len(products)} → {len(top_products)} high-quality products")
    return top_products
```

**Impact:**
- Curator sees 30 great products instead of 100 mediocre ones
- Saves ~70% of product description tokens
- Better curation quality → higher CTR

---

### 6. **Opus vs Sonnet Strategy**

**Current:** Both calls use Sonnet ($0.003/1K input tokens)
**Should be:**
- **Profile analysis (call #1):** Keep Sonnet - this is structure extraction, not taste
- **Gift curation (call #2):** Use Opus ($0.015/1K input tokens) - this is where taste matters

**Why this works:**
- Profile analysis: 5K input tokens × $0.003 = $0.015 (keep Sonnet)
- Gift curation: 15K input tokens × $0.015 = $0.225 (Opus)
- **Total cost: ~$0.24 per session**

**But with better input:**
- Gift curation: 8K input tokens × $0.015 = $0.12 (30 products, not 100)
- **New total: ~$0.135 per session**

**Revenue impact:**
- Opus curation → better gift picks → higher CTR
- Better products → higher commission rates (prioritize Etsy 4-5%, not Amazon 1-4%)
- **Target: $2-5 revenue per session** (15-40x cost)

---

### 7. **Database-First Product Search**

**Current flow:**
```
User generates recs → Call Etsy API → Call Awin API → Call eBay API → Call Amazon API
(4 API calls, slow, thin results)
```

**Should be:**
```
User generates recs → Query local database (instant, rich results)
Background job: Refresh database daily from all retailers
```

**Implementation:**
```python
# In multi_retailer_searcher.py
def search_products_multi_retailer(interests, max_per_source=10):
    # Try database first
    db_products = database.search_products_by_interests(
        interests=[i['name'] for i in interests],
        limit=100
    )

    if len(db_products) >= 50:
        logger.info(f"Using {len(db_products)} products from database cache")
        return db_products

    # Fallback to live API calls if database is stale
    logger.warning("Database insufficient, falling back to live retailer calls")
    # ... existing code ...
```

**Background refresh job (cron daily):**
```python
# scripts/refresh_product_database.py
def refresh_database():
    """Fetch products from all retailers and cache in database"""

    # Popular interests to pre-fetch
    top_interests = get_top_interests_from_sessions()  # e.g., ["taylor-swift", "hiking", "coffee"]

    for interest in top_interests:
        # Fetch from all retailers
        etsy_products = search_etsy(interest)
        awin_products = search_awin(interest)
        ebay_products = search_ebay(interest)
        amazon_products = search_amazon(interest)

        # Cache all in database
        for product in etsy_products + awin_products + ebay_products + amazon_products:
            database.upsert_product(product)

    database.set_metadata('last_refresh', datetime.now().isoformat())
    logger.info(f"Database refreshed with {total} products")
```

**Impact:**
- Instant product search (no waiting for API calls)
- Richer inventory (pre-fetched from all retailers)
- Lower per-session cost (database query is free)

---

## Implementation Priority

### Phase 1: Fix Broken Caching (Immediate 50% savings) 🔥
1. ✅ Fix config for profile caching
2. ✅ Wire up database.cache_profile() / get_cached_profile()
3. ✅ Test that cache hits work

**Estimated impact:** 50% reduction in profile analysis costs

### Phase 2: Smart Pre-Filtering (Better curator output) 🔥
1. ✅ Add product_intelligence table
2. ✅ Implement intelligent_product_filter()
3. ✅ Reduce curator input from 100 → 30 products

**Estimated impact:** 30% reduction in curator costs, 20% improvement in CTR

### Phase 3: Interest Intelligence (Reuse analysis) 🔥
1. ✅ Add interest_intelligence table
2. ✅ Import data from enrichment_data.py
3. ✅ Use in product filtering

**Estimated impact:** Better product matches, higher conversion

### Phase 4: Learning Loop (Compound growth)
1. ✅ Add curation_outcomes tracking
2. ✅ Update product_intelligence from outcomes
3. ✅ Continuous improvement as more sessions run

**Estimated impact:** Quality compounds over time

### Phase 5: Database-First Search (Scale when inventory grows)
1. ✅ Background refresh job
2. ✅ Database-first search strategy
3. ✅ Deploy when Skimlinks/Awin are live

**Estimated impact:** Instant search, richer inventory, lower per-session cost

---

## Revenue Model

**Current (broken):**
- Cost per session: $0.10-0.20
- Revenue per session: ~$0.50 (10 products × 5% CTR × $1 commission)
- **Margin: $0.30-0.40 per session** (2-3x cost)

**After optimization:**
- Cost per session: $0.08 (profile cache hit) + $0.12 (Opus curation with pre-filtered products) = **$0.20**
- Revenue per session: ~$2.00 (10 products × 10% CTR × $2 avg commission)
- **Margin: $1.80 per session** (10x cost)

**Why revenue goes up:**
1. Better products (pre-filtered by intelligence)
2. Opus curation (better taste)
3. Prioritize high-commission products (Etsy 5%, not Amazon 1%)
4. Learning loop (quality compounds)

**At 100 sessions/day:**
- Current: $30-40 profit/day
- Optimized: $180 profit/day
- **6x improvement**

---

## Next Steps

Ready to implement Phase 1-3 (fix caching + smart filtering + interest intelligence) right now?
This is the 80/20 - biggest impact, lowest risk.
