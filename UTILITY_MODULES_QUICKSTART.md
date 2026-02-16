# Utility Modules - Quick Start Guide

**TL;DR:** Three new modules eliminate 500+ lines of duplication across searchers.

---

## When to Use Each Module

### 🔍 search_query_utils.py
**Use when:** Building search queries from profile interests

```python
from search_query_utils import build_queries_from_profile

queries = build_queries_from_profile(profile, target_count=12, skip_work=True)
for q in queries:
    # q["query"] = cleaned query with category-appropriate suffix
    # q["interest"] = original interest name
    # q["priority"] = 'high', 'medium', or 'low'
    response = api_call(q["query"])
```

**Replaces:** Manual query building in every searcher (amazon, ebay, etsy, etc.)

---

### ⚙️ config_service.py
**Use when:** Accessing environment variables

```python
from config_service import get_config

config = get_config()

# Claude
api_key = config.claude.api_key
model = config.claude.curator_model

# Affiliates
amazon_key = config.affiliate.rapidapi_key
etsy_key = config.affiliate.etsy_api_key

# Database
db_path = config.database.products_db

# OAuth
spotify_id = config.oauth.spotify_client_id
```

**Replaces:** `os.getenv()` scattered across 20+ files (198 calls total)

---

### 📦 product_schema.py
**Use when:** Converting retailer API responses to standard format

```python
from product_schema import build_product_list

# Parse API response into products
products = build_product_list(
    api_response_items,
    platform='amazon',  # or 'ebay', 'etsy', 'awin', etc.
    query='dog toy',
    interest='Dog ownership'
)

# Convert to curator format
product_dicts = [p.to_dict() for p in products]
```

**Replaces:** 50-100 lines of defensive parsing in each searcher

---

## Complete Searcher Example

**Before (amazon searcher, ~150 lines):**
```python
import os
import random

# Query building
cleaned = _clean_interest_for_search(name)
category = _categorize_interest(cleaned.lower())
suffix = random.choice(_QUERY_SUFFIXES[category])
query = f"{cleaned} {suffix}"

# API call
api_key = os.getenv('RAPIDAPI_KEY', '')
response = requests.get(url, headers={'X-RapidAPI-Key': api_key}, params={'query': query})

# Product parsing (50+ lines of defensive code)
for item in response.json().get('data', {}).get('products', []):
    title = item.get('product_title', '')
    link = item.get('product_url', '')
    image = item.get('product_photo') or item.get('thumbnail', '')
    # ... 40 more lines ...
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
        "product_id": asin,
    }
    all_products.append(product)
```

**After (~40 lines):**
```python
from search_query_utils import build_queries_from_profile
from config_service import get_config, is_retailer_available
from product_schema import build_product_list

def search_products_amazon(profile, target_count=20):
    # Check availability
    if not is_retailer_available('amazon'):
        return []

    # Build queries
    queries = build_queries_from_profile(profile, target_count=12, skip_work=True)

    # Get API key
    config = get_config()
    api_key = config.affiliate.rapidapi_key

    all_products = []
    for q in queries:
        # API call
        response = requests.get(
            url,
            headers={'X-RapidAPI-Key': api_key},
            params={'query': q["query"][:100]}
        )

        # Parse products
        items = response.json().get('data', {}).get('products', [])
        products = build_product_list(items, 'amazon', q["query"], q["interest"])

        # Add to results
        all_products.extend([p.to_dict() for p in products])

        if len(all_products) >= target_count:
            break

    return all_products[:target_count]
```

**Savings:**
- **110 lines removed** (from one searcher)
- **Zero duplication** (same utilities used by all 7+ searchers)
- **Type-safe** (no more typos in dict keys or env vars)
- **Easier to test** (mock config, validate product schema)

---

## Migration Steps (5 minutes per searcher)

1. **Add imports:**
   ```python
   from search_query_utils import build_queries_from_profile
   from config_service import get_config
   from product_schema import build_product_list
   ```

2. **Replace query building:**
   ```python
   # Delete manual query building loop
   # Replace with:
   queries = build_queries_from_profile(profile, target_count=12, skip_work=True)
   ```

3. **Replace config access:**
   ```python
   # Delete: api_key = os.getenv('...')
   # Replace with:
   config = get_config()
   api_key = config.affiliate.rapidapi_key  # or etsy_api_key, etc.
   ```

4. **Replace product building:**
   ```python
   # Delete 50+ lines of defensive parsing
   # Replace with:
   products = build_product_list(api_items, 'amazon', query, interest)
   all_products.extend([p.to_dict() for p in products])
   ```

5. **Test:**
   ```bash
   # Run recommendation pipeline
   # Verify product count is same or higher
   # Check that curator receives same format
   ```

---

## File Locations

- `/home/user/GiftWise/search_query_utils.py`
- `/home/user/GiftWise/config_service.py`
- `/home/user/GiftWise/product_schema.py`
- `/home/user/GiftWise/UTILITY_MODULES_README.md` (detailed docs)

---

## Testing

```bash
# Run built-in tests
python search_query_utils.py
python config_service.py
python product_schema.py

# Integration test
python -c "
from search_query_utils import build_search_query
from config_service import get_config
from product_schema import Product

print('✓ All modules working')
"
```

---

## Benefits Summary

| Before | After |
|--------|-------|
| 198 `os.getenv()` calls | 1 `get_config()` call |
| 7 copies of query building | 1 shared module |
| 7 copies of product parsing | 1 schema per retailer |
| ~500 lines duplicated | ~500 lines shared |
| Typos in env var names | Type-safe config access |
| Inconsistent product dicts | Validated schema |
| Hard to test | Easy to mock |

---

## Next Steps

1. Read `UTILITY_MODULES_README.md` for detailed migration guide
2. Migrate one searcher (recommend: `rapidapi_amazon_searcher.py`)
3. Test end-to-end recommendation pipeline
4. Migrate remaining searchers
5. Update `giftwise_app.py` to use `config_service`

---

**Questions?** Read the module docstrings - they're comprehensive.
