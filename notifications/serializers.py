from rest_framework import serializers

from notifications.models import Notification
from translation.strings import resolve_language, translate_system_string

# event_type -> (catalog key, related-object attribute to supply as `title`)
# Deliberately covers only the event types whose exact display text can be
# reconstructed from data still available on the notification's related
# object today (its current title). COMPLAINT_STATUS_CHANGED needs the
# status *at the time the notification was raised*, which isn't stored
# separately from the pre-rendered message — rather than guess or fabricate
# that, notifications for it (and the other event types not listed here)
# honestly fall back to the original English `message`. See
# docs/... multilingual status notes for this known limitation.
_TRANSLATABLE_EVENTS: dict[str, tuple[str, str]] = {
    Notification.EventType.REPORT_SUBMITTED: ("notification.report_submitted", "related_report"),
    Notification.EventType.AI_ANALYSIS_COMPLETED: ("notification.ai_analysis_completed", "related_report"),
    Notification.EventType.COMPLAINT_SUBMITTED: ("notification.complaint_submitted", "related_complaint"),
}


class NotificationSerializer(serializers.ModelSerializer):
    """
    `message` is the original, canonical English text exactly as stored at
    creation time — never overwritten. `localized_message` is additive: a
    fresh rendering from the static system-string catalog
    (translation/strings.py) for the event types listed in
    `_TRANSLATABLE_EVENTS` above, in the requesting user's
    preferred_language when supported. Event types not listed there, or
    missing their related object, fall back to the original English
    `message` — an honest fallback, never a fabricated translation.
    `event_type` itself is never translated — it's the internal,
    machine-readable identifier.
    """

    localized_message = serializers.SerializerMethodField()
    message_language = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            "id",
            "event_type",
            "message",
            "localized_message",
            "message_language",
            "related_report",
            "related_complaint",
            "is_read",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "event_type",
            "message",
            "localized_message",
            "message_language",
            "related_report",
            "related_complaint",
            "created_at",
        ]

    def _requested_language(self) -> str:
        request = self.context.get("request")
        user = getattr(request, "user", None)
        preferred = getattr(user, "preferred_language", None)
        return resolve_language(preferred)

    def get_localized_message(self, notification: Notification) -> str:
        entry = _TRANSLATABLE_EVENTS.get(notification.event_type)
        if entry is None:
            return notification.message

        key, related_attr = entry
        related = getattr(notification, related_attr, None)
        title = getattr(related, "title", None)
        if not title:
            # related object was deleted (SET_NULL) or has no title — the
            # original message is the only text we can honestly show.
            return notification.message

        return translate_system_string(key, self._requested_language(), title=title)

    def get_message_language(self, notification: Notification) -> str:
        entry = _TRANSLATABLE_EVENTS.get(notification.event_type)
        if entry is None:
            return "en"  # original `message` is always English
        related = getattr(notification, entry[1], None)
        if not getattr(related, "title", None):
            return "en"
        return self._requested_language()
