import json
import logging
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from .models import WebPushSubscription

logger = logging.getLogger(__name__)


@login_required
@csrf_exempt
@require_POST
def save_subscription(request):
    """Browser calls this after user allows notifications."""
    try:
        data = json.loads(request.body)

        endpoint = data.get("endpoint")
        p256dh   = data.get("keys", {}).get("p256dh")
        auth     = data.get("keys", {}).get("auth")

        if not all([endpoint, p256dh, auth]):
            return JsonResponse({"error": "Missing fields"}, status=400)

        WebPushSubscription.objects.update_or_create(
            endpoint=endpoint,
            defaults={
                "user":   request.user,
                "p256dh": p256dh,
                "auth":   auth,
            }
        )
        logger.info("Web push subscription saved for %s", request.user.username)
        return JsonResponse({"status": "ok"})

    except Exception as e:
        logger.exception("Error saving web push subscription")
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@csrf_exempt
@require_POST
def delete_subscription(request):
    """Browser calls this when user blocks notifications."""
    try:
        data     = json.loads(request.body)
        endpoint = data.get("endpoint")

        if endpoint:
            WebPushSubscription.objects.filter(endpoint=endpoint).delete()

        return JsonResponse({"status": "deleted"})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
    

from django.contrib.admin.views.decorators import staff_member_required

@staff_member_required  
def test_push(request):
    from notifications.utils import send_web_push
    send_web_push(
        user=request.user,
        title="🔔 Test Notification",
        body="Web push is working on EnterGYM!",
        url="/"
    )
    from django.http import HttpResponse
    return HttpResponse("Push sent! Check your browser/phone.")