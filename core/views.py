"""Views for the core application."""

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


def home(request: HttpRequest) -> HttpResponse:
    """Render the public Vocabio home page.

    Args:
        request: The current HTTP request.

    Returns:
        The rendered home page response.
    """
    return render(request, "core/home.html")
