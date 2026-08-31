// Service worker: cache the app shell only. /api/* is never cached - a
// dashboard or chat reply served from a stale cache would be worse than no
// offline support at all, since it would look current and not be.
const SHELL_CACHE = "aios-shell-v1";
const SHELL_FILES = [
  "./", "./index.html", "./app.js", "./style.css", "./manifest.json",
  "./icons/icon-192.png", "./icons/icon-512.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(SHELL_CACHE).then((cache) => cache.addAll(SHELL_FILES))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((names) =>
      Promise.all(names.filter((n) => n !== SHELL_CACHE).map((n) => caches.delete(n)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  if (url.pathname.startsWith("/api/")) {
    return; // let the network handle it, no caching, no offline fallback
  }
  event.respondWith(
    caches.match(event.request).then((cached) => cached || fetch(event.request))
  );
});
