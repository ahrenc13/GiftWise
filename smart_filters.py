"""
WORK EXCLUSION FILTER - Don't suggest gifts someone gets through their job
Prevents suggesting EMS tools to paramedics, Indy 500 tickets to event staff, etc.

Author: Chad + Claude
Date: February 2026
"""

import logging
import re

logger = logging.getLogger(__name__)


class WorkExclusionFilter:
    """Filter out gift suggestions that are obviously work-related"""
    
    # Keywords that indicate professional/work items
    PROFESSIONAL_KEYWORDS = [
        'professional development', 'certification', 'training course',
        'industry conference', 'trade show', 'workshop', 'seminar',
        'safety equipment', 'safety tools', 'safety awareness',
        'work uniform', 'protective gear', 'industry tools',
        'professional membership', 'license', 'credential',
        'continuing education', 'ceu', 'ce credits'
    ]
    
    @staticmethod
    def is_work_related_gift(product_title, product_description, user_interests, user_profile=None):
        """
        Determine if a product is something they'd get through work
        
        Args:
            product_title: Gift product title
            product_description: Product description/snippet
            user_interests: List of interest dicts with 'name', 'is_work', 'description' or 'evidence'
            user_profile: Full profile with location, job details, etc.
        
        Returns:
            {
                'is_work_item': True,
                'reason': f"Contains professional keyword: '{keyword}'",
                'confidence': 0.8
            }
    
    # Extract work location/venue from profile if available
    work_venues = []
    work_companies = []
    
    if user_profile:
        # Check location context for work venues
        location_context = user_profile.get('location_context', {})
        city = (location_context or {}).get('city_region', '').lower()
        # Look for work-specific locations in interests
        for interest in user_interests:
            if not interest.get('is_work'):
                continue
            
            desc = interest.get('description', '').lower()
            
            # Extract venue/location mentions
                # "Works at Indianapolis Motor Speedway" → ["indianapolis motor speedway", "indy 500"]
                if 'works at' in desc or 'work at' in desc:
                    # Extract what comes after "works at"
                    import re
                    venue_match = re.search(r'works? (?:at|for) ([a-z0-9\s]+?)(?:\.|,|;|$)', desc)
                    if venue_match:
                        venue = venue_match.group(1).strip()
                        work_venues.append(venue)
                        
                        # Add common abbreviations
                        if 'motor speedway' in venue or 'indy 500' in desc:
                            work_venues.extend(['indy 500', 'indianapolis 500', 'motor speedway', 'race track'])
                        if 'concert venue' in venue or 'arena' in venue:
                            work_venues.extend(['backstage', 'vip access', 'behind the scenes'])
        
        # Check if gift is an experience at their workplace
        workplace_indicators = [
            'tour', 'behind the scenes', 'backstage', 'vip access', 'access to',
            'experience at', 'visit to', 'tickets to'
        ]
        
        for venue in work_venues:
            if venue in combined_text:
                # Check if it's a workplace experience (tour, access, etc.)
                if any(indicator in combined_text for indicator in workplace_indicators):
                    return {
                        'is_work_item': True,
                        'reason': f"Experience at their workplace: {venue}",
                        'confidence': 0.95
                    }
        
        # Check against work-related interests (original logic)
        for interest in user_interests:
            if not interest.get('is_work'):
                continue
            
            interest_name = interest.get('name', '').lower()
            interest_desc = (interest.get('description') or interest.get('evidence', '')).lower()
            
            # If product mentions their work interest, it's probably work-related
            if interest_name in combined_text:
                # BUT: Check if it's a collectible or fan item
                fan_indicators = ['poster', 'collectible', 'memorabilia', 'signed', 
                                 'replica', 'vintage', 'art', 'print', 'book about',
                                 'history of', 'documentary', 'biography']
                
                if any(indicator in combined_text for indicator in fan_indicators):
                    # This is a FAN item about their work, not a work tool
                    return {
                        'is_work_item': False,
                        'reason': f"Fan/collectible item related to {interest_name}",
                        'confidence': 0.9
                    }
                else:
                    # Direct work-related item
                    return {
                        'is_work_item': True,
                        'reason': f"Directly related to work interest: {interest_name}",
                        'confidence': 0.9
                    }
        
        # Not work-related
        return {
            'is_work_item': False,
            'reason': 'No work indicators found',
            'confidence': 0.7
        }
    
    @staticmethod
    def filter_products(products, user_profile):
        """
        Remove work-related items from product list
        
        Args:
            products: List of product dicts
            user_profile: Full profile dict with interests, location, etc.
        
        Returns:
            Filtered product list with work items removed
        """
        
        user_interests = user_profile.get('interests', [])
        filtered = []
        removed_count = 0
        
        for product in products:
            result = WorkExclusionFilter.is_work_related_gift(
                product.get('title', ''),
                product.get('snippet', ''),
                user_interests,
                user_profile  # Pass full profile for venue detection
            )
            
            if result['is_work_item']:
                logger.info(f"EXCLUDED work item: {product['title'][:60]} - {result['reason']}")
                removed_count += 1
            else:
                filtered.append(product)
        
        logger.info(f"Work filter removed {removed_count} items, kept {len(filtered)}")
        
        return filtered


class PassiveActiveFilter:
    """Distinguish between passive enjoyment (watching) and active participation (playing)"""
    
    @staticmethod
    def requires_active_participation(product_title, product_description):
        """
        Check if a product requires active participation
        
        Returns:
            {
                'requires_active': bool,
                'activity_type': 'playing' | 'practicing' | 'building' | 'passive',
                'confidence': float
            }
        """
        
        combined_text = f"{product_title} {product_description}".lower()
        
        # Active participation indicators
        active_indicators = {
            'playing': ['basketball hoop', 'soccer ball', 'tennis racket', 'golf clubs', 
                       'baseball bat', 'hockey stick', 'play with'],
            'practicing': ['training equipment', 'practice net', 'workout', 'exercise',
                          'fitness', 'drill', 'lesson'],
            'building': ['lego', 'model kit', 'build your own', 'diy', 'craft kit',
                        'construction', 'assembly required']
        }
        
        for activity_type, indicators in active_indicators.items():
            for indicator in indicators:
                if indicator in combined_text:
                    return {
                        'requires_active': True,
                        'activity_type': activity_type,
                        'confidence': 0.8,
                        'reason': f"Contains '{indicator}'"
                    }
        
        # Passive enjoyment indicators
        passive_indicators = ['watch', 'poster', 'book', 'documentary', 'biography',
                             'history of', 'art print', 'collectible', 'memorabilia',
                             'signed photo', 'card collection', 'magazine subscription']
        
        for indicator in passive_indicators:
            if indicator in combined_text:
                return {
                    'requires_active': False,
                    'activity_type': 'passive',
                    'confidence': 0.7,
                    'reason': f"Contains '{indicator}'"
                }
        
        # Default: assume passive
        return {
            'requires_active': False,
            'activity_type': 'passive',
            'confidence': 0.5,
            'reason': 'No clear activity indicators'
        }
    
    @staticmethod
    def filter_by_activity_type(products, user_interests):
        """
        Filter products based on whether user actively participates or passively enjoys
        
        Args:
            products: List of product dicts
            user_interests: List of interest dicts with 'activity_type' field
        
        Returns:
            Filtered product list
        """
        
        filtered = []
        removed_count = 0
        
        for product in products:
            # Get the interest this product matches
            interest_match = product.get('interest_match', '')
            
            # Find the corresponding user interest
            matching_interest = None
            for interest in user_interests:
                if interest.get('name', '').lower() == interest_match.lower():
                    matching_interest = interest
                    break
            
            if not matching_interest:
                # No matching interest found, keep the product
                filtered.append(product)
                continue
            
            # Check if product requires active participation
            product_activity = PassiveActiveFilter.requires_active_participation(
                product.get('title', ''),
                product.get('snippet', '')
            )
            
            user_is_passive = matching_interest.get('activity_type') == 'passive'
            
            # If user is passive but product requires active participation, exclude
            if user_is_passive and product_activity['requires_active']:
                logger.info(f"EXCLUDED active item for passive interest: {product['title'][:60]}")
                removed_count += 1
            else:
                filtered.append(product)
        
        logger.info(f"Activity filter removed {removed_count} items, kept {len(filtered)}")
        
        return filtered


def get_work_venue_phrases(profile):
    """Return list of phrases that indicate a workplace (for filtering experience gifts)."""
    import re
    phrases = []
    interests = profile.get('interests', [])
    for i in interests:
        if not i.get('is_work'):
            continue
        desc = (i.get('description') or i.get('evidence', '')).lower()
        name = i.get('name', '').lower()
        if 'works at' in desc or 'work at' in desc:
            m = re.search(r'works? (?:at|for) ([a-z0-9\s]+?)(?:\.|,|;|$)', desc)
            if m:
                v = m.group(1).strip()
                phrases.append(v)
                if 'motor speedway' in v or 'speedway' in v or 'ims' in desc:
                    phrases.extend(['ims', 'indianapolis motor speedway', 'indy 500', 'indianapolis 500'])
        if name:
            phrases.append(name)
    return list(set(phrases))


def filter_workplace_experiences(experience_gifts, profile):
    """Remove experience gifts that are at the recipient's workplace (e.g. behind-the-scenes IMS when they work at IMS)."""
    work_phrases = get_work_venue_phrases(profile)
    if not work_phrases:
        return experience_gifts
    workplace_indicators = ['behind the scenes', 'backstage', 'vip access', 'tour', 'experience at']
    filtered = []
    for exp in experience_gifts:
        combined = f"{exp.get('name', '')} {exp.get('location_details', '')} {exp.get('description', '')}".lower()
        is_workplace = False
        for phrase in work_phrases:
            if phrase.lower() in combined and any(ind in combined for ind in workplace_indicators):
                is_workplace = True
                logger.info(f"EXCLUDED workplace experience: {exp.get('name', '')[:60]} - matches work venue '{phrase}'")
                break
        if not is_workplace:
            filtered.append(exp)
    return filtered


def apply_smart_filters(products, profile):
    """
    Apply all smart filters to remove inappropriate gifts
    
    Args:
        products: List of product dicts
        profile: User profile with interests, location, work details
    
    Returns:
        Filtered product list
    """
    
    # Step 1: Remove work-related items (pass full profile for venue detection)
    products = WorkExclusionFilter.filter_products(products, profile)
    
    # Step 2: Filter by activity type (passive vs active)
    interests = profile.get('interests', [])
    products = PassiveActiveFilter.filter_by_activity_type(products, interests)
    
    logger.info(f"Smart filters complete: {len(products)} products remaining")
    
    return products
