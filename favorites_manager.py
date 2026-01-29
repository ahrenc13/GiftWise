"""
FAVORITES MANAGER
Save and manage favorite gift recommendations
"""

import json
import logging

logger = logging.getLogger('giftwise')

def add_favorite(user, recommendation_id):
    """
    Add a recommendation to favorites
    
    Args:
        user: User dict
        recommendation_id: ID or index of recommendation
    
    Returns:
        Updated user dict
    """
    favorites = user.get('favorites', [])
    
    if recommendation_id not in favorites:
        favorites.append(recommendation_id)
        user['favorites'] = favorites
        logger.info(f"Added favorite: {recommendation_id}")
    
    return user

def remove_favorite(user, recommendation_id):
    """
    Remove a recommendation from favorites
    
    Args:
        user: User dict
        recommendation_id: ID or index of recommendation
    
    Returns:
        Updated user dict
    """
    favorites = user.get('favorites', [])
    
    if recommendation_id in favorites:
        favorites.remove(recommendation_id)
        user['favorites'] = favorites
        logger.info(f"Removed favorite: {recommendation_id}")
    
    return user

def is_favorite(user, recommendation_id):
    """
    Check if recommendation is favorited
    
    Args:
        user: User dict
        recommendation_id: ID or index of recommendation
    
    Returns:
        True if favorited, False otherwise
    """
    favorites = user.get('favorites', [])
    return recommendation_id in favorites

def get_favorites(user, recommendations):
    """
    Get favorited recommendations
    
    Args:
        user: User dict
        recommendations: List of all recommendations
    
    Returns:
        List of favorited recommendations
    """
    favorites = user.get('favorites', [])
    return [rec for idx, rec in enumerate(recommendations) if idx in favorites]
