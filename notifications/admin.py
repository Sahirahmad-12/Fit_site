from django.contrib import admin
from .models import WebPushSubscription


@admin.register(WebPushSubscription)
class WebPushSubscriptionAdmin(admin.ModelAdmin):
    list_display  = ('user', 'created_at', 'short_endpoint')
    list_filter   = ('user',)
    readonly_fields = ('user', 'endpoint', 'p256dh', 'auth', 'created_at')

    def short_endpoint(self, obj):
        return obj.endpoint[:60] + '...'
    short_endpoint.short_description = 'Endpoint'