"""
LOCAL EVENTS INTELLIGENCE - Real-time event data and city-specific calendars

Integrates:
- Ticketmaster API for live concert/sports data
- City-specific annual event calendars
- Event caching to avoid excessive API calls
- Smart event matching to user interests

Makes experiences feel current and locally relevant.

Author: Chad + Claude
Date: February 2026
"""

import logging
import os
import json
import shelve
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import requests

logger = logging.getLogger(__name__)

# Ticketmaster API credentials
TICKETMASTER_API_KEY = os.environ.get('TICKETMASTER_API_KEY', '')

# Cache settings
EVENT_CACHE_PATH = os.path.join(os.path.dirname(__file__), 'data', 'event_cache')
CACHE_DURATION_HOURS = 24  # Cache events for 24 hours


# ================================================================================
# CITY-SPECIFIC ANNUAL EVENT CALENDARS
# ================================================================================

CITY_EVENT_CALENDARS = {
    'indianapolis': [
        {'name': 'Indianapolis 500', 'month': 5, 'type': 'sports', 'description': 'The Greatest Spectacle in Racing'},
        {'name': 'Indy 500 Carb Day', 'month': 5, 'type': 'sports'},
        {'name': 'Indy 500 Snake Pit (EDM concert)', 'month': 5, 'type': 'music'},
        {'name': 'Pacers season', 'month_range': [10, 4], 'type': 'sports'},
        {'name': 'Colts season', 'month_range': [9, 1], 'type': 'sports'},
        {'name': 'Penrod Arts Fair', 'month': 9, 'type': 'arts'},
        {'name': 'Indy Irish Fest', 'month': 9, 'type': 'festival'},
        {'name': 'Broad Ripple Art Fair', 'month': 5, 'type': 'arts'},
        {'name': 'Indiana State Fair', 'month': 8, 'type': 'festival'},
        {'name': 'Circle of Lights (downtown)', 'month': 11, 'type': 'holiday'},
    ],
    'chicago': [
        {'name': 'Cubs season', 'month_range': [4, 9], 'type': 'sports'},
        {'name': 'White Sox season', 'month_range': [4, 9], 'type': 'sports'},
        {'name': 'Bulls season', 'month_range': [10, 4], 'type': 'sports'},
        {'name': 'Blackhawks season', 'month_range': [10, 4], 'type': 'sports'},
        {'name': 'Lollapalooza', 'month': 8, 'type': 'music'},
        {'name': 'Taste of Chicago', 'month': 7, 'type': 'food'},
        {'name': 'Chicago Air & Water Show', 'month': 8, 'type': 'festival'},
        {'name': 'Chicago Marathon', 'month': 10, 'type': 'sports'},
        {'name': 'Chicago Jazz Festival', 'month': 9, 'type': 'music'},
        {'name': "St. Patrick's Day Parade", 'month': 3, 'type': 'festival'},
    ],
    'austin': [
        {'name': 'SXSW', 'month': 3, 'type': 'festival', 'description': 'Music, film, and tech mega-festival'},
        {'name': 'Austin City Limits Music Festival', 'month': 10, 'type': 'music'},
        {'name': 'UT Football season', 'month_range': [9, 12], 'type': 'sports'},
        {'name': 'Levitation (psych music festival)', 'month': 5, 'type': 'music'},
        {'name': 'Austin Food + Wine Festival', 'month': 5, 'type': 'food'},
        {'name': 'Blues on the Green', 'month_range': [5, 9], 'type': 'music'},
        {'name': 'Trail of Lights (Zilker Park)', 'month': 12, 'type': 'holiday'},
        {'name': 'Reggae Fest', 'month': 4, 'type': 'music'},
    ],
    'nashville': [
        {'name': 'CMA Fest', 'month': 6, 'type': 'music', 'description': 'Country music mega-festival'},
        {'name': 'Predators season', 'month_range': [10, 4], 'type': 'sports'},
        {'name': 'Titans season', 'month_range': [9, 1], 'type': 'sports'},
        {'name': 'Americana Music Festival', 'month': 9, 'type': 'music'},
        {'name': 'Nashville Film Festival', 'month': 10, 'type': 'arts'},
        {'name': 'Bonnaroo (nearby Manchester, TN)', 'month': 6, 'type': 'music'},
        {'name': 'Tomato Art Fest', 'month': 8, 'type': 'festival'},
    ],
    'los_angeles': [
        {'name': 'Lakers season', 'month_range': [10, 4], 'type': 'sports'},
        {'name': 'Clippers season', 'month_range': [10, 4], 'type': 'sports'},
        {'name': 'Dodgers season', 'month_range': [4, 10], 'type': 'sports'},
        {'name': 'Coachella', 'month': 4, 'type': 'music'},
        {'name': 'Stagecoach (country music)', 'month': 4, 'type': 'music'},
        {'name': 'LA Film Festival', 'month': 6, 'type': 'arts'},
        {'name': 'Hollywood Bowl summer season', 'month_range': [6, 9], 'type': 'music'},
    ],
    'san_francisco': [
        {'name': 'Warriors season', 'month_range': [10, 4], 'type': 'sports'},
        {'name': '49ers season', 'month_range': [9, 1], 'type': 'sports'},
        {'name': 'Outside Lands Music Festival', 'month': 8, 'type': 'music'},
        {'name': 'SF Pride', 'month': 6, 'type': 'festival'},
        {'name': 'Hardly Strictly Bluegrass', 'month': 10, 'type': 'music'},
        {'name': 'Bay to Breakers', 'month': 5, 'type': 'festival'},
    ],
    'seattle': [
        {'name': 'Seahawks season', 'month_range': [9, 1], 'type': 'sports'},
        {'name': 'Mariners season', 'month_range': [4, 9], 'type': 'sports'},
        {'name': 'Bumbershoot', 'month': 9, 'type': 'music'},
        {'name': 'Capitol Hill Block Party', 'month': 7, 'type': 'music'},
        {'name': 'Seattle International Film Festival', 'month': 5, 'type': 'arts'},
        {'name': 'Seafair', 'month': 8, 'type': 'festival'},
    ],
    'new_york': [
        {'name': 'Yankees season', 'month_range': [4, 10], 'type': 'sports'},
        {'name': 'Mets season', 'month_range': [4, 10], 'type': 'sports'},
        {'name': 'Knicks season', 'month_range': [10, 4], 'type': 'sports'},
        {'name': 'Nets season', 'month_range': [10, 4], 'type': 'sports'},
        {'name': 'Rangers season', 'month_range': [10, 4], 'type': 'sports'},
        {'name': 'US Open Tennis', 'month': 8, 'type': 'sports'},
        {'name': 'NYC Marathon', 'month': 11, 'type': 'sports'},
        {'name': 'Governors Ball', 'month': 6, 'type': 'music'},
        {'name': 'Shakespeare in the Park', 'month_range': [6, 8], 'type': 'arts'},
        {'name': 'Restaurant Week', 'month_range': [1, 7], 'type': 'food'},
        {'name': "New Year's Eve (Times Square)", 'month': 12, 'type': 'holiday'},
    ],
    'boston': [
        {'name': 'Red Sox season', 'month_range': [4, 10], 'type': 'sports'},
        {'name': 'Celtics season', 'month_range': [10, 4], 'type': 'sports'},
        {'name': 'Bruins season', 'month_range': [10, 4], 'type': 'sports'},
        {'name': 'Patriots season', 'month_range': [9, 2], 'type': 'sports'},
        {'name': 'Boston Marathon', 'month': 4, 'type': 'sports', 'description': "Patriots' Day tradition"},
        {'name': 'Boston Calling', 'month': 5, 'type': 'music'},
        {'name': 'Head of the Charles Regatta', 'month': 10, 'type': 'sports'},
        {'name': 'Boston Harborfest', 'month': 7, 'type': 'festival'},
    ],
}


# ================================================================================
# TICKETMASTER API INTEGRATION
# ================================================================================

def search_ticketmaster_events(
    city: str,
    state: Optional[str] = None,
    keywords: Optional[List[str]] = None,
    date_range_days: int = 90,
) -> List[Dict[str, Any]]:
    """
    Search Ticketmaster for upcoming events in a city.

    Args:
        city: City name
        state: State code (e.g., 'IN', 'TX')
        keywords: Optional keywords to filter events
        date_range_days: How many days ahead to search (default 90)

    Returns:
        List of event dicts with:
        {
            'name': 'Event name',
            'date': 'YYYY-MM-DD',
            'venue': 'Venue name',
            'url': 'Ticketmaster URL',
            'type': 'music|sports|arts',
            'price_range': '$50-$150',
        }
    """

    if not TICKETMASTER_API_KEY:
        logger.warning("Ticketmaster API key not set. Skipping live event search.")
        return []

    # Check cache first
    cache_key = f"{city}_{state}_{'-'.join(keywords or [])}".lower()
    cached = _get_cached_events(cache_key)
    if cached:
        logger.info(f"Returning cached Ticketmaster events for {city}")
        return cached

    # Build API request
    url = 'https://app.ticketmaster.com/discovery/v2/events.json'

    params = {
        'apikey': TICKETMASTER_API_KEY,
        'city': city,
        'size': 20,  # Max 20 events
        'sort': 'date,asc',
    }

    if state:
        params['stateCode'] = state

    if keywords:
        params['keyword'] = ' '.join(keywords)

    # Date range
    start_date = datetime.now().strftime('%Y-%m-%dT00:00:00Z')
    end_date = (datetime.now() + timedelta(days=date_range_days)).strftime('%Y-%m-%dT23:59:59Z')
    params['startDateTime'] = start_date
    params['endDateTime'] = end_date

    try:
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()

        events = []
        for item in data.get('_embedded', {}).get('events', []):
            event = {
                'name': item.get('name', ''),
                'date': item.get('dates', {}).get('start', {}).get('localDate', ''),
                'venue': item.get('_embedded', {}).get('venues', [{}])[0].get('name', ''),
                'url': item.get('url', ''),
                'type': _classify_event_type(item),
                'price_range': _extract_price_range(item),
                'source': 'ticketmaster',
            }
            events.append(event)

        # Cache results
        _cache_events(cache_key, events)

        logger.info(f"Found {len(events)} Ticketmaster events for {city}")
        return events

    except requests.exceptions.RequestException as e:
        logger.error(f"Ticketmaster API error: {e}")
        return []
    except Exception as e:
        logger.error(f"Error parsing Ticketmaster response: {e}")
        return []


def _classify_event_type(event_data: Dict) -> str:
    """Classify Ticketmaster event type."""
    classifications = event_data.get('classifications', [])
    if not classifications:
        return 'other'

    segment = classifications[0].get('segment', {}).get('name', '').lower()

    if 'music' in segment:
        return 'music'
    elif 'sports' in segment:
        return 'sports'
    elif 'arts' in segment or 'theatre' in segment:
        return 'arts'
    else:
        return 'other'


def _extract_price_range(event_data: Dict) -> str:
    """Extract price range from Ticketmaster event data."""
    price_ranges = event_data.get('priceRanges', [])
    if not price_ranges:
        return 'Price varies'

    min_price = price_ranges[0].get('min', 0)
    max_price = price_ranges[0].get('max', 0)

    if min_price and max_price:
        return f"${int(min_price)}-${int(max_price)}"
    elif min_price:
        return f"From ${int(min_price)}"
    else:
        return 'Price varies'


# ================================================================================
# EVENT CACHING
# ================================================================================

def _get_cached_events(cache_key: str) -> Optional[List[Dict]]:
    """Retrieve cached events if still fresh."""
    try:
        # Ensure data directory exists
        os.makedirs(os.path.dirname(EVENT_CACHE_PATH), exist_ok=True)

        with shelve.open(EVENT_CACHE_PATH) as cache:
            if cache_key in cache:
                cached_data = cache[cache_key]
                timestamp = cached_data.get('timestamp')
                events = cached_data.get('events', [])

                # Check if cache is still fresh
                if timestamp:
                    cache_age = datetime.now() - datetime.fromisoformat(timestamp)
                    if cache_age < timedelta(hours=CACHE_DURATION_HOURS):
                        return events

        return None

    except Exception as e:
        logger.warning(f"Error reading event cache: {e}")
        return None


def _cache_events(cache_key: str, events: List[Dict]) -> None:
    """Cache events with timestamp."""
    try:
        # Ensure data directory exists
        os.makedirs(os.path.dirname(EVENT_CACHE_PATH), exist_ok=True)

        with shelve.open(EVENT_CACHE_PATH) as cache:
            cache[cache_key] = {
                'timestamp': datetime.now().isoformat(),
                'events': events,
            }

    except Exception as e:
        logger.warning(f"Error caching events: {e}")


# ================================================================================
# COMBINED EVENT RETRIEVAL
# ================================================================================

def get_local_events(
    city: str,
    state: Optional[str] = None,
    month: Optional[int] = None,
    interests: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Get local events combining annual calendar + live Ticketmaster data.

    Args:
        city: City name
        state: State code
        month: Month to filter annual events (1-12)
        interests: User interests to filter events

    Returns:
        List of event dicts
    """

    events = []

    # Get annual calendar events for this city
    city_lower = city.lower().replace(' ', '_')
    if city_lower in CITY_EVENT_CALENDARS:
        annual_events = CITY_EVENT_CALENDARS[city_lower]

        # Filter by month if provided
        if month:
            annual_events = [
                e for e in annual_events
                if e.get('month') == month or
                   (e.get('month_range') and e['month_range'][0] <= month <= e['month_range'][1])
            ]

        # Convert to standard format
        for event in annual_events:
            events.append({
                'name': event['name'],
                'type': event['type'],
                'description': event.get('description', ''),
                'source': 'annual_calendar',
            })

    # Get live Ticketmaster events
    keywords = interests[:3] if interests else None  # Use top 3 interests as keywords
    ticketmaster_events = search_ticketmaster_events(city, state, keywords)
    events.extend(ticketmaster_events)

    logger.info(f"Retrieved {len(events)} total events for {city}")

    return events


def get_event_suggestions(
    city: str,
    state: Optional[str] = None,
    interests: Optional[List[str]] = None,
) -> List[str]:
    """
    Get human-readable event suggestions for experiences.

    Returns list of strings like:
    - "Pacers game tickets (NBA season Oct-Apr)"
    - "SXSW passes (March music/tech festival)"
    """

    events = get_local_events(city, state, interests=interests)

    suggestions = []
    for event in events[:6]:  # Max 6 suggestions
        name = event['name']
        event_type = event.get('type', '')
        description = event.get('description', '')

        if description:
            suggestions.append(f"{name} ({description})")
        elif event_type:
            suggestions.append(f"{name} ({event_type})")
        else:
            suggestions.append(name)

    return suggestions


# ================================================================================
# TESTING
# ================================================================================

if __name__ == '__main__':
    # Test 1: Indianapolis annual events
    print("=" * 80)
    print("TEST 1: Indianapolis annual events in May")
    print("=" * 80)
    events = get_local_events('Indianapolis', 'IN', month=5)
    print(f"Found {len(events)} events:")
    for event in events:
        print(f"  - {event['name']} ({event.get('type', 'unknown')})")

    # Test 2: Austin annual events
    print("\n" + "=" * 80)
    print("TEST 2: Austin annual events in March (SXSW)")
    print("=" * 80)
    events = get_local_events('Austin', 'TX', month=3)
    print(f"Found {len(events)} events:")
    for event in events:
        print(f"  - {event['name']} ({event.get('type', 'unknown')})")

    # Test 3: Event suggestions
    print("\n" + "=" * 80)
    print("TEST 3: Event suggestions for music lover in Nashville")
    print("=" * 80)
    suggestions = get_event_suggestions('Nashville', 'TN', interests=['music', 'country'])
    print("Suggestions:")
    for s in suggestions:
        print(f"  - {s}")

    # Test 4: Ticketmaster live search (if API key is set)
    if TICKETMASTER_API_KEY:
        print("\n" + "=" * 80)
        print("TEST 4: Live Ticketmaster search for Indianapolis concerts")
        print("=" * 80)
        live_events = search_ticketmaster_events('Indianapolis', 'IN', keywords=['concert'])
        print(f"Found {len(live_events)} live events:")
        for event in live_events[:5]:
            print(f"  - {event['name']} on {event['date']} at {event['venue']}")
            print(f"    {event['price_range']} - {event['url']}")
    else:
        print("\n[Skipping Ticketmaster test - API key not set]")
