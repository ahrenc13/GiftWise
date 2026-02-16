"""
EXPERIENCE SYNTHESIS - Create contextually connected experience packages
Prevents random mashing like "Stevie Nicks concert + basketball game"
Creates coherent packages like "Kitchen + cooking class"

NOW WITH REGIONAL INTELLIGENCE:
- Regional culture context (Midwest vs South vs West Coast vs Northeast)
- Seasonal appropriateness (no beach trips in Seattle winter)
- Local events (Indy 500, SXSW, etc.)
- Demographic synthesis (25F Austin ≠ 25F Indianapolis)

Author: Chad + Claude
Date: February 2026
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

# Import the new intelligence modules
try:
    from regional_culture import get_regional_context, get_gift_guidance_for_region
    from seasonal_experiences import get_seasonal_context, get_seasonal_experiences, should_avoid_outdoor
    from local_events import get_local_events, get_event_suggestions
    REGIONAL_INTELLIGENCE_AVAILABLE = True
except ImportError:
    REGIONAL_INTELLIGENCE_AVAILABLE = False
    logging.warning("Regional intelligence modules not available. Experience synthesis will use basic mode.")

logger = logging.getLogger(__name__)


class ExperienceSynthesizer:
    """Create complementary experience packages based on thematic clustering"""
    
    # Thematic clusters - interests that naturally go together
    THEMATIC_CLUSTERS = {
        'culinary': {
            'keywords': ['cooking', 'kitchen', 'food', 'restaurant', 'wine', 'chef', 'baking', 'recipes'],
            'experiences': [
                'Couples cooking class',
                'Wine tasting experience', 
                'Farm-to-table dinner',
                'Private chef experience',
                'Food tour',
                'Cooking workshop'
            ]
        },
        'outdoor_adventure': {
            'keywords': ['hiking', 'camping', 'outdoor', 'nature', 'trail', 'park', 'wilderness', 'kayaking'],
            'experiences': [
                'Guided hiking tour',
                'Camping weekend',
                'Kayaking adventure',
                'Nature photography workshop',
                'Rock climbing lesson',
                'Wilderness survival course'
            ]
        },
        'wellness_spa': {
            'keywords': ['yoga', 'meditation', 'spa', 'wellness', 'massage', 'relaxation', 'mindfulness'],
            'experiences': [
                'Couples spa day',
                'Yoga retreat weekend',
                'Meditation workshop',
                'Wellness retreat',
                'Hot springs visit',
                'Float therapy session'
            ]
        },
        'music_performance': {
            'keywords': ['concert', 'music', 'band', 'singer', 'performance', 'show', 'festival'],
            'experiences': [
                'Concert tickets',
                'Music festival weekend',
                'Intimate venue show',
                'Backstage meet and greet',
                'Music appreciation class',
                'Record store day'
            ]
        },
        'sports_active': {
            'keywords': ['sports', 'playing', 'training', 'practice', 'game', 'competition', 'fitness', 'gym'],
            'experiences': [
                'Personal training session',
                'Sports clinic or camp',
                'Gym membership',
                'Fitness class pass',
                'Sports equipment rental',
                'Competition entry'
            ]
        },
        'sports_watching': {
            'keywords': ['watching sports', 'fan', 'games', 'matches', 'team', 'championship'],
            'experiences': [
                'Premium game tickets',
                'Sports bar experience',
                'Watch party package',
                'Season ticket package',
                'Fan fest access',
                'Viewing party'
            ]
        },
        'arts_culture': {
            'keywords': ['art', 'museum', 'gallery', 'theater', 'culture', 'exhibition', 'performance art'],
            'experiences': [
                'Museum membership',
                'Gallery opening',
                'Theater tickets',
                'Art class',
                'Cultural tour',
                'Exhibition access'
            ]
        },
        'home_lifestyle': {
            'keywords': ['home', 'renovation', 'interior design', 'decorating', 'gardening', 'diy'],
            'experiences': [
                'Interior design consultation',
                'Home organization service',
                'Garden design workshop',
                'DIY class',
                'Furniture making workshop',
                'Home styling session'
            ]
        }
    }
    
    @staticmethod
    def cluster_interests(interests, profile_context):
        """
        Group interests into thematic clusters
        
        Args:
            interests: List of interest dicts
            profile_context: Additional context (location, home details, etc.)
        
        Returns:
            Dict of cluster_name -> matched_interests
        """
        
        clustered = {}
        
        for cluster_name, cluster_data in ExperienceSynthesizer.THEMATIC_CLUSTERS.items():
            keywords = cluster_data['keywords']
            matched_interests = []
            
            for interest in interests:
                interest_text = f"{interest.get('name', '')} {interest.get('description', '')}".lower()
                
                # Check if interest matches this cluster
                if any(keyword in interest_text for keyword in keywords):
                    matched_interests.append(interest)
            
            if matched_interests:
                clustered[cluster_name] = {
                    'interests': matched_interests,
                    'experiences': cluster_data['experiences']
                }
        
        # Check profile context for additional clustering
        # Example: "Beautiful renovated kitchen" → culinary cluster
        if profile_context:
            home_details = profile_context.get('home_details', '').lower()
            
            if 'kitchen' in home_details or 'cooking' in home_details:
                if 'culinary' in clustered:
                    clustered['culinary']['context_boost'] = True
                else:
                    clustered['culinary'] = {
                        'interests': [],
                        'experiences': ExperienceSynthesizer.THEMATIC_CLUSTERS['culinary']['experiences'],
                        'context_boost': True
                    }
        
        return clustered
    
    @staticmethod
    def generate_experiences(profile, location_context, max_experiences=3):
        """
        Generate contextually coherent experience packages with regional intelligence.

        Args:
            profile: User profile with interests, age, gender
            location_context: Geographic context (city_region, state, etc.)
            max_experiences: Number of experiences to generate

        Returns:
            List of experience dicts with coherent themes, regional context, and seasonal appropriateness
        """

        interests = profile.get('interests', [])

        # Cluster interests thematically
        clusters = ExperienceSynthesizer.cluster_interests(interests, profile)

        experiences = []

        # Prioritize clusters with context boost (e.g., kitchen → cooking)
        sorted_clusters = sorted(
            clusters.items(),
            key=lambda x: (x[1].get('context_boost', False), len(x[1]['interests'])),
            reverse=True
        )

        city = location_context.get('city_region', 'your city')

        # NEW: Get regional + seasonal intelligence
        regional_context = None
        seasonal_context = None
        local_events = []

        if REGIONAL_INTELLIGENCE_AVAILABLE:
            # Extract location details
            city_name = city.split(',')[0].strip() if city and ',' in city else city
            state = location_context.get('state') or (city.split(',')[1].strip() if city and ',' in city else None)
            age = profile.get('age')
            gender = profile.get('gender')
            current_month = datetime.now().month

            # Get regional context
            regional_context = get_regional_context(city=city_name, state=state, age=age, gender=gender)

            # Get seasonal context (determine region from regional_context)
            region = regional_context.get('region_name') if regional_context else None
            seasonal_context = get_seasonal_context(month=current_month, region=region)

            # Get local events
            interest_names = [i.get('name', '') for i in interests[:5]]
            local_events = get_event_suggestions(city_name, state, interests=interest_names) if city_name else []

            logger.info(f"Regional intelligence loaded: {region or 'unknown'}, {seasonal_context.get('season', 'unknown')} season, {len(local_events)} local events")

        for cluster_name, cluster_data in sorted_clusters[:max_experiences]:
            # Pick an experience from this cluster
            import random
            experience_template = random.choice(cluster_data['experiences'])

            # Get the relevant interests for this cluster
            cluster_interests = cluster_data['interests']

            # Create contextual experience
            if cluster_interests:
                interest_names = [i.get('name', '') for i in cluster_interests]

                # NEW: Check if this experience is seasonally appropriate
                is_outdoor = ExperienceSynthesizer._is_outdoor_experience(cluster_name, experience_template)

                # Skip outdoor experiences if weather is bad (optional - can be softened)
                if REGIONAL_INTELLIGENCE_AVAILABLE and seasonal_context:
                    if is_outdoor and should_avoid_outdoor(seasonal_context.get('month'), seasonal_context.get('region')):
                        # Try to substitute with indoor variant
                        indoor_experiences = [e for e in cluster_data['experiences'] if 'indoor' in e.lower() or 'class' in e.lower()]
                        if indoor_experiences:
                            experience_template = random.choice(indoor_experiences)
                            logger.info(f"Substituted outdoor experience with indoor variant: {experience_template}")

                description = ExperienceSynthesizer._generate_description_with_context(
                    experience_template,
                    interest_names,
                    city,
                    cluster_name,
                    regional_context,
                    seasonal_context,
                )

                experience = {
                    'title': experience_template,
                    'description': description,
                    'cluster': cluster_name,
                    'related_interests': interest_names,
                    'type': 'experience',
                    'regional_context': regional_context.get('demographic_synthesis') if regional_context else None,
                    'seasonal_notes': seasonal_context.get('weather_notes') if seasonal_context else None,
                }

                experiences.append(experience)

        # NEW: Add local event-based experiences if available
        if local_events and len(experiences) < max_experiences:
            for event in local_events[:max_experiences - len(experiences)]:
                experiences.append({
                    'title': event,
                    'description': f"A local event happening in {city} that matches their interests.",
                    'cluster': 'local_event',
                    'type': 'experience',
                    'is_local_event': True,
                })

        logger.info(f"Generated {len(experiences)} contextually coherent experiences (regional intelligence: {REGIONAL_INTELLIGENCE_AVAILABLE})")

        return experiences

    @staticmethod
    def _is_outdoor_experience(cluster_name: str, experience_name: str) -> bool:
        """Check if an experience is primarily outdoor."""
        outdoor_keywords = ['outdoor', 'hiking', 'camping', 'beach', 'kayaking', 'park', 'trail', 'garden']
        outdoor_clusters = ['outdoor_adventure']

        text = f"{cluster_name} {experience_name}".lower()
        return cluster_name in outdoor_clusters or any(keyword in text for keyword in outdoor_keywords)

    @staticmethod
    def _generate_description_with_context(
        experience_template: str,
        interest_names: List[str],
        city: str,
        cluster_name: str,
        regional_context: Optional[Dict] = None,
        seasonal_context: Optional[Dict] = None,
    ) -> str:
        """Generate description with regional and seasonal context."""

        # Start with base description
        base_descriptions = {
            'culinary': f"Since they love {', '.join(interest_names[:2])}, this {experience_template.lower()} in {city} would let them explore their culinary passions together.",
            'outdoor_adventure': f"Perfect for their love of {interest_names[0]}, this {experience_template.lower()} combines adventure with the great outdoors.",
            'wellness_spa': f"A relaxing {experience_template.lower()} to unwind and recharge. Great match for their interest in wellness and self-care.",
            'music_performance': f"They'll love this {experience_template.lower()} - a perfect way to experience {interest_names[0]} live in {city}.",
            'sports_watching': f"For the sports fan, these {experience_template.lower()} provide the ultimate viewing experience of their favorite teams.",
            'arts_culture': f"This {experience_template.lower()} in {city} aligns perfectly with their appreciation for {', '.join(interest_names[:2])}.",
            'home_lifestyle': f"Since they enjoy {interest_names[0]}, this {experience_template.lower()} would be both practical and personally meaningful."
        }

        description = base_descriptions.get(cluster_name, f"A great experience based on their interests in {', '.join(interest_names[:2])}.")

        # Add regional flavor if available
        if regional_context and regional_context.get('demographic_synthesis'):
            # Regional context already provides rich demographic insight
            # Example: "Young female in Austin loves live music..." - already captured in regional_context
            pass

        # Add seasonal note if relevant
        if seasonal_context:
            season = seasonal_context.get('season', '')
            if season and season != 'unknown':
                # Add subtle seasonal note
                seasonal_notes = {
                    'winter': "Perfect for cozy winter months.",
                    'spring': "Great for spring season.",
                    'summer': "Ideal for summer.",
                    'fall': "Perfect for fall season.",
                }
                description += f" {seasonal_notes.get(season, '')}"

        return description
    
    @staticmethod
    def _generate_description(experience_template, interest_names, city, cluster_name):
        """Generate a contextual description for the experience"""
        
        descriptions = {
            'culinary': f"Since they love {', '.join(interest_names[:2])}, this {experience_template.lower()} in {city} would let them explore their culinary passions together.",
            'outdoor_adventure': f"Perfect for their love of {interest_names[0]}, this {experience_template.lower()} combines adventure with the great outdoors.",
            'wellness_spa': f"A relaxing {experience_template.lower()} to unwind and recharge. Great match for their interest in wellness and self-care.",
            'music_performance': f"They'll love this {experience_template.lower()} - a perfect way to experience {interest_names[0]} live in {city}.",
            'sports_watching': f"For the sports fan, these {experience_template.lower()} provide the ultimate viewing experience of their favorite teams.",
            'arts_culture': f"This {experience_template.lower()} in {city} aligns perfectly with their appreciation for {', '.join(interest_names[:2])}.",
            'home_lifestyle': f"Since they enjoy {interest_names[0]}, this {experience_template.lower()} would be both practical and personally meaningful."
        }
        
        return descriptions.get(cluster_name, f"A great experience based on their interests in {', '.join(interest_names[:2])}.")
    
    @staticmethod
    def validate_experience_coherence(experience1, experience2):
        """
        Check if two experiences make sense together (for multi-experience packages)
        
        Returns:
            {
                'coherent': bool,
                'reason': str
            }
        """
        
        cluster1 = experience1.get('cluster', '')
        cluster2 = experience2.get('cluster', '')
        
        # Same cluster = always coherent
        if cluster1 == cluster2:
            return {'coherent': True, 'reason': 'Same thematic cluster'}
        
        # Compatible clusters
        compatible_pairs = [
            ('culinary', 'home_lifestyle'),  # Cooking + home = makes sense
            ('outdoor_adventure', 'wellness_spa'),  # Nature + wellness = retreat vibe
            ('music_performance', 'arts_culture'),  # Entertainment + culture
            ('sports_active', 'wellness_spa'),  # Fitness + recovery
        ]
        
        for pair in compatible_pairs:
            if (cluster1, cluster2) in [pair, pair[::-1]]:
                return {'coherent': True, 'reason': f'Compatible themes: {cluster1} + {cluster2}'}
        
        # Incompatible
        return {
            'coherent': False,
            'reason': f'Unrelated themes: {cluster1} and {cluster2} don\'t naturally complement each other'
        }


def generate_smart_experiences(profile, location_context, max_count=3):
    """
    Convenience function to generate contextually coherent experiences

    Args:
        profile: User profile
        location_context: Geographic info
        max_count: Max experiences to generate

    Returns:
        List of coherent experience recommendations
    """

    synthesizer = ExperienceSynthesizer()
    return synthesizer.generate_experiences(profile, location_context, max_count)


def synthesize_with_geo_culture(
    profile: Dict[str, Any],
    location_context: Dict[str, Any],
    max_experiences: int = 3
) -> Dict[str, Any]:
    """
    MASTER SYNTHESIS FUNCTION - Combines all intelligence layers.

    This is the "oh wow, this AI actually GETS my city" function.

    Synthesizes:
    1. Interest clustering (existing)
    2. Regional culture context (NEW)
    3. Seasonal appropriateness (NEW)
    4. Local events calendar (NEW)
    5. Demographic insights by region (NEW)

    Args:
        profile: User profile with interests, age, gender
        location_context: Geographic context (city_region, state)
        max_experiences: Number of experiences to generate

    Returns:
        {
            'experiences': [...],  # Experience recommendations
            'regional_guidance': 'Text description of regional gift norms',
            'seasonal_guidance': 'Text description of seasonal considerations',
            'local_events': [...],  # Upcoming local events
            'avoid_experiences': [...],  # Experiences to avoid (weather/culture)
        }
    """

    result = {
        'experiences': [],
        'regional_guidance': '',
        'seasonal_guidance': '',
        'local_events': [],
        'avoid_experiences': [],
    }

    # Generate core experiences (now with regional/seasonal intelligence baked in)
    experiences = generate_smart_experiences(profile, location_context, max_experiences)
    result['experiences'] = experiences

    # Add regional and seasonal guidance
    if REGIONAL_INTELLIGENCE_AVAILABLE:
        city_name = location_context.get('city_region', '').split(',')[0].strip() if location_context.get('city_region') else None
        state = location_context.get('state')
        age = profile.get('age')
        gender = profile.get('gender')
        current_month = datetime.now().month

        # Regional guidance
        regional_context = get_regional_context(city=city_name, state=state, age=age, gender=gender)
        result['regional_guidance'] = get_gift_guidance_for_region(regional_context)

        # Seasonal guidance
        region = regional_context.get('region_name') if regional_context else None
        from seasonal_experiences import get_seasonal_guidance
        result['seasonal_guidance'] = get_seasonal_guidance(current_month, region)

        # Local events
        interest_names = [i.get('name', '') for i in profile.get('interests', [])[:5]]
        result['local_events'] = get_event_suggestions(city_name, state, interests=interest_names) if city_name else []

        # Experiences to avoid (based on season + region)
        seasonal_context = get_seasonal_context(current_month, region)
        result['avoid_experiences'] = seasonal_context.get('avoid_experiences', [])

        logger.info(f"Geo-culture synthesis complete: {len(result['experiences'])} experiences, {len(result['local_events'])} local events")

    return result


# ================================================================================
# TESTING
# ================================================================================

if __name__ == '__main__':
    # Test the new geo-culture synthesis
    print("=" * 80)
    print("TEST: Geo-Culture Synthesis for 25F in Austin")
    print("=" * 80)

    test_profile = {
        'age': 27,
        'gender': 'F',
        'interests': [
            {'name': 'Live music', 'description': 'Loves indie concerts', 'intensity': 'passionate'},
            {'name': 'Yoga', 'description': 'Regular practice', 'intensity': 'moderate'},
            {'name': 'Cooking', 'description': 'Thai cooking enthusiast', 'intensity': 'passionate'},
        ],
    }

    test_location = {
        'city_region': 'Austin, Texas',
        'state': 'Texas',
    }

    result = synthesize_with_geo_culture(test_profile, test_location, max_experiences=3)

    print("\nEXPERIENCES:")
    for exp in result['experiences']:
        print(f"  - {exp['title']}")
        print(f"    {exp['description']}")

    print(f"\nREGIONAL GUIDANCE:")
    print(f"  {result['regional_guidance']}")

    print(f"\nSEASONAL GUIDANCE:")
    print(f"  {result['seasonal_guidance']}")

    print(f"\nLOCAL EVENTS:")
    for event in result['local_events'][:5]:
        print(f"  - {event}")

    print(f"\nAVOID (seasonal):")
    for avoid in result['avoid_experiences'][:3]:
        print(f"  - {avoid}")
