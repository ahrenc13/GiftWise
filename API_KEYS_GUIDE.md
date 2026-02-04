# Getting API Keys - Step by Step

This guide will walk you through getting YouTube, Last.fm, and SerpAPI keys. All are **free** (with generous free tiers) and take about 5-10 minutes each.

---

## YouTube API Key

**What it does:** Lets us see public YouTube channels, subscriptions, and playlists

### Step-by-Step:

1. **Go to Google Cloud Console**
   - Open: https://console.cloud.google.com/
   - Sign in with your Google account (any Gmail will work)

2. **Create a New Project**
   - Click the project dropdown at the top (says "Select a project")
   - Click "NEW PROJECT" button
   - Name it: `GiftWise` (or anything you want)
   - Click "CREATE"
   - Wait 30 seconds for it to create

3. **Enable YouTube Data API**
   - In the search bar at top, type: `YouTube Data API v3`
   - Click on "YouTube Data API v3" in results
   - Click the blue "ENABLE" button
   - Wait for it to enable (5-10 seconds)

4. **Create API Key**
   - Click "CREATE CREDENTIALS" button (top right)
   - Select "API key" from the dropdown
   - A popup will show your API key - it looks like: `AIzaSyB...` (long random string)
   - **Copy this entire key** - you'll paste it into v0 later

5. **Secure Your Key (Optional but Recommended)**
   - Click "RESTRICT KEY"
   - Under "API restrictions":
     - Select "Restrict key"
     - Check only "YouTube Data API v3"
   - Click "SAVE"

**You're done with YouTube!** Keep that key handy.

---

## Last.fm API Key

**What it does:** Lets us see public music listening history and favorite artists

### Step-by-Step:

1. **Create Last.fm Account (if needed)**
   - Go to: https://www.last.fm/
   - Click "Sign Up" if you don't have an account
   - Use any email - you don't need to actually use Last.fm

2. **Go to API Account Creation**
   - Visit: https://www.last.fm/api/account/create
   - You should be logged in already

3. **Fill Out the Form**
   - **Application name:** `GiftWise`
   - **Application description:** `AI-powered gift recommendation platform`
   - **Application homepage:** Your website URL (or just put `https://giftwise.app` for now)
   - **Callback URL:** Leave blank (we're not using OAuth for public data)
   - Check the agreement box
   - Click "Submit"

4. **Get Your API Key**
   - You'll see a page with:
     - **API key:** A long string like `1234567890abcdef...`
     - **Shared secret:** Another string (you don't need this for public data)
   - **Copy the API key** (just the API key, not the secret)

**You're done with Last.fm!** Keep that key handy.

---

## Add Keys to Your Project

Now that you have both keys:

### In v0:

1. Click the sidebar (left side)
2. Go to "Vars" section
3. Click "Add Variable"
4. Add these two:

   **First variable:**
   - Name: `YOUTUBE_API_KEY`
   - Value: `[paste your YouTube key here]`
   - Click "Add"

   **Second variable:**
   - Name: `LASTFM_API_KEY`
   - Value: `[paste your Last.fm key here]`
   - Click "Add"

That's it! Your app can now scrape YouTube and Last.fm data.

---

## Testing Your Keys

To make sure they work:

1. Deploy your app (click "Publish" in v0)
2. Go to your dashboard
3. Try connecting a YouTube channel:
   - Click "YouTube" under "Additional Platforms"
   - Enter a public username like: `mkbhd` or `natgeo`
   - Click "Add Profile"

If it works, you'll see "Connected" - that means your YouTube API key is working!

For Last.fm:
   - Try username: `rj` (Last.fm founder, very active profile)
   - Should connect and pull music data

---

## Cost & Limits

**YouTube API:**
- **Free tier:** 10,000 queries/day (plenty for testing)
- **Cost after:** Free for most use cases
- Each profile scrape uses ~5-10 queries

**Last.fm API:**
- **Completely free**
- No limits for public data
- Unlimited usage

You won't pay anything for normal usage!

---

## Troubleshooting

**YouTube key not working?**
- Make sure you enabled "YouTube Data API v3" (not just "YouTube API")
- Check that you copied the entire key (starts with `AIza`)
- Try creating a new unrestricted key first, then restrict it after testing

**Last.fm key not working?**
- Make sure you copied the API key, not the shared secret
- Check that you're logged into Last.fm when creating it
- The key should be 32 characters (hexadecimal)

**Still stuck?**
- Double-check the key is pasted correctly in v0 Vars (no extra spaces)
- Try redeploying after adding the keys
- Check the browser console for specific error messages

---

## SerpAPI Key (Real-Time Enrichment)

**What it does:** Provides real-time trending products, Reddit insights, demographic trends, and bestseller data

**Free tier:** 100 searches/month free (should be enough for testing)

### Step-by-Step:

1. **Sign Up**
   - Go to: https://serpapi.com/
   - Click "Register" in top right
   - Enter your email and create a password
   - Check your email and verify your account

2. **Get Your API Key**
   - Once logged in, you'll see your dashboard
   - Your API key is displayed right at the top
   - It looks like: `a1b2c3d4e5...` (64 characters)
   - Click "Copy" to copy the entire key

3. **Check Your Usage**
   - Free tier: 100 searches/month
   - Each gift recommendation uses ~5-10 searches
   - So you can generate ~10-20 gift recommendations/month for free
   - Paid plans start at $50/month for 5,000 searches if you need more

**You're done with SerpAPI!**

### What This Adds to Your Gift Recommendations:

- **Trending products** - What's hot right now in their interest categories
- **Reddit insights** - Popular gift recommendations from relevant communities
- **Demographic trends** - What people their age/location are into
- **Bestsellers** - Top-rated products in each category
- **Real-time validation** - Ensures recommended products are actually available

---

## Next Steps

Once all three keys are working:

1. ✅ YouTube will pull: subscribed channels, playlists, video interests
2. ✅ Last.fm will pull: top artists, tracks, genres, listening history
3. ✅ SerpAPI will add: trending products, Reddit insights, bestsellers, demographic data
4. ✅ This all feeds into the enrichment engine for maximum gift recommendation accuracy

These platforms give rich signals about interests without requiring the recipient to authorize anything - perfect for surprise gifts!

---

## Note on OAuth vs Public Data

**What we're using now:** Public data scraping (username-based)
- No recipient permission needed
- Perfect for surprise gifts
- Limited to what's publicly visible

**Future OAuth features** (for wishlists/subscription boxes):
- Users create their own gift wishlists
- More detailed data access
- Subscription box personalization
- Requires user to log in and authorize

For now, we're focused on the surprise gift use case with public data!
