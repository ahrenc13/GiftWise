# GiftWise: Operations & Scaling (Simple Guide)

**For:** When you have real users and need to know what to watch and when to change things.

---

## 1. Where to Look

### Railway logs (main place)

1. Open **Railway** → your project → **web** service.
2. Click **Deployments** → open the latest deployment.
3. Click **Deploy Logs** (or **View Logs**).
4. Use the search box to search logs (e.g. `429`, `SerpAPI`, `Scrape slots`, `Product search`).

### SerpAPI dashboard

- Go to [serpapi.com](https://serpapi.com) → log in → **Dashboard**.
- Check **Searches used** (e.g. 50/1000 this month).
- If you hit the limit, you’ll see **429** in Railway logs and “No products” for users.

### Apify dashboard (scraping)

- Go to [apify.com](https://apify.com) → log in → **Usage**.
- Check how much you’re using for Instagram and TikTok actors.
- If you run out, scrapes will fail and users will see errors or “No platforms have completed scraping.”

---

## 2. What the Log Messages Mean

| Log message | What it means | What to do |
|-------------|----------------|------------|
| **SerpAPI: waiting X.Xs (another user just used the API)** | Another user’s product search just ran; yours is waiting so we don’t hit SerpAPI limits. | Normal when 2+ users at once. If you see this a lot and users complain about slowness, see “When to raise limits” below. |
| **Found N products in X.Xs** | Product search finished. N = how many products; X.Xs = how long it took. | If X is often > 20–30s with several users, consider raising SerpAPI limits. |
| **Rate limited (429) for: …** | SerpAPI said “too many requests.” | You’re at or over your SerpAPI plan limit. Upgrade plan or add `SERPAPI_MIN_GAP_SECONDS` (see below). |
| **Scrape slots full (8 in use), waiting for a slot for Instagram/…** | All 8 scrape slots are in use; a new user’s scrape is waiting. | Normal under load. If you see this often and want more concurrency, raise `MAX_CONCURRENT_SCRAPERS` (see below). |
| **No products collected from search** | Product search returned 0 (often 429 or bad key). | Check SerpAPI dashboard and Railway vars; see “When things go wrong” below. |
| **Product search returned no results - may be misconfigured or rate limited** | Same as above; app is warning that something is wrong. | Same as above. |

---

## 3. When to Raise Limits (More Users = Good)

When you’re **happy with traffic** and have **upgraded** SerpAPI and/or Apify:

### In Railway: Variables

1. Railway → your project → **web** → **Variables**.
2. Add or edit:

| Variable | Default | When to change |
|----------|--------|----------------|
| **SERPAPI_MIN_GAP_SECONDS** | `2.0` | After upgrading SerpAPI plan: set to `1.0` or `0.5` so product search can run a bit faster under load. |
| **MAX_CONCURRENT_SCRAPERS** | `8` | After upgrading Apify/limits: set to `12` or `16` so more users can scrape at once. |

3. Save; Railway will redeploy. No code change needed.

### Optional: Two web workers

If the app has enough memory (e.g. 512MB+), you can handle two requests at once:

1. Open **railway.json** in the project.
2. Find the line with `gunicorn` and `--workers 1`.
3. Change `--workers 1` to `--workers 2`.
4. Commit and push; Railway redeploys.

---

## 4. When Things Go Wrong

### “No products” / 429 in logs

- **Cause:** SerpAPI limit (plan or per-minute).
- **Do:**  
  1. Check [serpapi.com](https://serpapi.com) dashboard (searches used).  
  2. If at limit: wait for reset or upgrade plan.  
  3. If not at limit: in Railway Variables, try `SERPAPI_MIN_GAP_SECONDS=2.5` or `3.0` to slow calls and avoid 429.

### Scraping never finishes / “No platforms have completed scraping”

- **Cause:** Apify limit, Instagram/TikTok blocking, or scraper error.
- **Do:**  
  1. Check Apify usage.  
  2. In Railway logs, search for `Scrape` or `Apify` to see errors.  
  3. If you see “Scrape slots full” a lot and have headroom on Apify, raise `MAX_CONCURRENT_SCRAPERS` (e.g. to 12).

### App feels slow with several users

- **Cause:** One worker + SerpAPI spacing + scrape cap.
- **Do:**  
  1. Raise limits as in “When to raise limits” (env vars + optional 2 workers).  
  2. In logs, check “Found N products in X.Xs” and “SerpAPI: waiting”; that shows where time is going.

---

## 5. Quick Checklist (Once a Week or After a Spike)

- [ ] Railway Deploy Logs: search for `429` or `ERROR`. If none, you’re good.
- [ ] SerpAPI dashboard: searches used vs plan. If close to limit, plan to upgrade or slow down (higher `SERPAPI_MIN_GAP_SECONDS`).
- [ ] Apify dashboard: usage vs plan. Same idea.
- [ ] If you see “Scrape slots full” or “SerpAPI: waiting” a lot and you’ve upgraded plans, add or adjust the Variables above.

---

## 6. Summary

- **Logs** = Railway Deploy Logs; search for `429`, `SerpAPI`, `Scrape slots`, `Found … products`.
- **Dashboards** = SerpAPI and Apify usage.
- **When traffic is good and you’ve upgraded:** set `SERPAPI_MIN_GAP_SECONDS` and/or `MAX_CONCURRENT_SCRAPERS` in Railway Variables; optionally use `--workers 2` in railway.json.
- **When something breaks:** use the “What the log messages mean” and “When things go wrong” sections above.

You don’t need to track fancy metrics; checking logs and dashboards when something feels off is enough to stay on top of scaling.
