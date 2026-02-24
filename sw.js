const cacheName = 'kutus-boda-v1';
const assets = ['./', './index.html', './manifest.json'];

// Install Service Worker
self.addEventListener('install', e => {
  e.waitUntil(caches.open(cacheName).then(cache => cache.addAll(assets)));
});

// Fetching assets
self.addEventListener('fetch', e => {
  e.respondWith(caches.match(e.request).then(res => res || fetch(e.request)));
});