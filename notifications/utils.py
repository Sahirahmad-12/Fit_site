import json
import logging
from pywebpush import webpush, WebPushException
from django.conf import settings
from django.contrib.auth.models import User
from .models import WebPushSubscription

logger = logging.getLogger(__name__)


def send_web_push(user, title, body, url="/"):
    """Send web push notification to all browser/PWA subscriptions of one user."""
    subscriptions = WebPushSubscription.objects.filter(user=user)

    for sub in subscriptions:
        try:
            webpush(
                subscription_info={
                    "endpoint": sub.endpoint,
                    "keys": {
                        "p256dh": sub.p256dh,
                        "auth":   sub.auth,
                    }
                },
                data=json.dumps({
                    "title": title,
                    "body":  body,
                    "url":   url,
                }),
                vapid_private_key=settings.VAPID_PRIVATE_KEY,
                vapid_claims=settings.VAPID_CLAIMS,
            )
            logger.info("Web push sent to %s", user.username)
        except WebPushException as e:
            logger.warning(
                "Web push failed for %s: %s | response=%s",
                user.username, e, getattr(e.response, "text", None)
            )
            sub.delete()
        except Exception as e:
            logger.exception("Unexpected web push error for %s: %s", user.username, e)


def send_web_push_to_all_staff(title, body, url="/"):
    """Send web push to every staff user who has a browser subscription."""
    staff_users = User.objects.filter(is_staff=True)
    for user in staff_users:
        send_web_push(user, title, body, url)