"""
Experience provider links — curated booking/search URLs for experience gifts.

Instead of dumping users to a generic Google search, map experience types to
known providers with real, stable URLs. The Google search becomes the fallback,
not the primary link.

Each provider entry has:
  - name: display name for the button
  - url_template: Python format string with {query} and/or {location} placeholders
  - icon: optional emoji/short label for the button (kept minimal)

Usage:
    providers = get_experience_providers(experience_name, location)
    # Returns list of {"name": "Ticketmaster", "url": "https://..."} dicts
"""

import re
import logging
from urllib.parse import quote

logger = logging.getLogger(__name__)


# -------------------------------------------------------------------
# Provider definitions: stable search URLs on known platforms
# -------------------------------------------------------------------

_PROVIDERS = {
    'concerts': [
        {'name': 'Ticketmaster', 'url_template': 'https://www.ticketmaster.com/search?q={query}&loc={location}'},
        {'name': 'StubHub', 'url_template': 'https://www.stubhub.com/search?q={query}'},
        {'name': 'SeatGeek', 'url_template': 'https://seatgeek.com/search?search={query}'},
    ],
    'sports_events': [
        {'name': 'Ticketmaster', 'url_template': 'https://www.ticketmaster.com/search?q={query}&loc={location}'},
        {'name': 'StubHub', 'url_template': 'https://www.stubhub.com/search?q={query}'},
        {'name': 'SeatGeek', 'url_template': 'https://seatgeek.com/search?search={query}'},
    ],
    'cooking_class': [
        {'name': 'Cozymeal', 'url_template': 'https://www.cozymeal.com/search?query={query}&location={location}'},
        {'name': 'Sur La Table', 'url_template': 'https://www.surlatable.com/cooking-classes/'},
        {'name': 'ClassBento', 'url_template': 'https://classbento.com/search?q={query}+{location}'},
    ],
    'art_class': [
        {'name': 'ClassBento', 'url_template': 'https://classbento.com/search?q={query}+{location}'},
        {'name': 'Painting with a Twist', 'url_template': 'https://www.paintingwithatwist.com/locations/'},
        {'name': 'Airbnb Experiences', 'url_template': 'https://www.airbnb.com/s/experiences?query={query}+{location}'},
    ],
    'travel': [
        {'name': 'Viator', 'url_template': 'https://www.viator.com/searchResults/all?text={query}+{location}'},
        {'name': 'Airbnb Experiences', 'url_template': 'https://www.airbnb.com/s/experiences?query={query}+{location}'},
        {'name': 'GetYourGuide', 'url_template': 'https://www.getyourguide.com/s/?q={query}+{location}'},
    ],
    'cruise': [
        {'name': 'Viking Cruises', 'url_template': 'https://www.vikingcruises.com/search?q={query}'},
        {'name': 'Expedia Cruises', 'url_template': 'https://www.expedia.com/Cruise-Search?query={query}'},
        {'name': 'CruiseCritic', 'url_template': 'https://www.cruisecritic.com/search/?searchTerm={query}'},
    ],
    'spa_wellness': [
        {'name': 'Spafinder', 'url_template': 'https://www.spafinder.com/search?q={location}'},
        {'name': 'Groupon', 'url_template': 'https://www.groupon.com/browse/{location}?query={query}'},
        {'name': 'Yelp', 'url_template': 'https://www.yelp.com/search?find_desc={query}&find_loc={location}'},
    ],
    'outdoor_adventure': [
        {'name': 'REI Experiences', 'url_template': 'https://www.rei.com/events/search?q={query}&location={location}'},
        {'name': 'Airbnb Experiences', 'url_template': 'https://www.airbnb.com/s/experiences?query={query}+{location}'},
        {'name': 'Viator', 'url_template': 'https://www.viator.com/searchResults/all?text={query}+{location}'},
    ],
    'wine_beer': [
        {'name': 'Viator', 'url_template': 'https://www.viator.com/searchResults/all?text={query}+{location}'},
        {'name': 'CellarPass', 'url_template': 'https://www.cellarpass.com/search?q={query}'},
        {'name': 'Yelp', 'url_template': 'https://www.yelp.com/search?find_desc={query}&find_loc={location}'},
    ],
    'fitness_class': [
        {'name': 'ClassPass', 'url_template': 'https://classpass.com/search/{location}?q={query}'},
        {'name': 'Groupon', 'url_template': 'https://www.groupon.com/browse/{location}?query={query}'},
        {'name': 'Yelp', 'url_template': 'https://www.yelp.com/search?find_desc={query}&find_loc={location}'},
    ],
    'museum_culture': [
        {'name': 'Viator', 'url_template': 'https://www.viator.com/searchResults/all?text={query}+{location}'},
        {'name': 'Yelp', 'url_template': 'https://www.yelp.com/search?find_desc={query}&find_loc={location}'},
    ],
    'dining': [
        {'name': 'OpenTable', 'url_template': 'https://www.opentable.com/s?term={query}&originId=0&corrid=0'},
        {'name': 'Resy', 'url_template': 'https://resy.com/cities?query={query}'},
        {'name': 'Yelp', 'url_template': 'https://www.yelp.com/search?find_desc={query}&find_loc={location}'},
    ],
    'pet_experience': [
        {'name': 'Rover', 'url_template': 'https://www.rover.com/search/?location={location}'},
        {'name': 'Yelp', 'url_template': 'https://www.yelp.com/search?find_desc={query}&find_loc={location}'},
    ],
}


# -------------------------------------------------------------------
# Experience classification — maps experience text to provider category
# -------------------------------------------------------------------

_EXPERIENCE_SIGNALS = {
    'concerts': ['concert', 'live music', 'tour', 'show tickets', 'music festival', 'gig'],
    'sports_events': ['game tickets', 'sports event', 'match tickets', 'nba', 'nfl', 'mlb', 'nhl',
                      'basketball game', 'football game', 'baseball game', 'soccer match', 'hockey game'],
    'cooking_class': ['cooking class', 'culinary class', 'baking class', 'cooking lesson',
                      'cooking workshop', 'chef', 'cuisine class', 'food workshop'],
    'art_class': ['art class', 'painting class', 'pottery class', 'ceramics', 'drawing class',
                  'craft workshop', 'art workshop', 'watercolor class', 'sculpture'],
    'cruise': ['cruise', 'river cruise', 'sailing trip', 'boat tour'],
    'travel': ['travel', 'trip', 'tour', 'sightseeing', 'excursion', 'guided tour',
               'walking tour', 'city tour', 'day trip'],
    'spa_wellness': ['spa', 'massage', 'facial', 'wellness', 'meditation class',
                     'yoga retreat', 'hot springs', 'sauna', 'float therapy'],
    'outdoor_adventure': ['hiking', 'kayaking', 'rock climbing', 'zip line', 'camping',
                          'rafting', 'horseback', 'adventure', 'parasailing', 'surfing lesson',
                          'scuba', 'snorkeling', 'paddleboard'],
    'wine_beer': ['wine tasting', 'brewery tour', 'winery', 'beer tasting', 'distillery',
                  'vineyard', 'sommelier', 'wine class'],
    'fitness_class': ['fitness class', 'gym', 'dance class', 'martial arts', 'boxing class',
                      'pilates', 'barre class', 'spin class', 'crossfit'],
    'museum_culture': ['museum', 'gallery', 'exhibit', 'theater', 'theatre', 'symphony',
                       'ballet', 'opera', 'cultural'],
    'dining': ['restaurant', 'dinner', 'tasting menu', 'fine dining', 'brunch',
               'supper club', 'food tour'],
    'pet_experience': ['dog park', 'pet', 'doggy', 'puppy playdate', 'dog-friendly',
                       'pet spa', 'dog training'],
}


def _classify_experience(experience_name, description=''):
    """Classify an experience into a provider category.

    Returns the category key (e.g. 'concerts', 'cooking_class') or None.
    """
    text = f"{experience_name} {description}".lower()

    best_category = None
    best_score = 0

    for category, signals in _EXPERIENCE_SIGNALS.items():
        score = sum(1 for signal in signals if signal in text)
        if score > best_score:
            best_score = score
            best_category = category

    return best_category


def _slugify_location(location):
    """Turn 'Indianapolis, Indiana' into 'indianapolis' for URL-friendly usage."""
    if not location:
        return ''
    # Take just the city part (before comma)
    city = location.split(',')[0].strip()
    return re.sub(r'[^a-z0-9]+', '-', city.lower()).strip('-')


def get_experience_providers(experience_name, location='', description=''):
    """Get curated provider links for an experience.

    Args:
        experience_name: e.g. "Thai Cooking Class" or "Chappell Roan Concert"
        location: e.g. "Indianapolis, Indiana"
        description: optional longer description for better classification

    Returns:
        List of dicts: [{"name": "Cozymeal", "url": "https://..."}, ...]
        Empty list if no providers match (caller should fall back to Google).
    """
    category = _classify_experience(experience_name, description)
    if not category or category not in _PROVIDERS:
        logger.debug(f"No provider category for experience: '{experience_name[:50]}'")
        return []

    providers = _PROVIDERS[category]
    query = quote(experience_name[:80])
    loc_slug = _slugify_location(location)
    loc_encoded = quote(location[:60]) if location else ''

    result = []
    for p in providers:
        try:
            url = p['url_template'].format(
                query=query,
                location=loc_encoded or loc_slug,
            )
            result.append({
                'name': p['name'],
                'url': url,
            })
        except (KeyError, ValueError) as e:
            logger.debug(f"Provider URL template error for {p['name']}: {e}")
            continue

    if result:
        logger.info(f"Experience providers for '{experience_name[:40]}' ({category}): {[p['name'] for p in result]}")

    return result
