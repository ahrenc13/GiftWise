"""
Judge v2 — adds dimensions that capture the "portrait quality" we are
trying to measure but the v1 judge does not.

v1 dimensions (still used, imported as-is from judge.py):
  specificity, evidence_grounding, splurge_integrity,
  ownership_avoidance, diversity

v2 adds:
  synthesis           - do items braid multiple signals where natural,
                        rather than each playing one tag?
  composition_shape   - does the list have shape (anchor/resonant/
                        surprising/aspirational), or is it flat?
  surprise_in_retrospect - is at least one pick unexpected but obviously
                        right once you read it? (this is the moat)
  restraint           - is there evidence of NOT covering every signal
                        literally? a short omitted-list in the output is
                        a positive signal; so is a list that holds back
                        on a signal we can see in the profile.
  portrait_coherence  - read the list as a stranger; does it feel like
                        a person who knows the giftee curated it, or
                        like a tag-matcher?

A score < 3 on any of these flags. portrait_coherence < 3 is a hard
fail — that is the headline "is this differentiated" signal.
"""

import json
import logging

logger = logging.getLogger(__name__)


_SYSTEM = """\
You are a senior taste editor evaluating a gift list for craft and \
intelligence. You are not scoring whether the items match the person's \
hobbies — that is table stakes. You are scoring whether this reads like \
a gift list a thoughtful human curator would produce, or like a tag-matcher.

Be strict. A 5 is rare. The reference points are Wirecutter gift guides, \
Blackbird Spyplane recommendations, top personal shoppers. A 3 is \
"acceptable but forgettable — could be from anywhere".\
"""


_PROMPT = """\
Evaluate this gift list against the profile.

# Profile (full)
Interests: {interest_summary}
Aesthetic: {aesthetic_summary}
Owns: {ownership_summary}
Aspirational: {aspirational_summary}
Budget: {budget_category}
Relationship: {relationship}

# Gift list
{concepts_block}

# Splurge
{splurge_block}

# Optional: portrait the curator wrote (if any)
{portrait_block}

# Optional: through-lines the curator extracted (if any)
{throughlines_block}

# Optional: signals the curator deliberately omitted (if any)
{restraint_block}

---

Score each dimension 1-5. Return ONLY valid JSON in this exact schema:

{{
  "synthesis": {{
    "score": <1-5>,
    "note": "<one sentence — do items braid multiple signals or each play one tag?>"
  }},
  "composition_shape": {{
    "score": <1-5>,
    "note": "<one sentence — is there a mix of anchor/resonant/surprising/aspirational?>"
  }},
  "surprise_in_retrospect": {{
    "score": <1-5>,
    "note": "<one sentence — is at least one pick unexpected but obviously right?>"
  }},
  "restraint": {{
    "score": <1-5>,
    "note": "<one sentence — is there evidence of holding back on literal signal coverage?>"
  }},
  "portrait_coherence": {{
    "score": <1-5>,
    "note": "<one sentence — does the list read like a person curated it, or a tag-matcher?>"
  }}
}}

Scoring guide:
5 = Excellent. A taste editor would publish this list.
4 = Strong. Clearly thoughtful, minor flat moments.
3 = Acceptable. Relevant, not memorable. Reads as competent.
2 = Weak. Reads as tag-matched output with a thin gloss of personalization.
1 = Bad. Obvious tag-match, no synthesis, no shape, no surprise.

Calibration anchors for portrait_coherence specifically:
- A list that is one item per stated interest, in interest order, with \
  why_perfect that just says "they like X" -> score 2.
- A list where some items hit through-lines, ordering varies, and the \
  splurge says something true about the person -> score 4.\
"""


def _summarize_interests(profile: dict) -> str:
    return ", ".join(
        f"{i['name']} ({i['intensity']}, {i.get('signal_momentum', 'stable')})"
        for i in profile.get("interests", [])
    )


def _aesthetic(profile: dict) -> str:
    return profile.get("style_preferences", {}).get("aesthetic_summary", "(unspecified)")


def _aspirational(profile: dict) -> str:
    asp = profile.get("aspirational_vs_current", {}).get("aspirational", [])
    return "; ".join(asp) if asp else "(none)"


def _concepts_block(output: dict) -> str:
    items = output.get("product_gifts", [])
    if not items:
        return "(no items)"
    lines = []
    for i, c in enumerate(items, 1):
        slot = c.get("slot", "(no slot)")
        signals = c.get("signals_engaged", [])
        signals_str = ", ".join(signals) if signals else "(none stated)"
        lines.append(f"{i}. [{slot}] {c.get('name', '(unnamed)')}")
        lines.append(f"   {c.get('description', '')[:140]}")
        lines.append(f"   Why: {c.get('why_perfect', '')[:240]}")
        lines.append(f"   Engages: {signals_str}")
        lines.append(f"   Price: {c.get('price_range', '?')}")
        lines.append("")
    return "\n".join(lines)


def _splurge_block(output: dict) -> str:
    s = output.get("splurge_item")
    if not s:
        return "(no splurge)"
    return (
        f"Name: {s.get('name', '(unnamed)')}\n"
        f"Why: {s.get('why_perfect', '')[:300]}\n"
        f"Price: {s.get('price_range', '?')}"
    )


def _portrait_block(output: dict) -> str:
    p = output.get("portrait_prose")
    return p if p else "(none — current pipeline does not produce a prose portrait)"


def _throughlines_block(output: dict) -> str:
    tls = output.get("through_lines", [])
    if not tls:
        return "(none — current pipeline does not produce through-lines)"
    return "\n".join(
        f"  - {t.get('phrase', '?')}: binds {t.get('binds', [])} ({t.get('why', '')[:120]})"
        for t in tls
    )


def _restraint_block(output: dict) -> str:
    r = output.get("restraint_omitted", [])
    if not r:
        return "(none stated by curator)"
    return "\n".join(
        f"  - {x.get('signal', '?')}: {x.get('why_held_back', '')[:120]}"
        for x in r
    )


def score_output_v2(fixture: dict, output: dict, claude_client, model: str = "claude-sonnet-4-6") -> dict:
    profile = fixture["profile"]

    prompt = _PROMPT.format(
        interest_summary=_summarize_interests(profile),
        aesthetic_summary=_aesthetic(profile),
        ownership_summary="; ".join(profile.get("ownership_signals", [])),
        aspirational_summary=_aspirational(profile),
        budget_category=profile.get("price_signals", {}).get("budget_category", "?"),
        relationship=fixture.get("relationship", "?"),
        concepts_block=_concepts_block(output),
        splurge_block=_splurge_block(output),
        portrait_block=_portrait_block(output),
        throughlines_block=_throughlines_block(output),
        restraint_block=_restraint_block(output),
    )

    try:
        response = claude_client.messages.create(
            model=model,
            max_tokens=700,
            system=_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()
        scores = json.loads(raw)
    except Exception as e:
        logger.error(f"[{fixture['name']}] Judge v2 failed: {e}")
        return {"scores": {}, "overall": None, "flags": [], "error": str(e)}

    numeric = [v["score"] for v in scores.values() if isinstance(v.get("score"), (int, float))]
    overall = round(sum(numeric) / len(numeric), 2) if numeric else None
    flags = [d for d, v in scores.items() if isinstance(v.get("score"), (int, float)) and v["score"] < 3]

    return {"scores": scores, "overall": overall, "flags": flags, "error": None}
