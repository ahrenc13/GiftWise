"""
GIFT CURATOR - Curate Products and Experience Gifts
Selects best-matching products and generates hyper-specific experience gifts

⚠️  OPUS-ONLY ZONE — NO EXCEPTIONS ⚠️
The prompt text in this file is the engine's taste layer. The following sections
were carefully tuned and must NOT be modified by Sonnet sessions:
  - GIFT REASONING FRAMEWORK (the 4-step ownership/adjacency/identity/surprise logic)
  - SELECTION PRINCIPLE (aspiration gap philosophy)
  - SYNTHESIS OVER CHECKLIST paragraph
  - ALREADY OWNS / ownership_section builder
  - Pronoun guidance and warm-language instructions
  - aesthetic_summary wiring in STYLE PREFERENCES
If you're Sonnet and see a quality problem in recommendations, DOCUMENT IT as a
code comment prefixed with "# SONNET-FLAG:" near the relevant prompt section.
Do not reword, reorder, or add instructions to the prompt. Opus will review.

Safe for any session: bug fixes (crashes, missing fields, format errors), adding
new product fields to the JSON schema, fixing template rendering issues.

Author: Chad + Claude
Date: February 2026
"""

import json
import logging

logger = logging.getLogger(__name__)


def curate_gifts(profile, products, recipient_type, relationship, claude_client, rec_count=10, enhanced_search_terms=None, enrichment_context=None, model=None, ontology_briefing=None, splurge_candidates=None):
    """
    Curate gift recommendations from real products and profile.

    Args:
        profile: Recipient profile from build_recipient_profile()
        products: List of real products from search_real_products()
        recipient_type: 'myself' or 'someone_else'
        relationship: Relationship type if someone_else
        claude_client: Anthropic client for AI curation
        rec_count: Number of product recommendations (default 10, +1 splurge when splurge_candidates present)
        enhanced_search_terms: Optional list of enhanced search terms from intelligence layer
        enrichment_context: Optional dict with demographics, trending, anti-recs from enrichment engine
        model: Claude model ID (default: claude-sonnet-4-20250514)
        splurge_candidates: Optional list of premium products ($200-$1500) for the splurge slot

    Returns:
        Dict with:
        - product_gifts: List of curated products (10 regular + 1 splurge when available)
        - experience_gifts: List of 2-3 hyper-specific experiences
    """
    # Compute splurge ceiling from profile budget category
    _SPLURGE_CEILING = {'budget': 300, 'moderate': 500, 'premium': 1000, 'luxury': 1500}
    budget_category = (profile.get('price_signals') or {}).get('budget_category', 'unknown')
    splurge_ceiling = _SPLURGE_CEILING.get(budget_category, 500)
    has_splurge = bool(splurge_candidates)

    if not model:
        model = "claude-sonnet-4-20250514"

    if not products:
        logger.error("No products to curate from")
        return {"product_gifts": [], "experience_gifts": []}
    
    logger.info(f"Selecting {rec_count} gifts from inventory of {len(products)} real products (inventory is {len(products)//max(rec_count,1)}x selection count)")
    
    # Build curation prompt
    # Import relationship rules
    from relationship_rules import get_relationship_guidance
    
    relationship_context = ""
    if recipient_type == 'someone_else' and relationship:
        # Get detailed relationship-specific rules
        relationship_context = get_relationship_guidance(relationship)
    
    # Extract aspirational/current/gaps for emphasis
    asp_curr = profile.get('aspirational_vs_current', {})
    gaps = asp_curr.get('gaps', [])[:5]
    aspirational = asp_curr.get('aspirational', [])[:5]
    current = asp_curr.get('current', [])[:5]
    
    # Build GIFT SWEET SPOTS section (lead with this!)
    sweet_spots = ""
    if gaps:
        sweet_spots = f"""
🎯 GIFT SWEET SPOTS - THE BEST OPPORTUNITIES (PRIORITIZE THESE):
{chr(10).join([f"- {gap}" for gap in gaps])}

These represent things they're interested in but don't have yet - the perfect gift zone where you can help them level up or try something new. Products matching these gaps should be HEAVILY WEIGHTED in your selection.

Context:
- What they currently have/do: {', '.join(current)}
- What they're aspiring to: {', '.join(aspirational)}
"""
    else:
        sweet_spots = f"""
🎯 WHAT THEY'RE INTO:
- Current interests: {', '.join(current + aspirational)[:8]}
"""
    
    # Add enhanced search terms if available
    enhanced_terms_section = ""
    if enhanced_search_terms:
        enhanced_terms_section = f"""
🔍 INTELLIGENCE-ENHANCED SEARCH TERMS (prefer products matching these):
{', '.join(enhanced_search_terms[:10])}

These are refined search terms from deep profile analysis - products matching these are likely to be especially good fits.
"""

    # Add enrichment intelligence (demographics, trending, anti-recs)
    enrichment_section = ""
    if enrichment_context:
        parts = []

        demo = enrichment_context.get('demographics', {})
        if demo and demo.get('demographic_bucket'):
            demo_lines = []
            if demo.get('gift_style'):
                demo_lines.append(f"Gift style: {demo['gift_style']}")
            if demo.get('popular_categories'):
                demo_lines.append(f"Popular for this demo: {', '.join(demo['popular_categories'][:6])}")
            if demo.get('avoid'):
                demo_lines.append(f"Avoid for this demo: {', '.join(demo['avoid'][:5])}")
            if demo.get('price_preference'):
                demo_lines.append(f"Typical budget: ${demo['price_preference'][0]}-${demo['price_preference'][1]}")
            if demo_lines:
                parts.append("👤 DEMOGRAPHIC INSIGHT ({}):\n{}".format(
                    demo['demographic_bucket'], chr(10).join(['  - ' + l for l in demo_lines])))

        trending = enrichment_context.get('trending_items', [])
        if trending:
            parts.append(f"📈 TRENDING IN 2026: {', '.join(str(t) for t in trending[:8])}")

        anti_recs = enrichment_context.get('anti_recommendations', [])
        if anti_recs:
            parts.append(f"🚫 AVOID THESE GIFT TYPES: {', '.join(str(a) for a in anti_recs[:8])}")

        price_g = enrichment_context.get('price_guidance', {})
        if price_g and price_g.get('guidance'):
            parts.append(f"💰 PRICE GUIDANCE: {price_g['guidance']}")

        enriched_interests = enrichment_context.get('enriched_interests', [])
        if enriched_interests:
            interest_intel = []
            for ei in enriched_interests[:8]:
                name = ei.get('interest', '')
                do_buy = ei.get('do_buy', [])[:3]
                dont_buy = ei.get('dont_buy', [])[:3]
                if do_buy or dont_buy:
                    line = f"  {name}:"
                    if do_buy:
                        line += f" SEEK [{', '.join(do_buy)}]"
                    if dont_buy:
                        line += f" SKIP [{', '.join(dont_buy)}]"
                    interest_intel.append(line)
            if interest_intel:
                parts.append("🎁 PER-INTEREST GIFT STRATEGY (same category can appear in both SEEK and SKIP — the difference is specificity and quality, not the category itself):\n" + chr(10).join(interest_intel))

        if parts:
            enrichment_section = "\n\n" + "\n\n".join(parts) + "\n"
    
    # Extract recipient city for location-aware instructions
    recipient_city = (profile.get('location_context') or {}).get('city_region') or 'Unknown'

    # Build ontology section if available
    ontology_section = ""
    if ontology_briefing:
        ontology_section = f"\n{ontology_briefing}\n"

    # Build ownership signals section
    ownership_section = ""
    ownership_signals = profile.get('ownership_signals', [])
    if ownership_signals:
        ownership_section = f"\nALREADY OWNS (do NOT recommend these or near-duplicates — recommend upgrades or complements instead):\n{', '.join(ownership_signals[:15])}\n"

    # Format profile for prompt (gaps moved to top, rest supporting)
    profile_summary = f"""
RECIPIENT PROFILE:

{sweet_spots}
{enhanced_terms_section}
{enrichment_section}
{ontology_section}
{ownership_section}
INTERESTS ({len(profile.get('interests', []))} identified):
{format_interests(profile.get('interests', []))}

LOCATION CONTEXT:
- Lives in: {profile.get('location_context', {}).get('city_region') or 'Unknown'}
- Specific places: {', '.join(profile.get('location_context', {}).get('specific_places', [])[:5])}
- Geographic constraints: {profile.get('location_context', {}).get('geographic_constraints', '')}

STYLE PREFERENCES:
- Visual style: {profile.get('style_preferences', {}).get('visual_style', 'Unknown')}
- Aesthetic: {profile.get('style_preferences', {}).get('aesthetic_summary', '')}
- Preferred brands: {', '.join(profile.get('style_preferences', {}).get('brands', [])[:5])}
- Quality level: {profile.get('style_preferences', {}).get('quality_level', 'Unknown')}

PRICE SIGNALS:
- Comfortable range: {profile.get('price_signals', {}).get('estimated_range', 'Unknown')}
- Budget category: {profile.get('price_signals', {}).get('budget_category', 'Unknown')}

GIFT_AVOID (do not suggest): {', '.join(profile.get('gift_avoid', [])[:8]) or 'None specified'}

WORKPLACE (NEVER suggest experiences or "behind the scenes" at these - they work there!):
{_format_work_venues(profile)}

SPECIFIC VENUES/PLACES:
{format_venues(profile.get('specific_venues', []))}
"""
    
    # Opus fix: hallucination grounding (Mar 3 2026)
    # Format products for prompt — numbered items serve as inventory_id anchors
    products_summary = f"━━━ PRODUCT INVENTORY ({len(products)} items) — ONLY PICK FROM THIS LIST ━━━\n\n" + format_products(products) + "\n\n━━━ END OF INVENTORY — every product gift must reference an item number above ━━━"

    # Append splurge candidates section if available (wired Apr 2026).
    # These are higher-priced items ($200-$1500) from the catalog DB, separated from the
    # regular pool. The curator can reference them when designating the SPLURGE PICK.
    # Opus task: update the SPLURGE PICK instruction to explicitly prefer items from this section.
    if splurge_candidates:
        splurge_formatted = format_products(splurge_candidates)
        products_summary += f"\n\n━━━ SPLURGE CANDIDATES ($200-$1500) ━━━\n\n{splurge_formatted}\n\n━━━ END SPLURGE CANDIDATES ━━━"
    
    # Pronoun guidance: "your/you" when recipient is user themselves, "their/they" when buying for someone else
    pronoun_possessive = "your" if recipient_type == 'myself' else "their"
    pronoun_subject = "you" if recipient_type == 'myself' else "they"
    pronoun_context = f"""
RECIPIENT CONTEXT: This is for {"the user themselves (gifts for you)" if recipient_type == 'myself' else "someone else (gifts for them)"}.
- Use "{pronoun_possessive}" and "{pronoun_subject}" in why_perfect and descriptions (e.g. "right up {pronoun_possessive} alley," "something {pronoun_subject}'ve been wanting").
- Use warm, human language. Avoid clinical phrasing like "met their aspiration," "aligns with their interests," "fulfills an aspirational goal," "addresses a gap."
- Prefer: "something {pronoun_subject}'ve been wanting," "right up {pronoun_possessive} alley," "perfect for someone who loves X," "{pronoun_subject}'ll love this because," "a little treat that shows you get them," "fits what {pronoun_subject} are into."
"""
    
    # Build splurge instruction block (only when splurge candidates exist)
    splurge_instruction = ""
    splurge_total_line = f"{rec_count} product gifts"
    if has_splurge:
        splurge_instruction = f"""
SPLURGE SLOT (1 additional pick — SEPARATE from your {rec_count} regular picks):
Pick the single most impressive gift from the SPLURGE CANDIDATES section above. This is the "if money were no object" pick — the nicest version of something {pronoun_subject} love, or a truly extraordinary item that matches {pronoun_possessive} strongest interest. Price ceiling: ${splurge_ceiling}. Set "is_splurge": true for this one product only, false for all others.
- MUST come from the SPLURGE CANDIDATES section (not the regular inventory)
- Should feel aspirational — a meaningful upgrade, not just an expensive version of a basic item
- If none of the splurge candidates are a good fit for the profile, pick the BEST one anyway and explain why in why_perfect
- The splurge pick is item #{rec_count + 1} in your product_gifts array (after the {rec_count} regular picks)
"""
        splurge_total_line = f"{rec_count} regular product gifts + 1 SPLURGE pick"

    prompt = f"""You are selecting {splurge_total_line} from a real inventory.

{pronoun_context}

{profile_summary}

{products_summary}

SELECT {rec_count} BEST PRODUCTS from the main inventory above{" PLUS 1 SPLURGE PICK from the splurge candidates" if has_splurge else ""}. Requirements:

SELECTION PRINCIPLE: The best gift fills an aspiration gap — something they WANT but don't yet HAVE. A gift matching a current interest risks duplicating what they own. A gift matching an aspiration makes them say "how did you KNOW?" At least 60% of your picks should target gaps/aspirational interests, not current ones.

SYNTHESIS OVER CHECKLIST: A gift set built by mapping one product to each interest is a spreadsheet, not a gift. The best sets find products at the INTERSECTION of two or more interests, or express familiar interests through unexpected forms.

GIFT REASONING FRAMEWORK — follow these steps for EVERY pick:
1. **Ownership check:** If the ALREADY OWNS section lists something similar, recommend the UPGRADE or the COMPLEMENT instead.
2. **Adjacency reasoning:** For each interest, consider what's ONE STEP AWAY. Someone who likes cooking doesn't need another cookbook — they might love artisan ingredients, a hand-forged knife, or a foraging workshop. Someone into music doesn't need a band poster — they might love a listening equipment upgrade or a concert experience.
3. **Identity signal matching:** Social media is identity performance. Gifts that let someone EXPRESS their identity in new ways convert better than direct-interest products. A dog person doesn't just want dog stuff — they want the thing that makes visitors say "oh you really love dogs" in a new way.
4. **The "they'd never buy this for themselves" test:** The best gifts are slightly outside their normal purchasing behavior but perfectly aligned with who they are. It should make someone feel KNOWN, not CATEGORIZED.

Before finalizing each pick, ask:
1. Can one product bridge TWO of their interests? (e.g., music + dogs → dog breed tote with band-style art, not a band poster AND a dog toy separately)
2. Am I defaulting to the most obvious product form? Band → poster. Coffee lover → mug. Reader → book. If yes, justify it or find something more specific and surprising.
3. Am I stacking the same product type across multiple interests? (three posters, three shirts, three mugs?) If so, you're repeating a form, not adding variety. Use each form at most once.

FOR MUSIC-HEAVY PROFILES: Do NOT pick a poster for each artist they like. Pick at most ONE poster for their top artist. Express the rest of the music passion through different forms — concert-ready accessories, music-themed apparel, instruments/gear, listening equipment, or a curated experience. A wall of band posters is a record store, not a gift set.

{splurge_instruction if has_splurge else '- SPLURGE PICK: Designate exactly ONE product as the "splurge pick" — an aspirational gift above ' + pronoun_possessive + ' typical budget but perfectly matched to ' + pronoun_possessive + ' strongest interest. Set "is_splurge": true for that one product only, false for all others. The splurge pick should make someone think "I would never buy this for myself, but I would LOVE it." It should be a meaningful upgrade, not just an expensive version of a basic item.'}
- PRIORITIZE products matching GIFT SWEET SPOTS (gaps/aspirational interests) - these are the best opportunities
- If the profile includes EXPLICIT WANT SIGNALS (phrases like "I need this", "someone buy me"), treat those as your highest-priority targets
- Match interests with SPECIFIC profile evidence (cite posts, behaviors, venues)
- Max 2 products per interest (spread across 5+ interests)
- Use exact URLs from product list
- Only direct product links (no search URLs)
- SOURCE PRIORITY: Prefer Etsy/eBay/Awin over Amazon when quality is comparable (Amazon is fallback only)

ALSO: Generate 3 hyper-specific experience gifts synthesizing 2+ profile elements.

Return JSON:
{{
  "product_gifts": [
    {{
      "inventory_id": <item number from the inventory list above (1-{len(products)})>,
      "name": "SHORT human-friendly name (e.g. 'Taylor Swift Eras Tour Poster' NOT 'Taylor Swift The Eras Tour Official Merch Concert Poster Wall Art Home Decor 24x36 Unframed')",
      "description": "what it is",
      "why_perfect": "DETAILED explanation citing SPECIFIC profile evidence (e.g., 'Based on {pronoun_possessive} 47 Taylor Swift TikToks and visits to Eras Tour watch parties, this captures {pronoun_possessive} Swiftie obsession' not just 'perfect for someone who loves Taylor Swift')",
      "where_to_buy": "domain",
      "product_url": "exact URL from the item's URL field above",
      "confidence_level": "safe_bet|adventurous",
      "is_splurge": false,
      "gift_type": "physical",
      "interest_match": "interest name"
    }}
  ],
  "experience_gifts": [
    {{
      "name": "SHORT, specific experience name (e.g. 'Couples Thai Cooking Class' not 'Cooking Experience')",
      "description": "1-2 sentence pitch: what this experience IS and what makes it special. Write it like you're selling someone on the idea.",
      "why_perfect": "2-3 sentences citing SPECIFIC profile evidence from 2+ interests/behaviors. Tell a mini-story connecting {pronoun_possessive} interests to this experience.",
      "experience_category": "one of: cooking_class|art_class|concerts|sports_events|travel|spa_wellness|outdoor_adventure|wine_beer|fitness_class|museum_culture|dining|pet_experience|other",
      "estimated_price": "$XX-$YY (realistic total including materials)",
      "location_specific": true/false,
      "location_details": "city/neighborhood or N/A",
      "materials_needed": [{{"item": "specific purchasable product name", "estimated_price": "$XX"}}],
      "how_to_execute": "Step-by-step plan in 3-5 short sentences. Be specific enough that the gift-giver can ACT on this immediately.",
      "how_to_make_it_special": "One specific personal touch that connects to {pronoun_possessive} profile",
      "confidence_level": "safe_bet|adventurous",
      "gift_type": "experience"
    }}
  ]
}}

CRITICAL REQUIREMENTS:

PRODUCT GIFTS:
- INVENTORY GROUNDING: You MUST select from the numbered inventory list above. For each pick, set `inventory_id` to the item number (1-{len(products)}) and copy the URL from that item's URL field. If you cannot point to a specific item number, you are hallucinating a product that does not exist — pick a different item that IS in the list.
- "name" field: Write a SHORT, clean, human-friendly title (3-8 words). Strip model numbers, SEO spam, size specs, and keyword stuffing from marketplace titles. Examples:
  * "DEWALT 20V MAX Cordless Drill/Driver Kit, 1/2-Inch (DCD771C2)" → "DeWalt Cordless Drill Kit"
  * "Breville BES870XL Barista Express Espresso Machine, Brushed Stainless Steel" → "Breville Barista Express Espresso Machine"
  * "Taylor Swift The Eras Tour Official Merch Poster Wall Art 24x36 Unframed" → "Taylor Swift Eras Tour Poster"
- product_url = direct product page ONLY - never search or homepage URLs
- why_perfect MUST cite SPECIFIC evidence from the profile (post counts, venue names, specific behaviors) not generic statements
- PRIORITIZE products matching gaps/aspirational interests over current interests
- SKIP used/pre-owned items, generic "mix & match" bundles, and bulk packs of cheap items. Every gift should feel intentional, not like a clearance bin find
- TICKET PRODUCTS: If a product is event tickets, concert tickets, or sports tickets for a specific city, ONLY select it if that city matches the recipient's city ("{recipient_city}"). Tickets for Boston, Buffalo, or any other city are worthless to someone in {recipient_city}. Skip wrong-city tickets entirely — use an experience gift for the artist/event instead.

EXPERIENCE GIFTS:
- Each experience must be a COHERENT PACKAGE: an activity + the materials to pull it off + a clear plan.
  Think of it as a gift box: "Here's what we're doing, here's what you need to buy, here's how to book it."
- NARRATIVE QUALITY: why_perfect must tell a mini-story connecting 2+ profile data points.
  BAD: "Matches their passion for cooking and travel."
  GOOD: "Based on {pronoun_possessive} 12 Thai food posts and that Bangkok trip bucket list, this hands-on class lets {pronoun_subject} recreate those pad thai cravings at home — plus {pronoun_subject}'ve been following 3 cooking accounts lately."
- description should SELL the experience in 1-2 punchy sentences. Not a dry summary.
  BAD: "A cooking class focused on Thai cuisine."
  GOOD: "Learn to make authentic pad thai and green curry from scratch — then eat everything you made with a glass of wine."

BOOKABLE vs. DIY — PICK THE RIGHT TYPE:
There are two valid experience types. Match the category to what can actually be delivered:

  BOOKABLE experiences (use specific categories: cooking_class, art_class, dining, spa_wellness, wine_beer, fitness_class, outdoor_adventure, museum_culture):
  These exist on-demand in virtually any city. Someone can go to Cozymeal/OpenTable/ClassPass right now and book them.
  Examples: Thai cooking class, pottery workshop, wine tasting, spa day, guided hike, jazz dinner

  DIY/PLAN-YOURSELF experiences (use category: other):
  The gift-giver creates the experience with advance purchases — no external booking needed.
  These are always reliable because they don't depend on a show existing or a class being offered.
  Examples: Themed listening party, backyard concert setup, movie marathon night, record store crawl
  Use category "other" for ALL of these. Do NOT use "concerts" for DIY music experiences.

CONCERTS RULE — BE HONEST ABOUT WHAT CAN BE BOOKED:
  ONLY use experience_category "concerts" if the artist is a well-known act who actively tours arenas or major venues (Taylor Swift, Beyoncé, Bruce Springsteen, etc.) — someone for whom tickets are likely available on Ticketmaster right now or in the near future.
  DO NOT use "concerts" for:
  - Tribute bands (e.g. "ELO Tribute Band Night") — these depend on a specific show existing in a specific city, which is highly unlikely and unverifiable
  - Niche or legacy artists who rarely tour
  - DIY backyard/home music events
  - "Music festival setup" or any self-organized event
  Instead, for music-interest profiles where a real concert is uncertain: suggest a THEMED LISTENING PARTY (category: other) with specific materials (quality Bluetooth speaker, artist poster, themed snacks), or a CONCERT FUND experience where the gift-giver sets aside money specifically for when the artist announces a tour.

- experience_category: Pick the category that determines HOW this gets booked. This directly controls what booking platforms we show. Wrong category = wrong links.
  - cooking_class, art_class, dining, spa_wellness, wine_beer, fitness_class, outdoor_adventure, museum_culture, concerts, sports_events → bookable, we show booking platform links
  - other → DIY, no external booking, just materials and a plan. Use this for themed home events, listening parties, backyard experiences.
- estimated_price: Be realistic. Include the class/tickets/booking fee AND materials.
- DO NOT include reservation_link or venue_website — we handle booking links automatically based on category. You focus on the WHAT and WHY, we handle the WHERE.
- materials_needed: Items the gift-giver buys IN ADVANCE to prepare or elevate the experience.
  * GOOD: "Watercolor paint set" for an art class, "Portable Bluetooth speaker" for a listening party, "Dog life jacket" for a lake day
  * BAD: "Water bottles" (everyone has these), "Tickets" (that's the booking, not a material), "Concert merch" (bought at the event), "Good vibes" (not a product)
  * NEVER suggest vinyl records, CDs, DVDs, or Blu-rays as materials — assume the recipient streams music and movies on Spotify/Apple Music/Netflix. The only exception: if the profile explicitly lists vinyl collecting, record collecting, or physical media as a stated passion.
  * Only include item name + estimated_price. We match products and add links automatically.
  * If the experience needs no advance purchases (e.g., restaurant dinner), use an empty list []
- how_to_execute: Write 3-5 SHORT sentences the gift-giver can act on. Be specific: "Search Cozymeal for Thai cooking classes in {recipient_city}" not "Find a local cooking class."
- MUST be personal/leisure ONLY — never work-themed, never professional development
- If no location context in profile, DO NOT suggest location-specific bookable experiences (use DIY/other instead)
- CONCERT/SHOW NAMES: NEVER include a distant city name in an experience. Write "Chappell Roan Concert Night" not "Chappell Roan at Madison Square Garden". We automatically generate ticket search links for the recipient's city ({recipient_city}).

GIFT TASTE — REJECT BORING PRACTICAL ITEMS:
A gift should make someone say "you GET me," not "thanks, I needed that." REJECT these categories entirely:
- Power adapters, converters, chargers, extension cords, cable organizers
- First aid kits, medicine organizers, pill cases
- Luggage tags, packing cubes, toiletry bags (unless luxury/designer)
- Phone stands, generic tech accessories, screen protectors
- Bulk packs, multi-packs, "essentials kits," variety packs
- Plain storage containers, drawer organizers, label makers
If an item is something people buy for themselves at a drugstore or airport, it is NOT a gift. Gifts are personal, thoughtful, and a little surprising.

GIFTING TROPES — REQUIRE DIRECT JUSTIFICATION:
Chocolate boxes, wine/gift baskets, and flower arrangements are last-resort defaults that signal low effort. They appear in the inventory because some profiles genuinely love these things — but "genuinely" means a direct, specific signal:
- Chocolate: they explicitly follow chocolate/dessert/pastry accounts, post about confectionery, or love French food. A "foodie" or "entertaining" interest is NOT sufficient.
- Wine or gift baskets: they are an actual wine enthusiast (wine tasting, winery visits, sommelier content) or explicitly love cheese/charcuterie. "Hosting" or "social" interests are NOT sufficient.
- Baby baskets: only if the profile has an explicit baby shower or new parent signal.
If a profile has these items in inventory but no direct justification, skip them and find the more specific, personal gift. A hiking enthusiast who also happens to like good food should get hiking gear, not a gourmet basket.

DIVERSITY & EVIDENCE:
- BRAND DIVERSITY (CRITICAL): NEVER select 2 products from the same brand or manufacturer. If you see "Yankee Candle" twice, pick ONE and replace the other with something different. Same for any brand—one product per brand, no exceptions.
- CATEGORY DIVERSITY: NEVER select 2 products that are essentially the same type of item (e.g., two candles, two mugs, two t-shirts, two posters). Each product should feel like a genuinely different type of gift.
- FORM DIVERSITY: Limit to 1 poster, 1 apparel item, 1 book — full stop, regardless of how many interests are present. If you have 6 music interests and 6 posters in the inventory, pick ONE poster. Express the other 5 interests through different product forms.
- INTEREST SPREAD: Max 2 products per single interest/theme (e.g., max 2 per band). Spread across at least 5+ distinct interests.
- NOVELTY: Prioritize unique, surprising, and thoughtful gifts over obvious/generic ones. A creative niche product is better than a mass-market default.
- Each recommendation must have SPECIFIC evidence from the profile (not generic "they'll love this")
- Total: {splurge_total_line} + 3 experience gifts (we will filter to keep 2-3)
- Every product gift MUST reference a real inventory item by number. Copy the URL exactly from that item — no invented products, no search pages.

BEFORE RETURNING YOUR JSON — SELF-CHECK (do this mentally for every product gift):
1. Verify inventory_id: does item #{{"inventory_id"}} in the list above exist? Does its URL match your product_url?
2. If the inventory_id is out of range or the URL doesn't match, REPLACE this pick with an actual inventory item.
3. Hallucinated products (not in the list) are silently dropped, wasting a recommendation slot.
Common failure mode: reasoning toward the "ideal" gift first, then inventing a product. Instead, BROWSE the inventory list and select FROM it — don't imagine the perfect product and try to find it.

{relationship_context}

Return ONLY the JSON object, no markdown, no backticks"""
    
    try:
        # Call Claude for curation
        logger.info("Calling Claude API for gift curation (model=%s)...", model)

        message = claude_client.messages.create(
            model=model,
            max_tokens=8192,
            messages=[{"role": "user", "content": prompt}],
            timeout=300.0
        )

        # Check if response was truncated (would lose experience gifts at end of JSON)
        if message.stop_reason == 'max_tokens':
            logger.warning("Curator response was TRUNCATED (hit max_tokens) — experiences may be missing")

        # Extract response
        response_text = ""
        for block in message.content:
            if block.type == "text":
                response_text += block.text
        
        response_text = response_text.strip()
        
        # Remove markdown if present
        if response_text.startswith('```'):
            response_text = response_text.split('```')[1]
            if response_text.startswith('json'):
                response_text = response_text[4:]
            response_text = response_text.strip()
        
        # Parse JSON
        curated_gifts = json.loads(response_text)

        # Separate splurge item from regular product gifts.
        # The curator places is_splurge=true on exactly one product.
        product_gifts = curated_gifts.get('product_gifts', [])
        splurge_item = None
        regular_gifts = []
        for gift in product_gifts:
            if gift.get('is_splurge'):
                if splurge_item is None:
                    splurge_item = gift
                    logger.info(f"Splurge pick identified: {gift.get('name', 'unknown')} (${gift.get('price', '?')})")
                else:
                    # Multiple splurge flags — keep only the first, demote the rest
                    gift['is_splurge'] = False
                    regular_gifts.append(gift)
            else:
                regular_gifts.append(gift)

        curated_gifts['product_gifts'] = regular_gifts
        curated_gifts['splurge_item'] = splurge_item

        logger.info(
            f"Curated {len(regular_gifts)} regular products + "
            f"{'1 splurge' if splurge_item else 'no splurge'} + "
            f"{len(curated_gifts.get('experience_gifts', []))} experiences"
        )

        return curated_gifts
        
    except Exception as e:
        logger.error(f"Error curating gifts: {e}", exc_info=True)
        return {"product_gifts": [], "experience_gifts": []}


def _format_work_venues(profile):
    """Extract work venues from profile (interests where is_work=true) for curator to avoid."""
    import re
    venues = []
    for i in profile.get('interests', []):
        if not i.get('is_work'):
            continue
        desc = (i.get('description') or i.get('evidence', '')).lower()
        name = i.get('name', '').lower()
        if 'works at' in desc or 'work at' in desc:
            m = re.search(r'works? (?:at|for) ([a-z0-9\s]+?)(?:\.|,|;|$)', desc)
            if m:
                venues.append(m.group(1).strip())
        if name and name not in venues:
            venues.append(name)
    if not venues:
        return "None identified"
    return ", ".join(venues[:10])


def format_interests(interests):
    """Format interests list for prompt"""
    if not interests:
        return "None identified"
    
    formatted = []
    for i in interests:
        name = i.get('name', 'Unknown')
        evidence = i.get('evidence') or i.get('description', '')
        intensity = i.get('intensity', 'moderate')
        interest_type = i.get('type', 'current')
        
        formatted.append(f"- {name} ({intensity}, {interest_type}): {evidence}")
    
    return '\n'.join(formatted[:15])  # Limit to top 15


def format_venues(venues):
    """Format specific venues for prompt"""
    if not venues:
        return "None identified"
    
    formatted = []
    for v in venues:
        name = v.get('name', 'Unknown')
        venue_type = v.get('type', 'venue')
        evidence = v.get('evidence', '')
        location = v.get('location', 'Location unknown')
        
        formatted.append(f"- {name} ({venue_type}) in {location}: {evidence}")
    
    return '\n'.join(formatted[:10])  # Limit to top 10


def format_products(products):
    """Format products list for prompt"""
    if not products:
        return "No products available"
    
    formatted = []
    for idx, p in enumerate(products, 1):
        title = p.get('title', 'Unknown')
        link = p.get('link', '')
        snippet = p.get('snippet', '')
        price = p.get('price', 'Price unknown')
        raw_domain = p.get('source_domain', 'unknown')
        # Don't expose marketplace backend names to the curator — they bias selection
        # toward or against products based on network rather than gift quality.
        _mktplace = {'tiktok shop', 'cj affiliate', 'cj', 'shareasale', 'unknown'}
        brand = p.get('brand', '')
        if raw_domain.lower() in _mktplace:
            domain = brand.strip().title() if brand else 'Online Shop'
        else:
            domain = raw_domain
        interest = p.get('interest_match', 'general')
        formatted.append(f"{idx}. {title}\n   Price: {price} | Domain: {domain} | Interest match: {interest}\n   Description: {snippet[:100]}\n   URL: {link}")
    
    return '\n\n'.join(formatted[:50])  # Limit to 50 products in prompt
