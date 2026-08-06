"""Shared helper utilities used across the project's apps."""

from django.http import HttpRequest


def get_client_ip(request: HttpRequest) -> str:
    """Return the best-effort IP address of the client making the request.

    The first address in ``X-Forwarded-For`` is preferred because the
    application normally runs behind a platform proxy. ``REMOTE_ADDR`` is
    used as a fallback for local development and for malformed or empty
    forwarded headers.

    Args:
        request: The current HTTP request.

    Returns:
        The forwarded client address, the direct remote address, or
        ``"unknown"`` when neither value is available.
    """
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")

    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()

        if client_ip:
            return client_ip

    return request.META.get("REMOTE_ADDR") or "unknown"
