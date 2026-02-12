"""
Application settings - centralized configuration from environment variables
Validates and provides type-safe access to all config
"""

import os
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger('giftwise')


@dataclass
class APISettings:
    """External API credentials"""
    # Core APIs
    anthropic_api_key: str = field(default_factory=lambda: os.environ.get('ANTHROPIC_API_KEY', ''))
    apify_api_token: str = field(default_factory=lambda: os.environ.get('APIFY_API_TOKEN', ''))
    serpapi_api_key: str = field(default_factory=lambda: os.environ.get('SERPAPI_API_KEY', ''))
    unsplash_access_key: str = field(default_factory=lambda: os.environ.get('UNSPLASH_ACCESS_KEY', ''))

    # Google APIs
    google_cse_api_key: str = field(default_factory=lambda: os.environ.get('GOOGLE_CSE_API_KEY', ''))
    google_custom_search_engine_id: str = field(default_factory=lambda: os.environ.get('GOOGLE_CUSTOM_SEARCH_ENGINE_ID', ''))
    google_youtube_api_key: str = field(default_factory=lambda: os.environ.get('GOOGLE_YOUTUBE_API_KEY', ''))

    # Stripe
    stripe_secret_key: str = field(default_factory=lambda: os.environ.get('STRIPE_SECRET_KEY', ''))
    stripe_price_id: str = field(default_factory=lambda: os.environ.get('STRIPE_PRICE_ID', ''))
    stripe_pro_price_id: str = field(default_factory=lambda: os.environ.get('STRIPE_PRO_PRICE_ID', ''))
    stripe_pro_annual_price_id: str = field(default_factory=lambda: os.environ.get('STRIPE_PRO_ANNUAL_PRICE_ID', ''))
    stripe_premium_price_id: str = field(default_factory=lambda: os.environ.get('STRIPE_PREMIUM_PRICE_ID', ''))


@dataclass
class RetailerAPISettings:
    """Retailer/affiliate network API credentials"""
    # Etsy
    etsy_api_key: str = field(default_factory=lambda: os.environ.get('ETSY_API_KEY', ''))
    etsy_client_id: str = field(default_factory=lambda: os.environ.get('ETSY_CLIENT_ID', ''))
    etsy_client_secret: str = field(default_factory=lambda: os.environ.get('ETSY_CLIENT_SECRET', ''))
    etsy_redirect_uri: str = field(default_factory=lambda: os.environ.get('ETSY_REDIRECT_URI', 'http://localhost:5000/oauth/etsy/callback'))

    # Awin
    awin_data_feed_api_key: str = field(default_factory=lambda: os.environ.get('AWIN_DATA_FEED_API_KEY', ''))

    # eBay
    ebay_client_id: str = field(default_factory=lambda: os.environ.get('EBAY_CLIENT_ID', ''))
    ebay_client_secret: str = field(default_factory=lambda: os.environ.get('EBAY_CLIENT_SECRET', ''))

    # ShareASale
    shareasale_affiliate_id: str = field(default_factory=lambda: os.environ.get('SHAREASALE_AFFILIATE_ID', ''))
    shareasale_api_token: str = field(default_factory=lambda: os.environ.get('SHAREASALE_API_TOKEN', ''))
    shareasale_api_secret: str = field(default_factory=lambda: os.environ.get('SHAREASALE_API_SECRET', ''))

    # Skimlinks
    skimlinks_publisher_id: str = field(default_factory=lambda: os.environ.get('SKIMLINKS_PUBLISHER_ID', ''))
    skimlinks_client_id: str = field(default_factory=lambda: os.environ.get('SKIMLINKS_CLIENT_ID', ''))
    skimlinks_client_secret: str = field(default_factory=lambda: os.environ.get('SKIMLINKS_CLIENT_SECRET', ''))
    skimlinks_domain_id: str = field(default_factory=lambda: os.environ.get('SKIMLINKS_PUBLISHER_DOMAIN_ID', ''))

    # Amazon (RapidAPI)
    rapidapi_key: str = field(default_factory=lambda: os.environ.get('RAPIDAPI_KEY', ''))
    amazon_affiliate_tag: str = field(default_factory=lambda: os.environ.get('AMAZON_AFFILIATE_TAG', ''))


@dataclass
class OAuthSettings:
    """OAuth provider credentials"""
    # Pinterest
    pinterest_client_id: str = field(default_factory=lambda: os.environ.get('PINTEREST_CLIENT_ID', ''))
    pinterest_client_secret: str = field(default_factory=lambda: os.environ.get('PINTEREST_CLIENT_SECRET', ''))
    pinterest_redirect_uri: str = field(default_factory=lambda: os.environ.get('PINTEREST_REDIRECT_URI', 'http://localhost:5000/oauth/pinterest/callback'))

    # Spotify
    spotify_client_id: str = field(default_factory=lambda: os.environ.get('SPOTIFY_CLIENT_ID', ''))
    spotify_client_secret: str = field(default_factory=lambda: os.environ.get('SPOTIFY_CLIENT_SECRET', ''))
    spotify_redirect_uri: str = field(default_factory=lambda: os.environ.get('SPOTIFY_REDIRECT_URI', 'http://localhost:5000/oauth/spotify/callback'))

    # Google
    google_client_id: str = field(default_factory=lambda: os.environ.get('GOOGLE_CLIENT_ID', ''))
    google_client_secret: str = field(default_factory=lambda: os.environ.get('GOOGLE_CLIENT_SECRET', ''))
    google_redirect_uri: str = field(default_factory=lambda: os.environ.get('GOOGLE_REDIRECT_URI', 'http://localhost:5000/oauth/google/callback'))


@dataclass
class ClaudeSettings:
    """Claude model configuration for A/B testing"""
    profile_model: str = field(default_factory=lambda: os.environ.get('CLAUDE_PROFILE_MODEL', 'claude-sonnet-4-20250514'))
    curator_model: str = field(default_factory=lambda: os.environ.get('CLAUDE_CURATOR_MODEL', 'claude-sonnet-4-20250514'))

    def __post_init__(self):
        """Log which models are configured"""
        logger.info(f"Claude models — profile: {self.profile_model}, curator: {self.curator_model}")


@dataclass
class AppSettings:
    """Core application settings"""
    # Flask
    secret_key: str = field(default_factory=lambda: os.environ.get('SECRET_KEY', ''))
    port: int = field(default_factory=lambda: int(os.environ.get('PORT', '5000')))
    debug: bool = field(default_factory=lambda: os.environ.get('FLASK_DEBUG', 'False').lower() == 'true')

    # Admin
    admin_dashboard_key: str = field(default_factory=lambda: os.environ.get('ADMIN_DASHBOARD_KEY', ''))

    # Performance
    max_concurrent_scrapers: int = field(default_factory=lambda: int(os.environ.get('MAX_CONCURRENT_SCRAPERS', '8')))

    def __post_init__(self):
        """Validate required settings"""
        if not self.secret_key:
            logger.warning("SECRET_KEY not set - sessions will not persist across restarts")


@dataclass
class Settings:
    """
    Master settings container
    Centralized configuration for the entire application
    """
    app: AppSettings = field(default_factory=AppSettings)
    api: APISettings = field(default_factory=APISettings)
    retailers: RetailerAPISettings = field(default_factory=RetailerAPISettings)
    oauth: OAuthSettings = field(default_factory=OAuthSettings)
    claude: ClaudeSettings = field(default_factory=ClaudeSettings)

    def validate_critical(self) -> list[str]:
        """
        Validate critical settings required for app to function
        Returns list of missing critical keys
        """
        missing = []

        if not self.app.secret_key:
            missing.append('SECRET_KEY')

        if not self.api.anthropic_api_key:
            missing.append('ANTHROPIC_API_KEY')

        if not self.api.apify_api_token:
            missing.append('APIFY_API_TOKEN')

        return missing

    def get_retailer_availability(self) -> dict[str, bool]:
        """
        Check which retailer integrations are configured
        Returns dict of retailer_name -> is_available
        """
        return {
            'etsy': bool(self.retailers.etsy_api_key.strip()),
            'awin': bool(self.retailers.awin_data_feed_api_key.strip()),
            'ebay': bool(self.retailers.ebay_client_id.strip() and self.retailers.ebay_client_secret.strip()),
            'shareasale': all([
                self.retailers.shareasale_affiliate_id.strip(),
                self.retailers.shareasale_api_token.strip(),
                self.retailers.shareasale_api_secret.strip(),
            ]),
            'skimlinks': bool(self.retailers.skimlinks_publisher_id.strip()),
            'amazon': bool(self.retailers.rapidapi_key.strip()),
        }


# Singleton instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    Get the global settings instance (singleton)
    Lazily loads settings on first access
    """
    global _settings
    if _settings is None:
        _settings = Settings()

        # Validate critical settings
        missing = _settings.validate_critical()
        if missing:
            logger.error(f"CRITICAL: Missing required environment variables: {', '.join(missing)}")
            logger.error("App may not function correctly. Check your .env file or environment configuration.")

    return _settings


def reload_settings():
    """
    Force reload of settings from environment
    Useful for testing or hot-reloading config
    """
    global _settings
    _settings = None
    return get_settings()
