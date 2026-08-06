"""Shared helpers and settings for account tests."""

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

from accounts.models import ApplicationPermissions

TEST_STORAGES = {
    "default": {
        "BACKEND": (
            "django.core.files.storage.FileSystemStorage"
        ),
    },
    "staticfiles": {
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage"
        ),
    },
}


def get_application_access_permission() -> Permission:
    """Return the application's custom access permission."""
    content_type = ContentType.objects.get_for_model(
        ApplicationPermissions,
        for_concrete_model=False,
    )

    return Permission.objects.get(
        content_type=content_type,
        codename="access_application",
    )
