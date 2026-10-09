const CACHE_NAME = 'btube-v2';

// BTube ke core offline assets
const ASSETS_TO_CACHE = [
  './',
  './frontend/index.html',
  './frontend/style.css',
  './frontend/app.js',
  './assets/js/api-client.js',
  './pages/watch.html',
  './pages/shorts.html',
  './pages/upload.html',
  './pages/upload-video.html',
  './pages/upload-short.html',
  './pages/your-videos.html',
  './manifest.json'
];

// Install Event
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(ASSETS_TO_CACHE);
    })
  );
  self.skipWaiting();
});

// Activate Event (Old Cache Cleanup)
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            return caches.delete(key);
          }
        })
      );
    })
  );
  self.clients.claim();
});

// Fetch Event
self.addEventListener('fetch', (event) => {
  const requestUrl = new URL(event.request.url);

  // 1. Video files aur Range streaming requests ko Service Worker se bypass karein
  if (
    requestUrl.pathname.includes('/api/videos/') ||
    requestUrl.pathname.endsWith('.mp4') ||
    requestUrl.pathname.endsWith('.webm') ||
    event.request.headers.get('range')
  ) {
    return; // Direct network fetch hone de
  }

  // 2. Static Assets ke liye Cache First / Network Fallback
  event.respondWith(
    caches.match(event.request).then((cachedResponse) => {
      if (cachedResponse) {
        return cachedResponse;
      }

      return fetch(event.request)
        .then((networkResponse) => {
          // Valid response ko cache me update karein (sirf GET requests)
          if (
            networkResponse &&
            networkResponse.status === 200 &&
            event.request.method === 'GET' &&
            !requestUrl.protocol.startsWith('chrome-extension')
          ) {
            const responseClone = networkResponse.clone();
            caches.open(CACHE_NAME).then((cache) => {
              cache.put(event.request, responseClone);
            });
          }
          return networkResponse;
        })
        .catch(() => {
          // Offline hone par navigation request par index.html dikhayein
          if (event.request.mode === 'navigate') {
            return caches.match('./frontend/index.html');
          }
        });
    })
  );
});
