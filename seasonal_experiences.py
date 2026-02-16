"""
SEASONAL EXPERIENCE INTELLIGENCE - Weather-aware, seasonally appropriate experiences

Makes experience recommendations smart by considering:
- Weather patterns by region (don't suggest beach in Seattle winter)
- Seasonal activities (Midwest winter = cozy indoor vs summer = lake life)
- Major annual events by month (Indy 500 in May, SXSW in March)
- Holiday context (avoid religious assumptions, but note cultural events)

This prevents dumb suggestions like "outdoor yoga in Chicago in February."

Author: Chad + Claude
Date: February 2026
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from calendar import month_name

logger = logging.getLogger(__name__)


# ================================================================================
# SEASONAL PATTERNS BY REGION
# ================================================================================

SEASONAL_PATTERNS = {
    'midwest': {
        'winter': {  # Dec, Jan, Feb
            'weather': 'Cold, snowy, brutal. Sub-zero wind chills.',
            'indoor_bias': 0.9,  # 90% indoor recommendations
            'experiences': [
                'Cozy restaurant experiences',
                'Indoor cooking classes',
                'Museum memberships',
                'Spa days',
                'Brewery tours (indoor)',
                'Comedy shows',
                'Concert halls',
                'Indoor fitness classes',
                'Art gallery crawls',
            ],
            'outdoor_with_prep': [
                'Ice skating (bundled up)',
                'Winter farmers markets (short)',
                'Holiday lights tours (car)',
                'Ice fishing (hardcore only)',
            ],
            'avoid': [
                'Outdoor dining',
                'Beach activities',
                'Water sports',
                'Open-air concerts',
                'Picnics',
            ],
        },
        'spring': {  # Mar, Apr, May
            'weather': 'Unpredictable. Can be 70° or snowing. Mud season.',
            'indoor_bias': 0.5,
            'experiences': [
                'Spring training baseball (if traveling)',
                'Botanical gardens (late spring)',
                'Outdoor markets (April onward)',
                'Brewery patios (weather permitting)',
                'Spring concerts',
                'Hiking (trails muddy early spring)',
            ],
            'outdoor_with_prep': [
                'Outdoor dining (bring jacket)',
                'Farmers markets (April/May)',
                'Park activities',
            ],
            'avoid': [
                'Water sports (too cold until late May)',
                'Beach activities',
            ],
        },
        'summer': {  # Jun, Jul, Aug
            'weather': 'Warm to hot, humid. Perfect outdoor weather.',
            'indoor_bias': 0.2,
            'experiences': [
                'Lake activities (swimming, boating)',
                'Outdoor concerts',
                'Baseball games',
                'Farmers markets',
                'Outdoor dining',
                'Hiking',
                'Camping',
                'Brewery patios',
                'Festival season',
                'Golf',
            ],
            'outdoor_with_prep': [],
            'avoid': [
                'Overly formal indoor experiences (people want to be outside)',
            ],
        },
        'fall': {  # Sep, Oct, Nov
            'weather': 'Gorgeous early fall, cold late fall. Best season.',
            'indoor_bias': 0.4,
            'experiences': [
                'Football games (tailgating season)',
                'Apple orchards',
                'Pumpkin patches',
                'Fall festivals',
                'Oktoberfest events',
                'Hiking (foliage tours)',
                'Outdoor dining (early fall)',
                'Wine tastings',
            ],
            'outdoor_with_prep': [
                'Outdoor activities (bring layers)',
            ],
            'avoid': [
                'Water sports (cold)',
                'Beach activities',
            ],
        },
    },

    'south': {
        'winter': {
            'weather': 'Mild. 50-60s. Occasional cold snaps but generally pleasant.',
            'indoor_bias': 0.3,
            'experiences': [
                'Outdoor dining (mild temps)',
                'Golf (year-round)',
                'Hiking',
                'Wine tastings',
                'Brewery tours',
                'Outdoor markets',
                'Football games (college season)',
            ],
            'outdoor_with_prep': [],
            'avoid': [
                'Water sports (chilly)',
                'Beach activities (unless Florida/Gulf Coast)',
            ],
        },
        'spring': {
            'weather': 'Beautiful. Perfect outdoor weather before summer heat.',
            'indoor_bias': 0.2,
            'experiences': [
                'Outdoor dining',
                'Festivals (peak season)',
                'Hiking',
                'Golf',
                'Outdoor concerts',
                'Farmers markets',
                'Baseball games',
                'Bourbon/whiskey tours (Kentucky)',
            ],
            'outdoor_with_prep': [],
            'avoid': [],
        },
        'summer': {
            'weather': 'HOT. Humid. Oppressive. AC is life.',
            'indoor_bias': 0.6,
            'experiences': [
                'Indoor dining (AC)',
                'Museums',
                'Indoor entertainment',
                'Early morning/evening outdoor activities',
                'Pool/beach clubs',
                'Water activities (lakes, beaches)',
                'Indoor sports (basketball games)',
            ],
            'outdoor_with_prep': [
                'Outdoor dining (evenings only, patios with fans/misters)',
                'Beach trips (hydrate)',
                'Pool parties',
            ],
            'avoid': [
                'Midday outdoor activities (heat stroke risk)',
                'Hiking (dangerous heat)',
                'Outdoor sports events (unless evening)',
            ],
        },
        'fall': {
            'weather': 'Still warm but cooling. Football season.',
            'indoor_bias': 0.3,
            'experiences': [
                'College football (SEC culture)',
                'Outdoor dining',
                'Festivals',
                'Hiking',
                'Golf',
                'Tailgating experiences',
                'Outdoor concerts',
            ],
            'outdoor_with_prep': [],
            'avoid': [],
        },
    },

    'west_coast': {
        'winter': {
            'weather': 'CA: Mild, rainy. PNW: Rainy, gloomy, but not super cold.',
            'indoor_bias': 0.4,
            'experiences': [
                'Wine country (Napa/Sonoma indoor tastings)',
                'Museums',
                'Indoor climbing gyms',
                'Spas',
                'Theater',
                'Rainy day coffee culture (Seattle)',
                'Indoor farmers markets',
            ],
            'outdoor_with_prep': [
                'Hiking (rain gear required in PNW)',
                'Skiing/snowboarding (mountains)',
                'Outdoor dining (CA only, with heaters)',
            ],
            'avoid': [
                'Beach activities (cold water year-round anyway)',
            ],
        },
        'spring': {
            'weather': 'Beautiful. Wildflower season.',
            'indoor_bias': 0.2,
            'experiences': [
                'Hiking (wildflowers)',
                'Wine country',
                'Outdoor dining',
                'Farmers markets',
                'Beach activities (warming up)',
                'Music festivals',
                'Baseball games',
            ],
            'outdoor_with_prep': [],
            'avoid': [],
        },
        'summer': {
            'weather': 'Perfect. Dry, warm. Best season.',
            'indoor_bias': 0.1,
            'experiences': [
                'Beach culture',
                'Hiking',
                'Outdoor concerts',
                'Wine country',
                'Farmers markets',
                'Outdoor dining',
                'Surfing',
                'Kayaking',
                'Music festivals',
            ],
            'outdoor_with_prep': [],
            'avoid': [
                'Indoor experiences (people want to be outside)',
            ],
        },
        'fall': {
            'weather': 'Still beautiful. Harvest season.',
            'indoor_bias': 0.2,
            'experiences': [
                'Wine harvest tours',
                'Hiking',
                'Outdoor dining',
                'Farmers markets',
                'Beach activities (still warm)',
                'Football games',
            ],
            'outdoor_with_prep': [],
            'avoid': [],
        },
    },

    'northeast': {
        'winter': {
            'weather': 'Cold, snowy. NYC less brutal than Boston.',
            'indoor_bias': 0.8,
            'experiences': [
                'Broadway shows',
                'Museums',
                'Fine dining',
                'Jazz clubs',
                'Comedy clubs',
                'Indoor markets',
                'Spa days',
                'Cooking classes',
            ],
            'outdoor_with_prep': [
                'Ice skating',
                'Skiing (mountains)',
                'Winter markets (bundled up)',
            ],
            'avoid': [
                'Outdoor dining',
                'Beach activities',
                'Water sports',
            ],
        },
        'spring': {
            'weather': 'Unpredictable early, gorgeous late spring.',
            'indoor_bias': 0.4,
            'experiences': [
                'Baseball games (Red Sox, Yankees)',
                'Outdoor dining (April/May)',
                'Farmers markets',
                'Hiking',
                'Museums with outdoor sculpture gardens',
                'Botanical gardens',
            ],
            'outdoor_with_prep': [
                'Outdoor activities (bring layers)',
            ],
            'avoid': [
                'Water sports (too cold)',
            ],
        },
        'summer': {
            'weather': 'Warm, humid. NYC hot, coasts pleasant.',
            'indoor_bias': 0.3,
            'experiences': [
                'Beach trips (Cape Cod, Jersey Shore, Hamptons)',
                'Outdoor concerts',
                'Baseball games',
                'Rooftop bars',
                'Outdoor dining',
                'Farmers markets',
                'Sailing',
                'Central Park activities',
            ],
            'outdoor_with_prep': [],
            'avoid': [],
        },
        'fall': {
            'weather': 'Stunning. Foliage season. Best time of year.',
            'indoor_bias': 0.3,
            'experiences': [
                'Foliage tours (Vermont, Berkshires, Hudson Valley)',
                'Apple picking',
                'Pumpkin patches',
                'Football games',
                'Outdoor dining',
                'Hiking',
                'Wine country (Finger Lakes)',
                'Theater season starts',
            ],
            'outdoor_with_prep': [
                'Outdoor activities (bring layers)',
            ],
            'avoid': [
                'Beach activities',
            ],
        },
    },
}


# ================================================================================
# MAJOR ANNUAL EVENTS BY MONTH
# ================================================================================

ANNUAL_EVENTS = {
    1: {  # January
        'national': ['New Year celebrations', 'NFL Playoffs', 'College football championships'],
        'regional': {
            'west_coast': ['Rose Bowl (Pasadena)'],
            'south': ['College football playoffs'],
        },
    },
    2: {  # February
        'national': ['Super Bowl', "Valentine's Day", 'NBA All-Star Weekend'],
        'regional': {
            'south': ['Mardi Gras (New Orleans, Mobile)'],
            'northeast': ['Fashion Week (NYC)'],
        },
    },
    3: {  # March
        'national': ['March Madness (college basketball)', 'Spring Training baseball', "St. Patrick's Day"],
        'regional': {
            'south': ['SXSW (Austin, mid-March)'],
            'midwest': ['St. Patrick\'s Day parades (Chicago)'],
        },
    },
    4: {  # April
        'national': ['MLB Opening Day', 'Masters golf', 'Easter (varies)'],
        'regional': {
            'northeast': ['Boston Marathon (Patriots\' Day, mid-April)'],
            'south': ['Jazz Fest (New Orleans, late April)'],
        },
    },
    5: {  # May
        'national': ['Mother\'s Day', 'Memorial Day', 'Cinco de Mayo'],
        'regional': {
            'midwest': ['Indianapolis 500 (Memorial Day weekend)', 'Indy 500 events all month'],
            'northeast': ['Kentucky Derby (Louisville, first Saturday)'],
        },
    },
    6: {  # June
        'national': ['Father\'s Day', 'Pride Month', 'Summer solstice'],
        'regional': {
            'south': ['CMA Fest (Nashville, early June)'],
            'northeast': ['Graduation season (colleges)'],
        },
    },
    7: {  # July
        'national': ['4th of July', 'MLB All-Star Game'],
        'regional': {
            'midwest': ['Summerfest (Milwaukee)'],
            'northeast': ['Newport Folk Festival (RI)'],
        },
    },
    8: {  # August
        'national': ['Back to school'],
        'regional': {
            'northeast': ['US Open tennis (NYC, late August)'],
            'midwest': ['State fairs season'],
        },
    },
    9: {  # September
        'national': ['Labor Day', 'NFL season starts', 'Fall equinox'],
        'regional': {
            'midwest': ['College football season'],
            'northeast': ['Fashion Week (NYC)'],
        },
    },
    10: {  # October
        'national': ['Halloween', 'MLB Playoffs', 'Oktoberfest events'],
        'regional': {
            'south': ['Austin City Limits (ACL) festival'],
            'midwest': ['Oktoberfest (widespread)'],
        },
    },
    11: {  # November
        'national': ['Thanksgiving', 'Black Friday', 'College football rivalry week'],
        'regional': {
            'midwest': ['Chicago Marathon (early November)'],
            'south': ['SEC football championship'],
        },
    },
    12: {  # December
        'national': ['Christmas', 'Hanukkah', 'New Year\'s Eve', 'Bowl games'],
        'regional': {
            'midwest': ['Holiday markets'],
            'northeast': ['Rockefeller Center Christmas tree (NYC)'],
        },
    },
}


# ================================================================================
# SYNTHESIS FUNCTIONS
# ================================================================================

def get_seasonal_context(
    month: int,
    region: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get seasonal context for a given month and region.

    Args:
        month: Month number (1-12)
        region: Region name ('midwest', 'south', 'west_coast', 'northeast')

    Returns:
        Dict with seasonal intelligence:
        {
            'season': 'winter',
            'month_name': 'February',
            'weather_notes': 'Cold, snowy...',
            'indoor_bias': 0.8,
            'recommended_experiences': [...],
            'avoid_experiences': [...],
            'major_events': [...],
        }
    """

    if not 1 <= month <= 12:
        logger.warning(f"Invalid month: {month}")
        return {'error': 'Invalid month'}

    # Determine season
    season = _get_season(month)

    context = {
        'month': month,
        'month_name': month_name[month],
        'season': season,
        'major_events': [],
    }

    # Add seasonal patterns if region is known
    if region and region in SEASONAL_PATTERNS:
        season_data = SEASONAL_PATTERNS[region].get(season, {})
        context['weather_notes'] = season_data.get('weather', '')
        context['indoor_bias'] = season_data.get('indoor_bias', 0.5)
        context['recommended_experiences'] = season_data.get('experiences', [])
        context['outdoor_with_prep'] = season_data.get('outdoor_with_prep', [])
        context['avoid_experiences'] = season_data.get('avoid', [])

    # Add major annual events for this month
    month_events = ANNUAL_EVENTS.get(month, {})
    context['major_events'].extend(month_events.get('national', []))
    if region and region in month_events.get('regional', {}):
        context['major_events'].extend(month_events['regional'][region])

    logger.info(f"Seasonal context for {month_name[month]} in {region or 'unknown region'}: {season}, indoor_bias={context.get('indoor_bias', 0.5)}")

    return context


def _get_season(month: int) -> str:
    """Map month to season."""
    if month in [12, 1, 2]:
        return 'winter'
    elif month in [3, 4, 5]:
        return 'spring'
    elif month in [6, 7, 8]:
        return 'summer'
    else:  # 9, 10, 11
        return 'fall'


def get_seasonal_experiences(
    month: int,
    region: Optional[str] = None,
    interests: Optional[List[str]] = None,
) -> List[str]:
    """
    Get seasonally appropriate experience suggestions.

    Args:
        month: Month number (1-12)
        region: Region name
        interests: List of user interests (to filter experiences)

    Returns:
        List of experience suggestions
    """

    context = get_seasonal_context(month, region)

    recommended = context.get('recommended_experiences', [])
    outdoor_with_prep = context.get('outdoor_with_prep', [])

    # Combine recommended + outdoor_with_prep
    all_experiences = recommended + outdoor_with_prep

    # If interests provided, filter experiences that match
    if interests:
        interest_lower = [i.lower() for i in interests]
        filtered = []
        for exp in all_experiences:
            exp_lower = exp.lower()
            if any(interest in exp_lower or exp_lower in interest for interest in interest_lower):
                filtered.append(exp)

        # If filtered list is too small, return all
        if len(filtered) >= 3:
            return filtered[:6]

    return all_experiences[:6]


def should_avoid_outdoor(month: int, region: Optional[str] = None) -> bool:
    """
    Check if outdoor experiences should be avoided this month in this region.

    Returns True if indoor_bias > 0.7 (strong preference for indoor)
    """
    context = get_seasonal_context(month, region)
    return context.get('indoor_bias', 0.5) > 0.7


def get_seasonal_guidance(month: int, region: Optional[str] = None) -> str:
    """
    Generate human-readable seasonal guidance.

    Returns a concise string describing seasonal considerations.
    Useful for feeding to gift curator or experience architect.
    """

    context = get_seasonal_context(month, region)

    parts = []

    month_name_str = context.get('month_name', '')
    season = context.get('season', '')
    weather = context.get('weather_notes', '')

    if month_name_str and season:
        parts.append(f"Current season: {season} ({month_name_str}).")

    if weather:
        parts.append(f"Weather: {weather}")

    # Indoor/outdoor guidance
    indoor_bias = context.get('indoor_bias', 0.5)
    if indoor_bias > 0.7:
        parts.append("Strong preference for indoor experiences due to weather.")
    elif indoor_bias < 0.3:
        parts.append("Great weather for outdoor experiences.")

    # Major events
    events = context.get('major_events', [])
    if events:
        events_str = ', '.join(events[:3])
        parts.append(f"Notable events this month: {events_str}.")

    return ' '.join(parts)


# ================================================================================
# TESTING
# ================================================================================

if __name__ == '__main__':
    # Test 1: Midwest winter
    print("=" * 80)
    print("TEST 1: Midwest in February")
    print("=" * 80)
    context = get_seasonal_context(month=2, region='midwest')
    print(f"Season: {context['season']}")
    print(f"Weather: {context['weather_notes']}")
    print(f"Indoor bias: {context['indoor_bias']}")
    print(f"\nRecommended experiences:")
    for exp in context['recommended_experiences'][:5]:
        print(f"  - {exp}")
    print(f"\nAvoid:")
    for exp in context['avoid_experiences'][:3]:
        print(f"  - {exp}")
    print(f"\nGuidance: {get_seasonal_guidance(2, 'midwest')}")

    # Test 2: Austin in March (SXSW)
    print("\n" + "=" * 80)
    print("TEST 2: South in March (SXSW time)")
    print("=" * 80)
    context = get_seasonal_context(month=3, region='south')
    print(f"Season: {context['season']}")
    print(f"Major events: {context['major_events']}")
    print(f"Indoor bias: {context['indoor_bias']}")

    # Test 3: Indianapolis in May (Indy 500)
    print("\n" + "=" * 80)
    print("TEST 3: Midwest in May (Indy 500)")
    print("=" * 80)
    context = get_seasonal_context(month=5, region='midwest')
    print(f"Season: {context['season']}")
    print(f"Major events: {context['major_events']}")
    print(f"Should avoid outdoor: {should_avoid_outdoor(5, 'midwest')}")

    # Test 4: West Coast summer
    print("\n" + "=" * 80)
    print("TEST 4: West Coast in July")
    print("=" * 80)
    context = get_seasonal_context(month=7, region='west_coast')
    print(f"Season: {context['season']}")
    print(f"Weather: {context['weather_notes']}")
    print(f"Indoor bias: {context['indoor_bias']}")
    print(f"\nRecommended experiences:")
    for exp in context['recommended_experiences'][:5]:
        print(f"  - {exp}")

    # Test 5: Get experiences filtered by interests
    print("\n" + "=" * 80)
    print("TEST 5: Seasonal experiences for cooking interest in winter")
    print("=" * 80)
    experiences = get_seasonal_experiences(
        month=1,
        region='midwest',
        interests=['cooking', 'food']
    )
    print("Experiences:")
    for exp in experiences:
        print(f"  - {exp}")
