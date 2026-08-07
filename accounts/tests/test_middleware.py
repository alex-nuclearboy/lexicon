"""Integration tests for the application access middleware."""

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.http import HttpRequest, HttpResponse
from django.test import TestCase, override_settings
from django.urls import include, path, reverse

from accounts.tests.helpers import (
    TEST_STORAGES,
    get_application_access_permission,
)

User = get_user_model()


def protected_view(request: HttpRequest) -> HttpResponse:
    """Return a minimal response for middleware integration tests.

    Args:
        request: The current HTTP request.

    Returns:
        A successful response for an authorised request.
    """
    del request

    return HttpResponse("Protected content")


urlpatterns = [
    path(
        "protected/",
        protected_view,
        name="protected",
    ),
    path(
        "control-panel/",
        admin.site.urls,
    ),
    path(
        "accounts/",
        include("accounts.urls"),
    ),
    path(
        "",
        include("core.urls"),
    ),
]


@override_settings(
    ROOT_URLCONF=__name__,
    STORAGES=TEST_STORAGES,
)
class ApplicationAccessMiddlewareTests(TestCase):
    """Verify application-wide access control through real requests."""

    @classmethod
    def setUpTestData(cls) -> None:
        """Create reusable accounts and the application permission."""
        cls.access_permission = get_application_access_permission()

        cls.user = User.objects.create_user(
            username="member",
            password="A-secure-test-password-123!",
        )
        cls.superuser = User.objects.create_superuser(
            username="admin",
            password="A-secure-test-password-123!",
        )

    def test_home_is_public(self) -> None:
        """Allow an anonymous user to open the public home page."""
        response = self.client.get(
            reverse("core:home")
        )

        self.assertEqual(response.status_code, 200)

    def test_login_page_is_public(self) -> None:
        """Allow an anonymous user to open the login page."""
        response = self.client.get(
            reverse("accounts:login")
        )

        self.assertEqual(response.status_code, 200)

    def test_anonymous_user_is_redirected_to_login(self) -> None:
        """Redirect an anonymous protected request and record the event."""
        protected_url = reverse("protected")
        login_url = reverse("accounts:login")

        with self.assertLogs(
            "vocabio.accounts.middleware",
            level="INFO",
        ) as captured_logs:
            response = self.client.get(protected_url)

        self.assertRedirects(
            response,
            f"{login_url}?next={protected_url}",
            fetch_redirect_response=False,
        )

        self.assertEqual(
            len(captured_logs.output),
            1,
        )

        log_message = captured_logs.output[0]

        self.assertIn(
            "[ACCESS|CHECK]",
            log_message,
        )
        self.assertIn(
            "outcome=redirected",
            log_message,
        )
        self.assertIn(
            "path=/protected/",
            log_message,
        )
        self.assertIn(
            "client_ip=127.0.0.1",
            log_message,
        )

    def test_user_with_permission_can_open_protected_view(
        self,
    ) -> None:
        """Allow a user with the application permission."""
        self.user.user_permissions.add(
            self.access_permission
        )
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("protected")
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Protected content",
        )

    def test_superuser_can_open_protected_view(self) -> None:
        """Allow an active superuser to open a protected view."""
        self.client.force_login(self.superuser)

        response = self.client.get(
            reverse("protected")
        )

        self.assertEqual(response.status_code, 200)

    def test_user_without_permission_receives_forbidden_response(
        self,
    ) -> None:
        """Return 403 and record an audit event when access is denied."""
        self.client.force_login(self.user)

        with self.assertLogs(
            "vocabio.audit.accounts.middleware",
            level="WARNING",
        ) as captured_logs:
            response = self.client.get(
                reverse("protected")
            )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            len(captured_logs.output),
            1,
        )

        log_message = captured_logs.output[0]

        self.assertIn(
            "[ACCESS|CHECK]",
            log_message,
        )
        self.assertIn(
            "outcome=denied",
            log_message,
        )
        self.assertIn(
            f"user_id={self.user.pk}",
            log_message,
        )
        self.assertIn(
            "path=/protected/",
            log_message,
        )
        self.assertIn(
            "client_ip=127.0.0.1",
            log_message,
        )
        self.assertNotIn(
            "username=",
            log_message,
        )

    def test_admin_namespace_uses_its_own_login_flow(self) -> None:
        """Leave Django Admin access control to Django Admin."""
        admin_url = reverse("admin:index")
        admin_login_url = reverse("admin:login")

        response = self.client.get(admin_url)

        self.assertRedirects(
            response,
            f"{admin_login_url}?next={admin_url}",
            fetch_redirect_response=False,
        )

    def test_unknown_path_returns_not_found(self) -> None:
        """Allow Django to handle unresolved paths as ordinary 404s."""
        response = self.client.get(
            "/missing-page/"
        )

        self.assertEqual(response.status_code, 404)

    def test_user_without_permission_can_log_out(self) -> None:
        """Keep logout available when application access is revoked."""
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("accounts:logout")
        )

        self.assertRedirects(
            response,
            reverse("core:home"),
        )
        self.assertNotIn(
            "_auth_user_id",
            self.client.session,
        )
