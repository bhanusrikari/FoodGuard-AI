"""Lightweight, unauthenticated endpoints for container/orchestrator health checks."""

from django.db import connection
from django.http import JsonResponse


def healthz(request):
    """GET /healthz/ — 200 if the app can reach the database, 503 otherwise."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return JsonResponse({"status": "ok"})
    except Exception:
        return JsonResponse({"status": "unavailable"}, status=503)
