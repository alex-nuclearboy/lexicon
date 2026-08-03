"""Authentication forms for the accounts application."""

from django import forms
from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from accounts.access import can_access_application
from accounts.ui_messages import APPLICATION_ACCESS_DENIED


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
            "required": _("Enter your username."),
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
            "required": _("Enter your password."),
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
            raise ValidationError(
                self.error_messages["access_denied"],
                code="access_denied",
            )
