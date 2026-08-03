"""Models and model-level permissions for the accounts application."""

from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _


class ApplicationAccess(User):
    """Define permission for access to the application."""

    class Meta:  # pylint: disable=too-few-public-methods
        """Configure the application access proxy model."""
        proxy = True
        default_permissions = ()
        permissions = [
            (
                "access_application",
                _("Can access the application"),
            ),
        ]
        verbose_name = _("application access")
        verbose_name_plural = _("application access")
