# 🔍 How to Get Google Custom Search Engine ID

You already have your **API Key**: `AIzaSyBtRBn7N9706EVTvYU-60UO8qU-bugyYbw`

Now you need the **Search Engine ID** (also called "CX" or "Engine ID").

---

## Step-by-Step Guide

### **Step 1: Go to Custom Search Engine Page**

1. Go to: **https://programmablesearchengine.google.com/controlpanel/create**
   - Or search "Google Custom Search Engine" and click the first result

### **Step 2: Create a New Search Engine**

**Option A: Search Entire Web (Recommended)**
1. **Sites to search:** Enter `*` (just an asterisk - this is Google's special syntax for "search entire web")
   - This is allowed and different from `*.com` patterns
   - This searches the entire web (not just specific sites)
   - **Important:** You need this for image search

**Option B: Search Specific Sites (Alternative)**
If `*` doesn't work, add these popular sites one by one:
- `amazon.com/*`
- `etsy.com/*`
- `uncommongoods.com/*`
- `etsy.com/shop/*`
- `lego.com/*`
- (Add up to 50 domains)

2. **Name:** `GiftWise Image Search` (or any name you want)

3. Click **"Create"**

### **Step 3: Get Your Search Engine ID**

1. After creating, you'll see a page with your search engine
2. Click **"Control Panel"** (or go to: https://programmablesearchengine.google.com/controlpanel/all)
3. Click on your search engine name
4. Look for **"Search engine ID"** or **"CX"**
   - It looks like: `017576662512468239146:omuauf_lfve`
   - Copy this entire string

### **Step 4: Enable Image Search**

1. In the Control Panel, go to **"Setup"** → **"Advanced"**
2. Turn ON **"Image search"**
3. If you used `*` in Step 2, **"Search the entire web"** should already be enabled
4. If you added specific sites, you can still enable image search
5. Click **"Save"**

**Note:** If you used `*` (asterisk), Google automatically enables "Search the entire web" - this is the recommended approach for product image search.

---

## What It Looks Like

Your Search Engine ID will be something like:
```
017576662512468239146:omuauf_lfve
```

Or shorter:
```
abc123def456:xyz789
```

**Format:** `numbers:letters_and_numbers`

---

## Quick Checklist

- [ ] Created Custom Search Engine
- [ ] Set "Sites to search" to `*` (asterisk)
- [ ] Copied Search Engine ID
- [ ] Enabled Image Search in Advanced settings
- [ ] Enabled "Search the entire web"

---

## Once You Have It

Send me your **Search Engine ID** and I'll add both keys to your `.env` file!

It should look something like: `017576662512468239146:omuauf_lfve`

---

**Note:** If you already created a search engine before, you can find it at:
https://programmablesearchengine.google.com/controlpanel/all

Just click on it and copy the Search Engine ID from there.
