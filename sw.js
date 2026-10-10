// BTube PWA Service Worker (Cache-Busting & Cloud Stream Passthrough)
const CACHE_NAME = 'btube-live-v10';

// Install Event: Purane sabhi workers ko turant replace karein
self.addEventListener('install', (event) => {
    console.log('[ServiceWorker] Installing new version:', CACHE_NAME);
    self.skipWaiting();
});

// Activate Event: Purana saara demo cache turant delete karein
self.addEventListener('activate', (event) => {
    console.log('[ServiceWorker] Activating & wiping old stale cache...');
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames.map((cache) => {
                    if (cache !== CACHE_NAME) {
                        console.log('[ServiceWorker] Deleting old cache:', cache);
                        return caches.delete(cache);
                    }
                })
            );
        }).then(() => {
            return self.clients.claim();
        })
    );
});

// Fetch Event: Network-First Strategy
// Firebase calls, audio/video streams, aur cloud data ko bina roke seedha live network se chalayein
self.addEventListener('fetch', (event) => {
    const requestUrl = new URL(event.request.url);

    // 1. Firebase API, Firestore, Google APIs, aur Storage streams ko bypass karein (No Caching)
    if (
        requestUrl.hostname.includes('firebase') ||
        requestUrl.hostname.includes('googleapis.com') ||
        requestUrl.hostname.includes('firestore') ||
        event.request.url.includes('.mp4') ||
        event.request.url.includes('.webm')
    ) {
        return; // Direct network stream
    }

    // 2. Normal Web Pages & Assets: Pehle fresh network se layein, fail hone par hi cache dekhein
    event.respondWith(
        fetch(event.request)
            .then((networkResponse) => {
                return networkResponse;
            })
            .catch(() => {
                return caches.match(event.request);
            })
    );
});
