"""
ENRICHMENT ENGINE
Main coordinator for enhancing recipient profiles with curated intelligence.
Uses static database + staged updates for reliability.
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Any, Optional

# Import static intelligence database
from enrichment_data import (
    GIFT_INTELLIGENCE,
    DEMOGRAPHIC_INTELLIGENCE,
    RELATIONSHIP_INTELLIGENCE,
    ANTI_RECOMMENDATIONS,
    TRENDING_2026,
    get_database_stats
)

class EnrichmentEngine:
    """
    Enhances recipient profiles with curated gift intelligence.
    
    Flow:
    1. Load recipient profile (interests, demographics, relationship)
    2. Match against static intelligence
    3. Check for staged updates (if available)
    4. Return enriched profile with actionable guidance
    """
    
    def __init__(self, updates_path='/mnt/user-data/staged_updates'):
        """
        Initialize enrichment engine.
        
        Args:
            updates_path: Path to staged update files (approved by user)
        """
        self.updates_path = updates_path
        self.staged_updates = self._load_staged_updates()
        
    def _load_staged_updates(self) -> Dict:
        """Load approved staged updates if available."""
        try:
            update_file = os.path.join(self.updates_path, 'approved_updates.json')
            if os.path.exists(update_file):
                with open(update_file, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            print(f"Warning: Could not load staged updates: {e}")
            return {}
    
    def enrich_profile(
        self,
        interests: List[str],
        age: Optional[int] = None,
        gender: Optional[str] = None,
        relationship: str = 'close_friend',
        location: Optional[str] = None,
        budget: Optional[tuple] = None
    ) -> Dict[str, Any]:
        """
        Main enrichment function - enhances profile with intelligence.
        
        Args:
            interests: List of recipient's interests
            age: Recipient's age
            gender: Recipient's gender
            relationship: Your relationship to recipient
            location: Recipient's location
            budget: Budget range (min, max)
            
        Returns:
            Enriched profile with enhanced recommendations
        """
        
        # Build enriched profile
        enriched = {
            'original_interests': interests,
            'enriched_interests': [],
            'demographics': self._get_demographic_guidance(age, gender),
            'relationship_guidance': self._get_relationship_guidance(relationship),
            'price_guidance': self._get_price_guidance(relationship, age, gender, budget),
            'search_strategy': [],
            'anti_recommendations': [],
            'trending_items': [],
            'quality_filters': [],
            'metadata': {
                'enrichment_version': '1.0.0',
                'enrichment_date': datetime.now().isoformat(),
                'data_sources': ['static_intelligence', 'staged_updates'],
                'confidence': 'high'
            }
        }
        
        # Enrich each interest
        for interest in interests:
            interest_data = self._enrich_interest(interest)
            if interest_data:
                enriched['enriched_interests'].append(interest_data)
        
        # Add global guidance
        enriched['search_strategy'] = self._build_search_strategy(enriched)
        enriched['quality_filters'] = self._build_quality_filters(enriched)
        
        return enriched
    
    def _enrich_interest(self, interest: str) -> Optional[Dict]:
        """
        Enhance a single interest with intelligence.
        
        Returns detailed gift guidance for this interest.
        """
        interest_key = interest.lower().replace(' ', '_')
        
        # Check staged updates first (fresher data)
        if interest_key in self.staged_updates.get('interests', {}):
            intel = self.staged_updates['interests'][interest_key]
        # Fallback to static data
        elif interest_key in GIFT_INTELLIGENCE:
            intel = GIFT_INTELLIGENCE[interest_key]
        else:
            # No intelligence available for this interest
            return None
        
        return {
            'interest': interest,
            'do_buy': intel.get('do_buy', []),
            'dont_buy': intel.get('dont_buy', []),
            'trending_2026': intel.get('trending_2026', []),
            'search_terms': intel.get('search_terms', []),
            'price_points': intel.get('price_points', {}),
            'activity_type': intel.get('activity_type', 'unknown'),
            'gift_occasions': intel.get('gift_occasions', [])
        }
    
    def _get_demographic_guidance(self, age: Optional[int], gender: Optional[str]) -> Dict:
        """Get demographic-specific gift guidance."""
        if not age or not gender:
            return {
                'note': 'No demographic data available',
                'guidance': 'Use interest-based recommendations only'
            }
        
        # Determine demographic bucket
        demo_key = None
        gender_lower = gender.lower() if gender else 'unknown'
        
        if age < 25:
            demo_key = f"{gender_lower}_18_25"
        elif age < 35:
            demo_key = f"{gender_lower}_25_35"
        elif age < 45:
            demo_key = f"{gender_lower}_35_45"
        else:
            demo_key = f"{gender_lower}_45_plus"
        
        # Check staged updates first
        if demo_key in self.staged_updates.get('demographics', {}):
            demo = self.staged_updates['demographics'][demo_key]
        # Fallback to static data
        elif demo_key in DEMOGRAPHIC_INTELLIGENCE:
            demo = DEMOGRAPHIC_INTELLIGENCE[demo_key]
        else:
            return {'note': 'No specific demographic guidance available'}
        
        return {
            'demographic_bucket': demo_key,
            'interests_bias': demo.get('interests_bias', []),
            'price_preference': demo.get('price_preference', (0, 0)),
            'gift_style': demo.get('gift_style', 'unknown'),
            'avoid': demo.get('avoid', []),
            'popular_categories': demo.get('popular_categories', [])
        }
    
    def _get_relationship_guidance(self, relationship: str) -> Dict:
        """Get relationship-specific gift guidance."""
        rel_key = relationship.lower().replace(' ', '_')
        
        # Check staged updates first
        if rel_key in self.staged_updates.get('relationships', {}):
            rel = self.staged_updates['relationships'][rel_key]
        # Fallback to static data
        elif rel_key in RELATIONSHIP_INTELLIGENCE:
            rel = RELATIONSHIP_INTELLIGENCE[rel_key]
        else:
            # Default to close_friend if unknown
            rel = RELATIONSHIP_INTELLIGENCE['close_friend']
        
        return {
            'relationship': relationship,
            'price_range': rel.get('price_range', (0, 0)),
            'sweet_spots': rel.get('sweet_spots', []),
            'gift_style': rel.get('gift_style', 'thoughtful'),
            'appropriateness': rel.get('appropriateness', {}),
            'red_flags': rel.get('red_flags', []),
            'winning_categories': rel.get('winning_categories', []),
            'occasions': rel.get('occasions', [])
        }
    
    def _get_price_guidance(
        self,
        relationship: str,
        age: Optional[int],
        gender: Optional[str],
        budget: Optional[tuple]
    ) -> Dict:
        """
        Determine optimal price range considering all factors.
        
        Priority: User budget > Relationship norms > Demographic preferences
        """
        # Start with relationship guidance
        rel_guidance = self._get_relationship_guidance(relationship)
        price_range = rel_guidance['price_range']
        sweet_spots = rel_guidance['sweet_spots']
        
        # Adjust for demographics if available
        demo_guidance = self._get_demographic_guidance(age, gender)
        if 'price_preference' in demo_guidance:
            demo_range = demo_guidance['price_preference']
            # Blend relationship and demographic ranges
            price_range = (
                (price_range[0] + demo_range[0]) // 2,
                (price_range[1] + demo_range[1]) // 2
            )
        
        # Override with user budget if provided
        if budget:
            price_range = budget
            # Recalculate sweet spots within budget
            sweet_spots = [
                budget[0] + (budget[1] - budget[0]) * 0.3,
                budget[0] + (budget[1] - budget[0]) * 0.5,
                budget[0] + (budget[1] - budget[0]) * 0.7
            ]
            sweet_spots = [int(spot) for spot in sweet_spots]
        
        return {
            'price_range': price_range,
            'sweet_spots': sweet_spots,
            'guidance': f"Target ${sweet_spots[1]} (range: ${price_range[0]}-${price_range[1]})",
            'budget_source': 'user_specified' if budget else 'calculated'
        }
    
    def _build_search_strategy(self, enriched_profile: Dict) -> List[Dict]:
        """
        Build search strategy based on enriched profile.
        
        Returns prioritized list of search approaches.
        """
        strategies = []
        
        # Strategy 1: Interest-specific searches
        for interest_data in enriched_profile['enriched_interests']:
            search_terms = interest_data.get('search_terms', [])
            do_buy = interest_data.get('do_buy', [])
            
            strategies.append({
                'priority': 1,
                'approach': 'interest_specific',
                'interest': interest_data['interest'],
                'search_terms': search_terms,
                'focus_categories': do_buy[:3],  # Top 3 recommended categories
                'price_filter': enriched_profile['price_guidance']['price_range']
            })
        
        # Strategy 2: Demographic-popular items
        demo_guidance = enriched_profile.get('demographics', {})
        if 'popular_categories' in demo_guidance:
            strategies.append({
                'priority': 2,
                'approach': 'demographic_popular',
                'categories': demo_guidance['popular_categories'],
                'price_filter': demo_guidance.get('price_preference', (0, 0))
            })
        
        # Strategy 3: Trending items
        strategies.append({
            'priority': 3,
            'approach': 'trending',
            'categories': TRENDING_2026.keys(),
            'note': 'Supplement core recommendations with trending items'
        })
        
        return strategies
    
    def _build_quality_filters(self, enriched_profile: Dict) -> List[str]:
        """
        Build list of quality filters to apply during product search.
        
        These help exclude inappropriate items.
        """
        filters = []
        
        # Add anti-recommendations from interests
        for interest_data in enriched_profile['enriched_interests']:
            dont_buy = interest_data.get('dont_buy', [])
            filters.extend(dont_buy)
        
        # Add relationship red flags
        rel_guidance = enriched_profile['relationship_guidance']
        filters.extend(rel_guidance.get('red_flags', []))
        
        # Add demographic avoidances
        demo_guidance = enriched_profile.get('demographics', {})
        filters.extend(demo_guidance.get('avoid', []))
        
        # Deduplicate
        filters = list(set(filters))
        
        return filters
    
    def get_enrichment_summary(self, enriched_profile: Dict) -> str:
        """
        Generate human-readable summary of enrichment.
        
        Useful for debugging and logging.
        """
        interests_count = len(enriched_profile['enriched_interests'])
        price_range = enriched_profile['price_guidance']['price_range']
        relationship = enriched_profile['relationship_guidance']['relationship']
        
        summary = f"""
ENRICHMENT SUMMARY
==================
Interests Enriched: {interests_count}
Relationship: {relationship}
Price Range: ${price_range[0]}-${price_range[1]}
Search Strategies: {len(enriched_profile['search_strategy'])}
Quality Filters: {len(enriched_profile['quality_filters'])}
Data Source: {', '.join(enriched_profile['metadata']['data_sources'])}
Confidence: {enriched_profile['metadata']['confidence']}
"""
        return summary.strip()


# =============================================================================
# HELPER FUNCTIONS FOR INTEGRATION
# =============================================================================

def enrich_profile_simple(
    interests: List[str],
    relationship: str = 'close_friend',
    age: Optional[int] = None,
    gender: Optional[str] = None,
    budget: Optional[tuple] = None
) -> Dict:
    """
    Simplified enrichment function for easy integration.
    
    Example usage in giftwise_app.py:
        from enrichment_engine import enrich_profile_simple
        
        enriched = enrich_profile_simple(
            interests=['basketball', 'cooking'],
            relationship='romantic_partner',
            age=28,
            gender='female',
            budget=(50, 150)
        )
        
        # Use enriched data for product search
        search_terms = []
        for interest in enriched['enriched_interests']:
            search_terms.extend(interest['search_terms'])
    """
    engine = EnrichmentEngine()
    return engine.enrich_profile(
        interests=interests,
        age=age,
        gender=gender,
        relationship=relationship,
        budget=budget
    )


def get_enhanced_search_terms(interests: List[str]) -> List[str]:
    """
    Quick function to get enhanced search terms for interests.
    
    Example usage:
        search_terms = get_enhanced_search_terms(['basketball', 'cooking'])
        # Returns: ['NBA collectibles', 'basketball memorabilia', 'chef knife set', ...]
    """
    enriched = enrich_profile_simple(interests=interests)
    search_terms = []
    for interest_data in enriched['enriched_interests']:
        search_terms.extend(interest_data.get('search_terms', []))
    return search_terms


def get_quality_exclusions(interests: List[str], relationship: str) -> List[str]:
    """
    Quick function to get items to exclude from search results.
    
    Example usage:
        exclusions = get_quality_exclusions(['basketball', 'cooking'], 'romantic_partner')
        # Returns: ['Basic basketballs', 'Gym equipment', 'Cheap cookware', ...]
    """
    enriched = enrich_profile_simple(interests=interests, relationship=relationship)
    return enriched['quality_filters']


def should_filter_product(product_title: str, quality_filters: List[str]) -> bool:
    """
    Check if a product should be filtered out based on quality filters.
    
    Args:
        product_title: Product title to check
        quality_filters: List of filter terms from enrichment
        
    Returns:
        True if product should be filtered out, False if it's okay
        
    Example usage:
        filters = get_quality_exclusions(['basketball'], 'romantic_partner')
        
        if should_filter_product("Wilson Basketball for Training", filters):
            # Skip this product
            continue
    """
    product_lower = product_title.lower()
    
    for filter_term in quality_filters:
        filter_lower = filter_term.lower()
        # Check for key words in filter term
        key_words = filter_lower.split()
        if all(word in product_lower for word in key_words):
            return True
    
    return False


# =============================================================================
# LOGGING AND DEBUGGING
# =============================================================================

def log_enrichment_stats():
    """Print statistics about the enrichment database."""
    stats = get_database_stats()
    print("\n" + "="*50)
    print("ENRICHMENT DATABASE STATS")
    print("="*50)
    print(f"Version: {stats['version']}")
    print(f"Last Update: {stats['last_update']}")
    print(f"Total Interests: {stats['total_interests']}")
    print(f"Total Demographics: {stats['total_demographics']}")
    print(f"Total Relationships: {stats['total_relationships']}")
    print(f"Coverage: {stats['coverage']}")
    print("="*50 + "\n")


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == '__main__':
    # Example: Enrich a profile
    print("Testing Enrichment Engine...\n")
    
    enriched = enrich_profile_simple(
        interests=['basketball', 'cooking', 'coffee'],
        relationship='romantic_partner',
        age=28,
        gender='female',
        budget=(60, 120)
    )
    
    # Print summary
    engine = EnrichmentEngine()
    print(engine.get_enrichment_summary(enriched))
    
    # Print search strategy
    print("\nSEARCH STRATEGY:")
    for i, strategy in enumerate(enriched['search_strategy'][:3], 1):
        print(f"\n{i}. {strategy['approach'].upper()}")
        if 'search_terms' in strategy:
            print(f"   Terms: {', '.join(strategy['search_terms'][:3])}")
        if 'focus_categories' in strategy:
            print(f"   Categories: {', '.join(strategy['focus_categories'])}")
    
    # Print quality filters
    print(f"\nQUALITY FILTERS ({len(enriched['quality_filters'])} total):")
    for filter_term in enriched['quality_filters'][:10]:
        print(f"  - {filter_term}")
    
    # Print database stats
    log_enrichment_stats()
