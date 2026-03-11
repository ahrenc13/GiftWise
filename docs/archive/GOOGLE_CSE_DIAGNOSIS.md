# Google Custom Search Engine – Diagnosis & Fixes

## Current architecture (new work with Claude)

1. **Profile analyzer** (`profile_analyzer.py`) – Builds a deep recipient profile from social data (Claude).
2. **Product searcher** (`product_searcher.py`) – **Uses Google CSE**: up to **15 web searches** (10 results each) from profile interests.
3. **Gift curator** (`gift_curator.py`) – Curates 10 product gifts + 2–3 experience gifts from those results (Claude).

**Other CSE consumers** (used in legacy flow or image/link steps):

- **`image_fetcher.py`** – Google CSE with `searchType=image` (1 query per recommendation when fetching images).
- **`link_validation.py`** – Google CSE for “shopping” validation (1 query per product when validating links).

In the **new flow**, only **product_searcher** calls Google CSE (15 calls per run). Image/link modules are not used there but share the same API key and quota.

---

## Why the search engine “blocks” – likely causes

### 1. **Daily quota (most likely)**

- **Free tier: 100 queries per day** per Google Cloud project.
- **New flow:** 15 CSE requests per recommendation run.
- **Rough limit:** ~6 full runs per day before quota is exceeded.
- **Symptom:** After some runs, API returns **429 (Too Many Requests)** or **403**, and the flow fails.

### 2. **API key restrictions (403)**

- In Google Cloud Console, the API key can be restricted by:
  - **Application:** e.g. “HTTP referrer” only.
- Your app runs **on the server** (e.g. Railway). Server-side requests do **not** send an HTTP referrer.
- If the key is restricted to “HTTP referrers” only, **every** CSE request can get **403 Forbidden**.
- **Fix:** Restrict the key by **“IP addresses”** (add your server IPs) or use **“None”** for testing, and ensure **“Custom Search API”** is allowed.

### 3. **Custom Search Engine (CSE) configuration**

- The **Programmable Search Engine** (cx) must be set to **“Search the entire web”** for product queries.
- If the CSE is “Image search” only or restricted to a short list of sites, **web** searches from `product_searcher` can return almost nothing or behave like they’re “blocked.”
- **Fix:** In [Programmable Search Engine](https://programmablesearchengine.google.com/), confirm the engine is “Search the entire web” (or includes the sites you need).

### 4. **SafeSearch and `safe='off'`**

- **`product_searcher.py`** uses **`safe='off'`**.
- Some keys or CSE settings force SafeSearch. For those, `safe='off'` can lead to **403** or empty/blocked results.
- **Fix:** Try **`safe='active'`** (or `'medium'`) in `product_searcher` to see if blocking stops.

### 5. **Env var mismatch (link_validation / image_fetcher)**

- **giftwise_app** and **product_searcher** use:
  - `GOOGLE_CSE_API_KEY`
  - `GOOGLE_CUSTOM_SEARCH_ENGINE_ID`
- **env.template** and **image_fetcher** / **link_validation** use:
  - `GOOGLE_CUSTOM_SEARCH_API_KEY`
  - `GOOGLE_CUSTOM_SEARCH_ENGINE_ID`
- **giftwise_app** patches **image_fetcher** at startup with `GOOGLE_CSE_API_KEY` and `GOOGLE_CUSTOM_SEARCH_ENGINE_ID`, so image search can work if only CSE vars are set.
- **link_validation** only reads `GOOGLE_CUSTOM_SEARCH_API_KEY` / `GOOGLE_CUSTOM_SEARCH_ENGINE_ID` and is **not** patched. If you only set `GOOGLE_CSE_API_KEY`, link_validation effectively has no key and won’t use CSE (no extra quota use, but also no validation).

For **blocking** in the **new flow**, the important part is: **one** set of credentials is used (CSE key + engine id). So the main things that will “stop” the search engine are: **quota**, **key restrictions**, **CSE config**, and **SafeSearch**.

---

## What to check when you have logs

When you upload logs, look for:

1. **HTTP status from Google CSE**
   - **429** → quota or rate limit (reduce calls, add backoff, or increase quota).
   - **403** → key restrictions, CSE not enabled, or SafeSearch/key policy (check key + CSE settings).
   - **400** → bad request (e.g. invalid `cx` or params).

2. **Response body**
   - Google often returns a JSON body with an `error` object and `message` (e.g. “rate limit exceeded”, “forbidden”, “invalid API key”). That message will pinpoint the block.

3. **Where it fails**
   - If it fails on the **first** request → likely **key/CSE config** or **SafeSearch**.
   - If it fails after **several** requests in one run → likely **rate limit**.
   - If it fails after **many runs** in a day** → likely **daily quota**.

---

## Code / config fixes applied (see below)

1. **Unify env vars** – Use `GOOGLE_CSE_API_KEY` and `GOOGLE_CUSTOM_SEARCH_ENGINE_ID` everywhere and document in `env.template`.
2. **Log 403/429 and body** – In `product_searcher` (and optionally image_fetcher/link_validation), log status code and response body when CSE returns non-200 so your logs show the exact “block” reason.
3. **Optional: SafeSearch** – Switch `product_searcher` to `safe='active'` to test if blocking is SafeSearch-related.
4. **Optional: Reduce queries** – Lower max queries in `product_searcher` (e.g. 15 → 8) to stay under quota more easily.

After you share logs, we can tie the exact message (e.g. “quota exceeded” vs “forbidden”) to one of the causes above and adjust CSE/key or code as needed.
