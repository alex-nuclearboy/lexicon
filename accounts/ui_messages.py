"""Reusable user-facing messages for the accounts application."""

from django.utils.translation import gettext_lazy as _

APPLICATION_ACCESS_DENIED = _(
    "This account does not have access to the application."
)

LOGIN_SUCCESSFUL = _("You have signed in successfully.")

LOGOUT_SUCCESSFUL = _("You have signed out successfully.")

PASSWORD_CHANGE_SUCCESSFUL = _("Your password has been changed successfully.")
