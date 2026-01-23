"""
GIFTWISE CONFIGURATION
Feature flags, pricing tiers, and limits

This file makes it easy to:
- Turn features on/off without code changes
- Adjust pricing/limits without redeployment
- A/B test features with different users
"""

import os

# ============================================================================
# FEATURE FLAGS - Toggle features on/off easily
# ============================================================================

FEATURES = {
    'youtube_integration': os.environ.get('FEATURE_YOUTUBE', 'False') == 'True',
    'friend_network': os.environ.get('FEATURE_FRIENDS', 'False') == 'True',
    'gift_emergency': os.environ.get('FEATURE_GIFT_EMERGENCY', 'True') == 'True',
    'monthly_regeneration': os.environ.get('FEATURE_MONTHLY_REGEN', 'True') == 'True',
}

# ============================================================================
# PRICING TIERS
# ============================================================================

TIERS = {
    'free': {
        'name': 'Free',
        'price': 0,
        'platforms_limit': 2,                    # Only 2 platforms
        'recommendations_limit': 5,               # Only 5 recommendations
        'regeneration_days': None,                # No regeneration (one-time only)
        'shareable_profile': False,               # No public profile
        'friend_network': False,                  # No friend network access
        'match_quality': 'standard',              # Lower accuracy
        'features': [
            'Connect 2 platforms',
            '5 gift recommendations',
            'One-time generation',
            'Basic match accuracy'
        ]
    },
    
    'pro': {
        'name': 'Pro',
        'price': 4.99,
        'platforms_limit': None,                  # Unlimited platforms
        'recommendations_limit': 10,              # Full 10 recommendations
        'regeneration_days': 30,                  # Monthly updates
        'shareable_profile': True,                # Public profile enabled
        'friend_network': True,                   # Friend network access
        'match_quality': 'premium',               # 95% accuracy
        'features': [
            'Connect ALL platforms (Instagram, Spotify, Pinterest, TikTok)',
            '10 ultra-specific recommendations',
            'Monthly automatic updates',
            'Shareable gift profile (giftwise.com/u/you)',
            'Friend network access',
            '95% match accuracy',
            'Priority support'
        ]
    },
    
    'gift_emergency': {
        'name': 'Gift Emergency',
        'price': 2.99,
        'type': 'one_time',
        'platforms_limit': None,                  # Auto-scrape public data
        'recommendations_limit': 10,              # Full 10 recommendations
        'regeneration_days': None,                # One-time only
        'shareable_profile': False,               # No profile
        'friend_network': False,                  # No friend network
        'match_quality': 'standard',
        'features': [
            'Instant recommendations for anyone',
            'Just provide their Instagram username',
            '10 specific gift ideas in 2 minutes',
            'No subscription needed'
        ]
    }
}

# ============================================================================
# PLATFORM PRIORITIES - Which platforms to show first
# ============================================================================

PLATFORM_PRIORITY = ['instagram', 'spotify', 'pinterest', 'tiktok', 'youtube']

# Descriptions shown to users
PLATFORM_DESCRIPTIONS = {
    'instagram': {
        'name': 'Instagram',
        'icon': '📷',
        'description': 'Full access to posts, hashtags, and interests. Shows lifestyle and aesthetic preferences.',
        'quality': 'high',
        'recommended_for_free': True
    },
    'spotify': {
        'name': 'Spotify',
        'icon': '🎵',
        'description': 'Top artists, playlists, and listening history. Perfect for music-related gifts.',
        'quality': 'high',
        'recommended_for_free': True
    },
    'pinterest': {
        'name': 'Pinterest',
        'icon': '📌',
        'description': 'Boards and pins show exactly what they\'re wishing for. Highest-intent data!',
        'quality': 'very_high',
        'recommended_for_free': False  # Save for Pro
    },
    'tiktok': {
        'name': 'TikTok',
        'icon': '🎬',
        'description': 'Current interests and trends. Public profile analysis.',
        'quality': 'medium',
        'recommended_for_free': False  # Save for Pro
    }
}

# ============================================================================
# UPGRADE PROMPTS - Messaging for free users
# ============================================================================

UPGRADE_MESSAGES = {
    'platforms_limit': {
        'title': '🔒 Unlock More Platforms',
        'description': 'Connect Pinterest + TikTok for better recommendations',
        'benefit': '2 platforms = 75% accuracy. 4 platforms = 95% accuracy!',
        'cta': 'Upgrade to Pro'
    },
    
    'recommendations_limit': {
        'title': '🔒 See 5 More Recommendations',
        'description': 'You\'re seeing 5 of 10 recommendations',
        'benefit': 'Pro users get all 10 ultra-specific gift ideas',
        'cta': 'Unlock All 10'
    },
    
    'regeneration': {
        'title': '🔒 Monthly Updates',
        'description': 'Your interests change. Your recommendations should too.',
        'benefit': 'Pro users get fresh recommendations every month automatically',
        'cta': 'Enable Auto-Updates'
    },
    
    'shareable_profile': {
        'title': '🔒 Share Your Gift Profile',
        'description': 'Get a shareable link (giftwise.com/u/you) for friends and family',
        'benefit': 'Let people know exactly what to get you!',
        'cta': 'Unlock Shareable Profile'
    },
    
    'friend_network': {
        'title': '🔒 See Friends\' Recommendations',
        'description': 'View gift ideas for all your friends in one place',
        'benefit': 'Never forget a birthday. Always have the perfect gift ready.',
        'cta': 'Unlock Friend Network'
    }
}

# ============================================================================
# RATE LIMITS - Prevent abuse
# ============================================================================

RATE_LIMITS = {
    'free': {
        'generations_per_day': 1,           # Can only generate once per day
        'generations_per_month': 2          # Total 2 times per month
    },
    'pro': {
        'generations_per_day': 5,           # Can regenerate 5x per day
        'generations_per_month': None       # Unlimited per month
    }
}

# ============================================================================
# STRIPE PRICE IDs (Set these from your Stripe dashboard)
# ============================================================================

STRIPE_PRICES = {
    'pro_monthly': os.environ.get('STRIPE_PRICE_PRO_MONTHLY'),
    'gift_emergency': os.environ.get('STRIPE_PRICE_GIFT_EMERGENCY')
}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_user_tier(user):
    """
    Determine user's tier based on their subscription status
    
    Args:
        user: User dict from database
        
    Returns:
        str: 'free' or 'pro'
    """
    if user.get('stripe_subscription_id') or user.get('stripe_subscription_status') == 'active':
        return 'pro'
    return 'free'


def get_tier_config(tier_name):
    """
    Get configuration for a specific tier
    
    Args:
        tier_name: 'free', 'pro', or 'gift_emergency'
        
    Returns:
        dict: Tier configuration
    """
    return TIERS.get(tier_name, TIERS['free'])


def can_connect_platform(user, platform_count):
    """
    Check if user can connect another platform
    
    Args:
        user: User dict
        platform_count: Current number of connected platforms
        
    Returns:
        bool: True if can connect, False otherwise
    """
    tier = get_user_tier(user)
    limit = TIERS[tier]['platforms_limit']
    
    if limit is None:  # Unlimited
        return True
    
    return platform_count < limit


def can_regenerate(user):
    """
    Check if user can regenerate recommendations
    
    Args:
        user: User dict
        
    Returns:
        tuple: (bool, str) - (can_regenerate, reason_if_not)
    """
    tier = get_user_tier(user)
    tier_config = TIERS[tier]
    
    # Check if regeneration is allowed for this tier
    if tier_config['regeneration_days'] is None:
        return False, "Upgrade to Pro for monthly regeneration"
    
    # Check last generation time
    from datetime import datetime, timedelta
    
    last_generated = user.get('last_generated')
    if not last_generated:
        return True, None
    
    last_gen_date = datetime.fromisoformat(last_generated)
    days_since = (datetime.now() - last_gen_date).days
    
    if days_since >= tier_config['regeneration_days']:
        return True, None
    
    days_remaining = tier_config['regeneration_days'] - days_since
    return False, f"Next regeneration in {days_remaining} days"


def get_platform_limit_message(user):
    """
    Get message to show when user hits platform limit
    
    Args:
        user: User dict
        
    Returns:
        dict: Message configuration
    """
    tier = get_user_tier(user)
    
    if tier == 'free':
        return {
            'title': 'Platform Limit Reached',
            'message': 'Free users can connect 2 platforms. Upgrade to Pro for unlimited platforms.',
            'upgrade_benefit': '4 platforms = 95% match accuracy vs 75% with 2 platforms',
            'cta': 'Upgrade to Pro - $4.99/month'
        }
    
    return None
