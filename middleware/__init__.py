"""
Flask middleware for authentication, authorization, and request processing
Decouples auth logic from route handlers
"""

from .auth import require_login, require_tier, optional_login, get_current_user

__all__ = ['require_login', 'require_tier', 'optional_login', 'get_current_user']
