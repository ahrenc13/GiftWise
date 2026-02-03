# What to Do Next – Get the App Running

Follow these steps in order.

---

## Step 1: Save and commit your changes

1. **Save all files** in Cursor (File → Save All or Ctrl+K S).
2. Open a terminal in the project folder (`c:\Users\Chad\Documents\GitHub\GiftWise`).
3. Run:

```powershell
git status
```

You should see modified files (e.g. `giftwise_app.py`, `profile_analyzer.py`, `product_searcher.py`, `templates/connect_platforms.html`, `env.template`) and possibly new files (`INTELLIGENCE_LAYER_AND_TEST_GUIDE.md`, `SESSION_SUMMARY_2026-02-02.md`, `NEXT_STEPS.md`).

4. Stage and commit:

```powershell
git add -A
git commit -m "Intelligence layer fix: real imports, friendly errors, profile analyzer TikTok fix"
git push
```

(Use your usual branch name if not `main`, e.g. `git push origin main`.)

---

## Step 2: Set environment variables on Railway

1. Go to [Railway](https://railway.app) → your project → your GiftWise service.
2. Open **Variables**.
3. Ensure these are set (add or update):

| Variable | Required | Where to get it |
|----------|----------|------------------|
| `SECRET_KEY` | Yes | Any long random string (e.g. 32+ characters). |
| `ANTHROPIC_API_KEY` | Yes | [Anthropic Console](https://console.anthropic.com) → API Keys. |
| `SERPAPI_API_KEY` | Yes | [SerpAPI](https://serpapi.com) → Dashboard → API Key. |
| `APIFY_API_TOKEN` | Yes | [Apify](https://apify.com) → Settings → Integrations → API Token. |

4. Save. Railway will redeploy when you push; if you already pushed, trigger a redeploy (Deployments → ⋮ → Redeploy) after changing variables.

---

## Step 3: Confirm deployment and intelligence layer

1. After the deploy finishes, open **Deployments** → latest deployment → **View Logs**.
2. In the logs, look for one of these right after startup:
   - **"Intelligence layer loaded successfully (enrichment_engine, experience_architect, payment_model)"** → layer is on.
   - **"Intelligence layer NOT loaded..."** → layer failed to import; check that `enrichment_engine.py`, `enrichment_data.py`, `experience_architect.py`, `payment_model.py` are in the repo root and that Railway **Root Directory** is blank or `/`.
3. Note your app URL (e.g. `https://your-app.up.railway.app`).

---

## Step 4: Run a full test

1. Open the app URL in a browser.
2. **Sign up** (email, etc.).
3. **Connect platforms**: add at least Instagram or TikTok (username).
4. **Start scraping** and wait until it finishes.
5. **Review profile**: you should see the profile review page with interests.
6. Click the main **“Find my gifts”** (or equivalent) button to approve and go to **Generating**.
7. Wait for **Recommendations** to load.

If something fails, check Railway logs for the exact error (e.g. missing key, import error).

---

## Step 5: If Git doesn’t show changes

- Run `git status` again after **Save All** in Cursor.
- If you still see “nothing to commit”:
  - Confirm you’re in `c:\Users\Chad\Documents\GitHub\GiftWise`.
  - Confirm the same folder is the one Cursor has open.
- If files show as modified, run the `git add -A` and `git commit` and `git push` from Step 1.

---

## Quick reference

- **Intelligence layer** = no extra API keys; it just needs the four `.py` files in the repo and importable.
- **Full flow** = needs `SECRET_KEY`, `ANTHROPIC_API_KEY`, `SERPAPI_API_KEY`, `APIFY_API_TOKEN` on Railway.
- **More detail** = see `INTELLIGENCE_LAYER_AND_TEST_GUIDE.md` in this repo.
