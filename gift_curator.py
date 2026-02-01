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
    
    logger.info(f"Curating {rec_count} products from {len(products)} options...")
    
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
- Gaps to fill: {', '.join(profile.get('aspirational_vs_current', {}).get('gaps', [])[:3])}

SPECIFIC VENUES/PLACES:
{format_venues(profile.get('specific_venues', []))}
"""
    
    # Format products for prompt
    products_summary = format_products(products)
    
    prompt = f"""You are an expert gift curator. You have a deep profile of the recipient and {len(products)} REAL products to choose from.

{profile_summary}{relationship_context}

AVAILABLE PRODUCTS ({len(products)} real products with actual purchase links):
{products_summary}

YOUR TASK:
1. Select the BEST {rec_count} products that match this person's profile
2. Generate 2-3 HYPER-SPECIFIC experience gift ideas

PRODUCT SELECTION CRITERIA:
- Match products to specific interests with evidence
- Ensure diverse coverage (don't pick 10 similar items)
- Prioritize ASPIRATIONAL interests (things they want but don't have)
- Consider relationship appropriateness
- Prefer unique, specialty items over generic mass-market products
- Stay within their comfortable price range
- No square pegs in round holes - only include perfect matches

EXPERIENCE GIFT CRITERIA (CRITICAL):
- Must be HYPER-SPECIFIC and custom-curated to this exact person
- Must synthesize multiple data points from their profile
- If location-specific, MUST use their actual location or specific venues they've mentioned
- If equipment/materials needed, INCLUDE shop links for those items
- Generic suggestions (like "book a cooking class") are NOT acceptable
- Each experience must PROVE it came from deep profile analysis

LOCATION RULES FOR EXPERIENCES:
- If suggesting a location-based experience, you MUST have geographic context
- Use specific venues from their profile if available
- If no location context, only suggest portable/at-home experiences
- DO NOT suggest generic location-based experiences without knowing where they are

EXPERIENCE EXAMPLES (showing specificity level required):

BAD: "Book a cooking class" (too generic)
GOOD: "Thai cooking workshop at Khan's Kitchen in Indianapolis - they posted about pad thai 5x and mentioned wanting to learn. Classes on Saturdays." [Include links to: cookbook, specialty ingredients set]

BAD: "Plan a date night" (too generic)
GOOD: "Studio Ghibli movie marathon with themed snacks - they referenced My Neighbor Totoro 3x, collect anime merch, and reposted Ghibli edits 8x." [Include links to: Criterion Collection box set, Japanese snack subscription, Totoro plushie]

BAD: "Go to a concert" (too generic)
GOOD: "Indie folk show at The Vogue (Indianapolis venue they've posted from) - they follow 3 indie folk artists and tagged #livemusic 12x. Check upcoming shows: Bon Iver, Phoebe Bridgers, The Lumineers" [Include links to: concert merch, vinyl of featured artist]

Return ONLY a JSON object with this structure:
{{
  "product_gifts": [
    {{
      "name": "exact product name from available products",
      "description": "what this product is",
      "why_perfect": "specific evidence from profile showing why this matches (cite interests, posts, behaviors)",
      "price": "price from product data",
      "where_to_buy": "source domain",
      "product_url": "direct product URL from search results",
      "image_url": "product image URL from search results",
      "confidence_level": "safe_bet|adventurous",
      "gift_type": "physical",
      "interest_match": "which interest(s) this matches from profile"
    }}
  ],
  "experience_gifts": [
    {{
      "name": "HYPER-SPECIFIC experience name (must show custom curation)",
      "description": "2-3 sentences explaining the experience and why it's perfect for them",
      "why_perfect": "synthesis of multiple profile data points that led to this suggestion - prove it's custom",
      "location_specific": true/false,
      "location_details": "specific venue/city if location-based, or 'N/A - portable experience'",
      "materials_needed": [
        {{
          "item": "what's needed",
          "where_to_buy": "retailer",
          "product_url": "shop link if available",
          "estimated_price": "$XX"
        }}
      ],
      "how_to_execute": "step-by-step for the gift-giver",
      "confidence_level": "safe_bet|adventurous",
      "gift_type": "experience"
    }}
  ]
}}

CRITICAL REQUIREMENTS:
- Product gifts MUST come from the provided product list (use exact URLs and data)
- Experience gifts MUST be hyper-specific and prove custom curation
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


def format_interests(interests):
    """Format interests list for prompt"""
    if not interests:
        return "None identified"
    
    formatted = []
    for i in interests:
        name = i.get('name', 'Unknown')
        evidence = i.get('evidence', '')
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
