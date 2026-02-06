"""
PROFILE DISPLAY HELPER - Format Gift Strategy Summary
Produces the "Gift Strategy" section for the profile review page.

Author: Chad + Claude
Date: February 2026
"""


def format_gift_strategy(profile):
    """
    Build a concise Gift Strategy summary from profile intelligence.
    Shows gaps (best gift opportunities), aspirational interests, and things to avoid.

    Args:
        profile: Complete recipient profile dict

    Returns:
        HTML string for display with Jinja2 | safe filter, or empty string if no data.
    """
    if not profile:
        return ""

    asp_curr = profile.get('aspirational_vs_current', {})
    current = asp_curr.get('current', [])[:5]
    aspirational = asp_curr.get('aspirational', [])[:5]
    gaps = asp_curr.get('gaps', [])[:4]
    avoid = profile.get('gift_avoid', [])[:6]

    if not gaps and not current and not aspirational and not avoid:
        return ""

    parts = []

    if gaps:
        parts.append(
            '<div class="strategy-block">'
            '<span class="strategy-icon">🎯</span>'
            f'<div><strong>Best gift opportunities:</strong> {_esc(", ".join(gaps))}'
            '<br><span class="strategy-hint">Things they want but don\'t have yet</span></div>'
            '</div>'
        )

    if aspirational:
        parts.append(
            '<div class="strategy-block">'
            '<span class="strategy-icon">✨</span>'
            f'<div><strong>Aspiring to:</strong> {_esc(", ".join(aspirational))}</div>'
            '</div>'
        )

    if current:
        parts.append(
            '<div class="strategy-block">'
            '<span class="strategy-icon">💚</span>'
            f'<div><strong>Already into:</strong> {_esc(", ".join(current))}</div>'
            '</div>'
        )

    if avoid:
        parts.append(
            '<div class="strategy-block">'
            '<span class="strategy-icon">🚫</span>'
            f'<div><strong>Avoid:</strong> {_esc(", ".join(avoid))}</div>'
            '</div>'
        )

    return "\n".join(parts)


def _esc(text):
    """Escape HTML special characters in user-provided text."""
    if not text:
        return ''
    return str(text).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')
