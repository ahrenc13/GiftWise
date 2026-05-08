"""
Claude-as-judge for GiftWise eval scoring.

Scores each fixture output on 5 dimensions (1-5):
  specificity        — concepts specific to THIS person, not generic hobby gifts
  evidence_grounding — why_perfect cites actual profile signals/quotes/ownership
  splurge_integrity  — splurge pick is genuinely premium and earned (not just pricey)
  ownership_avoidance — output avoids items listed in ownership_signals
  diversity          — spread across interests, price points, concept types

Score < 3 on any dimension is flagged. Splurge integrity is N/A if no splurge pick.
"""

import json
import logging

logger = logging.getLogger(__name__)

_JUDGE_SYSTEM = """\
You are a quality evaluator for GiftWise, an AI gift recommendation product.
GiftWise generates gift *concepts* (not specific products) from a person's social profile.
A great output is specific, surprising, and grounded in the actual signals in the profile.
A bad output is generic — gifts that could apply to anyone who has this interest.
Score honestly. Be strict. A 5 is rare. A 3 is "acceptable but forgettable".\
"""

_JUDGE_PROMPT = """\
Evaluate this GiftWise output against the profile that generated it.

## Profile Summary
Name/handle: {fixture_name}
Key interests: {interest_summary}
Owns already: {ownership_summary}
Budget category: {budget_category}
Failure modes to watch: {failure_modes}

## Gift Concepts Generated
{concepts_block}

## Splurge Pick
{splurge_block}

---
Score each dimension 1-5. Return ONLY valid JSON matching this exact schema:

{{
  "specificity": {{
    "score": <1-5>,
    "note": "<one sentence — what's specific, or what's generic>"
  }},
  "evidence_grounding": {{
    "score": <1-5>,
    "note": "<one sentence — does why_perfect cite real profile signals?>"
  }},
  "splurge_integrity": {{
    "score": <1-5 or null if no splurge>,
    "note": "<one sentence — is the splurge pick genuinely earned at that price point?>"
  }},
  "ownership_avoidance": {{
    "score": <1-5>,
    "note": "<one sentence — does the output avoid what they already own?>"
  }},
  "diversity": {{
    "score": <1-5>,
    "note": "<one sentence — spread across interests, price, concept types>"
  }}
}}

Scoring guide:
5 = Excellent. Would make the giver say "how did it know that?"
4 = Good. Specific and relevant, minor generic moments.
3 = Acceptable. Relevant interest, but the gift itself is obvious/forgettable.
2 = Weak. Could apply to anyone who has this hobby.
1 = Miss. Generic, ignores profile signals, or recommends something already owned.\
"""


def _build_concepts_block(output: dict) -> str:
    concepts = output.get("product_gifts", [])
    if not concepts:
        return "(no concepts generated)"
    lines = []
    for i, c in enumerate(concepts, 1):
        lines.append(f"{i}. {c.get('name', '(unnamed)')}")
        lines.append(f"   Description: {c.get('description', '')[:120]}")
        lines.append(f"   Why perfect: {c.get('why_perfect', '')[:200]}")
        lines.append(f"   Price: {c.get('price_range', 'unknown')}")
        lines.append("")
    return "\n".join(lines)


def _build_splurge_block(output: dict) -> str:
    splurge = output.get("splurge_item")
    if not splurge:
        return "(no splurge pick)"
    return (
        f"Name: {splurge.get('name', '(unnamed)')}\n"
        f"Description: {splurge.get('description', '')[:150]}\n"
        f"Why perfect: {splurge.get('why_perfect', '')[:200]}\n"
        f"Price: {splurge.get('price_range', 'unknown')}"
    )


def score_output(fixture: dict, output: dict, claude_client, model: str = "claude-sonnet-4-6") -> dict:
    """
    Score ideate_gifts output for a fixture using Claude as judge.

    Returns:
        {
            "scores": {dimension: {"score": int, "note": str}, ...},
            "overall": float,
            "flags": [list of flagged dimensions],
            "error": str | None
        }
    """
    profile = fixture["profile"]

    interest_summary = ", ".join(
        f"{i['name']} ({i['intensity']})" for i in profile.get("interests", [])
    )
    ownership_summary = "; ".join(profile.get("ownership_signals", []))
    budget_category = profile.get("price_signals", {}).get("budget_category", "unknown")
    failure_modes = ", ".join(fixture.get("failure_modes", []))

    prompt = _JUDGE_PROMPT.format(
        fixture_name=fixture["name"],
        interest_summary=interest_summary,
        ownership_summary=ownership_summary,
        budget_category=budget_category,
        failure_modes=failure_modes,
        concepts_block=_build_concepts_block(output),
        splurge_block=_build_splurge_block(output),
    )

    try:
        response = claude_client.messages.create(
            model=model,
            max_tokens=600,
            system=_JUDGE_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()

        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        scores = json.loads(raw)
    except Exception as e:
        logger.error(f"[{fixture['name']}] Judge failed: {e}")
        return {"scores": {}, "overall": None, "flags": [], "error": str(e)}

    # Compute overall (exclude null splurge)
    numeric = [
        v["score"] for v in scores.values()
        if isinstance(v.get("score"), (int, float))
    ]
    overall = round(sum(numeric) / len(numeric), 2) if numeric else None

    flags = [
        dim for dim, v in scores.items()
        if isinstance(v.get("score"), (int, float)) and v["score"] < 3
    ]

    return {"scores": scores, "overall": overall, "flags": flags, "error": None}
