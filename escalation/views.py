from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from escalation.models import Escalation
from escalation.permissions import IsReviewerOrAdmin
from escalation.serializers import (
    EscalationCreateSerializer,
    EscalationReadSerializer,
    EscalationUpdateSerializer,
)
from escalation.services import EscalationError

# Fields that are immutable after creation
_IMMUTABLE_FIELDS = {
    "complaint", "created_by", "original_language",
    "created_at", "updated_at",
}


@extend_schema_view(
    get=extend_schema(responses={200: EscalationReadSerializer(many=True)}),
    post=extend_schema(request=EscalationCreateSerializer, responses={201: EscalationReadSerializer, 400: dict}),
)
class EscalationListCreateView(APIView):
    """
    GET  /api/v1/escalations/  — list escalations (REVIEWER/ADMIN only)
    POST /api/v1/escalations/  — create escalation (REVIEWER/ADMIN only)
    """

    permission_classes = [IsReviewerOrAdmin]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get(self, request: Request) -> Response:
        qs = Escalation.objects.select_related(
            "complaint", "created_by", "assigned_to"
        ).all()
        serializer = EscalationReadSerializer(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request: Request) -> Response:
        serializer = EscalationCreateSerializer(
            data=request.data, context={"request": request}
        )
        if not serializer.is_valid():
            return Response(
                serializer.errors, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            escalation = serializer.save()
        except EscalationError as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            EscalationReadSerializer(escalation).data,
            status=status.HTTP_201_CREATED,
        )


@extend_schema_view(
    get=extend_schema(responses={200: EscalationReadSerializer, 404: dict}),
    patch=extend_schema(request=EscalationUpdateSerializer, responses={200: EscalationReadSerializer, 400: dict, 404: dict}),
)
class EscalationDetailView(APIView):
    """
    GET   /api/v1/escalations/<id>/
    PATCH /api/v1/escalations/<id>/
    """

    permission_classes = [IsReviewerOrAdmin]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def _get_object(self, pk: int):
        try:
            return Escalation.objects.select_related(
                "complaint", "created_by", "assigned_to"
            ).get(pk=pk)
        except Escalation.DoesNotExist:
            return None

    def get(self, request: Request, pk: int) -> Response:
        escalation = self._get_object(pk)
        if escalation is None:
            return Response(
                {"detail": "Escalation not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        self.check_object_permissions(request, escalation)
        return Response(
            EscalationReadSerializer(escalation).data,
            status=status.HTTP_200_OK,
        )

    def patch(self, request: Request, pk: int) -> Response:
        escalation = self._get_object(pk)
        if escalation is None:
            return Response(
                {"detail": "Escalation not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        self.check_object_permissions(request, escalation)

        # Block attempts to change immutable fields
        immutable_attempted = set(request.data.keys()) & _IMMUTABLE_FIELDS
        if immutable_attempted:
            return Response(
                {
                    "detail": (
                        "The following fields cannot be changed after creation: "
                        + ", ".join(sorted(immutable_attempted))
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = EscalationUpdateSerializer(
            escalation, data=request.data, partial=True
        )
        if not serializer.is_valid():
            return Response(
                serializer.errors, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            updated = serializer.save()
        except EscalationError as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            EscalationReadSerializer(updated).data,
            status=status.HTTP_200_OK,
        )
