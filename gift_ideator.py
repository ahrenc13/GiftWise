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

_PORTRAIT_SYSTEM = (
    "You write character portraits for gift recommendations. You work only from "
    "the verbatim signals provided — captions, quotes, named places. You never "
    "invent details that aren't in the source material. Your portraits are the "
    "anchor that downstream gift ideation reasons against, so accuracy matters "
    "more than flourish."
)

_PORTRAIT_PROMPT = """\
Write a 2-3 sentence portrait of this specific person. The portrait will be \
used as an anchor for generating gift concepts, so it must capture who THIS \
person is — not the category their interests fall into.

{ontology_section}\
RECIPIENT SIGNALS

{interest_blocks}

{ownership_line}\
{aesthetic_line}\
{location_line}{venues_line}
RULES
- Reference their actual quotes and named specifics — books they mentioned, \
places they tagged, things they do. Not "she's into political activism" — \
something like "she attends Indianapolis school-board meetings, quotes Ezra \
Klein, and just finished reading Abundance."
- Use details ONLY from the signals above. If you cannot point to a quote, \
evidence line, or named venue that supports a detail, do not include it.
- No standalone personality adjectives (passionate, dedicated, thoughtful, \
creative, adventurous, curious). Show the behavior; let the reader infer the \
trait. "She quotes Ezra Klein" not "she's politically engaged."
- No adverbs (genuinely, really, actually, just, truly).
- 2-3 sentences. One paragraph.
- Lowercase sentence starts are fine. No trailing period required on the last \
sentence.

Return ONLY the portrait text. No JSON, no labels, no commentary."""

_IDEATOR_PROMPT = """\
Generate {rec_count} gift concepts for this person.

You have NO product catalog. Ideate freely from their actual signals — the raw \
texture of who they are, not a tidied category label. The quotes below are the \
hero of this work. The interest names are shorthand; the quotes are the person.

PORTRAIT (anchor — every concept must fit THIS person, not the category labels)

{portrait}

{ontology_section}\
RECIPIENT PROFILE

{interest_blocks}

{ownership_line}\
{aesthetic_line}\
{price_line}\
{location_line}{venues_line}
A concept lands when it:
- Bridges 2+ of this person's specific signals (the quotes, not just the labels). \
The intersection is where the interesting gifts live. "Indie music × thrifting × \
sustainability" might suggest a restored vintage audio piece — not a band t-shirt.
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
- Could have been generated from just the interest label without the quotes. \
If you could remove the quotes above and still arrive at this concept, it's too \
generic. Regenerate from the quotes, not the label.

DURABILITY GATE (anti-fad rule)
Concepts that involve high cost ($300+), travel, or permanent installation must \
NOT be built primarily on a "rising" signal. Rising signals are ephemeral — a \
news cycle, a recent enthusiasm. Anchor expensive or permanent ideas to \
"stable" signals, multi-year evidence, or interests with deep textural quotes. \
A space-program moment is a fascination; it's not a reason to suggest a \
Florida launch trip or a permanent kitchen backsplash. If your only support \
is a rising signal, scale the concept down (a book, a print, a streamable doc) \
or pick a different signal to build on.

AMALGAM CONCEPTS (physical + experiential pairing)
A few of your concepts may be amalgams — one gift composed of two parts: a \
physical object plus an experience that activates it. A vinyl + concert ticket. \
A field guide + state-park membership. A cast-iron pan + cooking class. Use the \
optional "parts" field for these. The two parts must reinforce each other — \
not just two unrelated gifts bundled. Don't force amalgams; only when the \
intersection is obvious.

PLAYBOOK FIELDS (optional, per concept — use judgment)
The recipient won't see this card; the gift-giver will. Their job is to find \
and buy something that fits the concept. Help them. For each concept, populate \
ONLY the playbook fields where you can be specific and useful — leave the rest \
empty rather than fill them with generic content.
- what_it_is: One sentence clarifying the concept for someone unfamiliar. \
("Leaves of Grass is Walt Whitman's 1855 poetry collection — a foundational \
American work; first editions are the collector's prize.") Useful when the \
giver may not know why this matters.
- sweet_spot: The version that lands. ("Look for the 1860 third edition or \
later — earlier ones are museum-priced. Avoid abridged anthologies.") Most \
important field — separates good execution from disappointing.
- where_to_look: Specific marketplaces or shop types. ("AbeBooks, Heritage \
Auctions, or any well-reviewed antiquarian bookseller.") Only name marketplaces \
you are confident exist and serve this category. Do not invent shop names.
- search_phrases: 1-3 phrases the giver can paste into Google or a marketplace \
search to find this. ("Leaves of Grass first edition", "Whitman 1860 third \
edition") Concrete, not generic.
- what_to_skip: Common wrong turns. ("Don't grab a paperback Penguin Classics \
edition — that's a $12 high-school reader, not a gift.")

VOICE RULES FOR why_perfect AND PLAYBOOK FIELDS
- Reference specific quotes or evidence from this profile, not generic praise
- No adverbs: cut "genuinely", "really", "actually", "truly", "just"
- No needle drops: don't end with "that's why this works" or "that's the point"
- No "perfect gift" or "they'll absolutely love it" — describe the fit, not the feeling
- 2-3 sentences max for why_perfect

ANTI-HALLUCINATION RULES (highest priority)
- Do NOT invent specific stores, marketplaces, brand names, or product lines \
that you are not confident exist. If you don't know a specific seller for a \
concept, say "well-reviewed independent shop" or "specialty retailer" rather \
than fabricating a name.
- Do NOT name a specific city venue (a particular restaurant, store, gallery) \
unless it appears in the GROUND TRUTH venues list above OR it is a major \
institution you are confident exists (a city's symphony, a well-known museum, \
a flagship university).
- Do NOT cite specific prices for unique or rare items as if they were known \
facts. Use ranges ("$200–$800 depending on edition") and acknowledge \
uncertainty in price_range when warranted.
- If you cannot ground a detail in the signals or in well-known fact, OMIT it. \
A shorter, more conservative concept is better than a confident-sounding \
fabricated one. Hallucinations destroy trust faster than thin concepts do.
- search_phrases must be queries that will return real results on Google or \
the named marketplace. Test mentally: would I actually find this with this \
phrase?

SIGNAL WEIGHT LADDER
Each interest above is tagged [signal: strong / moderate / light]. This drives \
how you write about it — the confidence of the prose should match the certainty \
of the signal.

strong (passionate + stable): write with full confidence. The interest is \
established and sustained. Concepts built here can be declarative.

moderate (passionate + rising/fading, OR moderate + stable): write with \
measured confidence. Don't oversell the fit. A brief "based on consistent \
posts about X" grounds it without hedging.

light (moderate + rising/fading, OR any casual): write with explicit hedging. \
Example: "based on a few recent posts about X — may reflect a lasting \
interest, or could be the news cycle." Scale the gift commitment accordingly: \
a book, a print, a short class — not a trip or a permanent installation. \
Let the giver decide what to do with uncertain signal.

The durability gate (from above) applies to light signals: no travel, \
permanent installations, or $300+ gifts built primarily on light signals. \
For moderate signals at those price points, hedging the copy is acceptable.

RULES
- At least 3 concepts must explicitly bridge 2+ signals
- At least 2 should be surprising — things the giver wouldn't naturally reach for
- No gift cards, cash, or vague "experience vouchers" with no specifics
- search_terms must be concrete enough to actually return results on Google
- price_range must be realistic for this type of item

SPLURGE PICK
Also generate one splurge concept — the nicest version of something that fits \
this person, or an extravagant experience. Price: ${splurge_min}–${splurge_ceiling}. \
This should feel like an "if money were no object" pick that still makes sense \
for who they are. Apply the same quality bar: bridges signals, grounded in their \
actual quotes, specific, answers why they wouldn't buy it themselves.

Splurge must NOT be built on any rising signal, regardless of intensity — \
expensive commitments cannot ride an ephemeral enthusiasm. Even a "passionate" \
rising signal is a moment, not a pattern; a viral post or news-cycle spike \
inflates engagement without proving a durable interest. Anchor the splurge to \
a stable signal with multi-year evidence, or pick a different signal to build \
on. If no stable signal supports a splurge-priced concept, scale the splurge \
down to the low end of the range against a safer signal rather than force it.

Return JSON only. No markdown fences, no explanation before or after.

For OPTIONAL fields below: include them when you can be specific and grounded; \
OMIT them entirely (don't include the key) when you'd otherwise fill them with \
generic or speculative content.

{{
  "gift_concepts": [
    {{
      "name": "3-7 word concept label (not a brand name, a concept)",
      "description": "1-2 sentences: what this is specifically and why it fits",
      "why_perfect": "Why this lands for THIS person. Specific. References their actual signals or quotes.",
      "signal_intersection": "Which 2+ interests or quotes this bridges, or the dominant single signal",
      "search_terms": ["specific search query 1", "specific search query 2"],
      "gift_type": "physical",
      "price_range": "$X\u2013$Y",
      "interest_match": "primary interest label",
      "confidence_level": "safe_bet or adventurous",
      "what_it_is": "OPTIONAL — one sentence clarifying the concept for someone unfamiliar",
      "sweet_spot": "OPTIONAL — the version that lands; what to choose vs avoid",
      "where_to_look": "OPTIONAL — specific marketplaces or shop types",
      "search_phrases": ["OPTIONAL — concrete query 1", "concrete query 2"],
      "what_to_skip": "OPTIONAL — common wrong turns",
      "parts": {{
        "OPTIONAL_amalgam_only": "include this object only for amalgam concepts",
        "physical_part": "the physical object (e.g. 'Vinyl pressing of the album')",
        "experiential_part": "the experience that activates it (e.g. 'Tickets to the next tour stop in their region')"
      }}
    }}
  ],
  "splurge_concept": {{
    "name": "3-7 word concept label",
    "description": "1-2 sentences",
    "why_perfect": "Why this lands — specific to their signals or quotes",
    "signal_intersection": "Which signals this bridges",
    "search_terms": ["specific search query 1", "specific search query 2"],
    "gift_type": "physical",
    "price_range": "$X\u2013$Y (must be ${splurge_min}–${splurge_ceiling})",
    "interest_match": "primary interest label",
    "confidence_level": "adventurous",
    "what_it_is": "OPTIONAL — one sentence clarifying the concept",
    "sweet_spot": "OPTIONAL — the version that lands",
    "where_to_look": "OPTIONAL — specific marketplaces or shop types",
    "search_phrases": ["OPTIONAL — concrete query 1"],
    "what_to_skip": "OPTIONAL — common wrong turns"
  }}
}}"""

# Splurge ceiling by budget category — mirrors inventory mode behavior
_SPLURGE_CEILINGS = {
    'budget': 300,
    'moderate': 500,
    'premium': 1000,
    'luxury': 1500,
}
_SPLURGE_MIN = 200


def _format_profile_for_prompt(profile: Dict) -> Dict[str, str]:
    """Extract and format key signals from profile dict for the ideation prompt.

    Each interest is rendered as a block with its verbatim signal_quotes so the
    ideator reasons over raw evidence rather than a tidied category label.
    """
    interests = profile.get('interests', [])

    blocks = []
    for i in interests:
        name = (i.get('name') or '').strip()
        if not name:
            continue
        intensity = (i.get('intensity') or '').strip().lower()
        momentum = (i.get('signal_momentum') or '').strip().lower()
        evidence = (i.get('evidence') or i.get('description') or '').strip()[:180]
        raw_quotes = i.get('signal_quotes') or []

        # Signal weight: intensity × momentum → strong / moderate / light.
        # Drives hedging ladder in the prompt — strong = declarative, light = hedge copy.
        # passionate + rising collapses to light: a high-engagement spike on one post
        # isn't durable passion, and the durability gate must block splurge-priced or
        # permanent concepts that ride an ephemeral enthusiasm.
        if intensity == 'passionate':
            if momentum == 'stable':
                signal_weight = 'strong'
            elif momentum == 'rising':
                signal_weight = 'light'
            else:
                signal_weight = 'moderate'
        elif intensity == 'moderate':
            signal_weight = 'moderate' if momentum == 'stable' else 'light'
        else:
            signal_weight = 'light'

        header_parts = [intensity] if intensity else []
        if momentum and momentum in ('rising', 'fading'):
            header_parts.append(momentum)
        header = f"- {name}"
        if header_parts:
            header += f" ({', '.join(header_parts)})"
        header += f" [signal: {signal_weight}]"
        lines = [header]
        if evidence:
            lines.append(f"  evidence: {evidence}")

        cleaned = []
        for q in raw_quotes:
            if not q:
                continue
            q_str = str(q).strip().replace('\n', ' ').replace('\r', '')
            if q_str:
                cleaned.append(q_str[:120])
        if cleaned:
            lines.append("  quotes:")
            for q in cleaned[:3]:
                lines.append(f'    "{q}"')

        blocks.append('\n'.join(lines))

    interest_blocks = '\n'.join(blocks) if blocks else '- (no interests identified)'

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
    city = (loc.get('city_region') or '').strip() if loc.get('city_region') else ''
    state = (loc.get('state') or '').strip() if loc.get('state') else ''
    if city and state:
        location_line = f"Location: {city}, {state}\n"
    elif city:
        location_line = f"Location: {city}\n"
    else:
        location_line = ''

    # Specific venues — places the person has personally tagged or posted from.
    # These are GROUND TRUTH for venue-naming. Anything outside this list must be
    # described by type (a local independent X) or named only if it's a known
    # institution (symphony, museum, university). Hallucination guardrail.
    venues = profile.get('specific_venues') or []
    venue_lines = []
    for v in venues[:12]:
        if isinstance(v, dict):
            name = (v.get('name') or '').strip()
            vtype = (v.get('type') or '').strip()
            vloc = (v.get('location') or '').strip()
            if not name:
                continue
            parts_str = name
            if vtype:
                parts_str += f" ({vtype})"
            if vloc:
                parts_str += f" — {vloc}"
            venue_lines.append(f"  - {parts_str}")
        elif isinstance(v, str) and v.strip():
            venue_lines.append(f"  - {v.strip()}")
    if venue_lines:
        venues_line = (
            "Places she has named (GROUND TRUTH — safe to reference by name; "
            "outside this list, describe venue TYPE or cite known institutions only):\n"
            + '\n'.join(venue_lines) + '\n'
        )
    else:
        venues_line = ''

    return {
        'interest_blocks': interest_blocks,
        'ownership_line': ownership_line,
        'aesthetic_line': aesthetic_line,
        'price_line': price_line,
        'location_line': location_line,
        'venues_line': venues_line,
        'budget_category': budget_cat,
    }


def build_portrait(
    profile: Dict,
    claude_client,
    ontology_briefing: Optional[str] = None,
    model: Optional[str] = None,
) -> str:
    """Generate a 2-3 sentence character portrait from raw profile signals.

    Runs as a separate Claude call before ideation so the portrait gets dedicated
    attention (and the resulting text becomes a reasoning anchor for the
    downstream ideation call rather than competing with concept generation in a
    single pass). Grounded only in verbatim quotes, evidence lines, and named
    venues — does not invent details.

    Returns the portrait text, or empty string on failure (ideator will fall
    back to reasoning over the raw signals alone).
    """
    model = model or os.environ.get('CLAUDE_CURATOR_MODEL', _DEFAULT_MODEL)

    fields = _format_profile_for_prompt(profile)
    fields.pop('budget_category', None)
    fields.pop('price_line', None)

    ontology_section = ''
    if ontology_briefing and ontology_briefing.strip():
        ontology_section = f"THEMATIC INTELLIGENCE\n{ontology_briefing}\n\n"

    prompt = _PORTRAIT_PROMPT.format(
        ontology_section=ontology_section,
        **fields,
    )

    try:
        response = claude_client.messages.create(
            model=model,
            max_tokens=400,
            system=_PORTRAIT_SYSTEM,
            messages=[{'role': 'user', 'content': prompt}],
        )
        portrait = response.content[0].text.strip()
        # Strip stray markdown or quote wrapping if present
        if portrait.startswith('"') and portrait.endswith('"'):
            portrait = portrait[1:-1].strip()
        logger.info(f"PORTRAIT: {portrait[:280]}")
        return portrait
    except Exception as e:
        logger.error(f"PORTRAIT: Claude call failed: {e}")
        return ''


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
        Dict matching curate_gifts() format, plus portrait:
        {
            'product_gifts': [list of concept dicts],
            'experience_gifts': [],
            'splurge_item': concept dict with is_splurge=True, or None,
            'portrait': str (2-3 sentence character portrait, may be empty on failure),
        }
        Each concept dict has: name, description, why_perfect, search_terms,
        gift_type, price_range, interest_match, confidence_level, signal_intersection,
        is_concept=True, is_amalgam (bool), purchase_link (Google search URL),
        where_to_buy='Search'. Optional playbook fields when populated:
        what_it_is, sweet_spot, where_to_look, search_phrases, what_to_skip,
        parts ({physical_part, experiential_part}).
    """
    model = model or os.environ.get('CLAUDE_CURATOR_MODEL', _DEFAULT_MODEL)

    # Build the portrait first as a separate Claude call. Becomes the anchor
    # input to the ideation prompt rather than being generated alongside concepts.
    portrait = build_portrait(
        profile,
        claude_client,
        ontology_briefing=ontology_briefing,
        model=model,
    )

    # Build profile summary
    fields = _format_profile_for_prompt(profile)
    budget_category = fields.pop('budget_category', 'moderate')
    splurge_ceiling = _SPLURGE_CEILINGS.get(budget_category, 500)

    ontology_section = ''
    if ontology_briefing and ontology_briefing.strip():
        ontology_section = f"THEMATIC INTELLIGENCE\n{ontology_briefing}\n\n"

    portrait_for_prompt = portrait if portrait else '(portrait unavailable — reason directly from the signals below)'

    prompt = _IDEATOR_PROMPT.format(
        rec_count=rec_count,
        portrait=portrait_for_prompt,
        ontology_section=ontology_section,
        splurge_min=_SPLURGE_MIN,
        splurge_ceiling=splurge_ceiling,
        **fields,
    )

    logger.info(f"IDEATOR: Generating {rec_count} concepts + splurge (ceiling=${splurge_ceiling}, model={model})")

    try:
        response = claude_client.messages.create(
            model=model,
            max_tokens=8000,
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
        splurge_raw = data.get('splurge_concept')
        logger.info(f"IDEATOR: Parsed {len(concepts)} concepts, splurge={'yes' if splurge_raw else 'no'}")

    except json.JSONDecodeError as e:
        logger.error(f"IDEATOR: JSON parse failed: {e}")
        logger.error(f"IDEATOR: Raw (first 500): {raw[:500] if 'raw' in dir() else 'n/a'}")
        return {'product_gifts': [], 'experience_gifts': [], 'splurge_item': None, 'portrait': portrait}
    except Exception as e:
        logger.error(f"IDEATOR: Claude call failed: {e}")
        return {'product_gifts': [], 'experience_gifts': [], 'splurge_item': None, 'portrait': portrait}

    # Convert a raw concept dict to product_gift format
    def _concept_to_gift(concept, is_splurge=False):
        # Prefer playbook search_phrases for the primary search URL when present —
        # they're the giver-facing, marketplace-ready queries.
        search_phrases = concept.get('search_phrases') or []
        search_terms = concept.get('search_terms') or []
        primary_search = (
            (search_phrases[0] if search_phrases else None)
            or (search_terms[0] if search_terms else None)
            or concept.get('name', '')
        )
        search_url = f"https://www.google.com/search?q={quote(primary_search)}"

        # Optional amalgam parts. Only carry through if both sides are present —
        # a half-amalgam is a single-part gift, not an amalgam.
        parts_raw = concept.get('parts') or {}
        parts = None
        if isinstance(parts_raw, dict):
            physical = (parts_raw.get('physical_part') or '').strip()
            experiential = (parts_raw.get('experiential_part') or '').strip()
            if physical and experiential:
                parts = {
                    'physical_part': physical,
                    'experiential_part': experiential,
                }

        gift = {
            'name': concept.get('name', 'Gift Concept'),
            'description': concept.get('description', ''),
            'why_perfect': concept.get('why_perfect', ''),
            'signal_intersection': concept.get('signal_intersection', ''),
            'search_terms': search_terms,
            'gift_type': 'physical',
            'price_range': concept.get('price_range', ''),
            'interest_match': concept.get('interest_match', ''),
            'confidence_level': concept.get('confidence_level', 'adventurous' if is_splurge else 'safe_bet'),
            'is_concept': True,
            'is_splurge': is_splurge,
            'is_amalgam': bool(parts),
            'where_to_buy': 'Search',
            'product_url': search_url,
            'purchase_link': search_url,
            'image_url': '',
        }

        # Optional playbook fields — only attach if non-empty so downstream
        # templates can render conditionally without checking for empty strings.
        for field in ('what_it_is', 'sweet_spot', 'where_to_look', 'what_to_skip'):
            value = (concept.get(field) or '').strip()
            if value:
                gift[field] = value
        if search_phrases:
            cleaned_phrases = [str(p).strip() for p in search_phrases if str(p).strip()]
            if cleaned_phrases:
                gift['search_phrases'] = cleaned_phrases[:3]
        if parts:
            gift['parts'] = parts

        return gift

    product_gifts = [_concept_to_gift(c) for c in concepts]

    splurge_item = None
    if splurge_raw:
        splurge_item = _concept_to_gift(splurge_raw, is_splurge=True)
        logger.info(f"IDEATOR: Splurge concept: '{splurge_item['name']}' ({splurge_item['price_range']})")

    amalgam_count = sum(1 for g in product_gifts if g.get('is_amalgam'))
    playbook_count = sum(1 for g in product_gifts if g.get('sweet_spot'))
    logger.info(f"IDEATOR: {amalgam_count} amalgams, {playbook_count} concepts with sweet_spot guidance")

    return {
        'product_gifts': product_gifts,
        'experience_gifts': [],
        'splurge_item': splurge_item,
        'portrait': portrait,
    }
