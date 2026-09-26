"""
FoodGuard AI — AI Analysis Service.

Architecture
------------
AIAnalysisService is a clean abstraction layer that separates the view
from any analysis implementation.

The service exposes one public method:
    analyze_food_report(food_report)

It always upserts the AIAnalysis record (update-or-create) so repeated
calls update the existing row rather than inserting duplicates.

Current backend
---------------
RealAIAnalysisService — MobileNetV3-Small trained on the 3-class
FoodGuard Quality Dataset (normal / spoilage_indicator / mold_like_growth).
Model weights are loaded once and cached for the process lifetime.

Terminology
-----------
Results are a PRELIMINARY VISUAL ASSESSMENT only.
They do NOT constitute:
  - scientific food-safety certification
  - proof of contamination
  - evidence of restaurant wrongdoing

No external APIs.  No retraining.  No datasets.  No OCR.
"""

import logging
from pathlib import Path

from django.conf import settings
from django.utils import timezone

from food_reports.models import FoodReport
from ai_analysis.models import AIAnalysis

logger = logging.getLogger("foodguard")

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class AnalysisError(Exception):
    """Raised when an analysis cannot proceed."""


# ---------------------------------------------------------------------------
# Model-artifact paths (used to detect whether real model exists)
# Sourced from FOOD_QUALITY_MODEL_DIR (env-configurable; see settings.py).
# ---------------------------------------------------------------------------

_MODEL_DIR = Path(settings.FOOD_QUALITY_MODEL_DIR)
_MODEL_PT     = _MODEL_DIR / "model.pt"
_LABEL_MAP    = _MODEL_DIR / "label_map.json"


# ---------------------------------------------------------------------------
# Mock result — kept for fallback / testing without model artifacts
# ---------------------------------------------------------------------------

_MOCK_RESULT = {
    "food":         "unknown",
    "risk":         AIAnalysis.Risk.HUMAN_REVIEW,
    "confidence":   0.0,
    "concerns":     ["uncertain"],
    "message": (
        "AI analysis is currently running in mock mode. "
        "A real visual model will be integrated in a future release. "
        "This result is NOT a scientific food-safety determination."
    ),
    "model_name":    "mock-foodguard-ai",
    "model_version": "0.1.0",
}


# ---------------------------------------------------------------------------
# Base service
# ---------------------------------------------------------------------------

class AIAnalysisService:
    """
    Public interface for food-report AI analysis.

    Automatically delegates to RealAIAnalysisService when model.pt exists,
    falling back to the mock implementation when it does not.  This keeps
    the API layer, serializers, and tests unchanged.
    """

    def analyze_food_report(self, food_report: FoodReport) -> AIAnalysis:
        self._validate(food_report)

        analysis, _ = AIAnalysis.objects.update_or_create(
            food_report=food_report,
            defaults={"status": AIAnalysis.Status.PROCESSING},
        )

        try:
            result = self._run_analysis(food_report)
            analysis.status      = AIAnalysis.Status.COMPLETED
            analysis.risk        = result["risk"]
            analysis.confidence  = result["confidence"]
            analysis.concerns    = result["concerns"]
            analysis.message     = result["message"]
            analysis.model_name  = result["model_name"]
            analysis.model_version = result["model_version"]
            analysis.analyzed_at = timezone.now()
            analysis.save()

            from notifications.models import Notification
            from notifications.services import NotificationService
            NotificationService().notify(
                recipient=food_report.customer,
                event_type=Notification.EventType.AI_ANALYSIS_COMPLETED,
                message=f"AI analysis is ready for your report \"{food_report.title}\".",
                related_report=food_report,
            )
        except Exception as exc:
            # Log full detail server-side only — never expose internal
            # exception text, file paths, or stack traces to the API client
            # or persist them in a field the client can read back.
            logger.exception(
                "AI analysis failed for food_report_id=%s", food_report.pk
            )
            safe_message = (
                "AI analysis could not be completed due to an internal error. "
                "Please try again later."
            )
            analysis.status  = AIAnalysis.Status.FAILED
            analysis.message = safe_message
            analysis.save()
            raise AnalysisError(safe_message) from exc

        return analysis

    def _validate(self, food_report: FoodReport) -> None:
        if not food_report.image:
            raise AnalysisError(
                "This food report does not have an attached image. "
                "Please upload an image before requesting AI analysis."
            )

    def _run_analysis(self, food_report: FoodReport) -> dict:
        """
        Dispatch to real model if available, otherwise use mock.
        Subclasses may override this method.
        """
        if _MODEL_PT.exists() and _LABEL_MAP.exists():
            return _run_real_analysis(food_report)
        return _MOCK_RESULT.copy()


# ---------------------------------------------------------------------------
# Real-model analysis helper (called when artifacts exist)
# ---------------------------------------------------------------------------

def _run_real_analysis(food_report: FoodReport) -> dict:
    """
    Call the inference engine with the report's image path.
    Translates the inference engine's output into the canonical
    result dict expected by AIAnalysisService.
    """
    from ai_analysis.inference import run_inference

    # Resolve absolute image path from Django ImageField
    image_path = food_report.image.path

    result = run_inference(image_path)

    return {
        "food":          result["predicted_class"],
        "risk":          result["risk"],
        "confidence":    result["confidence"],
        "concerns":      result["concerns"],
        "message":       result["message"],
        "model_name":    result["model_name"],
        "model_version": result["model_version"],
    }
