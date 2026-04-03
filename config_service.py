"""
Configuration Service - Centralized environment variable management

This module provides type-safe, validated access to all environment variables
across the GiftWise application. It eliminates scattered os.getenv() calls and
provides a single source of truth for configuration.

Usage:
    from config_service import get_config

    config = get_config()

    # Access nested config
    api_key = config.claude.api_key
    etsy_key = config.affiliate.etsy_api_key
    db_path = config.database.products_db

    # Check configuration status
    if config.affiliate.amazon_affiliate_tag:
        # Amazon is configured
        pass

Migration from old pattern:
    # Before (scattered throughout modules):
    import os
    api_key = os.getenv('ANTHROPIC_API_KEY')
    profile_model = os.getenv('CLAUDE_PROFILE_MODEL', 'claude-sonnet-4-20250514')
    rapidapi_key = os.getenv('RAPIDAPI_KEY', '')
    etsy_key = os.getenv('ETSY_API_KEY', '')

    if not api_key:
        logger.warning("ANTHROPIC_API_KEY not set")

    # After:
    from config_service import get_config, is_retailer_available

    config = get_config()  # Singleton - loads once, validates, logs status

    # Access config
    api_key = config.claude.api_key
    profile_model = config.claude.profile_model
    rapidapi_key = config.affiliate.rapidapi_key
    etsy_key = config.affiliate.etsy_api_key

    # Check availability
    if is_retailer_available('etsy'):
        # Etsy is configured
        pass

    # Database paths
    db_path = config.database.products_db

    # OAuth credentials
    spotify_client_id = config.oauth.spotify_client_id

    # Benefits:
    # - Single source of truth for all env vars
    # - Validation happens once at startup
    # - Type-safe access (no typos in env var names)
    # - Easy to mock for testing

Author: Chad + Claude
Date: February 2026
"""

from dataclasses import dataclass, field
from typing import Optional
import os
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# AFFILIATE NETWORK CONFIGURATION
# =============================================================================

@dataclass
class AffiliateConfig:
    """Affiliate network credentials and settings"""

    # Amazon (RapidAPI)
    rapidapi_key: str = ""
    amazon_affiliate_tag: str = ""

    # eBay
    ebay_client_id: str = ""
    ebay_client_secret: str = ""
    ebay_app_id: str = ""  # Legacy field
    ebay_campaign_id: str = "5339236479"  # Default campaign ID

    # Etsy
    etsy_api_key: str = ""
    etsy_client_id: str = ""
    etsy_client_secret: str = ""

    # Awin (former ShareASale merchants)
    awin_data_feed_api_key: str = ""
    awin_publisher_id: str = ""
    awin_api_token: str = ""

    # ShareASale (legacy - migrated to Awin Oct 2025)
    shareasale_affiliate_id: str = ""
    shareasale_api_token: str = ""
    shareasale_api_secret: str = ""

    # CJ Affiliate
    cj_account_id: str = ""
    cj_api_key: str = ""
    cj_api_token: str = ""
    cj_website_id: str = ""

    # Yelp (for experience providers)
    yelp_api_key: str = ""

    @classmethod
    def from_env(cls) -> 'AffiliateConfig':
        """Load affiliate credentials from environment variables"""
        return cls(
            # Amazon
            rapidapi_key=os.getenv('RAPIDAPI_KEY', ''),
            amazon_affiliate_tag=os.getenv('AMAZON_AFFILIATE_TAG', ''),

            # eBay
            ebay_client_id=os.getenv('EBAY_CLIENT_ID', ''),
            ebay_client_secret=os.getenv('EBAY_CLIENT_SECRET', ''),
            ebay_app_id=os.getenv('EBAY_APP_ID', ''),
            ebay_campaign_id=os.getenv('EBAY_CAMPAIGN_ID', '5339236479'),

            # Etsy
            etsy_api_key=os.getenv('ETSY_API_KEY', ''),
            etsy_client_id=os.getenv('ETSY_CLIENT_ID', ''),
            etsy_client_secret=os.getenv('ETSY_CLIENT_SECRET', ''),

            # Awin
            awin_data_feed_api_key=os.getenv('AWIN_DATA_FEED_API_KEY', ''),
            awin_publisher_id=os.getenv('AWIN_PUBLISHER_ID', ''),
            awin_api_token=os.getenv('AWIN_API_TOKEN', ''),

            # ShareASale
            shareasale_affiliate_id=os.getenv('SHAREASALE_AFFILIATE_ID', ''),
            shareasale_api_token=os.getenv('SHAREASALE_TOKEN', ''),
            shareasale_api_secret=os.getenv('SHAREASALE_SECRET', ''),

            # CJ Affiliate
            cj_account_id=os.getenv('CJ_ACCOUNT_ID', ''),
            cj_api_key=os.getenv('CJ_API_KEY', ''),
            cj_api_token=os.getenv('CJ_API_TOKEN', ''),
            cj_website_id=os.getenv('CJ_WEBSITE_ID', ''),

            # Yelp
            yelp_api_key=os.getenv('YELP_API_KEY', ''),
        )

    def get_retailer_availability(self) -> dict[str, bool]:
        """
        Check which retailer integrations are configured.

        Returns:
            Dict mapping retailer name to availability status
        """
        return {
            'amazon': bool(self.rapidapi_key.strip()),
            'ebay': bool(self.ebay_client_id.strip() and self.ebay_client_secret.strip()),
            'etsy': bool(self.etsy_api_key.strip()),
            'awin': bool(self.awin_data_feed_api_key.strip()),
            'shareasale': bool(self.shareasale_affiliate_id.strip() and
                             self.shareasale_api_token.strip() and
                             self.shareasale_api_secret.strip()),
            'cj': bool(self.cj_api_key.strip() or self.cj_api_token.strip()),
            'yelp': bool(self.yelp_api_key.strip()),
        }


# =============================================================================
# CLAUDE AI CONFIGURATION
# =============================================================================

@dataclass
class ClaudeConfig:
    """Claude AI model configuration for A/B testing"""

    api_key: str
    profile_model: str = 'claude-sonnet-4-20250514'
    curator_model: str = 'claude-sonnet-4-20250514'

    @classmethod
    def from_env(cls) -> 'ClaudeConfig':
        """Load Claude config from environment with validation"""
        api_key = os.getenv('ANTHROPIC_API_KEY', '')

        if not api_key:
            logger.warning("ANTHROPIC_API_KEY not set - app will not function")

        return cls(
            api_key=api_key,
            profile_model=os.getenv('CLAUDE_PROFILE_MODEL', 'claude-sonnet-4-20250514'),
            curator_model=os.getenv('CLAUDE_CURATOR_MODEL', 'claude-sonnet-4-20250514'),
        )

    def log_configuration(self):
        """Log which models are configured (for debugging)"""
        logger.info(f"Claude models - profile: {self.profile_model}, curator: {self.curator_model}")


# =============================================================================
# DATABASE CONFIGURATION
# =============================================================================

@dataclass
class DatabaseConfig:
    """Database and storage paths"""

    # Base data directory
    data_dir: str = '/home/user/GiftWise/data'

    # Individual database files
    products_db: str = '/home/user/GiftWise/data/products.db'
    users_db: str = '/home/user/GiftWise/data/users.db'
    shares_db: str = '/home/user/GiftWise/data/shared_recommendations.db'
    referrals_db: str = '/home/user/GiftWise/data/referral_codes.db'
    stats_db: str = '/home/user/GiftWise/data/site_stats.db'
    progress_db: str = '/home/user/GiftWise/data/generation_progress.db'

    @classmethod
    def from_env(cls) -> 'DatabaseConfig':
        """Load database config from environment"""
        base_path = os.getenv('DATA_DIR', '/home/user/GiftWise/data')

        # Support both DATABASE_PATH (old) and DATA_DIR (new)
        legacy_db_path = os.getenv('DATABASE_PATH')
        if legacy_db_path:
            base_path = os.path.dirname(legacy_db_path)

        return cls(
            data_dir=base_path,
            products_db=os.getenv('PRODUCTS_DB_PATH', f"{base_path}/products.db"),
            users_db=os.getenv('USERS_DB_PATH', f"{base_path}/users.db"),
            shares_db=os.getenv('SHARES_DB_PATH', f"{base_path}/shared_recommendations.db"),
            referrals_db=os.getenv('REFERRALS_DB_PATH', f"{base_path}/referral_codes.db"),
            stats_db=os.getenv('STATS_DB_PATH', f"{base_path}/site_stats.db"),
            progress_db=os.getenv('PROGRESS_DB_PATH', f"{base_path}/generation_progress.db"),
        )


# =============================================================================
# OAUTH CONFIGURATION
# =============================================================================

@dataclass
class OAuthConfig:
    """OAuth provider credentials for social integrations"""

    # Instagram
    instagram_app_id: str = ""
    instagram_app_secret: str = ""
    instagram_redirect_uri: str = "https://giftwise.fit/connect/instagram/callback"

    # TikTok
    tiktok_client_key: str = ""
    tiktok_client_secret: str = ""
    tiktok_redirect_uri: str = "https://giftwise.fit/connect/tiktok/callback"

    # Spotify
    spotify_client_id: str = ""
    spotify_client_secret: str = ""
    spotify_redirect_uri: str = "https://giftwise.fit/connect/spotify/callback"

    # Pinterest
    pinterest_app_id: str = ""
    pinterest_app_secret: str = ""
    pinterest_client_id: str = ""
    pinterest_client_secret: str = ""
    pinterest_redirect_uri: str = "https://giftwise.fit/connect/pinterest/callback"

    # Google (YouTube)
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "https://giftwise.fit/oauth/google/callback"

    @classmethod
    def from_env(cls) -> 'OAuthConfig':
        """Load OAuth credentials from environment"""
        return cls(
            # Instagram
            instagram_app_id=os.getenv('INSTAGRAM_APP_ID', ''),
            instagram_app_secret=os.getenv('INSTAGRAM_APP_SECRET', ''),
            instagram_redirect_uri=os.getenv('INSTAGRAM_REDIRECT_URI',
                                            'https://giftwise.fit/connect/instagram/callback'),

            # TikTok
            tiktok_client_key=os.getenv('TIKTOK_CLIENT_KEY', ''),
            tiktok_client_secret=os.getenv('TIKTOK_CLIENT_SECRET', ''),
            tiktok_redirect_uri=os.getenv('TIKTOK_REDIRECT_URI',
                                         'https://giftwise.fit/connect/tiktok/callback'),

            # Spotify
            spotify_client_id=os.getenv('SPOTIFY_CLIENT_ID', ''),
            spotify_client_secret=os.getenv('SPOTIFY_CLIENT_SECRET', ''),
            spotify_redirect_uri=os.getenv('SPOTIFY_REDIRECT_URI',
                                          'https://giftwise.fit/connect/spotify/callback'),

            # Pinterest
            pinterest_app_id=os.getenv('PINTEREST_APP_ID', ''),
            pinterest_app_secret=os.getenv('PINTEREST_APP_SECRET', ''),
            pinterest_client_id=os.getenv('PINTEREST_CLIENT_ID', ''),
            pinterest_client_secret=os.getenv('PINTEREST_CLIENT_SECRET', ''),
            pinterest_redirect_uri=os.getenv('PINTEREST_REDIRECT_URI',
                                            'https://giftwise.fit/connect/pinterest/callback'),

            # Google
            google_client_id=os.getenv('GOOGLE_CLIENT_ID', ''),
            google_client_secret=os.getenv('GOOGLE_CLIENT_SECRET', ''),
            google_redirect_uri=os.getenv('GOOGLE_REDIRECT_URI',
                                         'https://giftwise.fit/oauth/google/callback'),
        )


# =============================================================================
# SCRAPING CONFIGURATION
# =============================================================================

@dataclass
class ScrapingConfig:
    """Web scraping and API credentials"""

    # Apify (Instagram/TikTok scraping)
    apify_api_token: str = ""

    # SerpAPI (Google search)
    serpapi_api_key: str = ""

    # Google Custom Search
    google_cse_api_key: str = ""
    google_custom_search_engine_id: str = ""

    # Unsplash (image fallbacks)
    unsplash_access_key: str = ""

    @classmethod
    def from_env(cls) -> 'ScrapingConfig':
        """Load scraping credentials from environment"""
        return cls(
            apify_api_token=os.getenv('APIFY_API_TOKEN', ''),
            serpapi_api_key=os.getenv('SERPAPI_API_KEY', ''),
            google_cse_api_key=os.getenv('GOOGLE_CSE_API_KEY', ''),
            google_custom_search_engine_id=os.getenv('GOOGLE_CUSTOM_SEARCH_ENGINE_ID', ''),
            unsplash_access_key=os.getenv('UNSPLASH_ACCESS_KEY', ''),
        )


# =============================================================================
# APPLICATION CONFIGURATION
# =============================================================================

@dataclass
class AppConfig:
    """Core application settings"""

    # Flask
    environment: str = 'development'
    debug: bool = False
    secret_key: str = 'dev-secret-key-change-in-production'
    port: int = 5000

    # Admin
    admin_dashboard_key: str = ''
    admin_emails: list[str] = field(default_factory=list)

    # Performance
    max_concurrent_scrapers: int = 8

    # Logging
    log_level: str = 'INFO'

    # Sub-configs
    affiliate: AffiliateConfig = field(default_factory=AffiliateConfig)
    claude: ClaudeConfig = field(default_factory=ClaudeConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    oauth: OAuthConfig = field(default_factory=OAuthConfig)
    scraping: ScrapingConfig = field(default_factory=ScrapingConfig)

    @classmethod
    def from_env(cls) -> 'AppConfig':
        """Load all configuration from environment with validation"""

        # Parse environment
        env = os.getenv('ENV', os.getenv('FLASK_ENV', 'development'))
        debug = os.getenv('FLASK_DEBUG', 'False').lower() in ('true', '1', 'yes')
        secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
        port = int(os.getenv('PORT', '5000'))

        # Admin
        admin_dashboard_key = os.getenv('ADMIN_DASHBOARD_KEY', '')
        admin_emails_str = os.getenv('ADMIN_EMAILS', '')
        admin_emails = [e.strip() for e in admin_emails_str.split(',') if e.strip()]

        # Performance
        max_concurrent = int(os.getenv('MAX_CONCURRENT_SCRAPERS', '8'))

        # Logging
        log_level = os.getenv('LOG_LEVEL', 'INFO').upper()

        return cls(
            environment=env,
            debug=debug,
            secret_key=secret_key,
            port=port,
            admin_dashboard_key=admin_dashboard_key,
            admin_emails=admin_emails,
            max_concurrent_scrapers=max_concurrent,
            log_level=log_level,
            affiliate=AffiliateConfig.from_env(),
            claude=ClaudeConfig.from_env(),
            database=DatabaseConfig.from_env(),
            oauth=OAuthConfig.from_env(),
            scraping=ScrapingConfig.from_env(),
        )

    def validate(self) -> list[str]:
        """
        Validate required configuration.

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        # Production checks
        if self.environment == 'production':
            if self.secret_key == 'dev-secret-key-change-in-production':
                errors.append("SECRET_KEY must be set in production")

            if not self.claude.api_key:
                errors.append("ANTHROPIC_API_KEY must be set")

            if self.debug:
                errors.append("DEBUG should be False in production")

        # Critical API keys (always)
        if not self.claude.api_key:
            errors.append("ANTHROPIC_API_KEY is required for core functionality")

        return errors

    def log_status(self):
        """Log configuration status for debugging"""
        logger.info(f"Environment: {self.environment}")
        logger.info(f"Debug mode: {self.debug}")
        logger.info(f"Port: {self.port}")

        # Log Claude config
        self.claude.log_configuration()

        # Log retailer availability
        availability = self.affiliate.get_retailer_availability()
        active_retailers = [name for name, available in availability.items() if available]
        logger.info(f"Active retailers: {', '.join(active_retailers) if active_retailers else 'none'}")

        if not active_retailers:
            logger.warning("No retailer integrations configured - product search will fail")


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_config: Optional[AppConfig] = None


def get_config() -> AppConfig:
    """
    Get global configuration instance (singleton).

    This is the main entry point for all config access. The config
    is loaded once on first access and cached for the lifetime of
    the process.

    Returns:
        AppConfig instance with all configuration loaded

    Example:
        config = get_config()
        api_key = config.claude.api_key
        if config.affiliate.etsy_api_key:
            # Etsy is configured
            pass
    """
    global _config

    if _config is None:
        _config = AppConfig.from_env()

        # Validate configuration
        errors = _config.validate()
        if errors:
            logger.error("Configuration validation failed:")
            for error in errors:
                logger.error(f"  - {error}")

        # Log status
        _config.log_status()

    return _config


def reload_config() -> AppConfig:
    """
    Force reload configuration from environment.

    Useful for testing or hot-reloading config without restarting
    the application.

    Returns:
        Fresh AppConfig instance
    """
    global _config
    _config = None
    return get_config()


# =============================================================================
# CONVENIENCE HELPERS
# =============================================================================

def is_retailer_available(retailer_name: str) -> bool:
    """
    Quick check if a specific retailer is configured.

    Args:
        retailer_name: 'amazon', 'ebay', 'etsy', 'awin', etc.

    Returns:
        True if retailer credentials are configured
    """
    config = get_config()
    availability = config.affiliate.get_retailer_availability()
    return availability.get(retailer_name.lower(), False)


def get_claude_model(model_type: str = 'curator') -> str:
    """
    Get configured Claude model for a specific use case.

    Args:
        model_type: 'profile' or 'curator'

    Returns:
        Model ID string (e.g., 'claude-sonnet-4-20250514')
    """
    config = get_config()
    if model_type == 'profile':
        return config.claude.profile_model
    return config.claude.curator_model


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    print("Configuration Service - Test Suite")
    print("=" * 60)

    # Test 1: Load config
    print("\n1. Loading configuration from environment:")
    config = get_config()
    print(f"  Environment: {config.environment}")
    print(f"  Debug: {config.debug}")
    print(f"  Secret key set: {'Yes' if config.secret_key else 'No'}")

    # Test 2: Claude config
    print("\n2. Claude API Configuration:")
    print(f"  API key set: {'Yes' if config.claude.api_key else 'No'}")
    print(f"  Profile model: {config.claude.profile_model}")
    print(f"  Curator model: {config.claude.curator_model}")

    # Test 3: Retailer availability
    print("\n3. Retailer Availability:")
    availability = config.affiliate.get_retailer_availability()
    for retailer, available in sorted(availability.items()):
        status = "✓ Available" if available else "✗ Not configured"
        print(f"  {retailer.capitalize()}: {status}")

    # Test 4: Database paths
    print("\n4. Database Configuration:")
    print(f"  Data directory: {config.database.data_dir}")
    print(f"  Products DB: {config.database.products_db}")
    print(f"  Users DB: {config.database.users_db}")

    # Test 5: Validation
    print("\n5. Configuration Validation:")
    errors = config.validate()
    if errors:
        print("  Validation errors:")
        for error in errors:
            print(f"    - {error}")
    else:
        print("  ✓ All validation checks passed")

    # Test 6: Convenience helpers
    print("\n6. Convenience Helpers:")
    print(f"  Amazon available: {is_retailer_available('amazon')}")
    print(f"  Etsy available: {is_retailer_available('etsy')}")
    print(f"  Curator model: {get_claude_model('curator')}")
    print(f"  Profile model: {get_claude_model('profile')}")

    print("\n" + "=" * 60)
    print("All tests complete!")
