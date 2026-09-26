"""
FoodGuard AI — Analytics endpoint.

Read-only aggregation over existing models — no new persisted state, no
fabricated trends/percentages, no comparison values the database can't
actually derive. Every number is a direct `Count` aggregation; nothing is
loaded into Python as a full queryset first.
"""

from django.db.models import Count
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from ai_analysis.models import AIAnalysis
from analytics.permissions import IsReviewerOrAdmin
from complaints.models import Complaint
from food_reports.models import FoodReport
from restaurants.models import Restaurant


def _counts_by(queryset, field: str) -> dict:
    rows = queryset.values(field).annotate(count=Count("id")).order_by()
    return {row[field]: row["count"] for row in rows}


@extend_schema_view(
    get=extend_schema(
        responses={200: dict, 403: dict},
        description="Reviewer/admin operational overview. Every number is a direct DB aggregation — no fabricated trends.",
    ),
)
class AnalyticsSummaryView(APIView):
    """GET /api/v1/analytics/summary/ — reviewer/admin operational overview."""

    permission_classes = [IsReviewerOrAdmin]

    def get(self, request: Request) -> Response:
        reports = FoodReport.objects.all()
        complaints = Complaint.objects.all()
        analyses = AIAnalysis.objects.all()
        restaurants = Restaurant.objects.all()

        data = {
            "reports": {
                "total": reports.count(),
                "by_status": _counts_by(reports, "status"),
                "by_priority": _counts_by(reports, "priority"),
            },
            "complaints": {
                "total": complaints.count(),
                "by_status": _counts_by(complaints, "status"),
                "by_priority": _counts_by(complaints, "priority"),
            },
            "ai_analysis": {
                "by_status": _counts_by(analyses, "status"),
                "by_risk": _counts_by(analyses, "risk"),
            },
            "restaurants": {
                "total": restaurants.count(),
                "pending_verification": restaurants.filter(is_verified=False).count(),
            },
        }
        return Response(data, status=status.HTTP_200_OK)
