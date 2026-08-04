"""URL configuration for the accounts application."""

from django.urls import path

from .views import (
    login_view,
    logout_view,
    password_change_view,
)


app_name = "accounts"  # pylint: disable=invalid-name

urlpatterns = [
    path(
        "login/",
        login_view,
        name="login",
    ),
    path(
        "logout/",
        logout_view,
        name="logout",
    ),
    path(
        "password/change/",
        password_change_view,
        name="password_change",
    ),
]
