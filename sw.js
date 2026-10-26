// Living Chess service worker — makes the game installable and fast on repeat loads.
// CACHE is stamped with a unique build id by deploy.sh, so every deploy installs a fresh
// worker, purges the previous cache on activate, and serves the new build.
const CACHE = 'living-chess-20261026233200';

self.addEventListener('install', () => self.skipWaiting());

self.addEventListener('activate', (e) => e.waitUntil(
  caches.keys()
    .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
    .then(() => self.clients.claim())
));

self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET') return;
  let url;
  try { url = new URL(req.url); } catch { return; }
  if (url.origin !== location.origin) return;   // never touch cross-origin (e.g. the Supabase API)

  // The page itself: always try the network first so a new deploy shows on the next load,
  // falling back to cache only when offline. The game assets it references are versioned
  // (?b=<build>) so they are fetched fresh whenever the build changes.
  if (req.mode === 'navigate') {
    e.respondWith(
      fetch(req)
        .then((res) => { caches.open(CACHE).then((c) => c.put(req, res.clone())); return res; })
        .catch(() => caches.match(req).then((h) => h || caches.match('index.html')))
    );
    return;
  }

  // Everything else: stale-while-revalidate (instant from cache, refresh in the background).
  e.respondWith(
    caches.open(CACHE).then((cache) => cache.match(req).then((hit) => {
      const net = fetch(req).then((res) => {
        if (res && res.ok && res.type === 'basic') cache.put(req, res.clone());
        return res;
      }).catch(() => hit);
      return hit || net;
    }))
  );
});
