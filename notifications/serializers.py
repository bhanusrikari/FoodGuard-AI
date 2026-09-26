from rest_framework import serializers

from notifications.models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            "id",
            "event_type",
            "message",
            "related_report",
            "related_complaint",
            "is_read",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "event_type",
            "message",
            "related_report",
            "related_complaint",
            "created_at",
        ]
