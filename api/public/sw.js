const CACHE='crosslearn-shell-v3';
const FILES=['/','/assets/workspace.js','/assets/workspace.css','/assets/styles.css'];
self.addEventListener('install',e=>e.waitUntil(caches.open(CACHE).then(c=>c.addAll(FILES))));
self.addEventListener('activate',e=>e.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k))))));
self.addEventListener('fetch',e=>{const url=new URL(e.request.url);if(e.request.method!=='GET'||url.origin!==location.origin||!FILES.includes(url.pathname))return;e.respondWith(fetch(e.request).catch(()=>caches.match(e.request)));});
