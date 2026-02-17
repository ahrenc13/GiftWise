"""
Centralized configuration management
All environment variables are loaded and validated here
"""

import os

from .settings import Settings, get_settings

# ---------------------------------------------------------------------------
# Legacy compatibility: old code does `import config; config.FEATURES`
# The config/ package shadows config.py, so we must re-export these here.
# ---------------------------------------------------------------------------

FEATURES = {
    # User-facing features
    'youtube_integration': os.environ.get('FEATURE_YOUTUBE', 'False') == 'True',
    'friend_network': os.environ.get('FEATURE_FRIENDS', 'False') == 'True',
    'gift_emergency': os.environ.get('FEATURE_GIFT_EMERGENCY', 'True') == 'True',
    'monthly_regeneration': os.environ.get('FEATURE_MONTHLY_REGEN', 'True') == 'True',

    # Infrastructure features
    'profile_caching': os.environ.get('FEATURE_PROFILE_CACHE', 'True') == 'True',
    'database_first': os.environ.get('FEATURE_DB_FIRST', 'True') == 'True',
    'relationship_rules': False,
    'admin_dashboard': os.environ.get('FEATURE_ADMIN', 'True') == 'True',
    'gift_guides': os.environ.get('FEATURE_GUIDES', 'True') == 'True',
}

PROFILE_CACHE_TTL_DAYS = 7  # How long to cache analyzed profiles (days)

__all__ = ['Settings', 'get_settings', 'FEATURES', 'PROFILE_CACHE_TTL_DAYS']
