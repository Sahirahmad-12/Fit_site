// ============================================================
//  geo_attendance.js  v7
//  /api/geo-mark-attendance/ is @csrf_exempt so SW messages
//  no longer need to carry csrfToken.
//  Manual button still sends X-CSRFToken (good practice).
//  Security: no gym coords, no userId in client code.
// ============================================================

(function () {
  'use strict';

  const cfg = window.GYM_CONFIG || {};
  const { isAuthenticated, isEnrolled, userHash } = cfg;
  const onAttendancePage = window.location.pathname.includes('attendence');

  // ── Location cache (localStorage, 10 min TTL) ────────────────
  const LOC_KEY    = `gym_loc_${userHash || 'anon'}`;
  const LOC_MAX_MS = 10 * 60 * 1000;

  function saveLoc(lat, lng) {
    try {
      localStorage.setItem(LOC_KEY, JSON.stringify({ lat, lng, ts: Date.now() }));
    } catch { /* storage full or private mode */ }
  }

  function loadLoc() {
    try {
      const raw = localStorage.getItem(LOC_KEY);
      if (!raw) return null;
      const loc = JSON.parse(raw);
      if (Date.now() - loc.ts > LOC_MAX_MS) return null;
      return loc;
    } catch { return null; }
  }

  // ── CSRF token (only used by manual button fetch) ────────────
  function getCsrf() {
    const m = document.cookie.match(/(^|;)\s*csrftoken=([^;]+)/);
    return m ? m[2] : '';
  }

  // ── Send message to active Service Worker ────────────────────
  function swPost(msg) {
    if (navigator.serviceWorker?.controller) {
      navigator.serviceWorker.controller.postMessage(msg);
    }
  }

  // ── Register Service Worker ──────────────────────────────────
  async function registerSW() {
    if (!('serviceWorker' in navigator)) return null;
    try {
      const reg = await navigator.serviceWorker.register(
        '/sw.js', { scope: '/', updateViaCache: 'none' }
      );
      reg.update();
      return reg;
    } catch { return null; }
  }

  // ── Tell SW to start polling ──────────────────────────────────
  function sendStartGeo() {
    swPost({
      type:   'START_GEO',
      config: {
        isEnrolled: Boolean(isEnrolled),
        userHash:   userHash || '',
        // ✅ NO gymLat, NO gymLng, NO radius, NO userId
      },
    });

    // If we have a cached position, give it to SW immediately
    const loc = loadLoc();
    if (loc) {
      setTimeout(() => swPost({ type: 'REPORT_LOC', lat: loc.lat, lng: loc.lng }), 400);
    }
  }

  // ── Listen for SW messages ───────────────────────────────────
  function listenToSW() {
    navigator.serviceWorker.addEventListener('message', (event) => {
      const { type } = event.data || {};

      if (type === 'REQUEST_LOC') {
        const cached = loadLoc();
        if (cached) {
          swPost({ type: 'REPORT_LOC', lat: cached.lat, lng: cached.lng });
          refreshLocCache();
        } else {
          navigator.geolocation.getCurrentPosition(
            (pos) => {
              saveLoc(pos.coords.latitude, pos.coords.longitude);
              swPost({ type: 'REPORT_LOC', lat: pos.coords.latitude, lng: pos.coords.longitude });
            },
            () => { /* silent */ },
            { enableHighAccuracy: true, timeout: 8000, maximumAge: 30_000 }
          );
        }
      }

      if (type === 'ATTENDANCE_MARKED' && onAttendancePage) {
        setTimeout(() => window.location.reload(), 1200);
      }
    });
  }

  function refreshLocCache() {
    if (!navigator.geolocation) return;
    navigator.geolocation.getCurrentPosition(
      (pos) => saveLoc(pos.coords.latitude, pos.coords.longitude),
      () => { /* silent */ },
      { enableHighAccuracy: true, timeout: 8000, maximumAge: 60_000 }
    );
  }

  function silentlyCache() {
    if (!navigator.geolocation) return;
    if (loadLoc()) { refreshLocCache(); return; }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        saveLoc(pos.coords.latitude, pos.coords.longitude);
        swPost({ type: 'CACHE_LOC', lat: pos.coords.latitude, lng: pos.coords.longitude });
      },
      () => { /* no permission yet */ },
      { enableHighAccuracy: true, timeout: 8000, maximumAge: 60_000 }
    );
  }

  // ── POST coords to server (manual button) ────────────────────
  async function postToServer(lat, lng) {
    const res = await fetch('/api/geo-mark-attendance/', {
      method:      'POST',
      credentials: 'same-origin',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken':  getCsrf(),   // still good practice for manual fetches
      },
      body: JSON.stringify({ lat, lng }),
    });
    if (res.status === 429) return { status: 'rate_limited' };
    try { return await res.json(); } catch { return { status: 'error' }; }
  }

  // ── UI helpers ───────────────────────────────────────────────
  function showGeoError(msg, distance) {
  const box  = document.getElementById('geo-error');
  const txt  = document.getElementById('geo-error-text');
  const dist = document.getElementById('geo-distance');
  if (txt) txt.textContent = msg;
  if (dist) dist.textContent = distance != null ? `📍 ${distance}m FROM GYM` : '';
  if (box) box.style.display = 'block';
  }

  function hideGeoError() {
  const box  = document.getElementById('geo-error');
  const dist = document.getElementById('geo-distance');
  if (box) box.style.display = 'none';
  if (dist) dist.textContent = '';
  }

  function setBtn(state) {
    const btn   = document.getElementById('btn-attend');
    const label = document.getElementById('btn-label');
    if (!btn || !label) return;
    if (state === 'loading') {
      btn.disabled      = true;
      label.textContent = '◈ LOCATING…';
    } else if (state === 'marked') {
      btn.disabled = true;
      btn.classList.add('marked');
      label.innerHTML = '<span class="check-icon">✓</span> ATTENDANCE LOGGED';
    } else {
      btn.disabled    = false;
      label.innerHTML = '<span class="pulse-ring"></span>◈ MARK ATTENDANCE';
    }
  }

  // ── Manual button press handler ──────────────────────────────
  window.checkLocationAndSubmit = function () {
    hideGeoError();
    if (!navigator.geolocation) {
      showGeoError('⊘ GEOLOCATION NOT SUPPORTED BY THIS BROWSER');
      return;
    }

    function handleResult(data) {
      switch (data?.status) {
        case 'success':
          setBtn('marked');
          hideGeoError();
          setTimeout(() => window.location.reload(), 1200);
          break;
        case 'exists':
          setBtn('marked');
          hideGeoError();
          break;
        case 'out_of_range':
          setBtn('idle');
          showGeoError('⊘ NOT AT GYM — MUST BE WITHIN GYM PREMISES', data.distance);
          break;
        case 'expired':
          setBtn('idle');
          showGeoError('⊘ MEMBERSHIP EXPIRED — PLEASE RENEW');
          break;
        case 'not_enrolled':
          setBtn('idle');
          showGeoError('⊘ NOT ENROLLED — PLEASE ENROLL FIRST');
          break;
        case 'rate_limited':
          setBtn('idle');
          showGeoError('⊘ TOO MANY ATTEMPTS — TRY AGAIN IN A MINUTE');
          break;
        default:
          setBtn('idle');
          showGeoError('⊘ ERROR — PLEASE TRY AGAIN');
      }
    }

    const cached = loadLoc();
    if (cached) {
      setBtn('loading');
      postToServer(cached.lat, cached.lng).then(handleResult).catch(() => {
        setBtn('idle');
        showGeoError('⊘ NETWORK ERROR — CHECK CONNECTION');
      });
      refreshLocCache();
      return;
    }

    setBtn('loading');
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const { latitude: lat, longitude: lng } = pos.coords;
        saveLoc(lat, lng);
        postToServer(lat, lng).then(handleResult).catch(() => {
          setBtn('idle');
          showGeoError('⊘ NETWORK ERROR — CHECK CONNECTION');
        });
      },
      (err) => {
        setBtn('idle');
        showGeoError(
          err.code === 1 ? '⊘ LOCATION BLOCKED — Allow location in browser settings' :
          err.code === 2 ? '⊘ LOCATION UNAVAILABLE — Check GPS / Network' :
                           '⊘ LOCATION TIMED OUT — Try again'
        );
      },
      { enableHighAccuracy: true, timeout: 10_000, maximumAge: 0 }
    );
  };

  async function requestNotifPermission() {
    if (!('Notification' in window)) return;
    if (Notification.permission === 'default') await Notification.requestPermission();
  }

  async function init() {
    if (!isAuthenticated) return;
    const reg = await registerSW();
    if (!reg) return;
    listenToSW();
    if (!isEnrolled) return;
    await requestNotifPermission();
    silentlyCache();
    if (navigator.serviceWorker.controller) {
      sendStartGeo();
    } else {
      navigator.serviceWorker.addEventListener('controllerchange', () => sendStartGeo());
    }
    navigator.serviceWorker.ready.then(() => setTimeout(sendStartGeo, 800));
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();