"""
Create the first admin/superuser account from environment variables.

Render's free tier has no shell/SSH access, so the usual interactive
`createsuperuser` prompt can't be run there after deploy. This command is
the non-interactive equivalent, wired into the deploy start command
instead (see render.yaml), and is safe to run on every deploy.

Required environment variables (all three -- no defaults, no fallback):
    DJANGO_ADMIN_USERNAME  This User model (users/models.py) has no
                           username field at all -- email is the unique
                           login identifier (USERNAME_FIELD). This value
                           is used only as the created account's
                           first_name; it is not a separate login field.
    DJANGO_ADMIN_EMAIL     Login identifier (USERNAME_FIELD).
    DJANGO_ADMIN_PASSWORD  Never logged, printed, or included in any
                           exception message raised by this command.

Idempotency: if a user with DJANGO_ADMIN_EMAIL already exists and is
already a full admin (is_staff + is_superuser + role=ADMIN), this command
does nothing and exits 0 -- safe to run on every deployment. If an account
with that email exists but is NOT already an admin, this command refuses
to silently escalate it and fails instead (see users/permissions.py and
analytics/permissions.py: this project's own RBAC checks the `role` field,
not just Django's is_staff/is_superuser, so both must be set together --
exactly what User.objects.create_superuser() below already does correctly).

Usage:
    python manage.py bootstrap_admin
"""

from __future__ import annotations

import os

from django.core.management.base import BaseCommand, CommandError

from users.models import User

REQUIRED_ENV_VARS = ("DJANGO_ADMIN_USERNAME", "DJANGO_ADMIN_EMAIL", "DJANGO_ADMIN_PASSWORD")


class Command(BaseCommand):
    help = (
        "Create the first admin/superuser account from "
        "DJANGO_ADMIN_USERNAME / DJANGO_ADMIN_EMAIL / DJANGO_ADMIN_PASSWORD "
        "environment variables. Idempotent: safe to run on every deploy."
    )

    def handle(self, *args, **options) -> None:
        missing = [name for name in REQUIRED_ENV_VARS if not os.getenv(name)]
        if missing:
            # Never include env var *values* here -- only names. This branch
            # is reached before the password variable is ever read into a
            # local variable below.
            raise CommandError(
                "bootstrap_admin: missing required environment variable(s): "
                f"{', '.join(missing)}. Set all of {', '.join(REQUIRED_ENV_VARS)} "
                "and re-run."
            )

        display_name = os.environ["DJANGO_ADMIN_USERNAME"]
        email = User.objects.normalize_email(os.environ["DJANGO_ADMIN_EMAIL"])
        password = os.environ["DJANGO_ADMIN_PASSWORD"]

        existing = User.objects.filter(email__iexact=email).first()
        if existing is not None:
            if existing.is_staff and existing.is_superuser and existing.role == User.Role.ADMIN:
                self.stdout.write(
                    self.style.SUCCESS(f"bootstrap_admin: admin '{email}' already exists -- skipping.")
                )
                return
            raise CommandError(
                f"bootstrap_admin: an account for '{email}' already exists but is not "
                "already a full admin (is_staff/is_superuser/role=ADMIN). Refusing to "
                "silently change an existing account's permissions -- resolve this "
                "manually via the Django admin if that's actually intended."
            )

        User.objects.create_superuser(
            email=email,
            password=password,
            first_name=display_name,
            last_name="Admin",
        )
        # Deliberately no reference to `password` past this point.
        self.stdout.write(self.style.SUCCESS(f"bootstrap_admin: created admin account for '{email}'."))
