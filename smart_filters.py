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
    def is_work_related_gift(product_title, product_description, user_interests):
        """
        Determine if a product is something they'd get through work
        
        Args:
            product_title: Gift product title
            product_description: Product description/snippet
            user_interests: List of interest dicts with 'name', 'is_work', 'description'
        
        Returns:
            {
                'is_work_item': bool,
                'reason': str,  # Why it was flagged
                'confidence': float  # 0-1 how sure we are
            }
        """
        
        combined_text = f"{product_title} {product_description}".lower()
        
        # Check for professional keywords
        for keyword in WorkExclusionFilter.PROFESSIONAL_KEYWORDS:
            if keyword in combined_text:
                return {
                    'is_work_item': True,
                    'reason': f"Contains professional keyword: '{keyword}'",
                    'confidence': 0.8
                }
        
        # Check against work-related interests
        for interest in user_interests:
            if not interest.get('is_work'):
                continue
            
            interest_name = interest.get('name', '').lower()
            interest_desc = interest.get('description', '').lower()
            
            # If product mentions their work interest, it's probably work-related
            if interest_name in combined_text:
                # BUT: Check if it's a collectible or fan item
                fan_indicators = ['poster', 'collectible', 'memorabilia', 'signed', 
                                 'replica', 'vintage', 'art', 'print', 'book about']
                
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
    def filter_products(products, user_interests):
        """
        Remove work-related items from product list
        
        Args:
            products: List of product dicts
            user_interests: List of interest dicts
        
        Returns:
            Filtered product list with work items removed
        """
        
        filtered = []
        removed_count = 0
        
        for product in products:
            result = WorkExclusionFilter.is_work_related_gift(
                product.get('title', ''),
                product.get('snippet', ''),
                user_interests
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


def apply_smart_filters(products, profile):
    """
    Apply all smart filters to remove inappropriate gifts
    
    Args:
        products: List of product dicts
        profile: User profile with interests
    
    Returns:
        Filtered product list
    """
    
    interests = profile.get('interests', [])
    
    # Step 1: Remove work-related items
    products = WorkExclusionFilter.filter_products(products, interests)
    
    # Step 2: Filter by activity type (passive vs active)
    products = PassiveActiveFilter.filter_by_activity_type(products, interests)
    
    logger.info(f"Smart filters complete: {len(products)} products remaining")
    
    return products
