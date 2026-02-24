"""
INTEREST ONTOLOGY — Pre-LLM enrichment layer for gift reasoning.

Enriches raw interests with thematic attributes BEFORE they reach the curator.
This is deterministic code, not an LLM call. Zero cost per session.

Purpose:
1. Map interests to attribute clusters (era, ethos, format, aesthetic, domain)
2. Cluster interests by shared attributes into themes
3. Identify the user's gift philosophy (object vs experience, collector vs consumer, etc.)
4. Output structured enrichment that guides the curator toward thematic,
   inferential gift reasoning instead of 1:1 literal interest→product matching.

Author: Chad + Claude
Date: February 2026
"""

import logging
import re
from collections import Counter, defaultdict
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 1. Interest → Attribute mappings
# ---------------------------------------------------------------------------

# Each interest carries implicit attributes. The curator can use these to
# make adjacency connections (e.g., two interests sharing "counterculture"
# ethos → recommend something that bridges both).

INTEREST_ATTRIBUTES = {
    # Music
    'the clash': {'era': 'punk/70s-80s', 'ethos': 'counterculture', 'format': 'music', 'aesthetic': 'raw/authentic'},
    'taylor swift': {'era': 'contemporary', 'ethos': 'fandom/community', 'format': 'music', 'aesthetic': 'polished/maximalist'},
    'vinyl collecting': {'ethos': 'curation', 'format': 'analog', 'aesthetic': 'retro/authentic', 'mindset': 'collector'},
    'vinyl record collecting': {'ethos': 'curation', 'format': 'analog', 'aesthetic': 'retro/authentic', 'mindset': 'collector'},
    'record collecting': {'ethos': 'curation', 'format': 'analog', 'aesthetic': 'retro/authentic', 'mindset': 'collector'},
    'indie music': {'ethos': 'counterculture', 'format': 'music', 'aesthetic': 'authentic/DIY', 'mindset': 'explorer'},
    'jazz': {'era': 'classic/timeless', 'ethos': 'sophistication', 'format': 'music', 'aesthetic': 'refined'},
    'hip hop': {'era': 'contemporary', 'ethos': 'self-expression', 'format': 'music', 'aesthetic': 'bold/street'},
    'classical music': {'era': 'classical', 'ethos': 'tradition', 'format': 'music', 'aesthetic': 'refined/elegant'},
    'country music': {'era': 'americana', 'ethos': 'roots/heritage', 'format': 'music', 'aesthetic': 'rustic/authentic'},
    'edm': {'era': 'contemporary', 'ethos': 'community/energy', 'format': 'music', 'aesthetic': 'neon/futuristic'},

    # Wellness & Fitness
    'yoga': {'domain': 'wellness', 'mindset': 'mindfulness', 'intensity': 'moderate', 'social': 'studio/retreat'},
    'meditation': {'domain': 'wellness', 'mindset': 'mindfulness', 'intensity': 'low', 'aesthetic': 'minimal/calm'},
    'hiking': {'domain': 'outdoor', 'mindset': 'adventure', 'intensity': 'high', 'aesthetic': 'rugged/natural'},
    'running': {'domain': 'fitness', 'mindset': 'discipline', 'intensity': 'high', 'aesthetic': 'technical'},
    'crossfit': {'domain': 'fitness', 'mindset': 'community/challenge', 'intensity': 'high', 'aesthetic': 'industrial'},
    'pilates': {'domain': 'wellness', 'mindset': 'self-care', 'intensity': 'moderate', 'aesthetic': 'clean/modern'},
    'weightlifting': {'domain': 'fitness', 'mindset': 'discipline', 'intensity': 'high', 'aesthetic': 'industrial'},
    'cycling': {'domain': 'fitness', 'mindset': 'adventure', 'intensity': 'high', 'aesthetic': 'technical'},
    'surfing': {'domain': 'outdoor', 'mindset': 'freedom', 'intensity': 'high', 'aesthetic': 'coastal/laid-back'},
    'rock climbing': {'domain': 'outdoor', 'mindset': 'challenge', 'intensity': 'high', 'aesthetic': 'rugged'},
    'martial arts': {'domain': 'fitness', 'mindset': 'discipline', 'intensity': 'high', 'ethos': 'tradition'},
    'swimming': {'domain': 'fitness', 'mindset': 'wellness', 'intensity': 'moderate', 'aesthetic': 'clean'},

    # Food & Drink
    'cooking': {'domain': 'food', 'mindset': 'creativity', 'social': 'hosting', 'aesthetic': 'artisanal'},
    'thai cooking': {'domain': 'food', 'mindset': 'creativity', 'ethos': 'exploration', 'aesthetic': 'artisanal'},
    'baking': {'domain': 'food', 'mindset': 'creativity', 'social': 'sharing', 'aesthetic': 'cozy/homey'},
    'coffee': {'domain': 'food-drink', 'mindset': 'ritual', 'aesthetic': 'artisanal', 'intensity': 'daily'},
    'craft beer': {'domain': 'food-drink', 'mindset': 'exploration', 'social': 'sharing/tasting', 'aesthetic': 'artisanal'},
    'wine': {'domain': 'food-drink', 'mindset': 'sophistication', 'social': 'entertaining', 'aesthetic': 'refined'},
    'tea': {'domain': 'food-drink', 'mindset': 'ritual', 'aesthetic': 'calm/mindful', 'intensity': 'daily'},
    'mixology': {'domain': 'food-drink', 'mindset': 'creativity', 'social': 'entertaining', 'aesthetic': 'sophisticated'},
    'barbecue': {'domain': 'food', 'mindset': 'mastery', 'social': 'hosting', 'aesthetic': 'rustic'},
    'vegan cooking': {'domain': 'food', 'ethos': 'conscious-living', 'mindset': 'creativity', 'aesthetic': 'clean'},

    # Creative
    'photography': {'domain': 'creative', 'mindset': 'observation', 'format': 'visual', 'aesthetic': 'varied'},
    'painting': {'domain': 'creative', 'mindset': 'expression', 'format': 'visual', 'aesthetic': 'varied'},
    'pottery': {'domain': 'creative', 'mindset': 'expression', 'format': 'tactile', 'aesthetic': 'artisanal'},
    'drawing': {'domain': 'creative', 'mindset': 'expression', 'format': 'visual', 'aesthetic': 'varied'},
    'knitting': {'domain': 'creative', 'mindset': 'patience', 'format': 'tactile', 'aesthetic': 'cozy'},
    'woodworking': {'domain': 'creative', 'mindset': 'mastery', 'format': 'tactile', 'aesthetic': 'rustic/craft'},
    'sewing': {'domain': 'creative', 'mindset': 'practical-creativity', 'format': 'tactile', 'aesthetic': 'varied'},
    'calligraphy': {'domain': 'creative', 'mindset': 'patience', 'format': 'visual', 'aesthetic': 'refined'},
    'graphic design': {'domain': 'creative', 'mindset': 'expression', 'format': 'digital', 'aesthetic': 'modern'},

    # Reading & Learning
    'reading': {'domain': 'intellectual', 'mindset': 'curiosity', 'format': 'books', 'intensity': 'daily'},
    'sci-fi': {'domain': 'intellectual', 'mindset': 'imagination', 'format': 'books/media', 'aesthetic': 'futuristic'},
    'true crime': {'domain': 'intellectual', 'mindset': 'curiosity', 'format': 'books/podcast', 'aesthetic': 'dark/intense'},
    'history': {'domain': 'intellectual', 'mindset': 'curiosity', 'format': 'books', 'aesthetic': 'classic'},
    'fantasy': {'domain': 'intellectual', 'mindset': 'imagination', 'format': 'books/media', 'aesthetic': 'epic/mythical'},
    'philosophy': {'domain': 'intellectual', 'mindset': 'reflection', 'format': 'books', 'aesthetic': 'minimal'},

    # Gaming
    'video games': {'domain': 'gaming', 'mindset': 'escapism', 'format': 'digital', 'social': 'varied'},
    'board games': {'domain': 'gaming', 'mindset': 'strategy', 'format': 'analog', 'social': 'group'},
    'dungeons and dragons': {'domain': 'gaming', 'mindset': 'imagination', 'format': 'analog', 'social': 'group'},
    'nintendo': {'domain': 'gaming', 'mindset': 'nostalgia', 'format': 'digital', 'aesthetic': 'playful'},
    'playstation': {'domain': 'gaming', 'mindset': 'immersion', 'format': 'digital', 'aesthetic': 'technical'},

    # Home & Living
    'interior design': {'domain': 'home', 'mindset': 'curation', 'aesthetic': 'varied', 'format': 'visual'},
    'gardening': {'domain': 'home', 'mindset': 'nurturing', 'aesthetic': 'natural', 'intensity': 'moderate'},
    'minimalism': {'domain': 'lifestyle', 'ethos': 'intentional-living', 'aesthetic': 'minimal/clean', 'mindset': 'curation'},
    'plants': {'domain': 'home', 'mindset': 'nurturing', 'aesthetic': 'natural/boho', 'social': 'community'},
    'candles': {'domain': 'home', 'mindset': 'ambiance', 'aesthetic': 'cozy', 'intensity': 'casual'},
    'home decor': {'domain': 'home', 'mindset': 'curation', 'aesthetic': 'varied', 'format': 'visual'},

    # Pets
    'dogs': {'domain': 'pets', 'mindset': 'nurturing', 'social': 'community', 'aesthetic': 'playful'},
    'cats': {'domain': 'pets', 'mindset': 'nurturing', 'social': 'identity', 'aesthetic': 'cozy'},

    # Fashion & Style
    'fashion': {'domain': 'style', 'mindset': 'self-expression', 'aesthetic': 'varied', 'format': 'visual'},
    'streetwear': {'domain': 'style', 'mindset': 'self-expression', 'aesthetic': 'bold/urban', 'ethos': 'counterculture'},
    'sneakers': {'domain': 'style', 'mindset': 'collecting', 'aesthetic': 'bold/street', 'ethos': 'hype-culture'},
    'thrifting': {'domain': 'style', 'mindset': 'exploration', 'aesthetic': 'eclectic', 'ethos': 'sustainable'},
    'jewelry': {'domain': 'style', 'mindset': 'self-expression', 'aesthetic': 'refined', 'format': 'tactile'},
    'skincare': {'domain': 'beauty', 'mindset': 'self-care', 'aesthetic': 'clean/modern', 'intensity': 'daily'},
    'makeup': {'domain': 'beauty', 'mindset': 'self-expression', 'aesthetic': 'varied', 'format': 'visual'},
    'fragrance': {'domain': 'beauty', 'mindset': 'identity', 'aesthetic': 'refined', 'intensity': 'daily'},

    # Travel & Outdoors
    'travel': {'domain': 'experience', 'mindset': 'adventure', 'social': 'varied', 'aesthetic': 'varied'},
    'camping': {'domain': 'outdoor', 'mindset': 'adventure', 'aesthetic': 'rugged', 'intensity': 'moderate'},
    'backpacking': {'domain': 'outdoor', 'mindset': 'adventure', 'aesthetic': 'minimal/rugged', 'ethos': 'exploration'},
    'fishing': {'domain': 'outdoor', 'mindset': 'patience', 'aesthetic': 'rustic', 'social': 'solitary/bonding'},
    'skiing': {'domain': 'outdoor', 'mindset': 'adventure', 'intensity': 'high', 'aesthetic': 'technical'},

    # Sports (spectator)
    'basketball': {'domain': 'sports', 'mindset': 'fandom', 'social': 'community', 'aesthetic': 'athletic'},
    'football': {'domain': 'sports', 'mindset': 'fandom', 'social': 'community', 'aesthetic': 'athletic'},
    'soccer': {'domain': 'sports', 'mindset': 'fandom', 'social': 'community', 'aesthetic': 'athletic'},
    'baseball': {'domain': 'sports', 'mindset': 'fandom', 'social': 'community', 'aesthetic': 'nostalgic'},
    'formula 1': {'domain': 'sports', 'mindset': 'fandom', 'aesthetic': 'technical/sleek', 'ethos': 'precision'},

    # Tech
    'technology': {'domain': 'tech', 'mindset': 'innovation', 'aesthetic': 'modern/sleek', 'format': 'digital'},
    'smart home': {'domain': 'tech', 'mindset': 'efficiency', 'aesthetic': 'modern', 'format': 'digital'},
    'programming': {'domain': 'tech', 'mindset': 'problem-solving', 'aesthetic': 'minimal', 'format': 'digital'},
    'astronomy': {'domain': 'science', 'mindset': 'wonder', 'aesthetic': 'cosmic', 'format': 'visual'},
    'drones': {'domain': 'tech', 'mindset': 'adventure', 'aesthetic': 'technical', 'format': 'gadget'},

    # Lifestyle
    'sustainability': {'ethos': 'conscious-living', 'mindset': 'intentional', 'aesthetic': 'natural/clean'},
    'self-care': {'domain': 'wellness', 'mindset': 'nurturing', 'aesthetic': 'calm', 'social': 'personal'},
    'astrology': {'domain': 'spiritual', 'mindset': 'identity', 'aesthetic': 'cosmic/mystical', 'social': 'community'},
    'tarot': {'domain': 'spiritual', 'mindset': 'reflection', 'aesthetic': 'mystical', 'format': 'analog'},
    'anime': {'domain': 'entertainment', 'mindset': 'fandom', 'aesthetic': 'colorful/expressive', 'format': 'visual'},
    'disney': {'domain': 'entertainment', 'mindset': 'nostalgia', 'aesthetic': 'whimsical', 'social': 'community'},
    'broadway': {'domain': 'entertainment', 'mindset': 'appreciation', 'aesthetic': 'dramatic', 'format': 'live'},
    'film': {'domain': 'entertainment', 'mindset': 'appreciation', 'aesthetic': 'varied', 'format': 'visual'},
}


# ---------------------------------------------------------------------------
# 2. Attribute-based heuristics for unmapped interests
# ---------------------------------------------------------------------------

# Keyword → attribute heuristics for interests not in the mapping above
KEYWORD_HEURISTICS = {
    # Domain detection
    'cook': {'domain': 'food'}, 'bak': {'domain': 'food'}, 'food': {'domain': 'food'},
    'coffee': {'domain': 'food-drink'}, 'beer': {'domain': 'food-drink'}, 'wine': {'domain': 'food-drink'},
    'tea': {'domain': 'food-drink'},
    'yoga': {'domain': 'wellness'}, 'meditat': {'domain': 'wellness'}, 'wellness': {'domain': 'wellness'},
    'hik': {'domain': 'outdoor'}, 'camp': {'domain': 'outdoor'}, 'fish': {'domain': 'outdoor'},
    'climb': {'domain': 'outdoor'}, 'surf': {'domain': 'outdoor'},
    'paint': {'domain': 'creative'}, 'draw': {'domain': 'creative'}, 'art': {'domain': 'creative'},
    'craft': {'domain': 'creative'}, 'photo': {'domain': 'creative'},
    'read': {'domain': 'intellectual'}, 'book': {'domain': 'intellectual'},
    'game': {'domain': 'gaming'}, 'gaming': {'domain': 'gaming'},
    'fashion': {'domain': 'style'}, 'style': {'domain': 'style'}, 'cloth': {'domain': 'style'},
    'skin': {'domain': 'beauty'}, 'makeup': {'domain': 'beauty'}, 'beauty': {'domain': 'beauty'},
    'plant': {'domain': 'home'}, 'garden': {'domain': 'home'}, 'decor': {'domain': 'home'},
    'dog': {'domain': 'pets'}, 'cat': {'domain': 'pets'}, 'pet': {'domain': 'pets'},
    'tech': {'domain': 'tech'}, 'gadget': {'domain': 'tech'},
    'travel': {'domain': 'experience'}, 'concert': {'format': 'live'},
    'music': {'format': 'music'}, 'band': {'format': 'music'},
    'vinyl': {'format': 'analog', 'mindset': 'collector'},
    'vintage': {'aesthetic': 'retro/authentic'}, 'retro': {'aesthetic': 'retro/authentic'},
    'minimal': {'aesthetic': 'minimal/clean'}, 'boho': {'aesthetic': 'bohemian'},
    'sport': {'domain': 'sports'},
    'run': {'domain': 'fitness'}, 'gym': {'domain': 'fitness'}, 'fit': {'domain': 'fitness'},
}


def _get_attributes(interest_name: str) -> Dict[str, str]:
    """Get attributes for an interest. Uses exact mapping first, then keyword heuristics."""
    key = interest_name.lower().strip()

    # Exact match
    if key in INTEREST_ATTRIBUTES:
        return dict(INTEREST_ATTRIBUTES[key])

    # Keyword heuristics
    attrs = {}
    for keyword, heuristic_attrs in KEYWORD_HEURISTICS.items():
        if keyword in key:
            attrs.update(heuristic_attrs)

    return attrs


# ---------------------------------------------------------------------------
# 3. Theme clustering
# ---------------------------------------------------------------------------

def _cluster_interests_by_theme(interests: List[Dict]) -> List[Dict]:
    """
    Cluster interests that share 2+ attributes into themes.

    Returns list of theme dicts with:
    - theme_name: Human-readable theme label
    - interests: List of interest names in this theme
    - shared_attributes: What they have in common
    """
    # Get attributes for all interests
    interest_attrs = []
    for interest in interests:
        name = interest.get('name', '')
        attrs = _get_attributes(name)
        if attrs:
            interest_attrs.append({'name': name, 'attrs': attrs})

    if len(interest_attrs) < 2:
        return []

    # Find pairs/groups that share 2+ attribute values
    themes = []
    used = set()

    for i in range(len(interest_attrs)):
        if i in used:
            continue
        group = [i]
        shared = {}

        for j in range(i + 1, len(interest_attrs)):
            if j in used:
                continue
            # Count shared attribute values
            common = {}
            for key in interest_attrs[i]['attrs']:
                if key in interest_attrs[j]['attrs'] and interest_attrs[i]['attrs'][key] == interest_attrs[j]['attrs'][key]:
                    common[key] = interest_attrs[i]['attrs'][key]

            if len(common) >= 2:
                group.append(j)
                if not shared:
                    shared = common
                else:
                    shared = {k: v for k, v in shared.items() if k in common and common[k] == v}

        if len(group) >= 2 and shared:
            theme_interests = [interest_attrs[idx]['name'] for idx in group]
            theme_name = _generate_theme_name(shared, theme_interests)
            themes.append({
                'theme_name': theme_name,
                'interests': theme_interests,
                'shared_attributes': shared,
            })
            for idx in group:
                used.add(idx)

    return themes


def _generate_theme_name(shared_attrs: Dict, interest_names: List[str]) -> str:
    """Generate a human-readable theme name from shared attributes."""
    parts = []

    if 'mindset' in shared_attrs:
        parts.append(shared_attrs['mindset'])
    if 'aesthetic' in shared_attrs:
        parts.append(shared_attrs['aesthetic'].split('/')[0])
    if 'domain' in shared_attrs:
        parts.append(shared_attrs['domain'])
    if 'ethos' in shared_attrs:
        parts.append(shared_attrs['ethos'].split('/')[0])

    if parts:
        return ' + '.join(parts[:3])
    return ' & '.join(interest_names[:2])


# ---------------------------------------------------------------------------
# 4. Gift philosophy inference
# ---------------------------------------------------------------------------

def _infer_gift_philosophy(interests: List[Dict], profile: Dict) -> Dict[str, str]:
    """
    Infer the recipient's gift philosophy from their profile.

    Returns dict with:
    - object_vs_experience: 'object_person' | 'experience_person' | 'balanced'
    - collector_vs_consumer: 'collector' | 'consumer' | 'balanced'
    - signaler_vs_private: 'signaler' | 'private' | 'balanced'
    - upgrader_vs_explorer: 'upgrader' | 'explorer' | 'balanced'
    """
    philosophy = {}

    # Count signals
    experience_signals = 0
    object_signals = 0
    collector_signals = 0
    consumer_signals = 0
    signaler_signals = 0
    private_signals = 0
    depth_signals = 0
    breadth_signals = 0

    for interest in interests:
        name = (interest.get('name') or '').lower()
        attrs = _get_attributes(name)
        intensity = (interest.get('intensity') or '').lower()
        activity_type = (interest.get('activity_type') or '').lower()

        # Object vs Experience
        domain = attrs.get('domain', '')
        if domain in ('experience', 'outdoor', 'wellness', 'fitness'):
            experience_signals += 1
        elif domain in ('home', 'style', 'tech', 'creative'):
            object_signals += 1
        if attrs.get('format') == 'live':
            experience_signals += 1

        # Collector vs Consumer
        mindset = attrs.get('mindset', '')
        if mindset in ('collector', 'curation'):
            collector_signals += 1
        elif mindset in ('ritual', 'daily'):
            consumer_signals += 1
        if attrs.get('format') == 'analog':
            collector_signals += 1

        # Signaler vs Private
        social = attrs.get('social', '')
        if social in ('community', 'identity', 'group'):
            signaler_signals += 1
        elif social in ('solitary', 'personal', 'solitary/bonding'):
            private_signals += 1

        # Upgrader vs Explorer
        if intensity == 'passionate':
            depth_signals += 1
        elif intensity == 'casual':
            breadth_signals += 1

    # Determine orientations
    def _classify(a, b, label_a, label_b):
        if a > b + 1:
            return label_a
        elif b > a + 1:
            return label_b
        return 'balanced'

    philosophy['object_vs_experience'] = _classify(object_signals, experience_signals, 'object_person', 'experience_person')
    philosophy['collector_vs_consumer'] = _classify(collector_signals, consumer_signals, 'collector', 'consumer')
    philosophy['signaler_vs_private'] = _classify(signaler_signals, private_signals, 'signaler', 'private')
    philosophy['upgrader_vs_explorer'] = _classify(depth_signals, breadth_signals, 'upgrader', 'explorer')

    return philosophy


# ---------------------------------------------------------------------------
# 5. Main enrichment function
# ---------------------------------------------------------------------------

def enrich_profile_with_ontology(profile: Dict) -> Dict[str, Any]:
    """
    Main entry point. Enriches a profile with thematic intelligence.

    Args:
        profile: Profile dict from profile_analyzer.py (with 'interests' list)

    Returns:
        Dict with:
        - themes: Clustered interest themes
        - gift_philosophy: Object/experience, collector/consumer orientations
        - interest_attributes: Per-interest attribute maps
        - curator_briefing: Pre-formatted text block for the curator prompt
    """
    interests = profile.get('interests', [])

    if not interests:
        return {
            'themes': [],
            'gift_philosophy': {},
            'interest_attributes': {},
            'curator_briefing': '',
        }

    # Get per-interest attributes
    interest_attrs = {}
    for interest in interests:
        name = interest.get('name', '')
        attrs = _get_attributes(name)
        if attrs:
            interest_attrs[name] = attrs

    # Cluster into themes
    themes = _cluster_interests_by_theme(interests)

    # Infer gift philosophy
    philosophy = _infer_gift_philosophy(interests, profile)

    # Build curator briefing text
    briefing = _build_curator_briefing(themes, philosophy, interest_attrs, profile)

    result = {
        'themes': themes,
        'gift_philosophy': philosophy,
        'interest_attributes': interest_attrs,
        'curator_briefing': briefing,
    }

    logger.info(f"Ontology enrichment: {len(interest_attrs)} interests mapped, "
                f"{len(themes)} themes found, philosophy={philosophy}")

    return result


def _build_curator_briefing(themes, philosophy, interest_attrs, profile) -> str:
    """Build a compact text briefing for the curator prompt."""
    parts = []

    # Themes section
    if themes:
        theme_lines = []
        for t in themes[:4]:  # Max 4 themes
            theme_lines.append(f"  - {t['theme_name']}: {', '.join(t['interests'][:4])}")
        parts.append("THEMATIC CLUSTERS (gifts bridging these work best):\n" + "\n".join(theme_lines))

    # Gift philosophy
    if philosophy:
        phil_parts = []
        if philosophy.get('object_vs_experience') != 'balanced':
            label = 'objects/things' if philosophy['object_vs_experience'] == 'object_person' else 'experiences/moments'
            phil_parts.append(f"Leans toward {label}")
        if philosophy.get('collector_vs_consumer') != 'balanced':
            label = 'curates/collects' if philosophy['collector_vs_consumer'] == 'collector' else 'uses/consumes'
            phil_parts.append(f"{label} rather than {'uses' if philosophy['collector_vs_consumer'] == 'collector' else 'collects'}")
        if philosophy.get('upgrader_vs_explorer') != 'balanced':
            label = 'goes deep in favorites' if philosophy['upgrader_vs_explorer'] == 'upgrader' else 'explores widely'
            phil_parts.append(label)
        if phil_parts:
            parts.append("GIFT ORIENTATION: " + "; ".join(phil_parts))

    # Adjacency hints — for each interest with attributes, suggest what's one step away
    adjacency_hints = _generate_adjacency_hints(interest_attrs)
    if adjacency_hints:
        parts.append("ADJACENCY HINTS (one step beyond the obvious):\n" + "\n".join(f"  - {h}" for h in adjacency_hints[:5]))

    return "\n\n".join(parts)


def _generate_adjacency_hints(interest_attrs: Dict[str, Dict]) -> List[str]:
    """
    Generate "one step away" gift hints for interests.
    These nudge the curator away from literal matches.
    """
    hints = []

    ADJACENCY_MAP = {
        'food': "cooking gear upgrades, artisan ingredients, experience classes (not cookbooks — they probably have many)",
        'food-drink': "brewing/tasting equipment, origin-story subscriptions, local artisan finds",
        'outdoor': "experience upgrades (guided trips, new terrain), high-quality consumables (camp food, maps), photography gear for documenting",
        'wellness': "premium practice gear, retreat experiences, mindfulness tools (not generic candles or bath bombs)",
        'creative': "premium materials they wouldn't buy themselves, workshop/class experiences, display/storage for their work",
        'intellectual': "first editions, author events, themed experiences (not just more books in the genre)",
        'gaming': "setup upgrades (lighting, chair, accessories), themed collectibles, gaming social experiences",
        'style': "statement pieces from emerging designers, care/maintenance for what they own, personal styling experiences",
        'sports': "game-day experience upgrades, signed memorabilia, behind-the-scenes tours",
        'pets': "custom portraits, premium care items, pet-and-owner matching gear",
        'music': "listening equipment upgrades, live show experiences, artist-adjacent merch (not just band t-shirts)",
        'home': "statement pieces for their aesthetic, experiences that inspire new design ideas",
        'tech': "premium accessories, setup upgrades, maker/tinkering kits",
        'beauty': "premium/niche brands they haven't tried, beauty experiences, curated sets from specific aesthetics",
        'entertainment': "premiere/event experiences, themed collectibles, behind-the-scenes content",
    }

    seen_domains = set()
    for name, attrs in interest_attrs.items():
        domain = attrs.get('domain', '')
        if domain and domain not in seen_domains:
            seen_domains.add(domain)
            hint = ADJACENCY_MAP.get(domain)
            if hint:
                hints.append(f"{name} → {hint}")

    return hints
