"""
FoodGuard AI — root URL configuration.
"""

import re

from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve as serve_static
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from config.views import healthz

urlpatterns = [
    # Django admin
    path("admin/", admin.site.urls),

    # Container/orchestrator health check (unauthenticated)
    path("healthz/", healthz, name="healthz"),

    # OpenAPI schema + docs UI
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),

    # Auth endpoints: /api/v1/auth/
    path("api/v1/auth/", include("users.urls", namespace="users")),

    # Restaurant endpoints: /api/v1/restaurants/
    path("api/v1/restaurants/", include("restaurants.urls", namespace="restaurants")),

    # Food report endpoints: /api/v1/reports/
    path("api/v1/reports/", include("food_reports.urls", namespace="food_reports")),

    # AI analysis endpoints: /api/v1/reports/<id>/analyze/ and /analysis/
    path("api/v1/reports/", include("ai_analysis.urls", namespace="ai_analysis")),

    # Complaint endpoints: /api/v1/complaints/
    path("api/v1/complaints/", include("complaints.urls", namespace="complaints")),

    # Escalation endpoints: /api/v1/escalations/
    path("api/v1/escalations/", include("escalation.urls", namespace="escalation")),

    # Feedback endpoints: /api/v1/feedback/
    path("api/v1/feedback/", include("feedback.urls", namespace="feedback")),

    # Notification endpoints: /api/v1/notifications/
    path("api/v1/notifications/", include("notifications.urls", namespace="notifications")),

    # Analytics endpoints: /api/v1/analytics/
    path("api/v1/analytics/", include("analytics.urls", namespace="analytics")),
]

# Serve uploaded media files. Always on in development (DEBUG=True); in
# production this stays on by default too (SERVE_MEDIA_VIA_DJANGO, see
# config/settings.py) until a reverse proxy / object storage takes over —
# without this, uploaded report images are unreachable in production, which
# was an open gap (see Dockerfile and README "Deployment" section).
#
# Deliberately NOT using django.conf.urls.static.static() here: that
# helper hardcodes `if not settings.DEBUG: return []` internally, so it
# silently serves nothing outside DEBUG no matter what condition wraps the
# call. django.views.static.serve is wired directly instead, exactly as
# Django's own docs describe for a small deployment that isn't yet putting
# a reverse proxy / object storage in front of media.
if settings.DEBUG or settings.SERVE_MEDIA_VIA_DJANGO:
    urlpatterns += [
        re_path(
            r"^%s(?P<path>.*)$" % re.escape(settings.MEDIA_URL.lstrip("/")),
            serve_static,
            {"document_root": settings.MEDIA_ROOT},
        ),
    ]
