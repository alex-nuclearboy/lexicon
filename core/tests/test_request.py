"""Tests for shared HTTP request helpers."""

from django.test import RequestFactory, SimpleTestCase

from core.request import get_client_ip


class GetClientIpTests(SimpleTestCase):
    """Verify validated client IP extraction."""

    def setUp(self) -> None:
        """Create the request factory used by every test."""
        self.request_factory = RequestFactory()

    def test_spoofed_leftmost_forwarded_address_is_ignored(
        self,
    ) -> None:
        """Trust only the final Koyeb-appended forwarded address."""
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

    def test_last_address_is_used_with_multiple_proxies(
        self,
    ) -> None:
        """Use the final address from a multi-proxy forwarding chain."""
        request = self.request_factory.get(
            "/",
            HTTP_X_FORWARDED_FOR=(
                "198.51.100.25, "
                "192.0.2.10, "
                "203.0.113.7"
            ),
            REMOTE_ADDR="127.0.0.1",
        )

        self.assertEqual(
            get_client_ip(request),
            "203.0.113.7",
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

    def test_valid_leftmost_ip_is_ignored_when_last_ip_is_invalid(
        self,
    ) -> None:
        """Do not fall back to an untrusted leftmost forwarded address."""
        request = self.request_factory.get(
            "/",
            HTTP_X_FORWARDED_FOR=(
                "198.51.100.25, not-an-ip"
            ),
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

    def test_forwarded_ipv6_address_is_supported(self) -> None:
        """Return a validated IPv6 address from the forwarding header."""
        request = self.request_factory.get(
            "/",
            HTTP_X_FORWARDED_FOR=(
                "198.51.100.25, 2001:db8::10"
            ),
            REMOTE_ADDR="127.0.0.1",
        )

        self.assertEqual(
            get_client_ip(request),
            "2001:db8::10",
        )
