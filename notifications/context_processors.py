from django.conf import settings


def vapid_key(request):
    """Makes VAPID_PUBLIC_KEY available in every Django template."""
    return {
        "VAPID_PUBLIC_KEY": getattr(settings, "VAPID_PUBLIC_KEY", "")
    }