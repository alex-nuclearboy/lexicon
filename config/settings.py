"""
Django settings for the Vocabio project.

The same settings module is used for local development and production.

Environment-specific and sensitive values are loaded from environment
variables. A local .env file is supported for development, while deployment
platform variables take precedence in production.
"""

import os
from datetime import timedelta
from pathlib import Path
from typing import Any

import dj_database_url
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

from .logging import build_logging_config


# ---------------------------------------------------------------------------
# Project paths
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent


# Load local development variables.
#
# Existing system environment variables are not overwritten, so variables
# supplied by Koyeb take precedence over values from a local .env file.
load_dotenv(BASE_DIR / ".env")


# ---------------------------------------------------------------------------
# Environment variable helpers
# ---------------------------------------------------------------------------

TRUE_ENV_VALUES = frozenset(
    {
        "1",
        "true",
        "yes",
        "on",
    }
)

FALSE_ENV_VALUES = frozenset(
    {
        "0",
        "false",
        "no",
        "off",
    }
)


def get_required_env(name: str) -> str:
    """
    Read and validate a required environment variable.

    Empty and whitespace-only values are rejected with a configuration error.
    """
    value = os.getenv(name, "").strip()

    if not value:
        raise ImproperlyConfigured(
            f"{name} is not set. "
            "Add it to the local .env file or deployment environment."
        )

    return value


def get_str_env(name: str, default: str) -> str:
    """
    Read a text environment variable.

    Missing, empty, and whitespace-only values use the default value.
    """
    return os.getenv(name, default).strip() or default


def get_bool_env(name: str, default: bool = False) -> bool:
    """
    Read and validate a Boolean environment variable.

    Common textual Boolean representations are accepted. Invalid values cause
    an explicit configuration error instead of silently becoming false.
    """
    default_value = "true" if default else "false"
    raw_value = os.getenv(name, default_value).strip().lower()

    if raw_value in TRUE_ENV_VALUES:
        return True

    if raw_value in FALSE_ENV_VALUES:
        return False

    raise ImproperlyConfigured(
        f"{name} must be a Boolean value, got {raw_value!r}."
    )


def get_int_env(name: str, default: int) -> int:
    """
    Read and validate a non-negative integer environment variable.

    The default value is used when the variable is absent. Invalid or negative
    values cause an explicit configuration error.
    """
    raw_value = os.getenv(name, str(default)).strip()

    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ImproperlyConfigured(
            f"{name} must be an integer, got {raw_value!r}."
        ) from exc

    if value < 0:
        raise ImproperlyConfigured(
            f"{name} must not be negative."
        )

    return value


def build_database_config(
    database_url: str,
    conn_max_age: int,
    connect_timeout: int,
) -> dict[str, Any]:
    """
    Build and validate the Django PostgreSQL configuration.

    The database URL is parsed into Django's configuration format. PostgreSQL
    usage, required connection values, connection timeout, health checks, and
    Neon pooled-connection compatibility are configured here.
    """
    try:
        database_config = dj_database_url.parse(
            database_url,
            conn_max_age=conn_max_age,
            conn_health_checks=conn_max_age > 0,
        )
    except (TypeError, ValueError) as exc:
        raise ImproperlyConfigured(
            "DATABASE_URL has an invalid format."
        ) from exc

    if database_config.get("ENGINE") != "django.db.backends.postgresql":
        raise ImproperlyConfigured(
            "DATABASE_URL must use PostgreSQL."
        )

    required_values = {
        "NAME": "database name",
        "USER": "database user",
        "PASSWORD": "database password",
        "HOST": "database host",
    }

    missing_values = [
        description
        for key, description in required_values.items()
        if not database_config.get(key)
    ]

    if missing_values:
        missing = ", ".join(missing_values)

        raise ImproperlyConfigured(
            f"DATABASE_URL is missing: {missing}."
        )

    database_options = database_config.get("OPTIONS") or {}

    # Keep an explicitly configured timeout from DATABASE_URL. Otherwise,
    # apply the timeout supplied through DATABASE_CONNECT_TIMEOUT.
    database_options.setdefault(
        "connect_timeout",
        connect_timeout,
    )

    database_config["OPTIONS"] = database_options

    # Neon pooled connection hosts contain "-pooler". Transaction pooling is
    # incompatible with PostgreSQL server-side cursors, so Django must disable
    # them for pooled connections.
    database_config["DISABLE_SERVER_SIDE_CURSORS"] = (
        "-pooler" in str(database_config.get("HOST", ""))
    )

    return database_config


# ---------------------------------------------------------------------------
# Core security settings
# ---------------------------------------------------------------------------

# A missing secret key is treated as a configuration error.
SECRET_KEY = get_required_env("DJANGO_SECRET_KEY")

# Debug mode should be enabled only in the local development environment.
DEBUG = get_bool_env(
    "DJANGO_DEBUG",
    default=False,
)

# Multiple hosts are supplied as a comma-separated environment variable.
ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv(
        "DJANGO_ALLOWED_HOSTS",
        "",
    ).split(",")
    if host.strip()
]

# Allow internal Koyeb requests addressed by a platform identifier.
for environment_name in (
    "KOYEB_SERVICE_ID",
    "KOYEB_INSTANCE_ID",
):
    koyeb_internal_host = os.getenv(
        environment_name,
        "",
    ).strip()

    if (
        koyeb_internal_host
        and koyeb_internal_host not in ALLOWED_HOSTS
    ):
        ALLOWED_HOSTS.append(koyeb_internal_host)

# Koyeb terminates TLS and forwards HTTP internally.
# # Trust this header so Django detects HTTPS and avoids redirect loops.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Redirect HTTP requests to HTTPS when enabled by the environment.
SECURE_SSL_REDIRECT = get_bool_env(
    "SECURE_SSL_REDIRECT",
    default=False,
)

# Production cookies are transmitted only over HTTPS.
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",
    "django.contrib.auth.backends.ModelBackend",
]

LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "core:home"
LOGOUT_REDIRECT_URL = "core:home"

# Store login attempts in the application database.
AXES_HANDLER = (
    "axes.handlers.database.AxesDatabaseHandler"
)

# Track and lock login attempts by username and IP address.
AXES_LOCKOUT_PARAMETERS = [
    ["username", "ip_address"],
]

# Lock the username and IP pair after five failed authentication attempts.
AXES_FAILURE_LIMIT = 5
AXES_LOCK_OUT_AT_FAILURE = True

# Allow authentication attempts again 15 minutes after lockout begins.
AXES_COOLOFF_TIME = timedelta(
    minutes=15,
)

# Keep the original lockout expiry when another attempt is made during lockout.
AXES_RESET_COOL_OFF_ON_FAILURE_DURING_LOCKOUT = False

# Clear accumulated failures after a successful authentication.
AXES_RESET_ON_SUCCESS = True

# Return a rate-limit response when authentication is blocked.
AXES_HTTP_RESPONSE_CODE = 429

# Render the styled lockout page.
AXES_LOCKOUT_TEMPLATE = (
    "accounts/login_lockout.html"
)

# Calculate the remaining wait time and add the Retry-After header
# whenever a lockout response is generated.
AXES_LOCKOUT_CALLABLE = (
    "accounts.security.login_lockout_response"
)

# Resolve the client IP consistently and map unknown values to None.
AXES_CLIENT_IP_CALLABLE = (
    "accounts.security.resolve_axes_client_ip"
)


# ---------------------------------------------------------------------------
# Application definition
# ---------------------------------------------------------------------------

INSTALLED_APPS = [
    "accounts.apps.AccountsConfig",
    "core.apps.CoreConfig",
    "axes",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "core.middleware.ApplicationAccessMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "axes.middleware.AxesMiddleware",
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
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

# Both local Docker PostgreSQL and production Neon use DATABASE_URL.
DATABASE_URL = get_required_env("DATABASE_URL")

# Local development normally uses zero to close the connection after each
# request. Production can use a positive value for persistent connections.
DATABASE_CONN_MAX_AGE = get_int_env(
    "DATABASE_CONN_MAX_AGE",
    default=0,
)

# Prevent an unavailable database from blocking a process indefinitely.
DATABASE_CONNECT_TIMEOUT = get_int_env(
    "DATABASE_CONNECT_TIMEOUT",
    default=5,
)

DATABASES = {
    "default": build_database_config(
        database_url=DATABASE_URL,
        conn_max_age=DATABASE_CONN_MAX_AGE,
        connect_timeout=DATABASE_CONNECT_TIMEOUT,
    ),
}


# ---------------------------------------------------------------------------
# Password validation
# ---------------------------------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "UserAttributeSimilarityValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "MinimumLengthValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "CommonPasswordValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "NumericPasswordValidator"
        ),
    },
]


# ---------------------------------------------------------------------------
# Internationalisation
# ---------------------------------------------------------------------------

LANGUAGE_CODE = get_str_env(
    "DJANGO_LANGUAGE_CODE",
    default="en-us",
)

TIME_ZONE = get_str_env(
    "DJANGO_TIME_ZONE",
    default="UTC",
)

USE_I18N = True

USE_TZ = True


# ---------------------------------------------------------------------------
# Static files
# ---------------------------------------------------------------------------

STATIC_URL = "static/"

STATICFILES_DIRS = [
    BASE_DIR / "static",
]

# collectstatic places all production static files in this directory.
STATIC_ROOT = BASE_DIR / "staticfiles"

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        # Static files receive hashed names, compression, and long-lived
        # caching headers suitable for production delivery through WhiteNoise.
        "BACKEND": (
            "whitenoise.storage.CompressedManifestStaticFilesStorage"
        ),
    },
}

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

LOGGING = build_logging_config(
    base_dir=BASE_DIR,
    debug=DEBUG,
)
