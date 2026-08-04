"""Authentication views for the accounts application."""

import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import (
    REDIRECT_FIELD_NAME,
    login,
    logout,
    update_session_auth_hash,
)
from django.contrib.auth.decorators import login_required
from django.core.exceptions import NON_FIELD_ERRORS
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import (
    require_http_methods,
    require_POST,
)

from core.utils import get_client_ip

from .access import can_access_application
from .forms import (
    ApplicationLoginForm,
    ApplicationPasswordChangeForm,
)
from .ui_messages import (
    LOGIN_SUCCESSFUL,
    LOGOUT_SUCCESSFUL,
    PASSWORD_CHANGE_SUCCESSFUL,
)

logger = logging.getLogger(
    f"vocabio.{__name__}"
)

audit_logger = logging.getLogger(
    f"vocabio.audit.{__name__}"
)


def _get_safe_redirect_url(
    request: HttpRequest,
) -> str | None:
    """Return a safe redirect target requested by the login flow.

    POST data is checked first so the target survives an unsuccessful form
    submission. Query parameters are used as a fallback for the initial login
    request.

    Args:
        request: The current HTTP request.

    Returns:
        A validated local or same-host redirect URL, or ``None`` when no safe
        target was provided.
    """
    redirect_to = (
        request.POST.get(REDIRECT_FIELD_NAME)
        or request.GET.get(REDIRECT_FIELD_NAME)
    )

    if not redirect_to:
        return None

    if url_has_allowed_host_and_scheme(
        url=redirect_to,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect_to

    return None


@sensitive_post_parameters()
@never_cache
@require_http_methods(["GET", "POST"])
@csrf_protect
def login_view(request: HttpRequest) -> HttpResponse:
    """Authenticate a user and start an application session.

    Authenticated users who already have access to the application are
    redirected immediately. Other users are shown the login form.

    Args:
        request: The current HTTP request.

    Returns:
        A redirect after successful authentication or a rendered login page.
    """
    logger.warning(
        "[SECURITY|PROXY_DIAGNOSTIC] "
        "x_forwarded_proto=%r | scheme=%s | is_secure=%s.",
        request.META.get("HTTP_X_FORWARDED_PROTO"),
        request.scheme,
        request.is_secure(),
    )

    redirect_url = _get_safe_redirect_url(request)

    if (
        request.user.is_authenticated
        and can_access_application(request.user)
    ):
        return redirect(
            redirect_url or settings.LOGIN_REDIRECT_URL
        )

    form = ApplicationLoginForm(
        request=request,
        data=(
            request.POST
            if request.method == "POST"
            else None
        ),
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

                messages.success(
                    request,
                    LOGIN_SUCCESSFUL,
                )

                return redirect(
                    redirect_url
                    or settings.LOGIN_REDIRECT_URL
                )

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
        {
            "form": form,
            REDIRECT_FIELD_NAME: redirect_url or "",
        },
    )


@sensitive_post_parameters()
@never_cache
@require_http_methods(["GET", "POST"])
@csrf_protect
@login_required
def password_change_view(
    request: HttpRequest,
) -> HttpResponse:
    """Allow an authenticated user to change their own password.

    Args:
        request: The current HTTP request.

    Returns:
        A redirect after a successful password change or the rendered
        password change form.
    """
    form = ApplicationPasswordChangeForm(
        user=request.user,
        data=(
            request.POST
            if request.method == "POST"
            else None
        ),
    )

    if request.method == "POST" and form.is_valid():
        user = form.save()

        update_session_auth_hash(
            request,
            user,
        )

        audit_logger.info(
            "[AUTH|PASSWORD_CHANGE] User changed their "
            "password successfully | username=%s | "
            "user_id=%s | ip=%s.",
            user.get_username(),
            user.pk,
            get_client_ip(request),
        )

        messages.success(
            request,
            PASSWORD_CHANGE_SUCCESSFUL,
        )

        return redirect(
            settings.LOGIN_REDIRECT_URL
        )

    return render(
        request,
        "accounts/password_change.html",
        {
            "form": form,
        },
    )


@never_cache
@require_POST
@csrf_protect
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

    messages.success(
        request,
        LOGOUT_SUCCESSFUL,
    )

    return redirect(
        settings.LOGOUT_REDIRECT_URL
    )
