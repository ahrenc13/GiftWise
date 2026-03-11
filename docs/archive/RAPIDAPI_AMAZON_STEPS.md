# RapidAPI Amazon – which API and how to use it

## Recommended API: **Real-Time Amazon Data** (OpenWeb Ninja)

Use this one for Amazon product search in GiftWise:

- **Name:** Real-Time Amazon Data  
- **URL:** https://rapidapi.com/letscrape-6bRBa3QguO5/api/real-time-amazon-data  
- **Why:** Product Search endpoint (`GET /search`), clear docs, 100 free requests/month on BASIC, supports US and other countries. Same RapidAPI key you already use.

**Alternatives** (if you prefer):

- **Axesso – Amazon Data Service** – https://rapidapi.com/axesso/api/axesso-amazon-data-service1 – Verified, 50 free/month.  
- **Amazon Product/Reviews/Keywords** (LogicBuilder) – https://rapidapi.com/logicbuilder/api/amazon-product-reviews-keywords – 67ms latency, real-time product/search.

---

## Steps to enact (Real-Time Amazon Data)

1. **Subscribe**
   - Go to https://rapidapi.com/letscrape-6bRBa3QguO5/api/real-time-amazon-data  
   - Sign in to RapidAPI (same account as your existing `RAPIDAPI_KEY`).  
   - Open **Pricing** and subscribe to **BASIC** (free, 100 requests/month) or a paid plan if you need more.

2. **Use your existing key**
   - GiftWise already uses `RAPIDAPI_KEY` from Railway.  
   - The same key works for any RapidAPI API you’re subscribed to.  
   - No new env var: keep using `RAPIDAPI_KEY`.

3. **Redeploy**
   - Redeploy so the app uses the new RapidAPI Amazon implementation (and the `enhanced_search_terms` fix).  
   - Amazon will run as the fallback product source (after Etsy, Awin, eBay, ShareASale).

4. **If search fails**
   - In the API’s **Playground**, open the **Product Search** endpoint and check the exact parameter names (e.g. `query` vs `keywords`, `country` vs `domain`).  
   - The code uses `query`, `country=US`, `page=1`. If the API uses different names, we can adjust the searcher.

---

## Log error you hit: `enhanced_search_terms`

Your log showed:

`search_products_multi_retailer() got an unexpected keyword argument 'enhanced_search_terms'`

That’s fixed: `enhanced_search_terms` is now a parameter of `search_products_multi_retailer`. Redeploy so the new code (and the RapidAPI Amazon implementation) is live.
