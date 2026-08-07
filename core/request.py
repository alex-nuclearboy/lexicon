"""HTTP request helpers shared across the project's applications."""

from ipaddress import ip_address

from django.http import HttpRequest


def _normalise_ip(value: str | None) -> str | None:
    """Return a validated IP address or None."""

    if not value:
        return None

    try:
        return str(ip_address(value.strip()))
    except ValueError:
        return None


def get_client_ip(request: HttpRequest) -> str | None:
    """Return the validated client IP address.

    Koyeb appends its verified client address to the right-hand side of
    ``X-Forwarded-For``. The final address is therefore preferred when the
    header is present. ``REMOTE_ADDR`` is used as a fallback.

    Args:
        request: The current HTTP request.

    Returns:
        The validated client IP address, or ``None`` when no valid address
        is available.
    """
    forwarded_for = request.META.get(
        "HTTP_X_FORWARDED_FOR",
        "",
    )

    if forwarded_for:
        forwarded_ip = forwarded_for.rsplit(
            ",",
            maxsplit=1,
        )[-1]

        client_ip = _normalise_ip(forwarded_ip)

        if client_ip is not None:
            return client_ip

    return _normalise_ip(
        request.META.get("REMOTE_ADDR")
    )
