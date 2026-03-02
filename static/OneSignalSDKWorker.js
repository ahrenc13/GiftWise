// GiftWise Service Worker (OneSignal push + same-origin passthrough)
//
// CRITICAL: Register our fetch handler BEFORE importScripts so it fires first.
// For every same-origin request (Flask API calls), we call event.respondWith()
// ourselves, which prevents any subsequent handler (including OneSignal's) from
// intercepting it. This fixes the silent hang on POST /api/generate-recommendations.

self.addEventListener('fetch', function(event) {
    // Same-origin requests: pass directly to the network, no SW interception.
    if (new URL(event.request.url).origin === self.location.origin) {
        event.respondWith(fetch(event.request));
        return;
    }
    // Cross-origin requests fall through to OneSignal's handler below.
});

// Activate immediately when a new version of this script is deployed —
// don't wait for existing tabs to close.
self.addEventListener('install', function() {
    self.skipWaiting();
});

self.addEventListener('activate', function(event) {
    event.waitUntil(self.clients.claim());
});

importScripts('https://cdn.onesignal.com/sdks/web/v16/OneSignalSDK.sw.js');
