# Service Modules Documentation
**Generated:** February 16, 2026

## Overview
This documentation describes the two new service modules that orchestrate GiftWise's recommendation generation pipeline.

---

## `progress_service.py`

### Purpose
Centralized, thread-safe progress tracking for background jobs.

### Main Class: `ProgressTracker`

#### Constructor
```python
ProgressTracker(storage: Optional[Dict] = None)
```
- **storage**: Dict-like object for storing progress (defaults to new dict)
- Can use in-memory dict or shelve for persistence

#### Methods

##### `set_progress(user_id, stage=None, stage_label=None, **kwargs)`
Update progress for a user.
- **user_id**: Unique user identifier
- **stage**: Pipeline stage (e.g., 'profile_analysis', 'searching_retailers')
- **stage_label**: Human-readable description
- **kwargs**: Additional data (interests, retailers, product_count, etc.)

##### `get_progress(user_id) -> Dict`
Get current progress for a user. Returns default state if user not found.

##### `mark_complete(user_id, success, error=None, **data)`
Mark a job as complete.
- **success**: Whether generation succeeded
- **error**: Optional error message if failed
- **data**: Additional completion data (recommendations, etc.)

##### `clear_progress(user_id)`
Remove progress tracking for a user.

##### `update_retailer_progress(user_id, retailer, status, count=0)`
Update progress for a specific retailer search.
- **retailer**: Name (e.g., 'Amazon', 'Etsy', 'eBay')
- **status**: 'searching', 'done', or 'skipped'
- **count**: Number of products found

#### Usage Example
```python
from progress_service import ProgressTracker

tracker = ProgressTracker(storage_dict)
tracker.set_progress('user_123', stage='searching', stage_label='Searching stores...')
tracker.update_retailer_progress('user_123', 'Amazon', 'done', count=20)
progress = tracker.get_progress('user_123')
tracker.mark_complete('user_123', success=True, recommendations=[...])
```

---

## `recommendation_service.py`

### Purpose
Orchestrates the full 8-step gift recommendation generation pipeline.

### Main Class: `RecommendationService`

#### Constructor
```python
RecommendationService(
    app_context,
    claude_client,
    models_config: Dict[str, str],
    progress_callback: Optional[Callable] = None
)
```
- **app_context**: Flask application context
- **claude_client**: Anthropic Claude API client
- **models_config**: Dict with 'profile' and 'curator' model names
- **progress_callback**: Optional callback(stage, stage_label, **kwargs)

#### Main Method

##### `generate_recommendations(...) -> List[Dict]`
Generates personalized gift recommendations through 8-step pipeline.

**Parameters:**
- **user_id**: Unique user identifier
- **user**: User data dict
- **platforms**: List of connected social platforms
- **recipient_type**: 'self' or 'other'
- **relationship**: Relationship type (e.g., 'close_friend')
- **approved_profile**: Optional pre-approved profile
- **enriched_profile**: Optional pre-enriched profile
- **enhanced_search_terms**: Optional pre-computed search terms
- **quality_filters**: Optional quality filters
- **recipient_age**: Optional recipient age
- **recipient_gender**: Optional recipient gender

**Returns:** List of recommendation dicts with keys:
- name, description, why_perfect
- price_range, where_to_buy
- product_url, purchase_link, image_url
- gift_type ('physical' or 'experience')
- confidence_level, interest_match
- (and more for experiences: materials_needed, is_bookable, is_diy, etc.)

**Raises:**
- `ValueError`: If profile building fails or no products found

#### Pipeline Steps (Internal Methods)

1. **`_build_profile()`** - Build or use approved recipient profile
2. **`_enrich_profile()`** - Enrich with intelligence layer
3. **`_search_products()`** - Search multi-retailer inventory
4. **`_apply_filters()`** - Apply quality and smart filters
5. **`_curate_gifts()`** - AI-powered gift curation
6. **`_cleanup_curation()`** - Post-curation cleanup & validation
7. **`_build_recommendations()`** - Format final recommendations
8. **`_process_images()`** - Backfill and validate images

#### Helper Methods

- `_optimize_product_selection()` - Revenue optimization pre-filtering
- `_track_recommendations()` - Track for learning loop
- `_get_regional_intelligence()` - Get regional context & local events
- `_build_experience_description()` - Build experience descriptions
- `_validate_or_replace_experience_link()` - Validate/replace experience URLs
- `_get_provider_links()` - Get curated provider links
- `_apply_affiliate_tag()` - Apply affiliate tracking
- `_validate_experience_url()` - Validate experience URL
- `_make_experience_search_link()` - Generate Google search link
- `_backfill_materials_links()` - Match materials to products

#### Usage Example
```python
from recommendation_service import RecommendationService
from progress_service import ProgressTracker

tracker = ProgressTracker(storage)
service = RecommendationService(
    app_context=app,
    claude_client=claude,
    models_config={'profile': 'claude-sonnet-4', 'curator': 'claude-sonnet-4'},
    progress_callback=lambda s, l, **kw: tracker.set_progress(user_id, s, l, **kw)
)

recommendations = service.generate_recommendations(
    user_id='user_123',
    user={...},
    platforms=[...],
    recipient_type='other',
    relationship='close_friend',
    ...
)
```

---

## Integration with `giftwise_app.py`

The main app now uses these services in `_run_generation_thread()`:

```python
def _run_generation_thread(user_id, user, platforms, ...):
    """Thin wrapper that delegates to services."""
    try:
        with app.app_context():
            # Initialize services
            tracker = ProgressTracker(_generation_progress)
            service = RecommendationService(
                app_context=app,
                claude_client=claude_client,
                models_config={'profile': MODEL1, 'curator': MODEL2},
                progress_callback=lambda s, l, **kw: tracker.set_progress(user_id, s, l, **kw)
            )
            
            # Generate recommendations
            recommendations = service.generate_recommendations(...)
            
            # Save to database
            save_user(user_id, {'recommendations': recommendations, ...})
            track_event('rec_run')
            tracker.set_progress(user_id, complete=True, success=True)
            
    except ValueError as e:
        tracker.set_progress(user_id, complete=True, success=False, error=str(e))
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        tracker.set_progress(user_id, complete=True, success=False, error='Unexpected error')
```

---

## Benefits

### For Development
- **Testability**: Each service can be tested in isolation
- **Maintainability**: Logic changes in ONE place (service)
- **Readability**: Clear separation of concerns
- **Reusability**: ProgressTracker works for ANY background job

### For Code Quality
- **Single Responsibility**: Each class does ONE thing
- **Dependency Injection**: Services receive dependencies via constructor
- **Graceful Degradation**: Optional modules with fallbacks
- **Error Handling**: Clear ValueError vs Exception distinction

### For Future Work
- Easy to add metrics/monitoring for each pipeline step
- Easy to add unit tests for each method
- Easy to swap implementations (e.g., different storage backends)
- Easy to extend with new pipeline steps

---

## Testing Recommendations

### Unit Tests
```python
# Test progress tracker
def test_progress_tracker_thread_safety():
    tracker = ProgressTracker()
    # Test concurrent updates
    
def test_progress_tracker_default_state():
    tracker = ProgressTracker()
    assert tracker.get_progress('user_123')['stage'] == 'unknown'

# Test recommendation service
def test_build_profile_with_approved():
    service = RecommendationService(...)
    profile = service._build_profile(..., approved_profile={...})
    assert profile == approved_profile

def test_enrich_profile_fallback():
    service = RecommendationService(...)
    # Mock intelligence_layer_available = False
    enriched, terms, filters = service._enrich_profile(...)
    assert enriched is None
```

### Integration Tests
```python
def test_full_pipeline_e2e():
    tracker = ProgressTracker()
    service = RecommendationService(...)
    recommendations = service.generate_recommendations(...)
    assert len(recommendations) > 0
    assert all('name' in r for r in recommendations)
```

---

## Module Dependencies

### `progress_service.py`
- **Standard library**: threading, datetime, typing
- **No external dependencies**

### `recommendation_service.py`
- **Standard library**: os, logging, re, datetime, typing, urllib.parse
- **External dependencies**: None (all imports are optional with fallbacks)
- **Optional modules**:
  - profile_analyzer
  - multi_retailer_searcher
  - gift_curator
  - smart_filters
  - enrichment_engine
  - regional_culture, local_events
  - post_curation_cleanup
  - image_fetcher
  - link_validation
  - experience_providers
  - revenue_optimizer
  - url_utils

---

**Last Updated:** February 16, 2026  
**Author:** Chad + Claude  
**Version:** 1.0
