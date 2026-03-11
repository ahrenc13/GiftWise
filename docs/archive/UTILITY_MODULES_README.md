# Utility Modules - Migration Guide

**Date:** February 16, 2026
**Purpose:** Three core utility modules that eliminate duplication and improve code quality

---

## Overview

Three new utility modules have been created to centralize common patterns:

1. **`search_query_utils.py`** - Query building for all retailer searchers
2. **`config_service.py`** - Centralized environment variable management
3. **`product_schema.py`** - Standardized product representation

---

## Module 1: search_query_utils.py

### Purpose
Removes eBay→Amazon coupling (anti-pattern) and provides shared query-building logic for all searcher modules.

### What it does
- Cleans interest names (removes filler like "fandom", "ownership and care")
- Detects categories (music, sports, travel, etc.)
- Builds optimized search queries with category-appropriate suffixes
- Enforces max query length (prevents API errors)

### Key Functions

```python
from search_query_utils import (
    clean_interest_for_search,
    categorize_interest,
    build_search_query,
    build_queries_from_profile,
)

# Clean interest name
clean_name = clean_interest_for_search("Dog ownership and care")
# → "Dog"

# Build single query
query = build_search_query("Taylor Swift fandom", intensity="passionate")
# → "Taylor Swift poster"

# Build all queries from profile (recommended)
queries = build_queries_from_profile(profile, target_count=12, skip_work=True)
# Returns list of dicts: [{"query": "...", "interest": "...", "priority": "high"}, ...]
```

### Migration for Searchers

**rapidapi_amazon_searcher.py:**
```python
# BEFORE (lines 18, 114-123):
try:
    from rapidapi_amazon_searcher import _clean_interest_for_search, _categorize_interest, _QUERY_SUFFIXES
except ImportError:
    # fallback...

cleaned = _clean_interest_for_search(name)
category = _categorize_interest(cleaned.lower())
suffix = random.choice(_QUERY_SUFFIXES[category])
query = f"{cleaned} {suffix}"

# AFTER:
from search_query_utils import build_queries_from_profile

# Option 1: Use batch builder (recommended)
queries = build_queries_from_profile(profile, target_count=12, skip_work=True)
for q in queries:
    query = q["query"]
    interest = q["interest"]
    priority = q["priority"]
    # ... make API call

# Option 2: Build individual queries
from search_query_utils import build_search_query
query = build_search_query(name, intensity=interest.get("intensity", "medium"))
```

**ebay_searcher.py:**
```python
# BEFORE (lines 18-25):
try:
    from rapidapi_amazon_searcher import _clean_interest_for_search, _categorize_interest, _QUERY_SUFFIXES
except ImportError:
    def _clean_interest_for_search(name):
        return name
    # ... fallbacks

# AFTER:
from search_query_utils import build_queries_from_profile

queries = build_queries_from_profile(profile, target_count=10, skip_work=True)
```

**Benefits:**
- No more sibling dependencies (eBay importing from Amazon)
- When CJ/Skimlinks need query building, they use the same shared module
- Easier to test and improve query building logic
- Consistent query format across all retailers

---

## Module 2: config_service.py

### Purpose
Centralizes all 198 `os.getenv()` calls scattered across 20+ files. Provides type-safe, validated configuration.

### What it does
- Loads all env vars once at startup
- Validates required credentials
- Provides nested, type-safe config object
- Logs configuration status for debugging

### Key Functions

```python
from config_service import get_config, is_retailer_available, get_claude_model

# Get singleton config instance
config = get_config()  # Loads once, caches forever

# Access Claude config
api_key = config.claude.api_key
profile_model = config.claude.profile_model
curator_model = config.claude.curator_model

# Access affiliate credentials
amazon_key = config.affiliate.rapidapi_key
amazon_tag = config.affiliate.amazon_affiliate_tag
etsy_key = config.affiliate.etsy_api_key
awin_key = config.affiliate.awin_data_feed_api_key

# Database paths
products_db = config.database.products_db
users_db = config.database.users_db

# OAuth credentials
spotify_id = config.oauth.spotify_client_id
spotify_secret = config.oauth.spotify_client_secret

# App settings
environment = config.environment  # 'development' or 'production'
debug = config.debug
admin_key = config.admin_dashboard_key

# Convenience helpers
if is_retailer_available('etsy'):
    # Etsy is configured
    pass

model = get_claude_model('curator')  # or 'profile'
```

### Migration Examples

**profile_analyzer.py:**
```python
# BEFORE:
import os
client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
model_name = os.environ.get('CLAUDE_PROFILE_MODEL', 'claude-sonnet-4-20250514')

# AFTER:
from config_service import get_config
config = get_config()
client = anthropic.Anthropic(api_key=config.claude.api_key)
model_name = config.claude.profile_model
```

**gift_curator.py:**
```python
# BEFORE:
import os
client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
model = os.environ.get('CLAUDE_CURATOR_MODEL', 'claude-sonnet-4-20250514')

# AFTER:
from config_service import get_config
config = get_config()
client = anthropic.Anthropic(api_key=config.claude.api_key)
model = config.claude.curator_model
```

**rapidapi_amazon_searcher.py:**
```python
# BEFORE:
def search_products_rapidapi_amazon(profile, api_key, target_count=20):
    if not (api_key and api_key.strip()):
        logger.warning("RapidAPI key not configured")
        return []

# AFTER:
from config_service import get_config, is_retailer_available

def search_products_rapidapi_amazon(profile, target_count=20):
    if not is_retailer_available('amazon'):
        logger.warning("Amazon not configured")
        return []

    config = get_config()
    api_key = config.affiliate.rapidapi_key
```

**database.py:**
```python
# BEFORE:
import os
DB_PATH = os.environ.get('DATABASE_PATH', '/home/user/GiftWise/data/products.db')

# AFTER:
from config_service import get_config
config = get_config()
DB_PATH = config.database.products_db
```

**Benefits:**
- Single source of truth for all configuration
- Validation happens once at startup (fail fast)
- Type-safe access (no typos in env var names)
- Easy to add new config (add to dataclass, not scattered getenv calls)
- Easy to mock for testing

---

## Module 3: product_schema.py

### Purpose
Standardizes product dict construction across 7+ searcher modules. Each retailer has different API formats - this normalizes them.

### What it does
- Provides `Product` dataclass with validation
- Builder functions for each retailer (Amazon, eBay, Etsy, Awin, Skimlinks, CJ)
- Auto-truncates titles to 200 chars
- Auto-generates product IDs if missing
- Includes commission rates for revenue optimization
- Batch building helper

### Key Functions

```python
from product_schema import Product, build_product_list

# Create from API response
product = Product.from_amazon(api_item, query="dog toy", interest="Dog")
product = Product.from_ebay(api_item, query="hiking gear", interest="Hiking")
product = Product.from_etsy(api_item, query="necklace", interest="Jewelry")

# Convert to dict for curator (backward compatible)
product_dict = product.to_dict()

# Batch building (recommended)
products = build_product_list(api_items, platform='amazon', query='coffee', interest='Coffee')
product_dicts = [p.to_dict() for p in products]
```

### Migration for Searchers

**rapidapi_amazon_searcher.py:**
```python
# BEFORE (lines 177-227):
for item in products_list:
    # ... lots of defensive parsing for title, link, image, price
    product = {
        "title": title[:200],
        "link": link,
        "snippet": title[:100],
        "image": image,
        "thumbnail": image,
        "image_url": image,
        "source_domain": "amazon.com",
        "search_query": query,
        "interest_match": interest,
        "priority": priority,
        "price": price or "",
        "product_id": asin or str(hash(title + link))[:16],
    }
    all_products.append(product)

# AFTER:
from product_schema import build_product_list

# Option 1: Batch build (cleanest)
products = build_product_list(products_list, 'amazon', query, interest)
for product in products:
    if product.product_id and product.product_id in seen_asins:
        continue
    if product.product_id:
        seen_asins.add(product.product_id)
    all_products.append(product.to_dict())

# Option 2: Individual builds (more control)
from product_schema import Product

for item in products_list:
    try:
        product = Product.from_amazon(item, query, interest)
        if product.product_id in seen_asins:
            continue
        seen_asins.add(product.product_id)
        all_products.append(product.to_dict())
    except Exception as e:
        logger.warning(f"Failed to build product: {e}")
        continue
```

**ebay_searcher.py:**
```python
# BEFORE (lines ~70-120):
# Defensive parsing of eBay response format
image_dict = item.get('image', {})
image_url = image_dict.get('imageUrl', '') if isinstance(image_dict, dict) else ''
# ... more parsing
product = {
    "title": title[:200],
    "link": link,
    # ... etc
}

# AFTER:
from product_schema import build_product_list

products = build_product_list(items, 'ebay', query, interest)
all_products.extend([p.to_dict() for p in products])
```

**etsy_searcher.py:**
```python
# BEFORE:
images = result.get('Images', [])
image_url = ''
if images and len(images) > 0:
    image_url = images[0].get('url_570xN', '')
# ... more parsing

# AFTER:
from product_schema import build_product_list

products = build_product_list(results, 'etsy', query, interest)
all_products.extend([p.to_dict() for p in products])
```

**awin_searcher.py:**
```python
# BEFORE:
# Custom CSV parsing, field extraction
link = _ci_get(row, 'aw_deep_link', 'merchant_deep_link')
# ... 50+ lines of parsing

# AFTER:
from product_schema import build_product_list

# Convert CSV rows to dicts (keep existing parsing)
# Then use Product builder for normalization
products = build_product_list(csv_rows, 'awin', query, interest)
```

**Benefits:**
- Consistent product schema across all retailers
- Validation and normalization handled automatically
- Commission rates included for revenue optimizer
- Easier to add new retailers (implement one builder function)
- Graceful error handling (failed products logged but don't crash batch)

---

## Testing

All three modules have comprehensive test suites:

```bash
# Test search query utils
python search_query_utils.py

# Test config service
python config_service.py

# Test product schema
python product_schema.py
```

---

## Migration Priority

### Phase 1: Low Risk (No Behavioral Change)
1. Adopt `config_service.py` in new code
2. Test `product_schema.py` with one searcher (amazon)
3. Verify backward compatibility

### Phase 2: Gradual Rollout
1. Migrate `rapidapi_amazon_searcher.py` to use all 3 modules
2. Migrate `ebay_searcher.py`
3. Migrate `etsy_searcher.py`

### Phase 3: Full Adoption
1. Update remaining searchers (awin, skimlinks, cj)
2. Update main app (`giftwise_app.py`) to use `config_service`
3. Remove old `config.py` and `config/settings.py`

---

## Backward Compatibility

All modules are designed for gradual migration:

- **search_query_utils.py:** eBay searcher already imports from Amazon (works now)
- **config_service.py:** Doesn't interfere with `os.getenv()` calls (can coexist)
- **product_schema.py:** `.to_dict()` returns exact format curator expects

No breaking changes required. Each searcher can migrate independently.

---

## Testing Checklist

Before deploying searcher changes:

- [ ] Test that queries are built correctly (`build_queries_from_profile()`)
- [ ] Test that products parse correctly (`build_product_list()`)
- [ ] Test that curator receives same dict format (`.to_dict()`)
- [ ] Test error handling (malformed API responses)
- [ ] Compare product count before/after (should be same or higher)
- [ ] Verify no regression in recommendation quality

---

## Questions?

These modules are production-ready with:
- Comprehensive docstrings
- Error handling
- Built-in test suites
- Migration examples
- Backward compatibility

Read the module source for detailed documentation.
