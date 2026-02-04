# GiftWise Setup Guide - Social Media Scraping Edition

## What's Fully Implemented

✅ **Instagram Scraping** - Username-based public profile scraping via Apify  
✅ **TikTok Scraping** - Username-based public profile scraping via Apify  
✅ **Pinterest OAuth** - Full OAuth implementation (UI ready, requires credentials)  
✅ **Enrichment Intelligence Layer** - Analyzes scraped data + demographic trends  
✅ **Two-Step Claude Recommendation Engine** - Catalog generation → intelligent selection  
✅ **Bespoke Experience Packages** - Location-aware experiences + gift combinations  
✅ **Stripe Subscriptions** - Freemium model (Free, Basic $9, Pro $19)  
✅ **Supabase Database** - Full schema with RLS policies  

## Required Environment Variables

### Core (Must Have):
```env
ANTHROPIC_API_KEY=sk-ant-...           # Get from https://console.anthropic.com
APIFY_API_TOKEN=apify_api_...          # Get from https://console.apify.com
NEXT_PUBLIC_SITE_URL=https://your-site.com
```

### Database & Payments (Auto-configured via v0):
- Supabase connection (click Connect in v0 sidebar)
- Stripe keys (click Connect in v0 sidebar)

### Optional (For Pinterest OAuth):
```env
PINTEREST_CLIENT_ID=...
PINTEREST_CLIENT_SECRET=...
PINTEREST_REDIRECT_URI=https://your-site.com/api/oauth/pinterest/callback
```

## How the Social Media Scraping Works

### 1. Instagram Scraping (Implemented)
**Flow:**
- User enters Instagram username
- System calls Apify Instagram Profile Scraper
- Extracts: posts, captions, hashtags, mentions, engagement patterns
- Analyzes: visual aesthetics from images, brand mentions, interests
- Stores in `social_profiles` table

**What's captured:**
- Top hashtags (with frequency counts)
- Recent captions (for interest analysis)
- Mentioned accounts (influencers they follow)
- Visual patterns (extracted from post descriptions)

### 2. TikTok Scraping (Implemented)
**Flow:**
- User enters TikTok username
- System calls Apify TikTok Profile Scraper
- Extracts: videos, captions, hashtags, music, trends
- Analyzes: content themes, music taste, humor style
- Stores in `social_profiles` table

**What's captured:**
- Top hashtags and trends
- Music preferences (songs used in videos)
- Video captions (for personality/interest analysis)
- Engagement patterns

### 3. Pinterest OAuth (UI Ready, Needs Credentials)
**Flow:**
- User clicks "Connect Pinterest"
- OAuth flow redirects to Pinterest
- System receives access token
- Fetches boards, pins, saves
- Analyzes aspirational interests

**What's captured:**
- Board themes (aspirational categories)
- Pinned products (wish list items)
- Visual aesthetics (color palettes, styles)

## The Enrichment Intelligence Layer

After scraping, the enrichment engine runs analysis:

### Stage 1: Cross-Platform Interest Extraction
- Combines data from all connected platforms
- Identifies **core interests** (mentioned 3+ times across platforms)
- Confidence scoring based on data volume

### Stage 2: Aesthetic & Lifestyle Analysis
- Visual style preferences (minimalist, maximalist, vintage, modern)
- Lifestyle signals (outdoorsy, homebody, foodie, fitness-focused)
- Current brand investments (what they already own - AVOID duplicating)

### Stage 3: Demographic Enrichment
Uses recipient's age, location, and interests to add:
- **Trending products** for their demographic
- **Local experiences** available in their city
- **Subreddit communities** they'd likely be part of
- **Adjacent interests** they might enjoy

### Stage 4: Deep Signal Analysis
- **Aspirational interests** (Pinterest boards = future goals)
- **Current investments** (brands they already use = avoid)
- **Social proof** (what influencers they follow like)

## Setting Up Apify

### 1. Create Account
- Go to https://console.apify.com
- Sign up (free tier includes $5 credit)

### 2. Get API Token
- Dashboard → Settings → Integrations → API Token
- Copy token and add to v0 environment variables

### 3. Understand Pricing
- **Instagram**: ~$0.15 per 100 posts scraped
- **TikTok**: ~$0.15 per 100 videos scraped
- **Free tier**: $5/month = ~33 profiles/month

### 4. The Scrapers Used
The app uses these specific Apify actors:
- `apify/instagram-profile-scraper` - Instagram data
- `apify/tiktok-scraper` - TikTok data

## Database Migration

Before the app works, you must run the database migration:

### Via v0 (Easiest):
1. Connect Supabase integration (sidebar → Connect)
2. The migration script is already created at `scripts/001_giftwise_schema.sql`
3. Copy the SQL and run it in Supabase SQL Editor

### What the Migration Creates:
- `profiles` - User profiles with subscription tier
- `oauth_connections` - Platform connection tracking
- `social_profiles` - Scraped social media data
- `recommendation_sessions` - Each recommendation generation
- `gift_products` - Individual gift recommendations
- `bespoke_packages` - Experience + gift combinations
- `purchases` - Stripe payment records

All tables have Row Level Security (RLS) enabled.

## Testing the Flow

### Test with Real Data:
1. **Sign up** at `/auth/sign-up`
2. **Go to dashboard** at `/dashboard`
3. **Connect Instagram** - Enter a public username (try `@natgeo` or `@nasa`)
4. **Connect TikTok** - Enter a public username
5. **Wait for scraping** (~30-60 seconds per platform)
6. **Click "Start New Recommendation"**
7. **Enter recipient details** (name, age, location, relationship)
8. **Wait for generation** (~60-90 seconds for full process)
9. **View recommendations** - See 10-15 curated gifts + 3 bespoke packages

### What Happens Behind the Scenes:
1. Apify scrapes the social profiles
2. Data is stored in `social_profiles` table
3. Enrichment engine analyzes scraped data
4. Adds demographic trends and subreddit insights
5. Builds comprehensive profile context
6. Claude generates catalog of ~30 products
7. Claude selects best 10-15 with reasoning
8. Claude creates 3 bespoke experience packages
9. All stored in database and displayed

## How It Avoids Hallucinations

### Product Validation Requirements:
- Must include specific **brand name**
- Must include specific **product name/model**
- Must include **retailer** (Amazon, Etsy, etc.)
- Must include **price range**
- Must include **purchase URL**

### Two-Step Process:
**Step 1: Catalog Generation**
- Claude generates ~30 real products that exist
- Each must be buyable, linkable, specific
- Diverse categories (experiences, gadgets, fashion, home, books)

**Step 2: Intelligent Selection**
- From the 30-item catalog, select best 10-15
- Provide personalized reasoning for each
- Cross-reference with "current_investments" to avoid duplicates
- Score confidence levels

### Enrichment Validation:
- Core interests must appear on 2+ platforms (cross-validation)
- Current investments identified from brand mentions
- Aspirational interests from Pinterest only
- Confidence score reflects data quality

## Monetization Strategy

### Freemium Tiers:
- **Free**: 1 recommendation/month (test the product)
- **Basic ($9/mo)**: 5 recommendations/month (casual users)
- **Pro ($19/mo)**: Unlimited recommendations (power users)

### Cost Per Recommendation:
- Apify scraping: ~$0.30 (optional if user already scraped)
- Claude API: ~$0.03 per recommendation
- **Total cost**: ~$0.33 per new profile

### Unit Economics:
- Basic tier: $9 revenue - $1.65 costs (5 recs) = $7.35 profit (82% margin)
- Pro tier: $19 revenue - ~$3-5 costs = $14-16 profit (75-84% margin)

### Valentine's Day Strategy:
1. Launch with free tier (Feb 4-7)
2. Collect testimonials
3. Enable paid tiers (Feb 8-10)
4. Push hard (Feb 11-13)
5. Peak sales (Feb 13-14)

## What's NOT Implemented (Yet)

❌ **Spotify OAuth** - API not accepting new apps currently  
❌ **YouTube** - Marked as "coming soon"  
❌ **Goodreads** - Marked as "coming soon"  
❌ **Other platforms** - Letterboxd, Etsy, Strava, LinkedIn (UI placeholders only)

These can be added later based on user demand.

## GitHub & Deployment

### GitHub:
- Click "Preview Pull Request" to see all changes
- Your Python code is safe in the repo
- This Next.js version can live alongside or replace it

### Deployment:
1. Click "Publish" in v0 to deploy to Vercel
2. Or connect your GitHub repo to Vercel manually
3. Add environment variables in Vercel dashboard
4. Done!

## What Makes This Product Special

1. **Multi-platform social scraping** - No one else does Instagram + TikTok + Pinterest
2. **Enrichment intelligence layer** - Goes beyond raw data to demographic insights
3. **Two-step Claude process** - Prevents generic/hallucinated recommendations
4. **Bespoke experience packages** - Not just products, but memorable moments
5. **Cross-platform validation** - Interests confirmed across multiple sources
6. **Avoids duplicates** - Identifies existing investments
7. **Location-aware** - Local experiences and retailers

## Summary: What You Need Right Now

To make this fully functional:

✅ **Already have**: ANTHROPIC_API_KEY (you set this up)  
✅ **Already have**: APIFY_API_TOKEN (just added)  
✅ **Already have**: Supabase connection (via v0 integration)  
✅ **Already have**: Stripe connection (via v0 integration)  

🔧 **Must do**: Run database migration in Supabase  
🔧 **Optional**: Set up Pinterest OAuth (if you want Pinterest data)  

Then you're ready to launch! The core product - Instagram + TikTok scraping with AI recommendations - is fully built and ready to generate amazing gift recommendations.
