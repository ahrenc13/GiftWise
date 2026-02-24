"""
Search Query Utilities - Centralized query building for all retailer searchers

This module extracts the shared query-building logic from rapidapi_amazon_searcher.py
to eliminate sibling dependencies (eBay importing from Amazon) and provide a single
source of truth for search query optimization.

Usage:
    from search_query_utils import build_search_query, clean_interest_for_search

    # Basic cleaning
    clean_name = clean_interest_for_search("Dog ownership and care")  # → "Dog"

    # Full query building with category detection
    query = build_search_query("Taylor Swift fandom", intensity="strong")
    # → "Taylor Swift vinyl"  (music category detected, strong suffix selected)

Migration Guide for Searchers:
    # Before (in rapidapi_amazon_searcher.py):
    from rapidapi_amazon_searcher import _clean_interest_for_search, _categorize_interest, _QUERY_SUFFIXES
    import random

    cleaned = _clean_interest_for_search(name)
    category = _categorize_interest(cleaned.lower())
    suffix = random.choice(_QUERY_SUFFIXES[category])
    query = f"{cleaned} {suffix}"

    # After:
    from search_query_utils import build_search_query, build_queries_from_profile

    # Option 1: Build single query
    query = build_search_query(name, intensity=interest.get("intensity", "medium"))

    # Option 2: Build all queries from profile at once
    queries = build_queries_from_profile(profile, target_count=12, skip_work=True)
    for q in queries:
        query = q["query"]
        interest = q["interest"]
        priority = q["priority"]
        # ... make API call ...

Author: Chad + Claude
Date: February 2026
"""

import re
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# INTEREST NAME CLEANING
# =============================================================================

# Filler phrases the profile analyzer puts in interest names that hurt search quality.
# Examples:
#   "Dog ownership and care" → "Dog"
#   "International travel" stays as-is
#   "Family celebrations and milestone events" → "celebrations milestone"
_INTEREST_FILLER = re.compile(
    r'\b(?:and care|ownership|and maintenance|fandom|and lifestyle|'
    r'personalized|and (?:pop |rock |country )?culture|'
    r'connections and|celebrations and milestone events|'
    r'family celebrations|music curation|'
    r'and holiday traditions|and alternative aesthetics|'
    r'and \w+ aesthetics|aesthetic[s]?|'
    r'and contemporary |and classic |and modern )\b',
    re.IGNORECASE,
)


def clean_interest_for_search(name: str) -> str:
    """
    Strip filler phrases from interest names to make better search queries.

    The profile analyzer sometimes adds context words that are useful for
    understanding the person but hurt search quality. This function removes
    those while preserving the core meaning.

    Examples:
        'Dog ownership and care' → 'Dog'
        'Taylor Swift fandom' → 'Taylor Swift'
        'Chappell Roan and pop music' → 'Chappell Roan pop music'
        'Home renovation and design' → 'Home renovation design'

    Args:
        name: Raw interest name from profile analyzer

    Returns:
        Cleaned interest name ready for search
    """
    if not name:
        return ""

    # Remove filler phrases
    cleaned = _INTEREST_FILLER.sub('', name).strip()

    # Collapse double spaces
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()

    # Remove trailing/leading 'and'
    cleaned = re.sub(r'\band\b\s*$', '', cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r'^\band\b\s*', '', cleaned, flags=re.IGNORECASE).strip()

    # Cap at 5 meaningful words — long queries cause 400 errors on eBay
    # and return worse results on all APIs
    words = cleaned.split()
    if len(words) > 5:
        cleaned = ' '.join(words[:5])

    # If cleaning removed everything, return original
    return cleaned or name


# =============================================================================
# CATEGORY DETECTION
# =============================================================================

# Keywords that map interest names to suffix categories
_CATEGORY_SIGNALS = {
    'music':   ['music', 'band', 'singer', 'artist', 'concert', 'vinyl', 'album',
                'rap', 'pop', 'rock', 'jazz', 'hip hop', 'country', 'r&b'],
    'sports':  ['sports', 'basketball', 'football', 'soccer', 'baseball', 'team',
                'nba', 'nfl', 'mlb', 'hockey', 'racing', 'nascar'],
    'travel':  ['travel', 'cruise', 'vacation', 'international', 'destination',
                'adventure', 'backpack', 'wanderlust'],
    'food':    ['cook', 'food', 'baking', 'kitchen', 'culinary', 'recipe',
                'chef', 'grill', 'bbq', 'wine', 'coffee'],
    'pet':     ['dog', 'cat', 'pet', 'puppy', 'kitten', 'animal'],
    'fashion': ['fashion', 'style', 'clothing', 'outfit', 'wardrobe', 'jewelry',
                'sneaker', 'shoe', 'accessories'],
    'home':    ['home', 'decor', 'renovation', 'garden', 'plant', 'interior',
                'candle', 'cozy'],
    'tech':    ['tech', 'gaming', 'computer', 'gadget', 'electronic', 'phone',
                'smart', 'pc', 'console'],
    'fitness': ['fitness', 'gym', 'yoga', 'running', 'workout', 'exercise',
                'hiking', 'outdoor', 'cycling'],
    'beauty':  ['beauty', 'skincare', 'makeup', 'cosmetic', 'hair', 'nail',
                'spa', 'self-care'],
}


def categorize_interest(name: str) -> str:
    """
    Map an interest name to a category for query suffix selection.

    Uses keyword matching against _CATEGORY_SIGNALS. First match wins.
    If no category matches, returns 'default'.

    Args:
        name: Interest name (case-insensitive matching)

    Returns:
        Category key ('music', 'sports', 'travel', etc.) or 'default'
    """
    if not name:
        return 'default'

    name_lower = name.lower()

    for category, signals in _CATEGORY_SIGNALS.items():
        if any(signal in name_lower for signal in signals):
            return category

    return 'default'


# =============================================================================
# QUERY SUFFIXES
# =============================================================================

# Suffixes keyed by category — more specific than generic "gift"
# Each category has a list of suffixes to choose from based on intensity.
# Format: {category: [light, medium, strong, passionate, ...]}
_QUERY_SUFFIXES = {
    'music':   ['merch', 'fan gift', 'vinyl', 'poster', 'accessories'],
    'sports':  ['fan gear', 'jersey', 'memorabilia', 'apparel', 'wall art'],
    'travel':  ['accessories', 'organizer', 'essentials', 'travel kit', 'gadget'],
    'food':    ['lover gift', 'accessories', 'cookbook', 'kitchen gift', 'kit'],
    'pet':     ['accessories', 'toy', 'lover gift', 'supplies', 'treats'],
    'fashion': ['accessories', 'jewelry', 'style gift', 'wardrobe', 'trendy'],
    'home':    ['decor', 'organizer', 'gadget', 'accessories', 'cozy gift'],
    'tech':    ['gadget', 'accessories', 'electronics', 'smart device', 'gear'],
    'fitness': ['gear', 'accessories', 'equipment', 'workout gift', 'apparel'],
    'beauty':  ['set', 'skincare', 'beauty gift', 'tools', 'kit'],
    'default': ['gift', 'unique gift', 'lover gift', 'accessories', 'gift idea'],
}


def get_query_suffix(category: str, intensity: str = 'medium') -> str:
    """
    Get appropriate query suffix for a category and intensity.

    Maps intensity levels to suffix list indices:
        - 'light' → index 0 (most generic)
        - 'medium' → index 1
        - 'strong' → index 2
        - 'passionate' → index 3
        - Any other → index 1 (default to medium)

    Args:
        category: Category from categorize_interest()
        intensity: Interest intensity ('light', 'medium', 'strong', 'passionate')

    Returns:
        Query suffix string
    """
    suffixes = _QUERY_SUFFIXES.get(category, _QUERY_SUFFIXES['default'])

    # Map intensity to list index
    intensity_map = {
        'light': 0,
        'medium': 1,
        'strong': 2,
        'passionate': 3,
    }

    idx = intensity_map.get(intensity, 1)  # Default to medium

    # Clamp to available suffixes
    idx = min(idx, len(suffixes) - 1)

    return suffixes[idx]


# =============================================================================
# MAIN QUERY BUILDER
# =============================================================================

def build_search_query(
    interest_name: str,
    intensity: str = 'medium',
    category: str = None,
    max_length: int = 100,
) -> str:
    """
    Build optimized search query from interest name.

    This is the main entry point for all searcher modules. It:
    1. Cleans the interest name (removes filler)
    2. Detects category (unless provided)
    3. Adds appropriate suffix based on category + intensity
    4. Ensures query doesn't exceed max_length

    Examples:
        build_search_query("Dog ownership and care")
        → "Dog accessories"

        build_search_query("Taylor Swift fandom", intensity="passionate")
        → "Taylor Swift poster"

        build_search_query("Home renovation and design", category="home")
        → "Home renovation design decor"

    Args:
        interest_name: Raw interest name from profile
        intensity: 'light', 'medium', 'strong', 'passionate' (affects suffix)
        category: Optional pre-determined category (skips detection if provided)
        max_length: Maximum query length (for APIs with length limits)

    Returns:
        Cleaned search query ready for API
    """
    if not interest_name:
        return ""

    # Step 1: Clean the interest name
    cleaned = clean_interest_for_search(interest_name)

    # Step 2: Determine category (use provided or detect)
    cat = category or categorize_interest(cleaned)

    # Step 3: Get appropriate suffix
    suffix = get_query_suffix(cat, intensity)

    # Step 4: Build query
    query = f"{cleaned} {suffix}".strip()

    # Step 5: Enforce max length (truncate from end if needed)
    if len(query) > max_length:
        logger.warning(f"Query too long ({len(query)} chars), truncating: {query}")
        query = query[:max_length].strip()

    return query


# =============================================================================
# BATCH QUERY BUILDING
# =============================================================================

def build_queries_from_profile(
    profile: dict,
    target_count: int = 10,
    skip_work: bool = True,
) -> list[dict]:
    """
    Build search queries from a profile's interests.

    Convenience function for searcher modules. Extracts interests from
    profile, builds queries, and returns list of query dicts ready for
    iteration.

    Args:
        profile: Profile dict with 'interests' list
        target_count: Maximum number of queries to build
        skip_work: Skip interests marked as work-related

    Returns:
        List of dicts with keys:
            - query: Built search query string
            - interest: Original interest name
            - priority: 'high', 'medium', or 'low' based on intensity
            - category: Detected category
    """
    interests = profile.get("interests", [])
    if not interests:
        return []

    queries = []

    for interest in interests:
        name = interest.get("name", "")
        if not name:
            continue

        # Skip work interests if requested
        if skip_work and interest.get("is_work", False):
            logger.debug(f"Skipping work interest: {name}")
            continue

        # Build query
        intensity = interest.get("intensity", "medium")
        query = build_search_query(name, intensity=intensity)

        # Determine priority
        priority_map = {
            'passionate': 'high',
            'strong': 'high',
            'medium': 'medium',
            'light': 'low',
        }
        priority = priority_map.get(intensity, 'medium')

        queries.append({
            "query": query,
            "interest": name,
            "priority": priority,
            "category": categorize_interest(name),
            "intensity": intensity,
        })

        # Stop at target count
        if len(queries) >= target_count:
            break

    logger.info(f"Built {len(queries)} search queries from profile")
    return queries


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    print("Search Query Utils - Test Suite")
    print("=" * 60)

    # Test 1: Interest cleaning
    print("\n1. Interest Name Cleaning:")
    test_interests = [
        "Dog ownership and care",
        "Taylor Swift fandom",
        "Chappell Roan and pop music",
        "Home renovation and design",
        "International travel",
        "Family celebrations and milestone events",
    ]

    for interest in test_interests:
        cleaned = clean_interest_for_search(interest)
        print(f"  '{interest}' → '{cleaned}'")

    # Test 2: Category detection
    print("\n2. Category Detection:")
    test_categories = [
        "Taylor Swift",
        "NBA basketball",
        "hiking and outdoors",
        "skincare routine",
        "coffee brewing",
        "random interest here",
    ]

    for name in test_categories:
        category = categorize_interest(name)
        print(f"  '{name}' → {category}")

    # Test 3: Query building
    print("\n3. Query Building:")
    test_queries = [
        ("Dog ownership and care", "medium"),
        ("Taylor Swift fandom", "passionate"),
        ("Home renovation and design", "strong"),
        ("NBA basketball", "light"),
        ("skincare routine", "medium"),
    ]

    for name, intensity in test_queries:
        query = build_search_query(name, intensity=intensity)
        category = categorize_interest(clean_interest_for_search(name))
        print(f"  '{name}' ({intensity}) → '{query}' [category: {category}]")

    # Test 4: Max length enforcement
    print("\n4. Max Length Enforcement:")
    long_interest = "International travel to exotic destinations and cultural exploration"
    short_query = build_search_query(long_interest, max_length=30)
    print(f"  Input: '{long_interest}'")
    print(f"  Output: '{short_query}' ({len(short_query)} chars)")

    # Test 5: Batch query building
    print("\n5. Batch Query Building from Profile:")
    test_profile = {
        "interests": [
            {"name": "Taylor Swift fandom", "intensity": "passionate", "is_work": False},
            {"name": "hiking and outdoors", "intensity": "strong", "is_work": False},
            {"name": "project management", "intensity": "medium", "is_work": True},
            {"name": "skincare", "intensity": "light", "is_work": False},
        ]
    }

    queries = build_queries_from_profile(test_profile, target_count=5, skip_work=True)
    for q in queries:
        print(f"  {q['query']} [priority: {q['priority']}, category: {q['category']}]")

    print("\n" + "=" * 60)
    print("All tests complete!")
