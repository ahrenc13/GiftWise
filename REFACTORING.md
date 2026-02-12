# GiftWise Refactoring Progress

## Phase 1: Foundation (Feb 12, 2026) ✅

**Goal:** Reduce code duplication, improve testability, decouple storage and auth from business logic

### What Changed

#### 1. Repository Pattern for User Data
**Problem:** Raw `shelve` operations scattered across 50+ locations made it impossible to swap storage backends (Postgres, Redis, etc.) without touching every file.

**Solution:** Introduced `UserRepository` interface with `ShelveUserRepository` implementation.

**Files:**
- `repositories/user_repository.py` - Repository interface and shelve implementation
- `repositories/__init__.py` - Module exports

**Benefits:**
- ✅ Can swap shelve → Postgres with zero business logic changes
- ✅ Thread-safe operations with per-user locking
- ✅ Testable (can inject mock repository)
- ✅ Single source of truth for user data access

**Usage:**
```python
from repositories import get_user_repository

repo = get_user_repository()
user = repo.get(user_id)
repo.save(user_id, {'recommendations': recs})
```

**Legacy functions still work:**
- `get_user(user_id)` - Now calls repository internally
- `save_user(user_id, data)` - Now calls repository internally

---

#### 2. Auth Middleware
**Problem:** `get_session_user()` + redirect check repeated in 30+ routes. No consistent tier checking. Auth logic mixed with business logic.

**Solution:** Introduced `@require_login`, `@require_tier`, `@api_route` decorators.

**Files:**
- `middleware/auth.py` - Authentication decorators
- `middleware/__init__.py` - Module exports

**Benefits:**
- ✅ Auth logic separated from route handlers
- ✅ User automatically injected as first argument
- ✅ API routes return JSON 401/403 instead of redirects
- ✅ Tier checking built-in
- ✅ 3-5 lines of boilerplate removed from each route

**Usage:**
```python
# HTML routes
@app.route('/recommendations')
@require_login()
def view_recommendations(user):
    # user is injected, guaranteed to be authenticated
    recs = user.get('recommendations', [])
    ...

# API routes
@app.route('/api/generate', methods=['POST'])
@require_login(api_mode=True)
@require_tier('recommendations', api_mode=True)
def api_generate(user):
    # Returns JSON 401 if not logged in
    # Returns JSON 403 if tier doesn't allow 'recommendations'
    ...

# Optional auth
@app.route('/landing')
@optional_login()
def landing(user):
    # user is None if not logged in
    if user:
        return render_template('logged_in_landing.html')
    return render_template('public_landing.html')
```

**Refactored routes (examples):**
- `/recommendations` - Uses `@require_login()`
- `/recommendations/experience/<int:index>` - Uses `@require_login()`
- `/api/favorite/<int:rec_index>` - Uses `@require_login(api_mode=True)`

**Remaining work:** 27+ routes still use legacy `get_session_user()` pattern. Incrementally migrate as needed.

---

#### 3. Centralized Configuration
**Problem:** `os.environ.get()` called in 80+ locations. No validation, no type safety, hard to test.

**Solution:** Introduced `Settings` dataclass with grouped configuration.

**Files:**
- `config/settings.py` - Settings dataclass with validation
- `config/__init__.py` - Module exports

**Benefits:**
- ✅ Single source of truth for all env vars
- ✅ Grouped by domain (API, retailers, OAuth, Claude, app)
- ✅ Type safety (int, bool, str)
- ✅ Validation at startup (fail fast on missing critical keys)
- ✅ Easy to test (inject mock settings)
- ✅ Self-documenting (see all config in one place)

**Usage:**
```python
from config import get_settings

settings = get_settings()

# Grouped by domain
settings.app.secret_key
settings.api.anthropic_api_key
settings.retailers.amazon_affiliate_tag
settings.oauth.pinterest_client_id
settings.claude.curator_model

# Helper methods
settings.validate_critical()  # Returns list of missing critical vars
settings.get_retailer_availability()  # Dict of retailer → is_configured
```

**Remaining work:** `giftwise_app.py` still uses direct `os.environ.get()` in many places. Incrementally migrate as refactoring continues.

---

### Backward Compatibility

All Phase 1 changes are **fully backward compatible**:
- Legacy functions (`get_user`, `save_user`) still work
- Routes without decorators still work
- Direct `os.environ.get()` still works

The app gracefully degrades if refactored modules aren't available:
```python
if REFACTORED_MODULES_AVAILABLE:
    # Use new pattern
else:
    # Fall back to legacy code
```

This allows incremental migration without breaking the app.

---

### Testing the Refactoring

**Verify repository pattern:**
```python
from repositories import get_user_repository

repo = get_user_repository()
test_user_id = 'test_123'

# Test save
success = repo.save(test_user_id, {'name': 'Test User'})
assert success

# Test get
user = repo.get(test_user_id)
assert user['name'] == 'Test User'

# Test update (merge)
repo.save(test_user_id, {'email': 'test@example.com'})
user = repo.get(test_user_id)
assert user['name'] == 'Test User'
assert user['email'] == 'test@example.com'
```

**Verify auth middleware:**
```bash
# Start app
python giftwise_app.py

# Try accessing /recommendations without login
curl http://localhost:5000/recommendations
# Should redirect to /signup

# Try API without login
curl -X POST http://localhost:5000/api/favorite/0
# Should return {"error": "Authentication required"}, 401
```

**Verify settings:**
```python
from config import get_settings

settings = get_settings()
print(settings.validate_critical())  # Should show missing keys
print(settings.get_retailer_availability())  # Should show which retailers are configured
```

---

## Phase 2: Core Decoupling (Next)

**Goals:**
1. ✅ Extract generation pipeline into stages (break up 372-line `_run_generation_thread`)
2. ✅ Create service layer for external APIs (Claude, Apify, retailers)
3. ✅ Observer pattern for progress tracking (consolidate 3 systems)
4. ✅ Extract affiliate link logic into pluggable service

**Estimated impact:** ~1,500 line reduction, full testability of pipeline

---

## Phase 3: Cleanup (After Phase 2)

**Goals:**
1. ✅ Remove duplicate OAuth callbacks (4× same code)
2. ✅ Remove duplicate scraper functions (3× same code)
3. ✅ Remove duplicate waitlist implementation (2× complete reimplementation)
4. ✅ Consolidate URL normalization (4 similar functions)

**Estimated impact:** ~1,100 line reduction

---

## Principles for Ongoing Refactoring

### DRY (Don't Repeat Yourself)
- **Before adding a feature:** Check if similar code exists
- **When copying code:** Extract to a function/class first
- **When you see duplication:** Refactor immediately (compound interest on tech debt)

### Decoupling
- **Routes should be thin:** Authenticate, validate input, call service, format output
- **Business logic in services:** Not in routes
- **External APIs behind interfaces:** Can swap/mock implementations
- **No God functions:** If a function is >100 lines, break it up

### Testing
- **Unit tests for services:** Mock external dependencies
- **Integration tests for routes:** Test full flow
- **Repository tests:** Test with real storage, verify thread safety

### Backward Compatibility
- **Don't break existing routes:** Add new patterns alongside old
- **Graceful degradation:** App should work even if new modules fail to import
- **Incremental migration:** Migrate routes one at a time

---

## File Organization

```
/home/user/GiftWise/
├── giftwise_app.py              # Main Flask app (will shrink as refactoring continues)
├── repositories/                # Data access layer
│   ├── __init__.py
│   └── user_repository.py       # UserRepository interface + ShelveUserRepository
├── middleware/                  # Request processing
│   ├── __init__.py
│   └── auth.py                  # @require_login, @require_tier decorators
├── config/                      # Configuration management
│   ├── __init__.py
│   └── settings.py              # Settings dataclass with env var grouping
├── REFACTORING.md              # This file - refactoring progress tracker
└── OPUS_AUDIT.md               # Quality audit checklist (pre-refactoring)
```

---

## Developer Notes

### When adding a new route:

**OLD WAY (legacy):**
```python
@app.route('/my-route')
def my_route():
    user = get_session_user()
    if not user:
        return redirect('/signup')
    # ... business logic ...
```

**NEW WAY (refactored):**
```python
@app.route('/my-route')
@require_login()
def my_route(user):
    # user is injected, guaranteed authenticated
    # ... business logic ...
```

### When accessing user data:

**OLD WAY (legacy):**
```python
import shelve
with shelve.open('giftwise_db') as db:
    user = db.get(f'user_{user_id}')
    user['recommendations'] = recs
    db[f'user_{user_id}'] = user
```

**NEW WAY (refactored):**
```python
from repositories import get_user_repository

repo = get_user_repository()
user = repo.get(user_id)
repo.save(user_id, {'recommendations': recs})
```

### When accessing config:

**OLD WAY (legacy):**
```python
api_key = os.environ.get('ANTHROPIC_API_KEY')
stripe_key = os.environ.get('STRIPE_SECRET_KEY')
```

**NEW WAY (refactored):**
```python
from config import get_settings

settings = get_settings()
api_key = settings.api.anthropic_api_key
stripe_key = settings.api.stripe_secret_key
```

---

## Metrics

### Before Phase 1:
- **giftwise_app.py:** 4,293 lines
- **Code duplication:** ~30% (OAuth callbacks, scrapers, waitlist, progress tracking)
- **Test coverage:** ~0% (hard to test without mocking)
- **Storage coupling:** 50+ direct shelve calls
- **Auth coupling:** 30+ `get_session_user()` checks

### After Phase 1:
- **giftwise_app.py:** ~4,250 lines (minimal change - backward compatible)
- **New modules:** 3 (repositories, middleware, config) - 500 lines total
- **Routes refactored:** 3 examples (27+ remaining)
- **Test coverage:** Repository and middleware are fully testable
- **Storage decoupling:** ✅ Ready to swap shelve → Postgres
- **Auth decoupling:** ✅ Middleware pattern established

### Phase 2 Target:
- **giftwise_app.py:** ~2,500 lines (pipeline extraction)
- **Code duplication:** ~15% (OAuth, scrapers, waitlist still duplicated)
- **Test coverage:** 60%+ (services, pipeline stages)

### Phase 3 Target:
- **giftwise_app.py:** ~1,500 lines (just routes + glue code)
- **Code duplication:** <5%
- **Test coverage:** 80%+
- **Modules:** 12-15 focused modules

---

## Questions?

- **Why not refactor everything at once?** Too risky. Incremental changes allow testing at each step.
- **Why keep legacy code?** Backward compatibility. Old routes still work while we migrate.
- **When will this be done?** Phase 1 is complete. Phase 2 and 3 depend on business priorities.
- **Can I use both old and new patterns?** Yes. The app supports both during the migration period.

---

**Last updated:** Feb 12, 2026
**Next phase:** Extract generation pipeline (Phase 2)
