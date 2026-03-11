# 🚀 OAuth Quick Start

## ✅ What's Ready

All OAuth integrations are **fully implemented** and ready to use:

- ✅ **Pinterest OAuth** - Complete
- ✅ **Spotify OAuth** - Complete  
- ✅ **Etsy OAuth** - Complete
- ✅ **Google/YouTube OAuth** - Complete

## 🔧 Quick Setup (5 minutes per platform)

### **1. Pinterest** (Already linked in UI)
- Go to https://developers.pinterest.com/apps/
- Create app → Get Client ID & Secret
- Add to `.env`:
  ```
  PINTEREST_CLIENT_ID=your_id
  PINTEREST_CLIENT_SECRET=your_secret
  ```

### **2. Spotify** (Now in UI)
- Go to https://developer.spotify.com/dashboard
- Create app → Get Client ID & Secret
- Add to `.env`:
  ```
  SPOTIFY_CLIENT_ID=your_id
  SPOTIFY_CLIENT_SECRET=your_secret
  ```

### **3. Etsy** (Now in UI)
- Go to https://www.etsy.com/developers/register
- Register → Create app → Get Keystring & Shared Secret
- Add to `.env`:
  ```
  ETSY_CLIENT_ID=your_keystring
  ETSY_CLIENT_SECRET=your_shared_secret
  ```

### **4. Google/YouTube** (OAuth or API Key)
- **OAuth:** https://console.cloud.google.com → Enable YouTube Data API → Create OAuth credentials
- **API Key:** https://console.cloud.google.com → Create API key
- Add to `.env`:
  ```
  GOOGLE_CLIENT_ID=your_id (for OAuth)
  GOOGLE_CLIENT_SECRET=your_secret (for OAuth)
  GOOGLE_YOUTUBE_API_KEY=your_key (for API key method)
  ```

## 🎯 How It Works

1. User clicks "Connect [Platform]"
2. Redirects to platform login
3. User authorizes
4. Redirects back with code
5. Code exchanged for token
6. Data fetched automatically
7. Saved to user account

## 📍 Routes

- `/oauth/pinterest` - Start Pinterest OAuth
- `/oauth/spotify` - Start Spotify OAuth
- `/connect/etsy` - Start Etsy OAuth
- `/oauth/google` - Start Google OAuth

All callbacks handle automatically!

---

**Everything is ready - just add your API credentials!**
