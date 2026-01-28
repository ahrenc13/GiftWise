# 🚨 Railway Crash Debugging Guide

## How to Get Logs

### **Option 1: Railway Dashboard**
1. Go to https://railway.app
2. Select your GiftWise project
3. Click on your service
4. Go to **"Deployments"** tab
5. Click on the latest deployment
6. Click **"View Logs"** or **"View Build Logs"**
7. Copy the error messages

### **Option 2: Railway CLI**
```bash
railway logs
```

### **Option 3: Railway API**
- Check Railway dashboard → Service → Logs

## Common Crash Causes

### **1. Missing Environment Variables**
**Error:** `ValueError: SECRET_KEY environment variable is required`
**Fix:** Set all required env vars in Railway dashboard

**Required Variables:**
- `SECRET_KEY`
- `ANTHROPIC_API_KEY`
- `APIFY_API_TOKEN`
- `STRIPE_SECRET_KEY` (if using payments)
- `PINTEREST_CLIENT_ID` (if using Pinterest)

### **2. Import Errors**
**Error:** `ModuleNotFoundError` or `ImportError`
**Fix:** Check `requirements.txt` includes all dependencies

### **3. Database/File System Issues**
**Error:** `PermissionError` or `FileNotFoundError`
**Fix:** Railway uses ephemeral filesystem - use Railway Postgres or external DB

### **4. Port Binding**
**Error:** `Address already in use` or port issues
**Fix:** Railway sets `PORT` env var automatically - use it:
```python
port = int(os.environ.get('PORT', 5000))
```

### **5. Memory Limits**
**Error:** `MemoryError` or process killed
**Fix:** Check Railway plan limits, optimize memory usage

### **6. Missing Data Directory**
**Error:** `FileNotFoundError: data/usage.db` or similar
**Fix:** Create directory in code or use Railway volumes

## Quick Fixes

### **Add Better Error Handling**
The app should catch errors and log them properly. Check:
- Flask error handlers
- Try/except blocks around critical code
- Logging configuration

### **Check Railway Logs Format**
Railway logs show:
- Build logs (during deployment)
- Runtime logs (when app is running)
- Error logs (crashes)

Look for:
- `Traceback` (Python errors)
- `Error:` or `Exception:`
- `ModuleNotFoundError`
- `ValueError`
- `ImportError`

## What to Paste Here

When asking for help, paste:
1. **The error message** (last 20-30 lines of logs)
2. **When it crashed** (during deployment? after a request?)
3. **What you were doing** (visiting a page? generating recommendations?)

## Example Log Format

```
[timestamp] ERROR: Exception on /generate-recommendations [POST]
Traceback (most recent call last):
  File "/app/giftwise_app.py", line 1234, in api_generate_recommendations
    ...
ValueError: SECRET_KEY environment variable is required
```

## Next Steps

1. **Get the logs** from Railway
2. **Paste them here** (last 30-50 lines)
3. **I'll help debug** the specific issue

---

**Note:** I cannot automatically monitor Railway - you need to paste logs here for me to help debug.
