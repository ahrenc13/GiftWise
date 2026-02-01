"""
EXPERIENCE SYNTHESIS - Create contextually connected experience packages
Prevents random mashing like "Stevie Nicks concert + basketball game"
Creates coherent packages like "Kitchen + cooking class"

Author: Chad + Claude  
Date: February 2026
"""

import logging

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
        Generate contextually coherent experience packages
        
        Args:
            profile: User profile with interests
            location_context: Geographic context
            max_experiences: Number of experiences to generate
        
        Returns:
            List of experience dicts with coherent themes
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
        
        for cluster_name, cluster_data in sorted_clusters[:max_experiences]:
            # Pick an experience from this cluster
            import random
            experience_template = random.choice(cluster_data['experiences'])
            
            # Get the relevant interests for this cluster
            cluster_interests = cluster_data['interests']
            
            # Create contextual experience
            if cluster_interests:
                interest_names = [i.get('name', '') for i in cluster_interests]
                
                experience = {
                    'title': experience_template,
                    'description': ExperienceSynthesizer._generate_description(
                        experience_template,
                        interest_names,
                        city,
                        cluster_name
                    ),
                    'cluster': cluster_name,
                    'related_interests': interest_names,
                    'type': 'experience'
                }
                
                experiences.append(experience)
        
        logger.info(f"Generated {len(experiences)} contextually coherent experiences")
        
        return experiences
    
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
