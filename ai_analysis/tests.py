"""
FoodGuard AI — ai_analysis test suite (Step 5).

24 tests covering:
  - AIAnalysis model creation and constraints
  - Service: mock result, metadata, upsert behaviour
  - API: POST /analyze/, GET /analysis/ (auth, ownership, 404s)
  - Permission boundaries: customer, reviewer, admin, restaurant user
  - Response structure and security (no password fields)
  - Preliminary-visual-assessment terminology
"""

import io
import tempfile

from decimal import Decimal
from pathlib import Path
from unittest.mock import patch
from django.core.exceptions import ValidationError
from django.test import override_settings
from PIL import Image as PilImage
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from ai_analysis import services as ai_services
from ai_analysis.models import AIAnalysis
from ai_analysis.services import AIAnalysisService, AnalysisError, _MOCK_RESULT
from food_reports.models import FoodReport
from restaurants.models import Restaurant
from users.models import User

# ai_analysis/services.py resolves _MODEL_PT / _LABEL_MAP once, from
# settings, at import time -- so whether a machine happens to have a real
# (or synthetic development) model.pt at FOOD_QUALITY_MODEL_DIR is ambient
# state these mock-mode tests must not depend on. Patching the two
# module-level path globals forces the mock branch deterministically,
# regardless of what's actually on disk on the machine running the suite.
_NO_MODEL_HERE = Path(tempfile.mkdtemp()) / "no_model_here" / "model.pt"


def _force_mock_mode():
    return patch.multiple(
        ai_services,
        _MODEL_PT=_NO_MODEL_HERE,
        _LABEL_MAP=_NO_MODEL_HERE.with_name("label_map.json"),
    )

TEMP_MEDIA = tempfile.mkdtemp()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_counter = [0]


def make_user(role=User.Role.CUSTOMER) -> User:
    _counter[0] += 1
    return User.objects.create_user(
        email=f"u{_counter[0]}@example.com",
        password="StrongPass99!",
        first_name="Test",
        last_name="User",
        role=role,
    )


def auth(user) -> dict:
    return {"HTTP_AUTHORIZATION": f"Bearer {str(RefreshToken.for_user(user).access_token)}"}


def make_restaurant(owner=None) -> Restaurant:
    if owner is None:
        owner = make_user(role=User.Role.RESTAURANT_USER)
    return Restaurant.objects.create(
        name="Test Dhaba",
        description="",
        address="1 Main St",
        city="Hyderabad",
        state="Telangana",
        pincode="500001",
        owner=owner,
        is_active=True,
    )


def make_png_bytes() -> bytes:
    buf = io.BytesIO()
    PilImage.new("RGB", (10, 10), color=(255, 0, 0)).save(buf, format="PNG")
    return buf.getvalue()


def make_report(customer, restaurant=None, with_image=False) -> FoodReport:
    if restaurant is None:
        restaurant = make_restaurant()
    report = FoodReport.objects.create(
        customer=customer,
        restaurant=restaurant,
        title="Hair in biryani",
        description="Found a long hair in my biryani.",
        status=FoodReport.Status.SUBMITTED,
    )
    if with_image:
        from django.core.files.uploadedfile import SimpleUploadedFile
        img = SimpleUploadedFile("img.png", make_png_bytes(), content_type="image/png")
        report.image.save("img.png", img, save=True)
    return report


ANALYZE_URL = lambda pk: f"/api/v1/reports/{pk}/analyze/"
RESULT_URL = lambda pk: f"/api/v1/reports/{pk}/analysis/"


# ===========================================================================
# 1–8: Model tests
# ===========================================================================

@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class TestAIAnalysisModel(APITestCase):

    def setUp(self):
        self.customer = make_user()
        self.report = make_report(self.customer, with_image=True)

    def test_01_model_creation(self):
        a = AIAnalysis.objects.create(food_report=self.report)
        self.assertIsNotNone(a.pk)
        self.assertEqual(a.food_report, self.report)

    def test_02_one_to_one_relationship(self):
        AIAnalysis.objects.create(food_report=self.report)
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            AIAnalysis.objects.create(food_report=self.report)

    def test_03_duplicate_analysis_prevented(self):
        """update_or_create must not create a second row."""
        AIAnalysis.objects.update_or_create(
            food_report=self.report,
            defaults={"status": AIAnalysis.Status.PENDING},
        )
        AIAnalysis.objects.update_or_create(
            food_report=self.report,
            defaults={"status": AIAnalysis.Status.COMPLETED},
        )
        self.assertEqual(
            AIAnalysis.objects.filter(food_report=self.report).count(), 1
        )

    def test_04_status_defaults_to_pending(self):
        a = AIAnalysis.objects.create(food_report=self.report)
        self.assertEqual(a.status, AIAnalysis.Status.PENDING)

    def test_05_confidence_lower_bound(self):
        a = AIAnalysis(food_report=self.report, confidence=Decimal("-0.001"))
        with self.assertRaises(ValidationError):
            a.full_clean()

    def test_06_confidence_upper_bound(self):
        a = AIAnalysis(food_report=self.report, confidence=Decimal("1.001"))
        with self.assertRaises(ValidationError):
            a.full_clean()

    def test_07_valid_risk_choice(self):
        a = AIAnalysis.objects.create(
            food_report=self.report, risk=AIAnalysis.Risk.HUMAN_REVIEW
        )
        self.assertEqual(a.risk, AIAnalysis.Risk.HUMAN_REVIEW)

    def test_08_valid_concern_structure(self):
        concerns = ["foreign_object", "hygiene_indicator"]
        a = AIAnalysis.objects.create(
            food_report=self.report, concerns=concerns
        )
        self.assertEqual(a.concerns, concerns)


# ===========================================================================
# 9–14: Service tests
# ===========================================================================

@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class TestAIAnalysisService(APITestCase):

    def setUp(self):
        self.customer = make_user()
        self.report_with_image = make_report(self.customer, with_image=True)
        self.report_no_image = make_report(self.customer, with_image=False)
        self.service = AIAnalysisService()

    def test_12_analysis_requires_image(self):
        with self.assertRaises(AnalysisError):
            self.service.analyze_food_report(self.report_no_image)

    def test_13_mock_service_returns_deterministic_result(self):
        with _force_mock_mode():
            a = self.service.analyze_food_report(self.report_with_image)
        self.assertEqual(a.status, AIAnalysis.Status.COMPLETED)
        self.assertEqual(a.risk, _MOCK_RESULT["risk"])
        self.assertEqual(float(a.confidence), _MOCK_RESULT["confidence"])
        self.assertEqual(a.concerns, _MOCK_RESULT["concerns"])

    def test_14_mock_model_metadata_is_correct(self):
        with _force_mock_mode():
            a = self.service.analyze_food_report(self.report_with_image)
        self.assertEqual(a.model_name, "mock-foodguard-ai")
        self.assertEqual(a.model_version, "0.1.0")

    def test_23_repeated_analysis_updates_existing_record(self):
        """Running analysis twice must not create duplicate rows."""
        self.service.analyze_food_report(self.report_with_image)
        self.service.analyze_food_report(self.report_with_image)
        count = AIAnalysis.objects.filter(food_report=self.report_with_image).count()
        self.assertEqual(count, 1)

    def test_24_ai_output_is_preliminary_visual_assessment(self):
        """Message must not claim scientific certainty."""
        with _force_mock_mode():
            a = self.service.analyze_food_report(self.report_with_image)
        # Message must contain the mock indicator, not fabricated certainty
        self.assertIn("mock mode", a.message.lower())
        # Confidence must be 0.0 in mock mode (no fake accuracy)
        self.assertEqual(float(a.confidence), 0.0)


# ===========================================================================
# 9–11, 15–22: API endpoint tests
# ===========================================================================

@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class TestAnalyzeEndpoint(APITestCase):

    def setUp(self):
        self.customer = make_user()
        self.other_customer = make_user()
        self.reviewer = make_user(role=User.Role.REVIEWER)
        self.admin_user = make_user(role=User.Role.ADMIN)
        self.restaurant_user = make_user(role=User.Role.RESTAURANT_USER)
        self.restaurant = make_restaurant(owner=self.restaurant_user)
        self.report = make_report(self.customer, self.restaurant, with_image=True)
        self.report_no_img = make_report(self.customer, self.restaurant, with_image=False)

    # 9 — customer can analyze own report
    def test_09_customer_can_analyze_own_report(self):
        resp = self.client.post(ANALYZE_URL(self.report.pk), **auth(self.customer))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    # 10 — customer cannot analyze another customer's report
    def test_10_customer_cannot_analyze_another_report(self):
        resp = self.client.post(
            ANALYZE_URL(self.report.pk), **auth(self.other_customer)
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    # 11 — unauthenticated → 401
    def test_11_analysis_requires_authentication(self):
        resp = self.client.post(ANALYZE_URL(self.report.pk))
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    # 12 — no image → 400
    def test_12_analyze_requires_image(self):
        resp = self.client.post(
            ANALYZE_URL(self.report_no_img.pk), **auth(self.customer)
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    # 15 — POST analyze endpoint returns analysis fields
    def test_15_post_analyze_endpoint(self):
        resp = self.client.post(ANALYZE_URL(self.report.pk), **auth(self.customer))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.json()
        self.assertIn("status", data)
        self.assertEqual(data["status"], AIAnalysis.Status.COMPLETED)

    # 16 — GET analysis endpoint
    def test_16_get_analysis_endpoint(self):
        # Create analysis first
        self.client.post(ANALYZE_URL(self.report.pk), **auth(self.customer))
        resp = self.client.get(RESULT_URL(self.report.pk), **auth(self.customer))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    # 17 — missing analysis returns 404
    def test_17_missing_analysis_returns_404(self):
        fresh_customer = make_user()
        fresh_report = make_report(fresh_customer, with_image=True)
        resp = self.client.get(RESULT_URL(fresh_report.pk), **auth(fresh_customer))
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    # 18 — reviewer can access analysis
    def test_18_reviewer_access(self):
        self.client.post(ANALYZE_URL(self.report.pk), **auth(self.customer))
        resp = self.client.get(RESULT_URL(self.report.pk), **auth(self.reviewer))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    # 19 — admin can access analysis
    def test_19_admin_access(self):
        self.client.post(ANALYZE_URL(self.report.pk), **auth(self.customer))
        resp = self.client.get(RESULT_URL(self.report.pk), **auth(self.admin_user))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    # 20 — restaurant user cannot access analysis even for own restaurant
    def test_20_restaurant_user_restriction(self):
        self.client.post(ANALYZE_URL(self.report.pk), **auth(self.customer))
        resp = self.client.get(
            RESULT_URL(self.report.pk), **auth(self.restaurant_user)
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    # 21 — API response structure
    def test_21_api_response_structure(self):
        resp = self.client.post(ANALYZE_URL(self.report.pk), **auth(self.customer))
        data = resp.json()
        for field in [
            "id", "food_report", "status", "risk", "confidence",
            "concerns", "message", "analyzed_at", "model_name",
            "model_version", "created_at", "updated_at",
        ]:
            self.assertIn(field, data, msg=f"Field '{field}' missing from response")

    # 22 — no password or internal security fields exposed
    def test_22_no_password_fields_in_response(self):
        resp = self.client.post(ANALYZE_URL(self.report.pk), **auth(self.customer))
        data = resp.json()
        for forbidden in ["password", "secret_key", "token", "hash"]:
            self.assertNotIn(forbidden, data)
