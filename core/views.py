"""Views for the core application."""

from django.db import DatabaseError, connection
from django.http import (
    HttpRequest,
    HttpResponse,
    JsonResponse,
)
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_safe


def home(request: HttpRequest) -> HttpResponse:
    """Render the public Vocabio home page.

    Args:
        request: The current HTTP request.

    Returns:
        The rendered home page response.
    """
    return render(request, "core/home.html")


@never_cache
@require_safe
def health_live(_request: HttpRequest) -> JsonResponse:
    """Confirm that the application process can serve requests."""
    return JsonResponse({"status": "ok"})


@never_cache
@require_safe
def health_ready(_request: HttpRequest) -> JsonResponse:
    """Confirm that the application and database are available."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except DatabaseError:
        return JsonResponse(
            {"status": "unavailable"},
            status=503,
        )

    return JsonResponse({"status": "ok"})
