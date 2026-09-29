# AuthFit/device_views.py
"""
Endpoints called by the React Native app to register/unregister a member's
FCM token for plan-expiry push notifications.

"""

import json
import logging

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .models import UserDevice

logger = logging.getLogger(__name__)


@login_required
@require_POST
def register_user_device(request):
    try:
        body        = json.loads(request.body)
        fcm_token   = body.get('token', '').strip()
        device_name = body.get('device_name', '').strip()[:120]
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({'ok': False, 'error': 'Invalid JSON.'}, status=400)

    if not fcm_token:
        return JsonResponse({'ok': False, 'error': 'token is required.'}, status=400)

    obj, created = UserDevice.objects.update_or_create(
        fcm_token=fcm_token,
        defaults={'user': request.user, 'device_name': device_name, 'active': True},
    )
    return JsonResponse({'ok': True, 'created': created})


@login_required
@require_POST
def unregister_user_device(request):
    try:
        body      = json.loads(request.body)
        fcm_token = body.get('token', '').strip()
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({'ok': False, 'error': 'Invalid JSON.'}, status=400)

    if not fcm_token:
        return JsonResponse({'ok': False, 'error': 'token is required.'}, status=400)

    updated = UserDevice.objects.filter(fcm_token=fcm_token, user=request.user).update(active=False)
    return JsonResponse({'ok': True, 'deactivated': updated > 0})