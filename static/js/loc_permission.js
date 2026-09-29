// ============================================================
//  loc_permission.js
//  Place in: static/js/loc_permission.js
//
//  Shows a friendly modal the FIRST TIME a logged-in user
//  visits the site asking for location permission.
//  - If allowed  → saves GPS to localStorage, never shows again
//  - If skipped  → records skip in localStorage, never shows again
//  - If browser already granted/denied → never shows (silent)
//
//  Load this in base.html BEFORE geo_attendance.js
// ============================================================

(function () {
  'use strict';

  const ASKED_KEY  = 'gym_loc_asked';   // localStorage flag
  const LOC_KEY    = 'gym_location';

  // Only run for authenticated users
  const cfg = window.GYM_CONFIG || {};
  if (!cfg.isAuthenticated) return;

  // ── Already asked before? Skip. ─────────────────────────────
  if (localStorage.getItem(ASKED_KEY)) return;

  // ── Browser already granted permission? Cache & skip modal. ─
  if (navigator.permissions) {
    navigator.permissions.query({ name: 'geolocation' }).then(result => {
      if (result.state === 'granted') {
        // Already allowed — silently cache and mark as asked
        localStorage.setItem(ASKED_KEY, 'granted');
        silentCache();
        return;
      }
      if (result.state === 'denied') {
        // Already denied — mark as asked, don't show modal
        localStorage.setItem(ASKED_KEY, 'denied');
        return;
      }
      // 'prompt' state — show our custom modal
      showModal();
    }).catch(() => {
      // permissions API not supported — show modal anyway
      showModal();
    });
  } else {
    // No permissions API (Safari) — show modal
    showModal();
  }

  // ── Silently grab GPS and store in localStorage ──────────────
  function silentCache() {
    if (!navigator.geolocation) return;
    navigator.geolocation.getCurrentPosition(
      pos => {
        localStorage.setItem(LOC_KEY, JSON.stringify({
          lat: pos.coords.latitude,
          lng: pos.coords.longitude,
          ts:  Date.now(),
        }));
      },
      () => { /* silent fail */ },
      { enableHighAccuracy: true, timeout: 8000, maximumAge: 60_000 }
    );
  }

  // ── Build & inject modal HTML ────────────────────────────────
  function showModal() {
    // Small delay so the page renders first (better UX)
    setTimeout(() => {
      const modal = document.createElement('div');
      modal.id = 'loc-permission-modal';
      modal.innerHTML = `
        <div class="loc-modal-card">
          <span class="loc-modal-icon">📍</span>
          <h2 class="loc-modal-title">ENABLE LOCATION</h2>
          <p class="loc-modal-body">
            EnterGYM uses your location to make attendance <strong>automatic</strong>.
          </p>
          <ul class="loc-modal-features">
            <li>
              <span class="feat-icon">⚡</span>
              <div>
                <strong>Auto-mark attendance</strong>
                Walk into the gym and attendance marks itself — no tapping required.
              </div>
            </li>
            <li>
              <span class="feat-icon">🔒</span>
              <div>
                <strong>Private & secure</strong>
                Your location is only checked against the gym. Never stored on our servers.
              </div>
            </li>
            <li>
              <span class="feat-icon">📵</span>
              <div>
                <strong>Phone in your pocket</strong>
                Works in the background — you don't need to open the app.
              </div>
            </li>
          </ul>
          <div class="loc-modal-actions">
            <button class="btn-loc-allow" id="btn-loc-allow">
              ◈ ALLOW LOCATION ACCESS
            </button>
            <button class="btn-loc-skip" id="btn-loc-skip">
              Skip for now
            </button>
          </div>
          <p class="loc-modal-privacy">
            Location is only used on your device to check gym proximity.<br>
            We never track or store your location on our servers.
          </p>
        </div>
      `;

      document.body.appendChild(modal);

      // ── Allow button ─────────────────────────────────────────
      document.getElementById('btn-loc-allow').addEventListener('click', () => {
        const btn = document.getElementById('btn-loc-allow');
        btn.classList.add('loading');
        btn.textContent = 'REQUESTING…';

        if (!navigator.geolocation) {
          closeModal(modal);
          localStorage.setItem(ASKED_KEY, 'unsupported');
          return;
        }

        navigator.geolocation.getCurrentPosition(
          pos => {
            // ✅ Granted — save location and flag
            localStorage.setItem(LOC_KEY, JSON.stringify({
              lat: pos.coords.latitude,
              lng: pos.coords.longitude,
              ts:  Date.now(),
            }));
            localStorage.setItem(ASKED_KEY, 'granted');

            // Tell SW about the new location
            if (navigator.serviceWorker.controller) {
              navigator.serviceWorker.controller.postMessage({
                type: 'CACHE_LOC',
                lat: pos.coords.latitude,
                lng: pos.coords.longitude,
              });
            }

            closeModal(modal, true);   // true = show success flash
          },
          error => {
            // ❌ Denied or failed
            localStorage.setItem(ASKED_KEY, error.code === 1 ? 'denied' : 'failed');
            closeModal(modal);

            // Show a gentle inline message if on attendance page
            if (cfg.onAttendancePage) {
              const errEl = document.getElementById('geo-error');
              const txtEl = document.getElementById('geo-error-text');
              if (errEl && txtEl) {
                txtEl.textContent = '⊘ LOCATION DENIED — tap the 🔒 lock icon in your browser to enable';
                errEl.style.display = 'block';
              }
            }
          },
          { enableHighAccuracy: true, timeout: 15_000, maximumAge: 0 }
        );
      });

      // ── Skip button ──────────────────────────────────────────
      document.getElementById('btn-loc-skip').addEventListener('click', () => {
        localStorage.setItem(ASKED_KEY, 'skipped');
        closeModal(modal);
      });

      // ── Close on backdrop click ──────────────────────────────
      modal.addEventListener('click', e => {
        if (e.target === modal) {
          localStorage.setItem(ASKED_KEY, 'skipped');
          closeModal(modal);
        }
      });

    }, 800);   // 800ms delay — page loads first
  }

  // ── Close modal with optional success flash ──────────────────
  function closeModal(modal, success = false) {
    modal.style.transition = 'opacity 0.3s ease';
    modal.style.opacity    = '0';

    setTimeout(() => {
      modal.remove();

      if (success) {
        // Flash a small success toast
        const toast = document.createElement('div');
        toast.style.cssText = `
          position: fixed;
          bottom: 24px;
          left: 50%;
          transform: translateX(-50%);
          background: rgba(57,255,110,0.1);
          border: 1px solid rgba(57,255,110,0.4);
          border-radius: 8px;
          padding: 12px 24px;
          font-family: 'Share Tech Mono', monospace;
          font-size: 13px;
          color: #39ff6e;
          letter-spacing: 1px;
          z-index: 99999;
          white-space: nowrap;
          box-shadow: 0 0 20px rgba(57,255,110,0.2);
          animation: toastIn 0.3s ease forwards;
        `;
        toast.textContent = '✓ LOCATION ENABLED — AUTO-ATTENDANCE ACTIVE';
        document.body.appendChild(toast);

        setTimeout(() => {
          toast.style.transition = 'opacity 0.4s ease';
          toast.style.opacity = '0';
          setTimeout(() => toast.remove(), 400);
        }, 3000);
      }
    }, 300);
  }

})();