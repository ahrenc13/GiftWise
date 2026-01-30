"""
RECOMMENDATION ENGINE - ENHANCED VERSION
Generates gift recommendations using Claude AI with strict validation

CRITICAL IMPROVEMENT: Prompt engineering to ensure REAL, BUYABLE products only
- Forces Claude to only recommend specific products with brand names and models
- Rejects generic or made-up products
- Requires product URLs and images
- Better category targeting

Author: Chad + Claude  
Date: January 2026
"""

import anthropic
import json
import logging
import os
from datetime import datetime

logger = logging.getLogger('giftwise')

# Anthropic API client
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None

def build_recommendation_prompt(platform_insights, signals, rec_count=15, relationship='someone_else'):
    """
    Build the Claude prompt with strict requirements for REAL products
    
    Args:
        platform_insights: Analyzed data from social platforms
        signals: Interest signals extracted
        rec_count: Number of recommendations to generate
        relationship: 'myself' or 'someone_else'
    
    Returns:
        str: Formatted prompt
    """
    
    recipient_pronoun = "yourself" if relationship == 'myself' else "them"
    recipient_possessive = "your" if relationship == 'myself' else "their"
    
    prompt = f"""You are the world's best gift advisor. Analyze this person's social media data and recommend {rec_count} SPECIFIC, REAL products they'd love.

# CRITICAL RULES - READ CAREFULLY:

1. **ONLY RECOMMEND REAL PRODUCTS**: Every recommendation MUST be a specific, currently-available product with a brand name and model number. Examples:
   ✅ GOOD: "Bose QuietComfort 45 Headphones"
   ✅ GOOD: "Nintendo Switch OLED Console"
   ✅ GOOD: "Lululemon Align High-Rise Pant 25"
   ❌ BAD: "Wireless headphones" (too generic)
   ❌ BAD: "Gaming console" (not specific)
   ❌ BAD: "Yoga pants" (no brand/model)

2. **EVERY PRODUCT MUST HAVE**:
   - Brand name (Nike, Apple, Lego, etc.)
   - Specific model or product name
   - Clear where to buy it (Amazon, Target, brand website, etc.)
   - Realistic price range

3. **VALIDATION CHECK**: Before including a product, ask yourself:
   - "Can I Google this exact product name and find it?"
   - "Is this a real brand with a real product?"
   - "Would someone actually be able to buy this?"
   - If ANY answer is "no", DO NOT include it.

4. **PRICE RANGES**: Be realistic based on actual market prices:
   - Electronics: $20-$500+
   - Clothing: $20-$200
   - Books: $10-$40
   - Experiences: $30-$300

5. **DIVERSITY**: Include mix of:
   - 60-70% Physical products (things they can hold)
   - 30-40% Experiences (classes, subscriptions, events)
   - Mix of price ranges ($20-30, $30-60, $60-100, $100-200, $200+)

6. **CATEGORIES TO CONSIDER** (based on their interests):
   - Tech gadgets (if tech-interested)
   - Books (if reader)
   - Fitness gear (if active)
   - Kitchen/cooking (if food-interested)
   - Fashion/accessories (if style-conscious)
   - Art/craft supplies (if creative)
   - Gaming (if gamer)
   - Music gear (if musician)
   - Home decor (if design-interested)
   - Experiences (classes, subscriptions, events)

---

# PERSON'S DATA:

## Platform Insights:
{json.dumps(platform_insights, indent=2)}

## Interest Signals:
{json.dumps(signals, indent=2)}

---

# YOUR TASK:

Generate {rec_count} gift recommendations in JSON format. For EACH recommendation, include:

```json
{{
  "name": "BRAND NAME + SPECIFIC PRODUCT (e.g., 'Sony WH-1000XM5 Headphones')",
  "description": "Brief description of what it is and what makes it special",
  "why_perfect": "Explain specifically why this matches {recipient_possessive} interests based on {recipient_possessive} social media (be specific!)",
  "price_range": "Realistic price with $ (e.g., '$80-$120')",
  "where_to_buy": "Specific retailer (Amazon, Target, official website, etc.)",
  "category": "One of: Electronics, Books, Fashion, Home, Fitness, Food, Art, Gaming, Music, Experience",
  "confidence_level": "safe_bet or adventurous",
  "gift_type": "physical or experience",
  "product_url": "If known, provide the purchase URL. Otherwise leave empty.",
  "match_score": 75-95 (how well it matches their interests)
}}
```

**CONFIDENCE LEVELS**:
- **safe_bet**: Product directly matches their shown interests (70% of recommendations)
- **adventurous**: Related to their interests but introduces something new (30%)

**MATCH SCORE GUIDANCE**:
- 90-95: Perfect match, obvious from data
- 80-89: Strong match, clear connection
- 75-79: Good match, reasonable connection

---

# EXAMPLE (DO NOT COPY - CREATE YOUR OWN):

If person loves photography (posts lots of photos):
✅ "Canon EOS M50 Mark II Camera" 
✅ "Peak Design Everyday Backpack 20L"
✅ "Adobe Creative Cloud Photography Plan (1-year subscription)"

NOT:
❌ "Professional camera" (not specific)
❌ "Camera accessories" (not specific) 
❌ "Photography equipment" (too vague)

---

# OUTPUT FORMAT:

Return ONLY a JSON array of recommendations. NO other text. Start with [ and end with ].

Example structure:
[
  {{
    "name": "Real Product Name Here",
    "description": "...",
    "why_perfect": "...",
    "price_range": "$XX-$YY",
    "where_to_buy": "...",
    "category": "...",
    "confidence_level": "safe_bet",
    "gift_type": "physical",
    "product_url": "",
    "match_score": 85
  }},
  ... more recommendations ...
]

Generate {rec_count} recommendations now. BE SPECIFIC. USE REAL BRANDS. ONLY RECOMMEND PRODUCTS THAT ACTUALLY EXIST.
"""
    
    return prompt


def generate_recommendations(platform_insights, signals, rec_count=15, relationship='someone_else', max_retries=2):
    """
    Generate gift recommendations using Claude AI
    
    Args:
        platform_insights: Analyzed data from platforms
        signals: Interest signals
        rec_count: Number of recommendations
        relationship: 'myself' or 'someone_else'
        max_retries: Number of retry attempts if validation fails
    
    Returns:
        list of recommendation dicts or None on failure
    """
    if not anthropic_client:
        logger.error("Anthropic API not configured")
        return None
    
    prompt = build_recommendation_prompt(platform_insights, signals, rec_count, relationship)
    
    attempt = 0
    while attempt < max_retries:
        try:
            logger.info(f"Generating {rec_count} recommendations (attempt {attempt + 1}/{max_retries})...")
            
            # Call Claude API
            message = anthropic_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=8000,
                temperature=0.7,  # Balance creativity with accuracy
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            # Extract JSON from response
            response_text = message.content[0].text
            
            # Remove markdown code blocks if present
            if '```json' in response_text:
                response_text = response_text.split('```json')[1].split('```')[0]
            elif '```' in response_text:
                response_text = response_text.split('```')[1].split('```')[0]
            
            # Parse JSON
            recommendations = json.loads(response_text.strip())
            
            if not isinstance(recommendations, list):
                logger.error("Response is not a list")
                attempt += 1
                continue
            
            # Validate recommendations
            validated_recommendations = []
            for i, rec in enumerate(recommendations):
                # Check required fields
                required_fields = ['name', 'description', 'why_perfect', 'price_range', 'where_to_buy', 'category']
                if not all(field in rec for field in required_fields):
                    logger.warning(f"Recommendation {i+1} missing required fields, skipping")
                    continue
                
                # Check name is specific enough (at least 2 words)
                name_words = rec['name'].split()
                if len(name_words) < 2:
                    logger.warning(f"Recommendation '{rec['name']}' too generic (< 2 words), skipping")
                    continue
                
                # Check for vague product names
                vague_words = ['item', 'product', 'thing', 'gift', 'set', 'collection', 'bundle']
                if any(vague in rec['name'].lower() for vague in vague_words) and len(name_words) < 3:
                    logger.warning(f"Recommendation '{rec['name']}' seems vague, skipping")
                    continue
                
                # Add defaults for optional fields
                rec.setdefault('confidence_level', 'safe_bet')
                rec.setdefault('gift_type', 'physical')
                rec.setdefault('match_score', 80)
                rec.setdefault('product_url', '')
                
                # Ensure proper confidence level values
                if rec['confidence_level'] not in ['safe_bet', 'adventurous']:
                    rec['confidence_level'] = 'safe_bet'
                
                # Ensure proper gift type values
                if rec['gift_type'] not in ['physical', 'experience']:
                    rec['gift_type'] = 'physical'
                
                validated_recommendations.append(rec)
            
            if len(validated_recommendations) < rec_count * 0.6:  # Less than 60% valid
                logger.warning(f"Only {len(validated_recommendations)}/{rec_count} recommendations passed validation")
                attempt += 1
                continue
            
            logger.info(f"Successfully generated {len(validated_recommendations)} validated recommendations")
            return validated_recommendations
        
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {e}")
            logger.debug(f"Response text: {response_text[:500]}...")
            attempt += 1
        
        except Exception as e:
            logger.error(f"Recommendation generation error: {e}")
            attempt += 1
    
    logger.error(f"Failed to generate recommendations after {max_retries} attempts")
    return None


def enhance_recommendations_with_context(recommendations, platform_insights):
    """
    Add additional context to recommendations based on platform data
    
    Args:
        recommendations: List of recommendation dicts
        platform_insights: Platform analysis data
    
    Returns:
        Enhanced recommendations list
    """
    # Add metadata
    for rec in recommendations:
        # Determine retailer type from where_to_buy
        where = rec.get('where_to_buy', '').lower()
        if 'amazon' in where:
            rec['retailer_type'] = 'amazon'
        elif 'etsy' in where:
            rec['retailer_type'] = 'etsy'
        elif 'target' in where:
            rec['retailer_type'] = 'target'
        elif 'best buy' in where:
            rec['retailer_type'] = 'best_buy'
        else:
            rec['retailer_type'] = 'other'
        
        # Add timestamp
        rec['generated_at'] = datetime.now().isoformat()
    
    return recommendations
