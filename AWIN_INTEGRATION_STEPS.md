# Awin integration – what you need and what to do

You’re approved at Awin. Here’s what we need from there and what to do next.

---

## 1. Get your **Data Feed API key** (for product search)

Awin doesn’t have a “keyword search” API like the old ShareASale one. Product data comes from **product feeds** (CSV downloads). GiftWise uses a **Data Feed API key** to list and download those feeds and search inside them.

**Where to get it:**

1. Log in at **https://ui.awin.com**
2. Go to **Toolbox → Create-a-Feed**
3. Use any standard feed download there; the URL will contain your **data feed API key**, or you can get the “full download link including the relevant API key” from that section.

Alternatively, the feed list URL is:

`https://productdata.awin.com/datafeed/list/apikey/YOUR_DATA_FEED_API_KEY`

If you already have a feed download link from Create-a-Feed, the `apikey=...` part (or the key in the path) is your **Data Feed API key**. It is **different** from the Publisher API token below.

---

## 2. (Optional) Get your **Publisher API token**

Used for Awin’s Publisher API (e.g. reporting, future features). Not required for the current product search integration.

**Where to get it:**

1. Go to **https://ui.awin.com/awin-api**
2. Open **API Credentials**, use your password, then **Show my API token**
3. Copy the token (Bearer style).

---

## 3. Add these in Railway

In your Railway project → **Variables**, add:

| Variable | Value | Required for product search? |
|----------|--------|------------------------------|
| `AWIN_DATA_FEED_API_KEY` | The key from step 1 (Create-a-Feed / feed list URL) | **Yes** |
| `AWIN_API_TOKEN` | Token from step 2 (awin-api page) | No (optional, for future use) |

Do **not** put these values in code or commit them; only in Railway (or `.env` locally).

---

## 4. What we did in the app

- Added **Awin product search** using your Data Feed API key: the app fetches the list of feeds you can access, then uses one or more feed CSVs to find products that match the user’s interests (e.g. “hiking gift”).
- Awin is used **in addition to** Etsy and Amazon (and any legacy ShareASale config). If `AWIN_DATA_FEED_API_KEY` is set, Awin is included in the multi-retailer search.

---

## 5. Quick checklist

1. Get **Data Feed API key** from Awin (Toolbox → Create-a-Feed or feed list URL).
2. Add **`AWIN_DATA_FEED_API_KEY`** in Railway with that value.
3. (Optional) Add **`AWIN_API_TOKEN`** in Railway if you want Publisher API available later.
4. Redeploy so the new variable is picked up.

After that, Awin is integrated for product search. If something doesn’t work (e.g. no products, or errors in logs), we can debug using the feed list and the first feed URL from your account.
