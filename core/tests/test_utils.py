"""Tests for shared core utilities."""

from django.test import RequestFactory, SimpleTestCase

from core.utils import get_client_ip


class GetClientIpTests(SimpleTestCase):
    """Verify best-effort client IP extraction."""

    def setUp(self) -> None:
        """Create the request factory used by every test."""
        self.request_factory = RequestFactory()

    def test_first_forwarded_address_is_returned(self) -> None:
        """Prefer the first address from X-Forwarded-For."""
        request = self.request_factory.get(
            "/",
            HTTP_X_FORWARDED_FOR=(
                "203.0.113.10, 10.0.0.1"
            ),
            REMOTE_ADDR="127.0.0.1",
        )

        self.assertEqual(
            get_client_ip(request),
            "203.0.113.10",
        )

    def test_forwarded_address_is_stripped(self) -> None:
        """Remove surrounding whitespace from the forwarded address."""
        request = self.request_factory.get(
            "/",
            HTTP_X_FORWARDED_FOR=(
                " 203.0.113.10 , 10.0.0.1"
            ),
            REMOTE_ADDR="127.0.0.1",
        )

        self.assertEqual(
            get_client_ip(request),
            "203.0.113.10",
        )

    def test_remote_address_is_used_without_forwarded_header(
        self,
    ) -> None:
        """Use REMOTE_ADDR when no forwarded header is available."""
        request = self.request_factory.get(
            "/",
            REMOTE_ADDR="127.0.0.1",
        )

        self.assertEqual(
            get_client_ip(request),
            "127.0.0.1",
        )

    def test_remote_address_is_used_for_empty_forwarded_value(
        self,
    ) -> None:
        """Use REMOTE_ADDR when the first forwarded value is empty."""
        request = self.request_factory.get(
            "/",
            HTTP_X_FORWARDED_FOR=", 10.0.0.1",
            REMOTE_ADDR="127.0.0.1",
        )

        self.assertEqual(
            get_client_ip(request),
            "127.0.0.1",
        )

    def test_unknown_is_returned_when_no_address_exists(
        self,
    ) -> None:
        """Return unknown when neither address source is available."""
        request = self.request_factory.get("/")

        request.META.pop("REMOTE_ADDR", None)

        self.assertEqual(
            get_client_ip(request),
            "unknown",
        )
