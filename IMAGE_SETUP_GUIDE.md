# 🖼️ Image Setup Guide

## Overview

The image system automatically adds thumbnails to all gift recommendations using multiple fallback strategies.

## How It Works

### **Priority Order:**

1. **Extract from Product URL** (Best)
   - Scrapes product page for main image
   - Works for Amazon, Etsy, brand sites
   - No API needed

2. **Google Custom Search API** (Good)
   - Searches for product images
   - Requires API key (free tier: 100 searches/day)

3. **Unsplash API** (Evocative)
   - Beautiful stock photos related to product
   - Requires API key (free: 50 requests/hour)
   - Marked as "Evocative" badge

4. **Placeholder** (Always Works)
   - Colored placeholder with product name
   - No API needed
   - Always available

## Setup (Optional APIs)

### **Google Custom Search API** (Recommended)

**Why:** Best for actual product images

**Steps:**
1. Go to https://console.cloud.google.com
2. Create new project (or use existing)
3. Enable "Custom Search API"
4. Create API key (Credentials → Create Credentials → API Key)
5. Create Custom Search Engine:
   - Go to https://programmablesearchengine.google.com
   - Create new search engine
   - Add sites: `amazon.com`, `etsy.com`, `google.com`
   - Get Search Engine ID
6. Add to `.env`:
   ```
   GOOGLE_CUSTOM_SEARCH_API_KEY=your_api_key_here
   GOOGLE_CUSTOM_SEARCH_ENGINE_ID=your_engine_id_here
   ```

**Free Tier:** 100 searches/day

---

### **Unsplash API** (Optional)

**Why:** Beautiful evocative images when product images unavailable

**Steps:**
1. Go to https://unsplash.com/developers
2. Create app
3. Get Access Key
4. Add to `.env`:
   ```
   UNSPLASH_ACCESS_KEY=your_access_key_here
   ```

**Free Tier:** 50 requests/hour

---

## Current Behavior

**Without APIs:**
- ✅ Extracts images from product URLs (works for most sites)
- ✅ Falls back to placeholder (always works)
- ✅ All recommendations have images

**With Google API:**
- ✅ Better product image matching
- ✅ More accurate product photos

**With Unsplash API:**
- ✅ Beautiful evocative images when product images unavailable
- ✅ Marked with "Evocative" badge

---

## Image Display

- **Size:** 250px height, responsive width
- **Aspect Ratio:** Maintained (cover)
- **Loading:** Lazy loading for performance
- **Fallback:** Shows 🎁 emoji if image fails to load
- **Badge:** "Evocative" badge on fallback images

---

## Performance

- **Caching:** Consider caching images (future enhancement)
- **Lazy Loading:** Images load as user scrolls
- **Error Handling:** Graceful fallback if image fails

---

## Testing

1. **Without APIs:** Should still get images from product URLs
2. **With Google API:** Better product image matching
3. **With Unsplash:** Evocative images for products without URLs

---

## Troubleshooting

**No images showing:**
- Check browser console for errors
- Verify product URLs are valid
- Check if images are blocked by CORS

**Images slow to load:**
- Normal - images load from external sources
- Consider image CDN (future enhancement)

**"Evocative" badge showing:**
- Normal - means using Unsplash or placeholder
- Product image wasn't available

---

## Next Steps

1. **Test without APIs** - Should work with URL extraction
2. **Add Google API** - For better product images (optional)
3. **Add Unsplash API** - For beautiful fallbacks (optional)
4. **Monitor performance** - Check image load times
5. **Consider caching** - Cache images to reduce API calls

---

**Note:** The system works without any APIs! APIs just improve image quality.
