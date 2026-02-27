"""
Unified Storage Service for GiftWise
====================================

Consolidates all shelve operations scattered across 8+ files into a single,
thread-safe, production-ready storage interface.

Features:
- Context manager for safe shelve operations
- Thread-safe access with RLock
- TTL/expiry cleanup utilities
- Graceful error handling
- Easy to swap backends later (Redis, PostgreSQL)

Files this replaces shelve usage in:
- share_manager.py
- referral_system.py
- site_stats.py
- usage_tracker.py
- giftwise_app.py
- progress_service.py
- local_events.py
- repositories/user_repository.py

Usage:
    # Option 1: Use factory functions for common databases
    from storage_service import get_share_storage
    storage = get_share_storage()
    storage.set('share_abc123', {'data': 'value'})

    # Option 2: Create custom storage instance
    storage = StorageService('/path/to/custom.db')
    storage.set('key', 'value')

    # Option 3: Use context manager for bulk operations
    with storage.open_db() as db:
        db['key1'] = 'value1'
        db['key2'] = 'value2'
        db.sync()
"""

import shelve
import threading
import logging
import time
import os
from contextlib import contextmanager
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class StorageService:
    """
    Thread-safe storage service wrapping shelve operations.

    Provides a unified interface for all key-value storage operations with:
    - Automatic error handling
    - Thread-safe access
    - TTL/expiry cleanup
    - Future-proof abstraction (can swap to Redis/PostgreSQL later)
    """

    def __init__(self, db_path: str):
        """
        Initialize storage service for a specific database.

        Args:
            db_path: Absolute path to shelve database file (without extension)

        Thread Safety:
            All operations are thread-safe via RLock. Multiple threads can safely
            read/write to the same StorageService instance.
        """
        self.db_path = db_path
        self._lock = threading.RLock()  # Reentrant lock for thread safety

        # Ensure data directory exists
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            logger.info(f"Created storage directory: {db_dir}")

    @contextmanager
    def open_db(self, writeback: bool = True):
        """
        Context manager for safe shelve operations.

        Ensures database is properly closed even if an error occurs.
        Use this for bulk operations that need multiple reads/writes.

        Args:
            writeback: If True, mutable entries are automatically written back

        Yields:
            shelve.Shelf: Open shelve database

        Example:
            with storage.open_db() as db:
                db['key1'] = 'value1'
                db['key2'] = 'value2'
                db.sync()  # Explicit sync for writeback=True
        """
        db = None
        try:
            db = shelve.open(self.db_path, writeback=writeback)
            yield db
        except Exception as e:
            logger.error(f"Shelve operation failed on {self.db_path}: {e}")
            raise
        finally:
            if db is not None:
                try:
                    db.close()
                except Exception as e:
                    logger.error(f"Failed to close shelve database {self.db_path}: {e}")

    def get(self, key: str, default=None) -> Any:
        """
        Get value with default fallback.

        Args:
            key: Storage key
            default: Value to return if key doesn't exist

        Returns:
            Stored value or default

        Raises:
            Exception: If shelve operation fails (use safe_get() to suppress)
        """
        with self._lock:
            with self.open_db() as db:
                return db.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """
        Set value with automatic sync.

        Args:
            key: Storage key
            value: Value to store (must be picklable)

        Raises:
            Exception: If shelve operation fails (use safe_set() to suppress)
        """
        with self._lock:
            with self.open_db() as db:
                db[key] = value
                db.sync()

    def delete(self, key: str) -> bool:
        """
        Delete key from storage.

        Args:
            key: Storage key to delete

        Returns:
            True if key existed and was deleted, False if key didn't exist

        Raises:
            Exception: If shelve operation fails
        """
        with self._lock:
            with self.open_db() as db:
                if key in db:
                    del db[key]
                    db.sync()
                    return True
                return False

    def exists(self, key: str) -> bool:
        """
        Check if key exists in storage.

        Args:
            key: Storage key to check

        Returns:
            True if key exists, False otherwise
        """
        with self._lock:
            with self.open_db() as db:
                return key in db

    def list_keys(self) -> List[str]:
        """
        List all keys in database.

        Returns:
            List of all keys currently in storage

        Note:
            For large databases, this can be slow. Consider pagination
            or key prefix patterns for better performance.
        """
        with self._lock:
            with self.open_db() as db:
                return list(db.keys())

    def cleanup_expired(self, ttl_field: str = 'created_at', max_age_seconds: int = 86400) -> int:
        """
        Clean up expired entries based on TTL field.

        Args:
            ttl_field: Name of timestamp field in stored dict (default: 'created_at')
            max_age_seconds: Maximum age in seconds before deletion (default: 24 hours)

        Returns:
            Number of entries deleted

        Example:
            # Delete shares older than 30 days
            storage.cleanup_expired(ttl_field='created_at', max_age_seconds=30*86400)

        Note:
            Only works with dict entries that have a timestamp field.
            Non-dict entries or dicts without the TTL field are skipped.
        """
        deleted = 0
        current_time = time.time()

        with self._lock:
            with self.open_db() as db:
                keys_to_delete = []

                for key in list(db.keys()):  # list() to avoid iterator issues
                    try:
                        entry = db[key]
                        if isinstance(entry, dict) and ttl_field in entry:
                            age = current_time - entry[ttl_field]
                            if age > max_age_seconds:
                                keys_to_delete.append(key)
                    except Exception as e:
                        logger.warning(f"Error checking expiry for key '{key}': {e}")
                        continue

                for key in keys_to_delete:
                    try:
                        del db[key]
                        deleted += 1
                    except Exception as e:
                        logger.error(f"Failed to delete expired key '{key}': {e}")

                if deleted > 0:
                    db.sync()
                    logger.info(f"Cleaned up {deleted} expired entries from {self.db_path}")

        return deleted

    def update(self, key: str, updates: Dict) -> None:
        """
        Update dict entry with new fields (merge operation).

        Args:
            key: Storage key
            updates: Dict of fields to add/update

        Example:
            storage.set('user', {'name': 'Alice', 'age': 25})
            storage.update('user', {'city': 'Austin'})
            # Result: {'name': 'Alice', 'age': 25, 'city': 'Austin'}

        Note:
            If key doesn't exist, creates new dict with updates.
            If stored value is not a dict, replaces it with updates dict.
        """
        with self._lock:
            with self.open_db() as db:
                entry = db.get(key, {})
                if not isinstance(entry, dict):
                    logger.warning(f"Key '{key}' is not a dict, replacing with updates")
                    entry = {}
                entry.update(updates)
                db[key] = entry
                db.sync()

    def increment(self, key: str, field: str, amount: int = 1) -> int:
        """
        Increment a numeric field (useful for counters).

        Args:
            key: Storage key (must be a dict)
            field: Field name within the dict
            amount: Amount to increment by (default: 1)

        Returns:
            New value after increment

        Example:
            storage.set('stats', {'views': 0})
            storage.increment('stats', 'views')  # Returns 1
            storage.increment('stats', 'views', amount=5)  # Returns 6

        Note:
            If key doesn't exist, creates new dict with field=amount.
            If field doesn't exist, initializes to 0 before increment.
        """
        with self._lock:
            with self.open_db() as db:
                entry = db.get(key, {})
                if not isinstance(entry, dict):
                    logger.warning(f"Key '{key}' is not a dict, creating new dict for increment")
                    entry = {}
                entry[field] = entry.get(field, 0) + amount
                db[key] = entry
                db.sync()
                return entry[field]

    def safe_get(self, key: str, default=None) -> Any:
        """
        Get with exception handling (never raises).

        Args:
            key: Storage key
            default: Value to return if key doesn't exist or error occurs

        Returns:
            Stored value, default, or default on error

        Use this when you don't want storage errors to crash your app.
        """
        try:
            return self.get(key, default)
        except Exception as e:
            logger.error(f"Storage get failed for key '{key}': {e}")
            return default

    def safe_set(self, key: str, value: Any) -> bool:
        """
        Set with exception handling (never raises).

        Args:
            key: Storage key
            value: Value to store

        Returns:
            True if successful, False if error occurred

        Use this when you don't want storage errors to crash your app.
        """
        try:
            self.set(key, value)
            return True
        except Exception as e:
            logger.error(f"Storage set failed for key '{key}': {e}")
            return False

    def safe_delete(self, key: str) -> bool:
        """
        Delete with exception handling (never raises).

        Args:
            key: Storage key to delete

        Returns:
            True if deleted, False if key didn't exist or error occurred
        """
        try:
            return self.delete(key)
        except Exception as e:
            logger.error(f"Storage delete failed for key '{key}': {e}")
            return False


# =============================================================================
# Factory Functions for Common Databases
# =============================================================================

_DATA_DIR = os.environ.get('DATA_DIR', '/home/user/GiftWise/data')


def get_share_storage() -> StorageService:
    """
    Get storage for share links.
    Path controlled by DATA_DIR env var (default: /home/user/GiftWise/data).
    Used by: share_manager.py
    """
    return StorageService(os.path.join(_DATA_DIR, 'shared_recommendations.db'))


def get_referral_storage() -> StorageService:
    """
    Get storage for referral codes.
    Path controlled by DATA_DIR env var (default: /home/user/GiftWise/data).
    Used by: referral_system.py
    """
    return StorageService(os.path.join(_DATA_DIR, 'referral_codes.db'))


def get_stats_storage() -> StorageService:
    """
    Get storage for site stats.
    Path controlled by DATA_DIR env var (default: /home/user/GiftWise/data).
    Used by: site_stats.py
    """
    return StorageService(os.path.join(_DATA_DIR, 'site_stats.db'))


def get_progress_storage() -> StorageService:
    """
    Get storage for generation progress.
    Path controlled by DATA_DIR env var (default: /home/user/GiftWise/data).
    Used by: progress_service.py
    """
    return StorageService(os.path.join(_DATA_DIR, 'generation_progress.db'))


def get_user_storage() -> StorageService:
    """
    Get storage for user data.
    Path controlled by DATA_DIR env var (default: /home/user/GiftWise/data).
    Used by: repositories/user_repository.py
    """
    return StorageService(os.path.join(_DATA_DIR, 'users.db'))


# =============================================================================
# Migration Examples
# =============================================================================

"""
MIGRATION GUIDE
===============

Example 1: share_manager.py
----------------------------

BEFORE:
    import shelve

    def save_share(share_id, data):
        with shelve.open('/home/user/GiftWise/data/shared_recommendations.db') as db:
            db[share_id] = data
            db.sync()

    def get_share(share_id):
        with shelve.open('/home/user/GiftWise/data/shared_recommendations.db') as db:
            return db.get(share_id)

AFTER:
    from storage_service import get_share_storage

    storage = get_share_storage()

    def save_share(share_id, data):
        storage.set(share_id, data)

    def get_share(share_id):
        return storage.get(share_id)


Example 2: site_stats.py (Counter Pattern)
-------------------------------------------

BEFORE:
    import shelve

    def increment_stat(stat_name):
        with shelve.open('/home/user/GiftWise/data/site_stats.db') as db:
            stats = db.get('stats', {})
            stats[stat_name] = stats.get(stat_name, 0) + 1
            db['stats'] = stats
            db.sync()

AFTER:
    from storage_service import get_stats_storage

    storage = get_stats_storage()

    def increment_stat(stat_name):
        storage.increment('stats', stat_name, amount=1)


Example 3: TTL Cleanup (Share Expiry)
--------------------------------------

BEFORE:
    import time
    import shelve

    def cleanup_old_shares():
        with shelve.open('/home/user/GiftWise/data/shared_recommendations.db') as db:
            keys_to_delete = []
            for key in db.keys():
                share = db[key]
                if time.time() - share['created_at'] > 30 * 86400:  # 30 days
                    keys_to_delete.append(key)
            for key in keys_to_delete:
                del db[key]
            db.sync()

AFTER:
    from storage_service import get_share_storage

    storage = get_share_storage()

    def cleanup_old_shares():
        deleted = storage.cleanup_expired(ttl_field='created_at', max_age_seconds=30*86400)
        print(f"Deleted {deleted} expired shares")


Example 4: Bulk Operations (Context Manager)
---------------------------------------------

BEFORE:
    import shelve

    def batch_update_stats(updates):
        with shelve.open('/home/user/GiftWise/data/site_stats.db') as db:
            for key, value in updates.items():
                db[key] = value
            db.sync()

AFTER:
    from storage_service import get_stats_storage

    storage = get_stats_storage()

    def batch_update_stats(updates):
        with storage.open_db() as db:
            for key, value in updates.items():
                db[key] = value
            db.sync()

    # OR use individual sets (slightly slower but cleaner):
    def batch_update_stats(updates):
        for key, value in updates.items():
            storage.set(key, value)
"""


# =============================================================================
# Tests
# =============================================================================

if __name__ == "__main__":
    import tempfile
    import shutil

    print("=" * 60)
    print("Storage Service Tests")
    print("=" * 60)
    print()

    # Create temporary test directory
    test_dir = tempfile.mkdtemp()
    test_db = os.path.join(test_dir, 'test.db')

    try:
        storage = StorageService(test_db)

        # Test 1: Basic get/set
        print("Test 1: Basic get/set")
        storage.set('name', 'Alice')
        result = storage.get('name')
        assert result == 'Alice', f"Expected 'Alice', got {result}"
        print("  ✓ Set and get work")
        print()

        # Test 2: Default values
        print("Test 2: Default values")
        result = storage.get('missing', 'default')
        assert result == 'default', f"Expected 'default', got {result}"
        print("  ✓ Default values work")
        print()

        # Test 3: Delete
        print("Test 3: Delete")
        storage.set('temp', 'value')
        assert storage.exists('temp'), "Key should exist after set"
        deleted = storage.delete('temp')
        assert deleted, "Delete should return True for existing key"
        assert not storage.exists('temp'), "Key should not exist after delete"
        deleted_again = storage.delete('temp')
        assert not deleted_again, "Delete should return False for non-existent key"
        print("  ✓ Delete works")
        print()

        # Test 4: Update
        print("Test 4: Update")
        storage.set('user', {'name': 'Bob', 'age': 25})
        storage.update('user', {'city': 'Austin'})
        user = storage.get('user')
        assert user['name'] == 'Bob', f"Expected name 'Bob', got {user.get('name')}"
        assert user['city'] == 'Austin', f"Expected city 'Austin', got {user.get('city')}"
        assert user['age'] == 25, f"Expected age 25, got {user.get('age')}"
        print("  ✓ Update works")
        print()

        # Test 5: Increment
        print("Test 5: Increment")
        storage.set('stats', {'views': 0})
        result1 = storage.increment('stats', 'views')
        assert result1 == 1, f"Expected 1, got {result1}"
        result2 = storage.increment('stats', 'views')
        assert result2 == 2, f"Expected 2, got {result2}"
        result3 = storage.increment('stats', 'clicks', amount=5)
        assert result3 == 5, f"Expected 5, got {result3}"
        stats = storage.get('stats')
        assert stats['views'] == 2, f"Expected views=2, got {stats.get('views')}"
        assert stats['clicks'] == 5, f"Expected clicks=5, got {stats.get('clicks')}"
        print("  ✓ Increment works")
        print()

        # Test 6: TTL cleanup
        print("Test 6: TTL cleanup")
        current_time = time.time()
        storage.set('old', {'created_at': current_time - 200, 'data': 'old'})
        storage.set('new', {'created_at': current_time, 'data': 'new'})
        storage.set('no_timestamp', {'data': 'no_timestamp'})  # Should be skipped
        storage.set('not_a_dict', 'plain_string')  # Should be skipped

        deleted = storage.cleanup_expired(ttl_field='created_at', max_age_seconds=100)
        assert deleted == 1, f"Expected 1 deletion, got {deleted}"
        assert not storage.exists('old'), "Old entry should be deleted"
        assert storage.exists('new'), "New entry should remain"
        assert storage.exists('no_timestamp'), "Entry without timestamp should remain"
        assert storage.exists('not_a_dict'), "Non-dict entry should remain"
        print("  ✓ TTL cleanup works")
        print()

        # Test 7: List keys
        print("Test 7: List keys")
        keys = storage.list_keys()
        expected_keys = {'name', 'user', 'stats', 'new', 'no_timestamp', 'not_a_dict'}
        actual_keys = set(keys)
        assert expected_keys == actual_keys, f"Expected {expected_keys}, got {actual_keys}"
        print(f"  ✓ List keys works ({len(keys)} keys found)")
        print()

        # Test 8: Context manager
        print("Test 8: Context manager for bulk operations")
        with storage.open_db() as db:
            db['bulk1'] = 'value1'
            db['bulk2'] = 'value2'
            db['bulk3'] = 'value3'
            db.sync()
        assert storage.get('bulk1') == 'value1'
        assert storage.get('bulk2') == 'value2'
        assert storage.get('bulk3') == 'value3'
        print("  ✓ Context manager works")
        print()

        # Test 9: Safe operations
        print("Test 9: Safe get/set (error handling)")
        storage.set('safe_key', 'safe_value')
        result = storage.safe_get('safe_key')
        assert result == 'safe_value'
        result = storage.safe_get('missing_key', 'fallback')
        assert result == 'fallback'
        success = storage.safe_set('another_key', 'another_value')
        assert success, "Safe set should return True on success"
        print("  ✓ Safe operations work")
        print()

        # Test 10: Thread safety (basic check)
        print("Test 10: Thread safety")
        import threading

        storage.set('counter', {'value': 0})

        def increment_counter():
            for _ in range(100):
                storage.increment('counter', 'value')

        threads = [threading.Thread(target=increment_counter) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        final_count = storage.get('counter')['value']
        assert final_count == 500, f"Expected 500, got {final_count} (thread safety issue)"
        print("  ✓ Thread safety works")
        print()

        print("=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)

    except AssertionError as e:
        print()
        print("=" * 60)
        print(f"❌ Test failed: {e}")
        print("=" * 60)
        raise

    finally:
        # Cleanup test directory
        shutil.rmtree(test_dir, ignore_errors=True)
