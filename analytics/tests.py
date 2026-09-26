"""
FoodGuard AI — analytics app test suite.

Covers: correct aggregation counts against known fixtures, role gating, and
absence of N+1 queries (aggregation must not scale with row count).
"""

from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from complaints.models import Complaint
from complaints.services import ComplaintService
from food_reports.models import FoodReport
from restaurants.models import Restaurant
from users.models import User

_counter = [0]


def make_user(role=User.Role.CUSTOMER) -> User:
    _counter[0] += 1
    return User.objects.create_user(
        email=f"a{_counter[0]}@example.com",
        password="StrongPass99!",
        first_name="Test",
        last_name="User",
        role=role,
    )


def auth(user) -> dict:
    return {"HTTP_AUTHORIZATION": f"Bearer {str(RefreshToken.for_user(user).access_token)}"}


def make_restaurant(owner=None, is_verified=False) -> Restaurant:
    if owner is None:
        owner = make_user(role=User.Role.RESTAURANT_USER)
    return Restaurant.objects.create(
        name="Test Dhaba", address="1 Main St", city="Hyderabad",
        state="Telangana", pincode="500001", owner=owner,
        is_active=True, is_verified=is_verified,
    )


class TestAnalyticsSummary(APITestCase):

    def setUp(self):
        self.customer = make_user()
        self.reviewer = make_user(role=User.Role.REVIEWER)
        self.restaurant_user = make_user(role=User.Role.RESTAURANT_USER)
        self.restaurant = make_restaurant(owner=self.restaurant_user, is_verified=True)
        make_restaurant(is_verified=False)

        self.report1 = FoodReport.objects.create(
            customer=self.customer, restaurant=self.restaurant, title="r1",
            description="d", status=FoodReport.Status.SUBMITTED,
        )
        self.report2 = FoodReport.objects.create(
            customer=self.customer, restaurant=self.restaurant, title="r2",
            description="d", status=FoodReport.Status.DRAFT,
        )
        ComplaintService().create(
            food_report=self.report1, requesting_user=self.customer,
            title="c1", description="d", category=Complaint.Category.SPOILAGE,
        )

    def test_01_reports_counts_correct(self):
        resp = self.client.get("/api/v1/analytics/summary/", **auth(self.reviewer))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.json()
        self.assertEqual(data["reports"]["total"], 2)
        self.assertEqual(data["reports"]["by_status"]["SUBMITTED"], 1)
        self.assertEqual(data["reports"]["by_status"]["DRAFT"], 1)

    def test_02_complaints_counts_correct(self):
        resp = self.client.get("/api/v1/analytics/summary/", **auth(self.reviewer))
        data = resp.json()
        self.assertEqual(data["complaints"]["total"], 1)
        self.assertEqual(data["complaints"]["by_status"]["SUBMITTED"], 1)

    def test_03_restaurant_counts_correct(self):
        resp = self.client.get("/api/v1/analytics/summary/", **auth(self.reviewer))
        data = resp.json()
        self.assertEqual(data["restaurants"]["total"], 2)
        self.assertEqual(data["restaurants"]["pending_verification"], 1)

    def test_04_customer_denied(self):
        resp = self.client.get("/api/v1/analytics/summary/", **auth(self.customer))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_05_restaurant_user_denied(self):
        resp = self.client.get("/api/v1/analytics/summary/", **auth(self.restaurant_user))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_06_unauthenticated_denied(self):
        resp = self.client.get("/api/v1/analytics/summary/")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_07_admin_allowed(self):
        admin = make_user(role=User.Role.ADMIN)
        resp = self.client.get("/api/v1/analytics/summary/", **auth(admin))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_08_query_count_does_not_scale_with_row_count(self):
        # Baseline with the small fixture set above.
        with CaptureQueriesContext(connection) as ctx:
            self.client.get("/api/v1/analytics/summary/", **auth(self.reviewer))
        baseline = len(ctx.captured_queries)

        # Add many more rows.
        for i in range(15):
            FoodReport.objects.create(
                customer=self.customer, restaurant=self.restaurant, title=f"extra{i}",
                description="d", status=FoodReport.Status.SUBMITTED,
            )

        with CaptureQueriesContext(connection) as ctx:
            self.client.get("/api/v1/analytics/summary/", **auth(self.reviewer))
        after = len(ctx.captured_queries)

        # A broken (N+1) implementation would grow roughly linearly with the
        # 15 new rows; a pure-aggregation implementation issues the same
        # fixed number of queries regardless of row count.
        self.assertEqual(baseline, after)
        self.assertLess(after, 15)
