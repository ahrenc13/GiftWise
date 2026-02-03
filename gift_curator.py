"""
GIFT CURATOR - Curate Products and Experience Gifts
Selects best-matching products and generates hyper-specific experience gifts

Author: Chad + Claude  
Date: February 2026
"""

import json
import logging

logger = logging.getLogger(__name__)


def curate_gifts(profile, products, recipient_type, relationship, claude_client, rec_count=10):
    """
    Curate gift recommendations from real products and profile.
    
    Args:
        profile: Recipient profile from build_recipient_profile()
        products: List of real products from search_real_products()
        recipient_type: 'myself' or 'someone_else'
        relationship: Relationship type if someone_else
        claude_client: Anthropic client for AI curation
        rec_count: Number of product recommendations (default 10)
    
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
    
    # Format profile for prompt
    profile_summary = f"""
RECIPIENT PROFILE:

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

ASPIRATIONAL VS. CURRENT:
- Aspirational (wants): {', '.join(profile.get('aspirational_vs_current', {}).get('aspirational', [])[:5])}
- Current (has): {', '.join(profile.get('aspirational_vs_current', {}).get('current', [])[:5])}
- Gaps to fill (prioritize these): {', '.join(profile.get('aspirational_vs_current', {}).get('gaps', [])[:5])}

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
    
    prompt = f"""You are an expert gift curator. You have a deep profile of the recipient and {len(products)} REAL products to choose from.

{profile_summary}{relationship_context}{pronoun_context}

INVENTORY – AVAILABLE PRODUCTS ({len(products)} real products with actual purchase links):
{products_summary}

YOUR TASK:
1. SELECT the BEST {rec_count} products FROM THIS INVENTORY ONLY. You have {len(products)} real options; choose the {rec_count} that match this person's profile best. Do not invent or reference products not in the list.
2. Generate 2-3 HYPER-SPECIFIC experience gift ideas (see EXPERIENCE section below). For materials_needed, prefer products from this same inventory when they fit.

TASTE CALIBRATION (CRITICAL):
- Avoid gifts that feel like the first Google result for "gift for X". Aim for thoughtful, human choices.
- Prefer items that show real familiarity with the interest (specific brands, niches, or experiences). If the best match is slightly unexpected, explain the connection clearly in why_perfect.
- Include at least 1-2 "adventurous" picks (confidence_level: adventurous) that are clearly linked to their interests but not obvious—and always cite profile evidence for why it fits.
- why_perfect MUST cite specific profile evidence (interest name, post, or behavior)—never generic fluff.
- Respect GIFT_AVOID: do not suggest anything that fits those categories.
- If quality_level or budget_category is present, match it; when in doubt, prefer one notch above generic (thoughtful mid-range over basic).

PRODUCT SELECTION CRITERIA:
- Match products to specific interests with evidence
- Ensure diverse coverage (don't pick 10 similar items)
- Prioritize GAPS and ASPIRATIONAL interests (things they want but don't have)
- Consider relationship appropriateness
- Prefer unique, specialty items over generic mass-market products
- Stay within their comfortable price range
- No square pegs in round holes - only include perfect matches

LINK AND IMAGE RULES (CRITICAL):
- product_url MUST be a DIRECT link to the actual product page from AVAILABLE PRODUCTS. Copy the URL field exactly.
- NEVER use a search URL (e.g. etsy.com/search?q=..., amazon.com/s?k=...) or a bare homepage (etsy.com, amazon.com). If the only URL in the list for an item is a search page, do NOT pick that item—choose a different product that has a direct listing URL.
- image_url MUST be the EXACT Image URL from that same product's line in AVAILABLE PRODUCTS. Never use an image from a different product—wrong image + right link = bad experience.

EXPERIENCE GIFT CRITERIA (CRITICAL):
- NEVER suggest an experience at their WORKPLACE (see WORKPLACE above). No "behind the scenes", "tour", "VIP access", or tickets to a venue where they work—that would be a clunker (they're already there).
- Experiences are actions or moments you create for the recipient—guided by what we know about them. The gift-giver needs clear steps and everything they need to make it happen.
- Each experience MUST synthesize at least 2 distinct profile data points (interests + location, or gaps + venues, or aspirational + style). why_perfect must name those data points.
- If location-specific: use their actual city/region or specific venues from their profile—but NEVER a venue listed in WORKPLACE. If no location context, only suggest portable/at-home experiences—never invent a location.
- materials_needed: List concrete items the gift-giver should buy. For each item that matches something in AVAILABLE PRODUCTS, you MUST set product_url to that product's exact URL and where_to_buy to its domain—so the gift-giver can click and buy. If no matching product in the list, leave product_url empty (we will add a find-it link). Include estimated_price for each item. This makes the experience turnkey.
- how_to_execute: Step-by-step for the gift-giver (what to book/buy, when, how to present it). Be specific so they can follow it without guessing.
- how_to_make_it_special: 1-2 sentences—e.g. how to frame it when giving, a small touch that shows thoughtfulness, or why this will feel memorable to the recipient.
- reservation_link: REQUIRED for restaurant/venue experiences. Provide a DIRECT link: OpenTable, Resy, Tock, or the venue's reservation page IN THE RECIPIENT'S AREA (see "Lives in" above). User must be able to click and book. If no bookable venue in their area, leave empty.
- venue_website: REQUIRED for location-based experiences when reservation_link is not available. Provide the venue's or provider's official website IN THE RECIPIENT'S CITY/REGION. Every location-based experience MUST have at least one of reservation_link or venue_website—no exceptions.
- Generic suggestions ("book a cooking class", "plan a date night") are NOT acceptable. Every experience must PROVE it came from this profile.

GEOGRAPHY RULES FOR EXPERIENCE LINKS (CRITICAL):
- reservation_link and venue_website MUST be for venues in the recipient's location only (use "Lives in" and "Specific places" from LOCATION CONTEXT above). Never link to a restaurant, class, or venue in a different city or state—that would be logistically wrong.
- If you cannot find or specify a real venue link in the recipient's area, leave reservation_link and venue_website empty; we will provide a geography-calibrated search link instead.
- location_details must match the recipient's city/region when the experience is location-specific.

LOCATION RULES FOR EXPERIENCES:
- Location-based experiences require geographic context in the profile. Use specific venues from their profile when available (and only those in their area).
- If no location context, only suggest portable/at-home experiences. DO NOT invent a city or venue.

EXPERIENCE EXAMPLES (specificity + actionable):

BAD: "Book a cooking class" (too generic)
GOOD: "Thai cooking workshop at Khan's Kitchen in Indianapolis - they posted about pad thai 5x and mentioned wanting to learn. Classes on Saturdays." materials_needed: [cookbook, specialty ingredients set] with links; how_to_execute: "Book class at [url], buy ingredients set 2 days before, present with a note: 'First of many Thai nights'"; how_to_make_it_special: "Frame it as 'your next date night' so they know you remembered their wish."

BAD: "Plan a date night" (too generic)
GOOD: "Studio Ghibli movie marathon with themed snacks - they referenced Totoro 3x, collect anime merch, reposted Ghibli 8x." materials_needed: [Criterion box set, Japanese snack subscription, Totoro plushie] with URLs; how_to_execute: "Order snacks and set up a cozy viewing nook; queue 2-3 films"; how_to_make_it_special: "Present the plushie as 'your viewing buddy'—ties the gift to the experience."

Return ONLY a JSON object with this structure:
{{
  "product_gifts": [
    {{
      "name": "exact product name from available products",
      "description": "what this product is (warm, human tone)",
      "why_perfect": "warm 1-2 sentences: why this fits them (use {pronoun_possessive}/{pronoun_subject}). Cite specific interest or behavior. No clinical language.",
      "price": "price from product data",
      "where_to_buy": "source domain",
      "product_url": "direct product URL from search results",
      "image_url": "EXACT image URL from the product's Image line in AVAILABLE PRODUCTS - copy it exactly",
      "confidence_level": "safe_bet|adventurous",
      "gift_type": "physical",
      "interest_match": "which interest(s) this matches from profile"
    }}
  ],
  "experience_gifts": [
    {{
      "name": "HYPER-SPECIFIC experience name (must show custom curation)",
      "description": "2-3 sentences: what the experience is and why it fits (warm, human tone)",
      "why_perfect": "Warm 1-2 sentences: why this experience is perfect for them. Cite 2+ profile data points in a natural way—no clinical phrasing.",
      "location_specific": true/false,
      "location_details": "specific venue/city if location-based, or 'N/A - portable experience'",
      "materials_needed": [
        {{
          "item": "concrete item to buy",
          "where_to_buy": "retailer or 'from product list above'",
          "product_url": "exact URL from AVAILABLE PRODUCTS when possible, else empty",
          "estimated_price": "$XX"
        }}
      ],
      "how_to_execute": "Clear step-by-step for the gift-giver: what to book/buy, when, in what order. Actionable.",
      "how_to_make_it_special": "1-2 sentences: how to present it, a thoughtful touch, or why it will feel memorable",
      "reservation_link": "Direct URL to book/reserve when applicable: OpenTable, Resy, Tock, or venue rez page. Empty if N/A.",
      "venue_website": "Venue or experience provider website / booking URL when applicable. Empty if N/A.",
      "confidence_level": "safe_bet|adventurous",
      "gift_type": "experience"
    }}
  ]
}}

CRITICAL REQUIREMENTS:
- Product gifts MUST be selected FROM THE INVENTORY ABOVE ONLY. Every product gift must be one of the {len(products)} listed products (use exact URLs and image URLs from that line). Never invent or reference a product not in the inventory. product_url = direct product page ONLY—never search or homepage.
- Experience gifts MUST be hyper-specific, cite 2+ profile data points in why_perfect, and include how_to_execute + how_to_make_it_special.
- Experience links (reservation_link, venue_website) are LOGISTICS-CRITICAL: they must point to venues in the recipient's city/region only (use "Lives in" and "Specific places"). Never link to a venue in another city or state. If you cannot find a real bookable venue in their area, leave both empty—we will supply a geography-calibrated search link.
- materials_needed for experiences: when an item matches a product in AVAILABLE PRODUCTS, copy that product's URL exactly into product_url and set where_to_buy to its domain. Never use search URLs—only direct product page URLs from the list. Empty product_url is OK when no match; we will add a find-it link.
- If no location context, DO NOT suggest location-specific experiences
- Each recommendation must have clear evidence from the profile
- Maintain variety - don't pick 10 similar products
- Total: {rec_count} product gifts + 2-3 experience gifts
- Return ONLY the JSON object, no markdown, no backticks"""
    
    try:
        # Call Claude for curation
        logger.info("Calling Claude API for gift curation...")
        
        message = claude_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=6000,
            messages=[{"role": "user", "content": prompt}],
            timeout=120.0
        )
        
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
        image_url = p.get('image', '') or p.get('thumbnail', '')
        formatted.append(f"{idx}. {title}\n   Price: {price} | Domain: {domain} | Interest match: {interest}\n   Description: {snippet[:150]}\n   URL: {link}\n   Image: {image_url}")
    
    return '\n\n'.join(formatted[:50])  # Limit to 50 products in prompt
