# 🚀 GIFTWISE COMPLETE SETUP GUIDE

## What You Just Got

A complete, production-ready multi-platform OAuth gift recommendation system with:
- ✅ Instagram OAuth integration
- ✅ Spotify OAuth integration
- ✅ Pinterest OAuth integration
- ✅ TikTok public scraping
- ✅ Multi-platform recommendation engine
- ✅ Beautiful responsive UI
- ✅ Stripe payment integration ready
- ✅ Amazon affiliate link support

---

## Quick Start (5 minutes to see it working locally)

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Set Up Environment
```bash
cp .env.template .env
# Edit .env with your API keys (see below for how to get them)
```

### Step 3: Run Locally
```bash
python giftwise_app.py
```

Visit: http://localhost:5000

**Note:** OAuth won't work yet - you need to set up the OAuth apps first (see below)

---

## Complete Setup Guide

### Part 1: Get Your API Keys (30-60 minutes first time)

#### 1. Anthropic API Key (5 minutes)
1. Go to https://console.anthropic.com
2. Sign up / log in
3. Go to API Keys
4. Create new key
5. Copy key to `.env` as `ANTHROPIC_API_KEY`

#### 2. Apify Token (5 minutes)
1. Go to https://console.apify.com
2. Sign up / log in
3. Go to Settings → Integrations
4. Copy API token
5. Add to `.env` as `APIFY_API_TOKEN`

---

### Part 2: Set Up OAuth Applications

#### Instagram OAuth (15-20 minutes)

**Steps:**
1. Go to https://developers.facebook.com
2. Click "My Apps" → "Create App"
3. Choose "Consumer" as app type
4. Fill in app details:
   - App Name: "Giftwise"
   - App Contact Email: your@email.com
5. Once created, go to "Add Products"
6. Find "Instagram" and click "Set Up"
7. Go to Instagram → Basic Display
8. Click "Create New App"
9. Fill in:
   - Client OAuth Settings:
     - Valid OAuth Redirect URIs: `http://localhost:5000/oauth/instagram/callback`
     - Deauthorize Callback URL: `http://localhost:5000/oauth/deauth`
     - Data Deletion Request URL: `http://localhost:5000/oauth/delete`
10. Click "Save Changes"
11. Copy:
    - Instagram App ID → `.env` as `INSTAGRAM_CLIENT_ID`
    - Instagram App Secret → `.env` as `INSTAGRAM_CLIENT_SECRET`

**For production:**
- Change redirect URI to `https://yourdomain.com/oauth/instagram/callback`
- Submit app for review (once you have 10+ test users)

---

#### Spotify OAuth (10 minutes)

**Steps:**
1. Go to https://developer.spotify.com/dashboard
2. Log in with Spotify account
3. Click "Create App"
4. Fill in:
   - App Name: "Giftwise"
   - App Description: "AI-powered gift recommendations"
   - Redirect URI: `http://localhost:5000/oauth/spotify/callback`
5. Accept terms and create
6. Click "Settings"
7. Copy:
   - Client ID → `.env` as `SPOTIFY_CLIENT_ID`
   - Client Secret → `.env` as `SPOTIFY_CLIENT_SECRET`

**For production:**
- Add production redirect URI in settings
- No review needed - Spotify OAuth works immediately

---

#### Pinterest OAuth (15 minutes)

**Steps:**
1. Go to https://developers.pinterest.com
2. Sign up / log in with Pinterest account
3. Click "Create app"
4. Fill in:
   - App name: "Giftwise"
   - Description: "AI gift recommendations"
   - Redirect URIs: `http://localhost:5000/oauth/pinterest/callback`
5. Accept terms and create
6. Go to app settings
7. Copy:
   - App ID → `.env` as `PINTEREST_CLIENT_ID`
   - App Secret → `.env` as `PINTEREST_CLIENT_SECRET`

**For production:**
- Add production redirect URI
- Submit for review once you have working product

---

### Part 3: Test Everything Locally

#### 1. Create .env file
```bash
SECRET_KEY=your-random-secret-key-here
ANTHROPIC_API_KEY=sk-ant-api03-YOUR_KEY
APIFY_API_TOKEN=apify_api_YOUR_TOKEN

INSTAGRAM_CLIENT_ID=your_instagram_id
INSTAGRAM_CLIENT_SECRET=your_instagram_secret
INSTAGRAM_REDIRECT_URI=http://localhost:5000/oauth/instagram/callback

SPOTIFY_CLIENT_ID=your_spotify_id
SPOTIFY_CLIENT_SECRET=your_spotify_secret
SPOTIFY_REDIRECT_URI=http://localhost:5000/oauth/spotify/callback

PINTEREST_CLIENT_ID=your_pinterest_id
PINTEREST_CLIENT_SECRET=your_pinterest_secret
PINTEREST_REDIRECT_URI=http://localhost:5000/oauth/pinterest/callback
```

#### 2. Run the app
```bash
python giftwise_app.py
```

#### 3. Test the flow
1. Visit http://localhost:5000
2. Click "Start Free Trial"
3. Enter email
4. Connect platforms (start with Spotify - easiest)
5. Generate recommendations
6. Check results!

---

### Part 4: Deploy to Production

#### Option A: Deploy to Railway (Recommended - Easiest)

**Steps:**
1. Sign up at https://railway.app
2. Click "New Project" → "Deploy from GitHub"
3. Connect your GitHub repo
4. Add environment variables in Railway dashboard
5. Deploy!

**Your app will be at:** `https://your-app.railway.app`

**Update OAuth redirect URIs to:**
- Instagram: `https://your-app.railway.app/oauth/instagram/callback`
- Spotify: `https://your-app.railway.app/oauth/spotify/callback`
- Pinterest: `https://your-app.railway.app/oauth/pinterest/callback`

---

#### Option B: Deploy to Heroku

```bash
# Install Heroku CLI
heroku login
heroku create giftwise-app

# Add environment variables
heroku config:set ANTHROPIC_API_KEY=your_key
heroku config:set SPOTIFY_CLIENT_ID=your_id
# ... etc for all env vars

# Deploy
git push heroku main
```

---

#### Option C: Deploy to Your Own Server (Digital Ocean, AWS, etc.)

1. Set up Ubuntu server
2. Install Python 3.11+
3. Clone your repo
4. Install requirements
5. Set up nginx reverse proxy
6. Use gunicorn to run Flask app
7. Set up SSL with Let's Encrypt

---

### Part 5: Add Stripe Payment (Optional for MVP)

**Setup:**
1. Create Stripe account at https://stripe.com
2. Go to Products → Add Product
3. Name: "Giftwise Pro"
4. Price: $4.99/month (recurring)
5. Copy Price ID
6. Add to `.env` as `STRIPE_PRICE_ID`
7. Get API keys from Developers → API Keys
8. Add Secret Key to `.env` as `STRIPE_SECRET_KEY`

**Create payment link:**
1. In Stripe, go to Payment Links → New
2. Select your product
3. Customize success/cancel URLs
4. Get link
5. Update landing page CTA button

---

### Part 6: Add Amazon Associates (For Monetization)

**Setup:**
1. Sign up at https://affiliate-program.amazon.com
2. Get your Associate ID (e.g., "giftwise-20")
3. Update `recommendation_engine.py`:
   - Find `create_amazon_search_url()` function
   - Add your associate ID as parameter

**Link format:**
```python
def create_amazon_search_url(product_name, associate_id="giftwise-20"):
    query = urllib.parse.quote_plus(product_name)
    return f"https://www.amazon.com/s?k={query}&tag={associate_id}"
```

---

## File Structure

```
giftwise/
├── giftwise_app.py              # Main Flask application
├── platform_integrations.py     # OAuth data fetching
├── recommendation_engine.py     # Claude recommendation generation
├── requirements.txt             # Python dependencies
├── .env                         # Environment variables (DO NOT COMMIT)
├── .env.template                # Template for .env
└── templates/
    ├── index.html               # Landing page
    ├── signup.html              # Email signup
    ├── connect_platforms.html   # Platform connection dashboard
    ├── generating.html          # Loading/generating page
    └── recommendations.html     # Results display
```

---

## How It Works

### User Flow:
1. **Landing Page** (`/`) → User sees demo recommendations
2. **Sign Up** (`/signup`) → User enters email
3. **Connect Platforms** (`/connect-platforms`) → User connects 2+ platforms
4. **Generate** (`/generate-recommendations`) → Shows loading screen
5. **API Call** (`/api/generate-recommendations`) → Fetches data + generates recs
6. **Results** (`/recommendations`) → Shows 10 specific recommendations

### OAuth Flow:
1. User clicks "Connect Instagram"
2. Redirects to Instagram OAuth
3. User approves
4. Instagram redirects back with code
5. Exchange code for access token
6. Store token in database
7. Return to platform connection page

### Data Fetching:
```python
# When generating recommendations:
1. Fetch Instagram data (OAuth API)
2. Fetch Spotify data (OAuth API)
3. Fetch Pinterest data (OAuth API)
4. Fetch TikTok data (public scraping via Apify)
5. Build context from all platforms
6. Send to Claude for recommendation generation
7. Parse and display results
```

---

## Troubleshooting

### OAuth redirect URI mismatch
**Error:** "Redirect URI mismatch"
**Fix:** Make sure redirect URI in `.env` EXACTLY matches what's in the OAuth app settings

### Instagram OAuth not working
**Error:** "Invalid client"
**Fix:** 
1. Check Instagram App ID and Secret are correct
2. Make sure you're using Instagram Basic Display, not Instagram Graph API
3. Add your Instagram account as a test user

### Spotify 400 error
**Error:** "Invalid grant"
**Fix:** Make sure redirect URI includes `http://` or `https://` scheme

### Pinterest OAuth fails
**Error:** Various Pinterest errors
**Fix:** Pinterest OAuth can be finicky. Make sure:
1. App is in "dev" mode
2. Redirect URI is exact match
3. Scope is correct (`boards:read pins:read user_accounts:read`)

### Recommendations failing
**Error:** "Error generating recommendations"
**Fix:** 
1. Check Anthropic API key is valid
2. Make sure at least 2 platforms are connected
3. Check platform data is being fetched successfully (add print statements)

---

## Database Considerations

**Current:** Using Python `shelve` (simple file-based storage)
- ✅ Works great for MVP
- ✅ No setup required
- ✅ Persists data
- ⚠️ Not scalable past ~100 users

**For production** (when you have 100+ users):

Upgrade to PostgreSQL:
```bash
pip install psycopg2-binary sqlalchemy
```

Create database schema:
```python
from sqlalchemy import create_engine, Column, String, JSON
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    email = Column(String, primary_key=True)
    platforms = Column(JSON)
    recommendations = Column(JSON)
    created_at = Column(String)
```

---

## Next Steps After Setup

### Week 1:
- [ ] Get all OAuth apps approved
- [ ] Test with 3-5 friends
- [ ] Fix any bugs
- [ ] Deploy to Railway/Heroku

### Week 2:
- [ ] Add Stripe payment
- [ ] Set up Amazon Associates
- [ ] Create beta user list (10 people)

### Week 3:
- [ ] Launch to beta users
- [ ] Collect feedback
- [ ] Iterate on recommendations

### Week 4:
- [ ] Public launch
- [ ] Post to Reddit (r/SideProject, r/Entrepreneur)
- [ ] Share on social media

---

## Support

If you get stuck:
1. Check this guide first
2. Check OAuth app settings (most common issue)
3. Look at error messages in terminal
4. Check browser console for frontend errors

---

## Security Notes

**IMPORTANT:**
- Never commit `.env` file to git
- Add `.env` to `.gitignore`
- Use environment variables for all secrets
- Rotate keys if accidentally exposed
- Use HTTPS in production (required for OAuth)

---

## You're Ready to Launch! 🚀

You now have:
- ✅ Complete OAuth integration
- ✅ Multi-platform recommendation engine
- ✅ Beautiful UI
- ✅ Stripe ready
- ✅ Amazon affiliate ready
- ✅ Production deployment guide

**Next:** Get your OAuth apps set up and start testing!
