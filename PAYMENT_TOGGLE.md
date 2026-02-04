# Payment System Toggle - Simple On/Off Switch

Your payment system has a **feature flag** that lets you instantly enable or disable it.

---

## For Early Testing (Payments OFF)

**Default state:** Payments are disabled

When payments are OFF:
- Users get unlimited recommendations
- No paywall or subscription checks
- Pricing page still visible but not enforced
- Perfect for beta testing without friction

**No action needed** - this is the default!

---

## For Launch Day (Payments ON)

When you're ready to enforce the freemium model:

### Option 1: Via v0 Sidebar (Easiest)

1. Go to the "Vars" section in v0 sidebar
2. Add a new environment variable:
   - Key: `NEXT_PUBLIC_PAYMENTS_ENABLED`
   - Value: `true`
3. Save and redeploy

That's it! Payments are now enforced.

### Option 2: Via Vercel Dashboard

1. Go to your Vercel project
2. Click "Settings" → "Environment Variables"
3. Add new variable:
   - Name: `NEXT_PUBLIC_PAYMENTS_ENABLED`
   - Value: `true`
4. Redeploy your app

---

## What Changes When Payments Are ON

**Free Tier:**
- 1 recommendation per month
- After 1, they hit paywall with upgrade prompt

**Basic Tier ($9/mo):**
- 5 recommendations per month

**Pro Tier ($19/mo):**
- Unlimited recommendations

**The enforcement happens automatically** - no code changes needed!

---

## Testing the Toggle

**Test with payments OFF:**
```bash
# No env var set (or set to "false")
# Generate 10+ recommendations to verify no limits
```

**Test with payments ON:**
```bash
# Add NEXT_PUBLIC_PAYMENTS_ENABLED=true
# Generate 2 recommendations as free user
# Second one should trigger upgrade prompt
```

---

## Recommended Timeline

**Week 1-2 (Beta):** Payments OFF
- Let testers generate freely
- Collect feedback on recommendations
- Fix bugs without payment friction

**Week 3 (Pre-launch):** Payments ON
- Test the upgrade flow
- Verify Stripe checkout works
- Confirm limits are enforced correctly

**Valentine's Day:** Launch with Payments ON
- Freemium enforced from day 1
- Referral credits active
- Conversion tracking enabled

---

## Emergency "Turn Off Payments" Button

If something goes wrong with Stripe during launch:

1. Go to Vercel dashboard
2. Find `NEXT_PUBLIC_PAYMENTS_ENABLED`
3. Change value to `false`
4. Redeploy (takes 30 seconds)
5. All users get free access while you fix the issue

This gives you a safety valve if payments break!

---

## Current Status

Right now: **Payments are OFF** (testing mode)

To check current status, look for the green banner on the dashboard that says "Testing Mode Active"
