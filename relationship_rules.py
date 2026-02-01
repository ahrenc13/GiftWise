"""
RELATIONSHIP RULES - Different gift appropriateness by relationship level
Ensures spouse gifts are intimate/romantic, acquaintance gifts are safe/neutral

Author: Chad + Claude
Date: February 2026
"""


class RelationshipRules:
    """Define gift appropriateness rules by relationship type"""
    
    RELATIONSHIP_TIERS = {
        'spouse': {
            'price_range': (50, 300),
            'intimacy_level': 'very_high',
            'appropriate_types': [
                'romantic experiences', 'jewelry', 'spa/wellness', 'weekend getaways',
                'personalized romantic gifts', 'luxury items', 'couples activities',
                'intimate apparel', 'anniversary-worthy', 'sentimental keepsakes'
            ],
            'avoid_types': [
                'generic items', 'office supplies', 'basic household items',
                'anything impersonal', 'gag gifts'
            ],
            'tone': 'romantic and deeply personal',
            'message_style': 'intimate, shows deep knowledge of them'
        },
        'partner': {
            'price_range': (50, 300),
            'intimacy_level': 'very_high',
            'appropriate_types': [
                'romantic experiences', 'jewelry', 'spa/wellness', 'weekend getaways',
                'personalized romantic gifts', 'luxury items', 'couples activities',
                'intimate apparel', 'anniversary-worthy', 'sentimental keepsakes'
            ],
            'avoid_types': [
                'generic items', 'office supplies', 'basic household items',
                'anything impersonal', 'gag gifts'
            ],
            'tone': 'romantic and deeply personal',
            'message_style': 'intimate, shows deep knowledge of them'
        },
        'close_friend': {
            'price_range': (30, 100),
            'intimacy_level': 'high',
            'appropriate_types': [
                'experiences together', 'hobby-related items', 'personalized gifts',
                'concert/event tickets', 'quality items they love', 'inside jokes',
                'meaningful but not romantic', 'fun adventures', 'shared memories'
            ],
            'avoid_types': [
                'romantic gifts', 'intimate apparel', 'generic corporate gifts',
                'anything too cheap', 'overtly sexual items'
            ],
            'tone': 'warm and personal',
            'message_style': 'shows you know them well, but friendly not romantic'
        },
        'family': {
            'price_range': (30, 150),
            'intimacy_level': 'high',
            'appropriate_types': [
                'quality hobby items', 'family experiences', 'personalized gifts',
                'practical luxuries', 'nostalgic items', 'family memories',
                'health/wellness', 'home comfort items'
            ],
            'avoid_types': [
                'romantic gifts', 'intimate apparel', 'gag gifts',
                'anything too trendy', 'controversial items'
            ],
            'tone': 'loving and thoughtful',
            'message_style': 'family-appropriate, shows care and understanding'
        },
        'friend': {
            'price_range': (20, 60),
            'intimacy_level': 'medium',
            'appropriate_types': [
                'fun hobby items', 'group activities', 'popular items they like',
                'books/media', 'food/drink experiences', 'casual outings',
                'trendy items', 'practical but nice', 'shared interest items'
            ],
            'avoid_types': [
                'anything romantic', 'intimate items', 'super cheap items',
                'overly personal gifts', 'anything too serious'
            ],
            'tone': 'friendly and fun',
            'message_style': 'shows you pay attention, but keeps it light'
        },
        'coworker': {
            'price_range': (15, 50),
            'intimacy_level': 'low',
            'appropriate_types': [
                'office-friendly items', 'coffee/snacks', 'desk accessories',
                'gift cards', 'general interest books', 'safe hobby items',
                'lunch/coffee', 'universally appealing items', 'professional items'
            ],
            'avoid_types': [
                'anything romantic', 'intimate items', 'controversial items',
                'alcohol (unless you know they drink)', 'religious items',
                'anything too personal', 'inside jokes they won\'t get'
            ],
            'tone': 'professional and friendly',
            'message_style': 'polite and appropriate, safe choices'
        },
        'acquaintance': {
            'price_range': (10, 35),
            'intimacy_level': 'very_low',
            'appropriate_types': [
                'gift cards', 'generic nice items', 'popular consumables',
                'coffee/tea sets', 'candles', 'basic hobby items',
                'safe universal items', 'simple thoughtful gestures'
            ],
            'avoid_types': [
                'anything personal', 'expensive items', 'intimate items',
                'inside jokes', 'controversial items', 'anything requiring deep knowledge'
            ],
            'tone': 'polite and safe',
            'message_style': 'generic but thoughtful, universally appropriate'
        }
    }
    
    @staticmethod
    def get_relationship_rules(relationship_type):
        """
        Get gift rules for a specific relationship
        
        Args:
            relationship_type: 'spouse', 'partner', 'close_friend', 'family', 
                             'friend', 'coworker', 'acquaintance'
        
        Returns:
            Dict with price_range, appropriate_types, avoid_types, etc.
        """
        
        relationship_lower = relationship_type.lower().replace(' ', '_')
        
        # Map variations to standard types
        mappings = {
            'significant_other': 'partner',
            'boyfriend': 'partner',
            'girlfriend': 'partner',
            'husband': 'spouse',
            'wife': 'spouse',
            'best_friend': 'close_friend',
            'close_family': 'family',
            'parent': 'family',
            'sibling': 'family',
            'colleague': 'coworker',
            'casual_friend': 'friend'
        }
        
        relationship_type = mappings.get(relationship_lower, relationship_lower)
        
        return RelationshipRules.RELATIONSHIP_TIERS.get(
            relationship_type,
            RelationshipRules.RELATIONSHIP_TIERS['friend']  # Default to friend
        )
    
    @staticmethod
    def format_relationship_prompt(relationship_type):
        """
        Create detailed prompt instructions for Claude based on relationship
        
        Returns:
            String with specific relationship guidance
        """
        
        rules = RelationshipRules.get_relationship_rules(relationship_type)
        
        min_price, max_price = rules['price_range']
        
        prompt = f"""
RELATIONSHIP: {relationship_type.upper().replace('_', ' ')}

CRITICAL RELATIONSHIP RULES:

Price Range: ${min_price}-${max_price}
- Stay within this range
- Don't suggest anything cheaper than ${min_price}
- Don't suggest anything more expensive than ${max_price}

Intimacy Level: {rules['intimacy_level'].replace('_', ' ').title()}

MUST INCLUDE THESE GIFT TYPES:
{chr(10).join(f"  ✓ {t}" for t in rules['appropriate_types'][:6])}

ABSOLUTELY AVOID:
{chr(10).join(f"  ✗ {t}" for t in rules['avoid_types'][:4])}

Tone: {rules['tone']}
Message Style: {rules['message_style']}

RELATIONSHIP-SPECIFIC EXAMPLES:
"""
        
        # Add examples for extreme cases
        if relationship_type in ['spouse', 'partner']:
            prompt += """
✓ GOOD: "Weekend spa getaway for two" ($200)
✓ GOOD: "Custom engraved jewelry with your anniversary date" ($120)
✓ GOOD: "Couples cooking class + romantic dinner" ($150)
✗ BAD: "Gift card to Target" (too generic)
✗ BAD: "Desk organizer" (too impersonal)
✗ BAD: "$15 candle" (too cheap for this relationship)
"""
        elif relationship_type == 'acquaintance':
            prompt += """
✓ GOOD: "$25 Starbucks gift card" (safe, appropriate)
✓ GOOD: "Nice scented candle set" ($30)
✓ GOOD: "Popular book they'd enjoy" ($20)
✗ BAD: "Personalized photo album" (too intimate)
✗ BAD: "$150 luxury item" (too expensive)
✗ BAD: "Inside joke item" (they won't get it)
"""
        elif relationship_type == 'coworker':
            prompt += """
✓ GOOD: "Premium coffee sampler" ($35)
✓ GOOD: "Sleek desk accessory" ($40)
✓ GOOD: "Lunch at nice restaurant" ($50)
✗ BAD: "Romantic anything" (inappropriate)
✗ BAD: "Personal hobby item requiring deep knowledge" (too personal)
✗ BAD: "$10 generic mug" (too cheap, thoughtless)
"""
        
        return prompt
    
    @staticmethod
    def filter_by_relationship(products, relationship_type):
        """
        Filter products to match relationship appropriateness
        
        Args:
            products: List of product dicts with 'title', 'snippet', 'price'
            relationship_type: Relationship level
        
        Returns:
            Filtered list of appropriate products
        """
        
        rules = RelationshipRules.get_relationship_rules(relationship_type)
        min_price, max_price = rules['price_range']
        avoid_keywords = rules['avoid_types']
        
        filtered = []
        
        for product in products:
            title = product.get('title', '').lower()
            snippet = product.get('snippet', '').lower()
            combined = f"{title} {snippet}"
            
            # Check if product contains avoid keywords
            should_avoid = False
            for avoid_term in avoid_keywords:
                if avoid_term.lower() in combined:
                    should_avoid = True
                    break
            
            if should_avoid:
                continue
            
            # Check price range if available
            price_str = product.get('price', '')
            if price_str:
                try:
                    # Extract numeric price
                    import re
                    price_match = re.search(r'\d+\.?\d*', price_str.replace(',', ''))
                    if price_match:
                        price = float(price_match.group())
                        
                        # Filter by price range
                        if price < min_price * 0.8 or price > max_price * 1.2:
                            continue  # Outside acceptable range (with 20% buffer)
                except:
                    pass  # If can't parse price, keep the product
            
            filtered.append(product)
        
        return filtered


def get_relationship_guidance(relationship_type):
    """
    Convenience function to get formatted relationship prompt
    
    Args:
        relationship_type: String like 'spouse', 'friend', 'coworker'
    
    Returns:
        Formatted prompt string for Claude
    """
    return RelationshipRules.format_relationship_prompt(relationship_type)
