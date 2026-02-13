"""
User data repository - decouples storage implementation from business logic
Provides a clean interface for user CRUD operations with thread safety
"""

import shelve
import threading
import logging
from typing import Optional, Protocol, Dict, Any
from contextlib import contextmanager

logger = logging.getLogger('giftwise')

# Global locks for thread-safe database access
db_locks: Dict[str, threading.Lock] = {}
lock_lock = threading.Lock()


class UserRepository(Protocol):
    """
    Protocol defining the interface for user data access
    Allows swapping storage backends (shelve -> Postgres -> DynamoDB) without touching business logic
    """

    def get(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve user data by ID. Returns None if not found."""
        ...

    def save(self, user_id: str, data: Dict[str, Any]) -> bool:
        """Save/update user data. Merges with existing data. Returns success status."""
        ...

    def create(self, user_id: str, initial_data: Dict[str, Any]) -> bool:
        """Create new user. Returns False if user already exists."""
        ...

    def delete(self, user_id: str) -> bool:
        """Delete user. Returns success status."""
        ...

    def exists(self, user_id: str) -> bool:
        """Check if user exists."""
        ...


class ShelveUserRepository:
    """
    Shelve-based implementation of UserRepository
    Thread-safe with per-user locking
    """

    def __init__(self, db_path: str = 'giftwise_db'):
        self.db_path = db_path

    def _get_lock(self, user_id: str) -> threading.Lock:
        """Get or create a lock for a specific user"""
        with lock_lock:
            if user_id not in db_locks:
                db_locks[user_id] = threading.Lock()
            return db_locks[user_id]

    @contextmanager
    def _db_connection(self):
        """Context manager for shelve database access"""
        db = None
        try:
            db = shelve.open(self.db_path)
            yield db
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            raise
        finally:
            if db:
                db.close()

    def _make_key(self, user_id: str) -> str:
        """Generate database key for user"""
        return f'user_{user_id}'

    def get(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user data from database"""
        if not user_id:
            return None

        try:
            with self._db_connection() as db:
                return db.get(self._make_key(user_id))
        except Exception as e:
            logger.error(f"Error getting user {user_id}: {e}")
            return None

    def save(self, user_id: str, data: Dict[str, Any]) -> bool:
        """
        Save user data to database (thread-safe)
        Merges new data with existing user data
        """
        if not user_id:
            logger.error("Attempted to save user with no user_id")
            return False

        lock = self._get_lock(user_id)
        try:
            with lock:
                with self._db_connection() as db:
                    key = self._make_key(user_id)
                    existing = db.get(key, {})
                    existing.update(data)
                    db[key] = existing
            return True
        except Exception as e:
            logger.error(f"Error saving user {user_id}: {e}")
            return False

    def create(self, user_id: str, initial_data: Dict[str, Any]) -> bool:
        """
        Create new user (fails if user already exists)
        """
        if not user_id:
            logger.error("Attempted to create user with no user_id")
            return False

        if self.exists(user_id):
            logger.warning(f"User {user_id} already exists")
            return False

        lock = self._get_lock(user_id)
        try:
            with lock:
                with self._db_connection() as db:
                    db[self._make_key(user_id)] = initial_data
            logger.info(f"Created user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error creating user {user_id}: {e}")
            return False

    def delete(self, user_id: str) -> bool:
        """Delete user from database"""
        if not user_id:
            return False

        lock = self._get_lock(user_id)
        try:
            with lock:
                with self._db_connection() as db:
                    key = self._make_key(user_id)
                    if key in db:
                        del db[key]
                        logger.info(f"Deleted user {user_id}")
                        return True
                    return False
        except Exception as e:
            logger.error(f"Error deleting user {user_id}: {e}")
            return False

    def exists(self, user_id: str) -> bool:
        """Check if user exists in database"""
        if not user_id:
            return False

        try:
            with self._db_connection() as db:
                return self._make_key(user_id) in db
        except Exception as e:
            logger.error(f"Error checking user existence {user_id}: {e}")
            return False


# Singleton instance (can be swapped for testing/different backends)
_user_repository: Optional[UserRepository] = None


def get_user_repository() -> UserRepository:
    """
    Get the user repository instance (singleton)
    Can be overridden for testing or different storage backends
    """
    global _user_repository
    if _user_repository is None:
        _user_repository = ShelveUserRepository()
    return _user_repository


def set_user_repository(repository: UserRepository):
    """
    Set a custom user repository implementation
    Useful for testing (mock repository) or swapping storage backends
    """
    global _user_repository
    _user_repository = repository
