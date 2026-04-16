"""
Gift Ideator — Concept-first gift generation, unconstrained by product catalog.

Generates gift concepts from profile signals alone. No inventory lookup.
Each concept has a why_perfect rationale and search terms to find it.

The ideator is the first stage of the two-stage ideate→match architecture.
It produces concept specs that can optionally be matched against inventory
(Stage 2) or surfaced directly with search links (concept mode).

Enable concept mode: set GIFT_CONCEPT_MODE=true in Railway env vars.

⚠️  OPUS-ONLY ZONE — Prompt taste layer.
Sonnet sessions: add SONNET-FLAG comments and move on.

Author: Chad + Claude
Date: April 2026
"""

import json
import logging
import os
from typing import Dict, List, Optional
from urllib.parse import quote

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = 'claude-sonnet-4-20250514'

_IDEATOR_SYSTEM = (
    "You are a gift strategist. You generate gift concepts for specific people "
    "based on their interests and personality signals — not from a product catalog. "
    "Your job is ideation, not inventory lookup. Every concept you produce should "
    "make the gift-giver think: I wouldn't have thought of that, but it's exactly right."
)

_IDEATOR_PROMPT = """\
Generate {rec_count} gift concepts for this person.

You have NO product catalog. Ideate freely. Describe the KIND of thing that \
would land — specific enough to find on Google or Amazon in under 60 seconds, \
not so specific you're naming a single SKU.

{ontology_section}\
RECIPIENT PROFILE
Interests: {interests_summary}
{ownership_line}\
{aesthetic_line}\
{price_line}\
{location_line}
HOW STRONG CONCEPTS WORK

A concept lands when it:
- Bridges 2+ of this person's interests. The intersection is where the \
interesting gifts live. "Indie music × thrifting × sustainability" might suggest \
a restored vintage audio piece — not a band t-shirt.
- Names a specific kind of object or experience, not a category. \
"Small-batch natural wine club, farm-direct subscription" is a concept. \
"Wine gift" is not.
- Answers "why wouldn't they buy this for themselves?" in one sentence. \
If you can't answer that, regenerate.
- Would make the gift-giver say "I didn't know that existed" or \
"I wouldn't have thought of that."

A concept fails when it:
- Restates an interest + noun ("into coffee → coffee mug", "hiker → hiking boots")
- Duplicates something they already own (see ownership signals above)
- Could appear unchanged on a generic gift guide

VOICE RULES FOR why_perfect
- Reference specific signals from this profile, not generic praise
- No adverbs: cut "genuinely", "really", "actually", "truly"
- No needle drops: don't end with "that's why this works" or "that's the point"
- No "perfect gift" or "they'll absolutely love it" — describe the fit, not the feeling
- 2-3 sentences max

RULES
- At least 3 concepts must explicitly bridge 2+ signals
- At least 2 should be surprising — things the giver wouldn't naturally reach for
- No gift cards, cash, or vague "experience vouchers" with no specifics
- search_terms must be concrete enough to actually return results on Google
- price_range must be realistic for this type of item

Return JSON only. No markdown fences, no explanation before or after.

{{
  "gift_concepts": [
    {{
      "name": "3-7 word concept label (not a brand name, a concept)",
      "description": "1-2 sentences: what this is specifically and why it fits",
      "why_perfect": "Why this lands for THIS person. Specific. References their actual signals.",
      "signal_intersection": "Which 2+ interests this bridges, or the dominant single signal",
      "search_terms": ["specific search query 1", "specific search query 2"],
      "gift_type": "physical",
      "price_range": "$X\u2013$Y",
      "interest_match": "primary interest label",
      "confidence_level": "safe_bet or adventurous"
    }}
  ]
}}"""


def _format_profile_for_prompt(profile: Dict) -> Dict[str, str]:
    """Extract and format key signals from profile dict for the ideation prompt."""
    interests = profile.get('interests', [])

    interest_parts = []
    for i in interests:
        name = (i.get('name') or '').strip()
        if not name:
            continue
        intensity = (i.get('intensity') or '').strip()
        evidence = (i.get('evidence') or i.get('description') or '').strip()[:120]
        part = name
        if intensity:
            part += f" ({intensity})"
        if evidence:
            part += f" — {evidence}"
        interest_parts.append(part)

    interests_summary = '; '.join(interest_parts) if interest_parts else 'not specified'

    # Ownership signals — things to avoid
    ownership = profile.get('ownership_signals', [])
    if ownership:
        items = ', '.join(str(o) for o in ownership[:10])
        ownership_line = f"Already owns (skip these): {items}\n"
    else:
        ownership_line = ''

    # Aesthetic
    aesthetic = (profile.get('aesthetic_summary') or '').strip()
    aesthetic_line = f"Aesthetic: {aesthetic}\n" if aesthetic else ''

    # Price signals
    price_signals = profile.get('price_signals') or {}
    budget_cat = price_signals.get('budget_category', 'moderate')
    est_range = price_signals.get('estimated_range', '$30–$150')
    price_line = f"Budget: {budget_cat} ({est_range})\n"

    # Location
    loc = profile.get('location_context') or {}
    city = (loc.get('city_region') or '').strip()
    state = (loc.get('state') or '').strip()
    if city and state:
        location_line = f"Location: {city}, {state}\n"
    elif city:
        location_line = f"Location: {city}\n"
    else:
        location_line = ''

    return {
        'interests_summary': interests_summary,
        'ownership_line': ownership_line,
        'aesthetic_line': aesthetic_line,
        'price_line': price_line,
        'location_line': location_line,
    }


def ideate_gifts(
    profile: Dict,
    recipient_type: str,
    relationship: str,
    claude_client,
    rec_count: int = 10,
    ontology_briefing: Optional[str] = None,
    model: Optional[str] = None,
) -> Dict:
    """
    Generate gift concepts unconstrained by product inventory.

    Args:
        profile: Profile dict from profile_analyzer (interests, ownership_signals, etc.)
        recipient_type: 'self' or 'other'
        relationship: e.g. 'close_friend', 'romantic_partner'
        claude_client: Anthropic Claude API client
        rec_count: Number of concepts to generate
        ontology_briefing: Optional briefing from interest_ontology (themes, philosophy)
        model: Claude model override

    Returns:
        Dict matching curate_gifts() format:
        {
            'product_gifts': [list of concept dicts],
            'experience_gifts': [],
            'splurge_item': None,
        }
        Each concept dict has: name, description, why_perfect, search_terms,
        gift_type, price_range, interest_match, confidence_level, signal_intersection,
        is_concept=True, purchase_link (Google search URL), where_to_buy='Search'.
    """
    model = model or os.environ.get('CLAUDE_CURATOR_MODEL', _DEFAULT_MODEL)

    # Build profile summary
    fields = _format_profile_for_prompt(profile)

    ontology_section = ''
    if ontology_briefing and ontology_briefing.strip():
        ontology_section = f"THEMATIC INTELLIGENCE\n{ontology_briefing}\n\n"

    prompt = _IDEATOR_PROMPT.format(
        rec_count=rec_count,
        ontology_section=ontology_section,
        **fields,
    )

    logger.info(f"IDEATOR: Generating {rec_count} gift concepts (model={model})")

    try:
        response = claude_client.messages.create(
            model=model,
            max_tokens=3500,
            system=_IDEATOR_SYSTEM,
            messages=[{'role': 'user', 'content': prompt}],
        )

        raw = response.content[0].text.strip()
        logger.info(f"IDEATOR: Response received ({len(raw)} chars)")

        # Strip markdown fences if model wraps output anyway
        if raw.startswith('```'):
            lines = raw.split('\n')
            raw = '\n'.join(lines[1:])
            if raw.endswith('```'):
                raw = raw[:-3].strip()

        data = json.loads(raw)
        concepts = data.get('gift_concepts', [])
        logger.info(f"IDEATOR: Parsed {len(concepts)} concepts")

    except json.JSONDecodeError as e:
        logger.error(f"IDEATOR: JSON parse failed: {e}")
        logger.error(f"IDEATOR: Raw (first 500): {raw[:500] if 'raw' in dir() else 'n/a'}")
        return {'product_gifts': [], 'experience_gifts': [], 'splurge_item': None}
    except Exception as e:
        logger.error(f"IDEATOR: Claude call failed: {e}")
        return {'product_gifts': [], 'experience_gifts': [], 'splurge_item': None}

    # Convert concepts to product_gift format
    product_gifts = []
    for concept in concepts:
        search_terms = concept.get('search_terms') or []
        primary_search = search_terms[0] if search_terms else concept.get('name', '')
        search_url = f"https://www.google.com/search?q={quote(primary_search)}"

        product_gifts.append({
            'name': concept.get('name', 'Gift Concept'),
            'description': concept.get('description', ''),
            'why_perfect': concept.get('why_perfect', ''),
            'signal_intersection': concept.get('signal_intersection', ''),
            'search_terms': search_terms,
            'gift_type': 'physical',
            'price_range': concept.get('price_range', ''),
            'interest_match': concept.get('interest_match', ''),
            'confidence_level': concept.get('confidence_level', 'safe_bet'),
            'is_concept': True,
            'where_to_buy': 'Search',
            'product_url': search_url,
            'purchase_link': search_url,
            'image_url': '',
        })

    return {
        'product_gifts': product_gifts,
        'experience_gifts': [],
        'splurge_item': None,
    }
