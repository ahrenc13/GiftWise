# Affiliate Network Applications Tracker

**Last Updated:** Feb 16, 2026

Track all affiliate network applications, approvals, and integration status.

## Application Status

| Network | Applied | Status | Expected Response | Priority |
|---------|---------|--------|-------------------|----------|
| **Skimlinks** | Feb 9 | ⏳ Pending | Feb 18-20 (7 biz days) | 🔥 CRITICAL |
| **CJ Affiliate** | Feb 15 (~70 brands) | ⏳ Pending | Feb 17-22 | 🔥 HIGH |
| **FlexOffers** | Feb 16 | ⏳ Pending | Feb 16-18 (same-day to 48h) | 🔥 HIGH |
| **Awin** (incl. ShareASale) | - | ✅ Approved, need to join advertisers | - | 🔥 HIGH |
| **Impact** | - | ❌ Account type issue | TBD (ticket open) | 🟡 MEDIUM |
| **Rakuten** | - | ✅ Approved, need brand apps | - | 🟡 MEDIUM |
| **Walmart Creator** | - | ⏳ Pending | TBD | 🟢 LOW |
| **Etsy Direct** | - | ⏳ Dev credentials pending | TBD | 🟡 MEDIUM |
| **Amazon Associates** | - | ✅ Active | - | ✅ LIVE |
| **eBay Partner Network** | - | ✅ Active | - | ✅ LIVE |

**NOTE:** ShareASale migrated to Awin in Oct 2025. All ShareASale merchants (Uncommon Goods, Personalization Mall, etc.) are now accessible through Awin.

## Approval Checklist

### Skimlinks (Blanket Access to 48,500 Merchants)
- [x] Application submitted (Feb 9)
- [ ] Approval received
- [ ] Publisher ID confirmed: 298548X178612
- [ ] JavaScript snippet installed (✅ Already in 40 templates)
- [ ] First click tracked
- [ ] Integration tested

**Expected Impact:** HUGE — Will unlock most brands in one approval

### CJ Affiliate (~70 Brands Applied)
- [x] Account created
- [x] Applications submitted to ~70 brands (Feb 15)
- [ ] First approvals coming in
- [ ] Track which brands auto-approve vs manual review
- [ ] Add approved brands to `cj_searcher.py`

**Key Brands to Watch:**
- Flowers: ProFlowers, 1-800-Flowers, FTD, Teleflora
- Jewelry: Kay Jewelers, Zales, Blue Nile, James Allen
- Apparel: American Eagle, J.Crew, Madewell, Columbia, North Face
- Home: Sur La Table, Williams Sonoma, Crate & Barrel

**Expected Approvals:**
- Auto-approve (24-48h): ~30-40 brands
- Manual review (3-7 days): ~30 brands

### Awin (Includes ShareASale Merchants as of Oct 2025)
- [x] Account created and approved
- [x] Initial research completed (Feb 16) - only found Portland Leather initially
- [ ] **NEW PRIORITY:** Search for former ShareASale merchants on Awin:
  - [ ] Uncommon Goods
  - [ ] Personalization Mall
  - [ ] Things Remembered
  - [ ] Oriental Trading
  - [ ] HomeWetBar
  - [ ] Other gift/personalization shops
- [ ] Join approved advertisers
- [ ] `awin_searcher.py` already exists - test with new advertisers once joined

**Expected Impact:** HIGH — ShareASale migration means all those unique gift merchants are now on Awin!

### FlexOffers
- [x] Application submitted (Feb 16)
- [ ] Account approved
- [ ] Browse Gifts & Flowers category
- [ ] Browse Home & Garden category
- [ ] Join auto-approve programs
- [ ] Create `flexoffers_searcher.py` module
- [ ] Add to `multi_retailer_searcher.py` pipeline

**Expected Impact:** MEDIUM-HIGH — Gap-filler for niche brands

### Impact (Account Type Issue)
- [x] Accidentally signed up as brand (not publisher)
- [x] Support ticket submitted
- [ ] Account type corrected
- [ ] Apply to priority brands:
  - [ ] Target
  - [ ] Ulta
  - [ ] Kohl's
  - [ ] Gap/Old Navy/Banana Republic
  - [ ] Home Depot
  - [ ] Adidas
  - [ ] Dyson

**Expected Impact:** HIGH — Major retail brands

### Rakuten
- [x] Account created
- [ ] Apply to individual brands:
  - [ ] Sephora
  - [ ] Nordstrom
  - [ ] Anthropologie
  - [ ] Free People
  - [ ] Coach
- [ ] Track approval status per brand

**Expected Impact:** MEDIUM — Premium retail brands


## Publisher Profile (Use for All Applications)

**Website:** https://giftwise.fit

**Description:**
```
AI-powered personalized gift recommendation platform. Users connect their social
media to receive curated gift suggestions matched to their interests and
personality. We combine social media insights with multi-retailer product search
to recommend thoughtful gifts from trusted brands.
```

**Audience:**
- Demographics: 25-45 year old women
- Intent: High-intent gift shoppers
- Geography: United States
- Behavior: Millennial/Gen Z, social media users

**Traffic:**
- Current: Beta (soft launch)
- Expected: 5,000-10,000 monthly visitors post-launch
- Source: Organic SEO, social media (TikTok/Instagram), direct

**Content:**
- 10 editorial gift guides (beauty, music, tech, travel, home, dog, Mother's Day, 3 Etsy guides)
- 4 SEO blog posts (evergreen gift content)
- AI-powered personalized recommendations

**Promotional Methods:**
- Content/Niche Website
- Blog/Review Site
- SEO/Organic Search
- Social Media Marketing
- Gift Guides & Editorial Content

**Why We're a Good Partner:**
```
We drive high-intent gift shoppers to merchants during peak seasons (Mother's Day,
Father's Day, holidays, birthdays). Our AI-powered personalization means users
receive targeted product recommendations, leading to higher conversion rates than
generic gift guides. We focus on quality curation over volume.
```

## Integration Priority (After Approval)

### Week 1 (Feb 17-23): Unlock Inventory
1. **Skimlinks approval** → Test immediately (already integrated)
2. **FlexOffers approval** → Add searcher module (~2 hours)
3. **ShareASale approval** → Add searcher module (~2 hours)
4. **CJ approvals rolling in** → Test with approved brands

### Week 2 (Feb 24-Mar 2): Expand & Optimize
5. **Impact account fixed** → Apply to Target, Ulta, etc.
6. **Rakuten brand apps** → Apply to Sephora, Nordstrom
7. **Monitor performance** via admin dashboard
8. **A/B test Opus curator** with better inventory

## Current Inventory Status

**LIVE (Feb 16):**
- Amazon (RapidAPI): ~20 products per session
- eBay (Browse API): ~10 products per session
- **Total: ~30 products** ❌ TOO THIN

**TARGET (Post-Approvals):**
- Skimlinks: +100 products (48,500 merchants)
- CJ Affiliate: +50 products (~70 brands)
- ShareASale: +30 products (gift specialists)
- FlexOffers: +20 products (niche brands)
- Amazon: ~20 products
- eBay: ~10 products
- **Total: 230+ products** ✅ HEALTHY

## Revenue Impact Projections

### Current State (Amazon + eBay only)
- Average commission: 2.5%
- Expected per-session: $0.05-0.10

### Post-Approvals (Multi-Network)
- Average commission: 4-5% (higher mix from Etsy, flowers, jewelry)
- Expected per-session: $0.15-0.25
- **2.5x revenue per session**

## Next Actions

**This Week (Feb 16-23):**
- [x] Apply to FlexOffers (submitted Feb 16)
- [x] Discovered ShareASale is now Awin (Feb 16)
- [ ] **PRIORITY:** Search Awin for former ShareASale merchants (Uncommon Goods, Personalization Mall, etc.)
- [ ] Join Awin advertisers once found
- [ ] Monitor CJ approvals daily
- [ ] Check Skimlinks approval (should come by Feb 18-20)
- [ ] Build FlexOffers searcher module (once approved)

**Next Week (Feb 24-Mar 2):**
- [ ] Test `awin_searcher.py` with newly joined advertisers
- [ ] Fix Impact account type issue
- [ ] Apply to Rakuten brands (Sephora, Nordstrom, etc.)
- [ ] Test full pipeline with 200+ products
- [ ] Run Opus vs Sonnet A/B test with better inventory
- [ ] Plan TikTok soft launch (once inventory is good)

## Support Contacts

- **Skimlinks:** publishers@skimlinks.com
- **CJ Affiliate:** Check dashboard for status
- **Awin:** https://www.awin.com/us/search/advertiser-directory (search for ShareASale merchants here)
- **FlexOffers:** support@flexoffers.com
- **Impact:** Support ticket system
- **Rakuten:** Check dashboard for brand status

## Important Migration Notes

**ShareASale → Awin (Oct 2025):**
ShareASale merged with Awin. All ShareASale merchants are now accessible through Awin's platform. The Awin account we already have gives access to these merchants - we just need to search for and join them individually.

**What this means:**
- ✅ No need to apply to ShareASale separately
- ✅ Awin account already approved
- 🔍 Need to search Awin's advertiser directory for former ShareASale brands
- 📝 Join each advertiser individually (like we do with other networks)

**Priority merchants to search for on Awin:**
- Uncommon Goods (unique gifts)
- Personalization Mall (custom items)
- Things Remembered (personalized jewelry)
- Oriental Trading (party/bulk gifts)
- HomeWetBar (custom barware)
- Portland Leather (already found)
