from django.conf import settings
from django.db import models


class Notification(models.Model):
    """
    A single in-app notification for one recipient.

    Design principles
    ------------------
    1. Recorded synchronously by the service layer that raises the event —
       no realtime/websocket/queue infrastructure. Clients poll
       GET /api/v1/notifications/.
    2. `related_report` / `related_complaint` are optional deep-link
       targets, SET_NULL on delete so a notification survives its subject
       being removed (it just loses the link).
    3. `message` is plain, human-readable text decided by the raising
       service — this model has no opinion on wording.
    """

    class EventType(models.TextChoices):
        REPORT_SUBMITTED = "REPORT_SUBMITTED", "Report Submitted"
        REPORT_STATUS_CHANGED = "REPORT_STATUS_CHANGED", "Report Status Changed"
        AI_ANALYSIS_COMPLETED = "AI_ANALYSIS_COMPLETED", "AI Analysis Completed"
        COMPLAINT_SUBMITTED = "COMPLAINT_SUBMITTED", "Complaint Submitted"
        COMPLAINT_STATUS_CHANGED = "COMPLAINT_STATUS_CHANGED", "Complaint Status Changed"
        ESCALATION_CREATED = "ESCALATION_CREATED", "Escalation Created"
        ESCALATION_UPDATED = "ESCALATION_UPDATED", "Escalation Updated"

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
        verbose_name="recipient",
    )

    event_type = models.CharField(
        max_length=30,
        choices=EventType.choices,
        db_index=True,
        verbose_name="event type",
    )

    message = models.TextField(verbose_name="message")

    related_report = models.ForeignKey(
        "food_reports.FoodReport",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notifications",
        verbose_name="related report",
    )

    related_complaint = models.ForeignKey(
        "complaints.Complaint",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notifications",
        verbose_name="related complaint",
    )

    is_read = models.BooleanField(default=False, db_index=True, verbose_name="is read")

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "notification"
        verbose_name_plural = "notifications"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "is_read"], name="notif_recipient_read_idx"),
        ]

    def __str__(self) -> str:
        return f"Notification[{self.event_type}] to user_id={self.recipient_id}"
