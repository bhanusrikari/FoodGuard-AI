from django.core.exceptions import ValidationError as DjangoValidationError
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from food_reports.models import FoodReport
from food_reports.permissions import IsCustomerOwner, ReportListPermission
from food_reports.serializers import (
    FoodReportCreateSerializer,
    FoodReportReadSerializer,
    FoodReportUpdateSerializer,
)
from food_reports.services import FoodReportSubmissionService, SubmissionValidationError
from users.models import User

_REVIEWER_ADMIN = {User.Role.REVIEWER, User.Role.ADMIN}


@extend_schema_view(
    get=extend_schema(responses={200: FoodReportReadSerializer(many=True)}),
    post=extend_schema(
        request=FoodReportCreateSerializer,
        responses={201: FoodReportReadSerializer, 400: dict},
        description="multipart/form-data — `image` is an optional file field.",
    ),
)
class ReportListCreateView(APIView):
    """
    GET  /api/v1/reports/  — list reports
    POST /api/v1/reports/  — create a new DRAFT report (CUSTOMER only)
    """

    permission_classes = [ReportListPermission]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request: Request) -> Response:
        role = request.user.role
        if role in _REVIEWER_ADMIN:
            # Reviewers / admins see all reports
            qs = FoodReport.objects.select_related(
                "customer", "restaurant"
            ).all()
        else:
            # Customers see only their own
            qs = FoodReport.objects.select_related(
                "customer", "restaurant"
            ).filter(customer=request.user)

        serializer = FoodReportReadSerializer(
            qs, many=True, context={"request": request}
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request: Request) -> Response:
        serializer = FoodReportCreateSerializer(
            data=request.data, context={"request": request}
        )
        if not serializer.is_valid():
            return Response(
                serializer.errors, status=status.HTTP_400_BAD_REQUEST
            )
        report = serializer.save()
        return Response(
            FoodReportReadSerializer(report, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


@extend_schema_view(
    get=extend_schema(responses={200: FoodReportReadSerializer, 404: dict}),
    patch=extend_schema(
        request=FoodReportUpdateSerializer,
        responses={200: FoodReportReadSerializer, 400: dict, 403: dict, 404: dict},
        description="multipart/form-data — DRAFT reports owned by the requesting customer only.",
    ),
    delete=extend_schema(responses={204: None, 403: dict, 404: dict}),
)
class ReportDetailView(APIView):
    """
    GET    /api/v1/reports/<id>/
    PATCH  /api/v1/reports/<id>/
    DELETE /api/v1/reports/<id>/
    """

    permission_classes = [IsCustomerOwner]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def _get_object(self, pk: int) -> FoodReport | None:
        try:
            return FoodReport.objects.select_related(
                "customer", "restaurant"
            ).get(pk=pk)
        except FoodReport.DoesNotExist:
            return None

    def get(self, request: Request, pk: int) -> Response:
        report = self._get_object(pk)
        if report is None:
            return Response(
                {"detail": "Report not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        self.check_object_permissions(request, report)
        serializer = FoodReportReadSerializer(
            report, context={"request": request}
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request: Request, pk: int) -> Response:
        report = self._get_object(pk)
        if report is None:
            return Response(
                {"detail": "Report not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        self.check_object_permissions(request, report)

        # Only the owner (CUSTOMER) may update; reviewers/admins are read-only
        if request.user.role in _REVIEWER_ADMIN:
            return Response(
                {"detail": "Reviewers and admins have read-only access to reports."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Customer may only edit DRAFT reports
        if not report.is_editable:
            return Response(
                {
                    "detail": (
                        "Only DRAFT reports can be edited. "
                        f"This report is '{report.get_status_display()}'."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # Guard: customer cannot change customer / status / priority fields
        forbidden_fields = {"customer", "status", "priority"}
        attempted = set(request.data.keys()) & forbidden_fields
        if attempted:
            return Response(
                {
                    "detail": (
                        "You are not permitted to change: "
                        + ", ".join(sorted(attempted))
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = FoodReportUpdateSerializer(
            report, data=request.data, partial=True,
            context={"request": request},
        )
        if not serializer.is_valid():
            return Response(
                serializer.errors, status=status.HTTP_400_BAD_REQUEST
            )
        updated = serializer.save()
        return Response(
            FoodReportReadSerializer(updated, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    def delete(self, request: Request, pk: int) -> Response:
        report = self._get_object(pk)
        if report is None:
            return Response(
                {"detail": "Report not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        self.check_object_permissions(request, report)

        if request.user.role in _REVIEWER_ADMIN:
            return Response(
                {"detail": "Reviewers and admins have read-only access to reports."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if not report.is_editable:
            return Response(
                {
                    "detail": (
                        "Only DRAFT reports can be deleted. "
                        f"This report is '{report.get_status_display()}'."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        report.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema_view(
    post=extend_schema(request=None, responses={200: FoodReportReadSerializer, 400: dict, 403: dict, 404: dict}),
)
class ReportSubmitView(APIView):
    """
    POST /api/v1/reports/<id>/submit/

    Transitions a DRAFT report to SUBMITTED.
    Only the owning CUSTOMER may submit.
    Requires: title, description, restaurant, image all present.
    """

    permission_classes = [IsCustomerOwner]

    def post(self, request: Request, pk: int) -> Response:
        try:
            report = FoodReport.objects.select_related(
                "customer", "restaurant"
            ).get(pk=pk)
        except FoodReport.DoesNotExist:
            return Response(
                {"detail": "Report not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        self.check_object_permissions(request, report)

        # Reviewers / admins cannot submit on behalf of a customer
        if request.user.role in _REVIEWER_ADMIN:
            return Response(
                {"detail": "Only the report owner may submit a report."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            service = FoodReportSubmissionService(report, request.user)
            updated = service.submit()
        except (SubmissionValidationError, DjangoValidationError) as exc:
            # Normalise to list of messages
            messages = (
                exc.messages
                if hasattr(exc, "messages")
                else [str(exc)]
            )
            return Response(
                {"detail": messages},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            FoodReportReadSerializer(updated, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )
