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

WORK INTERESTS (do NOT base experience gifts on these—only personal/leisure): {', '.join([i.get('name', '') for i in profile.get('interests', []) if i.get('is_work')]) or 'None'}

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

RECIPIENT: {len(profile.get('interests', []))} interests including {', '.join([i.get('name', '') for i in profile.get('interests', [])[:3]])}
Location: {profile.get('location_context', {}).get('city_region', 'Unknown')}
Avoid: {', '.join(profile.get('gift_avoid', [])[:3]) or 'None'}

{products_summary}

SELECT {rec_count} BEST PRODUCTS from above. Requirements:
- Match interests with profile evidence
- Max 2 products per interest (spread across 5+ interests)
- Use exact URLs and image URLs from product list
- Only direct product links (no search URLs)
- SOURCE PRIORITY: Prefer gifts from Etsy, Awin, eBay, and ShareASale (see "Domain" in each product). Only choose products from Amazon (domain amazon.com) when you cannot find strong interest matches from other platforms—use Amazon only to fill in if needed.

ALSO: Generate 2 hyper-specific experience gifts synthesizing 2+ profile elements. EXPERIENCE GIFTS must be based ONLY on personal/leisure interests—never on work interests (see WORK INTERESTS above). Do not suggest IndyCar, EMS, nursing, healthcare, or any job-related experiences; experiences should feel like escape from work, not extension of it.

Return JSON:
{{
  "product_gifts": [
    {{
      "name": "exact name from list",
      "description": "what it is",
      "why_perfect": "why it fits (cite interest)",
      "price": "from product",
      "where_to_buy": "domain",
      "product_url": "exact URL from list",
      "image_url": "exact image URL from list",
      "confidence_level": "safe_bet|adventurous",
      "gift_type": "physical",
      "interest_match": "interest name"
    }}
  ],
  "experience_gifts": [
    {{
      "name": "specific experience",
      "description": "what/why",
      "why_perfect": "cite 2+ profile points",
      "location_specific": true/false,
      "location_details": "venue/city or N/A",
      "materials_needed": [{{"item": "", "where_to_buy": "", "product_url": "", "estimated_price": ""}}],
      "how_to_execute": "steps",
      "how_to_make_it_special": "touch",
      "reservation_link": "URL or empty",
      "venue_website": "URL or empty",
      "confidence_level": "safe_bet|adventurous",
      "gift_type": "experience"
    }}
  ]
}}

REQUIREMENTS:
- Product gifts MUST be selected FROM THE INVENTORY ABOVE ONLY. Every product gift must be one of the {len(products)} listed products (use exact URLs and image URLs from that line). Never invent or reference a product not in the inventory. product_url = direct product page ONLY - never search or homepage.
- Experience gifts MUST be hyper-specific, cite 2+ profile data points in why_perfect, and include how_to_execute + how_to_make_it_special. They must NOT be based on work interests—only personal/leisure (see WORK INTERESTS).
- Experience links (reservation_link, venue_website) are LOGISTICS-CRITICAL: they must point to venues in the recipient's city/region only (use "Lives in" and "Specific places"). Never link to a venue in another city or state. If you cannot find a real bookable venue in their area, leave both empty - we will supply a geography-calibrated search link.
- materials_needed for experiences: when an item matches a product in AVAILABLE PRODUCTS, copy that product's URL exactly into product_url and set where_to_buy to its domain. Never use search URLs - only direct product page URLs from the list. Empty product_url is OK when no match; we will add a find-it link.
- If no location context, DO NOT suggest location-specific experiences
- Each recommendation must have clear evidence from the profile
- DIVERSITY: Max 2 products per single interest/theme (e.g. max 2 per band). Spread across at least 5+ interests.
- Total: {rec_count} product gifts + 2-3 experience gifts
- Every product gift product_url MUST be an exact copy of a URL from the INVENTORY list above - no invented products, no search pages.
- AMAZON DEPRIORITIZED: Treat Amazon as fill-in only. Prefer Etsy, Awin, eBay, ShareASale; select Amazon products only when there aren't good matches from those sources.
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
        image_url = p.get('image', '') or p.get('thumbnail', '') or p.get('image_url', '')
        formatted.append(f"{idx}. {title}\n   Price: {price} | Domain: {domain} | Interest match: {interest}\n   Description: {snippet[:150]}\n   URL: {link}\n   Image: {image_url}")
    
    return '\n\n'.join(formatted[:50])  # Limit to 50 products in prompt
