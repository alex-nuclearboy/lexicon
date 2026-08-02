from django.conf import settings
from django.contrib.auth import login, logout
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from .forms import OwnerLoginForm


def login_view(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect(settings.LOGIN_REDIRECT_URL)

    form = OwnerLoginForm(
        request.POST or None,
        request=request,
    )

    if request.method == "POST" and form.is_valid():
        user = form.get_user()

        if user is not None:
            login(request, user)
            return redirect(settings.LOGIN_REDIRECT_URL)

    return render(
        request,
        "accounts/login.html",
        {"form": form},
    )


@require_POST
def logout_view(request: HttpRequest) -> HttpResponse:
    logout(request)

    return redirect(settings.LOGOUT_REDIRECT_URL)
