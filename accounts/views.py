"""Authentication views for the accounts application."""

import logging
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.core.exceptions import NON_FIELD_ERRORS
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from core.utils import get_client_ip
from .access import can_access_application
from .forms import ApplicationLoginForm
from .ui_messages import LOGIN_SUCCESSFUL, LOGOUT_SUCCESSFUL


audit_logger = logging.getLogger(
    f"vocabio.audit.{__name__}"
)


def login_view(request: HttpRequest) -> HttpResponse:
    """Authenticate a user and start an application session.

    Authenticated users who already have access to the application are
    redirected immediately. Other users are shown the login form.

    Args:
        request: The current HTTP request.

    Returns:
        A redirect after successful authentication or a rendered login page.
    """
    if (
        request.user.is_authenticated
        and can_access_application(request.user)
    ):
        return redirect(settings.LOGIN_REDIRECT_URL)

    form = ApplicationLoginForm(
        request=request,
        data=request.POST or None,
    )

    if request.method == "POST":
        if form.is_valid():
            user = form.get_user()

            if user is not None:
                login(request, user)

                audit_logger.info(
                    "[AUTH|LOGIN] User signed in successfully | "
                    "username=%s | user_id=%s | ip=%s.",
                    user.get_username(),
                    user.pk,
                    get_client_ip(request),
                )

                messages.success(request, LOGIN_SUCCESSFUL)

                return redirect(settings.LOGIN_REDIRECT_URL)

        elif form.has_error(
            NON_FIELD_ERRORS,
            code="invalid_login",
        ):
            audit_logger.warning(
                "[AUTH|FAILED] Login attempt failed because "
                "the credentials were invalid | ip=%s.",
                get_client_ip(request),
            )

    return render(
        request,
        "accounts/login.html",
        {"form": form},
    )


@require_POST
def logout_view(request: HttpRequest) -> HttpResponse:
    """End the current session and redirect after logout.

    Args:
        request: The current HTTP request.

    Returns:
        A redirect to the configured logout destination.
    """
    user_id = (
        request.user.pk
        if request.user.is_authenticated
        else None
    )
    username = (
        request.user.get_username()
        if request.user.is_authenticated
        else None
    )
    client_ip = get_client_ip(request)

    logout(request)

    if user_id is not None:
        audit_logger.info(
            "[AUTH|LOGOUT] User signed out successfully | "
            "username=%s | user_id=%s | ip=%s.",
            username,
            user_id,
            client_ip,
        )

    messages.success(request, LOGOUT_SUCCESSFUL)

    return redirect(settings.LOGOUT_REDIRECT_URL)
