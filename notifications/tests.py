"""
FoodGuard AI — notifications app test suite.

Covers: model creation, service fan-out to reviewers/admins, ownership on
list/detail, is_read toggle, and one test per real hook point proving the
existing workflow services actually create a notification (not mocked).
"""

from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from ai_analysis.services import AIAnalysisService
from complaints.models import Complaint
from complaints.services import ComplaintService
from escalation.services import EscalationService
from food_reports.models import FoodReport
from food_reports.services import FoodReportSubmissionService
from notifications.models import Notification
from notifications.services import NotificationService
from restaurants.models import Restaurant
from users.models import User

_counter = [0]


def make_user(role=User.Role.CUSTOMER) -> User:
    _counter[0] += 1
    return User.objects.create_user(
        email=f"n{_counter[0]}@example.com",
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
        name="Test Dhaba", address="1 Main St", city="Hyderabad",
        state="Telangana", pincode="500001", owner=owner, is_active=True,
    )


def make_png():
    import io
    from django.core.files.uploadedfile import SimpleUploadedFile
    from PIL import Image as PilImage
    buf = io.BytesIO()
    PilImage.new("RGB", (10, 10), color=(200, 100, 50)).save(buf, format="PNG")
    return SimpleUploadedFile("img.png", buf.getvalue(), content_type="image/png")


class TestNotificationModel(APITestCase):

    def test_01_create_notification(self):
        user = make_user()
        n = Notification.objects.create(
            recipient=user,
            event_type=Notification.EventType.REPORT_SUBMITTED,
            message="Test message",
        )
        self.assertIsNotNone(n.pk)
        self.assertFalse(n.is_read)


class TestNotificationServiceFanOut(APITestCase):

    def test_02_notify_single_recipient(self):
        user = make_user()
        n = NotificationService().notify(
            recipient=user, event_type=Notification.EventType.REPORT_SUBMITTED, message="hi"
        )
        self.assertEqual(n.recipient, user)

    def test_03_notify_reviewers_and_admins_fans_out_to_all_staff(self):
        reviewer = make_user(role=User.Role.REVIEWER)
        admin = make_user(role=User.Role.ADMIN)
        customer = make_user(role=User.Role.CUSTOMER)  # must NOT receive it

        created = NotificationService().notify_reviewers_and_admins(
            event_type=Notification.EventType.COMPLAINT_SUBMITTED, message="new complaint"
        )
        recipients = {n.recipient_id for n in created}
        self.assertIn(reviewer.pk, recipients)
        self.assertIn(admin.pk, recipients)
        self.assertNotIn(customer.pk, recipients)


class TestNotificationAPI(APITestCase):

    def setUp(self):
        self.owner = make_user()
        self.other = make_user()
        self.n1 = Notification.objects.create(
            recipient=self.owner, event_type=Notification.EventType.REPORT_SUBMITTED, message="m1"
        )

    def test_04_list_returns_only_own_notifications(self):
        Notification.objects.create(
            recipient=self.other, event_type=Notification.EventType.REPORT_SUBMITTED, message="not mine"
        )
        resp = self.client.get("/api/v1/notifications/", **auth(self.owner))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        ids = {row["id"] for row in resp.json()}
        self.assertEqual(ids, {self.n1.pk})

    def test_05_unauthenticated_denied(self):
        resp = self.client.get("/api/v1/notifications/")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_06_mark_as_read_by_owner(self):
        resp = self.client.patch(
            f"/api/v1/notifications/{self.n1.pk}/", {"is_read": True},
            format="json", **auth(self.owner),
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.n1.refresh_from_db()
        self.assertTrue(self.n1.is_read)

    def test_07_cannot_mark_another_users_notification(self):
        resp = self.client.patch(
            f"/api/v1/notifications/{self.n1.pk}/", {"is_read": True},
            format="json", **auth(self.other),
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_08_cannot_patch_protected_fields(self):
        resp = self.client.patch(
            f"/api/v1/notifications/{self.n1.pk}/", {"message": "hacked"},
            format="json", **auth(self.owner),
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


class TestNotificationHookPoints(APITestCase):
    """Proves real workflow services actually create notifications — not mocked."""

    def test_09_report_submission_notifies_reviewers_and_admins(self):
        reviewer = make_user(role=User.Role.REVIEWER)
        customer = make_user()
        restaurant = make_restaurant()
        report = FoodReport.objects.create(
            customer=customer, restaurant=restaurant, title="Hair in food",
            description="desc", status=FoodReport.Status.DRAFT,
        )
        report.image.save("img.png", make_png(), save=True)

        FoodReportSubmissionService(report, customer).submit()

        self.assertTrue(
            Notification.objects.filter(
                recipient=reviewer, event_type=Notification.EventType.REPORT_SUBMITTED,
                related_report=report,
            ).exists()
        )

    def test_10_ai_analysis_completion_notifies_customer(self):
        customer = make_user()
        restaurant = make_restaurant()
        report = FoodReport.objects.create(
            customer=customer, restaurant=restaurant, title="t", description="d",
            status=FoodReport.Status.SUBMITTED,
        )
        report.image.save("img.png", make_png(), save=True)

        AIAnalysisService().analyze_food_report(report)

        self.assertTrue(
            Notification.objects.filter(
                recipient=customer, event_type=Notification.EventType.AI_ANALYSIS_COMPLETED,
                related_report=report,
            ).exists()
        )

    def test_11_complaint_creation_notifies_reviewers_and_admins(self):
        admin = make_user(role=User.Role.ADMIN)
        customer = make_user()
        restaurant = make_restaurant()
        report = FoodReport.objects.create(
            customer=customer, restaurant=restaurant, title="t", description="d",
            status=FoodReport.Status.SUBMITTED,
        )
        complaint = ComplaintService().create(
            food_report=report, requesting_user=customer,
            title="Complaint", description="desc", category=Complaint.Category.SPOILAGE,
        )
        self.assertTrue(
            Notification.objects.filter(
                recipient=admin, event_type=Notification.EventType.COMPLAINT_SUBMITTED,
                related_complaint=complaint,
            ).exists()
        )

    def test_12_complaint_status_update_notifies_customer(self):
        customer = make_user()
        restaurant = make_restaurant()
        report = FoodReport.objects.create(
            customer=customer, restaurant=restaurant, title="t", description="d",
            status=FoodReport.Status.SUBMITTED,
        )
        complaint = ComplaintService().create(
            food_report=report, requesting_user=customer,
            title="c", description="d", category=Complaint.Category.OTHER,
        )
        ComplaintService().update(complaint, {"status": Complaint.Status.UNDER_REVIEW})

        self.assertTrue(
            Notification.objects.filter(
                recipient=customer, event_type=Notification.EventType.COMPLAINT_STATUS_CHANGED,
                related_complaint=complaint,
            ).exists()
        )

    def test_13_escalation_creation_notifies_assignee(self):
        from escalation.models import Escalation

        assignee = make_user(role=User.Role.REVIEWER)
        creator = make_user(role=User.Role.ADMIN)
        customer = make_user()
        restaurant = make_restaurant()
        report = FoodReport.objects.create(
            customer=customer, restaurant=restaurant, title="t", description="d",
            status=FoodReport.Status.SUBMITTED,
        )
        complaint = ComplaintService().create(
            food_report=report, requesting_user=customer, title="c", description="d",
            category=Complaint.Category.OTHER,
        )
        ComplaintService().update(complaint, {"status": Complaint.Status.UNDER_REVIEW})

        EscalationService().create(
            complaint=complaint, requesting_user=creator,
            escalation_level=Escalation.Level.LEVEL_1, reason="needs review",
            assigned_to_user=assignee,
        )

        self.assertTrue(
            Notification.objects.filter(
                recipient=assignee, event_type=Notification.EventType.ESCALATION_CREATED,
            ).exists()
        )
