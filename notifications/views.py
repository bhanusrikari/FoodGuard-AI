from drf_spectacular.utils import extend_schema, extend_schema_view, inline_serializer
from rest_framework import serializers, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from notifications.models import Notification
from notifications.permissions import IsNotificationOwner
from notifications.serializers import NotificationSerializer


@extend_schema_view(
    get=extend_schema(responses={200: NotificationSerializer(many=True)}),
)
class NotificationListView(APIView):
    """GET /api/v1/notifications/ — the requesting user's own notifications, newest first."""

    permission_classes = [IsNotificationOwner]

    def get(self, request: Request) -> Response:
        qs = Notification.objects.filter(recipient=request.user).select_related(
            "related_report", "related_complaint"
        )
        return Response(
            NotificationSerializer(qs, many=True, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )


@extend_schema_view(
    patch=extend_schema(
        request=inline_serializer(name="NotificationPatch", fields={"is_read": serializers.BooleanField()}),
        responses={200: NotificationSerializer, 400: dict, 403: dict, 404: dict},
    ),
)
class NotificationDetailView(APIView):
    """PATCH /api/v1/notifications/<id>/ — mark as read/unread. Owner only."""

    permission_classes = [IsNotificationOwner]

    def _get_object(self, pk: int):
        try:
            return Notification.objects.get(pk=pk)
        except Notification.DoesNotExist:
            return None

    def patch(self, request: Request, pk: int) -> Response:
        notification = self._get_object(pk)
        if notification is None:
            return Response({"detail": "Notification not found."}, status=status.HTTP_404_NOT_FOUND)
        self.check_object_permissions(request, notification)

        if set(request.data.keys()) - {"is_read"}:
            return Response(
                {"detail": "Only 'is_read' may be updated."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        is_read = request.data.get("is_read")
        if not isinstance(is_read, bool):
            return Response(
                {"detail": "'is_read' must be a boolean."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        notification.is_read = is_read
        notification.save(update_fields=["is_read"])
        return Response(
            NotificationSerializer(notification, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )
