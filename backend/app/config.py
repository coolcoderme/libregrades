import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

BASE_DIR = Path(__file__).resolve().parent.parent


def _running_in_docker():
    return os.path.exists("/.dockerenv") or os.environ.get("DOCKER_CONTAINER") == "1"


def _rewrite_docker_url(url, local_default):
    if not url:
        return local_default
    if _running_in_docker():
        return url
    if "@db:" in url or "@redis:" in url:
        override = os.environ.get("LOCAL_DATABASE_URL") if "postgres" in url else None
        if override:
            return override
        if "postgres" in url:
            return local_default
    return url


_sqlite = f"sqlite:///{BASE_DIR / 'libregrades.db'}"
_db_url = _rewrite_docker_url(os.environ.get("DATABASE_URL"), _sqlite)


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-insecure-change-me")
    DEBUG = os.environ.get("DEBUG", "True").lower() in ("1", "true", "yes")
    DISTRICT_NAME = os.environ.get("DISTRICT_NAME", "LibreGrades District")

    SQLALCHEMY_DATABASE_URI = _db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", SECRET_KEY)
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=int(os.environ.get("JWT_ACCESS_MINUTES", 60)))
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=int(os.environ.get("JWT_REFRESH_DAYS", 7)))

    UPLOAD_FOLDER = str(BASE_DIR / "media")
    PROFILE_UPLOAD_FOLDER = str(BASE_DIR / "media" / "profiles")
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024
    ALLOWED_PROFILE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

    WTF_CSRF_ENABLED = True

    CELERY_BROKER_URL = _rewrite_docker_url(
        os.environ.get("CELERY_BROKER_URL", "redis://127.0.0.1:6379/0"),
        "redis://127.0.0.1:6379/0",
    )
    CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", CELERY_BROKER_URL)
    CELERY_TIMEZONE = os.environ.get("CELERY_TIMEZONE", "UTC")

    SMTP_HOST = os.environ.get("SMTP_HOST", "localhost")
    SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
    SMTP_USER = os.environ.get("SMTP_USER", "")
    SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
    SMTP_FROM = os.environ.get("SMTP_FROM", "libregrades@localhost")
    SMTP_USE_TLS = os.environ.get("SMTP_USE_TLS", "True").lower() in ("1", "true", "yes")
