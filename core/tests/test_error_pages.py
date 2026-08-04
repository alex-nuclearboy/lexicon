"""Tests for custom application error pages."""

from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.contrib.messages.storage.fallback import (
    FallbackStorage,
)
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpRequest
from django.test import (
    RequestFactory,
    SimpleTestCase,
    override_settings,
)
from django.urls import reverse
from django.views.defaults import (
    page_not_found,
    permission_denied,
    server_error,
)


@override_settings(DEBUG=False)
class ErrorPageTests(SimpleTestCase):
    """Verify custom application error responses."""

    def setUp(self) -> None:
        """Create the request factory used by the tests."""
        self.request_factory = RequestFactory()

    def _create_request(
        self,
        path: str,
    ) -> HttpRequest:
        """Create a request with standard template dependencies.

        Args:
            path: The requested application path.

        Returns:
            A prepared HTTP request.
        """
        request = self.request_factory.get(path)
        request.user = AnonymousUser()
        request.session = {}

        setattr(
            request,
            "_messages",
            FallbackStorage(request),
        )

        return request

    def test_permission_denied_page(self) -> None:
        """Render the custom 403 response."""
        request = self._create_request(
            "/restricted/",
        )

        response = permission_denied(
            request,
            PermissionDenied(),
        )

        self.assertEqual(
            response.status_code,
            403,
        )
        self.assertContains(
            response,
            "Access denied",
            status_code=403,
        )
        self.assertContains(
            response,
            "error-page--error",
            status_code=403,
        )
        self.assertContains(
            response,
            'class="error-page__link"',
            status_code=403,
        )
        self.assertContains(
            response,
            f'href="{reverse("core:home")}"',
            status_code=403,
        )
        self.assertNotContains(
            response,
            "button--secondary",
            status_code=403,
        )

    def test_page_not_found_page(self) -> None:
        """Render the custom 404 response."""
        request = self._create_request(
            "/missing-page/",
        )

        response = page_not_found(
            request,
            Http404(),
        )

        self.assertEqual(
            response.status_code,
            404,
        )
        self.assertContains(
            response,
            "Page not found",
            status_code=404,
        )
        self.assertContains(
            response,
            "error-page--neutral",
            status_code=404,
        )
        self.assertContains(
            response,
            'class="error-page__link"',
            status_code=404,
        )
        self.assertContains(
            response,
            f'href="{reverse("core:home")}"',
            status_code=404,
        )
        self.assertNotContains(
            response,
            "button--secondary",
            status_code=404,
        )

    def test_server_error_page(self) -> None:
        """Render the custom standalone 500 response."""
        request = self.request_factory.get(
            "/server-error/",
        )

        response = server_error(request)

        self.assertEqual(
            response.status_code,
            500,
        )
        self.assertContains(
            response,
            "Something went wrong",
            status_code=500,
        )
        self.assertContains(
            response,
            "Please try again later.",
            status_code=500,
        )
        self.assertContains(
            response,
            'href="/"',
            status_code=500,
        )
        self.assertContains(
            response,
            "<style>",
            status_code=500,
        )

    def test_server_error_template_is_self_contained(
        self,
    ) -> None:
        """Keep the 500 template free from runtime dependencies."""
        template_path = (
            Path(settings.BASE_DIR)
            / "templates"
            / "500.html"
        )
        template_source = template_path.read_text(
            encoding="utf-8",
        )

        forbidden_template_tags = (
            "{% extends",
            "{% include",
            "{% static",
            "{% url",
        )

        for template_tag in forbidden_template_tags:
            with self.subTest(
                template_tag=template_tag,
            ):
                self.assertNotIn(
                    template_tag,
                    template_source,
                )
