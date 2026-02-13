"""
Authentication and authorization middleware
Provides decorators to protect routes and inject authenticated user
"""

from functools import wraps
from flask import session, redirect, jsonify, request
from typing import Optional, Dict, Any, Callable
import logging

logger = logging.getLogger('giftwise')


def get_current_user() -> Optional[Dict[str, Any]]:
    """
    Get current authenticated user from session
    Returns None if not logged in

    This function will be injected with the repository after app initialization
    """
    # Import here to avoid circular dependency
    from repositories import get_user_repository

    user_id = session.get('user_id')
    if not user_id:
        return None

    repo = get_user_repository()
    return repo.get(user_id)


def require_login(redirect_to: str = '/signup', api_mode: bool = False):
    """
    Decorator to require user authentication

    Args:
        redirect_to: URL to redirect to if not authenticated (for HTML routes)
        api_mode: If True, returns JSON 401 instead of redirect (for API routes)

    Usage:
        @app.route('/recommendations')
        @require_login()
        def recommendations(user):
            # user is automatically injected
            ...

        @app.route('/api/generate', methods=['POST'])
        @require_login(api_mode=True)
        def api_generate(user):
            # Returns 401 JSON if not authenticated
            ...
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def wrapper(*args, **kwargs):
            user = get_current_user()

            if not user:
                if api_mode:
                    return jsonify({'error': 'Authentication required'}), 401
                else:
                    return redirect(redirect_to)

            # Inject user as first argument to route handler
            return f(user, *args, **kwargs)

        return wrapper
    return decorator


def optional_login():
    """
    Decorator that injects user if logged in, None otherwise
    Does not require authentication

    Usage:
        @app.route('/landing')
        @optional_login()
        def landing(user):
            # user is None if not logged in
            if user:
                return render_template('logged_in_landing.html')
            return render_template('public_landing.html')
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def wrapper(*args, **kwargs):
            user = get_current_user()
            return f(user, *args, **kwargs)
        return wrapper
    return decorator


def require_tier(feature: str, api_mode: bool = False):
    """
    Decorator to require specific subscription tier for a feature
    Must be used AFTER @require_login

    Args:
        feature: Feature name to check (e.g., 'profiles', 'monthly_updates')
        api_mode: If True, returns JSON 403 instead of redirect

    Usage:
        @app.route('/api/generate-recommendations', methods=['POST'])
        @require_login(api_mode=True)
        @require_tier('recommendations', api_mode=True)
        def api_generate_recommendations(user):
            # Only called if user has tier access to 'recommendations'
            ...
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def wrapper(user, *args, **kwargs):
            # Import here to avoid circular dependency
            from giftwise_app import check_tier_limit

            if not check_tier_limit(user, feature):
                error_msg = f'Upgrade required to access {feature}'

                if api_mode:
                    return jsonify({'error': error_msg, 'upgrade_required': True}), 403
                else:
                    return redirect(f'/upgrade?feature={feature}')

            return f(user, *args, **kwargs)
        return wrapper
    return decorator


def json_body_required(schema: Optional[Dict[str, type]] = None):
    """
    Decorator to require and validate JSON body in POST requests

    Args:
        schema: Optional dict mapping field names to expected types
                Example: {'username': str, 'age': int}

    Usage:
        @app.route('/api/connect/instagram', methods=['POST'])
        @require_login(api_mode=True)
        @json_body_required({'username': str})
        def connect_instagram(user, data):
            username = data['username']  # Guaranteed to exist and be str
            ...
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not request.is_json:
                return jsonify({'error': 'Content-Type must be application/json'}), 400

            data = request.get_json()
            if not data:
                return jsonify({'error': 'Request body is required'}), 400

            # Validate schema if provided
            if schema:
                for field, expected_type in schema.items():
                    if field not in data:
                        return jsonify({'error': f'Missing required field: {field}'}), 400

                    if not isinstance(data[field], expected_type):
                        return jsonify({
                            'error': f'Field {field} must be {expected_type.__name__}'
                        }), 400

            # Inject data as argument
            return f(*args, data=data, **kwargs)
        return wrapper
    return decorator


# Convenience decorator for common API pattern
def api_route(require_auth: bool = True, require_json: bool = False,
              tier: Optional[str] = None):
    """
    Composite decorator for API routes
    Combines authentication, tier checking, and JSON validation

    Usage:
        @app.route('/api/favorites', methods=['POST'])
        @api_route(require_auth=True, require_json=True)
        def api_add_favorite(user, data):
            # user is injected, data is validated JSON
            ...
    """
    def decorator(f: Callable) -> Callable:
        # Apply decorators in reverse order (innermost first)
        decorated = f

        if require_json:
            decorated = json_body_required()(decorated)

        if tier:
            decorated = require_tier(tier, api_mode=True)(decorated)

        if require_auth:
            decorated = require_login(api_mode=True)(decorated)

        return decorated
    return decorator
