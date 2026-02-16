"""
INTEGRATION EXAMPLE - How to use regional intelligence in GiftWise

This shows exactly how to integrate the new regional/seasonal/event modules
into the existing GiftWise pipeline.

Author: Chad + Claude
Date: February 2026
"""

from regional_culture import get_regional_context, get_gift_guidance_for_region
from seasonal_experiences import get_seasonal_context, get_seasonal_guidance, should_avoid_outdoor
from local_events import get_local_events, get_event_suggestions
from experience_synthesis import synthesize_with_geo_culture


# ================================================================================
# EXAMPLE 1: Add regional guidance to gift curator prompt
# ================================================================================

def enhance_curator_prompt_with_regional_intelligence(profile):
    """
    Add regional context to the gift curator prompt.
    
    Integration point: gift_curator.py, build_curator_prompt()
    """
    
    # Extract location info
    loc_ctx = profile.get('location_context', {})
    city_region = loc_ctx.get('city_region', '')
    city = city_region.split(',')[0].strip() if city_region else None
    state = loc_ctx.get('state')
    age = profile.get('age')
    gender = profile.get('gender')
    
    # Get regional context
    regional_context = get_regional_context(city=city, state=state, age=age, gender=gender)
    regional_guidance = get_gift_guidance_for_region(regional_context)
    
    # Get seasonal context
    from datetime import datetime
    current_month = datetime.now().month
    region = regional_context.get('region_name') if regional_context else None
    seasonal_guidance = get_seasonal_guidance(current_month, region)
    
    # Build enhanced prompt section
    enhanced_prompt = f"""

REGIONAL & SEASONAL INTELLIGENCE:

{regional_guidance}

{seasonal_guidance}

REGIONAL GIFT PREFERENCES:
- Personalization preference: {regional_context.get('gift_norms', {}).get('personalization_preference', 'moderate')}
- Experience vs Thing: {regional_context.get('gift_norms', {}).get('experience_vs_thing', 'balanced')}
- Style notes: {regional_context.get('style_notes', 'N/A')}

Use this regional intelligence when selecting gifts. Respect local culture and seasonal appropriateness.
"""
    
    return enhanced_prompt


# ================================================================================
# EXAMPLE 2: Generate smart experiences with full context
# ================================================================================

def generate_regional_experiences(profile):
    """
    Generate experiences with regional + seasonal + local event intelligence.
    
    Integration point: experience_architect.py or giftwise_app.py experience generation
    """
    
    # Build location context (this should already exist in your profile)
    location_context = profile.get('location_context', {})
    
    # Use the master synthesis function
    result = synthesize_with_geo_culture(
        profile=profile,
        location_context=location_context,
        max_experiences=3
    )
    
    # Result contains:
    # - experiences: List of experience dicts with regional context
    # - regional_guidance: Text for curator/display
    # - seasonal_guidance: Text for curator/display
    # - local_events: List of local events
    # - avoid_experiences: List of things to avoid
    
    return result


# ================================================================================
# EXAMPLE 3: Display regional context in templates
# ================================================================================

def prepare_profile_for_template_with_regional_context(profile):
    """
    Enhance profile dict with regional intelligence for template display.
    
    Integration point: giftwise_app.py, before rendering recommendations.html
    """
    
    # Get location info
    loc_ctx = profile.get('location_context', {})
    city_region = loc_ctx.get('city_region', '')
    city = city_region.split(',')[0].strip() if city_region else None
    state = loc_ctx.get('state')
    age = profile.get('age')
    gender = profile.get('gender')
    
    # Get regional context
    regional_context = get_regional_context(city=city, state=state, age=age, gender=gender)
    
    # Get local events
    from datetime import datetime
    current_month = datetime.now().month
    interest_names = [i.get('name', '') for i in profile.get('interests', [])[:5]]
    local_events = get_event_suggestions(city, state, interests=interest_names) if city else []
    
    # Add to profile for template
    profile['regional_vibe'] = regional_context.get('city_vibe') or regional_context.get('region_name', '').replace('_', ' ').title()
    profile['local_events'] = local_events[:5]  # Top 5 events
    profile['signature_experiences'] = regional_context.get('signature_experiences', [])[:3]
    
    return profile


# ================================================================================
# EXAMPLE 4: Filter experiences by season
# ================================================================================

def filter_experiences_by_season(experiences, profile):
    """
    Filter or adapt experiences based on seasonal appropriateness.
    
    Integration point: Post-curation or in experience generation
    """
    
    from datetime import datetime
    
    # Get location info
    loc_ctx = profile.get('location_context', {})
    city_region = loc_ctx.get('city_region', '')
    city = city_region.split(',')[0].strip() if city_region else None
    state = loc_ctx.get('state')
    
    # Get region
    regional_context = get_regional_context(city=city, state=state)
    region = regional_context.get('region_name')
    
    # Get seasonal context
    current_month = datetime.now().month
    seasonal_context = get_seasonal_context(current_month, region)
    
    # Filter experiences
    filtered_experiences = []
    avoid_list = seasonal_context.get('avoid_experiences', [])
    
    for exp in experiences:
        exp_title = exp.get('title', '').lower()
        
        # Check if experience should be avoided this season
        should_skip = False
        for avoid_term in avoid_list:
            if avoid_term.lower() in exp_title:
                should_skip = True
                break
        
        if not should_skip:
            # Add seasonal note to description
            exp['seasonal_note'] = seasonal_context.get('weather_notes', '')
            filtered_experiences.append(exp)
    
    return filtered_experiences


# ================================================================================
# EXAMPLE 5: Complete integration in main recommendation flow
# ================================================================================

def build_recommendations_with_regional_intelligence(profile, products):
    """
    COMPLETE EXAMPLE: Full integration in main recommendation flow.
    
    This shows how to enhance the entire recommendation pipeline.
    """
    
    # Step 1: Get regional context for curator prompt enhancement
    loc_ctx = profile.get('location_context', {})
    city_region = loc_ctx.get('city_region', '')
    city = city_region.split(',')[0].strip() if city_region else None
    state = loc_ctx.get('state')
    age = profile.get('age')
    gender = profile.get('gender')
    
    regional_context = get_regional_context(city=city, state=state, age=age, gender=gender)
    regional_guidance = get_gift_guidance_for_region(regional_context)
    
    # Step 2: Get seasonal context
    from datetime import datetime
    current_month = datetime.now().month
    region = regional_context.get('region_name')
    seasonal_context = get_seasonal_context(current_month, region)
    seasonal_guidance = get_seasonal_guidance(current_month, region)
    
    # Step 3: Generate smart experiences with full intelligence
    experience_result = synthesize_with_geo_culture(
        profile=profile,
        location_context=loc_ctx,
        max_experiences=3
    )
    
    # Step 4: Build complete recommendation package
    recommendations = {
        'products': products,  # Your existing product recommendations
        'experiences': experience_result['experiences'],
        
        # NEW: Regional intelligence
        'regional_vibe': regional_context.get('city_vibe') or regional_context.get('region_name', '').replace('_', ' ').title(),
        'regional_guidance': regional_guidance,
        'demographic_synthesis': regional_context.get('demographic_synthesis'),
        
        # NEW: Seasonal intelligence
        'seasonal_guidance': seasonal_guidance,
        'current_season': seasonal_context.get('season'),
        'weather_notes': seasonal_context.get('weather_notes'),
        
        # NEW: Local events
        'local_events': experience_result['local_events'],
        'signature_experiences': regional_context.get('signature_experiences', [])[:3],
        
        # NEW: Things to avoid
        'avoid_experiences': experience_result['avoid_experiences'],
    }
    
    return recommendations


# ================================================================================
# TESTING
# ================================================================================

if __name__ == '__main__':
    # Test profile
    test_profile = {
        'age': 27,
        'gender': 'F',
        'location_context': {
            'city_region': 'Indianapolis, Indiana',
            'state': 'Indiana',
        },
        'interests': [
            {'name': 'Yoga', 'description': 'Regular practice', 'intensity': 'moderate'},
            {'name': 'Craft beer', 'description': 'Brewery hopping', 'intensity': 'moderate'},
            {'name': 'Hiking', 'description': 'Weekend trails', 'intensity': 'passionate'},
        ],
    }
    
    print("=" * 80)
    print("EXAMPLE 1: Enhanced curator prompt")
    print("=" * 80)
    enhanced_prompt = enhance_curator_prompt_with_regional_intelligence(test_profile)
    print(enhanced_prompt)
    
    print("\n" + "=" * 80)
    print("EXAMPLE 2: Regional experiences")
    print("=" * 80)
    experiences = generate_regional_experiences(test_profile)
    for exp in experiences['experiences']:
        print(f"\n- {exp['title']}")
        print(f"  {exp['description']}")
    
    print("\n" + "=" * 80)
    print("EXAMPLE 3: Profile enhanced for template")
    print("=" * 80)
    enhanced_profile = prepare_profile_for_template_with_regional_context(test_profile.copy())
    print(f"Regional vibe: {enhanced_profile.get('regional_vibe')}")
    print(f"Local events: {enhanced_profile.get('local_events')[:3]}")
    print(f"Signature experiences: {enhanced_profile.get('signature_experiences')[:3]}")
    
    print("\n" + "=" * 80)
    print("EXAMPLE 5: Complete recommendation package")
    print("=" * 80)
    test_products = [
        {'title': 'Yoga mat', 'price': '$45'},
        {'title': 'Hiking boots', 'price': '$120'},
    ]
    recs = build_recommendations_with_regional_intelligence(test_profile, test_products)
    print(f"\nRegional vibe: {recs['regional_vibe']}")
    print(f"Seasonal guidance: {recs['seasonal_guidance'][:100]}...")
    print(f"\nLocal events:")
    for event in recs['local_events'][:3]:
        print(f"  - {event}")
