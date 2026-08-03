"""Shared helper utilities used across the project's apps."""

from django.http import HttpRequest


def get_client_ip(request: HttpRequest) -> str:
    """
    Return the best-effort IP address of the client making the request.

    The first address in ``X-Forwarded-For`` is used when present, since the
    application typically runs behind a platform proxy (e.g. Koyeb). The
    direct ``REMOTE_ADDR`` value is used as a fallback for local development,
    where no such proxy sits in front of the server.
    """
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")

    if forwarded_for:
        # The header may list several hops; the client is the first one.
        return forwarded_for.split(",")[0].strip()

    return request.META.get("REMOTE_ADDR", "unknown")
