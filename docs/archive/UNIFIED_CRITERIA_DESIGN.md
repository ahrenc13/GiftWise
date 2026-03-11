# Unified Gift Criteria (Future Design)

## Current behavior

1. **Profile** is built (interests, location, style, price signals, etc.).
2. **Enrichment** (optional) adds enhanced search terms.
3. **Each vendor** gets the same profile and builds its **own** queries from interests (e.g. "Dog ownership and care gift", "Live music fan merchandise").
4. We call vendors **in sequence** (Etsy → Awin → eBay → ShareASale → Amazon) and **fill** until we hit `target_count`. The first vendor(s) that return enough products dominate the inventory.
5. **Curator** (Claude) picks the "best" from that inventory. If the inventory is 100% from one source (e.g. eBay), the curator can only choose from that source—there is no cross-vendor suitability evaluation.

So we **do** use profile-based criteria, but we **don’t** yet:

- Derive a single **vendor-agnostic** “ideal gift” spec (e.g. search phrases, categories, price band) and pass *that* to every API.
- **Request from all vendors in parallel** (or with a fixed cap per vendor) so the pool is always mixed.
- Have the curator **explicitly compare** “best match from Etsy vs best match from eBay vs best match from Amazon” for the same interest.

## What “unified criteria” would add

1. **Criteria layer**  
   From the profile (and optionally enrichment), produce one **gift criteria** object, e.g.:
   - Search phrases / keywords (e.g. “dog gift”, “live music merchandise”, “travel accessories”).
   - Price range, quality level, preferred attributes (handmade, personalized, etc.).
   - Optional: categories or verticals.

2. **Same criteria → all APIs**  
   Pass that criteria to **every** vendor (Etsy, Awin, eBay, ShareASale, Amazon). Each API maps the criteria to its own query format (keywords, filters, etc.). No vendor sees the raw profile; they all see the same normalized criteria.

3. **Cap per vendor + mixed pool**  
   Request up to **N products per vendor** (e.g. 5) so the combined inventory is always a **mix** of sources. No single API can fill the entire list.

4. **Curator evaluates across sources**  
   Curator sees the full mixed inventory and is prompted to:
   - Prefer **diversity of source** (e.g. at least 2–3 vendors in the final 10).
   - Choose the **best fit per interest** even when that means picking Etsy over eBay or Amazon for a given slot.

## Current behavior (inventory, no forced vendor mix)

- **Large inventory**: we request `target_count` (or `MAX_INVENTORY_SIZE // 5`) from **each** vendor and merge into one pool (Etsy + Awin + eBay + ShareASale + Amazon). So we build a large set of choices (up to ~100 products across hundreds of sellers). No per-vendor cap on how many we *take*—we take everything each API returns.
- **Curator picks the best N**: the final 10 are chosen from that pool by fit to the profile. We do **not** force a vendor mix in the output; if all 10 best fits are from Amazon (or one vendor), that's acceptable.

## When to implement full unified criteria

- When Etsy (and optionally Awin) are live and we have 3+ vendors returning products: a single criteria spec + parallel/capped requests + “best fit across vendors” in the curator will maximize quality and diversity.
- Optional: criteria could be produced by a small Claude call (“Given this profile, output 5–10 gift search phrases and a price range”) so it’s consistent and editable before any API is called.
