from django.db import models
from django.contrib.auth.models import User


class WebPushSubscription(models.Model):
    """
    Stores a browser/PWA push subscription for web admins.
    One user can have multiple browser subscriptions (phone PWA + laptop etc.)
    """
    user      = models.ForeignKey(User, on_delete=models.CASCADE, related_name='web_push_subs')
    endpoint  = models.TextField(unique=True)
    p256dh    = models.TextField()   # public key
    auth      = models.TextField()   # auth secret
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} — {self.endpoint[:50]}"

    class Meta:
        verbose_name = 'Web Push Subscription'
        verbose_name_plural = 'Web Push Subscriptions'