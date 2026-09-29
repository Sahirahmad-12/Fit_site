# AuthFit/geo_views.py

import os
import json
import math
import logging
from django.utils import timezone
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from django.conf import settings
from django.core.cache import cache
from AuthFit.models import Attendence, Enrollment

logger = logging.getLogger(__name__)

# ── Load gym coords at startup — never sent to browser ───────
_GYM_LAT    = float(os.environ.get('GYM_LATITUDE',      21.2179))
_GYM_LNG    = float(os.environ.get('GYM_LONGITUDE',     81.3311))
_GYM_RADIUS = float(os.environ.get('GYM_RADIUS_METERS', 100))


def _haversine(lat1, lng1, lat2, lng2):
    R  = 6_371_000
    φ1 = math.radians(lat1)
    φ2 = math.radians(lat2)
    Δφ = math.radians(lat2 - lat1)
    Δλ = math.radians(lng2 - lng1)
    a  = math.sin(Δφ/2)**2 + math.cos(φ1) * math.cos(φ2) * math.sin(Δλ/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _is_json_request(request):
    """Only accept application/json — blocks form submissions and CSRF-bypass attempts."""
    ct = request.META.get('HTTP_CONTENT_TYPE', request.META.get('CONTENT_TYPE', ''))
    return 'application/json' in ct


# ── Main geo attendance endpoint ─────────────────────────────
@require_POST
@csrf_exempt
@login_required
def geo_mark_attendance(request):
    """
    POST /api/geo-mark-attendance/

    WHY csrf_exempt here:
      The Service Worker posts from a background context where injecting
      the CSRF cookie value into headers is unreliable (cookie may not be
      readable inside SW scope on some browsers). We compensate with:
        1. @login_required  — valid session cookie required (not forgeable cross-origin)
        2. Content-Type: application/json check — browser form submissions can't set this
        3. Rate limiting    — 10 calls/min per user
      This matches the standard Django REST / fetch-API pattern.

    Accepts: { "lat": float, "lng": float }
    Gym coordinates never leave the server.
    """
    uid = request.user.id
    # ── Reject non-JSON (form submissions, CSRF-bypass probes) ─
    if not _is_json_request(request):
        return JsonResponse(
            {'status': 'error', 'error': 'JSON required'},
            status=415
        )

    # ── Rate limit: 10 calls per minute per user ───────────────
    rl_key = f"geo_rl_{request.user.id}"
    calls  = cache.get(rl_key, 0)
    if calls >= 10:
        return JsonResponse(
            {'status': 'rate_limited', 'error': 'Too many requests'},
            status=429
        )
    try:
        cache.add(rl_key, 0, timeout=60)
        cache.incr(rl_key)
    except Exception:
        pass

    # ── Parse and validate coordinates ────────────────────────
    try:
        body = json.loads(request.body)
        lat  = float(body['lat'])
        lng  = float(body['lng'])
    except (KeyError, ValueError, TypeError, json.JSONDecodeError):
        return JsonResponse(
            {'status': 'error', 'error': 'Invalid coordinates'},
            status=400
        )

    if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
        return JsonResponse(
            {'status': 'error', 'error': 'Coordinates out of range'},
            status=400
        )

    # ── Enrollment check (cached 5 min) ───────────────────────
    enroll_key = f"enrollment_status_{uid}"
    enroll_data = cache.get(enroll_key)

    if enroll_data is None:
        try:
            enrollment  = Enrollment.objects.get(user=request.user)
            enroll_data = {'exists': True, 'expired': enrollment.is_expired}
            cache.set(enroll_key, enroll_data, timeout=300)
        except Enrollment.DoesNotExist:
            return JsonResponse({
                'status': 'not_enrolled',
                'error':  'Please enroll before marking attendance.'
            }, status=403)

    if not enroll_data.get('exists'):
        return JsonResponse({
            'status': 'not_enrolled',
            'error':  'Please enroll before marking attendance.'
        }, status=403)

    if enroll_data.get('expired'):
        return JsonResponse({
            'status': 'expired',
            'error':  'Your membership has expired. Please renew.'
        }, status=403)

    # ── Already marked today? (cache check first) ─────────────
    today   = timezone.localdate()
    att_key = f"att_marked_{request.user.id}_{today}"   # matches context_processors.py

    if cache.get(att_key):
        return JsonResponse({
            'status':  'exists',
            'message': 'Attendance already marked today.'
        })

    # ── Distance check — GYM COORDS NEVER LEAVE THIS FUNCTION ─
    distance = _haversine(lat, lng, _GYM_LAT, _GYM_LNG)
    if distance > _GYM_RADIUS:
        return JsonResponse(
        {
            'status': 'out_of_range',
            'message': 'You are not within the gym premises.',
            'distance': round(distance)
        },
        status=403
    )

    # ── Mark attendance ────────────────────────────────────────
    try:
        _, created = Attendence.objects.get_or_create(
            user=request.user,
            date=today,
        )
    except Exception:
        logger.exception("DB error in geo_mark_attendance user=%s", request.user.id)
        return JsonResponse(
            {'status': 'error', 'error': 'Database error. Try again.'},
            status=500
        )

    # Cache the marked flag
    cache.set(att_key, True, timeout=86400)

    # ── Invalidate the today attendance list cache ─────────────────
    cache.delete(f"today_attendance_{today}")  # staff list page

    if created:
        return JsonResponse({'status': 'success', 'message': 'Attendance marked!','distance': round(distance)})
    else:
        return JsonResponse({'status': 'exists', 'message': 'Attendance already marked today.','distance': round(distance)})


# ── Status check ──────────────────────────────────────────────
@login_required
@require_GET
def attendance_status(request):
    """GET /api/attendance-status/ — SW calls this before sending coords."""
    uid = request.user.id

    enroll_key = f"enrolled_{request.user.id}"
    enroll_data = cache.get(enroll_key)
    if enroll_data is None:
        try:
            enrollment  = Enrollment.objects.get(user=request.user)
            enroll_data = {'exists': True, 'expired': enrollment.is_expired}
        except Enrollment.DoesNotExist:
            enroll_data = {'exists': False, 'expired': False}
        cache.set(enroll_key, enroll_data, timeout=300)

    is_enrolled = enroll_data.get('exists') and not enroll_data.get('expired')
    if not is_enrolled:
        return JsonResponse({'marked': False, 'enrolled': False})

    today   = timezone.localdate()
    att_key = f"att_marked_{uid}_{today}"
    marked  = cache.get(att_key)

    if marked is None:
        marked = Attendence.objects.filter(user=request.user, date=today).exists()
        cache.set(att_key, marked, timeout=86400 if marked else 60)

    return JsonResponse({'marked': bool(marked), 'enrolled': True})


# ── Serve SW from root (/sw.js) ───────────────────────────────
def serve_sw(request):
    sw_path = os.path.join(settings.BASE_DIR, 'static', 'js', 'sw.js')
    real_sw   = os.path.realpath(sw_path)
    real_base = os.path.realpath(str(settings.BASE_DIR))

    if not real_sw.startswith(real_base + os.sep):
        return HttpResponse('// forbidden', content_type='application/javascript', status=403)
    
    try:
        with open(real_sw, 'r') as f:
            content = f.read()
        response = HttpResponse(content, content_type='application/javascript')
        response['Service-Worker-Allowed'] = '/'
        response['Cache-Control']          = 'no-cache, no-store, must-revalidate'
        return response
    except FileNotFoundError:
        return HttpResponse('// sw.js not found', content_type='application/javascript', status=404)