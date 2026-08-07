"""Authentication forms for the accounts application."""

import logging

from django import forms
from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from accounts.access import can_access_application
from accounts.ui_messages import APPLICATION_ACCESS_DENIED
from core.request import get_client_ip

audit_logger = logging.getLogger(f"vocabio.audit.{__name__}")


class ApplicationLoginForm(AuthenticationForm):
    """Authenticate a user and enforce the application access policy."""

    username = forms.CharField(
        label=_("Username"),
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "autocomplete": "username",
                "autofocus": True,
                "placeholder": _("Enter your username"),
            }
        ),
        error_messages={
            "required": _("Username is required."),
        },
    )

    password = forms.CharField(
        label=_("Password"),
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "autocomplete": "current-password",
                "placeholder": _("Enter your password"),
            }
        ),
        error_messages={
            "required": _("Password is required."),
        },
    )

    error_messages = {
        "invalid_login": _(
            "Please enter a correct username and password. "
            "Note that both fields may be case-sensitive."
        ),
        "inactive": _("This account is inactive."),
        "access_denied": APPLICATION_ACCESS_DENIED,
    }

    def confirm_login_allowed(
        self,
        user: AbstractBaseUser,
    ) -> None:
        """Confirm that an authenticated user may access the application.

        Args:
            user: The successfully authenticated user.

        Raises:
            ValidationError: If the account is inactive or the user does not
                have permission to access the application.
        """
        super().confirm_login_allowed(user)

        if not can_access_application(user):
            client_ip = (
                get_client_ip(self.request)
                if self.request is not None
                else None
            )

            audit_logger.warning(
                "[AUTH|LOGIN] Authenticated account denied application "
                "access | outcome=denied | user_id=%s | client_ip=%s.",
                user.pk,
                client_ip or "<unknown>",
            )

            raise ValidationError(
                self.error_messages["access_denied"],
                code="access_denied",
            )


class ApplicationPasswordChangeForm(PasswordChangeForm):
    """Allow a user to change their own password."""

    def __init__(
        self,
        *args,
        **kwargs,
    ) -> None:
        """Configure password fields for the application interface."""
        super().__init__(*args, **kwargs)

        old_password = self.fields["old_password"]
        old_password.label = _("Current password")
        old_password.error_messages["required"] = _(
            "Current password is required."
        )
        old_password.widget.attrs.update(
            {
                "class": "form-control",
                "autocomplete": "current-password",
                "autofocus": True,
                "placeholder": _("Enter your current password"),
            }
        )

        new_password1 = self.fields["new_password1"]
        new_password1.label = _("New password")
        new_password1.error_messages["required"] = _(
            "New password is required."
        )
        new_password1.widget.attrs.update(
            {
                "class": "form-control",
                "autocomplete": "new-password",
                "placeholder": _("Enter a new password"),
            }
        )

        new_password2 = self.fields["new_password2"]
        new_password2.label = _("Confirm new password")
        new_password2.error_messages["required"] = _(
            "Password confirmation is required."
        )
        new_password2.widget.attrs.update(
            {
                "class": "form-control",
                "autocomplete": "new-password",
                "placeholder": _("Enter the new password again"),
            }
        )
