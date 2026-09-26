from rest_framework.permissions import BasePermission

from users.models import User

_ALLOWED_ROLES = {User.Role.REVIEWER, User.Role.ADMIN}


class IsReviewerOrAdmin(BasePermission):
    message = "Only reviewers and admins may access analytics."

    def has_permission(self, request, view) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in _ALLOWED_ROLES
        )
