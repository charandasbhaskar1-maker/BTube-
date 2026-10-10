javascript
const CACHE_NAME = 'btube-v3';

const ASSETS_TO_CACHE = [
  './',
  './index.html',
  './manifest.json',
  './frontend/index.html',
  './frontend/style.css',
  './frontend/app.js',
  './assets/js/api-client.js',
  './pages/watch.html',
  './pages/shorts.html',
  './pages/upload.html',
  './pages/upload-video.html',
  './pages/upload-short.html',
  './pages/your-videos.html'
];

// Service Worker install
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(ASSETS_TO_CACHE))
      .catch(error => {
        console.error('BTube cache install error:', error);
      })
  );

  self.skipWaiting();
});

// पुराने कैश हटाएँ
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys
          .filter(key => key.startsWith('btube-') &&
                         key !== CACHE_NAME)
          .map(key => caches.delete(key))
      )
    ).then(() => self.clients.claim())
  );
});

// नेटवर्क और कैश से पेज लोड करना
self.addEventListener('fetch', event => {
  const request = event.request;
  const url = new URL(request.url);

  // केवल GET requests संभालें
  if (request.method !== 'GET') return;

  // Firebase और अन्य बाहरी साइटों को कैश न करें
  if (url.origin !== self.location.origin) return;

  // वीडियो स्ट्रीमिंग और Range requests को सीधे नेटवर्क से चलाएँ
  if (
    url.pathname.includes('/api/videos/') ||
    /\.(mp4|webm|mov|m4v)$/i.test(url.pathname) ||
    request.headers.has('range')
  ) {
    return;
  }

  // HTML पेज: पहले नेटवर्क, फिर ऑफलाइन होने पर कैश
  const isHTML =
    request.mode === 'navigate' ||
    request.destination === 'document' ||
    url.pathname.endsWith('.html') ||
    url.pathname.endsWith('/');

  if (isHTML) {
    event.respondWith(
      fetch(request)
        .then(response => {
          if (response.ok) {
            const copy = response.clone();
            caches.open(CACHE_NAME)
              .then(cache => cache.put(request, copy));
          }
          return response;
        })
        .catch(async () => {
          const cached = await caches.match(request);

          if (cached) return cached;

          return new Response(
            'BTube खोलने के लिए इंटरनेट कनेक्शन आवश्यक है।',
            {
              status: 503,
              headers: {
                'Content-Type': 'text/plain; charset=utf-8'
              }
            }
          );
        })
    );

    return;
  }

  // CSS, JavaScript और अन्य स्थिर फाइलें
  event.respondWith(
    caches.match(request).then(async cached => {
      const networkPromise = fetch(request).then(response => {
        if (response.ok) {
          const copy = response.clone();
          caches.open(CACHE_NAME)
            .then(cache => cache.put(request, copy));
        }
        return response;
      });

      // उपलब्ध कैश तुरंत दें और नेटवर्क से अपडेट करें।
      // अगली बार नया संस्करण इस्तेमाल होगा।
      if (cached) {
        event.waitUntil(networkPromise.catch(() => {}));
        return cached;
      }

      return networkPromise;
    })
  );
});
