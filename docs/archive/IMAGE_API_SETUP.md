# 🖼️ Image API Setup Guide

Complete step-by-step guide to set up Google Custom Search and Unsplash APIs for product images.

---

## 📸 Google Custom Search API (Product Images)

### **Why Google Custom Search?**
- Finds actual product images from retailers
- More accurate than generic image search
- Free tier: 100 searches/day
- Perfect for product thumbnails

### **Step 1: Create Google Cloud Project**

1. Go to https://console.cloud.google.com
2. Click **"Select a project"** → **"New Project"**
3. Name it: `GiftWise` (or any name)
4. Click **"Create"**

### **Step 2: Enable Custom Search API**

1. In your project, go to **"APIs & Services"** → **"Library"**
2. Search for **"Custom Search API"**
3. Click **"Enable"**

### **Step 3: Create API Key**

1. Go to **"APIs & Services"** → **"Credentials"**
2. Click **"+ CREATE CREDENTIALS"** → **"API Key"**
3. Copy your API key (looks like: `AIzaSy...`)
4. **Optional but recommended:** Click "Restrict key"
   - Under "API restrictions", select "Restrict key"
   - Choose "Custom Search API"
   - Click "Save"

### **Step 4: Create Custom Search Engine**

1. Go to https://programmablesearchengine.google.com/controlpanel/create
2. **Sites to search:** Enter `*` (asterisk - searches entire web)
3. **Name:** `GiftWise Image Search` (or any name)
4. Click **"Create"**
5. Click **"Control Panel"** for your engine
6. Under **"Setup"** → **"Basics"**, find your **Search Engine ID**
   - Looks like: `017576662512468239146:omuauf_lfve`
7. **Enable Image Search:**
   - Go to **"Setup"** → **"Advanced"**
   - Turn ON **"Image search"**
   - Turn ON **"Search the entire web"**
   - Click **"Save"**

### **Step 5: Add to .env File**

Add these two lines to your `.env` file:

```bash
GOOGLE_CUSTOM_SEARCH_API_KEY=AIzaSy...your_api_key_here
GOOGLE_CUSTOM_SEARCH_ENGINE_ID=017576662512468239146:omuauf_lfve
```

**Replace with your actual values!**

---

## 🎨 Unsplash API (Evocative Images)

### **Why Unsplash?**
- Beautiful, high-quality images
- Great for "evocative" images when product image isn't available
- Free tier: 50 requests/hour
- Professional photography

### **Step 1: Create Unsplash Account**

1. Go to https://unsplash.com/developers
2. Click **"Register as a developer"**
3. Sign up with email or GitHub

### **Step 2: Create Application**

1. After logging in, go to https://unsplash.com/oauth/applications
2. Click **"New Application"**
3. **Application name:** `GiftWise` (or any name)
4. **Description:** `Gift recommendation app for product images`
5. Accept terms and click **"Create application"**

### **Step 3: Get Access Key**

1. In your application dashboard, find **"Access Key"**
2. Copy it (looks like: `abc123def456...`)
3. **Note:** This is your `UNSPLASH_ACCESS_KEY`

### **Step 4: Add to .env File**

Add this line to your `.env` file:

```bash
UNSPLASH_ACCESS_KEY=abc123def456...your_access_key_here
```

**Replace with your actual access key!**

---

## ✅ Complete .env Example

Here's what your `.env` file should look like with image APIs:

```bash
# Flask
SECRET_KEY=your-secret-key-here

# Anthropic API
ANTHROPIC_API_KEY=sk-ant-api03-YOUR_KEY_HERE

# Image APIs
GOOGLE_CUSTOM_SEARCH_API_KEY=AIzaSy...your_google_api_key
GOOGLE_CUSTOM_SEARCH_ENGINE_ID=017576662512468239146:omuauf_lfve
UNSPLASH_ACCESS_KEY=abc123def456...your_unsplash_key

# Other APIs...
APIFY_API_TOKEN=apify_api_YOUR_TOKEN_HERE
# ... etc
```

---

## 🧪 Testing Your Setup

### **Test Google Custom Search:**

```python
# Test in Python shell
import os
from dotenv import load_dotenv
load_dotenv()

from image_fetcher import get_google_image_search

api_key = os.environ.get('GOOGLE_CUSTOM_SEARCH_API_KEY')
engine_id = os.environ.get('GOOGLE_CUSTOM_SEARCH_ENGINE_ID')

result = get_google_image_search('LEGO Architecture Tokyo', api_key, engine_id)
print(result)  # Should print an image URL
```

### **Test Unsplash:**

```python
from image_fetcher import get_unsplash_image

access_key = os.environ.get('UNSPLASH_ACCESS_KEY')
result = get_unsplash_image('gift box', access_key)
print(result)  # Should print an image URL
```

---

## 🚀 How It Works in GiftWise

The image fetching follows this priority:

1. **Product Page** → Extract image from product URL (if direct product page)
2. **Google Custom Search** → Find product image using product name
3. **Unsplash** → Get evocative image if product image not found
4. **Placeholder** → Fallback if all else fails

**You don't need both APIs** - either one will improve image quality:
- **Google Custom Search** = Better for actual product images
- **Unsplash** = Better for beautiful evocative images

**Recommendation:** Start with Google Custom Search (more accurate for products), add Unsplash later if you want prettier fallback images.

---

## 💰 Pricing

### **Google Custom Search API:**
- **Free:** 100 searches/day
- **Paid:** $5 per 1,000 queries after free tier
- **For GiftWise:** Free tier should be plenty (100 recommendations/day = 100 image searches)

### **Unsplash API:**
- **Free:** 50 requests/hour
- **Paid:** $99/month for unlimited
- **For GiftWise:** Free tier should be plenty (50 recommendations/hour = 50 image requests)

---

## 🔒 Security Notes

1. **Never commit `.env` file** to Git
2. **Restrict Google API key** to Custom Search API only
3. **Keep API keys secret** - don't share publicly
4. **Rotate keys** if accidentally exposed

---

## 🐛 Troubleshooting

### **"No images appearing"**
- Check `.env` file has correct variable names
- Verify API keys are correct (no extra spaces)
- Check API quotas haven't been exceeded
- Look at server logs for error messages

### **"Google API error: 403"**
- API key might not be restricted correctly
- Custom Search API might not be enabled
- Check billing is enabled (even for free tier)

### **"Unsplash API error: 401"**
- Access key might be incorrect
- Check for extra spaces in `.env` file
- Verify application is approved (should be instant)

### **"Images work locally but not on Railway"**
- Make sure `.env` variables are set in Railway dashboard
- Go to Railway project → Variables → Add each variable
- Redeploy after adding variables

---

## 📋 Quick Checklist

- [ ] Google Cloud project created
- [ ] Custom Search API enabled
- [ ] API key created and copied
- [ ] Custom Search Engine created
- [ ] Search Engine ID copied
- [ ] Image search enabled in engine settings
- [ ] Unsplash developer account created
- [ ] Unsplash application created
- [ ] Access key copied
- [ ] Both keys added to `.env` file
- [ ] Tested locally
- [ ] Added to Railway environment variables (if deploying)

---

**That's it!** Once you add the API keys to your `.env` file, images will automatically start appearing in your recommendations. 🎉
