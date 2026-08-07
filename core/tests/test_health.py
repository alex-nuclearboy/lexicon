"""Tests for the application health endpoints."""

from unittest.mock import patch

from django.db import DatabaseError
from django.test import TestCase
from django.urls import reverse


class HealthEndpointTests(TestCase):
    """Verify the public application health endpoints."""

    def test_liveness_returns_ok_without_database_query(self) -> None:
        """Return success without accessing the database."""
        with patch("core.views.connection.cursor") as cursor:
            response = self.client.get(
                reverse("core:health-live"),
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
        cursor.assert_not_called()

    def test_readiness_returns_ok_when_database_is_available(
        self,
    ) -> None:
        """Return success when the database responds."""
        response = self.client.get(
            reverse("core:health-ready"),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_readiness_returns_503_for_database_error(self) -> None:
        """Return a generic failure response for database errors."""
        with patch(
            "core.views.connection.cursor",
            side_effect=DatabaseError("Database unavailable"),
        ):
            with self.assertLogs(
                "django.request",
                level="ERROR",
            ):
                response = self.client.get(
                    reverse("core:health-ready"),
                )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json(),
            {"status": "unavailable"},
        )
        self.assertNotContains(
            response,
            "Database unavailable",
            status_code=503,
        )
