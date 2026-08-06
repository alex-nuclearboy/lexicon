"""Security helpers for the accounts application."""

import logging
from math import ceil
from typing import Any

from axes.helpers import (
    get_client_username,
    get_cool_off,
    get_failure_limit,
)
from axes.models import AccessAttempt
from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils import timezone

from core.utils import get_client_ip

audit_logger = logging.getLogger(f"vocabio.audit.{__name__}")


def resolve_axes_client_ip(
    request: HttpRequest,
) -> str | None:
    """Return a database-safe client IP for Axes.

    Convert the ``"unknown"`` sentinel from ``get_client_ip`` to ``None``

    Args:
        request: The current HTTP request.

    Returns:
        The client's IP address, or ``None`` when it could not be resolved.
    """
    client_ip = get_client_ip(request)
    return client_ip if client_ip != "unknown" else None


def login_lockout_response(
    request: HttpRequest,
    _original_response: HttpResponse | None,
    credentials: dict[str, Any] | None,
) -> HttpResponse:
    """Return a lockout page with the remaining cool-off time.

    Args:
        request: The current HTTP request.
        _original_response: The response replaced by the lockout response.
        credentials: Authentication credentials supplied to Django.

    Returns:
        A rendered HTTP 429 response containing the remaining lockout time.
    """
    username = (
        get_client_username(
            request,
            credentials,
        )
        or ""
    )
    client_ip = resolve_axes_client_ip(request)
    cool_off = get_cool_off(request)

    retry_after_seconds = 0

    if cool_off is not None:
        retry_after_seconds = ceil(cool_off.total_seconds())

        if username:
            access_attempts = (
                AccessAttempt.objects  # pylint: disable=no-member
            )

            latest_attempt_time = (
                access_attempts.filter(
                    username=username,
                    ip_address=client_ip,
                )
                .order_by("-attempt_time")
                .values_list(
                    "attempt_time",
                    flat=True,
                )
                .first()
            )

            if latest_attempt_time is not None:
                lockout_expires_at = latest_attempt_time + cool_off

                retry_after_seconds = max(
                    1,
                    ceil(
                        (
                            lockout_expires_at - timezone.now()
                        ).total_seconds()
                    ),
                )

    retry_after_minutes = (
        max(
            1,
            ceil(retry_after_seconds / 60),
        )
        if retry_after_seconds
        else None
    )

    audit_logger.warning(
        "[AUTH|LOCKOUT] Login attempt blocked because the username and IP "
        "address are temporarily locked | username=%s | ip_address=%s | "
        "retry_after_seconds=%s.",
        username or "<unknown>",
        client_ip or "<unknown>",
        (
            retry_after_seconds
            if retry_after_seconds is not None
            else "unknown"
        ),
    )

    response = render(
        request,
        settings.AXES_LOCKOUT_TEMPLATE,
        {
            "failure_limit": get_failure_limit(
                request,
                credentials,
            ),
            "username": username,
            "retry_after_seconds": retry_after_seconds,
            "retry_after_minutes": retry_after_minutes,
        },
        status=settings.AXES_HTTP_RESPONSE_CODE,
    )

    if retry_after_seconds:
        response.headers["Retry-After"] = str(retry_after_seconds)

    return response
