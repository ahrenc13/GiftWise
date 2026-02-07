"""
GIFT CURATOR - Curate Products and Experience Gifts
Selects best-matching products and generates hyper-specific experience gifts

Author: Chad + Claude  
Date: February 2026
"""

import json
import logging

logger = logging.getLogger(__name__)


def curate_gifts(profile, products, recipient_type, relationship, claude_client, rec_count=10, enhanced_search_terms=None, enrichment_context=None):
    """
    Curate gift recommendations from real products and profile.

    Args:
        profile: Recipient profile from build_recipient_profile()
        products: List of real products from search_real_products()
        recipient_type: 'myself' or 'someone_else'
        relationship: Relationship type if someone_else
        claude_client: Anthropic client for AI curation
        rec_count: Number of product recommendations (default 10)
        enhanced_search_terms: Optional list of enhanced search terms from intelligence layer
        enrichment_context: Optional dict with demographics, trending, anti-recs from enrichment engine
    
    Returns:
        Dict with:
        - product_gifts: List of 10 curated products
        - experience_gifts: List of 2-3 hyper-specific experiences
    """
    
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
                        line += f" BUY [{', '.join(do_buy)}]"
                    if dont_buy:
                        line += f" AVOID [{', '.join(dont_buy)}]"
                    interest_intel.append(line)
            if interest_intel:
                parts.append("🎁 PER-INTEREST GUIDANCE:\n" + chr(10).join(interest_intel))

        if parts:
            enrichment_section = "\n\n" + "\n\n".join(parts) + "\n"
    
    # Format profile for prompt (gaps moved to top, rest supporting)
    profile_summary = f"""
RECIPIENT PROFILE:

{sweet_spots}
{enhanced_terms_section}
{enrichment_section}
INTERESTS ({len(profile.get('interests', []))} identified):
{format_interests(profile.get('interests', []))}

LOCATION CONTEXT:
- Lives in: {profile.get('location_context', {}).get('city_region') or 'Unknown'}
- Specific places: {', '.join(profile.get('location_context', {}).get('specific_places', [])[:5])}
- Geographic constraints: {profile.get('location_context', {}).get('geographic_constraints', '')}

STYLE PREFERENCES:
- Visual style: {profile.get('style_preferences', {}).get('visual_style', 'Unknown')}
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
    
    # Format products for prompt
    products_summary = format_products(products)
    
    # Pronoun guidance: "your/you" when recipient is user themselves, "their/they" when buying for someone else
    pronoun_possessive = "your" if recipient_type == 'myself' else "their"
    pronoun_subject = "you" if recipient_type == 'myself' else "they"
    pronoun_context = f"""
RECIPIENT CONTEXT: This is for {"the user themselves (gifts for you)" if recipient_type == 'myself' else "someone else (gifts for them)"}.
- Use "{pronoun_possessive}" and "{pronoun_subject}" in why_perfect and descriptions (e.g. "right up {pronoun_possessive} alley," "something {pronoun_subject}'ve been wanting").
- Use warm, human language. Avoid clinical phrasing like "met their aspiration," "aligns with their interests," "fulfills an aspirational goal," "addresses a gap."
- Prefer: "something {pronoun_subject}'ve been wanting," "right up {pronoun_possessive} alley," "perfect for someone who loves X," "{pronoun_subject}'ll love this because," "a little treat that shows you get them," "fits what {pronoun_subject} are into."
"""
    
    prompt = f"""You are selecting {rec_count} product gifts from a real inventory.

{pronoun_context}

{profile_summary}

{products_summary}

SELECT {rec_count} BEST PRODUCTS from above. Requirements:
- PRIORITIZE products matching GIFT SWEET SPOTS (gaps/aspirational interests) - these are the best opportunities
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
      "name": "SHORT human-friendly name (e.g. 'Taylor Swift Eras Tour Poster' NOT 'Taylor Swift The Eras Tour Official Merch Concert Poster Wall Art Home Decor 24x36 Unframed')",
      "description": "what it is",
      "why_perfect": "DETAILED explanation citing SPECIFIC profile evidence (e.g., 'Based on {pronoun_possessive} 47 Taylor Swift TikToks and visits to Eras Tour watch parties, this captures {pronoun_possessive} Swiftie obsession' not just 'perfect for someone who loves Taylor Swift')",
      "price": "from product",
      "where_to_buy": "domain",
      "product_url": "exact URL from list",
      "confidence_level": "safe_bet|adventurous",
      "gift_type": "physical",
      "interest_match": "interest name"
    }}
  ],
  "experience_gifts": [
    {{
      "name": "specific experience",
      "description": "what/why",
      "why_perfect": "DETAILED explanation citing SPECIFIC profile evidence from 2+ interests/behaviors",
      "location_specific": true/false,
      "location_details": "venue/city or N/A",
      "materials_needed": [{{"item": "", "where_to_buy": "", "product_url": "", "estimated_price": ""}}],
      "how_to_execute": "detailed steps",
      "how_to_make_it_special": "personal touch",
      "reservation_link": "URL or empty",
      "venue_website": "URL or empty",
      "confidence_level": "safe_bet|adventurous",
      "gift_type": "experience"
    }}
  ]
}}

CRITICAL REQUIREMENTS:

PRODUCT GIFTS:
- Product gifts MUST be selected FROM THE INVENTORY ABOVE ONLY. Every product gift must be one of the {len(products)} listed products (use exact URLs from that line). Never invent or reference a product not in the inventory.
- "name" field: Write a SHORT, clean, human-friendly title (3-8 words). Strip model numbers, SEO spam, size specs, and keyword stuffing from marketplace titles. Examples:
  * "DEWALT 20V MAX Cordless Drill/Driver Kit, 1/2-Inch (DCD771C2)" → "DeWalt Cordless Drill Kit"
  * "Breville BES870XL Barista Express Espresso Machine, Brushed Stainless Steel" → "Breville Barista Express Espresso Machine"
  * "Taylor Swift The Eras Tour Official Merch Poster Wall Art 24x36 Unframed" → "Taylor Swift Eras Tour Poster"
- product_url = direct product page ONLY - never search or homepage URLs
- why_perfect MUST cite SPECIFIC evidence from the profile (post counts, venue names, specific behaviors) not generic statements
- PRIORITIZE products matching gaps/aspirational interests over current interests

EXPERIENCE GIFTS:
- Experience gifts MUST be hyper-specific, cite 2+ profile data points in why_perfect with SPECIFIC evidence
- Experience gifts MUST be personal/leisure ONLY - never work-themed, never professional development
- Experience links (reservation_link, venue_website) are LOGISTICS-CRITICAL:
  * MUST be real, bookable venue websites in recipient's city/region ONLY (use "Lives in" and "Specific places")
  * DO NOT INVENT URLs. DO NOT use search pages, generic event finder sites, or placeholder URLs
  * Examples of INVALID links: "https://search.com/venue", "https://eventfinder.com/events", "https://example.com/book", any URL with "search", "find", "discover", "events" in domain
  * If you cannot find a REAL venue website in their area (e.g., "https://bluedoorjazzclub.com", "https://indianapolismuseum.org"), leave reservation_link AND venue_website EMPTY
  * Empty is better than fake - we will supply a geography-calibrated search link
  * For national experiences (not tied to a venue), leave both empty and explain in how_to_execute
- materials_needed: Items the gift-giver needs to BUY IN ADVANCE to prepare or execute this experience. Think: what do they need to purchase before the day arrives?
  * GOOD examples: "Portable Bluetooth speaker" for a picnic, "Dog life jacket" for a lake day, "Watercolor paint set" for an art class
  * BAD examples: "Concert merchandise" (bought AT the event, not in advance), "Commemorative poster" (a souvenir, not a material), "Tickets" (that's the reservation_link, not a material)
  * Each item should be a specific, purchasable product — not a task ("make a playlist"), an abstract concept ("good vibes"), or something bought at the venue
  * When an item matches a product in AVAILABLE PRODUCTS, copy that product's URL exactly into product_url. Never use search URLs. Empty product_url is OK when no match; we will add a find-it link.
  * If the experience doesn't require advance purchases (e.g., a restaurant dinner), use an empty list []
- If no location context, DO NOT suggest location-specific experiences

DIVERSITY & EVIDENCE:
- BRAND DIVERSITY (CRITICAL): NEVER select 2 products from the same brand or manufacturer. If you see "Yankee Candle" twice, pick ONE and replace the other with something different. Same for any brand—one product per brand, no exceptions.
- CATEGORY DIVERSITY: NEVER select 2 products that are essentially the same type of item (e.g., two candles, two mugs, two t-shirts, two posters). Each product should feel like a genuinely different type of gift.
- INTEREST SPREAD: Max 2 products per single interest/theme (e.g., max 2 per band). Spread across at least 5+ distinct interests.
- NOVELTY: Prioritize unique, surprising, and thoughtful gifts over obvious/generic ones. A creative niche product is better than a mass-market default.
- Each recommendation must have SPECIFIC evidence from the profile (not generic "they'll love this")
- Total: {rec_count} product gifts + 3 experience gifts (we will filter to keep 2-3)
- Every product gift product_url MUST be an exact copy of a URL from the INVENTORY list above - no invented products, no search pages.

{relationship_context}

Return ONLY the JSON object, no markdown, no backticks"""
    
    try:
        # Call Claude for curation
        logger.info("Calling Claude API for gift curation...")
        
        message = claude_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=12000,
            messages=[{"role": "user", "content": prompt}],
            timeout=120.0
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
        
        logger.info(f"Curated {len(curated_gifts.get('product_gifts', []))} products + {len(curated_gifts.get('experience_gifts', []))} experiences")
        
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
        domain = p.get('source_domain', 'unknown')
        interest = p.get('interest_match', 'general')
        formatted.append(f"{idx}. {title}\n   Price: {price} | Domain: {domain} | Interest match: {interest}\n   Description: {snippet[:150]}\n   URL: {link}")
    
    return '\n\n'.join(formatted[:50])  # Limit to 50 products in prompt
