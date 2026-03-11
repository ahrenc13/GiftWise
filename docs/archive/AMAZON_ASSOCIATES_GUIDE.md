# 🛒 AMAZON ASSOCIATES SETUP GUIDE - Complete Integration

## Overview
Set up Amazon Associates to earn 1-10% commission on gift recommendations.

---

## Part 1: Account Signup (15 minutes)

### Step 1: Create Amazon Associates Account
1. Go to https://affiliate-program.amazon.com
2. Click "Sign up" or "Join now for free"
3. Log in with existing Amazon account (or create one)

### Step 2: Account Information
Fill in your details:

**Account Information:**
- Name: Your legal name
- Address: Your address
- Phone: Your phone number

**Website/App Information:**
- **Website URL:** Enter your domain (e.g., `giftwise.com`)
  - Don't have a domain yet? Use a free landing page URL or `coming-soon.giftwise.com`
- **App name** (if applicable): Giftwise
- **Description:** AI-powered gift recommendation service that analyzes social media
- **Topics:** Gifts, Shopping, Technology, Lifestyle

**Profile Information:**
- **How do you drive traffic?**
  - Select: Search Engine Optimization (SEO), Social Media, Email Marketing
- **How do you build links?**
  - Select: I use links in my content
- **How do you monetize?**
  - Select: Affiliate Marketing
- **Website/app type:**
  - Select: Comparison Shopping, Deals/Coupons, Product Reviews
- **Primary reason for joining:**
  - Select: Monetization

### Step 3: Verify Identity
- Enter payment/tax information
- Verify phone number
- Accept Operating Agreement

### Step 4: Get Your Associate ID
After approval (usually instant), you'll get:
- **Associate ID (Store ID):** e.g., `giftwise-20`
- This appears in: Settings → Account Settings

**IMPORTANT:** Your Associate ID is what tracks your commissions!

---

## Part 2: Understanding Amazon Links

### Link Format
```
https://www.amazon.com/dp/PRODUCT_ASIN/?tag=YOUR_ASSOCIATE_ID
```

**Components:**
- `dp/` = detail page
- `PRODUCT_ASIN` = unique product ID (B07QR73T66)
- `tag=` = your Associate ID

**Example:**
```
Product: Focusrite Scarlett Solo (3rd Gen)
ASIN: B07QR73T66
Your ID: giftwise-20

Link: https://www.amazon.com/dp/B07QR73T66/?tag=giftwise-20
```

---

## Part 3: Finding Product ASINs

### Method 1: Manual Search (Quick start)

**Steps:**
1. Search for product on Amazon.com
2. Open product page
3. Scroll down to "Product Information"
4. Copy ASIN (or find in URL)

**Example:**
```
URL: https://www.amazon.com/Focusrite-Scarlett-Audio-Interface-Tools/dp/B07QR73T66/
                                                                       ^^^^^^^^^^
                                                                       This is the ASIN
```

### Method 2: Amazon Product API (Automated)

**Setup:**
1. Sign up for Product Advertising API
2. Get Access Key and Secret Key
3. Install SDK: `pip install python-amazon-paapi`

**Code:**
```python
from amazon.paapi import AmazonAPI

# Initialize API
amazon = AmazonAPI(
    key='YOUR_ACCESS_KEY',
    secret='YOUR_SECRET_KEY',
    tag='giftwise-20',  # Your Associate ID
    country='US'
)

def find_product(product_name):
    """Search Amazon and return affiliate link"""
    try:
        # Search for product
        results = amazon.search_items(keywords=product_name)
        
        if results and results.items:
            product = results.items[0]
            
            return {
                'title': product.item_info.title.display_value,
                'asin': product.asin,
                'price': product.offers.listings[0].price.amount if product.offers else None,
                'affiliate_link': product.detail_page_url,  # Already has your tag
                'image': product.images.primary.large.url
            }
    except Exception as e:
        print(f"Error: {e}")
        return None

# Usage
product = find_product("Focusrite Scarlett Solo")
print(product['affiliate_link'])
# Output: https://www.amazon.com/dp/B07QR73T66/?tag=giftwise-20
```

---

## Part 4: Integration into Giftwise

### Option A: Manual Links (MVP - Start Here)

**For each recommendation, manually:**

1. Search product name on Amazon
2. Get ASIN from URL or product page
3. Create affiliate link: `https://www.amazon.com/dp/ASIN/?tag=giftwise-20`
4. Add to recommendation output

**Example Recommendation with Link:**
```python
recommendations = [
    {
        "name": "Focusrite Scarlett Solo USB Audio Interface (3rd Gen)",
        "price": "$130",
        "match": 92,
        "confidence": "safe",
        "reason": "Heavy School of Rock involvement...",
        "amazon_link": "https://www.amazon.com/dp/B07QR73T66/?tag=giftwise-20"
    }
]
```

**Update HTML to show link:**
```html
<div class="recommendation-card">
    <h3>{{ rec.name }}</h3>
    <p>{{ rec.price }} | {{ rec.match }}% match</p>
    <p>{{ rec.reason }}</p>
    <a href="{{ rec.amazon_link }}" target="_blank" class="buy-button">
        View on Amazon →
    </a>
</div>
```

---

### Option B: Automated with Product API (Month 2)

**Full automation:**

```python
import anthropic
from amazon.paapi import AmazonAPI

# Initialize both APIs
claude = anthropic.Anthropic(api_key="YOUR_CLAUDE_KEY")
amazon = AmazonAPI(
    key='YOUR_AMAZON_KEY',
    secret='YOUR_AMAZON_SECRET',
    tag='giftwise-20',
    country='US'
)

def generate_recommendations_with_links(user_data):
    """Generate recommendations AND find Amazon links"""
    
    # 1. Generate recommendations with Claude (as before)
    recommendations = generate_gift_recommendations(user_data)
    
    # 2. For each recommendation, find Amazon link
    for rec in recommendations:
        product_name = rec['name']
        
        # Search Amazon
        amazon_result = amazon.search_items(keywords=product_name)
        
        if amazon_result and amazon_result.items:
            product = amazon_result.items[0]
            
            # Add Amazon data to recommendation
            rec['amazon_link'] = product.detail_page_url
            rec['amazon_price'] = product.offers.listings[0].price.display_amount if product.offers else rec['price']
            rec['amazon_image'] = product.images.primary.large.url
            rec['amazon_rating'] = product.browse_node_info.website_sales_rank if hasattr(product, 'browse_node_info') else None
        else:
            # Fallback: manual search link
            search_query = product_name.replace(' ', '+')
            rec['amazon_link'] = f"https://www.amazon.com/s?k={search_query}&tag=giftwise-20"
    
    return recommendations

# Usage
recs = generate_recommendations_with_links(user_data)

for rec in recs:
    print(f"{rec['name']}")
    print(f"Link: {rec['amazon_link']}")
    print(f"Price: {rec['amazon_price']}")
    print()
```

---

## Part 5: Commission Rates by Category

**Amazon commission structure:**

| Category | Commission |
|----------|-----------|
| Luxury Beauty, Amazon Coins | 10% |
| Digital Music, Physical Books, Kitchen | 4.5% |
| Toys, Furniture, Home, Lawn & Garden, Pets Products, Headphones, Beauty, Musical Instruments, Business & Industrial Supplies | 4% |
| Physical Video Games, Video Game Consoles | 1% |
| Digital Video Games | 0% |
| Everything Else | 3% |

**Your products:**
- Music equipment (Focusrite): **4%**
- Books (Depeche Mode book): **4.5%**
- Sports memorabilia: **3%**
- Pet products (Pomeranian costume): **4%**

**Average across Giftwise:** ~**4% commission**

---

## Part 6: Tracking Performance

### View Your Earnings

**In Amazon Associates Dashboard:**
1. Go to "Reports" → "Earnings Report"
2. See:
   - Clicks: How many people clicked your links
   - Conversion rate: % who bought
   - Items ordered: What they bought
   - Earnings: Your commission

**Key metrics:**
- **Click-through rate (CTR):** 20-30% is good
- **Conversion rate:** 3-8% is typical for Amazon
- **Average order value:** $80-120 for gifts

### Example Performance

**Month 1 with 100 users:**
- 100 users
- 10 recommendations each = 1,000 links shown
- 20% CTR = 200 clicks
- 5% conversion = 10 purchases
- Average order: $100
- Commission (4%): $4 per purchase
- **Total earnings: $40**

**Month 6 with 1,000 users:**
- 1,000 users
- 10,000 links shown
- 20% CTR = 2,000 clicks
- 5% conversion = 100 purchases
- Average order: $100
- **Total earnings: $400/month = $4,800/year**

---

## Part 7: Best Practices

### DO:
✅ **Use specific product names** (helps matching)
✅ **Link directly to products** (not search pages)
✅ **Update links if products unavailable** 
✅ **Disclose affiliate relationship** (legally required)
✅ **Track which recs get most clicks** (optimize)

### DON'T:
❌ **Don't click your own links** (Amazon bans for this)
❌ **Don't share links in spam** (get banned)
❌ **Don't create fake urgency** ("limited time!")
❌ **Don't mask affiliate ID** (breaks TOS)

---

## Part 8: Legal Requirements

### FTC Disclosure

**Required statement:**
"As an Amazon Associate, I earn from qualifying purchases."

**Where to add:**
- Footer of website ✅
- Near "Buy" buttons ✅
- In email recommendations ✅

**Example placement:**
```html
<div class="footer">
    <p>As an Amazon Associate, we earn from qualifying purchases.</p>
</div>
```

---

## Part 9: Quick Start Checklist

**This Week:**
- [ ] Sign up for Amazon Associates
- [ ] Get your Associate ID (e.g., `giftwise-20`)
- [ ] Manually create 10 test affiliate links
- [ ] Add links to recommendation output
- [ ] Add FTC disclosure to landing page
- [ ] Test: Click link, verify tracking in dashboard

**Month 2:**
- [ ] Sign up for Product Advertising API
- [ ] Automate link generation
- [ ] Track click-through rates
- [ ] Optimize top-performing categories

---

## Part 10: Revenue Calculator

**Your numbers:**
```
Users per month: 100
Recommendations per user: 10
Total links shown: 1,000

Click-through rate: 20%
Clicks: 200

Conversion rate: 5%
Purchases: 10

Average order value: $100
Average commission rate: 4%
Commission per purchase: $4

Monthly affiliate revenue: $40
Annual affiliate revenue: $480

With 1,000 users: $4,800/year
With 10,000 users: $48,000/year 💰
```

---

## Part 11: Complete Integration Example

**Recommendation with affiliate link:**

```python
def format_recommendation_for_display(rec):
    """Format recommendation with Amazon affiliate link"""
    
    # Your Associate ID
    ASSOCIATE_ID = "giftwise-20"
    
    # Get or create Amazon link
    if 'asin' in rec:
        amazon_link = f"https://www.amazon.com/dp/{rec['asin']}/?tag={ASSOCIATE_ID}"
    else:
        # Fallback: search link
        search_term = rec['name'].replace(' ', '+')
        amazon_link = f"https://www.amazon.com/s?k={search_term}&tag={ASSOCIATE_ID}"
    
    return f"""
    <div class="recommendation">
        <h3>{rec['name']}</h3>
        <p class="price">{rec['price']} | {rec['match']}% match</p>
        <p class="confidence">{rec['confidence']}</p>
        <p class="reason">{rec['reason']}</p>
        <a href="{amazon_link}" target="_blank" class="buy-button">
            View on Amazon →
        </a>
    </div>
    """
```

---

## Part 12: Advanced: Product API Setup

### Step 1: Register for API Access

1. Go to https://affiliate-program.amazon.com/assoc_credentials/home
2. Click "Product Advertising API"
3. Fill out application
4. Get approved (usually 1-2 days)
5. Get credentials:
   - Access Key
   - Secret Key

### Step 2: Install SDK

```bash
pip install python-amazon-paapi
```

### Step 3: Test API

```python
from amazon.paapi import AmazonAPI

amazon = AmazonAPI(
    key='YOUR_ACCESS_KEY',
    secret='YOUR_SECRET_KEY',
    tag='giftwise-20',
    country='US'
)

# Test search
results = amazon.search_items(keywords="Focusrite Scarlett Solo")

if results:
    product = results.items[0]
    print(f"Title: {product.item_info.title.display_value}")
    print(f"ASIN: {product.asin}")
    print(f"Link: {product.detail_page_url}")
    print(f"Price: {product.offers.listings[0].price.display_amount}")
```

---

## Summary: Start Simple, Scale Smart

### Week 1 (Manual):
```
✓ Sign up for Associates
✓ Get Associate ID
✓ Manually add 10 links to test
✓ Add disclosure
✓ Launch!
```

### Month 2 (Automated):
```
✓ Product API access
✓ Auto-generate links
✓ Track performance
✓ Optimize
```

### Month 6 (Optimized):
```
✓ A/B test link placement
✓ Track category performance
✓ Negotiate direct partnerships
✓ Scale revenue
```

**The key:** Start with manual links this week. You can always automate later!

---

## Quick Reference

```
Amazon Associates Account
✅ Account created: _______
✅ Associate ID: giftwise-20 (example)
✅ Link format: https://www.amazon.com/dp/ASIN/?tag=giftwise-20
✅ Disclosure added to site: [ ]
✅ First test link created: [ ]
```

**Ready to launch!** 🚀
