# Storage Service Migration Guide

## Overview

The new `storage_service.py` consolidates all shelve operations scattered across 8+ files into a single, thread-safe, production-ready storage interface.

## Files Using Shelve (Migration Targets)

1. **share_manager.py** - Share link storage
2. **referral_system.py** - Referral code storage
3. **site_stats.py** - Site statistics/analytics
4. **usage_tracker.py** - Usage tracking
5. **giftwise_app.py** - Main app (various shelve operations)
6. **local_events.py** - Event logging
7. **repositories/user_repository.py** - User data persistence

**Note:** `progress_service.py` uses in-memory dict storage (no shelve migration needed).

## Quick Migration Examples

### Example 1: Simple Get/Set (share_manager.py)

**BEFORE:**
```python
import shelve

def save_share(share_id, data):
    with shelve.open('/home/user/GiftWise/data/shared_recommendations.db') as db:
        db[share_id] = data
        db.sync()

def get_share(share_id):
    with shelve.open('/home/user/GiftWise/data/shared_recommendations.db') as db:
        return db.get(share_id)
```

**AFTER:**
```python
from storage_service import get_share_storage

storage = get_share_storage()

def save_share(share_id, data):
    storage.set(share_id, data)

def get_share(share_id):
    return storage.get(share_id)
```

### Example 2: Counter/Increment (site_stats.py)

**BEFORE:**
```python
import shelve

def increment_stat(stat_name):
    with shelve.open('/home/user/GiftWise/data/site_stats.db') as db:
        stats = db.get('stats', {})
        stats[stat_name] = stats.get(stat_name, 0) + 1
        db['stats'] = stats
        db.sync()
```

**AFTER:**
```python
from storage_service import get_stats_storage

storage = get_stats_storage()

def increment_stat(stat_name):
    storage.increment('stats', stat_name, amount=1)
```

### Example 3: TTL/Expiry Cleanup (share expiry)

**BEFORE:**
```python
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
```

**AFTER:**
```python
from storage_service import get_share_storage

storage = get_share_storage()

def cleanup_old_shares():
    deleted = storage.cleanup_expired(ttl_field='created_at', max_age_seconds=30*86400)
    print(f"Deleted {deleted} expired shares")
```

## Available Factory Functions

```python
from storage_service import (
    get_share_storage,      # /data/shared_recommendations.db
    get_referral_storage,   # /data/referral_codes.db
    get_stats_storage,      # /data/site_stats.db
    get_progress_storage,   # /data/generation_progress.db
    get_user_storage,       # /data/users.db
)
```

## Common Patterns

### Pattern 1: Basic CRUD
```python
storage.set('key', 'value')
value = storage.get('key', default='fallback')
exists = storage.exists('key')
deleted = storage.delete('key')
```

### Pattern 2: Dict Updates
```python
storage.set('user', {'name': 'Alice', 'age': 25})
storage.update('user', {'city': 'Austin'})  # Merges new fields
# Result: {'name': 'Alice', 'age': 25, 'city': 'Austin'}
```

### Pattern 3: Counters
```python
storage.increment('stats', 'views')  # Increment by 1
storage.increment('stats', 'clicks', amount=5)  # Increment by 5
```

### Pattern 4: Bulk Operations (Context Manager)
```python
with storage.open_db() as db:
    db['key1'] = 'value1'
    db['key2'] = 'value2'
    db['key3'] = 'value3'
    db.sync()
```

### Pattern 5: Safe Operations (Never Raise)
```python
value = storage.safe_get('key', default='fallback')  # Never raises
success = storage.safe_set('key', 'value')  # Returns True/False
```

## Benefits

1. **Thread Safety** - All operations use RLock for safe concurrent access
2. **Consistent Error Handling** - Unified logging and error patterns
3. **TTL/Expiry Support** - Built-in cleanup for time-based expiry
4. **Future-Proof** - Easy to swap backend (Redis, PostgreSQL) later
5. **Less Boilerplate** - Eliminates repetitive shelve.open/sync/close code
6. **Testing** - Comprehensive test suite included

## Migration Strategy

1. **Phase 1: Add storage_service.py** ✅ Complete
2. **Phase 2: Migrate one file at a time** (start with simplest: share_manager.py)
3. **Phase 3: Test each migration thoroughly**
4. **Phase 4: Remove old shelve imports once all migrated**

## Testing

Run storage service tests:
```bash
python storage_service.py
```

Expected output: All 10 tests should pass (basic get/set, defaults, delete, update, increment, TTL cleanup, list keys, context manager, safe ops, thread safety).

## Notes

- All factory functions ensure `/home/user/GiftWise/data/` directory exists
- Thread-safe for multi-threaded Flask app (Gunicorn workers)
- Maintains backward compatibility with existing data
- No changes to database file format (still shelve under the hood)
