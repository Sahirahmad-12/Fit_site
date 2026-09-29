# shop/device_views.py
"""
Endpoints called by the React Native app to register/unregister FCM tokens.

Add to shop/urls.py:
    path('devices/register/',   views_device.register_device,   name='register_device'),
    path('devices/unregister/', views_device.unregister_device, name='unregister_device'),
"""

import json
import logging
from django.conf import settings

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import StaffDevice

logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def register_device(request):
    # Verify shared secret sent by the app
    if request.headers.get('X-Api-Key') != settings.API_KEY:
        return JsonResponse({'ok': False, 'error': 'Unauthorized.'}, status=403)

    try:
        body        = json.loads(request.body)
        fcm_token   = body.get('token', '').strip()
        device_name = body.get('device_name', '').strip()[:120]
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({'ok': False, 'error': 'Invalid JSON.'}, status=400)

    if not fcm_token:
        return JsonResponse({'ok': False, 'error': 'token is required.'}, status=400)

    # No user association needed — any device that knows the key is staff-owned
    obj, created = StaffDevice.objects.update_or_create(
        fcm_token=fcm_token,
        defaults={'device_name': device_name, 'active': True},
    )
    return JsonResponse({'ok': True, 'created': created})

# shop/device_views.py

@csrf_exempt
@require_POST
def unregister_device(request):
    if request.headers.get('X-Api-Key') != settings.API_KEY:
        return JsonResponse({'ok': False, 'error': 'Unauthorized.'}, status=403)

    try:
        body      = json.loads(request.body)
        fcm_token = body.get('token', '').strip()
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({'ok': False, 'error': 'Invalid JSON.'}, status=400)

    if not fcm_token:
        return JsonResponse({'ok': False, 'error': 'token is required.'}, status=400)

    updated = StaffDevice.objects.filter(fcm_token=fcm_token).update(active=False)
    return JsonResponse({'ok': True, 'deactivated': updated > 0})