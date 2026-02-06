"""
PROFILE DISPLAY HELPER - Format Intelligence Summary
Converts technical profile data into conversational, human-readable summaries

Author: Chad + Claude
Date: February 2026
"""


def format_intelligence_summary(profile):
    """
    Format rich profile data into conversational summary for "Other Info" section.
    
    This replaces the simple "Location: Indianapolis" with a comprehensive but
    readable summary that showcases the depth of analysis.
    
    Args:
        profile: Complete recipient profile dict
        
    Returns:
        Formatted string (markdown) for display
    """
    
    if not profile:
        return "No profile information available"
    
    location_ctx = profile.get('location_context', {})
    style = profile.get('style_preferences', {})
    price = profile.get('price_signals', {})
    asp_curr = profile.get('aspirational_vs_current', {})
    
    sections = []
    
    # === Location & Places ===
    city = location_ctx.get('city_region', '')
    places = location_ctx.get('specific_places', [])[:4]
    constraints = location_ctx.get('geographic_constraints', '')
    
    if city or places:
        location_text = f"**Where They Live & Go**  \n"
        if city:
            if places:
                places_str = ', '.join(places)
                location_text += f"Based in {city}, with regular visits to {places_str}. "
            else:
                location_text += f"Based in {city}. "
        
        if constraints:
            location_text += constraints
        
        sections.append(location_text.strip())
    
    # === Style & Preferences ===
    visual_style = style.get('visual_style', '')
    brands = style.get('brands', [])[:5]
    quality = style.get('quality_level', '')
    
    if visual_style or brands or quality:
        style_text = "**Their Style**  \n"
        
        if visual_style:
            style_text += f"{visual_style} aesthetic"
        
        if brands:
            brands_str = ', '.join(brands)
            if visual_style:
                style_text += f" with a preference for brands like {brands_str}"
            else:
                style_text += f"Gravitates toward brands like {brands_str}"
        
        if quality:
            if visual_style or brands:
                style_text += f". {quality}"
            else:
                style_text += quality
        
        if not style_text.endswith('.'):
            style_text += '.'
        
        sections.append(style_text)
    
    # === Budget ===
    price_range = price.get('estimated_range', '')
    budget_cat = price.get('budget_category', '')
    
    if price_range or budget_cat:
        price_text = "**Budget Signals**  \n"
        if price_range:
            price_text += f"Comfortable range: {price_range}"
        if budget_cat:
            if price_range:
                price_text += f" ({budget_cat})"
            else:
                price_text += budget_cat
        if not price_text.endswith('.'):
            price_text += '.'
        sections.append(price_text)
    
    # === Gift Sweet Spots (THE MONEY SECTION) ===
    current = asp_curr.get('current', [])[:5]
    aspirational = asp_curr.get('aspirational', [])[:5]
    gaps = asp_curr.get('gaps', [])[:4]
    
    if gaps or current or aspirational:
        sweet_spot_text = "**Gift Sweet Spots 🎯**  \n"
        
        if gaps:
            # This is the best case - we have clear gaps
            sweet_spot_text += f"Currently into: {', '.join(current)}  \n"
            sweet_spot_text += f"Aspiring to: {', '.join(aspirational)}  \n"
            sweet_spot_text += f"**The gap between these is your best gift zone** — {', '.join(gaps)}."
        elif current and aspirational:
            # We have both but no explicit gaps
            all_interests = list(set(current + aspirational))[:6]
            sweet_spot_text += f"Active interests: {', '.join(all_interests)}"
        elif current:
            # Only current
            sweet_spot_text += f"Current interests: {', '.join(current)}"
        elif aspirational:
            # Only aspirational
            sweet_spot_text += f"Aspiring interests: {', '.join(aspirational)}"
        
        sections.append(sweet_spot_text)
    
    # === Things to Avoid ===
    avoid = profile.get('gift_avoid', [])[:6]
    
    if avoid:
        avoid_text = f"**What to Avoid**  \n{', '.join(avoid)}"
        sections.append(avoid_text)
    
    # === Specific Venues ===
    venues = profile.get('specific_venues', [])[:4]
    venue_names = [v.get('name', '') for v in venues if v.get('name')]
    
    if venue_names:
        venue_text = f"**Venues They Know**  \n{', '.join(venue_names)} — experiences at familiar places will resonate."
        sections.append(venue_text)
    
    # === Work Context (Hidden unless needed for debugging) ===
    # Don't show this to user, but keep the data structure for internal use
    
    # Combine all sections
    if not sections:
        return "**Profile Analysis**  \nAnalyzing social media activity to build personalized recommendations..."
    
    return "\n\n".join(sections)


def format_intelligence_summary_compact(profile):
    """
    Compact version for mobile or limited space.
    Shows only the essentials: location, sweet spots, avoid.
    
    Args:
        profile: Complete recipient profile dict
        
    Returns:
        Compact formatted string (markdown)
    """
    
    if not profile:
        return "No profile information available"
    
    sections = []
    
    # Location (one line)
    city = profile.get('location_context', {}).get('city_region', '')
    if city:
        sections.append(f"📍 {city}")
    
    # Sweet spots (prioritize gaps)
    asp_curr = profile.get('aspirational_vs_current', {})
    gaps = asp_curr.get('gaps', [])[:3]
    
    if gaps:
        sections.append(f"🎯 Best opportunities: {', '.join(gaps)}")
    else:
        current = asp_curr.get('current', [])[:4]
        if current:
            sections.append(f"🎯 Into: {', '.join(current)}")
    
    # Avoid
    avoid = profile.get('gift_avoid', [])[:3]
    if avoid:
        sections.append(f"❌ Avoid: {', '.join(avoid)}")
    
    return "  \n".join(sections) if sections else "Analyzing profile..."
