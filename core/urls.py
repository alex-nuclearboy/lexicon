"""URL configuration for the core application."""

from django.urls import path

from core.views import home

app_name = "core"  # pylint: disable=invalid-name

urlpatterns = [
    path("", home, name="home"),
]
