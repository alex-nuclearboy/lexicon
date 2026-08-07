"""URL configuration for the core application."""

from django.urls import path

from core.views import health_live, health_ready, home

app_name = "core"  # pylint: disable=invalid-name


urlpatterns = [
    path(
        "",
        home,
        name="home",
    ),
    path(
        "health/live/",
        health_live,
        name="health-live",
    ),
    path(
        "health/ready/",
        health_ready,
        name="health-ready",
    ),
]
