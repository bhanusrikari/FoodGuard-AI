"""
FoodGuard AI — Escalation Service Layer.

Responsibilities
----------------
- Validate complaint existence and review state
- Derive created_by, original_language from context (never from client)
- Validate assigned_to role (must be REVIEWER or ADMIN)
- Prevent active-duplicate escalation per complaint
- Create escalation record
- Validate and execute status transitions
- Manage resolved_at timestamp

No AI logic. No notification logic. No translation logic.
"""

from django.utils import timezone

from complaints.models import Complaint
from escalation.models import Escalation
from users.models import User


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class EscalationError(Exception):
    """Raised when an escalation business rule is violated."""


# ---------------------------------------------------------------------------
# Allowed status transitions
# ---------------------------------------------------------------------------

_ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    Escalation.Status.PENDING: {Escalation.Status.IN_REVIEW},
    Escalation.Status.IN_REVIEW: {Escalation.Status.RESOLVED},
    Escalation.Status.RESOLVED: {Escalation.Status.CLOSED},
    Escalation.Status.CLOSED: set(),  # terminal
}

_RESOLVED_STATUSES = {Escalation.Status.RESOLVED, Escalation.Status.CLOSED}

# Roles permitted to be assigned to an escalation
_ASSIGNABLE_ROLES = {User.Role.REVIEWER, User.Role.ADMIN}


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class EscalationService:
    """
    Encapsulates escalation creation and lifecycle management.

    Usage — creation
    ----------------
    service = EscalationService()
    escalation = service.create(
        complaint=complaint,
        requesting_user=request.user,
        escalation_level=...,
        reason=...,
        assigned_to_user=...  # optional
    )

    Usage — update
    --------------
    escalation = service.update(escalation, validated_data)
    """

    # ------------------------------------------------------------------
    # Creation
    # ------------------------------------------------------------------

    def create(
        self,
        *,
        complaint: Complaint,
        requesting_user,
        escalation_level: str,
        reason: str,
        assigned_to_user=None,
    ) -> Escalation:
        self._check_complaint_status(complaint)
        self._check_no_active_escalation(complaint)
        if assigned_to_user is not None:
            self._check_assignee_role(assigned_to_user)

        escalation = Escalation.objects.create(
            complaint=complaint,
            created_by=requesting_user,
            assigned_to=assigned_to_user,
            escalation_level=escalation_level,
            reason=reason,
            original_language=requesting_user.preferred_language,
            status=Escalation.Status.PENDING,
        )

        from notifications.models import Notification
        from notifications.services import NotificationService
        message = f"Escalation created for complaint \"{complaint.title}\"."
        if assigned_to_user is not None:
            NotificationService().notify(
                recipient=assigned_to_user,
                event_type=Notification.EventType.ESCALATION_CREATED,
                message=message,
                related_complaint=complaint,
            )
        else:
            NotificationService().notify_reviewers_and_admins(
                event_type=Notification.EventType.ESCALATION_CREATED,
                message=message,
                related_complaint=complaint,
            )

        return escalation

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update(self, escalation: Escalation, validated_data: dict) -> Escalation:
        new_status = validated_data.get("status")
        if new_status and new_status != escalation.status:
            self._check_status_transition(escalation.status, new_status)

        new_assignee = validated_data.get("assigned_to")
        if new_assignee is not None:
            self._check_assignee_role(new_assignee)

        for attr, value in validated_data.items():
            setattr(escalation, attr, value)

        # Manage resolved_at
        if escalation.status in _RESOLVED_STATUSES:
            if escalation.resolved_at is None:
                escalation.resolved_at = timezone.now()
        else:
            escalation.resolved_at = None

        escalation.save()

        from notifications.models import Notification
        from notifications.services import NotificationService
        message = f"Escalation for complaint \"{escalation.complaint.title}\" was updated."
        notified_ids = set()
        for recipient in [escalation.created_by, escalation.assigned_to]:
            if recipient is not None and recipient.pk not in notified_ids:
                NotificationService().notify(
                    recipient=recipient,
                    event_type=Notification.EventType.ESCALATION_UPDATED,
                    message=message,
                    related_complaint=escalation.complaint,
                )
                notified_ids.add(recipient.pk)

        return escalation

    # ------------------------------------------------------------------
    # Private guards
    # ------------------------------------------------------------------

    def _check_complaint_status(self, complaint: Complaint) -> None:
        """
        Complaint should be UNDER_REVIEW before escalation.
        Warn but don't hard-block if it's in another non-terminal state,
        to allow flexibility for admins.  Hard-block RESOLVED/CLOSED.
        """
        terminal = {Complaint.Status.RESOLVED, Complaint.Status.CLOSED}
        if complaint.status in terminal:
            raise EscalationError(
                f"Cannot escalate a complaint that is already "
                f"'{complaint.get_status_display()}'. "
                "Only open complaints may be escalated."
            )

    def _check_no_active_escalation(self, complaint: Complaint) -> None:
        active = Escalation.objects.filter(
            complaint=complaint,
            status__in=[Escalation.Status.PENDING, Escalation.Status.IN_REVIEW],
        ).exists()
        if active:
            raise EscalationError(
                "An active escalation already exists for this complaint. "
                "Resolve or close the existing escalation before creating a new one."
            )

    def _check_assignee_role(self, user) -> None:
        if user.role not in _ASSIGNABLE_ROLES:
            raise EscalationError(
                f"User '{user.email}' cannot be assigned to an escalation. "
                "Only REVIEWER or ADMIN users may be assigned."
            )

    def _check_status_transition(self, current: str, requested: str) -> None:
        allowed = _ALLOWED_TRANSITIONS.get(current, set())
        if requested not in allowed:
            raise EscalationError(
                f"Status transition from '{current}' to '{requested}' is not allowed. "
                f"Allowed from '{current}': "
                + (", ".join(sorted(allowed)) if allowed else "none (terminal state)")
            )
