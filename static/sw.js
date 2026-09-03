// Minimal service worker -- exists mainly so the browser considers this
// site "installable" (Add to Home Screen / Install app) on Android/Chrome.
// It intentionally does NOT cache any page content (dashboard, portal,
// puppy listings, etc.) -- those always come from the network, so nothing
// ever goes stale. Only the static app shell (logo/icons/css) is
// cache-first, since those rarely change and it's safe to reuse them.
//
// IMPORTANT: whenever style.css, the logo, or an icon changes, bump this
// version string -- otherwise installed apps keep serving the old cached
// file indefinitely, even after a fresh deploy.
const SHELL_CACHE = "summit-doodles-shell-v4";
const SHELL_ASSETS = [
  "/static/css/style.css",
  "/static/img/logo-full.png",
  "/static/img/logo-icon.png",
  "/static/img/icons/icon-192.png",
  "/static/img/icons/icon-512.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(SHELL_CACHE).then((cache) => cache.addAll(SHELL_ASSETS)).catch(() => {})
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
  const isShellAsset = event.request.method === "GET" && SHELL_ASSETS.includes(url.pathname);
  if (!isShellAsset) return; // everything else: normal network request, untouched
  event.respondWith(
    caches.match(event.request).then((cached) => cached || fetch(event.request))
  );
});
