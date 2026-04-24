// Minimal service worker for PWA installability
self.addEventListener("install", (e) => {
  self.skipWaiting();
});

self.addEventListener("activate", (e) => {
  e.waitUntil(self.clients.claim());
});

self.addEventListener("fetch", (e) => {
  // Let the browser handle fetches normally.
  // Next.js App Router already handles static caching well.
});
