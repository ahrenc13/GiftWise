"""
Intake analyzer — converts conversational embed input into a profile dict
shaped like the fixtures in evals/fixtures.py.

This is the v2 replacement for the Instagram/TikTok scraping path — instead
of pulling signals from social, we ask the giver directly. The output shape
is identical to the existing profile schema so portrait_ideator (and
eventually the production curator) consumes it unchanged.

Usage:
    from intake_analyzer import analyze_intake
    profile = analyze_intake(
        intake_text="She's been getting really into pottery, has a wheel...",
        relationship="romantic_partner",
        budget_category="moderate",
        recipient_name_or_initial="M",
        claude_client=client,
    )
    # profile is a dict with: interests, ownership_signals, style_preferences,
    # price_signals, aspirational_vs_current, gift_avoid, gift_relationship_guidance
"""

import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)


VALID_RELATIONSHIPS = ("close_friend", "romantic_partner", "family_member", "colleague", "other")
VALID_BUDGETS = ("budget", "moderate", "premium", "luxury")


_SYSTEM = """\
You are GiftWise's intake analyzer. You read what a gift-giver tells you about \
the recipient and produce a structured profile that downstream curators use to \
build a gift list.

You are reading a single person — a real human, not an archetype. Resist the \
urge to pad with stereotypical interests; only include what is actually \
supported by what the giver said. If the giver said little, return a thin \
profile honestly — the curator handles thin profiles fine.\
"""


_PROMPT = """\
A gift-giver is describing the recipient. Convert what they said into the \
structured profile schema below.

# What the giver said
{intake_text}

# Structured fields
relationship: {relationship}
budget_category: {budget_category}
recipient_name_or_initial: {name}

---

Return ONLY valid JSON in this exact schema:

{{
  "interests": [
    {{
      "name": "<short interest name>",
      "evidence": "<what the giver said that supports this>",
      "description": "<one sentence>",
      "intensity": "<casual|moderate|passionate>",
      "type": "current",
      "is_work": false,
      "activity_type": "<active|passive|both>",
      "confidence": "<low|medium|high>",
      "signal_quotes": ["<exact phrase from giver, if any>"],
      "signal_momentum": "<rising|stable|declining>"
    }}
  ],
  "location_context": {{
    "city_region": "<if mentioned, else 'unspecified'>",
    "specific_places": [],
    "geographic_constraints": "<if mentioned, else 'unspecified'>"
  }},
  "ownership_signals": ["<thing the giver said the recipient already owns>"],
  "style_preferences": {{
    "visual_style": "<one phrase, or 'unspecified'>",
    "aesthetic_summary": "<one sentence portrait of their sensibility>",
    "colors": [],
    "brands": ["<brand the giver mentioned>"],
    "quality_level": "<budget|mid-range|premium|luxury|unspecified>"
  }},
  "price_signals": {{
    "estimated_range": "<derived from budget_category>",
    "budget_category": "{budget_category}",
    "notes": "<any pricing context the giver gave>"
  }},
  "aspirational_vs_current": {{
    "aspirational": ["<thing the giver said they want or are working toward>"],
    "current": ["<thing the giver said they currently do>"],
    "gaps": ["<thing the giver said they want but don't have>"]
  }},
  "gift_avoid": ["<thing the giver explicitly said to avoid>"],
  "specific_venues": [],
  "gift_relationship_guidance": {{
    "appropriate_types": ["<types of gifts that fit this relationship>"],
    "boundaries": "<one phrase about what fits {relationship}>",
    "intimacy_level": "<one phrase>"
  }}
}}

Rules:
- Only include interests, ownership signals, gaps, etc. that the giver \
  actually said or that are clearly implied. Do not invent.
- If the giver said almost nothing, return a thin profile (1-2 interests, \
  empty arrays where appropriate). Do not pad.
- For signal_quotes, include verbatim phrases from the giver's text only.
- intensity defaults to "moderate" when unclear; confidence defaults to "medium".
- estimated_range from budget_category: budget→$25-75, moderate→$75-200, \
  premium→$100-300, luxury→$200-600.\
"""


def _strip_fences(raw: str) -> str:
    s = raw.strip()
    if s.startswith("```"):
        s = s.split("```")[1]
        if s.startswith("json"):
            s = s[4:]
        s = s.strip()
    return s


def analyze_intake(
    *,
    intake_text: str,
    relationship: str,
    budget_category: str,
    recipient_name_or_initial: Optional[str] = None,
    claude_client,
    model: str = "claude-sonnet-4-6",
) -> dict:
    """
    Convert conversational intake into a profile dict shaped for the curator.

    Args:
        intake_text: free-text from the giver describing the recipient
        relationship: one of VALID_RELATIONSHIPS
        budget_category: one of VALID_BUDGETS
        recipient_name_or_initial: optional, for the prompt only — not stored
        claude_client: anthropic.Anthropic instance
        model: which Claude model

    Returns:
        Profile dict with the same top-level keys as evals/fixtures.py profiles.

    Raises:
        ValueError if inputs are invalid or the model returns unparseable JSON.
    """
    if relationship not in VALID_RELATIONSHIPS:
        raise ValueError(f"relationship must be one of {VALID_RELATIONSHIPS}")
    if budget_category not in VALID_BUDGETS:
        raise ValueError(f"budget_category must be one of {VALID_BUDGETS}")
    if not intake_text or len(intake_text.strip()) < 10:
        raise ValueError("intake_text must contain at least 10 characters")

    name = recipient_name_or_initial.strip() if recipient_name_or_initial else "(unspecified)"

    prompt = _PROMPT.format(
        intake_text=intake_text.strip(),
        relationship=relationship,
        budget_category=budget_category,
        name=name,
    )

    logger.info(f"INTAKE: calling {model} with {len(prompt)} char prompt (intake {len(intake_text)} chars)")

    response = claude_client.messages.create(
        model=model,
        max_tokens=2500,
        system=_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.content[0].text

    try:
        profile = json.loads(_strip_fences(raw))
    except json.JSONDecodeError as e:
        logger.error(f"INTAKE: JSON parse failed: {e}")
        logger.error(f"INTAKE: raw[:500]={raw[:500]}")
        raise ValueError(f"intake analyzer produced invalid JSON: {e}")

    # Backfill required fields the prompt shape demands but the model
    # might omit on a thin profile.
    profile.setdefault("interests", [])
    profile.setdefault("ownership_signals", [])
    profile.setdefault("specific_venues", [])
    profile.setdefault("gift_avoid", [])
    profile.setdefault("location_context", {"city_region": "unspecified", "specific_places": [], "geographic_constraints": "unspecified"})
    profile.setdefault("style_preferences", {"visual_style": "unspecified", "aesthetic_summary": "", "colors": [], "brands": [], "quality_level": "unspecified"})
    profile.setdefault("price_signals", {"estimated_range": "", "budget_category": budget_category, "notes": ""})
    profile.setdefault("aspirational_vs_current", {"aspirational": [], "current": [], "gaps": []})
    profile.setdefault("gift_relationship_guidance", {"appropriate_types": [], "boundaries": "", "intimacy_level": ""})

    logger.info(f"INTAKE: parsed {len(profile.get('interests', []))} interests, "
                f"{len(profile.get('ownership_signals', []))} ownership signals")
    return profile
