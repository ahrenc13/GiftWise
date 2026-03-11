# Storage Service: Before & After Examples

## Pattern 1: Simple Get/Set

### ❌ BEFORE (Repetitive, error-prone)
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

### ✅ AFTER (Clean, concise)
```python
from storage_service import get_share_storage

storage = get_share_storage()

def save_share(share_id, data):
    storage.set(share_id, data)

def get_share(share_id):
    return storage.get(share_id)
```

**Savings**: 8 lines → 2 lines

---

## Pattern 2: Counter/Increment

### ❌ BEFORE (Manual dict manipulation)
```python
import shelve

def increment_stat(stat_name):
    with shelve.open('/home/user/GiftWise/data/site_stats.db') as db:
        stats = db.get('stats', {})
        stats[stat_name] = stats.get(stat_name, 0) + 1
        db['stats'] = stats
        db.sync()
```

### ✅ AFTER (Built-in increment)
```python
from storage_service import get_stats_storage

storage = get_stats_storage()

def increment_stat(stat_name):
    storage.increment('stats', stat_name)
```

**Savings**: 6 lines → 1 line

---

## Pattern 3: Dict Update (Merge Fields)

### ❌ BEFORE (Get, modify, set)
```python
import shelve

def update_user_city(user_id, city):
    with shelve.open('/home/user/GiftWise/data/users.db') as db:
        user = db.get(user_id, {})
        user['city'] = city
        db[user_id] = user
        db.sync()
```

### ✅ AFTER (Built-in update)
```python
from storage_service import get_user_storage

storage = get_user_storage()

def update_user_city(user_id, city):
    storage.update(user_id, {'city': city})
```

**Savings**: 5 lines → 1 line

---

## Pattern 4: TTL/Expiry Cleanup

### ❌ BEFORE (Manual iteration and deletion)
```python
import time
import shelve

def cleanup_old_shares():
    with shelve.open('/home/user/GiftWise/data/shared_recommendations.db') as db:
        keys_to_delete = []
        for key in db.keys():
            share = db[key]
            if isinstance(share, dict) and 'created_at' in share:
                if time.time() - share['created_at'] > 30 * 86400:
                    keys_to_delete.append(key)
        
        for key in keys_to_delete:
            del db[key]
        
        db.sync()
        return len(keys_to_delete)
```

### ✅ AFTER (Built-in cleanup)
```python
from storage_service import get_share_storage

storage = get_share_storage()

def cleanup_old_shares():
    return storage.cleanup_expired(
        ttl_field='created_at',
        max_age_seconds=30 * 86400
    )
```

**Savings**: 13 lines → 5 lines

---

## Pattern 5: Bulk Operations

### ❌ BEFORE (Manual context management)
```python
import shelve

def batch_save_stats(stats_dict):
    with shelve.open('/home/user/GiftWise/data/site_stats.db') as db:
        for key, value in stats_dict.items():
            db[key] = value
        db.sync()
```

### ✅ AFTER (Context manager)
```python
from storage_service import get_stats_storage

storage = get_stats_storage()

def batch_save_stats(stats_dict):
    with storage.open_db() as db:
        for key, value in stats_dict.items():
            db[key] = value
        db.sync()
```

**Alternative (individual sets - cleaner but slightly slower):**
```python
def batch_save_stats(stats_dict):
    for key, value in stats_dict.items():
        storage.set(key, value)
```

---

## Pattern 6: Safe Operations (Never Crash)

### ❌ BEFORE (No error handling)
```python
import shelve

def get_user_safe(user_id):
    try:
        with shelve.open('/home/user/GiftWise/data/users.db') as db:
            return db.get(user_id, {})
    except Exception as e:
        print(f"Error: {e}")
        return {}
```

### ✅ AFTER (Built-in safe operations)
```python
from storage_service import get_user_storage

storage = get_user_storage()

def get_user_safe(user_id):
    return storage.safe_get(user_id, default={})
```

**Bonus**: Errors automatically logged with context

---

## Pattern 7: Check Existence

### ❌ BEFORE (Manual check)
```python
import shelve

def has_referral_code(code):
    with shelve.open('/home/user/GiftWise/data/referral_codes.db') as db:
        return code in db
```

### ✅ AFTER (Built-in exists)
```python
from storage_service import get_referral_storage

storage = get_referral_storage()

def has_referral_code(code):
    return storage.exists(code)
```

---

## Pattern 8: Thread Safety

### ❌ BEFORE (Not thread-safe!)
```python
import shelve

# Multiple threads calling this = race condition!
def increment_views():
    with shelve.open('/home/user/GiftWise/data/site_stats.db') as db:
        stats = db.get('stats', {})
        stats['views'] = stats.get('views', 0) + 1
        db['stats'] = stats
        db.sync()
```

### ✅ AFTER (Thread-safe by default)
```python
from storage_service import get_stats_storage

storage = get_stats_storage()

# Safe for concurrent access!
def increment_views():
    storage.increment('stats', 'views')
```

**Why it's safe**: StorageService uses RLock internally

---

## Summary: Code Reduction

| Pattern | Before Lines | After Lines | Savings |
|---------|--------------|-------------|---------|
| Simple Get/Set | 8 | 2 | 75% |
| Counter/Increment | 6 | 1 | 83% |
| Dict Update | 5 | 1 | 80% |
| TTL Cleanup | 13 | 5 | 62% |
| Thread Safety | 6 + locks | 1 | Built-in |

**Total across 7 files**: Estimated 50-100 lines of boilerplate eliminated

---

## Migration Checklist

For each file you migrate:

1. [ ] Import storage factory function
2. [ ] Create module-level storage instance
3. [ ] Replace `shelve.open()` calls with storage methods
4. [ ] Remove `db.sync()` calls (automatic)
5. [ ] Remove `shelve` import if no longer needed
6. [ ] Test functionality
7. [ ] Check logs for any storage errors

---

## Testing Your Migration

```python
# Quick smoke test
def test_storage_migration():
    from storage_service import get_share_storage
    
    storage = get_share_storage()
    
    # Test set/get
    storage.set('test_key', {'test': True})
    assert storage.get('test_key')['test'] == True
    
    # Test update
    storage.update('test_key', {'new_field': 'value'})
    assert storage.get('test_key')['new_field'] == 'value'
    
    # Test delete
    storage.delete('test_key')
    assert not storage.exists('test_key')
    
    print("✅ Migration working correctly!")

test_storage_migration()
```
