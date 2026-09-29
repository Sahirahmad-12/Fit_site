from django.contrib import admin
from .models import Product, Order, ProductFlavor, StaffDevice

admin.site.register(Product)
admin.site.register(ProductFlavor)
admin.site.register(Order)

@admin.register(StaffDevice)
class StaffDeviceAdmin(admin.ModelAdmin):
    list_display = (
        'device_name',
        'active',
        'last_seen',
    )

    list_filter = (
        'active',
    )

    search_fields = (
        'device_name',
        'fcm_token',
    )

    readonly_fields = (
        'fcm_token',
        'last_seen',
    )

    actions = ['deactivate_selected']

    @admin.action(description='Deactivate selected devices')
    def deactivate_selected(self, request, queryset):
        queryset.update(active=False)