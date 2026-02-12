"""
GIFTWISE CONFIGURATION
Centralized constants for the entire application

This file makes it easy to:
- Turn features on/off without code changes
- Adjust pricing/limits without redeployment
- A/B test features with different users
- Manage API credentials and database settings
- Configure retailer priorities and rate limits

Author: Chad + Claude
Date: February 2026
"""

import os

# =============================================================================
# ENVIRONMENT & DEPLOYMENT
# =============================================================================

ENV = os.environ.get('ENV', 'development')
DEBUG = ENV == 'development'
SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# =============================================================================
# DATABASE
# =============================================================================

DB_PATH = os.environ.get('DATABASE_PATH', '/home/user/GiftWise/data/products.db')

# Database refresh configuration
REFRESH_CONFIG = {
    'schedule': 'daily',  # How often to refresh (daily, weekly)
    'time': '02:00',      # UTC time to run refresh (2am UTC)
    'stale_threshold_days': 7,  # Mark products stale if not seen in X days
    'batch_size': 100,    # Products to process per batch
    'max_products_per_retailer': 500,  # Cap to prevent runaway storage
}

# Profile cache settings
PROFILE_CACHE_TTL_DAYS = 7  # How long to cache analyzed profiles

# =============================================================================
# AFFILIATE API CREDENTIALS
# =============================================================================

# Amazon (RapidAPI)
RAPIDAPI_KEY = os.environ.get('RAPIDAPI_KEY', '')
RAPIDAPI_HOST = os.environ.get('RAPIDAPI_HOST', 'real-time-amazon-data.p.rapidapi.com')

# eBay
EBAY_APP_ID = os.environ.get('EBAY_APP_ID', '')
EBAY_CAMPAIGN_ID = os.environ.get('EBAY_CAMPAIGN_ID', '5339236479')

# Etsy
ETSY_API_KEY = os.environ.get('ETSY_API_KEY', '')

# Awin
AWIN_API_TOKEN = os.environ.get('AWIN_API_TOKEN', '')
AWIN_PUBLISHER_ID = os.environ.get('AWIN_PUBLISHER_ID', '')

# Skimlinks
SKIMLINKS_PUBLISHER_ID = os.environ.get('SKIMLINKS_PUBLISHER_ID', '')
SKIMLINKS_CLIENT_ID = os.environ.get('SKIMLINKS_CLIENT_ID', '')
SKIMLINKS_CLIENT_SECRET = os.environ.get('SKIMLINKS_CLIENT_SECRET', '')
SKIMLINKS_PUBLISHER_DOMAIN_ID = os.environ.get('SKIMLINKS_PUBLISHER_DOMAIN_ID', '')

# CJ Affiliate
CJ_ACCOUNT_ID = os.environ.get('CJ_ACCOUNT_ID', '')
CJ_API_KEY = os.environ.get('CJ_API_KEY', '')
CJ_WEBSITE_ID = os.environ.get('CJ_WEBSITE_ID', '')  # PID from CJAM

# ShareASale (legacy - migrated to Awin)
SHAREASALE_TOKEN = os.environ.get('SHAREASALE_TOKEN', '')
SHAREASALE_SECRET = os.environ.get('SHAREASALE_SECRET', '')
SHAREASALE_AFFILIATE_ID = os.environ.get('SHAREASALE_AFFILIATE_ID', '')

# =============================================================================
# CLAUDE API
# =============================================================================

ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')

# Model selection
CLAUDE_MODEL_PROFILE_ANALYSIS = os.environ.get('CLAUDE_MODEL_PROFILE', 'claude-3-5-sonnet-20241022')
CLAUDE_MODEL_GIFT_CURATION = os.environ.get('CLAUDE_MODEL_CURATOR', 'claude-3-5-sonnet-20241022')

# Cost tracking (approximate, update as pricing changes)
CLAUDE_COST_PER_1M_INPUT_TOKENS = 3.00  # USD
CLAUDE_COST_PER_1M_OUTPUT_TOKENS = 15.00  # USD

# =============================================================================
# SOCIAL MEDIA CREDENTIALS
# =============================================================================

# Instagram
INSTAGRAM_APP_ID = os.environ.get('INSTAGRAM_APP_ID', '')
INSTAGRAM_APP_SECRET = os.environ.get('INSTAGRAM_APP_SECRET', '')
INSTAGRAM_REDIRECT_URI = os.environ.get('INSTAGRAM_REDIRECT_URI', 'https://giftwise.fit/connect/instagram/callback')

# TikTok
TIKTOK_CLIENT_KEY = os.environ.get('TIKTOK_CLIENT_KEY', '')
TIKTOK_CLIENT_SECRET = os.environ.get('TIKTOK_CLIENT_SECRET', '')
TIKTOK_REDIRECT_URI = os.environ.get('TIKTOK_REDIRECT_URI', 'https://giftwise.fit/connect/tiktok/callback')

# Spotify (limited by Development Mode restrictions as of Feb 2026)
SPOTIFY_CLIENT_ID = os.environ.get('SPOTIFY_CLIENT_ID', '')
SPOTIFY_CLIENT_SECRET = os.environ.get('SPOTIFY_CLIENT_SECRET', '')
SPOTIFY_REDIRECT_URI = os.environ.get('SPOTIFY_REDIRECT_URI', 'https://giftwise.fit/connect/spotify/callback')

# Pinterest
PINTEREST_APP_ID = os.environ.get('PINTEREST_APP_ID', '')
PINTEREST_APP_SECRET = os.environ.get('PINTEREST_APP_SECRET', '')
PINTEREST_REDIRECT_URI = os.environ.get('PINTEREST_REDIRECT_URI', 'https://giftwise.fit/connect/pinterest/callback')

# =============================================================================
# PRODUCT SEARCH SETTINGS
# =============================================================================

# Default search configuration
DEFAULT_PRODUCTS_PER_RETAILER = 20
MAX_TOTAL_INVENTORY_POOL = 200  # Before curator sees it
FINAL_RECOMMENDATION_COUNT = 10  # After curation + cleanup

# Retailer priority (higher = shown first in equal-scoring scenarios)
RETAILER_PRIORITY = {
    'etsy': 1,          # Highest commission, unique items
    'awin': 2,          # Multiple brands, good commission
    'ebay': 3,          # Broad inventory
    'shareasale': 4,    # Legacy, being phased out
    'skimlinks': 5,     # Broad but lower commission due to revenue share
    'cj': 6,            # Pending activation
    'amazon': 10,       # Fallback - lowest commission
}

# Search terms per interest (enrichment engine generates these)
SEARCH_TERMS_PER_INTEREST = 3

# Price range defaults (USD)
DEFAULT_MIN_PRICE = 10.00
DEFAULT_MAX_PRICE = 200.00

# =============================================================================
# IMAGE HANDLING
# =============================================================================

# Image validation
MIN_IMAGE_WIDTH = 100
MIN_IMAGE_HEIGHT = 100
IMAGE_TIMEOUT_SECONDS = 5

# Placeholder images
PLACEHOLDER_IMAGE_URL = '/static/images/gift-placeholder.png'

# =============================================================================
# RELATIONSHIP & FILTERING
# =============================================================================

# Relationship types
RELATIONSHIP_TYPES = [
    'parent', 'sibling', 'partner', 'best_friend',
    'friend', 'extended_family', 'coworker', 'acquaintance'
]

# Work-exclusion keywords (used by smart_filters.py)
WORK_EXCLUSION_KEYWORDS = [
    'planner', 'organizer', 'notebook', 'desk', 'office',
    'productivity', 'workspace', 'calendar', 'journal'
]

# =============================================================================
# LOGGING
# =============================================================================

LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# =============================================================================
# ANALYTICS TARGETS (Future)
# =============================================================================

# Target metrics (not yet implemented)
TARGET_AFFILIATE_CTR = 0.25  # 25% of displayed products clicked
TARGET_SOURCE_DIVERSITY = 0.40  # 40% non-Amazon
TARGET_THUMBNAIL_SUCCESS = 0.85  # 85% real images
TARGET_SESSION_COST = 0.15  # Max $0.15 per recommendation session

# ============================================================================
# FEATURE FLAGS - Toggle features on/off easily
# ============================================================================

FEATURES = {
    # User-facing features
    'youtube_integration': os.environ.get('FEATURE_YOUTUBE', 'False') == 'True',
    'friend_network': os.environ.get('FEATURE_FRIENDS', 'False') == 'True',
    'gift_emergency': os.environ.get('FEATURE_GIFT_EMERGENCY', 'True') == 'True',
    'monthly_regeneration': os.environ.get('FEATURE_MONTHLY_REGEN', 'True') == 'True',

    # Infrastructure features
    'profile_caching': os.environ.get('FEATURE_PROFILE_CACHE', 'True') == 'True',
    'database_first': os.environ.get('FEATURE_DB_FIRST', 'True') == 'True',
    'relationship_rules': False,  # Disabled as hard filter, used as soft guidance
    'admin_dashboard': os.environ.get('FEATURE_ADMIN', 'True') == 'True',
    'gift_guides': os.environ.get('FEATURE_GUIDES', 'True') == 'True',
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
# USER RATE LIMITS - Prevent abuse
# ============================================================================

USER_RATE_LIMITS = {
    'free': {
        'generations_per_day': 1,           # Can only generate once per day
        'generations_per_month': 2          # Total 2 times per month
    },
    'pro': {
        'generations_per_day': 5,           # Can regenerate 5x per day
        'generations_per_month': None       # Unlimited per month
    }
}

# API RATE LIMITS - Retailer API limits (requests per hour)
API_RATE_LIMITS = {
    'amazon': 100,      # RapidAPI tier limit
    'ebay': 5000,       # eBay Browse API default
    'etsy': 100,        # Etsy v3 API default (verify on approval)
    'awin': 60,         # Conservative estimate (1 req/min)
    'skimlinks': 100,   # Verify in publisher portal
    'cj': 100,          # Verify in developer portal
    'shareasale': 60,   # Legacy
}

# ============================================================================
# STRIPE PRICE IDs (Set these from your Stripe dashboard)
# ============================================================================

STRIPE_PRICES = {
    'pro_monthly': os.environ.get('STRIPE_PRICE_PRO_MONTHLY'),
    'gift_emergency': os.environ.get('STRIPE_PRICE_GIFT_EMERGENCY')
}

# ============================================================================
# VALIDATION
# ============================================================================

def validate_config():
    """
    Validate critical configuration on startup.
    Logs warnings for missing credentials but doesn't block app startup.
    """
    import logging
    logger = logging.getLogger(__name__)

    # Critical for core functionality
    if not ANTHROPIC_API_KEY:
        logger.error("ANTHROPIC_API_KEY not set - app will not function")
        return False

    # Warnings for missing retailer credentials
    if not RAPIDAPI_KEY:
        logger.warning("RAPIDAPI_KEY not set - Amazon search disabled")

    if not EBAY_APP_ID:
        logger.warning("EBAY_APP_ID not set - eBay search disabled")

    if not ETSY_API_KEY:
        logger.warning("ETSY_API_KEY not set - Etsy search disabled")

    if not AWIN_API_TOKEN or not AWIN_PUBLISHER_ID:
        logger.warning("Awin credentials incomplete - Awin search disabled")

    if not SKIMLINKS_PUBLISHER_ID:
        logger.warning("Skimlinks credentials missing - awaiting approval")

    if not CJ_API_KEY:
        logger.warning("CJ credentials missing - awaiting developer portal access")

    logger.info("Configuration validation complete")
    return True


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


# =============================================================================
# COMMAND LINE TESTING
# =============================================================================

if __name__ == "__main__":
    print("GiftWise Configuration")
    print("=" * 50)
    print(f"Environment: {ENV}")
    print(f"Debug mode: {DEBUG}")
    print(f"Database path: {DB_PATH}")
    print()
    print("Affiliate Credential Status:")
    print(f"  Claude API: {'✓ Set' if ANTHROPIC_API_KEY else '✗ Missing'}")
    print(f"  Amazon (RapidAPI): {'✓ Set' if RAPIDAPI_KEY else '✗ Missing'}")
    print(f"  eBay: {'✓ Set' if EBAY_APP_ID else '✗ Missing'}")
    print(f"  Etsy: {'✓ Set' if ETSY_API_KEY else '✗ Missing'}")
    print(f"  Awin: {'✓ Set' if AWIN_API_TOKEN and AWIN_PUBLISHER_ID else '✗ Missing'}")
    print(f"  Skimlinks: {'✓ Set' if SKIMLINKS_PUBLISHER_ID else '✗ Missing'}")
    print(f"  CJ: {'✓ Set' if CJ_API_KEY else '✗ Missing'}")
    print()
    print("Feature Flags:")
    for feature, enabled in FEATURES.items():
        status = '✓ Enabled' if enabled else '✗ Disabled'
        print(f"  {feature}: {status}")
    print()
    validate_config()
