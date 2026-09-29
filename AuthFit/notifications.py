# AuthFit/notifications.py
"""
Push-notification helpers for plan-expiry reminders.

Usage:
    from AuthFit.notifications import send_expiry_reminders
    send_expiry_reminders()
"""

import logging
from datetime import timedelta
from django.utils import timezone
from Shop.notifications import send_push_to_tokens
from .models import Enrollment, UserDevice
from notifications.utils import send_web_push_to_all_staff

logger = logging.getLogger(__name__)

REMINDER_WINDOW_DAYS = 3   # start notifying 3 days before expiry
OVERDUE_CUTOFF_DAYS  = 2   # stop notifying 7 days after expiry


def send_expiry_reminders() -> int:
    today = timezone.localdate()

    enrollments = (
        Enrollment.objects
        .filter(
            DueDate__isnull=False,
            DueDate__lte=today + timedelta(days=REMINDER_WINDOW_DAYS),
            DueDate__gte=today - timedelta(days=OVERDUE_CUTOFF_DAYS),
        )
        .exclude(last_expiry_notif_sent=today)
        .select_related('user', 'selectPlan')
    )

    sent_count = 0

    for enr in enrollments:
        tokens = list(
            UserDevice.objects.filter(user=enr.user, active=True)
            .values_list('fcm_token', flat=True)
        )

        title, body = _build_message(enr, today)

        if tokens:
            send_push_to_tokens(
                tokens=tokens,
                title=title,
                body=body,
                data={
                    "enrollment_id": str(enr.id),
                    "screen":        "Profile",
                    "type":          "plan_expiry",
                },
                channel_id='entergym_expiry',
            )
            sent_count += 1
            send_web_push_to_all_staff(
                title=title,
                body=body,
                url="/admin-tools/payments/",
            )
        else:
            logger.debug(
                "send_expiry_reminders: no devices for user_id=%s, skipping push",
                enr.user_id,
            )

        enr.last_expiry_notif_sent = today
        enr.save(update_fields=['last_expiry_notif_sent'])

    logger.info("Expiry reminders processed for %d enrollments", sent_count)
    return sent_count


def _build_message(enr, today):
    days_left = (enr.DueDate - today).days
    plan_name = enr.selectPlan.plan if enr.selectPlan else "your plan"

    if days_left < 0:
        title = "Membership Expired"
        body  = f"Your {plan_name} expired {abs(days_left)} day(s) ago. Renew now to continue your access."
    elif days_left == 0:
        title = "Membership Expires Today"
        body  = f"Your {plan_name} expires today. Renew now to avoid interruption."
    elif days_left == 1:
        title = "Membership Expires Tomorrow"
        body  = f"Your {plan_name} expires tomorrow. Renew now to keep your access uninterrupted."
    else:
        title = "Membership Expiring Soon"
        body  = f"Your {plan_name} expires in {days_left} days. Renew now to avoid losing access."

    return title, body