"""Tests for shared HTTP request helpers."""

from django.test import RequestFactory, SimpleTestCase

from core.request import get_client_ip


class GetClientIpTests(SimpleTestCase):
    """Verify validated client IP extraction."""

    def setUp(self) -> None:
        """Create the request factory used by every test."""
        self.request_factory = RequestFactory()

    def test_last_forwarded_address_is_returned(self) -> None:
        """Prefer the final address from X-Forwarded-For."""
        request = self.request_factory.get(
            "/",
            HTTP_X_FORWARDED_FOR=(
                "203.0.113.10, 10.0.0.1"
            ),
            REMOTE_ADDR="127.0.0.1",
        )

        self.assertEqual(
            get_client_ip(request),
            "10.0.0.1",
        )

    def test_forwarded_address_is_stripped(self) -> None:
        """Remove whitespace from the final forwarded address."""
        request = self.request_factory.get(
            "/",
            HTTP_X_FORWARDED_FOR=(
                "203.0.113.10, 10.0.0.1 "
            ),
            REMOTE_ADDR="127.0.0.1",
        )

        self.assertEqual(
            get_client_ip(request),
            "10.0.0.1",
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

    def test_remote_address_is_used_for_invalid_forwarded_ip(
        self,
    ) -> None:
        """Use REMOTE_ADDR when the forwarded address is invalid."""
        request = self.request_factory.get(
            "/",
            HTTP_X_FORWARDED_FOR="not-an-ip",
            REMOTE_ADDR="127.0.0.1",
        )

        self.assertEqual(
            get_client_ip(request),
            "127.0.0.1",
        )

    def test_none_is_returned_when_no_address_exists(
        self,
    ) -> None:
        """Return None when neither address source is available."""
        request = self.request_factory.get("/")

        request.META.pop("REMOTE_ADDR", None)

        self.assertIsNone(
            get_client_ip(request)
        )

    def test_none_is_returned_when_all_addresses_are_invalid(
        self,
    ) -> None:
        """Return None when neither source contains a valid IP."""
        request = self.request_factory.get(
            "/",
            HTTP_X_FORWARDED_FOR="not-an-ip",
            REMOTE_ADDR="also-not-an-ip",
        )

        self.assertIsNone(
            get_client_ip(request)
        )

    def test_ipv6_address_is_supported(self) -> None:
        """Return a validated IPv6 address."""
        request = self.request_factory.get(
            "/",
            REMOTE_ADDR="2001:db8::1",
        )

        self.assertEqual(
            get_client_ip(request),
            "2001:db8::1",
        )
