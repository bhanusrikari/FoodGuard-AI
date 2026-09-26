from django.contrib import admin

from notifications.models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("id", "recipient", "event_type", "is_read", "created_at")
    list_filter = ("event_type", "is_read", "created_at")
    search_fields = ("recipient__email", "message")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)
