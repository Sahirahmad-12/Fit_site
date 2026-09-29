from django.core.cache import cache

MAX_ATTEMPTS = 3
LOCKOUT_SECONDS = 60


def check_login_attempt(ip: str, phone: str) -> bool:
    """Returns False if the phone is currently locked out."""
    key = f"login:{phone}"
    try:
        attempts = cache.get(key, 0)
        return attempts < MAX_ATTEMPTS
    except Exception:
        return True  # Fail open on cache error


def record_failed_attempt(ip: str, phone: str) -> None:
    """Increments the failure counter. Call only after a failed authenticate()."""
    key = f"login:{phone}"
    try:
        if not cache.get(key):
            cache.set(key, 1, timeout=LOCKOUT_SECONDS)
        else:
            cache.incr(key)
    except Exception:
        pass


def reset_attempt(ip: str, phone: str) -> None:
    """Clears the counter after a successful login."""
    key = f"login:{phone}"
    try:
        cache.delete(key)
    except Exception:
        pass
