# Phase 4: Infrastructure Hardening - Research

**Researched:** 2026-04-02
**Domain:** Dead code removal (Skimlinks), in-flight duplicate prevention, rate limit architecture
**Confidence:** HIGH — all findings are from direct file reads with line numbers

---

## Summary

This phase has two independent plans. Plan 04-01 removes dead Skimlinks code — the service is defunct but references are scattered across more files than the task description implies (`giftwise_app.py`, `recommendation_service.py`, `multi_retailer_searcher.py`, `models.py`, `config.py`, `config_service.py`, `config/settings.py`, `revenue_optimizer.py`, `image_fetcher.py`, `product_schema.py`, `products/ingestion.py`, `base.html`). Plan 04-02 (in-flight dedup + rate limit verification) is largely ALREADY DONE — `profile_analyzer.py` already has a correct threading.Event-based in-flight dedup, and rate limiting already uses SQLite with WAL mode via `check_and_record_pipeline_run()`. The main work for 04-02 is verification and documentation, not fresh implementation.

**Primary recommendation:** 04-01 requires careful multi-file surgery. 04-02 is primarily a verification task — the mechanisms exist and appear correct.

---

## Plan 04-01: Skimlinks Dead Code Removal

### Q1: Does `skimlinks_searcher.py` exist? What does it contain?

**YES.** File: `/home/user/GiftWise/skimlinks_searcher.py` (262 lines)

**Contents:**
- Module docstring describing Skimlinks Product Key API v2
- Env vars expected: `SKIMLINKS_PUBLISHER_ID`, `SKIMLINKS_CLIENT_ID`, `SKIMLINKS_CLIENT_SECRET`, `SKIMLINKS_PUBLISHER_DOMAIN_ID`
- Module-level token cache globals: `_access_token`, `_token_expires`, `_TOKEN_BUFFER`
- **Functions:**
  - `_get_access_token(client_id, client_secret)` — OAuth2 client credentials flow against `authentication.skimapis.com`
  - `_search_products(publisher_id, domain_id, access_token, query, ...)` — GET against `products.skimapis.com/v2/publisher/{pub_id}/product`
  - `_extract_domain(url)` — utility, extracts domain from URL
  - `_parse_product(product_data, interest, query, priority)` — converts Skimlinks API response to standard product dict
  - `wrap_affiliate_link(url, publisher_id)` — wraps any URL with `go.skimresources.com/?id=...&url=...` redirect
  - `search_products_skimlinks(profile, publisher_id, client_id, client_secret, domain_id, ...)` — main entry point, builds search queries from profile interests and calls `_search_products` in a loop

**Imports in `skimlinks_searcher.py`:** `logging`, `re`, `time`, `requests`, `urllib.parse.quote` — all standard, no project-specific imports.

### Q2: Does `giftwise_app.py` import or reference `skimlinks_searcher`?

**NO direct import** of `skimlinks_searcher` module. No `import skimlinks_searcher` or `from skimlinks_searcher import` anywhere in `giftwise_app.py`.

**However, it has these Skimlinks references:**

| Line | Code |
|------|------|
| 466 | `SKIMLINKS_PUBLISHER_ID = os.environ.get('SKIMLINKS_PUBLISHER_ID', '')` |
| 3019 | Comment: `2. All merchant links: wrap with Skimlinks redirect if publisher ID is set` |
| 3031 | `# Step 2: Skimlinks server-side wrapping (when approved)` |
| 3032 | `if SKIMLINKS_PUBLISHER_ID and not url.startswith('https://go.skimresources.com'):` |
| 3033 | `url = f"https://go.skimresources.com/?id={SKIMLINKS_PUBLISHER_ID}&url={quote(url)}"` |

These are all inside the `_apply_affiliate_tag()` function (lines 3015–3035). The env var read (line 466) makes `SKIMLINKS_PUBLISHER_ID` a module-level constant.

### Q3: Which templates contain Skimlinks references?

Only **one template** has Skimlinks content:

**`/home/user/GiftWise/templates/base.html`**

| Line | Content |
|------|---------|
| 336 | `<!-- Skimlinks snippet - Publisher ID: 298548X178612 -->` |
| 337–346 | Full JS async loader block that fetches `https://s.skimresources.com/js/298548X178612.skimlinks.js` |
| 343 | `s.src = 'https://s.skimresources.com/js/298548X178612.skimlinks.js';` |

The JS snippet runs on **every page** served through `base.html` (which is extended by all pages). The publisher ID `298548X178612` is hardcoded in the JS src URL (not templated).

No other templates in `/home/user/GiftWise/templates/` matched the search patterns `skimlinks`, `publisher_id=298548X178612`, `skimresources`, `skimlinks.com`.

**Note:** `/home/user/GiftWise/scripts/convert_templates.py` (line 56–57) has a regex that strips Skimlinks scripts: `re.sub(r'<script[^>]*skimlinks[^>]*>.*?</script>', '', ...)` — this is a migration utility, not a live template.

### Q4: Other Python files importing from `skimlinks_searcher`?

Full list of Python files with Skimlinks references (besides `skimlinks_searcher.py` itself and `giftwise_app.py`):

| File | References |
|------|-----------|
| `multi_retailer_searcher.py` | Lines 47–50: 4 Skimlinks params in function signature; line 66: comment; line 77: logging; lines 301–315: conditional `_run_skimlinks()` closure that does `from skimlinks_searcher import search_products_skimlinks` at runtime |
| `recommendation_service.py` | Line 57: `self.skimlinks_publisher_id = os.environ.get('SKIMLINKS_PUBLISHER_ID', '')`; lines 362–365: passes 4 Skimlinks env vars to `search_all_retailers()`; lines 1204–1206: server-side URL wrapping logic (identical to giftwise_app.py version) |
| `models.py` | Line 32: string `'skimlinks'` in retailer type comment |
| `revenue_optimizer.py` | Line 30: `'skimlinks': 0.04` in commission rates dict |
| `image_fetcher.py` | Line 411: `'skimlinks'` in supported retailer list; line 441: `'skimlinks': _extract_skimlinks_image` in dispatcher dict; lines 559–580+: `_extract_skimlinks_image()` function |
| `product_schema.py` | Line 86: `'skimlinks': 0.03` commission rate; lines 419–463: `Product.from_skimlinks()` classmethod; lines 531, 553: `'skimlinks'` in platform list and dispatcher dict |
| `products/ingestion.py` | Lines 47–49: try/except import of `skimlinks_searcher`; lines 330–382: `refresh_skimlinks()` function; lines 451, 466, 509, 534, 554: `'skimlinks'` in retailer choices and result dicts |
| `config.py` | Lines 63–67: 4 Skimlinks env var reads; line 132: priority weight; line 379: product limit; lines 423–424: warning log; line 559: status print |
| `config_service.py` | Lines 107–111: 4 Skimlinks fields in dataclass; lines 151–155: 4 env var reads; line 182: `'skimlinks'` in available retailers check |
| `config/settings.py` | Lines 57–61: 4 Skimlinks fields; line 162: `'skimlinks'` in active retailers |
| `base_searcher.py` | Line 5: comment only |

**Runtime import location:** `multi_retailer_searcher.py` line 303 does `from skimlinks_searcher import search_products_skimlinks` inside a closure. This import only executes if `skimlinks_publisher_id` is truthy (line 301). Since `SKIMLINKS_PUBLISHER_ID` env var is not set in Railway (Skimlinks is defunct), this code path never runs in production.

---

## Plan 04-02: In-Flight Duplicate Prevention + Rate Limit Verification

### Q5: Where is the profile analysis Claude API call? Function name and line?

**Function:** `build_recipient_profile()` in `/home/user/GiftWise/profile_analyzer.py` (line 238)

**Called from `giftwise_app.py`:**
- Line 2905: `profile = build_recipient_profile(platforms, recipient_type, relationship, claude_client, model=CLAUDE_PROFILE_MODEL)`
  - This is inside the route that handles the profile review step (not the generate-recommendations route)

**Called from `recommendation_service.py`** as well — the service has its own call path via the pipeline.

### Q6: Is there an existing in-flight dict or lock mechanism?

**YES — fully implemented** in `/home/user/GiftWise/profile_analyzer.py`:

| Line | Code |
|------|------|
| 30–36 | Module docstring explaining the pattern + declarations |
| 35 | `_inflight_profiles = {}  # hash -> threading.Event` |
| 36 | `_inflight_lock = threading.Lock()` |
| 294–312 | Full in-flight check inside `build_recipient_profile()` |
| 295–301 | `with _inflight_lock:` block — checks if hash is already in-flight, registers a new Event if not |
| 304–312 | If event returned (another thread is working): `event.wait(timeout=120)`, then re-checks cache |
| 951–955 | Success path: `with _inflight_lock: event = _inflight_profiles.pop(profile_hash, None); if event: event.set()` |
| 962–966 | Exception path: same cleanup — pops and sets the event even on failure |

**The mechanism is correct and complete.** Thread A registers its hash, runs the Claude call. Thread B finds the hash, waits on the Event (up to 120s). When Thread A finishes (success or failure), it sets the event. Thread B wakes up, re-checks the cache, uses the result if found. If Thread A failed and didn't cache anything, Thread B logs a warning and proceeds with its own analysis (safe fallback).

**The CLAUDE.md note** ("Duplicate in-flight Claude API calls — two concurrent profile analysis requests for the same profile hash...") was written in March 2026 and has since been fixed. The fix is already merged.

### Q7: What is the profile hash variable called and where is it computed?

**Variable name:** `profile_hash`

**Computed in:** `/home/user/GiftWise/profile_analyzer.py`, inside `build_recipient_profile()`:

- Line 265: `profile_hash = None` (initialized)
- Line 275: `_PROMPT_VERSION = "2026-03-22-attribution-v5"` (local constant, NOT a module-level variable)
- Lines 276–285: `cache_data` dict built from all platform data + relationship + `_PROMPT_VERSION`
- Line 285: `cache_str = json.dumps(cache_data, sort_keys=True)`
- Line 286: `profile_hash = hashlib.sha256(cache_str.encode()).hexdigest()`

**Cache lookup:** Line 289: `cached_profile = database.get_cached_profile(profile_hash)`

**Note:** `_PROMPT_VERSION` is defined as a local variable inside the function, not at module level. The CLAUDE.md mentions it should be bumped when the analyzer prompt changes materially — this requires editing line 275.

### Q8: Where does rate limiting happen in `giftwise_app.py`? What backend?

**Rate limiting location in `giftwise_app.py`:**

| Line | Code |
|------|------|
| 98–99 | `# Rate limiting (1 full pipeline run per IP per 24 hours)` / `from database import check_and_record_pipeline_run` |
| 2634–2652 | Full rate limit block inside the generate-recommendations route |
| 2646 | `client_ip = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()` |
| 2647 | `allowed, reset_time = check_and_record_pipeline_run(client_ip)` |
| 2648–2652 | If not allowed: renders `rate_limited.html` with 429 status |

**Admin bypass:** Lines 2637–2639 — admin emails (from `ADMIN_EMAILS` env var) bypass rate limiting entirely. Lines 2641–2644 — paid `gift_emergency` credits also bypass the IP limit (one credit consumed per run).

**Backend:** **SQLite via `database.py`**, NOT shelve. The `check_and_record_pipeline_run()` function at `database.py` line 905 uses `get_db_connection()` which opens the SQLite DB with WAL mode enabled (`PRAGMA journal_mode=WAL`, line 31).

**Race condition assessment:** The `INSERT OR REPLACE` at database.py line 933–936 is a single atomic SQLite operation. Under WAL mode with 3 Gunicorn sync workers, the SELECT + INSERT OR REPLACE pattern is NOT atomic — two workers could both SELECT, both see no row or an expired row, and both INSERT OR REPLACE. This is a real (though low-probability at current traffic) race condition. The CLAUDE.md Load Testing audit flags this category. **However**, the consequence of the race is benign: both workers would allow the run and record the timestamp, effectively giving the user two runs instead of one. Not a security issue at current traffic levels.

### Q9: Does `database.py` have a `rate_limits` table? What is its schema?

**YES.** Defined at `database.py` lines 174–179:

```sql
CREATE TABLE IF NOT EXISTS rate_limits (
    ip TEXT PRIMARY KEY,
    last_run TIMESTAMP NOT NULL
)
```

- **Primary key:** `ip` (TEXT) — one row per IP address
- **`last_run`:** TIMESTAMP — stored as ISO format string via `now.isoformat()` (line 935)
- **No index needed:** PRIMARY KEY on `ip` creates an implicit index
- **WAL mode:** Enabled per-connection at line 31 — applies to all reads/writes including this table

---

## Scope Clarification: Files Touched by Each Plan

### Plan 04-01 Files (Skimlinks Removal)

**Must change:**
- `/home/user/GiftWise/skimlinks_searcher.py` — DELETE the file
- `/home/user/GiftWise/templates/base.html` — remove lines 336–346 (Skimlinks JS snippet)
- `/home/user/GiftWise/giftwise_app.py` — remove line 466 (env var), lines 3031–3033 (URL wrapping logic), update comment on line 3019
- `/home/user/GiftWise/multi_retailer_searcher.py` — remove lines 47–50 (params), lines 66/77 (comments/logging), lines 301–315 (conditional block)
- `/home/user/GiftWise/recommendation_service.py` — remove line 57 (instance var), lines 362–365 (4 params passed), lines 1204–1206 (URL wrapping)
- `/home/user/GiftWise/revenue_optimizer.py` — remove line 30 (`'skimlinks': 0.04`)
- `/home/user/GiftWise/image_fetcher.py` — remove line 411 entry, line 441 entry, lines 559–580+ (`_extract_skimlinks_image` function)
- `/home/user/GiftWise/product_schema.py` — remove line 86 commission rate, lines 419–463 (`from_skimlinks` classmethod), lines 531/553 list entries
- `/home/user/GiftWise/models.py` — remove `'skimlinks'` from comment on line 32
- `/home/user/GiftWise/config.py` — remove lines 63–67 (env var reads), line 132 (priority), line 379 (limit), lines 423–424 (warning), line 559 (status print)
- `/home/user/GiftWise/config_service.py` — remove lines 107–111 (4 fields), lines 151–155 (4 env reads), line 182 (retailer check)
- `/home/user/GiftWise/config/settings.py` — remove lines 57–61 (4 fields), line 162 (retailer check)
- `/home/user/GiftWise/products/ingestion.py` — remove lines 47–49 (import), lines 330–382 (`refresh_skimlinks` function), lines 451/466/509/534/554 (retailer list entries)

**May leave untouched (comments/scripts only):**
- `/home/user/GiftWise/scripts/convert_templates.py` — line 56–57 is a migration utility regex; harmless to leave or remove
- `/home/user/GiftWise/scripts/verify_templates.py` — line 30–32 warns if Skimlinks found outside base.html; after removal this check will always pass (harmless)
- `/home/user/GiftWise/base_searcher.py` — line 5 is a comment only

### Plan 04-02 Status

**In-flight dedup:** ALREADY IMPLEMENTED correctly. No new code needed. Task is verification only.

**Rate limiting:** ALREADY IMPLEMENTED in SQLite. No new code needed. The minor SELECT+INSERT race is documented in CLAUDE.md's Opus audit backlog and is not a blocking issue at current traffic.

**Suggested 04-02 task:** Read `profile_analyzer.py` lines 30–36 and 294–316 and 951–966. Confirm the mechanism works as described. Check that `_PROMPT_VERSION` (line 275) is current. Verify `check_and_record_pipeline_run` is the only rate-limit path and shelve is not used anywhere. Confirm no `storage_service` rate-limit calls exist.

---

## Common Pitfalls for 04-01

### Pitfall 1: Missing `recommendation_service.py` URL wrapping
**What goes wrong:** Removing only the `giftwise_app.py` `_apply_affiliate_tag` Skimlinks block but missing the identical block in `recommendation_service.py` `_apply_affiliate_tag` method (line 1204–1206). Both files have the same wrapping logic.
**Prevention:** Search for `go.skimresources.com` after changes to verify zero remaining references.

### Pitfall 2: Leaving env var read alive
**What goes wrong:** Removing the JS snippet and the URL wrapping but leaving `SKIMLINKS_PUBLISHER_ID = os.environ.get(...)` at line 466. The variable would evaluate to `''` in production (env var not set) so no functional harm, but it's confusing dead code.
**Prevention:** Remove the module-level constant AND all its uses together.

### Pitfall 3: `products/ingestion.py` try/except import
**What goes wrong:** The import of `skimlinks_searcher` is wrapped in a try/except (lines 47–49) so it silently fails rather than crashing when the file is deleted. This means the file won't error on startup — but `refresh_skimlinks()` (lines 330–382) would still be called if someone invokes it, and would fail with `skimlinks_searcher is None` (line 341 guards against this). Still, the whole function should be removed.
**Prevention:** Remove the entire `refresh_skimlinks()` function and all references to `'skimlinks'` in the retailer dispatch dicts.

### Pitfall 4: `base.html` is extended by all pages
**What goes wrong:** Removing the wrong block or leaving a stray `</script>` tag breaks the HTML structure for every page.
**Prevention:** The block to remove is lines 336–346 inclusive (the comment + the `<script>` block with the Skimlinks loader). The Sovrn snippet is in a comment block immediately after (lines 348–355) and should be left alone.

---

## Rate Limit Architecture Notes

**Current implementation is SQLite-backed, which is correct for this deployment.**

The CLAUDE.md mentions the shelve-based rate limiting race (Opus audit item). That audit item was written before the current implementation — the actual code uses SQLite with `INSERT OR REPLACE`, not shelve. The shelve-based rate limiting no longer exists in the current codebase.

**Verify this** by searching `storage_service` for any rate limit references — expected: none found.
<br>
`check_and_record_pipeline_run` is the single code path for rate limiting. It is called only from `giftwise_app.py` line 2647.

---

## Sources

All findings from direct file reads — no external sources needed.

| File | Lines Examined |
|------|---------------|
| `/home/user/GiftWise/skimlinks_searcher.py` | All (262 lines) |
| `/home/user/GiftWise/giftwise_app.py` | 95–130, 460–470, 2625–2680, 2895–2910, 3015–3035 |
| `/home/user/GiftWise/templates/base.html` | 330–360 |
| `/home/user/GiftWise/profile_analyzer.py` | 30–43, 238–319, 935–970 |
| `/home/user/GiftWise/database.py` | 26–42, 170–185, 900–940 |
| `/home/user/GiftWise/multi_retailer_searcher.py` | 40–70, 295–320 |
| `/home/user/GiftWise/recommendation_service.py` | 55–60, 355–375, 1198–1210 |
| All other `.py` files | Grep results for `skimlinks` pattern |

**Confidence:** HIGH across all findings — every claim is backed by direct line reads.
