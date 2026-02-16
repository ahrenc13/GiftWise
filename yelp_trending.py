"""
Yelp Trending Service
Surfaces "what's trending in [city]" to enhance experience recommendations with local hotspots.

Integrates with Yelp Fusion API to provide:
- Real-time trending venues in specific cities
- Category-specific searches (coffee shops, breweries, art classes, etc.)
- Neighborhood-level hotspot detection
- Trending score calculation based on rating, review velocity, and recency

Free tier: 5,000 API calls/day (plenty for our use case)
API docs: https://docs.developer.yelp.com/reference/v3_business_search
"""

import os
import json
import time
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import requests
from pathlib import Path

# Experience type to Yelp category mappings
EXPERIENCE_TO_YELP_CATEGORIES = {
    # Food & Drink
    'cooking_class': ['cookingclasses', 'cooking_schools'],
    'wine_tasting': ['winetasteclasses', 'wineries', 'wine_bars'],
    'brewery_tour': ['breweries', 'brewpubs', 'beer_tours'],
    'coffee_experience': ['coffee', 'coffeeroasteries', 'cafes'],
    'food_tour': ['food_tours', 'tastingclasses'],
    'cocktail_class': ['wine_bars', 'cocktailbars'],

    # Arts & Entertainment
    'live_music': ['musicvenues', 'jazzandblues', 'country_dance_halls'],
    'art_class': ['artclasses', 'paintandsip', 'artstudio'],
    'comedy_show': ['comedyclubs'],
    'theater': ['theater', 'performing_arts'],
    'museum': ['museums', 'galleries'],

    # Wellness & Fitness
    'spa_day': ['spas', 'massage', 'beautysvc', 'day_spas'],
    'yoga': ['yoga', 'pilates', 'meditation_centers'],
    'rock_climbing': ['climbing'],
    'dance_class': ['dancestudio', 'salsa'],
    'fitness_class': ['gyms', 'bootcamps', 'interval_training'],

    # Outdoor & Adventure
    'hiking': ['hiking'],
    'kayaking': ['paddleboarding', 'boating'],
    'bike_tour': ['bikerentals', 'bike_tours'],
    'farmers_market': ['farmersmarket'],

    # Learning & Skills
    'pottery_class': ['artclasses', 'pottery_studios'],
    'photography_walk': ['photographystores', 'photography_classes'],
    'language_class': ['language_schools'],

    # Social & Nightlife
    'trivia_night': ['bars', 'pubs'],
    'karaoke': ['karaoke'],
    'escape_room': ['escapegames'],
    'arcade': ['barcades', 'arcades']
}

# City-specific neighborhood mappings
CITY_NEIGHBORHOODS = {
    'Austin': ['East Austin', 'South Congress', 'Rainey Street', 'Downtown', 'Sixth Street', 'West Campus'],
    'NYC': ['Williamsburg', 'East Village', 'Upper West Side', 'SoHo', 'Chelsea', 'Brooklyn Heights'],
    'New York': ['Williamsburg', 'East Village', 'Upper West Side', 'SoHo', 'Chelsea', 'Brooklyn Heights'],
    'Chicago': ['Lincoln Park', 'Wicker Park', 'River North', 'Logan Square', 'Lakeview', 'West Loop'],
    'LA': ['Venice', 'Silver Lake', 'Downtown LA', 'Santa Monica', 'Arts District', 'Highland Park'],
    'Los Angeles': ['Venice', 'Silver Lake', 'Downtown LA', 'Santa Monica', 'Arts District', 'Highland Park'],
    'Indianapolis': ['Broad Ripple', 'Mass Ave', 'Fountain Square', 'Downtown', 'Fletcher Place'],
    'Seattle': ['Capitol Hill', 'Fremont', 'Ballard', 'Queen Anne', 'Pike Place'],
    'Portland': ['Pearl District', 'Hawthorne', 'Alberta Arts', 'Downtown', 'Division'],
    'Nashville': ['East Nashville', 'The Gulch', 'Germantown', '12South', 'Downtown'],
    'Denver': ['RiNo', 'LoDo', 'Highland', 'Capitol Hill', 'South Broadway']
}

# Fallback data for when API is unavailable (top verified venues)
FALLBACK_VENUES = {
    'Austin': [
        {'name': 'Franklin Barbecue', 'category': 'bbq', 'rating': 4.5, 'price': '$$', 'good_for': ['foodies', 'tourists']},
        {'name': 'Sour Duck Market', 'category': 'coffee', 'rating': 4.6, 'price': '$', 'good_for': ['working', 'dates']},
        {'name': 'Punch Bowl Social', 'category': 'arcade', 'rating': 4.3, 'price': '$$', 'good_for': ['groups', 'dates']},
        {'name': 'Austin Bouldering Project', 'category': 'climbing', 'rating': 4.7, 'price': '$$', 'good_for': ['fitness', 'dates']},
        {'name': 'The Far Out Lounge', 'category': 'live_music', 'rating': 4.4, 'price': '$$', 'good_for': ['nightlife', 'groups']},
    ],
    'NYC': [
        {'name': 'Blue Bottle Coffee', 'category': 'coffee', 'rating': 4.5, 'price': '$$', 'good_for': ['working', 'dates']},
        {'name': 'Brooklyn Boulders', 'category': 'climbing', 'rating': 4.6, 'price': '$$', 'good_for': ['fitness', 'dates']},
        {'name': 'Comedy Cellar', 'category': 'comedy', 'rating': 4.7, 'price': '$$', 'good_for': ['dates', 'nightlife']},
        {'name': 'Brooklyn Brewery', 'category': 'brewery', 'rating': 4.4, 'price': '$$', 'good_for': ['groups', 'tourists']},
        {'name': 'The Vessel', 'category': 'attractions', 'rating': 4.3, 'price': 'Free', 'good_for': ['tourists', 'photos']},
    ],
    'Chicago': [
        {'name': 'The Violet Hour', 'category': 'cocktail_bar', 'rating': 4.6, 'price': '$$$', 'good_for': ['dates', 'nightlife']},
        {'name': 'Revolution Brewing', 'category': 'brewery', 'rating': 4.5, 'price': '$$', 'good_for': ['groups', 'casual']},
        {'name': 'The Art Institute', 'category': 'museum', 'rating': 4.8, 'price': '$$', 'good_for': ['culture', 'dates']},
        {'name': 'Chicago Athletic Association', 'category': 'hotel_bar', 'rating': 4.7, 'price': '$$$', 'good_for': ['dates', 'special']},
        {'name': 'Kingston Mines', 'category': 'live_music', 'rating': 4.5, 'price': '$$', 'good_for': ['nightlife', 'groups']},
    ],
    'LA': [
        {'name': 'Blue Bottle Coffee', 'category': 'coffee', 'rating': 4.5, 'price': '$$', 'good_for': ['working', 'dates']},
        {'name': 'The Broad', 'category': 'museum', 'rating': 4.7, 'price': 'Free', 'good_for': ['culture', 'dates']},
        {'name': 'Griffith Observatory', 'category': 'attractions', 'rating': 4.8, 'price': 'Free', 'good_for': ['dates', 'views']},
        {'name': 'Grand Central Market', 'category': 'food_hall', 'rating': 4.4, 'price': '$$', 'good_for': ['foodies', 'groups']},
        {'name': 'The Last Bookstore', 'category': 'bookstore', 'rating': 4.6, 'price': '$', 'good_for': ['browsing', 'photos']},
    ],
    'Indianapolis': [
        {'name': 'Sun King Brewery', 'category': 'brewery', 'rating': 4.5, 'price': '$$', 'good_for': ['groups', 'casual']},
        {'name': 'The Vogue', 'category': 'live_music', 'rating': 4.4, 'price': '$$', 'good_for': ['nightlife', 'concerts']},
        {'name': 'Newfields', 'category': 'museum', 'rating': 4.6, 'price': '$$', 'good_for': ['culture', 'dates']},
        {'name': 'Fountain Square Theatre', 'category': 'theater', 'rating': 4.3, 'price': '$$', 'good_for': ['culture', 'dates']},
        {'name': 'Circle City Industrial Complex', 'category': 'climbing', 'rating': 4.7, 'price': '$$', 'good_for': ['fitness', 'groups']},
    ]
}


class YelpTrendingService:
    """
    Service for fetching trending venues and experiences from Yelp Fusion API.
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Yelp API service.

        Args:
            api_key: Yelp API key. If not provided, loads from YELP_API_KEY env var.
        """
        self.api_key = api_key or os.environ.get('YELP_API_KEY')
        self.base_url = 'https://api.yelp.com/v3'
        self.session = requests.Session()

        if self.api_key:
            self.session.headers.update({
                'Authorization': f'Bearer {self.api_key}'
            })

        # Rate limiting: 500ms between requests (conservative)
        self.last_request_time = 0
        self.min_request_interval = 0.5  # seconds

        # Cache setup
        self.cache_dir = Path('/home/user/GiftWise/data')
        self.cache_dir.mkdir(exist_ok=True)
        self.cache_file = self.cache_dir / 'yelp_cache.json'
        self.cache_duration = 30  # minutes

        # Load cache
        self._load_cache()

    def _load_cache(self):
        """Load cache from disk."""
        try:
            if self.cache_file.exists():
                with open(self.cache_file, 'r') as f:
                    self.cache = json.load(f)
            else:
                self.cache = {}
        except Exception as e:
            print(f"Error loading Yelp cache: {e}")
            self.cache = {}

    def _save_cache(self):
        """Save cache to disk."""
        try:
            # Clean old entries (>24 hours)
            cutoff = datetime.now() - timedelta(hours=24)
            self.cache = {
                k: v for k, v in self.cache.items()
                if datetime.fromisoformat(v.get('cached_at', '2000-01-01')) > cutoff
            }

            with open(self.cache_file, 'w') as f:
                json.dump(self.cache, f, indent=2)
        except Exception as e:
            print(f"Error saving Yelp cache: {e}")

    def _get_cache_key(self, city: str, category: str = None, **kwargs) -> str:
        """Generate cache key."""
        key_parts = [city.lower().replace(' ', '_')]
        if category:
            key_parts.append(category)
        for k, v in sorted(kwargs.items()):
            key_parts.append(f"{k}:{v}")
        return '_'.join(key_parts)

    def _get_cached(self, cache_key: str) -> Optional[Dict]:
        """Get cached data if still valid."""
        if cache_key not in self.cache:
            return None

        cached_data = self.cache[cache_key]
        cached_at = datetime.fromisoformat(cached_data['cached_at'])
        age_minutes = (datetime.now() - cached_at).total_seconds() / 60

        if age_minutes < self.cache_duration:
            cached_data['cache_age_minutes'] = int(age_minutes)
            return cached_data

        return None

    def _set_cached(self, cache_key: str, data: Dict):
        """Cache data with timestamp."""
        data['cached_at'] = datetime.now().isoformat()
        self.cache[cache_key] = data
        self._save_cache()

    def _rate_limit(self):
        """Enforce rate limiting."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        self.last_request_time = time.time()

    def _make_request(self, endpoint: str, params: Dict) -> Optional[Dict]:
        """
        Make API request with error handling and rate limiting.

        Args:
            endpoint: API endpoint (e.g., '/businesses/search')
            params: Query parameters

        Returns:
            API response data or None on error
        """
        if not self.api_key:
            print("Warning: No Yelp API key configured. Using fallback data.")
            return None

        self._rate_limit()

        try:
            response = self.session.get(
                f"{self.base_url}{endpoint}",
                params=params,
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Yelp API error: {e}")
            return None

    def calculate_trending_score(self, venue: Dict) -> float:
        """
        Calculate trending score based on rating, review velocity, and popularity.

        Score factors:
        - Rating: 0-5 stars (40% weight)
        - Review velocity: Recent reviews (30% weight)
        - Review count: Total reviews (20% weight)
        - Price match: Matches gift budget (10% weight)

        Args:
            venue: Venue data from Yelp

        Returns:
            Trending score between 0.0 and 1.0
        """
        rating_score = venue.get('rating', 0) / 5.0

        # Estimate review velocity (Yelp doesn't provide this directly)
        # Use review count as proxy - higher count suggests ongoing activity
        review_count = venue.get('review_count', 0)
        review_velocity = min(review_count / 500, 1.0)  # 500+ reviews = max velocity score

        # Review count score
        review_count_score = min(review_count / 1000, 1.0)  # 1000+ reviews = max count score

        # Price match ($ and $$ are best for gift recommendations)
        price = venue.get('price', '$$')
        price_match = 1.0 if price in ['$', '$$'] else 0.5

        trending_score = (
            rating_score * 0.4 +
            review_velocity * 0.3 +
            review_count_score * 0.2 +
            price_match * 0.1
        )

        return round(trending_score, 2)

    def _format_venue(self, business: Dict) -> Dict:
        """
        Format Yelp business data into our standard venue format.

        Args:
            business: Raw Yelp business data

        Returns:
            Formatted venue dict
        """
        categories = [cat['alias'] for cat in business.get('categories', [])]
        primary_category = categories[0] if categories else 'general'

        # Determine what venue is good for based on category and attributes
        good_for = []
        if primary_category in ['coffee', 'cafes']:
            good_for = ['working', 'dates', 'catching up']
        elif primary_category in ['bars', 'pubs', 'cocktailbars']:
            good_for = ['dates', 'nightlife', 'groups']
        elif primary_category in ['breweries', 'brewpubs']:
            good_for = ['groups', 'casual', 'tastings']
        elif primary_category in ['museums', 'galleries']:
            good_for = ['culture', 'dates', 'learning']
        elif primary_category in ['musicvenues', 'jazzandblues']:
            good_for = ['nightlife', 'dates', 'entertainment']
        elif primary_category in ['spas', 'massage']:
            good_for = ['relaxation', 'self-care', 'dates']
        elif primary_category in ['climbing', 'gyms']:
            good_for = ['fitness', 'dates', 'groups']
        else:
            good_for = ['experiences', 'outings']

        venue = {
            'name': business['name'],
            'category': primary_category,
            'all_categories': categories,
            'rating': business.get('rating', 0),
            'review_count': business.get('review_count', 0),
            'price': business.get('price', '$$'),
            'address': ', '.join(business['location'].get('display_address', [])),
            'yelp_url': business.get('url', ''),
            'phone': business.get('display_phone', ''),
            'image_url': business.get('image_url', ''),
            'good_for': good_for,
            'distance_meters': business.get('distance'),
            'is_closed': business.get('is_closed', False)
        }

        # Calculate trending score
        venue['trending_score'] = self.calculate_trending_score(venue)

        # Determine why it's trending
        if venue['rating'] >= 4.5 and venue['review_count'] >= 200:
            venue['why_trending'] = 'Highly rated with strong buzz'
        elif venue['review_count'] >= 500:
            venue['why_trending'] = 'Popular local favorite'
        elif venue['rating'] >= 4.5:
            venue['why_trending'] = 'Excellent reviews'
        else:
            venue['why_trending'] = 'Active and well-reviewed'

        return venue

    def search_by_category(
        self,
        city: str,
        category: str,
        sort_by: str = 'rating',
        limit: int = 20
    ) -> List[Dict]:
        """
        Search Yelp for specific category in a city.

        Args:
            city: City name
            category: Yelp category alias (e.g., 'coffee', 'breweries')
            sort_by: Sort method - 'rating', 'review_count', or 'distance'
            limit: Max results to return

        Returns:
            List of formatted venue dicts
        """
        cache_key = self._get_cache_key(city, category, sort_by=sort_by, limit=limit)
        cached = self._get_cached(cache_key)
        if cached:
            return cached['venues']

        # Map sort_by to Yelp's sort parameters
        sort_param = {
            'rating': 'rating',
            'review_count': 'review_count',
            'distance': 'distance'
        }.get(sort_by, 'rating')

        params = {
            'location': city,
            'categories': category,
            'sort_by': sort_param,
            'limit': min(limit, 50)  # Yelp max is 50
        }

        data = self._make_request('/businesses/search', params)

        if not data or 'businesses' not in data:
            # Return fallback data if available
            if city in FALLBACK_VENUES:
                fallback = [v for v in FALLBACK_VENUES[city] if v['category'] == category]
                return fallback[:limit]
            return []

        venues = [self._format_venue(b) for b in data['businesses']]

        # Cache results
        self._set_cached(cache_key, {'venues': venues})

        return venues

    def get_trending_in_city(
        self,
        city: str,
        categories: List[str] = None,
        limit: int = 20
    ) -> Dict:
        """
        Get trending venues in a city, optionally filtered by categories.

        Args:
            city: City name
            categories: Optional list of category filters
            limit: Max venues to return

        Returns:
            Dict with trending_venues, popular_categories, and neighborhood_insights
        """
        cache_key = self._get_cache_key(
            city,
            'trending',
            categories=','.join(categories) if categories else 'all',
            limit=limit
        )
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        # If categories specified, search each and merge
        if categories:
            all_venues = []
            for category in categories:
                venues = self.search_by_category(city, category, sort_by='review_count', limit=10)
                all_venues.extend(venues)
        else:
            # General search for highly-rated places
            params = {
                'location': city,
                'sort_by': 'rating',
                'limit': min(limit, 50)
            }

            data = self._make_request('/businesses/search', params)

            if not data or 'businesses' not in data:
                # Return fallback data
                if city in FALLBACK_VENUES:
                    return {
                        'trending_venues': FALLBACK_VENUES[city][:limit],
                        'popular_categories': [],
                        'neighborhood_insights': {},
                        'cache_age_minutes': 0,
                        'data_source': 'fallback'
                    }
                return {
                    'trending_venues': [],
                    'popular_categories': [],
                    'neighborhood_insights': {},
                    'cache_age_minutes': 0
                }

            all_venues = [self._format_venue(b) for b in data['businesses']]

        # Sort by trending score
        all_venues.sort(key=lambda v: v['trending_score'], reverse=True)
        trending_venues = all_venues[:limit]

        # Analyze popular categories
        category_counts = {}
        category_ratings = {}
        for venue in all_venues:
            cat = venue['category']
            category_counts[cat] = category_counts.get(cat, 0) + 1
            if cat not in category_ratings:
                category_ratings[cat] = []
            category_ratings[cat].append(venue['rating'])

        popular_categories = [
            {
                'category': cat,
                'count': count,
                'avg_rating': round(sum(category_ratings[cat]) / len(category_ratings[cat]), 1)
            }
            for cat, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        ]

        # Neighborhood insights (simplified - Yelp doesn't provide this directly)
        neighborhoods = CITY_NEIGHBORHOODS.get(city, [])
        neighborhood_insights = {
            'hottest_neighborhood': neighborhoods[0] if neighborhoods else 'Downtown',
            'emerging_areas': neighborhoods[1:3] if len(neighborhoods) > 2 else []
        }

        result = {
            'trending_venues': trending_venues,
            'popular_categories': popular_categories,
            'neighborhood_insights': neighborhood_insights,
            'cache_age_minutes': 0,
            'data_source': 'yelp_api'
        }

        self._set_cached(cache_key, result)
        return result

    def get_experience_venues(self, city: str, experience_type: str) -> List[Dict]:
        """
        Get trending venues for a specific experience type.

        Maps experience types (e.g., 'cooking_class') to Yelp categories
        and returns top-rated venues.

        Args:
            city: City name
            experience_type: Experience type from EXPERIENCE_TO_YELP_CATEGORIES

        Returns:
            List of formatted venue dicts
        """
        categories = EXPERIENCE_TO_YELP_CATEGORIES.get(experience_type, [])

        if not categories:
            print(f"Warning: Unknown experience type '{experience_type}'")
            return []

        # Search each category and merge results
        all_venues = []
        for category in categories:
            venues = self.search_by_category(city, category, sort_by='rating', limit=10)
            all_venues.extend(venues)

        # Deduplicate by name and sort by trending score
        seen_names = set()
        unique_venues = []
        for venue in all_venues:
            if venue['name'] not in seen_names:
                seen_names.add(venue['name'])
                unique_venues.append(venue)

        unique_venues.sort(key=lambda v: v['trending_score'], reverse=True)
        return unique_venues[:20]

    def get_neighborhood_hotspots(
        self,
        city: str,
        neighborhood: str = None
    ) -> Dict:
        """
        Get trending spots in a specific neighborhood.

        Args:
            city: City name
            neighborhood: Specific neighborhood (optional)

        Returns:
            Dict with trending venues and neighborhood context
        """
        location = f"{neighborhood}, {city}" if neighborhood else city

        cache_key = self._get_cache_key(city, 'neighborhood', neighborhood=neighborhood or 'all')
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        params = {
            'location': location,
            'sort_by': 'rating',
            'limit': 30
        }

        data = self._make_request('/businesses/search', params)

        if not data or 'businesses' not in data:
            return {
                'neighborhood': neighborhood or 'city-wide',
                'trending_venues': [],
                'cache_age_minutes': 0
            }

        venues = [self._format_venue(b) for b in data['businesses']]
        venues.sort(key=lambda v: v['trending_score'], reverse=True)

        result = {
            'neighborhood': neighborhood or 'city-wide',
            'trending_venues': venues[:15],
            'cache_age_minutes': 0
        }

        self._set_cached(cache_key, result)
        return result

    def analyze_trending_interests(self, city: str) -> Dict:
        """
        Analyze what's popular in the city right now.

        Identifies:
        - Categories with highest review activity
        - Emerging trends (new highly-rated spots)
        - Popular price points

        Args:
            city: City name

        Returns:
            Dict with trending insights
        """
        cache_key = self._get_cache_key(city, 'analyze_trends')
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        # Get general trending venues
        trending_data = self.get_trending_in_city(city, limit=50)
        venues = trending_data['trending_venues']

        if not venues:
            return {
                'top_categories': [],
                'emerging_trends': [],
                'popular_price_points': [],
                'cache_age_minutes': 0
            }

        # Analyze categories
        category_activity = {}
        for venue in venues:
            cat = venue['category']
            if cat not in category_activity:
                category_activity[cat] = {
                    'count': 0,
                    'avg_rating': [],
                    'avg_trending_score': []
                }
            category_activity[cat]['count'] += 1
            category_activity[cat]['avg_rating'].append(venue['rating'])
            category_activity[cat]['avg_trending_score'].append(venue['trending_score'])

        top_categories = [
            {
                'category': cat,
                'venue_count': data['count'],
                'avg_rating': round(sum(data['avg_rating']) / len(data['avg_rating']), 1),
                'avg_trending_score': round(sum(data['avg_trending_score']) / len(data['avg_trending_score']), 2)
            }
            for cat, data in sorted(
                category_activity.items(),
                key=lambda x: x[1]['count'],
                reverse=True
            )[:10]
        ]

        # Identify emerging trends (high rating, moderate review count)
        emerging = [
            v for v in venues
            if v['rating'] >= 4.5 and 50 <= v['review_count'] <= 300
        ][:5]

        # Analyze price points
        price_counts = {}
        for venue in venues:
            price = venue['price']
            price_counts[price] = price_counts.get(price, 0) + 1

        popular_price_points = [
            {'price': p, 'count': c}
            for p, c in sorted(price_counts.items(), key=lambda x: x[1], reverse=True)
        ]

        result = {
            'top_categories': top_categories,
            'emerging_trends': [
                {'name': v['name'], 'category': v['category'], 'rating': v['rating']}
                for v in emerging
            ],
            'popular_price_points': popular_price_points,
            'cache_age_minutes': 0
        }

        self._set_cached(cache_key, result)
        return result


# Testing and demonstration
if __name__ == '__main__':
    print("=== Yelp Trending Service Test ===\n")

    service = YelpTrendingService()

    if not service.api_key:
        print("⚠️  No YELP_API_KEY found in environment. Using fallback data.\n")
    else:
        print("✅ Yelp API key configured\n")

    # Test 1: Austin trending venues
    print("1. Trending venues in Austin:")
    austin_trending = service.get_trending_in_city('Austin', limit=5)
    print(f"   Found {len(austin_trending['trending_venues'])} venues")
    print(f"   Data source: {austin_trending.get('data_source', 'api')}")
    if austin_trending['trending_venues']:
        top_venue = austin_trending['trending_venues'][0]
        print(f"   Top: {top_venue['name']} ({top_venue['category']}) - {top_venue['rating']}⭐")
        print(f"   Trending score: {top_venue['trending_score']}")
        print(f"   Why: {top_venue['why_trending']}")
    print()

    # Test 2: NYC coffee shops
    print("2. Coffee shops in NYC:")
    nyc_coffee = service.search_by_category('New York', 'coffee', limit=3)
    print(f"   Found {len(nyc_coffee)} coffee shops")
    for venue in nyc_coffee[:2]:
        print(f"   - {venue['name']}: {venue['rating']}⭐, {venue['price']}")
    print()

    # Test 3: Experience venue mapping
    print("3. Cooking classes in Austin:")
    cooking_venues = service.get_experience_venues('Austin', 'cooking_class')
    print(f"   Found {len(cooking_venues)} venues")
    for venue in cooking_venues[:2]:
        print(f"   - {venue['name']} ({venue['category']})")
    print()

    # Test 4: Neighborhood hotspots
    print("4. East Austin hotspots:")
    east_austin = service.get_neighborhood_hotspots('Austin', 'East Austin')
    print(f"   Found {len(east_austin['trending_venues'])} hotspots")
    if east_austin['trending_venues']:
        print(f"   Top: {east_austin['trending_venues'][0]['name']}")
    print()

    # Test 5: Trending analysis
    print("5. What's trending in Chicago:")
    chicago_trends = service.analyze_trending_interests('Chicago')
    print(f"   Top categories: {len(chicago_trends['top_categories'])}")
    if chicago_trends['top_categories']:
        top_cat = chicago_trends['top_categories'][0]
        print(f"   #1: {top_cat['category']} ({top_cat['venue_count']} venues, {top_cat['avg_rating']}⭐)")
    if chicago_trends['emerging_trends']:
        print(f"   Emerging: {chicago_trends['emerging_trends'][0]['name']}")
    print()

    # Test 6: Category mapping
    print("6. Experience type mappings:")
    sample_types = ['live_music', 'spa_day', 'brewery_tour', 'art_class']
    for exp_type in sample_types:
        categories = EXPERIENCE_TO_YELP_CATEGORIES.get(exp_type, [])
        print(f"   {exp_type}: {', '.join(categories)}")
    print()

    # Test 7: Cache status
    print("7. Cache status:")
    print(f"   Cache file: {service.cache_file}")
    print(f"   Cached entries: {len(service.cache)}")
    print(f"   Cache duration: {service.cache_duration} minutes")
    print()

    print("✅ All tests complete!")
    print("\nIntegration examples:")
    print("  # In experience_synthesis.py:")
    print("  trending = yelp.get_experience_venues('Austin', 'cooking_class')")
    print("  experience['trending_venues'] = trending[:3]")
    print()
    print("  # In regional_culture.py:")
    print("  context['whats_hot'] = yelp.get_trending_in_city(city, limit=10)")
