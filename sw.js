/* Genie's Film Spinner - offline shell + poster cache */
const VERSION = "v2";
const SHELL = `spinner-shell-${VERSION}`;
const POSTERS = `spinner-posters-${VERSION}`;
const SHELL_FILES = [
  "./", "./index.html", "./films.json", "./manifest.webmanifest",
  "./icons/icon-192.png", "./icons/icon-512.png",
  "./icons/icon-maskable-512.png", "./icons/apple-touch-icon.png",
];
const POSTER_LIMIT = 400;

self.addEventListener("install", e => {
  e.waitUntil(caches.open(SHELL)
    .then(c => c.addAll(SHELL_FILES))
    .then(() => self.skipWaiting()));
});

self.addEventListener("activate", e => {
  e.waitUntil(caches.keys()
    .then(keys => Promise.all(keys
      .filter(k => k !== SHELL && k !== POSTERS)
      .map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

async function trim(cache, max) {
  const keys = await cache.keys();
  if (keys.length > max) {
    for (const k of keys.slice(0, keys.length - max)) await cache.delete(k);
  }
}

self.addEventListener("fetch", e => {
  const { request } = e;
  if (request.method !== "GET") return;
  const url = new URL(request.url);

  // posters: serve from cache, fall back to network and keep a copy
  if (url.hostname === "a.ltrbxd.com") {
    e.respondWith((async () => {
      const cache = await caches.open(POSTERS);
      const hit = await cache.match(request);
      if (hit) return hit;
      try {
        const res = await fetch(request);
        if (res.ok || res.type === "opaque") {
          cache.put(request, res.clone()).then(() => trim(cache, POSTER_LIMIT));
        }
        return res;
      } catch (err) {
        return hit || Response.error();
      }
    })());
    return;
  }

  // app shell: network first so a redeploy is picked up, cache as the fallback
  if (url.origin === self.location.origin) {
    e.respondWith((async () => {
      try {
        const res = await fetch(request);
        if (res.ok) (await caches.open(SHELL)).put(request, res.clone());
        return res;
      } catch (err) {
        const hit = await caches.match(request);
        return hit || (await caches.match("./index.html")) || Response.error();
      }
    })());
  }
});
