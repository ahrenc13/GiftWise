# Affiliate Partner Status

Last updated: Mar 2026

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
| GameFly | $5/lead, 10% used | gaming, video games | 0% on new games/consoles |
| GreaterGood | 2-15% | pets, philanthropy | Max 1 product returned |
| GroundLuxe | 10% | wellness, sleep, yoga | Highest EPC ($150-221). No medical claims. |
| Russell Stover | 5% | chocolate, sweets | 5-day cookie (very short) |
| SilverRushStyle | 15% | jewelry, gemstones, bohemian | 60-day cookie, artisan silver |
| SoccerGarage | 7% (scales to 10%) | soccer | 60-day cookie, ~$125 AOV |
| TechForLess | 5% | tech, gadgets, laptops | Refurb/open-box electronics |
| Tenergy | 8% | eco, sustainability, tech | Rechargeable batteries, solar |
| TrinityRoad / Catholic Co | 8% | Catholic faith milestones | 6 sites incl. rosary.com |
| zChocolat | 20% (highest!) | chocolate, gourmet, luxury | Ships to 244 countries, ~$120 AOV |
| Winebasket / BabyBasket | 7% | wine, new baby, gourmet | ~$110 AOV |

### Awin — Expanding
Account active. 13 merchants confirmed (Feb 26). Dynamic feed search live for feed-enabled merchants.

**Feed-enabled (dynamic search active):**
- Crown and Paw (pet portraits, 60-day cookie)
- LoveIsARose (up to 10%, $250 AOV — highest $/sale)
- Formulary 55 (8%, luxury soaps/crèmes)
- Dylan's Candy Bar (14-day cookie — short)
- Matr Boomie (fair trade, 60-day cookie)
- Maison Balzac (French glassware)
- Promeed (silk bedding)

**No feed (static lists in `awin_searcher.py`):**
- VitaJuwel (crystal water bottles, ~$130) — TODO: replace placeholder URLs with real Awin deep links
- VSGO (15%, camera bags) — TODO: replace placeholder URLs with real Awin deep links
- Woven Woven

**Blocked:** Yadea (e-scooters), POSIE AND PENN (beds, amber status)

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
