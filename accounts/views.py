"""Authentication views for the accounts application."""

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from .access import can_access_application
from .forms import ApplicationLoginForm
from .ui_messages import LOGIN_SUCCESSFUL, LOGOUT_SUCCESSFUL


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

    if request.method == "POST" and form.is_valid():
        user = form.get_user()

        if user is not None:
            login(request, user)
            messages.success(request, LOGIN_SUCCESSFUL)

            return redirect(settings.LOGIN_REDIRECT_URL)

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
    logout(request)
    messages.success(request, LOGOUT_SUCCESSFUL)

    return redirect(settings.LOGOUT_REDIRECT_URL)
