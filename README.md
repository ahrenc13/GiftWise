# 🎁 GiftWise - AI-Powered Gift Recommendations

## Modern Next.js App with Claude AI

A beautiful, production-ready gift recommendation platform that uses AI to analyze social profiles and suggest thoughtful, personalized gifts. Built with Next.js 16, Supabase, Stripe, and Claude AI.

### Core Features
- Multi-platform profile analysis (Instagram, TikTok, Pinterest, Spotify)
- Claude AI-powered gift curation (~30 products → top 10-15 selections)
- Bespoke experience packages (experiences + complementary gifts)
- Freemium model with Stripe subscriptions
- Beautiful, human-feeling design (warm colors, serif typography)

---

## 🚀 Tech Stack

- **Framework**: Next.js 16 with App Router and React 19
- **Database**: Supabase (PostgreSQL with Row Level Security)
- **AI**: Anthropic Claude 3.5 Sonnet
- **Payments**: Stripe Checkout & Subscriptions
- **Styling**: Tailwind CSS with custom design tokens
- **Typography**: DM Serif Display (headings) + Inter (body)
- **Deployment**: Optimized for Vercel

---

## 📁 Project Structure

```
app/
├── page.tsx                           # Landing page with pricing
├── dashboard/page.tsx                 # Connect platforms & start recs
├── recommendations/[sessionId]/       # Display curated gifts
├── pricing/                           # Stripe checkout flow
├── auth/                              # Supabase authentication
└── api/
    ├── generate-recommendations/      # Claude recommendation engine
    └── generate-bespoke-packages/     # Experience package creation

components/
├── connect-platform-button.tsx        # OAuth connection UI
├── start-recommendation-button.tsx    # Start recommendation flow
├── bespoke-packages.tsx              # Display experience packages
└── checkout.tsx                      # Stripe checkout embed

lib/
├── supabase/                         # Supabase clients (server/client)
├── products.ts                       # Stripe product catalog
└── stripe.ts                         # Stripe server client

scripts/
└── 001_giftwise_schema.sql           # Database schema migration
```

---

## 🚀 Quick Start

### 1. Set Up Integrations (v0 Sidebar)

**Connect Supabase:**
1. Go to "Connect" in the sidebar
2. Add Supabase integration
3. This creates your database and adds env vars automatically

**Connect Stripe:**
1. Go to "Connect" in the sidebar  
2. Add Stripe integration
3. Get test API keys for development

### 2. Add Environment Variables (v0 Sidebar)

Go to "Vars" in the sidebar and add:
- `ANTHROPIC_API_KEY` - Get from https://console.anthropic.com
- `NEXT_PUBLIC_SITE_URL` - Your site URL (e.g., https://giftwise.vercel.app)

### 3. Run Database Migration

Execute `scripts/001_giftwise_schema.sql` via the Supabase dashboard or v0 sidebar.

### 4. Deploy

Click "Publish" in v0 to deploy to Vercel automatically!

---

## 🎯 How It Works

### User Flow:
1. **Sign up** → Create account with Supabase auth
2. **Connect platforms** → Link Instagram, TikTok, Pinterest, Spotify via OAuth/Apify
3. **Enter recipient info** → Name, age, location, relationship
4. **Start generation** → Trigger AI analysis (processing takes ~30-60 seconds)
5. **View recommendations** → See 10-15 curated gifts with reasoning
6. **Explore bespoke packages** → Experience + gift combinations tailored to them
7. **Upgrade for more** → Free tier (1/month) → Paid plans (unlimited)

### AI Recommendation Process:

**Step 1: Profile Building**
- Scrape connected social platforms for interests, aesthetics, locations
- Extract: music taste, visual style, hobbies, aspirations, existing items
- Build comprehensive recipient profile with cross-platform validation

**Step 2: Catalog Generation (Claude)**
- Prompt Claude to generate ~30 real, buyable gift ideas
- Include: exact product names, brands, models, retailers, prices
- Ensure products exist, have images, and are purchasable online
- Mix categories: experiences, gadgets, fashion, home, books, etc.

**Step 3: Selection & Curation (Claude)**
- From the 30-item catalog, select the best 10-15 gifts
- Provide personalized reasoning for each selection
- Score confidence levels and match percentages
- Avoid items they likely already own (from social data)

**Step 4: Bespoke Packages (Claude)**
- Create 3 unique experience + gift combinations
- Personalized to their location, interests, personality
- Include realistic pricing and shopping links
- Each package tells a cohesive story

---

## 🔑 Required API Keys

### Core (Required):
1. **Anthropic API Key** - Get from https://console.anthropic.com
   - Free tier available, then ~$0.03 per recommendation
2. **Supabase Project** - Auto-configured via v0 integration
3. **Stripe Account** - Auto-configured via v0 integration (optional but recommended)

### OAuth Platforms (Recommended):
For best results, set up OAuth apps for social platforms:

1. **Apify** - For Instagram/TikTok scraping
   - https://console.apify.com
   - Free tier: $5/month credit
   
2. **Spotify API** - For music taste analysis
   - https://developer.spotify.com/dashboard
   - Free, takes 10 minutes to set up

3. **Pinterest API** - For visual/aspiration analysis  
   - https://developers.pinterest.com
   - Free, takes 15 minutes to set up

*Note: OAuth setup is optional for MVP - you can start with manual profile input and add OAuth later.*

---

## ✨ Key Features

### AI-Powered Curation
- Two-step Claude process: catalog generation → intelligent selection
- Product validation with real URLs, prices, and images
- Avoids hallucinations by requiring specific brands/models
- Personalized reasoning for each recommendation
- Cross-platform signal validation for accuracy

### Bespoke Experience Packages
- Combines experiences (dinners, concerts, classes) with complementary gifts
- Location-aware suggestions based on recipient's city
- Cohesive themes that tell a story
- Realistic pricing with shopping links
- 3 unique packages per recommendation session

### Beautiful, Human Design
- Warm color palette (rose, terracotta, sage green, cream)
- DM Serif Display for personality, Inter for readability
- Personal language ("for them", "thoughtfully curated")
- Generous spacing and breathing room
- No generic AI aesthetic - feels like a thoughtful friend

### Freemium Monetization
- Free tier: 1 recommendation per month
- Basic ($9/mo): 5 recommendations  
- Pro ($19/mo): Unlimited recommendations
- Stripe-powered subscriptions with automatic billing
- Valentine's Day timing for seasonal boost

---

## 💰 Business Model

**Freemium Subscription:**
- Free: 1 recommendation/month
- Basic ($9/mo): 5 recommendations/month  
- Pro ($19/mo): Unlimited recommendations

**Cost Structure:**
- Claude API: ~$0.03 per recommendation
- Apify scraping: ~$0.30 per recipient (optional)
- Stripe fees: 2.9% + $0.30
- Hosting: Free on Vercel (hobby tier)

**Potential Revenue Streams:**
- Subscriptions (primary)
- Amazon affiliate links (secondary)
- Gift concierge service for high-value users (future)

---

## 🔒 Security & Best Practices

- Row Level Security (RLS) on all Supabase tables
- Server-side price validation for Stripe
- HTTP-only cookies for sessions
- OAuth 2.0 for social platform connections
- Environment variables for all secrets
- Input validation and sanitization
- Proper error handling throughout

---

## 🚀 Deployment

### Deploy to Vercel (Recommended):
1. Click "Publish" in v0 (deploys automatically)
2. Or: Connect your GitHub repo to Vercel
3. Add environment variables in Vercel dashboard
4. Deploy!

### Database Setup:
1. Connect Supabase integration in v0
2. Execute `scripts/001_giftwise_schema.sql` 
3. Verify tables created successfully

### Production Checklist:
- ✅ Supabase project connected
- ✅ Stripe account configured (or use test mode)
- ✅ Anthropic API key added
- ✅ Database migration executed
- ✅ Test signup → connect platforms → generate recommendations
- ✅ Verify Stripe checkout works

---

## 🎯 Next Steps

### Immediate (This Week):
1. **Test the full flow** - Sign up, connect platforms (manually for now), generate recommendations
2. **Set up Anthropic API** - Get API key from https://console.anthropic.com
3. **Deploy to production** - Click Publish in v0
4. **Test with 3-5 friends** - Get real user feedback

### Short-term (Next 2 Weeks):
1. **Set up OAuth apps** - Apify, Spotify, Pinterest for real social data
2. **Refine prompts** - Improve Claude's recommendations based on feedback
3. **Add more gift sources** - Etsy, specialty retailers beyond Amazon
4. **Valentine's launch** - Soft launch to capture seasonal demand

### Medium-term (Month 2):
1. **Collect feedback** - Iterate on UI/UX and recommendation quality
2. **Add sharing** - Let users share their recommendations ("Wish List")
3. **Build waitlist/referrals** - Viral growth mechanics
4. **Scale marketing** - Reddit, Product Hunt, Instagram ads

### Future Features:
- Gift history tracking (avoid re-gifting)
- Collaboration mode (split costs with others)
- Occasion reminders (birthdays, anniversaries)
- Group gifting pools
- AI chat interface for refinement

---

## 🐛 Troubleshooting

**"Session not found" errors:**
- Check that Supabase is properly connected
- Verify database migration ran successfully

**Recommendations not generating:**
- Confirm ANTHROPIC_API_KEY is set correctly
- Check API quota hasn't been exceeded
- Verify Claude API endpoint is accessible

**Stripe checkout not working:**
- Make sure Stripe integration is connected
- Check that products are configured in lib/products.ts
- Verify STRIPE_SECRET_KEY is present

---

## 📝 Database Schema

Key tables (see `scripts/001_giftwise_schema.sql`):
- **profiles** - User profiles with subscription tier
- **oauth_connections** - Platform connection tokens
- **social_profiles** - Scraped recipient data
- **recommendation_sessions** - Each recommendation generation
- **gift_products** - Individual gift recommendations
- **bespoke_packages** - Experience + gift packages
- **purchases** - Stripe payment records

All tables have Row Level Security (RLS) enabled for data protection.

---

## 💡 Design Philosophy

**Why it doesn't look AI-generated:**
- Warm, human color palette (no purple/cyan/tech colors)
- Serif headings add personality and warmth
- Personal language throughout ("for them", "perfect because...")
- Real product reasoning shown, not hidden
- Generous whitespace and breathing room
- Thoughtful micro-interactions

**Core values reflected in design:**
- **Thoughtfulness** - Every detail considered
- **Warmth** - Inviting, not clinical
- **Clarity** - Easy to understand and use
- **Delight** - Small moments of joy

---

## 📄 License

MIT License - feel free to fork and adapt!

---

**Built with:** Next.js 16, Supabase, Claude AI, Stripe, and care  
**Version:** 1.0 (Next.js migration)  
**Ready for:** Valentine's Day 2026 launch 🎁
