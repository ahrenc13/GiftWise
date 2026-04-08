# Affiliate Partner Status

Last updated: Apr 2026

## Vendor Evaluation Rubric

When evaluating new Awin (or any network) applicants, apply this rubric before joining. Document verdicts in the "Reviewed & rejected" section of the relevant network.

| Signal | Reject if... |
|--------|-------------|
| Commission | < 4% unless exceptional product fit and high EPC |
| Cookie window | < 7 days |
| EPC | < $0.10 on an established program (new programs get a pass if other signals are strong) |
| Approval rate | < 70% (they're declining too many valid clicks) |
| CVR | < 0.5% is a red flag; < 0.1% is a hard reject |
| Payment status | Amber = caution; amber + risk flag = reject unless brand is exceptional |
| Risk level | exposurelevel2 or higher = do not join until established |
| Product category | Auto parts, pharma, beds, scooters, industrial goods — not giftable |
| Price range | Median < $10 or > $1,500 with no splurge-tier angle |
| Brand recognition | No homepage, no reviews, no social presence = junk vendor |
| Program age | < 6 months old with no EPC data = wait and watch |

**Auto-reject any vendor with 2+ red flags.** Single red flags are judgment calls based on category fit and brand quality.

---

## Active Networks

### CJ Affiliate — Primary Inventory Driver
GraphQL product search integrated. Filters non-joined advertisers. 15+ static partners with hardcoded product lists in `cj_searcher.py`.

| Partner | Commission | Trigger Interests | Notes |
|---------|-----------|-------------------|-------|
| illy caffè | 6% new / 4% existing | coffee, espresso | 45-day cookie, ~$125 AOV. No discount language. |
| Peet's Coffee | 10% | coffee, tea, gourmet | Coupons: NEWSUB30, WEBFRIEND5 |
| MonthlyClubs | varies | subscription, foodies, alcohol | 6 clubs (beer, wine, cheese, flowers, chocolate, coffee) |
| FlowersFast | 20% | flowers, romance, anniversaries | Same-day delivery. No FTD/Teleflora trademarks. |
| FragranceShop | 5% | perfume, cologne, beauty | 45-day cookie |
| GameFly | $5/lead, 10% used | gaming, video games | 0% on new games/consoles. **Consider dropping** — gaming is a major gift category but GameFly's model (rentals, used purchases) is a weak gift recommendation path. |
| GreaterGood | 2-15% | pets, philanthropy | Max 1 product returned |
| GroundLuxe | 10% | wellness, sleep, yoga | Highest EPC ($150-221). No medical claims. |
| Russell Stover | 5% | chocolate, sweets | 5-day cookie (very short). **Consider dropping** — gift shoppers rarely convert within 5 days; zChocolat (20%) covers this category better. |
| SilverRushStyle | 15% | jewelry, gemstones, bohemian | 60-day cookie, artisan silver |
| SoccerGarage | 7% (scales to 10%) | soccer | 60-day cookie, ~$125 AOV |
| TechForLess | 5% | tech, gadgets, laptops | Refurb/open-box electronics |
| Tenergy | 8% | eco, sustainability, tech | Rechargeable batteries, solar |
| TrinityRoad / Catholic Co | 8% | Catholic faith milestones | 6 sites incl. rosary.com |
| zChocolat | 20% (highest!) | chocolate, gourmet, luxury | Ships to 244 countries, ~$120 AOV |
| Winebasket / BabyBasket | 7% | wine, new baby, gourmet | ~$110 AOV |

### Awin — Expanding
Account active. 20 merchants confirmed (Mar 2026). Dynamic feed search live for feed-enabled merchants.

**Feed-enabled (dynamic search active):**
- Crown and Paw (pet portraits, 60-day cookie)
- LoveIsARose (up to 10%, $250 AOV — highest $/sale)
- Formulary 55 (8%, luxury soaps/crèmes)
- Dylan's Candy Bar (14-day cookie — short)
- Matr Boomie (fair trade, 60-day cookie)
- Maison Balzac (French glassware)
- Promeed (silk bedding) — **narrow gift fit; monitor EPC before keeping**
- Prosto Concept (hand-crafted baby pillows, organic, 50% CVR, 4.06 EPC — excellent)
- King Koil (air mattresses, 30-day cookie, feed+reporting) — **low gift fit; consider blocking at sync**
- Nextrition Pet (premium pet nutrition, 11.6% CVR, 100% approval)
- Ravin Crossbows (hunting/outdoor, 5% commission, 100% approval, feed enabled)

**No feed (static lists in `awin_searcher.py`):**
- VitaJuwel (crystal water bottles, ~$130) — TODO: replace placeholder URLs with real Awin deep links
- VSGO (15%, camera bags) — TODO: replace placeholder URLs with real Awin deep links
- Woven Woven
- Gourmet Gift Basket Store (gift baskets, 60-day cookie, green payment — perfect gift category)
- Goldia.com (fine jewelry, 7.5% commission, $160 AOV, 95K products, 100% approval, green payment)
- OUTFITR (adventure/camping gear, 10% commission, 30-day cookie)

**Blocked at sync:** Yadea (e-scooters), POSIE AND PENN (beds, amber status)

**Declined invitations (Mar 2026):** Canadian Insulin (pharma), Oedro (auto parts), PURTY BODY (too niche for gifts)

**Reviewed & rejected (Apr 2026):**
- **Cronjager** — Hard reject. 0.066% CVR, $0.05 EPC, amber payment status, exposurelevel1 risk, 73% approval rate. UK streetwear brand, narrow category fit.
- **Tangsem / pgfinds.com** — Pass for now. Commission fields show 0/0 in Awin (program not properly configured). Unknown brand, launched Jul 2025, no track record. 90-day cookie and 100% approval are positives — revisit Q4 2026 if they have real commission data.
- **Cosabella (US)** — Hold. Legitimate luxury lingerie brand but amber status + exposurelevel2 risk on a program launched Jan 2026 with 0% approval rate, no feed, no EPC data. Revisit Q3 2026.

**~35 more applications pending** from Feb 25. See `AWIN_APPLICATIONS_FEB25.md` for full list with tiers, EPC, conversion rates.

**Still need to join:** Uncommon Goods, Personalization Mall, Things Remembered, Oriental Trading, HomeWetBar (these are NOT on Awin — search CJ/FlexOffers).

**Note:** ShareASale migrated to Awin Oct 2025. All ShareASale merchants accessible through Awin.

### Amazon Associates — Active
1-4% commission (lowest). ~20 products per run.

### eBay Partner Network — Active
1-4% commission. ~12 products per run. EPN campaign params wired to all links.

## Pending Networks

| Network | Status | Key Brands |
|---------|--------|------------|
| Impact.com | Account type issue, second ticket filed | Target, Ulta, Kohl's, Gap, Home Depot, Adidas, Dyson |
| FlexOffers | Applied Feb 16, status unknown | 12,000+ advertisers |
| Rakuten | Account active, need to apply to brands | Sephora, Nordstrom, Anthropologie, Coach |
| Walmart Creator | Application submitted | Walmart |
| Etsy Direct | Dev credentials pending | Etsy (would bypass Awin) |

## Defunct

- **Skimlinks:** Service shut down. `skimlinks_searcher.py` is dead code. JS snippet still in templates (remove when convenient).

## Brand-to-Network Mapping

For the full ~70 brand mapping (family wishlist), see `AFFILIATE_NETWORK_RESEARCH.md`.

Key mappings:
- **Impact:** Target, Ulta, Kohl's, Gap, Home Depot, Dyson, Adidas, Spanx, Petco
- **CJ:** Macy's, Nike, American Eagle, J.Crew, Columbia, North Face, Kiehl's
- **Rakuten:** Sephora, Nordstrom, Anthropologie, Free People, Coach, ASOS
- **Awin:** Etsy, UGG, Lululemon, Portland Leather
- **No program:** Brandy Melville, Aritzia, IKEA (no US), Gymshark (invite-only)
