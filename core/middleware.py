"""Site-wide application access control for Vocabio."""

import logging
from collections.abc import Callable

from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse
from django.urls import Resolver404, resolve

from accounts.access import can_access_application
from accounts.ui_messages import APPLICATION_ACCESS_DENIED
from core.utils import get_client_ip


GetResponse = Callable[[HttpRequest], HttpResponse]

logger = logging.getLogger(
    f"vocabio.{__name__}"
)

audit_logger = logging.getLogger(
    f"vocabio.audit.{__name__}"
)


# Named URL patterns that bypass the application access check.
#
# The home page and login page remain publicly available. Logout is exempt so
# that an authenticated user can still end the session if application access
# is revoked while the session is active.
EXEMPT_URL_NAMES = frozenset(
    {
        "core:home",
        "accounts:login",
        "accounts:logout",
    }
)


# Django Admin manages its own authentication and staff permissions.
EXEMPT_PATH_PREFIXES = (
    "/admin/",
)


class ApplicationAccessMiddleware:
    """Protect application views with the central access policy.

    Anonymous users are redirected to the configured login page. Active
    authenticated users must be superusers or hold the dedicated application
    access permission.

    Explicitly exempt views and Django Admin are allowed to manage their own
    access rules.
    """

    def __init__(
        self,
        get_response: GetResponse,
    ) -> None:
        """Initialise the middleware.

        Args:
            get_response: The next callable in Django's middleware chain.
        """
        self.get_response = get_response

    def __call__(
        self,
        request: HttpRequest,
    ) -> HttpResponse:
        """Apply the application access policy to the current request.

        Args:
            request: The current HTTP request.

        Returns:
            The response from the next middleware or view.

        Raises:
            PermissionDenied: If an authenticated user does not have
                application access.
        """
        if self._is_exempt(request):
            return self.get_response(request)

        if not request.user.is_authenticated:
            logger.info(
                "[ACCESS|REDIRECT] Anonymous request redirected "
                "to login | path=%s | ip=%s.",
                request.path,
                get_client_ip(request),
            )

            return redirect_to_login(
                request.get_full_path(),
                login_url=settings.LOGIN_URL,
            )

        if can_access_application(request.user):
            return self.get_response(request)

        audit_logger.warning(
            "[ACCESS|DENIED] Application access denied | "
            "username=%s | user_id=%s | path=%s | ip=%s.",
            request.user.get_username(),
            request.user.pk,
            request.path,
            get_client_ip(request),
        )

        raise PermissionDenied(
            str(APPLICATION_ACCESS_DENIED)
        )

    @staticmethod
    def _is_exempt(
        request: HttpRequest,
    ) -> bool:
        """Return whether the request bypasses application access control.

        Args:
            request: The current HTTP request.

        Returns:
            ``True`` when the requested path is explicitly exempt.
        """
        path = request.path_info

        if path.startswith(EXEMPT_PATH_PREFIXES):
            return True

        try:
            match = resolve(path)
        except Resolver404:
            # Non-existent paths should continue to Django's normal 404
            # handling rather than being redirected to the login page.
            return True

        return match.view_name in EXEMPT_URL_NAMES
