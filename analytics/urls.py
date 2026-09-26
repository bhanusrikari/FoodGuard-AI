from django.urls import path

from analytics.views import AnalyticsSummaryView

app_name = "analytics"

urlpatterns = [
    path("summary/", AnalyticsSummaryView.as_view(), name="summary"),
]
