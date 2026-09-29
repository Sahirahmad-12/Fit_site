# shop/notifications.py
"""
Push-notification helpers for EnterGYM.

Usage:
    from shop.notifications import notify_staff_new_order
    notify_staff_new_order(order)   # call this from place_order view
"""

import logging
import os
import firebase_admin
from firebase_admin import credentials, messaging
from django.conf import settings
from .models import StaffDevice
from notifications.utils import send_web_push_to_all_staff

logger = logging.getLogger(__name__)

# ── Init Firebase app once ────────────────────────────────────────────────────
def _get_firebase_app():
    """Return the default Firebase app, initialising it on first call."""
    if not firebase_admin._apps:
        cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
        firebase_admin.initialize_app(cred)
    return firebase_admin.get_app()


# ── Core send helper ──────────────────────────────────────────────────────────
def send_push_to_tokens(tokens: list[str], title: str, body: str, data: dict = None, channel_id: str = 'entergym_orders') -> int:
    """
    Send a multicast push notification to a list of FCM tokens.
    Returns the number of successes.
    Silently removes tokens that FCM says are invalid/expired.
    """
    if not tokens:
        return 0

    _get_firebase_app()

    message = messaging.MulticastMessage(
        tokens=tokens,
        notification=messaging.Notification(title=title, body=body),
        data={str(k): str(v) for k, v in (data or {}).items()},
        android=messaging.AndroidConfig(
            priority='high',
            notification=messaging.AndroidNotification(
                icon='ic_notification',   # drawable in your Android app
                color='#ff4d00',
                channel_id=channel_id,
            ),
        ),
        apns=messaging.APNSConfig(
            payload=messaging.APNSPayload(
                aps=messaging.Aps(sound='default', badge=1)
            )
        ),
    )

    try:
        response = messaging.send_each_for_multicast(message)
        logger.info(
            "FCM multicast: %d success, %d failure (out of %d tokens)",
            response.success_count, response.failure_count, len(tokens),
        )
        _prune_bad_tokens(tokens, response)
        return response.success_count
    except Exception as exc:
        logger.exception("FCM send failed: %s", exc)
        return 0


def _prune_bad_tokens(tokens: list[str], response) -> None:
    """Remove FCM tokens that returned UNREGISTERED or INVALID_ARGUMENT errors."""
    from AuthFit.models import UserDevice  # local import avoids circular import

    bad = []
    for idx, result in enumerate(response.responses):
        if not result.success and result.exception:
            code = getattr(result.exception, 'code', '')
            if code in ('UNREGISTERED', 'INVALID_ARGUMENT'):
                bad.append(tokens[idx])

    if bad:
        removed_staff = StaffDevice.objects.filter(fcm_token__in=bad).update(active=False)
        removed_user  = UserDevice.objects.filter(fcm_token__in=bad).update(active=False)
        if removed_staff or removed_user:
            logger.info("Deactivated stale FCM tokens — staff:%d user:%d", removed_staff, removed_user)

# ── Domain-specific notification ─────────────────────────────────────────────
def notify_staff_new_order(order) -> None:
    """
    Push a 'new order' notification to every active staff device.
    Call this right after Order.objects.create(...).
    """
    flavor_part = f" ({order.flavor.name})" if order.flavor else ""
    customer    = (
        order.user.get_full_name().strip()
        or order.user.username
    )
    send_web_push_to_all_staff(
        title=f"🛒 New Order #{order.id}",
        body=f"{customer} ordered {order.product.name}{flavor_part} × {order.quantity} — ₹{int(order.total_price)}",
        url="/shop/orders/admin/"
    )

    tokens = list(
        StaffDevice.objects.filter(active=True)
        .values_list('fcm_token', flat=True)
    )
    if not tokens:
        logger.debug("notify_staff_new_order: no staff devices registered, skipping.")
        return
    

    send_push_to_tokens(
        tokens=tokens,
        title=f"🛒 New Order #{order.id}",
        body=(
            f"{customer} ordered {order.product.name}{flavor_part} "
            f"× {order.quantity} — ₹{int(order.total_price)}"
        ),
        data={
            "order_id":   str(order.id),
            "screen":     "AdminOrders",   # deep-link hint for the app
            "type":       "new_order",
        },
    )


def notify_staff_new_enrollment(enrollment) -> None:
    """
    Push a 'new member joined' notification to every active staff device.
    Call this right after a new Enrollment is saved.
    """
    gender_emoji = "💪" if enrollment.gender == "M" else "🌟"
    plan_name = enrollment.selectPlan.plan if enrollment.selectPlan else "a plan"
    send_web_push_to_all_staff(
        title=f"{gender_emoji} New Member Joined!",
        body=f"{enrollment.fullname} enrolled with {plan_name} plan 🏋️",
        url="/admin-tools/payments/"
    )
    tokens = list(
        StaffDevice.objects.filter(active=True)
        .values_list('fcm_token', flat=True)
    )

    if not tokens:
        logger.debug("notify_staff_new_enrollment: no staff devices registered, skipping.")
        return
    

    send_push_to_tokens(
        tokens=tokens,
        title=f"{gender_emoji} New Member Joined!",
        body=(
            f"{enrollment.fullname} just enrolled at EnterGYM "
            f"with the {plan_name} plan. Welcome them to the family! 🏋️"
        ),
        data={
            "enrollment_id": str(enrollment.id),
            "unique_id":     enrollment.unique_id,
            "screen":        "MemberDetail",
            "type":          "new_enrollment",
        },
        channel_id="entergym_orders",   # reuse existing high-priority channel
    )