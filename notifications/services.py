"""
FoodGuard AI — Notification Service.

Responsibilities
----------------
- Create Notification rows for a recipient or a set of recipients.
- Provide the `notify_reviewers_and_admins` fan-out helper used by other
  apps' services when an event needs to reach the operational team rather
  than one specific user.

No realtime/websocket/queue infrastructure — notifications are plain
synchronous DB writes, polled by the client via GET /api/v1/notifications/.
This module has no opinion on *when* to notify; callers (food_reports,
ai_analysis, complaints, escalation services) decide that.
"""

from notifications.models import Notification
from users.models import User

_STAFF_ROLES = [User.Role.REVIEWER, User.Role.ADMIN]


class NotificationService:

    def notify(
        self,
        *,
        recipient,
        event_type: str,
        message: str,
        related_report=None,
        related_complaint=None,
    ) -> Notification:
        return Notification.objects.create(
            recipient=recipient,
            event_type=event_type,
            message=message,
            related_report=related_report,
            related_complaint=related_complaint,
        )

    def notify_reviewers_and_admins(
        self,
        *,
        event_type: str,
        message: str,
        related_report=None,
        related_complaint=None,
    ) -> list[Notification]:
        staff = User.objects.filter(role__in=_STAFF_ROLES)
        return [
            self.notify(
                recipient=user,
                event_type=event_type,
                message=message,
                related_report=related_report,
                related_complaint=related_complaint,
            )
            for user in staff
        ]
