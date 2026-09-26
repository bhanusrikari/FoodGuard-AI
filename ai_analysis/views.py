from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from food_reports.models import FoodReport
from ai_analysis.models import AIAnalysis
from ai_analysis.permissions import CanAccessAnalysis
from ai_analysis.serializers import AIAnalysisSerializer
from ai_analysis.services import AIAnalysisService, AnalysisError


def _get_report_or_404(report_id: int):
    """Return FoodReport or None."""
    try:
        return FoodReport.objects.select_related("customer").get(pk=report_id)
    except FoodReport.DoesNotExist:
        return None


@extend_schema_view(
    post=extend_schema(
        request=None,
        responses={200: AIAnalysisSerializer, 400: dict, 403: dict, 404: dict},
        description=(
            "Runs (or re-runs) preliminary AI visual assessment for a report. "
            "Falls back to a mock result when the real model artifact isn't "
            "configured; see ai_analysis.services for the dispatch logic."
        ),
    ),
)
class AnalyzeReportView(APIView):
    """
    POST /api/v1/reports/<report_id>/analyze/

    Triggers AI analysis for the given FoodReport.

    - Authenticated customer: own report only.
    - Reviewer / Admin: any authorized report.
    - Restaurant user: denied (does not inherit access from restaurant ownership).
    - Unauthenticated: 401.

    The report must have an attached image.
    If an AIAnalysis already exists for this report, it is updated in place
    (no duplicate rows).
    """

    permission_classes = [CanAccessAnalysis]

    def post(self, request: Request, report_id: int) -> Response:
        report = _get_report_or_404(report_id)
        if report is None:
            return Response(
                {"detail": "Food report not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        self.check_object_permissions(request, report)

        try:
            service = AIAnalysisService()
            analysis = service.analyze_food_report(report)
        except AnalysisError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            AIAnalysisSerializer(analysis).data,
            status=status.HTTP_200_OK,
        )


@extend_schema_view(
    get=extend_schema(responses={200: AIAnalysisSerializer, 403: dict, 404: dict}),
)
class ReportAnalysisView(APIView):
    """
    GET /api/v1/reports/<report_id>/analysis/

    Returns the existing AIAnalysis for the given FoodReport.

    Access rules identical to AnalyzeReportView.
    Returns 404 if no analysis has been run yet.
    """

    permission_classes = [CanAccessAnalysis]

    def get(self, request: Request, report_id: int) -> Response:
        report = _get_report_or_404(report_id)
        if report is None:
            return Response(
                {"detail": "Food report not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        self.check_object_permissions(request, report)

        try:
            analysis = report.ai_analysis
        except AIAnalysis.DoesNotExist:
            return Response(
                {"detail": "No AI analysis exists for this report yet."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            AIAnalysisSerializer(analysis).data,
            status=status.HTTP_200_OK,
        )
