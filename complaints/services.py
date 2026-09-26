"""
FoodGuard AI — Complaint Service Layer.

Responsibilities
----------------
- Validate FoodReport ownership before creation
- Verify FoodReport is in SUBMITTED status
- Prevent duplicate complaints per FoodReport
- Derive customer, restaurant, original_language from context (never from client)
- Create Complaint record
- Validate and execute status transitions
- Set / clear resolved_at appropriately

No AI logic. No escalation logic. No translation logic.
"""

from django.utils import timezone

from food_reports.models import FoodReport
from complaints.models import Complaint


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class ComplaintError(Exception):
    """Generic complaint business-rule violation."""


# ---------------------------------------------------------------------------
# Valid status transitions
# ---------------------------------------------------------------------------

# Maps current status → allowed next statuses (reviewer/admin only)
_ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    Complaint.Status.SUBMITTED: {
        Complaint.Status.UNDER_REVIEW,
    },
    Complaint.Status.UNDER_REVIEW: {
        Complaint.Status.SUBMITTED,   # revert with documented reason
        Complaint.Status.RESOLVED,
    },
    Complaint.Status.RESOLVED: {
        Complaint.Status.CLOSED,
    },
    Complaint.Status.CLOSED: set(),  # terminal state
}

# Statuses that represent resolution (trigger resolved_at timestamp)
_RESOLVED_STATUSES = {Complaint.Status.RESOLVED, Complaint.Status.CLOSED}


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class ComplaintService:
    """
    Encapsulates complaint creation and lifecycle management.

    Usage — creation
    ----------------
    service = ComplaintService()
    complaint = service.create(
        food_report=report,
        requesting_user=request.user,
        title=..., description=..., category=...
    )

    Usage — update (reviewer/admin)
    --------------------------------
    complaint = service.update(complaint, validated_data)
    """

    # ------------------------------------------------------------------
    # Creation
    # ------------------------------------------------------------------

    def create(
        self,
        *,
        food_report: FoodReport,
        requesting_user,
        title: str,
        description: str,
        category: str,
    ) -> Complaint:
        """
        Validate and create a Complaint.

        Raises ComplaintError on any rule violation.
        """
        self._check_report_ownership(food_report, requesting_user)
        self._check_report_submitted(food_report)
        self._check_no_existing_complaint(food_report)

        complaint = Complaint.objects.create(
            food_report=food_report,
            customer=requesting_user,
            # Derived server-side — never from the client
            restaurant=food_report.restaurant,
            original_language=requesting_user.preferred_language,
            title=title,
            description=description,
            category=category,
            status=Complaint.Status.SUBMITTED,
            priority=Complaint.Priority.LOW,
        )

        from notifications.models import Notification
        from notifications.services import NotificationService
        NotificationService().notify_reviewers_and_admins(
            event_type=Notification.EventType.COMPLAINT_SUBMITTED,
            message=f"New complaint filed: \"{complaint.title}\".",
            related_complaint=complaint,
        )

        return complaint

    # ------------------------------------------------------------------
    # Update (reviewer / admin only)
    # ------------------------------------------------------------------

    def update(self, complaint: Complaint, validated_data: dict) -> Complaint:
        """
        Apply a validated partial update to an existing Complaint.

        Handles:
        - status transition validation
        - resolved_at bookkeeping
        """
        new_status = validated_data.get("status")
        status_changed = bool(new_status and new_status != complaint.status)

        if status_changed:
            self._check_status_transition(complaint.status, new_status)

        for attr, value in validated_data.items():
            setattr(complaint, attr, value)

        # Manage resolved_at based on the resulting status
        current_status = getattr(complaint, "status")
        if current_status in _RESOLVED_STATUSES:
            if complaint.resolved_at is None:
                complaint.resolved_at = timezone.now()
        else:
            complaint.resolved_at = None

        complaint.save()

        if status_changed:
            from notifications.models import Notification
            from notifications.services import NotificationService
            NotificationService().notify(
                recipient=complaint.customer,
                event_type=Notification.EventType.COMPLAINT_STATUS_CHANGED,
                message=(
                    f"Your complaint \"{complaint.title}\" status changed to "
                    f"{complaint.get_status_display()}."
                ),
                related_complaint=complaint,
            )

        return complaint

    # ------------------------------------------------------------------
    # Private guards
    # ------------------------------------------------------------------

    def _check_report_ownership(self, food_report: FoodReport, user) -> None:
        if food_report.customer_id != user.pk:
            raise ComplaintError(
                "You can only file a complaint for your own food report."
            )

    def _check_report_submitted(self, food_report: FoodReport) -> None:
        if food_report.status != FoodReport.Status.SUBMITTED:
            raise ComplaintError(
                "A complaint can only be filed against a SUBMITTED food report. "
                f"This report is currently '{food_report.get_status_display()}'."
            )

    def _check_no_existing_complaint(self, food_report: FoodReport) -> None:
        if Complaint.objects.filter(food_report=food_report).exists():
            raise ComplaintError(
                "A complaint already exists for this food report. "
                "Only one complaint per report is permitted."
            )

    def _check_status_transition(
        self, current: str, requested: str
    ) -> None:
        allowed = _ALLOWED_TRANSITIONS.get(current, set())
        if requested not in allowed:
            raise ComplaintError(
                f"Status transition from '{current}' to '{requested}' is not allowed. "
                f"Allowed transitions from '{current}': "
                + (", ".join(sorted(allowed)) if allowed else "none (terminal state)")
            )
