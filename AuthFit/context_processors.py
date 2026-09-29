# AuthFit/context_processors.py

import hmac
import hashlib
import json
import logging

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)


def _user_hash(uid: int) -> str:
    return hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        str(uid).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()[:16]


def gym_config(request):
    """
    Injects window.GYM_CONFIG into templates.

    Exposes only:
    - isAuthenticated
    - isEnrolled
    - alreadyMarked
    - userHash

    Never exposes:
    - user.id
    - gym coordinates
    - radius
    """

    is_enrolled = False
    already_marked = False
    user_hash = ""

    if request.user.is_authenticated:

        uid = request.user.id
        today = timezone.localdate()

        # --------------------------------------------------
        # User Hash
        # --------------------------------------------------
        try:
            user_hash = _user_hash(uid)

        except Exception:
            logger.exception(
                "Failed generating user hash for user %s",
                uid
            )

        # --------------------------------------------------
        # Enrollment Check
        # --------------------------------------------------
        try:
            enroll_key = f"enrollment_status_{uid}"

            enroll_data = cache.get(enroll_key)

            if enroll_data is None:

                from AuthFit.models import Enrollment

                enrollment = (
                    Enrollment.objects
                    .filter(user=request.user)
                    .first()
                )

                if enrollment:

                    enroll_data = {
                        "exists": True,
                        "expired": bool(enrollment.is_expired),
                    }

                else:

                    enroll_data = {
                        "exists": False,
                        "expired": False,
                    }

                cache.set(
                    enroll_key,
                    enroll_data,
                    timeout=300
                )

            is_enrolled = (
                bool(enroll_data.get("exists"))
                and
                not bool(enroll_data.get("expired"))
            )

            logger.debug(
                "User=%s enrolled=%s cache=%s",
                uid,
                is_enrolled,
                enroll_data
            )

        except Exception:
            logger.exception(
                "Enrollment check failed for user %s",
                uid
            )

        # --------------------------------------------------
        # Attendance Check
        # --------------------------------------------------
        if is_enrolled:

            try:
                att_key = f"att_marked_{uid}_{today}"

                already_marked = cache.get(att_key)

                if already_marked is None:

                    from AuthFit.models import Attendence

                    already_marked = Attendence.objects.filter(
                        user=request.user,
                        date=today,
                    ).exists()

                    cache.set(
                        att_key,
                        already_marked,
                        timeout=86400 if already_marked else 60
                    )

            except Exception:
                logger.exception(
                    "Attendance check failed for user %s",
                    uid
                )

    config = {
        "isAuthenticated": request.user.is_authenticated,
        "isEnrolled": bool(is_enrolled),
        "alreadyMarked": bool(already_marked),
        "userHash": user_hash,
    }

    return {
        "GYM_CONFIG_JSON": json.dumps(config),
        "is_enrolled": bool(is_enrolled),
        "already_marked": bool(already_marked),
    }