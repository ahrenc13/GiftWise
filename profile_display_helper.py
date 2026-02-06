"""
PROFILE DISPLAY HELPER - Format Intelligence Summary
Converts technical profile data into conversational, human-readable summaries

Author: Chad + Claude
Date: February 2026
"""


def format_intelligence_summary(profile):
    """
    Format rich profile data into conversational summary for profile review page.

    This replaces the simple "Location: Indianapolis" with a comprehensive but
    readable summary that showcases the depth of analysis.

    Args:
        profile: Complete recipient profile dict

    Returns:
        Formatted HTML string for display (used with Jinja2 | safe filter)
    """

    if not profile:
        return "<p>No profile information available</p>"

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
        location_text = "<strong>Where They Live &amp; Go</strong><br>"
        if city:
            if places:
                places_str = ', '.join(_esc(p) for p in places)
                location_text += f"Based in {_esc(city)}, with regular visits to {places_str}. "
            else:
                location_text += f"Based in {_esc(city)}. "

        if constraints:
            location_text += _esc(constraints)

        sections.append(location_text.strip())

    # === Style & Preferences ===
    visual_style = style.get('visual_style', '')
    brands = style.get('brands', [])[:5]
    quality = style.get('quality_level', '')

    if visual_style or brands or quality:
        style_text = "<strong>Their Style</strong><br>"

        if visual_style:
            style_text += f"{_esc(visual_style)} aesthetic"

        if brands:
            brands_str = ', '.join(_esc(b) for b in brands)
            if visual_style:
                style_text += f" with a preference for brands like {brands_str}"
            else:
                style_text += f"Gravitates toward brands like {brands_str}"

        if quality:
            if visual_style or brands:
                style_text += f". {_esc(quality)}"
            else:
                style_text += _esc(quality)

        if not style_text.endswith('.'):
            style_text += '.'

        sections.append(style_text)

    # === Budget ===
    price_range = price.get('estimated_range', '')
    budget_cat = price.get('budget_category', '')

    if price_range or budget_cat:
        price_text = "<strong>Budget Signals</strong><br>"
        if price_range:
            price_text += f"Comfortable range: {_esc(price_range)}"
        if budget_cat:
            if price_range:
                price_text += f" ({_esc(budget_cat)})"
            else:
                price_text += _esc(budget_cat)
        if not price_text.endswith('.'):
            price_text += '.'
        sections.append(price_text)

    # === Gift Sweet Spots (THE MONEY SECTION) ===
    current = asp_curr.get('current', [])[:5]
    aspirational = asp_curr.get('aspirational', [])[:5]
    gaps = asp_curr.get('gaps', [])[:4]

    if gaps or current or aspirational:
        sweet_spot_text = "<strong>Gift Sweet Spots 🎯</strong><br>"

        if gaps:
            current_str = ', '.join(_esc(c) for c in current)
            aspirational_str = ', '.join(_esc(a) for a in aspirational)
            gaps_str = ', '.join(_esc(g) for g in gaps)
            sweet_spot_text += f"Currently into: {current_str}<br>"
            sweet_spot_text += f"Aspiring to: {aspirational_str}<br>"
            sweet_spot_text += f"<strong>The gap between these is your best gift zone</strong> &mdash; {gaps_str}."
        elif current and aspirational:
            all_interests = list(set(current + aspirational))[:6]
            sweet_spot_text += f"Active interests: {', '.join(_esc(i) for i in all_interests)}"
        elif current:
            sweet_spot_text += f"Current interests: {', '.join(_esc(c) for c in current)}"
        elif aspirational:
            sweet_spot_text += f"Aspiring interests: {', '.join(_esc(a) for a in aspirational)}"

        sections.append(sweet_spot_text)

    # === Things to Avoid ===
    avoid = profile.get('gift_avoid', [])[:6]

    if avoid:
        avoid_text = f"<strong>What to Avoid</strong><br>{', '.join(_esc(a) for a in avoid)}"
        sections.append(avoid_text)

    # === Specific Venues ===
    venues = profile.get('specific_venues', [])[:4]
    venue_names = [v.get('name', '') for v in venues if v.get('name')]

    if venue_names:
        venue_text = f"<strong>Venues They Know</strong><br>{', '.join(_esc(v) for v in venue_names)} &mdash; experiences at familiar places will resonate."
        sections.append(venue_text)

    # === Work Context (Hidden unless needed for debugging) ===
    # Don't show this to user, but keep the data structure for internal use

    # Combine all sections
    if not sections:
        return "<p><strong>Profile Analysis</strong><br>Analyzing social media activity to build personalized recommendations...</p>"

    return "<br><br>".join(sections)


def format_intelligence_summary_compact(profile):
    """
    Compact version for mobile or limited space.
    Shows only the essentials: location, sweet spots, avoid.

    Args:
        profile: Complete recipient profile dict

    Returns:
        Compact formatted HTML string
    """

    if not profile:
        return "<p>No profile information available</p>"

    sections = []

    # Location (one line)
    city = profile.get('location_context', {}).get('city_region', '')
    if city:
        sections.append(f"📍 {_esc(city)}")

    # Sweet spots (prioritize gaps)
    asp_curr = profile.get('aspirational_vs_current', {})
    gaps = asp_curr.get('gaps', [])[:3]

    if gaps:
        sections.append(f"🎯 Best opportunities: {', '.join(_esc(g) for g in gaps)}")
    else:
        current = asp_curr.get('current', [])[:4]
        if current:
            sections.append(f"🎯 Into: {', '.join(_esc(c) for c in current)}")

    # Avoid
    avoid = profile.get('gift_avoid', [])[:3]
    if avoid:
        sections.append(f"❌ Avoid: {', '.join(_esc(a) for a in avoid)}")

    return "<br>".join(sections) if sections else "<p>Analyzing profile...</p>"


def _esc(text):
    """Escape HTML special characters in user-provided text."""
    if not text:
        return ''
    return str(text).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')
