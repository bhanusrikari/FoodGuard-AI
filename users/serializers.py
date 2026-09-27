from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from users.models import User


class RegisterSerializer(serializers.ModelSerializer):
    """
    Public registration serializer.

    - Accepts only the fields listed in `fields`.
    - role, is_staff, and is_superuser are NEVER accepted from the client.
    - Always creates a CUSTOMER.
    - Returns the safe subset (no password / hash).
    """

    password = serializers.CharField(
        write_only=True,
        required=True,
        style={"input_type": "password"},
    )

    class Meta:
        model = User
        fields = [
            "email",
            "password",
            "first_name",
            "last_name",
            "phone",
            "preferred_language",
        ]
        extra_kwargs = {
            "first_name": {"required": True},
            "last_name": {"required": True},
        }

    # ------------------------------------------------------------------
    # Field-level validation
    # ------------------------------------------------------------------

    def validate_email(self, value: str) -> str:
        normalised = value.strip().lower()
        if User.objects.filter(email=normalised).exists():
            raise serializers.ValidationError(
                "A user with this email already exists."
            )
        return normalised

    def validate_password(self, value: str) -> str:
        # Runs all AUTH_PASSWORD_VALIDATORS from settings
        validate_password(value)
        return value

    def validate_preferred_language(self, value: str) -> str:
        valid_codes = [lang[0] for lang in User.Language.choices]
        if value not in valid_codes:
            raise serializers.ValidationError(
                f"'{value}' is not a supported language. "
                f"Choose from: {', '.join(valid_codes)}."
            )
        return value

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    def create(self, validated_data: dict) -> User:
        # role is always CUSTOMER for public registration — never from client
        return User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            first_name=validated_data["first_name"],
            last_name=validated_data["last_name"],
            phone=validated_data.get("phone", ""),
            preferred_language=validated_data.get(
                "preferred_language", User.Language.ENGLISH
            ),
            role=User.Role.CUSTOMER,
        )


class UserResponseSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for returning safe user data.
    Never includes password or password hash.
    """

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "phone",
            "role",
            "preferred_language",
            "is_active",
            "date_joined",
            "updated_at",
        ]
        read_only_fields = fields


class UpdatePreferredLanguageSerializer(serializers.Serializer):
    """
    Validates a `preferred_language` update for the authenticated user.

    Deliberately narrow — this is not a general profile-update endpoint,
    just the one field the frontend's language selector needs to persist
    server-side (see docs/... multilingual architecture notes). Extending
    it to other profile fields is a separate decision, not bundled in here.
    """

    preferred_language = serializers.CharField(required=True)

    def validate_preferred_language(self, value: str) -> str:
        valid_codes = [lang[0] for lang in User.Language.choices]
        if value not in valid_codes:
            raise serializers.ValidationError(
                f"'{value}' is not a supported language. "
                f"Choose from: {', '.join(valid_codes)}."
            )
        return value


class LoginSerializer(serializers.Serializer):
    """
    Validates email + password credentials.
    Returns the authenticated User instance on success.
    """

    email = serializers.EmailField()
    password = serializers.CharField(
        write_only=True,
        style={"input_type": "password"},
    )

    def validate(self, attrs: dict) -> dict:
        email = attrs.get("email", "").strip().lower()
        password = attrs.get("password", "")

        if not email or not password:
            raise serializers.ValidationError(
                "Both email and password are required."
            )

        user = authenticate(
            request=self.context.get("request"),
            username=email,   # Django's authenticate uses USERNAME_FIELD
            password=password,
        )

        if user is None:
            raise serializers.ValidationError(
                "Invalid credentials. Please check your email and password."
            )

        if not user.is_active:
            raise serializers.ValidationError(
                "This account has been deactivated."
            )

        attrs["user"] = user
        return attrs


class LogoutSerializer(serializers.Serializer):
    """Accepts the refresh token to blacklist on logout."""

    refresh = serializers.CharField()
