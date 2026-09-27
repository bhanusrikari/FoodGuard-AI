"""
Tests for `python manage.py bootstrap_admin`
(users/management/commands/bootstrap_admin.py).

Covers: successful first creation, idempotent re-run, missing required
environment variables, and that the password is never present in any
captured command output.
"""

from __future__ import annotations

import io
import os
from contextlib import contextmanager
from unittest import mock

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from users.models import User

_ADMIN_ENV = {
    "DJANGO_ADMIN_USERNAME": "siteadmin",
    "DJANGO_ADMIN_EMAIL": "bootstrap-admin@example.com",
    "DJANGO_ADMIN_PASSWORD": "Sup3rSecret!Password2026",
}


@contextmanager
def _env(overrides: dict[str, str | None]):
    """Context manager that sets/removes exactly the given env vars for the
    duration of the block, restoring the prior environment afterward --
    regardless of what the ambient shell/test runner already has set."""
    with mock.patch.dict(os.environ, {}, clear=False):
        for key, value in overrides.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        yield


class TestBootstrapAdminCreation(TestCase):
    def test_creates_admin_with_correct_permissions(self):
        with _env(_ADMIN_ENV):
            out = io.StringIO()
            call_command("bootstrap_admin", stdout=out)

        user = User.objects.get(email="bootstrap-admin@example.com")
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertEqual(user.role, User.Role.ADMIN)
        self.assertEqual(user.first_name, "siteadmin")
        self.assertTrue(user.check_password("Sup3rSecret!Password2026"))

    def test_created_user_count_is_exactly_one(self):
        with _env(_ADMIN_ENV):
            call_command("bootstrap_admin", stdout=io.StringIO())
        self.assertEqual(User.objects.filter(email="bootstrap-admin@example.com").count(), 1)


class TestBootstrapAdminIdempotency(TestCase):
    def test_second_run_does_not_create_a_duplicate(self):
        with _env(_ADMIN_ENV):
            call_command("bootstrap_admin", stdout=io.StringIO())
            call_command("bootstrap_admin", stdout=io.StringIO())  # must not raise

        self.assertEqual(User.objects.filter(email="bootstrap-admin@example.com").count(), 1)

    def test_second_run_reports_already_exists_and_exits_cleanly(self):
        with _env(_ADMIN_ENV):
            call_command("bootstrap_admin", stdout=io.StringIO())
            out = io.StringIO()
            call_command("bootstrap_admin", stdout=out)  # must not raise
        self.assertIn("already exists", out.getvalue())

    def test_existing_non_admin_account_with_same_email_is_not_escalated(self):
        User.objects.create_user(
            email="bootstrap-admin@example.com",
            password="whatever-not-relevant",
            first_name="Regular",
            last_name="Customer",
        )
        with _env(_ADMIN_ENV):
            with self.assertRaises(CommandError):
                call_command("bootstrap_admin", stdout=io.StringIO())

        user = User.objects.get(email="bootstrap-admin@example.com")
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)


class TestBootstrapAdminMissingEnvVars(TestCase):
    def test_missing_username_fails_clearly(self):
        with _env({**_ADMIN_ENV, "DJANGO_ADMIN_USERNAME": None}):
            with self.assertRaises(CommandError) as ctx:
                call_command("bootstrap_admin", stdout=io.StringIO())
        self.assertIn("DJANGO_ADMIN_USERNAME", str(ctx.exception))
        self.assertEqual(User.objects.count(), 0)

    def test_missing_email_fails_clearly(self):
        with _env({**_ADMIN_ENV, "DJANGO_ADMIN_EMAIL": None}):
            with self.assertRaises(CommandError) as ctx:
                call_command("bootstrap_admin", stdout=io.StringIO())
        self.assertIn("DJANGO_ADMIN_EMAIL", str(ctx.exception))
        self.assertEqual(User.objects.count(), 0)

    def test_missing_password_fails_clearly(self):
        with _env({**_ADMIN_ENV, "DJANGO_ADMIN_PASSWORD": None}):
            with self.assertRaises(CommandError) as ctx:
                call_command("bootstrap_admin", stdout=io.StringIO())
        self.assertIn("DJANGO_ADMIN_PASSWORD", str(ctx.exception))
        self.assertEqual(User.objects.count(), 0)

    def test_all_missing_lists_all_three(self):
        with _env({"DJANGO_ADMIN_USERNAME": None, "DJANGO_ADMIN_EMAIL": None, "DJANGO_ADMIN_PASSWORD": None}):
            with self.assertRaises(CommandError) as ctx:
                call_command("bootstrap_admin", stdout=io.StringIO())
        message = str(ctx.exception)
        for name in ("DJANGO_ADMIN_USERNAME", "DJANGO_ADMIN_EMAIL", "DJANGO_ADMIN_PASSWORD"):
            self.assertIn(name, message)

    def test_blank_string_env_var_counts_as_missing(self):
        with _env({**_ADMIN_ENV, "DJANGO_ADMIN_PASSWORD": ""}):
            with self.assertRaises(CommandError):
                call_command("bootstrap_admin", stdout=io.StringIO())
        self.assertEqual(User.objects.count(), 0)


class TestBootstrapAdminNeverLogsPassword(TestCase):
    def test_password_absent_from_stdout_on_success(self):
        with _env(_ADMIN_ENV):
            out = io.StringIO()
            call_command("bootstrap_admin", stdout=out)
        self.assertNotIn(_ADMIN_ENV["DJANGO_ADMIN_PASSWORD"], out.getvalue())

    def test_password_absent_from_stdout_on_idempotent_rerun(self):
        with _env(_ADMIN_ENV):
            call_command("bootstrap_admin", stdout=io.StringIO())
            out = io.StringIO()
            call_command("bootstrap_admin", stdout=out)
        self.assertNotIn(_ADMIN_ENV["DJANGO_ADMIN_PASSWORD"], out.getvalue())

    def test_password_absent_from_exception_message_on_missing_vars(self):
        with _env({**_ADMIN_ENV, "DJANGO_ADMIN_USERNAME": None}):
            with self.assertRaises(CommandError) as ctx:
                call_command("bootstrap_admin", stdout=io.StringIO())
        self.assertNotIn(_ADMIN_ENV["DJANGO_ADMIN_PASSWORD"], str(ctx.exception))

    def test_password_absent_from_exception_message_on_non_admin_conflict(self):
        User.objects.create_user(
            email="bootstrap-admin@example.com", password="irrelevant", first_name="A", last_name="B",
        )
        with _env(_ADMIN_ENV):
            with self.assertRaises(CommandError) as ctx:
                call_command("bootstrap_admin", stdout=io.StringIO())
        self.assertNotIn(_ADMIN_ENV["DJANGO_ADMIN_PASSWORD"], str(ctx.exception))
