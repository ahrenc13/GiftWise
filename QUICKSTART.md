# ⚡ Quick Start - Get GiftWise Running in 10 Minutes

## What You Need (Free Accounts)

1. **Anthropic API Key** (Required)
   - Go to: https://console.anthropic.com
   - Sign up → Create API key
   - Copy it somewhere safe

2. **Apify Token** (Optional but recommended)
   - Go to: https://console.apify.com
   - Sign up → Get API token
   - Free tier gives you $5/month credit

---

## 3 Simple Steps to Launch

### Step 1: Add Your API Keys (2 minutes)

In the v0 interface:
1. Look for the sidebar on the left
2. Click **"Vars"** (Variables)
3. Add these:
   - `ANTHROPIC_API_KEY` = paste your Claude API key
   - `APIFY_API_TOKEN` = paste your Apify token (optional)
   - `NEXT_PUBLIC_SITE_URL` = your app URL (get this in Step 2)

### Step 2: Deploy the App (3 minutes)

1. Click the **"Publish"** button (top right in v0)
2. Wait for deployment to finish
3. Copy your app URL (looks like: `giftwise-abc123.vercel.app`)
4. Go back to Step 1 and update `NEXT_PUBLIC_SITE_URL` with this URL
5. Click "Publish" one more time to update

### Step 3: Set Up Database (5 minutes)

1. In v0 sidebar → Click **"Connect"**
2. Add **Supabase** integration
3. Wait for it to connect (30 seconds)
4. Click the Supabase link to open dashboard
5. In Supabase dashboard:
   - Click **"SQL Editor"** (left sidebar)
   - Click **"New Query"**
   - Go back to v0 and copy ALL of `scripts/001_giftwise_schema.sql`
   - Paste into Supabase SQL Editor
   - Click **"Run"**
   - Should see green success messages

---

## Test It Works

1. Go to your app URL
2. Click **"Get Started"**
3. Sign up with your email
4. Check email for confirmation link
5. Click confirmation → You're in!
6. On dashboard, click **"Connect"** on Instagram
7. Type: `natgeo` (National Geographic's public account)
8. Click **"Add Profile"**
9. Fill in recipient form:
   - Name: Sarah
   - Age: 28  
   - Location: San Francisco, CA
   - Budget: $50-200
10. Click **"Generate Recommendations"**
11. Wait 30-60 seconds
12. See personalized gift recommendations!

---

## You're Live!

That's it. You now have a working AI gift recommendation platform.

**What to test:**
- Try different public Instagram usernames
- Try different ages/locations/budgets
- See how recommendations change

**Next steps:**
- Add TikTok, Pinterest, YouTube usernames for richer data
- Set up Stripe for payments (optional)
- Share with friends to test

---

## Troubleshooting

**Error: "Session not found"**
→ Database not set up. Go back to Step 3.

**Error: "Failed to connect platform"**
→ Check APIFY_API_TOKEN is set in Step 1. Or the profile is private.

**No recommendations showing**
→ Check ANTHROPIC_API_KEY is correct. Check browser console (F12) for errors.

**Need more help?**
→ Read TESTING.md for detailed troubleshooting.
