"""
Portrait-shaped curator prototype.

This is the architectural counter-proposal to the current pipeline:
  current = profile_analyzer (LLM #1) -> ontology -> per-interest search ->
            gift_curator/gift_ideator (LLM #2) picks per silo
  portrait = single LLM call that:
    1. synthesizes a *portrait* (not a tag list) from the profile
    2. extracts 2-4 cross-cutting through-lines
    3. composes a list with explicit shape (anchor / resonant /
       surprising / aspirational / restraint)
    4. self-critiques: would a stranger think a person curated this,
       or a tag-matcher?

No inventory required for this prototype. We are testing whether the
*prompt architecture* produces better-shaped recommendations, not whether
it can match against the current catalog. Once we know the architecture
moves the quality bar, we layer inventory.

Output schema mirrors gift_ideator.ideate_gifts so evals/judge.py can
score it unchanged. Three new fields are added for the new judge
dimensions:
  portrait_prose      str   - the synthesized portrait the agent wrote
  through_lines       list  - the 2-4 cross-cutting threads
  restraint_omitted   list  - signals deliberately NOT made literal in picks

Usage:
  from evals.portrait_ideator import ideate_gifts_portrait
  out = ideate_gifts_portrait(fixture['profile'], 'other', 'close_friend',
                              client, model='claude-opus-4-7')
"""

import json
import logging

logger = logging.getLogger(__name__)


_SYSTEM = """\
You are GiftWise's senior gift curator. Your job is not to match interests \
to products. Your job is to read a person and compose a gift list that \
demonstrates you understood them.

The bar is set by the best human gift-givers and curators (Wirecutter \
gift guides, Blackbird Spyplane, Brain Pickings, top personal shoppers \
at Bergdorf or Mr. Porter). They never sample-by-tag. They build a \
portrait of the person and let the portrait drive the picks.

Failure modes to avoid:
  - On-the-nose: "She likes fly fishing -> here is fly fishing gear"
  - Tag-stacking: every item tries to combine every signal (Frankenstein gifts)
  - Hedge-and-cover: one item per stated interest, no synthesis
  - Generic: items that could go to anyone with this hobby
  - Literalism: recommending the obvious thing for an explicit signal when \
    a sideways pick would say "I see you" louder

Excellence looks like:
  - The list, read together, feels like a portrait of a specific person
  - Some items resonate with multiple signals; some are quietly on-theme
  - Negative space is used: not every signal needs to be visible in a pick
  - At least one pick is surprising-but-obvious-in-retrospect
  - The splurge is "the thing that says I see you" — not just expensive\
"""


_PROMPT = """\
Compose a gift list for the person profiled below.

Work in four phases. Show your work for phase 1 and 2 in the output JSON.

# Phase 1 — Portrait
Write a 4-6 sentence prose portrait. Not a list of facts; a reading of a \
person. Capture sensibility, values, the texture of their life, what they \
are becoming, and the negative space (what they would NOT want to be).

# Phase 2 — Through-lines
Identify 2-4 cross-cutting threads. Each thread is a short phrase that \
braids multiple signals into one essence. Examples (do not copy these):
  - "patience as practice" (binds fly fishing + ceramics + slow reading)
  - "objects that improve with use" (binds leather goods + cast iron + denim)
A through-line is NOT an interest. It is the *why* underneath the interests.

# Phase 3 — Composition
Compose {rec_count} regular gifts + 1 splurge. Each item fills a slot. \
Use these slots in roughly this distribution across the {rec_count} regulars:
  anchor       2-3 items - the most obvious thing a thoughtful gift-giver
                          would think of for this person, well-chosen.
                          AT LEAST ONE anchor must be allowed to be earnest
                          and on-signal — its why_perfect should be permitted
                          to say "she ties her own flies, and this is the
                          best premium tool kit at her level" without
                          invoking a through-line. The architecture's value
                          is in the rest of the list, not in dressing up
                          every pick as synthesis.
  resonant     3-4 items - sits at intersection of 2+ signals or a through-line.
  surprising   2-3 items - adjacent, unexpected, but obvious in retrospect.
  aspirational 1-2 items - speaks to who they are becoming, not who they are.

The splurge slot is "portrait-as-object": the single most expensive thing \
that says I see you. Not the most expensive product in their interest \
category; the most resonant.

# Texture rule

A great gift list is photographable. Across the {rec_count} regulars, no \
more than 2 picks may be subscriptions, memberships, software licenses, \
gift cards, or other intangibles. Prefer items with sensory specificity — \
a material, a weight, a sound, a smell, a color you can name. "Snow Peak \
titanium mug" beats "annual coffee subscription" for the same person, \
same budget, same occasion. If you find yourself reaching for an abstract \
service, ask: is there a physical object that does the same emotional work?

This is not a rule against experiences (the splurge can be one) or against \
pragmatism (Darn Tough socks are great). It is a rule against a list whose \
dominant texture is "things she'll receive in her email inbox over the \
next year."

# Phase 4 — Restraint
Before finalizing, list any signals from the profile that you DELIBERATELY \
did not make literal in the picks. This is not failure to cover them — \
it is restraint. Explain why each was held back (e.g., "her veganism is \
a value, not a hobby — I let it shape what I avoided rather than what I \
recommended").

# Profile
{profile_json}

# Recipient context
recipient_type: {recipient_type}
relationship: {relationship}

# Ownership signals (do NOT recommend any of these or near-duplicates)
{ownership_block}

# Things to avoid
{avoid_block}

{voice_block}

---

Return ONLY valid JSON in this exact schema:

{{
  "portrait_prose": "<phase 1 output, 4-6 sentences>",
  "through_lines": [
    {{"phrase": "<short>", "binds": ["<signal>", "<signal>"], "why": "<one sentence>"}}
  ],
  "product_gifts": [
    {{
      "name": "<gift concept name>",
      "description": "<one sentence describing the gift>",
      "why_perfect": "<why THIS person, citing the portrait or through-lines, not just an interest tag>",
      "price_range": "<$X-Y>",
      "slot": "<anchor|resonant|surprising|aspirational>",
      "signals_engaged": ["<signal or through-line names this item plays on>"]
    }}
  ],
  "splurge_item": {{
    "name": "<splurge concept name>",
    "description": "<one sentence>",
    "why_perfect": "<why THIS is the portrait-as-object choice>",
    "price_range": "<$X-Y>",
    "signals_engaged": ["<...>"]
  }},
  "restraint_omitted": [
    {{"signal": "<signal name from profile>", "why_held_back": "<one sentence>"}}
  ]
}}

Hard rules:
- Do not recommend anything in the ownership signals list above.
- Do not recommend anything in the avoid list above.
- Splurge price must be appropriate to budget_category in the profile \
  (budget: <=$300, moderate: <=$500, premium: <=$1000, luxury: <=$1500).
- Every product_gift's why_perfect must reference the portrait OR a \
  through-line OR specific evidence quotes — not just "they like X".
- Slots must be roughly balanced. A list of 10 anchors fails this rubric.\
"""


def _build_voice_block(voice_axis: float) -> str:
    """
    Inject voice-axis guidance that overrides phase 3 slot distribution and
    why_perfect style. voice_axis in [0.0, 1.0]:
        <= 0.3 = practical (on-signal, actionable)
        0.3 < v < 0.7 = balanced (use phase 3 defaults)
        >= 0.7 = taste-edited (synthesis, sensibility)
    """
    if voice_axis <= 0.3:
        return f"""# Voice setting: practical (voice_axis = {voice_axis:.2f})

This curator's audience prefers practical, on-signal, actionable picks over \
taste-edited ones. They want gifts the recipient will use on Tuesday, not \
gifts that demonstrate the giver's sensibility.

OVERRIDE the phase 3 slot distribution with this one (totals MUST equal the \
regular pick count exactly — do not exceed it):
  anchor       5 items - lean heavily into obvious-and-perfect picks. Most
                        of the list lives here.
  resonant     3 items - keep some synthesis, but don't lead with it.
  surprising   1 item  - one quietly surprising pick is enough.
  aspirational 1 item  - the aspirational pick must tie to a concrete next
                        step (a class, a course, a specific trip), not a
                        vague gesture toward who they're becoming.

why_perfect style: concrete, immediate, utility-forward. Pretend you are \
writing for a reader who skims and decides in 5 seconds. Avoid through-line \
language unless it earns its place. "She ties her own flies and this is the \
best premium tool kit at her level" beats "honoring the craft beneath the \
sport, this dignifies the bench." When in doubt, cut the metaphor.

The portrait_prose, through_lines, and restraint_omitted fields stay — they \
are the foundation. Only the picks themselves shift toward utility.\
"""
    if voice_axis >= 0.7:
        return f"""# Voice setting: taste-edited (voice_axis = {voice_axis:.2f})

This curator's audience expects taste-edited curation — synthesis, restraint, \
sensibility. They are reading a gift list the way they read Blackbird Spyplane \
or a Wirecutter gift guide: for the editor's eye, not for shopping convenience.

OVERRIDE the phase 3 slot distribution with this one (totals MUST equal the \
regular pick count exactly — do not exceed it):
  anchor       2 items - keep ONE-TO-TWO earnest anchors as required, but
                        lean elsewhere. Most of the list is not anchor.
  resonant     4 items - synthesis is the headline. Most picks should
                        braid 2+ signals or sit on a through-line.
  surprising   3 items - the surprising-but-obvious-in-retrospect pick is
                        essential, not optional.
  aspirational 1 item  - point at who they are becoming.

why_perfect style: name the through-line, name the sensibility, trust the \
reader. Resonance over utility when both could fit. "Yanagi is the philosophical \
bedrock under everything she's drawn to" is the right register.

The portrait_prose, through_lines, and restraint_omitted fields are \
load-bearing here — they explain why each pick lives where it does.\
"""
    return f"""# Voice setting: balanced (voice_axis = {voice_axis:.2f})

Use the default slot distribution from phase 3. Mix practical and taste-edited \
freely. Both why_perfect styles are welcome.\
"""


def _build_ownership_block(profile: dict) -> str:
    items = profile.get("ownership_signals", [])
    if not items:
        return "(none specified)"
    return "\n".join(f"  - {x}" for x in items)


def _build_avoid_block(profile: dict) -> str:
    items = profile.get("gift_avoid", [])
    if not items:
        return "(none specified)"
    return "\n".join(f"  - {x}" for x in items)


def _strip_fences(raw: str) -> str:
    s = raw.strip()
    if s.startswith("```"):
        s = s.split("```")[1]
        if s.startswith("json"):
            s = s[4:]
        s = s.strip()
    return s


def ideate_gifts_portrait(
    profile: dict,
    recipient_type: str,
    relationship: str,
    claude_client,
    rec_count: int = 10,
    model: str = "claude-opus-4-7",
    voice_axis: float = 0.5,
) -> dict:
    """
    Single-call portrait-shaped curator. Returns the same top-level keys
    as gift_ideator.ideate_gifts (product_gifts, splurge_item) plus three
    new fields (portrait_prose, through_lines, restraint_omitted) that
    the new judge dimensions will read.

    voice_axis in [0.0, 1.0]:
        <= 0.3 = practical (on-signal, actionable)
        0.3 < v < 0.7 = balanced (default)
        >= 0.7 = taste-edited (synthesis, sensibility)
    The validation revealed that some users prefer practical over taste-edited
    even when the latter scores higher on synthesis. Production partners will
    set this per their audience.

    No experience_gifts in this prototype — we are isolating the curation
    architecture question. Experiences can be layered back later.
    """
    if not (0.0 <= voice_axis <= 1.0):
        raise ValueError(f"voice_axis must be in [0.0, 1.0], got {voice_axis}")

    profile_for_prompt = {
        k: v for k, v in profile.items()
        if k in (
            "interests",
            "location_context",
            "style_preferences",
            "price_signals",
            "aspirational_vs_current",
            "gift_relationship_guidance",
        )
    }

    prompt = _PROMPT.format(
        rec_count=rec_count,
        profile_json=json.dumps(profile_for_prompt, indent=2),
        recipient_type=recipient_type,
        relationship=relationship,
        ownership_block=_build_ownership_block(profile),
        avoid_block=_build_avoid_block(profile),
        voice_block=_build_voice_block(voice_axis),
    )

    logger.info(f"PORTRAIT: calling {model} (voice_axis={voice_axis:.2f}) with {len(prompt)} char prompt")

    response = claude_client.messages.create(
        model=model,
        max_tokens=4000,
        system=_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.content[0].text

    try:
        parsed = json.loads(_strip_fences(raw))
    except json.JSONDecodeError as e:
        logger.error(f"PORTRAIT: JSON parse failed: {e}")
        logger.error(f"PORTRAIT: raw[:500]={raw[:500]}")
        return {
            "product_gifts": [],
            "experience_gifts": [],
            "splurge_item": None,
            "portrait": None,
            "portrait_prose": None,
            "through_lines": [],
            "restraint_omitted": [],
            "_parse_error": str(e),
            "_raw": raw,
        }

    return {
        "product_gifts": parsed.get("product_gifts", []),
        "experience_gifts": [],
        "splurge_item": parsed.get("splurge_item"),
        "portrait": None,
        "portrait_prose": parsed.get("portrait_prose"),
        "through_lines": parsed.get("through_lines", []),
        "restraint_omitted": parsed.get("restraint_omitted", []),
    }
