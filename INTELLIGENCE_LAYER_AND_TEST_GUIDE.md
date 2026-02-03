# Intelligence Layer & Full Test Guide

**Purpose:** Confirm the intelligence layer is in place and give you a clear checklist + test steps for a full successful run.

---

## 1. Is the Intelligence Layer In Place? ✅

**Yes.** The code is wired correctly:

- **Imports** (in `giftwise_app.py`, after `load_dotenv()`):  
  `enrichment_engine`, `experience_architect`, and `payment_model` are imported in a `try`/`except`.  
  On success: `INTELLIGENCE_LAYER_AVAILABLE = True`.  
  On failure: `INTELLIGENCE_LAYER_AVAILABLE = False` and the app still runs without enrichment.

- **Usage:**
  - **Review step** (profile for validation): when `INTELLIGENCE_LAYER_AVAILABLE`, the app calls `enrich_profile_simple()` and stores `enriched_profile`, `enhanced_search_terms`, `quality_filters` in session.
  - **Generate flow**: same enrichment when the layer is available and not already enriched from review; otherwise uses profile as-is.
  - **Quality filter**: products are filtered with `should_filter_product()` when `quality_filters` is non-empty (only set when the intelligence layer ran).

- **Startup log:**  
  On deploy you’ll see either:
  - `Intelligence layer loaded successfully (enrichment_engine, experience_architect, payment_model)`  
  or
  - `Intelligence layer NOT loaded - enrichment and quality filters disabled...`  
  So you can confirm from Railway (or local) logs that the layer loaded.

---

## 2. Do You Need API Keys for the Intelligence Layer? **No**

The intelligence layer does **not** use any API keys or env vars:

| Module               | What it does                         | API keys / env |
|----------------------|--------------------------------------|----------------|
| `enrichment_engine`  | Enriches profile, quality filters    | **None**       |
| `enrichment_data`   | Static gift/intelligence data        | **None**       |
| `experience_architect` | Experience packages (imported; used if you add routes) | **None** |
| `payment_model`      | Pricing/tiers (imported; used if you add routes)     | **None**       |

- All logic and data are in-code (and optional staged updates from a path that’s safe if missing).
- No external APIs are called by these modules.
- They only need to be **present and importable** (no missing files or syntax errors).

So the intelligence layer will work as long as the four files are in the repo and Railway (or your environment) can import them. No extra credentials are required for the layer itself.

---

## 3. Credentials Required for a Full Successful Test

For the **full flow** (signup → connect platforms → scrape → review profile → generate recommendations), you need these set in Railway (and in `.env` locally):

### Required (app won’t work fully without these)

| Variable           | Used for                    | Where to get it |
|--------------------|-----------------------------|------------------|
| `SECRET_KEY`       | Flask session               | Any long random string |
| `ANTHROPIC_API_KEY`| Profile + curation (Claude) | [Anthropic Console](https://console.anthropic.com) |
| `SERPAPI_API_KEY`  | Product search              | [SerpAPI](https://serpapi.com) (free tier has a limit) |
| `APIFY_API_TOKEN`  | Instagram/TikTok scraping   | [Apify](https://apify.com) (Instagram/TikTok scrapers) |

### Optional (improve experience but not required for core test)

| Variable                         | Used for              |
|----------------------------------|-----------------------|
| `GOOGLE_CSE_API_KEY` / `GOOGLE_CUSTOM_SEARCH_ENGINE_ID` | Better product images |
| `UNSPLASH_ACCESS_KEY`            | Fallback images      |
| Stripe keys                      | Payments             |
| OAuth keys (Pinterest, Spotify, etc.) | Connect those platforms |

**Summary:** For a full successful test of the new routes and intelligence layer, you **must** have:

1. **SECRET_KEY**  
2. **ANTHROPIC_API_KEY**  
3. **SERPAPI_API_KEY**  
4. **APIFY_API_TOKEN**  

Set these in Railway: **Project → Your Service → Variables**. Add each name and value, then redeploy.

---

## 4. Quick Checklist Before Testing

- [ ] **Code:** Imports for the intelligence layer are **outside** the docstring in `giftwise_app.py` (they run at startup).
- [ ] **Files in repo (and on Railway):**  
  `enrichment_engine.py`, `enrichment_data.py`, `experience_architect.py`, `payment_model.py` at repo root (or wherever Railway runs the app).
- [ ] **Env on Railway:**  
  `SECRET_KEY`, `ANTHROPIC_API_KEY`, `SERPAPI_API_KEY`, `APIFY_API_TOKEN` set.
- [ ] **Branch:** Railway is deploying the branch you pushed (e.g. `main`).
- [ ] **Root directory:** Railway “Root Directory” is blank or `/` so it sees the repo root (and the four `.py` files).

---

## 5. Full Test Steps (End-to-End)

1. **Deploy**  
   Push your branch and let Railway deploy.

2. **Check logs**  
   In Railway logs, look for:
   - `Intelligence layer loaded successfully...`  
   If you see `Intelligence layer NOT loaded...`, the four modules aren’t loading (path, branch, or missing file).

3. **Sign up**  
   Open the app → Sign up (email, etc.).

4. **Connect platforms**  
   Add at least one of: Instagram, TikTok (username only; scraping uses Apify).

5. **Start scraping**  
   Click through to start scraping. Wait until both (or your chosen) platforms show complete.

6. **Review profile**  
   You should land on the profile review step. Interests and location should be filled from the intelligence layer if it loaded.

7. **Approve and generate**  
   Click the main CTA to approve the profile and go to the “generating” screen.

8. **Recommendations**  
   Wait for the API to finish. You should get a list of product + experience recommendations.

9. **Logs to confirm intelligence layer usage**  
   - “Enriching profile with intelligence layer…”  
   - “Profile enriched: X enhanced search terms”  
   - “Applying intelligence quality filters…” (if any products are filtered)

If any step fails, the logs (and the checklist above) will tell you whether it’s missing credentials, missing files, or a wrong path/branch.

---

## 6. If the Intelligence Layer Still Doesn’t Load

1. **Railway logs**  
   Check for the exact error right after startup (e.g. `ImportError`, `ModuleNotFoundError`).

2. **File presence**  
   In Railway, confirm the four files are in the built app (e.g. build output or “View source” if available). If you use a monorepo or custom root, ensure “Root Directory” includes these files.

3. **Run the import locally**  
   In your repo root:
   ```bash
   python -c "
   from enrichment_engine import enrich_profile_simple, should_filter_product
   from experience_architect import create_multiple_experiences
   from payment_model import get_pricing_for_user
   print('Intelligence layer OK')
   r = enrich_profile_simple(interests=['cooking'], relationship='close_friend')
   print('enrich_profile_simple OK', len(r.get('enriched_interests', [])))
   "
   ```
   If this fails locally, fix the import/syntax error before debugging Railway.

4. **Staged updates path (optional)**  
   Enrichment engine can load optional updates from a path (e.g. `/mnt/user-data/staged_updates`). If that path doesn’t exist, it just uses in-code data; no env var is required. You can ignore this unless you’re explicitly using staged updates.

---

**Summary:** The intelligence layer is in place and does not need API keys. For a full successful test, set **SECRET_KEY**, **ANTHROPIC_API_KEY**, **SERPAPI_API_KEY**, and **APIFY_API_TOKEN** on Railway, then follow the checklist and test steps above. Use the startup and enrichment log lines to confirm the layer is loaded and used.
