# 💳 STRIPE SETUP GUIDE - Complete Implementation

## Overview
Set up Stripe to accept $4.99/month subscriptions for Giftwise.

---

## Part 1: Stripe Account Setup (10 minutes)

### Step 1: Create Stripe Account
1. Go to https://stripe.com
2. Click "Start now" or "Sign in"
3. Create account with email/password
4. Verify your email

### Step 2: Activate Your Account
1. Complete business details (can use personal info for now)
2. Add bank account for payouts
3. Verify identity (ID, SSN, etc.)
4. **Note:** You can test in "Test Mode" before activating

### Step 3: Get Your API Keys
1. In Stripe Dashboard, click "Developers" → "API keys"
2. You'll see two keys:
   - **Publishable key** (starts with `pk_test_` or `pk_live_`)
   - **Secret key** (starts with `sk_test_` or `sk_live_`)
3. **IMPORTANT:** Keep secret key SECRET - never share or commit to GitHub

---

## Part 2: Create Subscription Product (5 minutes)

### Step 1: Create Product
1. In Stripe Dashboard, go to "Products" → "Add product"
2. Fill in:
   - **Name:** Giftwise Pro
   - **Description:** AI-powered gift recommendations from social media
   - **Pricing model:** Recurring
   - **Price:** $4.99
   - **Billing period:** Monthly
3. Click "Save product"

### Step 2: Get Price ID
1. After saving, you'll see a **Price ID** (starts with `price_`)
2. Copy this - you'll need it for integration
3. Example: `price_1234567890abcdefg`

---

## Part 3: Integration Code

### Option A: Simple Payment Link (EASIEST - 5 minutes)

**Best for:** Quick launch, no coding needed

**Steps:**
1. In Stripe Dashboard, go to "Payment links" → "New"
2. Select your Giftwise Pro product
3. Customize success/cancel URLs
4. Click "Create link"
5. Copy the link (looks like: `https://buy.stripe.com/test_xxxxx`)
6. **Update your landing page button:**

```html
<!-- Replace the CTA button href with your Stripe payment link -->
<a href="https://buy.stripe.com/YOUR_LINK_HERE" class="cta-button">
    Start Free Trial
</a>
```

**Pros:**
- ✅ No code required
- ✅ Works immediately
- ✅ Stripe handles everything

**Cons:**
- ⚠️ Less customization
- ⚠️ Redirects to Stripe-hosted page

---

### Option B: Stripe Checkout (Better - 30 minutes)

**Best for:** Custom flow, better UX

**Backend Code (Python/Flask):**

```python
# Install: pip install stripe flask

import stripe
from flask import Flask, request, jsonify, redirect

app = Flask(__name__)

# Your Stripe secret key
stripe.api_key = "sk_test_YOUR_SECRET_KEY_HERE"

# Your Stripe Price ID (from Part 2)
PRICE_ID = "price_YOUR_PRICE_ID_HERE"

@app.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    """Create a Stripe Checkout session for subscription"""
    try:
        # Get customer email from form
        customer_email = request.form.get('email')
        
        # Create Stripe Checkout session
        checkout_session = stripe.checkout.Session.create(
            customer_email=customer_email,
            payment_method_types=['card'],
            line_items=[{
                'price': PRICE_ID,
                'quantity': 1,
            }],
            mode='subscription',
            success_url='https://yourdomain.com/success?session_id={CHECKOUT_SESSION_ID}',
            cancel_url='https://yourdomain.com/cancel',
            # Optional: 7-day free trial
            subscription_data={
                'trial_period_days': 7,
            },
        )
        
        # Redirect to Stripe Checkout
        return redirect(checkout_session.url, code=303)
    
    except Exception as e:
        return jsonify(error=str(e)), 403

if __name__ == '__main__':
    app.run(port=4242)
```

**Frontend Code (HTML form):**

```html
<!-- Add to your landing page -->
<form action="/create-checkout-session" method="POST">
    <input type="email" name="email" placeholder="Your email" required>
    <button type="submit" class="cta-button">Start Free Trial</button>
</form>
```

---

### Option C: Full Custom Integration (Advanced - 2+ hours)

**Best for:** Complete control, embedded payment

Use Stripe Elements for fully custom checkout flow.
See: https://stripe.com/docs/payments/checkout/custom-success-page

---

## Part 4: Webhook Setup (CRITICAL for subscriptions)

Webhooks tell your server when subscription events happen (signup, cancellation, payment failure, etc.)

### Step 1: Create Webhook Endpoint

```python
# Add to your Flask app
import os

# Webhook secret (from Stripe Dashboard)
WEBHOOK_SECRET = "whsec_YOUR_WEBHOOK_SECRET"

@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle Stripe webhook events"""
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')
    
    try:
        # Verify webhook signature
        event = stripe.Webhook.construct_event(
            payload, sig_header, WEBHOOK_SECRET
        )
    except ValueError as e:
        # Invalid payload
        return 'Invalid payload', 400
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        return 'Invalid signature', 400
    
    # Handle the event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        
        # Customer subscribed successfully
        customer_id = session['customer']
        customer_email = session['customer_email']
        
        # TODO: Save to your database
        print(f"New subscription: {customer_email}")
        
    elif event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']
        
        # Customer cancelled
        customer_id = subscription['customer']
        
        # TODO: Update your database
        print(f"Subscription cancelled: {customer_id}")
        
    elif event['type'] == 'invoice.payment_failed':
        invoice = event['data']['object']
        
        # Payment failed
        customer_id = invoice['customer']
        
        # TODO: Send email notification
        print(f"Payment failed: {customer_id}")
    
    return jsonify(success=True)
```

### Step 2: Register Webhook in Stripe

1. In Stripe Dashboard, go to "Developers" → "Webhooks"
2. Click "Add endpoint"
3. Enter your URL: `https://yourdomain.com/webhook`
4. Select events to listen for:
   - `checkout.session.completed`
   - `customer.subscription.deleted`
   - `invoice.payment_failed`
   - `invoice.payment_succeeded`
5. Copy the **Signing secret** (starts with `whsec_`)
6. Update your code with this secret

---

## Part 5: Testing (Before Going Live)

### Test Mode
Stripe provides test credit cards:

**Successful payment:**
- Card: 4242 4242 4242 4242
- Expiry: Any future date
- CVC: Any 3 digits
- ZIP: Any 5 digits

**Declined payment:**
- Card: 4000 0000 0000 0002

### Test Your Flow
1. Use test API keys (`pk_test_` and `sk_test_`)
2. Go through full payment flow
3. Check webhook events arrive
4. Verify data saved correctly

---

## Part 6: Go Live Checklist

Before switching to live mode:

- [ ] Account activated (identity verified, bank added)
- [ ] Live API keys obtained
- [ ] Product created in live mode
- [ ] Webhook endpoint registered with live mode
- [ ] Test with real card (charge $0.50 and refund)
- [ ] SSL certificate on your domain (required for production)
- [ ] Update all code to use live keys
- [ ] Terms of Service and Privacy Policy on site

---

## Complete Example: Minimal Viable Setup

**File: app.py**
```python
import stripe
from flask import Flask, request, redirect, render_template

app = Flask(__name__)

# REPLACE THESE
stripe.api_key = "sk_test_YOUR_KEY"
PRICE_ID = "price_YOUR_PRICE"

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/checkout', methods=['POST'])
def checkout():
    email = request.form.get('email')
    
    session = stripe.checkout.Session.create(
        customer_email=email,
        payment_method_types=['card'],
        line_items=[{'price': PRICE_ID, 'quantity': 1}],
        mode='subscription',
        success_url='https://yourdomain.com/success',
        cancel_url='https://yourdomain.com/',
        subscription_data={'trial_period_days': 7},
    )
    
    return redirect(session.url, code=303)

@app.route('/success')
def success():
    return "Welcome to Giftwise! Check your email for login details."

if __name__ == '__main__':
    app.run(debug=True, port=5000)
```

**File: templates/index.html**
```html
<!DOCTYPE html>
<html>
<head>
    <title>Giftwise</title>
</head>
<body>
    <h1>Start Your Free Trial</h1>
    <form action="/checkout" method="POST">
        <input type="email" name="email" placeholder="your@email.com" required>
        <button type="submit">Start 7-Day Free Trial</button>
    </form>
</body>
</html>
```

**Run:**
```bash
pip install stripe flask
python app.py
```

Visit: http://localhost:5000

---

## Cost Breakdown

**Stripe fees:**
- 2.9% + $0.30 per transaction
- For $4.99 subscription: **$0.44 fee**
- You keep: **$4.55**

**Your economics:**
- Revenue: $4.55
- Scraping cost: $1.00
- Affiliate revenue: $4.00 (average)
- **Net profit: $7.55 per user** 💰

---

## Next Steps

1. **This week:** Use Payment Link (Option A) for fastest launch
2. **Month 2:** Upgrade to Checkout integration (Option B) for better UX
3. **Month 3+:** Add webhook handling for automation

---

## Support Resources

- Stripe Docs: https://stripe.com/docs
- Checkout Guide: https://stripe.com/docs/payments/checkout
- Webhook Guide: https://stripe.com/docs/webhooks
- Test Cards: https://stripe.com/docs/testing

---

## Quick Reference

```
✅ Stripe Account Created
✅ Product Created ($4.99/month)
✅ Price ID: price_________________
✅ Publishable Key: pk_test_________________
✅ Secret Key: sk_test_________________ (KEEP SECRET!)
✅ Payment Link: https://buy.stripe.com/_________________
```

**Recommended first step:** Use Payment Link for immediate launch, then iterate!
