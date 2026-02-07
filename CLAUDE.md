# GiftWise — Project Intelligence

## What This Is
AI-powered gift recommendation app. Flask pipeline: scrape social media → Claude analyzes profile → enrich with static data → search retailers → Claude curates gifts → programmatic cleanup → display.

## Business Model & Revenue Architecture

### Revenue Streams (Priority Order)

**1. Affiliate Revenue (Primary — optimize relentlessly)**
Every product recommendation is an affiliate link opportunity. Revenue per click varies by source:
- Amazon Associates: 1-4% commission (lowest, but highest conversion)
- Etsy Affiliates: ~4-5% commission
- Awin merchants: 5-10% depending on advertiser
- eBay Partner Network: 1-4%

**Key insight: Multi-retailer diversity is a revenue multiplier.** Etsy/Awin products earn 2-5x the commission of Amazon per sale. Every architectural decision that improves non-Amazon representation directly increases revenue. Never optimize for one retailer — the system should surface the best gift from the best source, which naturally favors higher-commission retailers for niche/personalized products.

**Affiliate implementation rules:**
- All product URLs must pass through affiliate link wrapping before display
- Track click-through rate and conversion rate per source_domain — this data drives retailer prioritization
- If a retailer's API breaks (Etsy 403, Awin 500), treat it as a revenue emergency, not just a feature bug
- Never let affiliate optimization override gift quality — users who get bad recommendations don't come back, and retention is worth more than any single commission

**2. Subscription Tiers (Secondary — builds recurring revenue)**
- Free tier: 1-2 profiles/month, Amazon-only results
- Paid tier ($5-10/mo or $30-50/year): Unlimited profiles, multi-retailer (Etsy, eBay, Awin), saved profiles, refresh reminders
- Anchor annual pricing to gifting seasons (Christmas, Valentine's, Mother's/Father's Day)
- The profile is the retention asset — saved profiles with "refresh before their birthday" notifications create repeat usage

**3. Corporate/B2B (Future — highest ceiling)**
- Corporate gifting is a $300B+ market with terrible personalization
- A version ingesting LinkedIn + social signals for corporate-appropriate recommendations
- relationship_rules.py already handles "coworker" and "acquaintance" appropriateness tiers
- This is a separate product, not a feature of the consumer app

### Revenue-Aware Development Principles

When making any architectural decision, apply this framework:

**Does this change affect click-through rate?**
- Thumbnails directly impact CTR. A product with a real image gets 3-5x more clicks than a placeholder. Thumbnail fixes are revenue fixes.
- Product descriptions (why_perfect) drive purchase intent. Generic "they'll love this" descriptions don't convert. Evidence-based descriptions ("Based on their 47 Taylor Swift TikToks...") create confidence to click and buy.
- Dead links are lost revenue. Every 404 is a user who was ready to buy and bounced.

**Does this change affect source diversity?**
- More Etsy/Awin/eBay in the output = higher average commission per click
- Amazon should be a quality fallback, not the default — it has the lowest commission rate
- Source diversity also improves perceived value for paying subscribers ("I can't find these on Amazon myself")

**Does this change affect retention?**
- Saved profiles are the retention flywheel. Features that make profiles more useful over time (refresh, comparison, history) increase lifetime value.
- Recommendation quality is the #1 retention driver. One "how did it know?!" moment creates a repeat customer. One set of generic gifts creates a churned user.
- Session cost matters: two Claude Sonnet calls + retailer APIs = ~$0.05-0.10 per session. Affiliate or subscription revenue must exceed this. Don't add API calls without considering unit economics.

### Metrics That Matter (When Analytics Are Implemented)
- **Affiliate CTR**: % of displayed products that get clicked → target >25%
- **Source diversity ratio**: % of final recommendations that are non-Amazon → target >40%
- **Thumbnail success rate**: % of products with real images (not placeholders) → target >85%
- **Profile reuse rate**: % of users who run recommendations for a saved profile again → retention signal
- **Session cost**: Total API spend per recommendation session → keep under $0.15

## Technical Architecture Notes

### Key Files
- `giftwise_app.py` — Main app (~2800 lines), orchestrates the full pipeline
- `profile_analyzer.py` — Claude call #1: social data → structured profile
- `gift_curator.py` — Claude call #2: profile + inventory → curated recommendations
- `post_curation_cleanup.py` — Programmatic enforcement of diversity rules (brand, category, interest, source)
- `enrichment_engine.py` — Static intelligence layer (do_buy/dont_buy per interest, demographics, trending)
- `multi_retailer_searcher.py` — Orchestrates all retailer searches, merges inventory pool
- `rapidapi_amazon_searcher.py`, `ebay_searcher.py`, `etsy_searcher.py`, `awin_searcher.py` — Per-retailer search modules
- `smart_filters.py` — Work exclusion, passive/active filtering
- `image_fetcher.py` — Thumbnail validation and fallback chain
- `relationship_rules.py` — Relationship-appropriate gift guidance (disabled as hard filter, used as soft curator guidance)

### Patterns to Follow
- Images are resolved programmatically from inventory, never from curator LLM output
- Products are interleaved by source before the curator sees them (no positional bias)
- post_curation_cleanup.py is the enforcement layer — if a rule must be guaranteed, enforce it there, not in the prompt
- Prompts are for quality and judgment. Code is for rules and guarantees. Never rely on a prompt to do what code can enforce.
- Snippets must describe the product, not just the seller. "Carbon steel wok, 14-inch, flat bottom" beats "From ThaiKitchenStore".
- Curator gets 14 candidates, cleanup trims to 10. This gives cleanup room to enforce diversity without falling short.

### Patterns to Avoid
- Don't route structured data (URLs, image links, prices) through LLM prompts — they corrupt it
- Don't add "CRITICAL" to every prompt instruction — when everything is critical, nothing is
- Don't add API calls without considering per-session cost
- Don't hard-filter products before curation unless absolutely necessary (kills diversity). Prefer soft guidance in the prompt + programmatic cleanup after.
- Don't build features that only work for one retailer. Every feature should degrade gracefully when a source is unavailable.

### Current Status of Retailer Integrations
- Amazon (RapidAPI): Active, working
- eBay (Browse API): Active, working
- Etsy (v3 API): Awaiting developer credentials
- Awin (Data Feed API): Debugging 500 errors
- ShareASale: Not active

When Etsy and Awin come online, their snippet quality must match Amazon's before they're useful (see IMPLEMENTATION_PLAN.md changes 2-4).
