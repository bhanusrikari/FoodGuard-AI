"""Focused, DB-free tests for the notification multilingual wiring
(notifications/serializers.py's localized_message / message_language
fields). Uses stub objects instead of real Notification model instances —
these fields only read event_type/message/related_report.title/
related_complaint.title, so a duck-typed stub is sufficient.

Run:
    python -m notifications.test_translation
"""

import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django  # noqa: E402

django.setup()

from notifications.models import Notification  # noqa: E402
from notifications.serializers import NotificationSerializer  # noqa: E402


def _notification_stub(event_type, message="original english text", related_report=None, related_complaint=None):
    return SimpleNamespace(
        event_type=event_type,
        message=message,
        related_report=related_report,
        related_complaint=related_complaint,
    )


def _serializer_with_language(preferred_language):
    request = SimpleNamespace(user=SimpleNamespace(preferred_language=preferred_language))
    return NotificationSerializer(context={"request": request})


class TestTranslatableEvents(unittest.TestCase):
    def test_report_submitted_translates_with_title(self):
        serializer = _serializer_with_language("hi")
        stub = _notification_stub(
            Notification.EventType.REPORT_SUBMITTED,
            related_report=SimpleNamespace(title="Cold biryani"),
        )
        text = serializer.get_localized_message(stub)
        self.assertIn("Cold biryani", text)
        self.assertTrue(any("ऀ" <= ch <= "ॿ" for ch in text))

    def test_ai_analysis_completed_translates_with_title(self):
        serializer = _serializer_with_language("te")
        stub = _notification_stub(
            Notification.EventType.AI_ANALYSIS_COMPLETED,
            related_report=SimpleNamespace(title="Mystery curry"),
        )
        text = serializer.get_localized_message(stub)
        self.assertIn("Mystery curry", text)
        self.assertTrue(any("ఀ" <= ch <= "౿" for ch in text))

    def test_complaint_submitted_translates_with_title(self):
        serializer = _serializer_with_language("hi")
        stub = _notification_stub(
            Notification.EventType.COMPLAINT_SUBMITTED,
            related_complaint=SimpleNamespace(title="Foreign object found"),
        )
        text = serializer.get_localized_message(stub)
        self.assertIn("Foreign object found", text)

    def test_english_user_gets_english_rendering(self):
        serializer = _serializer_with_language("en")
        stub = _notification_stub(
            Notification.EventType.REPORT_SUBMITTED,
            related_report=SimpleNamespace(title="Cold biryani"),
        )
        text = serializer.get_localized_message(stub)
        self.assertEqual(text, 'A new food report "Cold biryani" was submitted and needs review.')


class TestUntranslatableEventsFallBackHonestly(unittest.TestCase):
    def test_complaint_status_changed_falls_back_to_original_message(self):
        """Status-at-the-time isn't reconstructable from the related
        object's *current* state — must not guess/fabricate a translation."""
        serializer = _serializer_with_language("hi")
        stub = _notification_stub(
            Notification.EventType.COMPLAINT_STATUS_CHANGED,
            message="Your complaint status changed to RESOLVED.",
            related_complaint=SimpleNamespace(title="Foreign object found"),
        )
        text = serializer.get_localized_message(stub)
        self.assertEqual(text, "Your complaint status changed to RESOLVED.")

    def test_escalation_created_falls_back_to_original_message(self):
        serializer = _serializer_with_language("te")
        stub = _notification_stub(Notification.EventType.ESCALATION_CREATED, message="An escalation was created.")
        text = serializer.get_localized_message(stub)
        self.assertEqual(text, "An escalation was created.")

    def test_missing_related_object_falls_back_to_original_message(self):
        """SET_NULL means related_report can legitimately be None (its
        subject was deleted) — must not crash, must not fabricate a title."""
        serializer = _serializer_with_language("hi")
        stub = _notification_stub(
            Notification.EventType.REPORT_SUBMITTED,
            message="A new food report was submitted.",
            related_report=None,
        )
        text = serializer.get_localized_message(stub)
        self.assertEqual(text, "A new food report was submitted.")


class TestMessageLanguageField(unittest.TestCase):
    def test_translatable_event_reports_requested_language(self):
        serializer = _serializer_with_language("hi")
        stub = _notification_stub(
            Notification.EventType.REPORT_SUBMITTED,
            related_report=SimpleNamespace(title="Cold biryani"),
        )
        self.assertEqual(serializer.get_message_language(stub), "hi")

    def test_untranslatable_event_reports_english(self):
        serializer = _serializer_with_language("hi")
        stub = _notification_stub(Notification.EventType.ESCALATION_UPDATED)
        self.assertEqual(serializer.get_message_language(stub), "en")

    def test_missing_related_object_reports_english(self):
        serializer = _serializer_with_language("hi")
        stub = _notification_stub(Notification.EventType.REPORT_SUBMITTED, related_report=None)
        self.assertEqual(serializer.get_message_language(stub), "en")

    def test_unsupported_language_reports_english(self):
        serializer = _serializer_with_language("kn")
        stub = _notification_stub(
            Notification.EventType.COMPLAINT_SUBMITTED,
            related_complaint=SimpleNamespace(title="x"),
        )
        self.assertEqual(serializer.get_message_language(stub), "en")


if __name__ == "__main__":
    unittest.main()
