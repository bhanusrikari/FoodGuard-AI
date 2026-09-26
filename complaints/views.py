from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from users.models import User
from complaints.models import Complaint
from complaints.permissions import ComplaintListCreatePermission, IsComplaintOwner
from complaints.serializers import (
    ComplaintCreateSerializer,
    ComplaintReadSerializer,
    ComplaintUpdateSerializer,
)
from complaints.services import ComplaintError

_REVIEWER_ADMIN = {User.Role.REVIEWER, User.Role.ADMIN}

# Fields that only REVIEWER / ADMIN may set
_PROTECTED_FIELDS = {
    "customer", "restaurant", "food_report", "original_language",
    "status", "priority", "resolution_notes",
    "submitted_at", "updated_at", "resolved_at",
}


@extend_schema_view(
    get=extend_schema(responses={200: ComplaintReadSerializer(many=True)}),
    post=extend_schema(request=ComplaintCreateSerializer, responses={201: ComplaintReadSerializer, 400: dict}),
)
class ComplaintListCreateView(APIView):
    """
    GET  /api/v1/complaints/  — list complaints (filtered by role)
    POST /api/v1/complaints/  — create complaint (CUSTOMER only)
    """

    permission_classes = [ComplaintListCreatePermission]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get(self, request: Request) -> Response:
        role = request.user.role
        if role in _REVIEWER_ADMIN:
            qs = Complaint.objects.select_related(
                "customer", "restaurant", "food_report"
            ).all()
        else:
            # CUSTOMER sees only their own; RESTAURANT_USER sees nothing here
            qs = Complaint.objects.select_related(
                "customer", "restaurant", "food_report"
            ).filter(customer=request.user)

        serializer = ComplaintReadSerializer(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request: Request) -> Response:
        serializer = ComplaintCreateSerializer(
            data=request.data, context={"request": request}
        )
        if not serializer.is_valid():
            return Response(
                serializer.errors, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            complaint = serializer.save()
        except ComplaintError as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            ComplaintReadSerializer(complaint).data,
            status=status.HTTP_201_CREATED,
        )


@extend_schema_view(
    get=extend_schema(responses={200: ComplaintReadSerializer, 404: dict}),
    patch=extend_schema(
        request=ComplaintUpdateSerializer,
        responses={200: ComplaintReadSerializer, 400: dict, 403: dict, 404: dict},
        description="REVIEWER/ADMIN only — status, priority, resolution_notes.",
    ),
)
class ComplaintDetailView(APIView):
    """
    GET   /api/v1/complaints/<id>/
    PATCH /api/v1/complaints/<id>/
    """

    permission_classes = [IsComplaintOwner]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def _get_object(self, pk: int):
        try:
            return Complaint.objects.select_related(
                "customer", "restaurant", "food_report"
            ).get(pk=pk)
        except Complaint.DoesNotExist:
            return None

    def get(self, request: Request, pk: int) -> Response:
        complaint = self._get_object(pk)
        if complaint is None:
            return Response(
                {"detail": "Complaint not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        self.check_object_permissions(request, complaint)
        return Response(
            ComplaintReadSerializer(complaint).data, status=status.HTTP_200_OK
        )

    def patch(self, request: Request, pk: int) -> Response:
        complaint = self._get_object(pk)
        if complaint is None:
            return Response(
                {"detail": "Complaint not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        self.check_object_permissions(request, complaint)

        # Customers have read-only access after creation
        if request.user.role == User.Role.CUSTOMER:
            return Response(
                {
                    "detail": (
                        "Customers cannot update complaint fields after creation. "
                        "Workflow updates are performed by Reviewers and Admins."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # Reviewer / Admin — validate they are not attempting to change
        # protected-read fields (food_report, customer, restaurant, etc.)
        immutable_attempted = set(request.data.keys()) - {
            "status", "priority", "resolution_notes"
        }
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

        serializer = ComplaintUpdateSerializer(
            complaint, data=request.data, partial=True
        )
        if not serializer.is_valid():
            return Response(
                serializer.errors, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            updated = serializer.save()
        except ComplaintError as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            ComplaintReadSerializer(updated).data, status=status.HTTP_200_OK
        )
