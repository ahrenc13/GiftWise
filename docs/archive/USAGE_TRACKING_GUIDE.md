# 📊 Usage Tracking Guide

## Overview

The usage tracking system monitors your API usage (Anthropic Claude API and Apify scraping) to help you stay within limits and avoid unexpected cutoffs.

## Accessing Usage Dashboard

**URL:** `/usage` or visit `http://localhost:5000/usage` (when running locally)

**API Endpoint:** `/api/usage` (returns JSON)

## What's Tracked

### **Anthropic Claude API**
- **Daily:** Requests and tokens used today
- **Monthly:** Requests and tokens used this month
- **Remaining:** How much capacity you have left

### **Apify Scraping**
- **Daily:** Compute units used today
- **Monthly:** Compute units used this month
- **By Platform:** Breakdown of Instagram vs TikTok scraping

## Default Limits

The system uses default limits based on typical free/paid tiers. **Update these in `usage_tracker.py`** based on your actual plan:

```python
API_LIMITS = {
    'anthropic': {
        'daily_requests': 1000,      # Update based on your plan
        'daily_tokens': 1000000,     # 1M tokens/day
        'monthly_requests': 30000,
        'monthly_tokens': 30000000,  # 30M tokens/month
    },
    'apify': {
        'daily_compute': 100,        # Free tier: ~100/day
        'monthly_compute': 3000,     # Free tier: ~3000/month
    }
}
```

## How to Update Limits

1. **Check your Anthropic plan:**
   - Go to https://console.anthropic.com
   - Check your plan details
   - Update `API_LIMITS['anthropic']` in `usage_tracker.py`

2. **Check your Apify plan:**
   - Go to https://console.apify.com
   - Check your compute unit limits
   - Update `API_LIMITS['apify']` in `usage_tracker.py`

## Usage Dashboard Features

### **Visual Indicators:**
- 🟢 **Green (Good):** < 50% usage
- 🟡 **Yellow (Warning):** 50-80% usage
- 🔴 **Red (Critical):** > 80% usage

### **Information Displayed:**
- Current usage (requests, tokens, compute units)
- Remaining capacity
- Percentage used
- Breakdown by request type (Anthropic)
- Breakdown by platform (Apify)

## Automatic Tracking

Usage is automatically tracked when:
- ✅ Recommendations are generated (Anthropic API)
- ✅ Instagram profiles are scraped (Apify)
- ✅ TikTok profiles are scraped (Apify)

## Manual Usage Check

**Via Browser:**
```
http://localhost:5000/usage
```

**Via API (JSON):**
```bash
curl http://localhost:5000/api/usage
```

**Via Python:**
```python
from usage_tracker import get_usage_summary

summary = get_usage_summary()
print(f"Remaining today: {summary['remaining']['anthropic']['daily']['requests']} requests")
```

## Troubleshooting

### **"Usage tracking not available"**
- Make sure `usage_tracker.py` exists
- Check that `data/` directory exists (it's created automatically)

### **Limits seem wrong**
- Update `API_LIMITS` in `usage_tracker.py` to match your actual plan
- Restart your Flask app

### **Usage not updating**
- Check that tracking is enabled (`USAGE_TRACKING_AVAILABLE = True`)
- Check Flask logs for tracking errors
- Verify `data/usage.db` file exists and is writable

## Example Output

```
🤖 Anthropic API - Today
Requests: 15 / 1000 (1.5%) 🟢
Tokens: 45,000 / 1,000,000 (4.5%) 🟢
Remaining: 985 requests, 955,000 tokens

🕷️ Apify Scraping - Today
Compute Units: 3 / 100 (3%) 🟢
Remaining: 97 compute units
```

## Next Steps

1. **Update limits** in `usage_tracker.py` to match your plan
2. **Visit `/usage`** to see current usage
3. **Monitor regularly** to avoid hitting limits
4. **Set up alerts** (future feature) when approaching limits

---

**Note:** Usage data is stored locally in `data/usage.db`. This is fine for MVP, but consider cloud storage for production.
