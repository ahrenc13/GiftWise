# 🔄 How to Restart Your Flask App

## What is Flask?

**Flask** is the Python web framework your GiftWise app uses. It's the "engine" that runs your website.

---

## Two Ways to Run Your App

### **Option 1: Running Locally (on your computer)**

If you're testing on your own computer:

1. **Stop the app:**
   - In the terminal where Flask is running, press `Ctrl+C`

2. **Start it again:**
   ```bash
   python giftwise_app.py
   ```
   Or:
   ```bash
   flask run
   ```

3. **The app will reload** and pick up your new `.env` file

---

### **Option 2: Running on Railway (Cloud Hosting)**

If your app is deployed on Railway (which you mentioned earlier):

1. **Add Environment Variables to Railway:**
   - Go to your Railway project dashboard
   - Click on your service
   - Go to **"Variables"** tab
   - Add these three variables:
     ```
     GOOGLE_CUSTOM_SEARCH_API_KEY=AIzaSyBtRBn7N9706EVTvYU-60UO8qU-bugyYbw
     GOOGLE_CUSTOM_SEARCH_ENGINE_ID=656fcb5f1950c44db
     UNSPLASH_ACCESS_KEY=xaoAuGaebQjpX6kOg9p1wQjMH9FLTDEUlQL2lla7FMU
     ```
   - Railway will automatically redeploy when you add variables

2. **OR Commit and Push (if you want to deploy code changes):**
   ```bash
   git add .
   git commit -m "Add image API keys"
   git push origin main
   ```
   - Railway will automatically redeploy when you push

---

## Which One Are You Using?

**Check your situation:**
- **Local:** You run `python giftwise_app.py` in your terminal
- **Railway:** Your app is at a Railway URL (like `yourapp.railway.app`)

---

## Important: Railway Needs Environment Variables Too!

**If you're using Railway**, you MUST add the environment variables to Railway's dashboard:

1. Go to https://railway.app
2. Open your project
3. Click on your service
4. Go to **"Variables"** tab
5. Click **"+ New Variable"**
6. Add each variable:
   - `GOOGLE_CUSTOM_SEARCH_API_KEY` = `AIzaSyBtRBn7N9706EVTvYU-60UO8qU-bugyYbw`
   - `GOOGLE_CUSTOM_SEARCH_ENGINE_ID` = `656fcb5f1950c44db`
   - `UNSPLASH_ACCESS_KEY` = `xaoAuGaebQjpX6kOg9p1wQjMH9FLTDEUlQL2lla7FMU`

**Railway will automatically restart** when you add variables!

---

## Quick Answer

**If running locally:**
- Press `Ctrl+C` to stop
- Run `python giftwise_app.py` again

**If on Railway:**
- Add environment variables to Railway dashboard (they'll auto-restart)
- OR commit/push to GitHub (Railway auto-deploys)

---

**The `.env` file only works locally.** Railway needs the variables added to their dashboard!
