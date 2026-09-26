from rest_framework.permissions import BasePermission


class IsNotificationOwner(BasePermission):
    """Own notifications only — no role gets access to another user's notifications."""

    message = "You do not have permission to access this notification."

    def has_permission(self, request, view) -> bool:
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj) -> bool:
        return bool(request.user and request.user.is_authenticated and obj.recipient_id == request.user.pk)
