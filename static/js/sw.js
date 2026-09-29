// ============================================================
//  EnterGYM Service Worker v7
//  /api/geo-mark-attendance/ is @csrf_exempt + @login_required
//  so no CSRF token needed — session cookie handles auth.
//  Security: NO gym coords, NO userId, NO client-side check.
// ============================================================

self.addEventListener('install',  () => self.skipWaiting());
self.addEventListener('activate', e  => e.waitUntil(self.clients.claim()));

// ── State ────────────────────────────────────────────────────
let isEnrolled      = false;
let userHash        = '';      // opaque per-user hash, no raw PK
let watchIntervalId = null;

// ── Message handler ──────────────────────────────────────────
self.addEventListener('message', async (event) => {
  const msg = event.data || {};

  switch (msg.type) {

    case 'START_GEO':
      isEnrolled = msg.config?.isEnrolled === true;
      userHash   = msg.config?.userHash   || '';

      if (watchIntervalId === null && isEnrolled) {
        requestLocationFromClients();
        watchIntervalId = setInterval(requestLocationFromClients, 30_000);
      }
      break;

    case 'REPORT_LOC':
    case 'CACHE_LOC':
      if (isEnrolled) {
        await tryAutoMark(msg.lat, msg.lng);
      }
      break;

    case 'STOP_GEO':
      clearInterval(watchIntervalId);
      watchIntervalId = null;
      break;
  }
});

// ── Ask all open tabs for their current GPS position ─────────
async function requestLocationFromClients() {
  if (!isEnrolled) return;
  const clients = await self.clients.matchAll({ type: 'window' });
  if (clients.length === 0) return;
  clients.forEach(c => c.postMessage({ type: 'REQUEST_LOC' }));
}

// ── Main auto-mark flow ──────────────────────────────────────
async function tryAutoMark(lat, lng) {
  if (lat == null || lng == null) return;

  // Namespace flag by userHash — no bleed between users on same device
  const today   = new Date().toISOString().slice(0, 10);
  const doneKey = `att_done_${userHash}_${today}`;

  const flagCache = await caches.open('att-flags');
  const existing  = await flagCache.match(doneKey);
  if (existing) return;   // already marked today — skip

  const result = await postCoordsToServer(lat, lng);
  if (!result) return;

  const { status } = result;

  if (status === 'success') {
    await flagCache.put(doneKey, new Response('1'));
    showNotification('✅ Attendance Marked!',
      "You're at EnterGYM — attendance logged automatically.");
    const clients = await self.clients.matchAll({ type: 'window' });
    clients.forEach(c => c.postMessage({ type: 'ATTENDANCE_MARKED' }));
    clearInterval(watchIntervalId);
    watchIntervalId = null;

  } else if (status === 'exists') {
    await flagCache.put(doneKey, new Response('1'));
    clearInterval(watchIntervalId);
    watchIntervalId = null;

  } else if (status === 'expired' || status === 'not_enrolled') {
    isEnrolled = false;
    clearInterval(watchIntervalId);
    watchIntervalId = null;
  }
  // 'out_of_range' → keep polling every 30s
}

// ── POST user's coords to server ─────────────────────────────
async function postCoordsToServer(lat, lng) {
  try {
    const res = await fetch('/api/geo-mark-attendance/', {
      method:      'POST',
      credentials: 'include',          // sends session cookie — that's all we need
      headers:     { 'Content-Type': 'application/json' },
      body:        JSON.stringify({ lat, lng }),
    });

    if (res.status === 429) return { status: 'rate_limited' };
    if (res.status === 403) {
      const data = await res.json().catch(() => ({}));
      return { status: data.status || 'forbidden' };
    }
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;   // offline / Render cold-start
  }
}

// ── Push notification ─────────────────────────────────────────
async function showNotification(title, body) {
  if (Notification.permission !== 'granted') return;
  if (self.registration.showNotification) {
    self.registration.showNotification(title, {
      body,
      icon:     '/static/images/Logo.png',
      badge:    '/static/images/Logo.png',
      tag:      'gym-attendance',
      renotify: false,
      data:     { url: '/attendence/' },
    });
  }
}

// ── Notification click → open attendance page ─────────────────
self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  event.waitUntil(
    self.clients.matchAll({ type: 'window' }).then(clients => {
      for (const c of clients) {
        if (c.url.includes('/attendence/')) { c.focus(); return; }
      }
      self.clients.openWindow('/attendence/');
    })
  );
});

// Handle incoming push
self.addEventListener('push', function(event) {
    const data = event.data.json();
    event.waitUntil(
        self.registration.showNotification(data.title, {
            body: data.body,
            icon: '/static/icons/icon-192.png',
            badge: '/static/icons/icon-72.png',
            data: { url: data.url }
        })
    );
});

// Handle notification click
self.addEventListener('notificationclick', function(event) {
    event.notification.close();
    event.waitUntil(
        clients.openWindow(event.notification.data.url)
    );
});