import os
import sys
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlsplit

import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR.parent))
load_dotenv(BASE_DIR / ".env")
FACE_WORKER_NODE_ID = os.getenv("FACE_WORKER_NODE_ID") or "legacy"
if not FACE_WORKER_NODE_ID or len(FACE_WORKER_NODE_ID) > 100:
    raise RuntimeError("FACE_WORKER_NODE_ID must contain 1–100 characters.")
FACE_MATCH_THRESHOLD = float(os.getenv("FACE_MATCH_THRESHOLD", "0.50"))
FACE_SEARCH_TIMEOUT_MINUTES = int(os.getenv("FACE_SEARCH_TIMEOUT_MINUTES", "120"))
if not 10 <= FACE_SEARCH_TIMEOUT_MINUTES <= 360:
    raise RuntimeError("FACE_SEARCH_TIMEOUT_MINUTES must be between 10 and 360.")
if not 0.363 <= FACE_MATCH_THRESHOLD <= 0.95:
    raise RuntimeError("FACE_MATCH_THRESHOLD must be between 0.363 and 0.95.")
DEBUG = os.getenv("DJANGO_DEBUG", "false").lower() == "true"
SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]
ALLOWED_HOSTS = os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,testserver").split(",")
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "apps.accounts",
    "apps.community",
    "apps.face_search",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "config.middleware.private_api_responses",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF = "config.urls"
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
            ]
        },
    }
]
WSGI_APPLICATION = "config.wsgi.application"
database_url = os.getenv("DATABASE_URL", "")
if database_url:
    DATABASES = {"default": dj_database_url.parse(database_url, conn_max_age=0)}
    if not DATABASES["default"]["ENGINE"].endswith("postgresql"):
        raise RuntimeError("DATABASE_URL must use PostgreSQL.")
    DATABASES["default"]["DISABLE_SERVER_SIDE_CURSORS"] = True
    DATABASES["default"].setdefault("OPTIONS", {})["connect_timeout"] = 15
    if ".neon.tech" in DATABASES["default"].get("HOST", ""):
        DATABASES["default"]["OPTIONS"].setdefault("sslmode", "require")
    if not DEBUG:
        options = DATABASES["default"]["OPTIONS"]
        if options.setdefault("sslmode", "require") not in {"require", "verify-ca", "verify-full"}:
            raise RuntimeError("Production requires a TLS connection to PostgreSQL.")
elif DEBUG:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": os.getenv("SQLITE_DATABASE_PATH") or str(BASE_DIR / "db.sqlite3"),
            "OPTIONS": {"timeout": 30, "transaction_mode": "IMMEDIATE"},
        }
    }
else:
    raise RuntimeError("Production requires a PostgreSQL DATABASE_URL.")
AUTH_USER_MODEL = "accounts.User"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 12},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
LANGUAGE_CODE = "en-in"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
COLLEGE_DOMAIN = "sait.ac.in"
PRIVACY_VERSION = "2026-11-17"
TERMS_VERSION = "2026-11-17"
MAIN_ADMIN_EMAIL = "pixel.club@sait.ac.in"
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:8081").rstrip("/")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
CORS_ALLOWED_ORIGINS = os.getenv("CORS_ALLOWED_ORIGINS", FRONTEND_URL).split(",")
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = CORS_ALLOWED_ORIGINS
CSRF_FAILURE_VIEW = "config.views.csrf_failure"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
REFRESH_COOKIE_SECURE = not DEBUG
SECURE_SSL_REDIRECT = not DEBUG
SECURE_HSTS_SECONDS = 0 if DEBUG else 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = os.getenv("DJANGO_HSTS_INCLUDE_SUBDOMAINS") == "true"
SECURE_HSTS_PRELOAD = os.getenv("DJANGO_HSTS_PRELOAD") == "true"
if not DEBUG and os.getenv("DJANGO_TRUST_HTTPS_PROXY") == "true":
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
DATA_UPLOAD_MAX_MEMORY_SIZE = 64 * 1024
cache_url = os.getenv("PIXEL_CACHE_URL", "")
if cache_url:
    if urlsplit(cache_url).scheme not in {"redis", "rediss"}:
        raise RuntimeError("PIXEL_CACHE_URL must be a Redis URL.")
    CACHES = {
        "default": {"BACKEND": "django.core.cache.backends.redis.RedisCache", "LOCATION": cache_url}
    }
EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND",
    "django.core.mail.backends.filebased.EmailBackend"
    if DEBUG
    else "django.core.mail.backends.smtp.EmailBackend",
)
EMAIL_FILE_PATH = BASE_DIR / ".local" / "emails"
EMAIL_HOST = os.getenv("EMAIL_HOST", "")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "true").lower() == "true"
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_TIMEOUT = 10
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "PIXEL <pixel.club@sait.ac.in>")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = BACKEND_URL + "/api/v1/auth/google/callback/"
OAUTH_APP_REDIRECTS = {
    "web": FRONTEND_URL + "/auth/callback",
    "native": "pixelmobile://auth/callback",
}
REST_FRAMEWORK = {
    "NUM_PROXIES": int(os.getenv("DJANGO_TRUSTED_PROXY_COUNT", "0")),
    "EXCEPTION_HANDLER": "config.api_errors.user_facing_exception_handler",
    "DEFAULT_AUTHENTICATION_CLASSES": ["apps.accounts.authentication.SessionJWTAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "3000/hour",
        "user": "3000/hour",
        "media_viewer": "300/minute",
        "auth": "600/minute",
        "email": "60/minute",
        "credential": "10/minute",
        "email_account": "5/hour",
        "search": "60/minute",
        "face_search": "12/hour",
    },
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=5),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ISSUER": "pixel",
    "AUDIENCE": "pixel-app",
    "CHECK_REVOKE_TOKEN": True,
}
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {"redact_oauth": {"()": "config.logging.RedactOAuthQuery"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "filters": ["redact_oauth"]}},
    "loggers": {"django.server": {"handlers": ["console"], "level": "INFO", "propagate": False}},
}
if not DEBUG:
    if (
        len(SECRET_KEY) < 50
        or len(set(SECRET_KEY)) < 5
        or SECRET_KEY.startswith("django-insecure-")
    ):
        raise RuntimeError("Production requires a strong random Django secret.")
    if (
        not EMAIL_HOST
        or EMAIL_BACKEND != "django.core.mail.backends.smtp.EmailBackend"
        or not EMAIL_USE_TLS
    ):
        raise RuntimeError("Production requires SMTP email delivery over TLS.")
    if not cache_url:
        raise RuntimeError("Production requires a shared Redis cache for rate limits.")
    if not ALLOWED_HOSTS or any(not host or host.startswith((".", "*")) for host in ALLOWED_HOSTS):
        raise RuntimeError("Production requires explicit allowed hostnames.")
    for origin in (FRONTEND_URL, BACKEND_URL, *CORS_ALLOWED_ORIGINS):
        parts = urlsplit(origin)
        if (
            parts.scheme != "https"
            or not parts.hostname
            or parts.username
            or parts.password
            or parts.path
            or parts.query
            or parts.fragment
        ):
            raise RuntimeError("Production requires explicit HTTPS origins.")
