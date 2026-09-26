"""
FoodGuard AI — users app test suite.

23 tests covering:
  - Model / manager behaviour
  - Registration endpoint
  - Login endpoint
  - JWT tokens
  - Profile endpoint
  - Logout + blacklist
  - Security invariants (no password in response, role protection)
"""

from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from users.models import User


# ======================================================================
# Helpers
# ======================================================================

def make_user(**kwargs) -> User:
    """Create a CUSTOMER user for testing."""
    defaults = {
        "email": "test@example.com",
        "password": "StrongPass99!",
        "first_name": "Test",
        "last_name": "User",
        "phone": "9999999999",
        "preferred_language": User.Language.ENGLISH,
    }
    defaults.update(kwargs)
    return User.objects.create_user(**defaults)


REGISTER_URL = "/api/v1/auth/register/"
LOGIN_URL = "/api/v1/auth/login/"
REFRESH_URL = "/api/v1/auth/token/refresh/"
PROFILE_URL = "/api/v1/auth/profile/"
LOGOUT_URL = "/api/v1/auth/logout/"

VALID_PAYLOAD = {
    "email": "new@example.com",
    "password": "StrongPass99!",
    "first_name": "Jane",
    "last_name": "Doe",
    "phone": "9876543210",
    "preferred_language": "en",
}


# ======================================================================
# 1. User creation
# ======================================================================

class TestUserCreation(APITestCase):

    def test_01_user_creation(self):
        """Manager creates a user with correct attributes."""
        user = make_user()
        self.assertEqual(user.email, "test@example.com")
        self.assertEqual(user.first_name, "Test")
        self.assertTrue(user.is_active)

    # ------------------------------------------------------------------
    # 2. Email uniqueness
    # ------------------------------------------------------------------

    def test_02_email_uniqueness(self):
        """Two users with the same email are not allowed at the DB level."""
        make_user()
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            User.objects.create_user(
                email="test@example.com",
                password="AnotherPass99!",
                first_name="Other",
                last_name="User",
            )

    # ------------------------------------------------------------------
    # 3. Password hashing
    # ------------------------------------------------------------------

    def test_03_password_is_hashed(self):
        """Raw password must never be stored in the database."""
        user = make_user()
        self.assertNotEqual(user.password, "StrongPass99!")
        self.assertTrue(user.password.startswith("pbkdf2_") or
                        user.password.startswith("bcrypt") or
                        user.password.startswith("argon2") or
                        "$" in user.password)
        self.assertTrue(user.check_password("StrongPass99!"))

    # ------------------------------------------------------------------
    # 4. create_user
    # ------------------------------------------------------------------

    def test_04_create_user_defaults(self):
        """create_user sets is_staff=False and is_superuser=False."""
        user = make_user(email="a@example.com")
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    # ------------------------------------------------------------------
    # 5. create_superuser
    # ------------------------------------------------------------------

    def test_05_create_superuser(self):
        """create_superuser sets is_staff=True, is_superuser=True, role=ADMIN."""
        su = User.objects.create_superuser(
            email="admin@example.com",
            password="AdminPass99!",
            first_name="Admin",
            last_name="User",
        )
        self.assertTrue(su.is_staff)
        self.assertTrue(su.is_superuser)
        self.assertEqual(su.role, User.Role.ADMIN)

    # ------------------------------------------------------------------
    # 6. Default CUSTOMER role
    # ------------------------------------------------------------------

    def test_06_default_role_is_customer(self):
        """Users created via create_user always start as CUSTOMER."""
        user = make_user(email="b@example.com")
        self.assertEqual(user.role, User.Role.CUSTOMER)


# ======================================================================
# Registration endpoint tests
# ======================================================================

class TestRegistration(APITestCase):

    def setUp(self):
        # /auth/register/ is throttle-scoped (see users.views.RegisterView).
        # DRF's throttle cache persists across test methods within a run
        # (it's a plain Django cache, not reset by APITestCase), so without
        # clearing it here this class's own repeated real HTTP calls to the
        # same endpoint would eventually trip the rate limit and fail with
        # 429 instead of the assertion each test actually intends to check.
        cache.clear()

    # ------------------------------------------------------------------
    # 7. Public registration
    # ------------------------------------------------------------------

    def test_07_public_registration_succeeds(self):
        """Valid payload returns 201 with expected fields."""
        response = self.client.post(REGISTER_URL, VALID_PAYLOAD, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertEqual(data["email"], "new@example.com")
        self.assertEqual(data["role"], User.Role.CUSTOMER)
        self.assertIn("id", data)
        self.assertIn("date_joined", data)

    # ------------------------------------------------------------------
    # 8. Duplicate email
    # ------------------------------------------------------------------

    def test_08_duplicate_email_rejected(self):
        """Registering with an already-used email returns 400."""
        self.client.post(REGISTER_URL, VALID_PAYLOAD, format="json")
        response = self.client.post(REGISTER_URL, VALID_PAYLOAD, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ------------------------------------------------------------------
    # 9. Invalid (weak) password
    # ------------------------------------------------------------------

    def test_09_weak_password_rejected(self):
        """Passwords that fail Django validators return 400."""
        payload = {**VALID_PAYLOAD, "email": "weak@example.com", "password": "123"}
        response = self.client.post(REGISTER_URL, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ------------------------------------------------------------------
    # 10. Language validation
    # ------------------------------------------------------------------

    def test_10_invalid_language_rejected(self):
        """Unsupported language code returns 400."""
        payload = {**VALID_PAYLOAD, "email": "lang@example.com",
                   "preferred_language": "xx"}
        response = self.client.post(REGISTER_URL, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_10b_valid_language_accepted(self):
        """Each supported language code is accepted."""
        for i, code in enumerate(["en", "te", "hi", "ta", "kn", "mr"]):
            payload = {
                **VALID_PAYLOAD,
                "email": f"lang{i}@example.com",
                "preferred_language": code,
            }
            response = self.client.post(REGISTER_URL, payload, format="json")
            self.assertEqual(
                response.status_code, status.HTTP_201_CREATED,
                msg=f"Language '{code}' should be accepted.",
            )

    # ------------------------------------------------------------------
    # 11. Cannot register as ADMIN
    # ------------------------------------------------------------------

    def test_11_cannot_register_as_admin(self):
        """Supplying role=ADMIN in registration payload is ignored — role stays CUSTOMER."""
        payload = {**VALID_PAYLOAD, "email": "admin2@example.com",
                   "role": User.Role.ADMIN}
        response = self.client.post(REGISTER_URL, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json()["role"], User.Role.CUSTOMER)

    # ------------------------------------------------------------------
    # 12. Cannot register as REVIEWER
    # ------------------------------------------------------------------

    def test_12_cannot_register_as_reviewer(self):
        """Supplying role=REVIEWER in registration payload is ignored."""
        payload = {**VALID_PAYLOAD, "email": "reviewer@example.com",
                   "role": User.Role.REVIEWER}
        response = self.client.post(REGISTER_URL, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json()["role"], User.Role.CUSTOMER)

    # ------------------------------------------------------------------
    # 13. Cannot register as RESTAURANT_USER
    # ------------------------------------------------------------------

    def test_13_cannot_register_as_restaurant_user(self):
        """Supplying role=RESTAURANT_USER in registration payload is ignored."""
        payload = {**VALID_PAYLOAD, "email": "resto@example.com",
                   "role": User.Role.RESTAURANT_USER}
        response = self.client.post(REGISTER_URL, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json()["role"], User.Role.CUSTOMER)


# ======================================================================
# Login endpoint tests
# ======================================================================

class TestLogin(APITestCase):

    def setUp(self):
        cache.clear()  # see TestRegistration.setUp — same throttle-cache reason
        self.user = make_user()

    # ------------------------------------------------------------------
    # 14. Successful login
    # ------------------------------------------------------------------

    def test_14_successful_login(self):
        """Valid credentials return 200 with access + refresh tokens."""
        response = self.client.post(
            LOGIN_URL,
            {"email": "test@example.com", "password": "StrongPass99!"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn("access", data)
        self.assertIn("refresh", data)

    # ------------------------------------------------------------------
    # 15. Invalid login
    # ------------------------------------------------------------------

    def test_15_invalid_login_returns_401(self):
        """Wrong password returns HTTP 401."""
        response = self.client.post(
            LOGIN_URL,
            {"email": "test@example.com", "password": "WrongPassword!"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # ------------------------------------------------------------------
    # 16. JWT access token
    # ------------------------------------------------------------------

    def test_16_access_token_in_login_response(self):
        """Login response contains a non-empty access token string."""
        response = self.client.post(
            LOGIN_URL,
            {"email": "test@example.com", "password": "StrongPass99!"},
            format="json",
        )
        access = response.json().get("access", "")
        self.assertTrue(len(access) > 20)

    # ------------------------------------------------------------------
    # 17. JWT refresh token
    # ------------------------------------------------------------------

    def test_17_refresh_token_in_login_response(self):
        """Login response contains a non-empty refresh token string."""
        response = self.client.post(
            LOGIN_URL,
            {"email": "test@example.com", "password": "StrongPass99!"},
            format="json",
        )
        refresh = response.json().get("refresh", "")
        self.assertTrue(len(refresh) > 20)


# ======================================================================
# Profile endpoint tests
# ======================================================================

class TestProfile(APITestCase):

    def setUp(self):
        self.user = make_user()
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)

    # ------------------------------------------------------------------
    # 18. Profile requires authentication
    # ------------------------------------------------------------------

    def test_18_profile_requires_authentication(self):
        """Profile endpoint without token returns 401."""
        response = self.client.get(PROFILE_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # ------------------------------------------------------------------
    # 22. Unauthenticated profile returns 401 (explicit alias)
    # ------------------------------------------------------------------

    def test_22_unauthenticated_profile_returns_401(self):
        """Duplicate explicit check — no token = 401."""
        response = self.client.get(PROFILE_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # ------------------------------------------------------------------
    # 19. Profile response structure
    # ------------------------------------------------------------------

    def test_19_profile_response_structure(self):
        """Authenticated profile returns all required fields."""
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.access_token}"
        )
        response = self.client.get(PROFILE_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        for field in [
            "id", "email", "first_name", "last_name", "phone",
            "role", "preferred_language", "is_active",
            "date_joined", "updated_at",
        ]:
            self.assertIn(field, data, msg=f"Field '{field}' missing from profile.")

    # ------------------------------------------------------------------
    # 23. Password never appears in API response
    # ------------------------------------------------------------------

    def test_23_password_never_in_profile_response(self):
        """Profile response must not contain password or hash."""
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.access_token}"
        )
        response = self.client.get(PROFILE_URL)
        data = response.json()
        self.assertNotIn("password", data)
        self.assertNotIn("password_hash", data)
        # Also verify the registration response never leaks password
        reg_response = self.client.post(
            REGISTER_URL,
            {
                "email": "nopwd@example.com",
                "password": "StrongPass99!",
                "first_name": "No",
                "last_name": "Pwd",
                "preferred_language": "en",
            },
            format="json",
        )
        reg_data = reg_response.json()
        self.assertNotIn("password", reg_data)


# ======================================================================
# Logout + blacklist tests
# ======================================================================

class TestLogout(APITestCase):

    def setUp(self):
        self.user = make_user(email="logout@example.com")
        self.refresh_obj = RefreshToken.for_user(self.user)
        self.access_token = str(self.refresh_obj.access_token)
        self.refresh_token = str(self.refresh_obj)

    # ------------------------------------------------------------------
    # 20. Logout succeeds
    # ------------------------------------------------------------------

    def test_20_logout_succeeds(self):
        """Authenticated logout with valid refresh token returns 200."""
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.access_token}"
        )
        response = self.client.post(
            LOGOUT_URL, {"refresh": self.refresh_token}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # ------------------------------------------------------------------
    # 21. Refresh token is blacklisted after logout
    # ------------------------------------------------------------------

    def test_21_refresh_token_blacklisted_after_logout(self):
        """Using a blacklisted refresh token returns 401."""
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.access_token}"
        )
        # Logout — blacklists the token
        self.client.post(
            LOGOUT_URL, {"refresh": self.refresh_token}, format="json"
        )
        # Attempt to refresh with the now-blacklisted token
        response = self.client.post(
            REFRESH_URL, {"refresh": self.refresh_token}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
