# Affiliate network: ShareASale → Awin

**Summary:** ShareASale was acquired by **Awin** (awin.com). The ShareASale platform was closed in **October 2025**; publishers and advertisers were migrated to Awin.

---

## What this means for GiftWise

- **Existing ShareASale credentials:** If you had a ShareASale account, it was migrated to Awin. Use the **Awin** publisher dashboard and API; the old ShareASale API (`api.shareasale.com`) may be deprecated or redirected.
- **New signups:** Use **Awin** (awin.com), not ShareASale. Sign up as a publisher at Awin and use Awin’s API and product feeds.

---

## Awin resources

- **Publisher signup / dashboard:** https://www.awin.com  
- **API docs (publishers):** https://developer.awin.com/apidocs/for-publishers  
- **Product feeds:** https://developer.awin.com/docs/product-feed-publisher-guide-intro  
- **Post-upgrade FAQ (ShareASale → Awin):** https://success.awin.com/s/article/Post-upgrade-FAQ-ShareASale-to-Awin  

---

## Code and env vars in this repo

- **`affiliate_searcher.py`** still uses the ShareASale API endpoint and env vars (`SHAREASALE_AFFILIATE_ID`, `SHAREASALE_API_TOKEN`, `SHAREASALE_API_SECRET`). That may work if Awin still exposes a compatible API for migrated accounts; otherwise it will need to be updated to Awin’s API.
- **Next step:** When you have Awin publisher credentials, we can add an **Awin searcher** (or switch `affiliate_searcher.py` to Awin’s API) and use Awin-specific env vars. Until then, the existing ShareASale env vars are unchanged so existing configs don’t break.

---

## Railway variables

- If you’re setting this up **new**, plan on **Awin** and ask for Awin API credentials (publisher API key / token, etc.).
- If you already have **ShareASale** env vars in Railway from before the migration, leave them in place for now; we can switch to Awin env vars once an Awin integration is in place.
