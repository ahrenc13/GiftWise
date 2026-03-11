# eBay integration – steps

eBay is integrated as a product source (Browse API). Use these steps to get credentials and configure the app.

---

## 1. Join eBay Developers Program

1. Go to **https://developer.ebay.com/join**
2. Sign in or create an account (free; includes 5,000 API calls/day).

---

## 2. Get OAuth credentials (App ID + Cert ID)

1. Log in at **https://developer.ebay.com**
2. Go to **Your Account → Application Keys** (or **My Account → Application Keys**).
3. Create an app or use an existing one.
4. For **Production**, copy:
   - **App ID (Client ID)**
   - **Cert ID (Client Secret)**
5. For testing you can use **Sandbox** keys first; the app is wired for **Production** by default (`api.ebay.com`). To use Sandbox you’d need to point the searcher at Sandbox token and Browse URLs.

---

## 3. Add variables in Railway

In your Railway project → **Variables**, add:

| Variable | Value |
|--------|--------|
| `EBAY_CLIENT_ID` | Your App ID (Client ID) from step 2 |
| `EBAY_CLIENT_SECRET` | Your Cert ID (Client Secret) from step 2 |

Do **not** put these in code or commit them; only in Railway (or `.env` locally).

---

## 4. Redeploy

Redeploy so the new variables are picked up. eBay will then be used in the product flow after Etsy and Awin (order: Etsy → Awin → eBay → ShareASale → Amazon).

---

## 5. (Optional) Etsy 403 – “all flowers” / no Etsy results

If logs show **Etsy API 403 Forbidden** for every request:

- **Cause:** The app is using a key that isn’t allowed for that environment (e.g. Sandbox key against production, or app not yet approved for production).
- **Fix:**
  1. In Etsy Developer Portal, confirm the app is **approved for production** (not just Sandbox).
  2. Use the **production** API key in Railway (`ETSY_API_KEY`), not the Sandbox key.
  3. Ensure the key has the **listings** scope needed for `GET /v3/application/listings/active`.

Until Etsy returns 200, the app will rely on Awin (and now eBay) for product results. The “all flowers” result happened because **only Awin** was returning products and the first feed used was a single florist (Bunches.co.uk). The Awin logic has been updated to use **multiple feeds** and to **deprioritize florist-only advertisers** so results are more diverse.
