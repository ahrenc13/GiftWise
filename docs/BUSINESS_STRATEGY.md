# GiftWise — Business Strategy

## Revenue Model

**Primary:** Affiliate commissions on product clicks. Multi-retailer diversity is a revenue multiplier — CJ/Awin earn 2-5x vs Amazon per sale.

**Secondary:** Subscription tiers (not yet enforced). Infrastructure built but not wired to gatekeeping.

**Future:** Corporate/B2B gifting ($300B+ market).

## Session Economics

- Claude API cost per session: ~$0.10 (Sonnet)
- Affiliate revenue per session: ~$0.00-$0.05 (most visitors don't buy)
- Railway hosting: ~$5-20/month fixed

You are currently subsidizing every session. That's intentional — need traffic before monetizing.

## Paywall Trigger Thresholds

| Threshold | Action |
|-----------|--------|
| < 5 sessions/day | Keep fully free |
| 5-15/day | Add 1 run/day rate limiting per IP (already active) |
| 15-30/day sustained | Calculate cost vs affiliate revenue. If cost >> revenue for 2+ weeks, add account requirement |
| 30+/day, revenue not catching up | Soft paywall: require free account (just email) |
| Paying users exist | Hard paywall with Stripe |

**Before any paywall:** Inventory must be good. Don't paywall during traffic spikes (TikTok moment). Rate limit before paywalling. First paywall should be soft (email only, not payment).

## Subscription Tiers (Planned, Not Enforced)

- **Free:** Full access, 1 run/day rate limit
- **Pro ($4.99-$7.99/month):** Multiple profiles, monthly refresh, shareable links
- **Gift Emergency ($2.99 one-time):** 10 recs, no account needed

Stripe integration (`/subscribe` route) exists but isn't wired to gatekeeping.

## Revenue Priority

Affiliate > Subscription right now because:
1. No payment friction — users just click links
2. Every approved network multiplies revenue without code changes
3. Subscription needs volume to justify conversion funnel

Flip when: monthly affiliate revenue is steady but clearly lower than what 5% subscription conversion would generate at your traffic level.

## Commission Priority

Optimize for high-commission sources:
1. zChocolat (CJ) — 20%
2. FlowersFast (CJ) — 20%
3. SilverRushStyle (CJ) — 15%
4. VSGO (Awin) — 15%
5. LoveIsARose (Awin) — 10%, $250 AOV
6. Peet's (CJ) — 10%
7. GroundLuxe (CJ) — 10%, highest EPC
8. Amazon — 1-4% (lowest, deprioritize)

## Check Session Count

```
Admin dashboard: /admin/stats?key=YOUR_KEY
→ "rec_run" events = full pipeline sessions

Railway dashboard → Metrics → Requests / 7 = avg sessions/day
```
