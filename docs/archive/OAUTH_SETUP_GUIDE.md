# 🔐 OAuth Setup Guide

## Overview

Complete OAuth implementations for Pinterest, Spotify, Etsy, and Google (YouTube).

## ✅ What's Implemented

### **1. Pinterest OAuth** ✅
- Full OAuth 2.0 flow
- Fetches boards and pins
- Stores access/refresh tokens

### **2. Spotify OAuth** ✅
- Full OAuth 2.0 flow
- Fetches top artists, tracks, playlists
- Stores access/refresh tokens

### **3. Etsy OAuth** ✅
- Full OAuth 2.0 flow
- Fetches favorites/wishlist
- Stores access/refresh tokens

### **4. Google OAuth (YouTube)** ✅
- Full OAuth 2.0 flow
- Fetches channel subscriptions
- Alternative: API key method (no OAuth)

---

## 🔧 Setup Instructions

### **Pinterest OAuth**

**Steps:**
1. Go to https://developers.pinterest.com/apps/
2. Create new app
3. Get Client ID and Client Secret
4. Set Redirect URI: `http://localhost:5000/oauth/pinterest/callback` (dev) or your production URL
5. Add to `.env`:
   ```
   PINTEREST_CLIENT_ID=your_client_id
   PINTEREST_CLIENT_SECRET=your_client_secret
   PINTEREST_REDIRECT_URI=http://localhost:5000/oauth/pinterest/callback
   ```

**Scopes Required:**
- `boards:read`
- `pins:read`

---

### **Spotify OAuth**

**Steps:**
1. Go to https://developer.spotify.com/dashboard
2. Create new app
3. Get Client ID and Client Secret
4. Set Redirect URI: `http://localhost:5000/oauth/spotify/callback`
5. Add to `.env`:
   ```
   SPOTIFY_CLIENT_ID=your_client_id
   SPOTIFY_CLIENT_SECRET=your_client_secret
   SPOTIFY_REDIRECT_URI=http://localhost:5000/oauth/spotify/callback
   ```

**Scopes Required:**
- `user-top-read`
- `user-read-recently-played`
- `playlist-read-private`
- `user-library-read`

---

### **Etsy OAuth**

**Steps:**
1. Go to https://www.etsy.com/developers/register
2. Register as developer
3. Create new app
4. Get Keystring (Client ID) and Shared Secret (Client Secret)
5. Set Redirect URI: `http://localhost:5000/oauth/etsy/callback`
6. Add to `.env`:
   ```
   ETSY_CLIENT_ID=your_keystring
   ETSY_CLIENT_SECRET=your_shared_secret
   ETSY_REDIRECT_URI=http://localhost:5000/oauth/etsy/callback
   ```

**Scopes Required:**
- `favorites_r`
- `profile_r`

**Note:** Etsy may require PKCE - check their latest docs

---

### **Google OAuth (YouTube)**

**Steps:**
1. Go to https://console.cloud.google.com
2. Create new project
3. Enable "YouTube Data API v3"
4. Create OAuth 2.0 credentials:
   - APIs & Services → Credentials
   - Create Credentials → OAuth client ID
   - Application type: Web application
   - Authorized redirect URIs: `http://localhost:5000/oauth/google/callback`
5. Get Client ID and Client Secret
6. Add to `.env`:
   ```
   GOOGLE_CLIENT_ID=your_client_id
   GOOGLE_CLIENT_SECRET=your_client_secret
   GOOGLE_REDIRECT_URI=http://localhost:5000/oauth/google/callback
   ```

**Alternative: API Key Method**
- Get YouTube Data API key (simpler, no OAuth)
- Add to `.env`:
   ```
   GOOGLE_YOUTUBE_API_KEY=your_api_key
   ```
- Use channel ID input method (already implemented)

**Scopes Required:**
- `https://www.googleapis.com/auth/youtube.readonly`

---

## 🚀 Routes Added

### **OAuth Initiation:**
- `/oauth/pinterest` - Start Pinterest OAuth
- `/oauth/spotify` - Start Spotify OAuth
- `/oauth/etsy` - Start Etsy OAuth (via `/connect/etsy`)
- `/oauth/google` - Start Google OAuth

### **OAuth Callbacks:**
- `/oauth/pinterest/callback` - Handle Pinterest callback
- `/oauth/spotify/callback` - Handle Spotify callback
- `/oauth/etsy/callback` - Handle Etsy callback
- `/oauth/google/callback` - Handle Google callback

---

## 📋 Environment Variables Summary

Add all OAuth credentials to `.env`:

```bash
# Pinterest
PINTEREST_CLIENT_ID=...
PINTEREST_CLIENT_SECRET=...
PINTEREST_REDIRECT_URI=http://localhost:5000/oauth/pinterest/callback

# Spotify
SPOTIFY_CLIENT_ID=...
SPOTIFY_CLIENT_SECRET=...
SPOTIFY_REDIRECT_URI=http://localhost:5000/oauth/spotify/callback

# Etsy
ETSY_CLIENT_ID=...
ETSY_CLIENT_SECRET=...
ETSY_REDIRECT_URI=http://localhost:5000/oauth/etsy/callback

# Google/YouTube
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_REDIRECT_URI=http://localhost:5000/oauth/google/callback
GOOGLE_YOUTUBE_API_KEY=...  # Optional: API key method
```

---

## 🔒 Security Features

- **CSRF Protection:** State parameter verification
- **Token Storage:** Secure storage in user database
- **Refresh Tokens:** Stored for automatic token renewal
- **Error Handling:** Comprehensive error messages

---

## 🧪 Testing

1. **Test OAuth Flow:**
   - Click "Connect" button
   - Should redirect to platform login
   - Authorize app
   - Should redirect back and connect

2. **Test Disconnect:**
   - Click "Disconnect" button
   - Platform should be removed
   - Can reconnect anytime

3. **Test Data Fetching:**
   - After OAuth, data should be fetched automatically
   - Check user's platform data

---

## 🐛 Troubleshooting

### **"OAuth not configured"**
- Check environment variables are set
- Verify redirect URIs match exactly
- Check client ID/secret are correct

### **"Invalid state"**
- CSRF protection - normal if session expired
- Try connecting again

### **"Token exchange failed"**
- Check client secret is correct
- Verify redirect URI matches exactly
- Check platform API status

### **"Data fetch failed"**
- Token might be expired
- Check API permissions/scopes
- Verify API is enabled

---

## 📊 OAuth Status

| Platform | OAuth | API Key Alternative | Status |
|----------|-------|---------------------|--------|
| Pinterest | ✅ | ❌ | Complete |
| Spotify | ✅ | ❌ | Complete |
| Etsy | ✅ | ❌ | Complete |
| YouTube | ✅ | ✅ | Complete |

---

## 🎯 Next Steps

1. **Set up OAuth apps** for each platform
2. **Add credentials** to `.env`
3. **Test OAuth flows** end-to-end
4. **Update production redirect URIs** when deploying
5. **Monitor token expiry** (implement refresh if needed)

---

**All OAuth integrations are ready!** Just add your API credentials.
