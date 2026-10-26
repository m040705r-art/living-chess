// Living Chess service worker — makes the game installable and fast on repeat loads.
// Strategy: stale-while-revalidate for same-origin GETs. First load fills the cache; later loads
// serve instantly from cache and refresh in the background. Bump CACHE to force a refresh.
const CACHE = 'living-chess-v1';

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
