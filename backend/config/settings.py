import os
from datetime import timedelta
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

BASE_DIR = Path(__file__).resolve().parent.parent


def _running_in_docker() -> bool:
    return os.path.exists("/.dockerenv") or os.environ.get("DOCKER_CONTAINER") == "1"


def _rewrite_docker_url(url: str | None, *, local_default: str) -> str:
    """Replace Docker Compose hostnames when running manage.py on the host OS."""
    if not url:
        return local_default
    if _running_in_docker():
        return url
    if "@db:" in url or "@redis:" in url:
        override = os.environ.get("LOCAL_DATABASE_URL") if "postgres" in url else os.environ.get(
            "LOCAL_REDIS_URL"
        )
        if override:
            return override
        if "postgres" in url:
            return local_default
        return url.replace("@redis:", "@127.0.0.1:")
    return url


_SQLITE_URL = f"sqlite:///{BASE_DIR / 'db.sqlite3'}"
_database_url = _rewrite_docker_url(os.environ.get("DATABASE_URL"), local_default=_SQLITE_URL)

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-insecure-change-me")
DEBUG = os.environ.get("DEBUG", "True").lower() in ("1", "true", "yes")
ALLOWED_HOSTS = [h.strip() for h in os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")]
if DEBUG:
    ALLOWED_HOSTS.append("testserver")

DISTRICT_NAME = os.environ.get("DISTRICT_NAME", "LibreGrades District")
EXTENSIONS_ENCRYPTION_KEY = os.environ.get("EXTENSIONS_ENCRYPTION_KEY", "")

try:
    import whitenoise  # noqa: F401

    _USE_WHITENOISE = True
except ImportError:
    _USE_WHITENOISE = False

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "drf_spectacular",
    "apps.core",
    "apps.accounts",
    "apps.students",
    "apps.medical",
    "apps.emergency",
    "apps.scheduling",
    "apps.grades",
    "apps.credits",
    "apps.attendance",
    "apps.behavior",
    "apps.notifications",
    "apps.communications",
    "apps.extensions",
    "apps.portal",
    "social_django",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    *(
        ["whitenoise.middleware.WhiteNoiseMiddleware"]
        if _USE_WHITENOISE
        else []
    ),
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.portal.middleware.StaffTwoFactorMiddleware",
    "apps.extensions.middleware.PortalPreferencesMiddleware",
    "apps.extensions.middleware.SessionTrackingMiddleware",
    "apps.extensions.middleware.AdminIPAllowlistMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.portal.context_processors.portal_context",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": dj_database_url.parse(_database_url, conn_max_age=600),
}

AUTH_USER_MODEL = "accounts.User"

AUTHENTICATION_BACKENDS = (
    "social_core.backends.google.GoogleOAuth2",
    "social_core.backends.microsoft.MicrosoftOAuth2",
    "django.contrib.auth.backends.ModelBackend",
)

SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = os.environ.get("GOOGLE_OAUTH2_KEY", "")
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = os.environ.get("GOOGLE_OAUTH2_SECRET", "")
SOCIAL_AUTH_MICROSOFT_GRAPH_KEY = os.environ.get("MICROSOFT_OAUTH2_KEY", "")
SOCIAL_AUTH_MICROSOFT_GRAPH_SECRET = os.environ.get("MICROSOFT_OAUTH2_SECRET", "")
SOCIAL_AUTH_LOGIN_REDIRECT_URL = "/"
SOCIAL_AUTH_LOGIN_ERROR_URL = "/login/"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "America/Los_Angeles"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
if _USE_WHITENOISE:
    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
        },
    }
    WHITENOISE_USE_FINDERS = not _running_in_docker()
elif not DEBUG and _database_url.startswith("sqlite") and not _running_in_docker():
    # Local runserver without whitenoise: allow admin CSS via Django staticfiles
    DEBUG = True

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "portal:login"
LOGIN_REDIRECT_URL = "portal:dashboard"
LOGOUT_REDIRECT_URL = "portal:login"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=int(os.environ.get("JWT_ACCESS_MINUTES", 60))),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=int(os.environ.get("JWT_REFRESH_DAYS", 7))),
    "ROTATE_REFRESH_TOKENS": True,
}

SPECTACULAR_SETTINGS = {
    "TITLE": "LibreGrades API",
    "DESCRIPTION": "Self-hosted student information system API",
    "VERSION": "1.0.0",
}

CORS_ALLOW_ALL_ORIGINS = DEBUG

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.environ.get("SMTP_HOST", "localhost")
EMAIL_PORT = int(os.environ.get("SMTP_PORT", "587"))
EMAIL_HOST_USER = os.environ.get("SMTP_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "True").lower() in ("1", "true", "yes")
DEFAULT_FROM_EMAIL = os.environ.get("SMTP_FROM", "libregrades@localhost")

CELERY_BROKER_URL = _rewrite_docker_url(
    os.environ.get("CELERY_BROKER_URL", "redis://127.0.0.1:6379/0"),
    local_default="redis://127.0.0.1:6379/0",
)
CELERY_RESULT_BACKEND = CELERY_BROKER_URL
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULE = {
    "check-missing-assignments": {
        "task": "apps.notifications.tasks.check_missing_assignments",
        "schedule": timedelta(hours=24),
    },
    "weekly-digest": {
        "task": "apps.extensions.tasks_advanced.send_weekly_parent_digests",
        "schedule": timedelta(days=7),
    },
}
