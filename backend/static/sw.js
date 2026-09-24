const CACHE_NAME = 'ya-materiels-v1';
const SHELL_URLS = [
  '/',
  'https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js',
  'https://cdn.jsdelivr.net/npm/xlsx@0.18.5/dist/xlsx.full.min.js',
];

// Installation : mise en cache du shell
self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE_NAME).then(c => c.addAll(SHELL_URLS).catch(() => {}))
  );
  self.skipWaiting();
});

// Activation : suppression des anciens caches
self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

// Interception des requêtes
self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);

  // Requêtes API : réseau uniquement — pas de mise en cache SW
  // (géré côté JS avec localStorage)
  if(url.pathname.startsWith('/api/')) {
    e.respondWith(
      fetch(e.request).catch(() =>
        new Response(JSON.stringify({error:'offline', detail:'Hors connexion'}),
          {status:503, headers:{'Content-Type':'application/json'}})
      )
    );
    return;
  }

  // Ressources CDN externe : cache first
  if(url.origin !== self.location.origin) {
    e.respondWith(
      caches.match(e.request).then(cached => {
        if(cached) return cached;
        return fetch(e.request).then(res => {
          if(res.ok) {
            const clone = res.clone();
            caches.open(CACHE_NAME).then(c => c.put(e.request, clone));
          }
          return res;
        }).catch(() => cached || new Response('', {status:504}));
      })
    );
    return;
  }

  // Shell HTML : network first, fallback cache
  e.respondWith(
    fetch(e.request).then(res => {
      if(res.ok) {
        const clone = res.clone();
        caches.open(CACHE_NAME).then(c => c.put(e.request, clone));
      }
      return res;
    }).catch(() => caches.match('/').then(c => c || new Response('Hors connexion', {status:503})))
  );
});
