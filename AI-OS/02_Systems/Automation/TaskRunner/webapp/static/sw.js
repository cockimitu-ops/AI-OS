// Service worker: cache the app shell only. /api/* is never cached - a
// dashboard or chat reply served from a stale cache would be worse than no
// offline support at all, since it would look current and not be.
// v5: the Nothing Phone was showing an app old enough to predate the compute
// nodes entirely - no PC in the list at all. Network-first already fetches a
// fresh app.js, but the service worker ITSELF only updates when the browser
// re-fetches sw.js, and a changed cache name is what forces that activation.
const SHELL_CACHE = "aios-shell-v5";
const SHELL_FILES = [
  "./", "./index.html", "./app.js", "./fx.js", "./style.css", "./manifest.json",
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
  // Never touched by the cache:
  //   /api/*       - a dashboard or chat reply from a stale cache would look
  //                  current without being current, which is worse than no
  //                  offline support at all.
  //   /downloads/* - generated reports hold real business names, addresses
  //                  and phone numbers. The server gates those behind a
  //                  token; a copy sitting in a browser cache is not gated
  //                  by anything.
  if (url.pathname.startsWith("/api/") || url.pathname.startsWith("/downloads/")) {
    return;
  }
  // Network-first for the app shell, cache only as the offline fallback.
  // Cache-first is the usual PWA default and it is the wrong one here: this
  // app changes several times a day, and a service worker serving last
  // week's app.js from cache is the classic way a PWA gets stuck on a
  // version its owner has already fixed - invisible, because the page loads
  // perfectly, just wrong.
  event.respondWith(
    fetch(event.request)
      .then((response) => {
        if (response && response.ok && event.request.method === "GET") {
          const copy = response.clone();
          caches.open(SHELL_CACHE).then((cache) => cache.put(event.request, copy));
        }
        return response;
      })
      .catch(() => caches.match(event.request))
  );
});
