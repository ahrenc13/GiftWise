# 🧪 Simple Testing Guide for GiftWise

## You're a Beginner? Perfect! Follow These Steps:

---

## Step 1: Make Sure Everything is Set Up

### Check Your Environment Variables (in v0 sidebar)

Go to the **"Vars"** section in the v0 sidebar and make sure you have:

✅ **ANTHROPIC_API_KEY** - Your Claude API key  
✅ **NEXT_PUBLIC_SITE_URL** - Your site URL  
✅ **APIFY_API_TOKEN** - For Instagram/TikTok scraping (optional but recommended)

**Don't have these?**
- Anthropic API: Get free at https://console.anthropic.com
- Apify: Get free trial at https://console.apify.com

---

## Step 2: Deploy Your App

1. In v0, click the **"Publish"** button (top right)
2. This deploys your app to Vercel automatically
3. You'll get a URL like: `https://giftwise-xyz123.vercel.app`
4. Copy this URL!

---

## Step 3: Connect Supabase Database

1. In v0 sidebar, click **"Connect"**
2. Add **Supabase** integration
3. Once connected, go to the Supabase dashboard
4. Run the database migration:
   - Find your project in Supabase
   - Go to "SQL Editor"
   - Copy/paste the contents of `scripts/001_giftwise_schema.sql`
   - Click "Run"
   - You should see "Success" messages

---

## Step 4: Test the App Yourself

### A. Create an Account
1. Go to your deployed URL
2. Click **"Get Started"** or **"Sign Up"**
3. Enter your email and create a password
4. Check your email for confirmation link
5. Click the confirmation link
6. You're now logged in!

### B. Go to Dashboard
1. After logging in, you'll see your dashboard
2. You should see platform connection cards (Instagram, TikTok, etc.)

### C. Add a Test Profile
Let's use a real public Instagram account to test:

**Example public accounts you can test with:**
- Instagram: `natgeo` (National Geographic - great content)
- TikTok: `natgeo` 
- YouTube: `natgeo`
- Goodreads: Try any public username
- Last.fm: `last-fm-user` (or any active user)

**How to connect:**
1. Click **"Connect"** on Instagram card
2. Enter: `natgeo` (without @)
3. Click **"Add Profile"**
4. Wait 5-10 seconds - it's scraping their public posts!
5. You should see "Connected" status

### D. Enter Recipient Details
1. Scroll down to "Start New Recommendation"
2. Fill in the form:
   - **Recipient Name**: "Sarah" (or anyone)
   - **Age**: 28
   - **Location**: "San Francisco, CA"
   - **Relationship**: "Friend"
   - **Budget**: $50 - $200
3. Click **"Generate Recommendations"**

### E. Wait for Magic
1. You'll see a loading screen
2. This takes 30-60 seconds (Claude is working!)
3. **Don't refresh the page** - it's analyzing the social data

### F. View Recommendations
1. You should see 10-15 gift recommendations
2. Each has:
   - Product name and description
   - Why it's perfect for them
   - Price and where to buy
   - Confidence score
3. Scroll down to see **Bespoke Packages** - unique experience + gift combos!

---

## Step 5: Common Issues & Fixes

### "Session not found" error
- Make sure you ran the database migration in Step 3
- Try logging out and back in

### "Failed to connect platform" error
- Check that APIFY_API_TOKEN is set in environment variables
- Try a different username
- Make sure the profile is public, not private

### Recommendations not generating
- Check ANTHROPIC_API_KEY is set correctly
- Check the browser console for errors (F12 → Console tab)
- Make sure you connected at least one platform

### Page is blank / broken
- Check the v0 preview logs for errors
- Try clearing your browser cache
- Redeploy the app

---

## Step 6: Test Different Scenarios

### Scenario 1: Test Multiple Platforms
- Add Instagram `@natgeo`
- Add TikTok `@natgeo`
- Generate recommendations
- See how cross-platform data improves results

### Scenario 2: Test Different Recipients
- Try a younger person (age 22) vs older (age 45)
- Try different locations (NYC vs rural)
- Try different relationships (partner vs coworker)
- Notice how recommendations change!

### Scenario 3: Test Budget Ranges
- Try $20-50 budget
- Try $200-500 budget
- See how recommendations adjust

---

## Step 7: Check the Database

Want to see the raw data?

1. Go to Supabase dashboard
2. Click "Table Editor"
3. Browse tables:
   - **oauth_connections** - See connected platforms
   - **social_profiles** - See scraped data
   - **recommendation_sessions** - See all recommendation runs
   - **gift_products** - See individual gift recommendations
   - **bespoke_packages** - See experience packages

---

## What Success Looks Like

✅ You can sign up and log in  
✅ You can add public social profiles by username  
✅ You can generate recommendations in 30-60 seconds  
✅ You see 10-15 personalized gifts with reasoning  
✅ You see 3 bespoke experience packages  
✅ Everything looks good (not broken)  

---

## Advanced: Test Stripe Payments

1. In v0 sidebar → **"Connect"** → Add Stripe
2. Go to `/pricing` page
3. Try checking out with test card: `4242 4242 4242 4242`
4. Expiry: Any future date, CVC: Any 3 digits
5. Check Stripe dashboard to confirm payment worked

---

## Need Help?

### Debugging Steps:
1. Open browser console (F12 → Console)
2. Look for red error messages
3. Look for `[v0]` debug logs
4. Screenshot the error
5. Check if database tables exist in Supabase

### Common Fixes:
- **Clear cache** - Ctrl+Shift+R (Windows) or Cmd+Shift+R (Mac)
- **Redeploy** - Click "Publish" again in v0
- **Check env vars** - Make sure all keys are set
- **Check database** - Verify tables exist in Supabase

---

## You're Ready! 🎁

That's it! You now have a working AI-powered gift recommendation platform. Test it with real public profiles and see the magic happen.

**Pro tip:** The more platforms you connect, the better the recommendations. Instagram + TikTok + Pinterest gives the most comprehensive view of someone's interests.
