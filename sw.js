/**
 * BTube PWA Service Worker (v11)
 * Features:
 * - App-Shell Precaching (Offline UI Fallback)
 * - Video Stream Passthrough (Prevents HTTP 206 Range Errors)
 * - Safe Bypass for FastAPI Backend, Cloud Storage & Firebase
 * - Immediate Lifecycle Takeover (skipWaiting + clients.claim)
 */

const CACHE_NAME = 'btube-live-v11';

// Static Shell Assets for Instant App Launch
const APP_SHELL_ASSETS = [
    '/',
    '/index.html',
    '/assets/css/global.css',
    '/assets/js/api-client.js',
    '/manifest.json'
];

// 1. Install Event: Cache essential UI assets & activate immediately
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            return cache.addAll(APP_SHELL_ASSETS).catch((err) => {
                console.warn('[ServiceWorker] Shell precache partial skip:', err);
            });
        })
    );
    self.skipWaiting();
});

// 2. Activate Event: Wipe stale caches and claim all clients
self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames.map((cache) => {
                    if (cache !== CACHE_NAME) {
                        return caches.delete(cache);
                    }
                })
            );
        }).then(() => {
            return self.clients.claim();
        })
    );
});

// 3. Fetch Event: Media-aware streaming & Network-First Strategy
self.addEventListener('fetch', (event) => {
    const request = event.request;
    const requestUrl = new URL(request.url);

    // BYPASS 1: Non-GET requests (POST uploads, auth, Super Thanks ledger)
    if (request.method !== 'GET') {
        return;
    }

    // BYPASS 2: Video/Audio streaming & Range requests (Prevents HTTP 206 Cache exceptions)
    if (
        request.headers.get('range') ||
        requestUrl.pathname.endsWith('.mp4') ||
        requestUrl.pathname.endsWith('.webm') ||
        requestUrl.pathname.endsWith('.m4a') ||
        requestUrl.pathname.includes('/stream')
    ) {
        return; // Direct network browser passthrough
    }

    // BYPASS 3: Backend API routes & External Cloud Services
    if (
        requestUrl.pathname.startsWith('/api/') ||
        requestUrl.pathname.startsWith('/uploads/') ||
        requestUrl.hostname.includes('firebase') ||
        requestUrl.hostname.includes('googleapis.com') ||
        requestUrl.hostname.includes('firestore') ||
        requestUrl.hostname.includes('onrender.com')
    ) {
        return; // Direct live network fetch
    }

    // APP ASSETS: Network-First with Cache Fallback
    event.respondWith(
        fetch(request)
            .then((networkResponse) => {
                // Cache valid HTTP 200 responses only
                if (networkResponse && networkResponse.status === 200 && networkResponse.type === 'basic') {
                    const responseClone = networkResponse.clone();
                    caches.open(CACHE_NAME).then((cache) => {
                        cache.put(request, responseClone);
                    });
                }
                return networkResponse;
            })
            .catch(() => {
                // Fallback to cache when offline
                return caches.match(request).then((cachedResponse) => {
                    if (cachedResponse) {
                        return cachedResponse;
                    }
                    // Offline landing fallback
                    if (request.mode === 'navigate') {
                        return caches.match('/index.html');
                    }
                });
            })
    );
});
