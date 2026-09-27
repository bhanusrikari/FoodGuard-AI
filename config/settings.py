"""
Django settings for config project.

FoodGuard AI Backend
"""

from datetime import timedelta
from pathlib import Path
import os

from django.core.exceptions import ImproperlyConfigured


# ============================================================
# BASE DIRECTORY
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent


# ============================================================
# SECURITY
# ============================================================

_INSECURE_DEFAULT_SECRET_KEY = "django-insecure-foodguard-dev-only-change-in-production"

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", _INSECURE_DEFAULT_SECRET_KEY)

DEBUG = os.getenv("DJANGO_DEBUG", "True").lower() == "true"

if not DEBUG and SECRET_KEY == _INSECURE_DEFAULT_SECRET_KEY:
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY must be set to a real secret when DJANGO_DEBUG=False. "
        "Refusing to start with the insecure development default in production."
    )

_default_allowed_hosts = "127.0.0.1,localhost"
ALLOWED_HOSTS = [
    h.strip()
    for h in os.getenv("DJANGO_ALLOWED_HOSTS", _default_allowed_hosts).split(",")
    if h.strip()
]

# Production-only hardening. Left off under DEBUG so the local dev workflow
# (plain HTTP on localhost) is completely unaffected.
if not DEBUG:
    SECURE_SSL_REDIRECT = os.getenv("DJANGO_SECURE_SSL_REDIRECT", "True").lower() == "true"
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = int(os.getenv("DJANGO_SECURE_HSTS_SECONDS", "31536000"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    CSRF_TRUSTED_ORIGINS = [
        o.strip() for o in os.getenv("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()
    ]

# Safe under HTTP too — always on.
SECURE_CONTENT_TYPE_NOSNIFF = True

# Defense-in-depth above the 5 MB app-level check in food_reports.services.validate_report_image.
DATA_UPLOAD_MAX_MEMORY_SIZE = 6 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 6 * 1024 * 1024


# ============================================================
# APPLICATIONS
# ============================================================

INSTALLED_APPS = [
    # Django apps
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Third-party apps
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "drf_spectacular",

    # FoodGuard apps
    "users",
    "restaurants",
    "food_reports",
    "ai_analysis",
    "complaints",
    "escalation",
    "feedback",
    "translation",
    "notifications",
    "analytics",
]


# ============================================================
# CUSTOM USER MODEL
# ============================================================

AUTH_USER_MODEL = "users.User"


# ============================================================
# MIDDLEWARE
# ============================================================

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",

    # CORS — must be as high as possible
    "corsheaders.middleware.CorsMiddleware",

    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


# ============================================================
# URL CONFIGURATION
# ============================================================

ROOT_URLCONF = "config.urls"


# ============================================================
# TEMPLATES
# ============================================================

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]


# ============================================================
# WSGI / ASGI
# ============================================================

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"


# ============================================================
# DATABASE — PostgreSQL on port 5434 (FoodGuard isolated instance)
# ============================================================

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DATABASE_NAME", "foodguard_db"),
        "USER": os.getenv("DATABASE_USER", "foodguard_user"),
        "PASSWORD": os.getenv("DATABASE_PASSWORD", "foodguard_password"),
        "HOST": os.getenv("DATABASE_HOST", "127.0.0.1"),
        "PORT": os.getenv("DATABASE_PORT", "5434"),
    }
}


# ============================================================
# PASSWORD VALIDATION
# ============================================================

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation"
            ".UserAttributeSimilarityValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation"
            ".MinimumLengthValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation"
            ".CommonPasswordValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation"
            ".NumericPasswordValidator"
        ),
    },
]


# ============================================================
# INTERNATIONALIZATION
# ============================================================

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True


# ============================================================
# STATIC FILES
# ============================================================

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"


# ============================================================
# MEDIA FILES
# ============================================================

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Django's static() helper (wired up in config/urls.py) is not efficient at
# real scale, but for this MVP — no reverse proxy or object storage in
# front of the container yet — it is the minimum needed to make uploaded
# report images reachable at all outside DEBUG. Set this to False once
# nginx / a CDN / object storage takes over serving MEDIA_URL directly, per
# the Dockerfile's deployment notes.
SERVE_MEDIA_VIA_DJANGO = os.getenv("SERVE_MEDIA_VIA_DJANGO", "True").lower() == "true"


# ============================================================
# DJANGO REST FRAMEWORK
# ============================================================

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.ScopedRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        # Applied only to views that opt in via `throttle_scope` (auth login/register).
        # Unscoped views are unaffected — DRF only throttles a view when its
        # throttle class's scope is set and a matching rate exists here.
        "auth_anon": "10/min",
    },
}

SPECTACULAR_SETTINGS = {
    "TITLE": "FoodGuard AI API",
    "DESCRIPTION": (
        "Food safety reporting, complaint management, and preliminary AI visual "
        "assessment API. AI results are preliminary visual assessments only — "
        "not a scientific food-safety certification."
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}


# ============================================================
# SIMPLE JWT
# ============================================================

SIMPLE_JWT = {
    # Token lifetimes
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),

    # Rotation and blacklisting
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,

    # Algorithm
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,

    # Header
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",

    # Token claims
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",

    # Token classes
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
    "TOKEN_TYPE_CLAIM": "token_type",
    "TOKEN_USER_CLASS": "rest_framework_simplejwt.models.TokenUser",
}


# ============================================================
# CORS
# ============================================================

CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]


# ============================================================
# AI ANALYSIS — food-quality model configuration
# ============================================================
# Model artifacts (model.pt / label_map.json / train_config.json) are never
# committed to the repo (see .gitignore) and may not exist on every machine —
# ai_analysis falls back to the mock implementation when they're absent.

FOOD_QUALITY_MODEL_DIR = Path(
    os.getenv("FOOD_QUALITY_MODEL_DIR", str(BASE_DIR / "models" / "food_quality"))
)

# Below this confidence, AI results are forced to HUMAN_REVIEW regardless of
# the predicted class. 0.70 is the value already validated when this model
# was trained; not changed here.
AI_CONFIDENCE_THRESHOLD = float(os.getenv("AI_CONFIDENCE_THRESHOLD", "0.70"))


# ============================================================
# TRANSLATION SERVICE
# ============================================================
# Provider abstraction only — "none" (the default) means TranslationService
# always returns an explicit "unavailable" result rather than fabricating a
# translation. Set to a real provider name once one is actually configured.

TRANSLATION_PROVIDER = os.getenv("TRANSLATION_PROVIDER", "none")


# ============================================================
# LOGGING
# ============================================================

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": os.getenv("DJANGO_LOG_LEVEL", "INFO"),
            "propagate": False,
        },
        "foodguard": {
            "handlers": ["console"],
            "level": os.getenv("FOODGUARD_LOG_LEVEL", "INFO"),
            "propagate": False,
        },
    },
}


# ============================================================
# DEFAULT PRIMARY KEY
# ============================================================

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
