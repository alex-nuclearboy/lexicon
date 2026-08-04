"""Integration tests for login attempt lockouts."""

from datetime import timedelta
from math import ceil

from axes.models import AccessAttempt
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponse
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import ApplicationAccess


User = get_user_model()

TEST_PASSWORD = "Secure-test-password-123!"
WRONG_PASSWORD = "Incorrect-test-password-456!"

TEST_STORAGES = {
    "default": {
        "BACKEND": (
            "django.core.files.storage.FileSystemStorage"
        ),
    },
    "staticfiles": {
        "BACKEND": (
            "django.contrib.staticfiles.storage."
            "StaticFilesStorage"
        ),
    },
}


@override_settings(STORAGES=TEST_STORAGES)
class LoginLockoutTests(TestCase):
    """Verify username-based authentication lockouts."""

    @classmethod
    def setUpTestData(cls) -> None:
        """Create users with application access."""
        content_type = ContentType.objects.get_for_model(
            ApplicationAccess,
            for_concrete_model=False,
        )
        access_permission = Permission.objects.get(
            content_type=content_type,
            codename="access_application",
        )

        cls.user = User.objects.create_user(
            username="lockout-member",
            password=TEST_PASSWORD,
        )
        cls.other_user = User.objects.create_user(
            username="other-member",
            password=TEST_PASSWORD,
        )

        cls.user.user_permissions.add(
            access_permission
        )
        cls.other_user.user_permissions.add(
            access_permission
        )

    def setUp(self) -> None:
        """Resolve URLs used by lockout tests."""
        self.login_url = reverse(
            "accounts:login"
        )
        self.home_url = reverse(
            "core:home"
        )

    def _post_login(
        self,
        *,
        username: str,
        password: str,
        ip_address: str = "192.0.2.1",
    ) -> HttpResponse:
        """Submit login credentials from a selected test address."""
        return self.client.post(
            self.login_url,
            {
                "username": username,
                "password": password,
            },
            REMOTE_ADDR=ip_address,
        )

    def test_lockout_policy_configuration(
        self,
    ) -> None:
        """Use the selected database-backed lockout policy."""
        self.assertEqual(
            settings.AXES_HANDLER,
            (
                "axes.handlers.database."
                "AxesDatabaseHandler"
            ),
        )
        self.assertEqual(
            settings.AXES_LOCKOUT_PARAMETERS,
            ["username"],
        )
        self.assertEqual(
            settings.AXES_FAILURE_LIMIT,
            5,
        )
        self.assertTrue(
            settings.AXES_LOCK_OUT_AT_FAILURE
        )
        self.assertEqual(
            settings.AXES_COOLOFF_TIME,
            timedelta(minutes=15),
        )
        self.assertFalse(
            settings.AXES_RESET_COOL_OFF_ON_FAILURE_DURING_LOCKOUT
        )
        self.assertTrue(
            settings.AXES_RESET_ON_SUCCESS
        )
        self.assertEqual(
            settings.AXES_HTTP_RESPONSE_CODE,
            429,
        )
        self.assertEqual(
            settings.AXES_LOCKOUT_TEMPLATE,
            "accounts/login_lockout.html",
        )
        self.assertEqual(
            settings.AXES_LOCKOUT_CALLABLE,
            "accounts.security.login_lockout_response",
        )
        self.assertEqual(
            settings.AXES_CLIENT_IP_CALLABLE,
            "accounts.security.discard_client_ip",
        )

    def test_failed_attempt_is_stored_in_database(
        self,
    ) -> None:
        """Persist a failed authentication attempt."""
        response = self._post_login(
            username=self.user.username,
            password=WRONG_PASSWORD,
        )

        self.assertEqual(
            response.status_code,
            200,
        )
        self.assertTrue(
            AccessAttempt.objects.filter(  # pylint: disable=no-member
                username=self.user.username,
            ).exists()
        )

    def test_username_is_locked_on_fifth_failure(
        self,
    ) -> None:
        """Lock a username after five failed attempts."""
        for _attempt in range(
            settings.AXES_FAILURE_LIMIT - 1
        ):
            response = self._post_login(
                username=self.user.username,
                password=WRONG_PASSWORD,
            )

            self.assertEqual(
                response.status_code,
                200,
            )

        response = self._post_login(
            username=self.user.username,
            password=WRONG_PASSWORD,
        )

        self.assertEqual(
            response.status_code,
            429,
        )
        self.assertTemplateUsed(
            response,
            "accounts/login_lockout.html",
        )
        self.assertIn(
            "Retry-After",
            response.headers,
        )

        retry_after_seconds = int(
            response.headers["Retry-After"]
        )

        self.assertGreater(
            retry_after_seconds,
            0,
        )
        self.assertLessEqual(
            retry_after_seconds,
            int(
                settings.AXES_COOLOFF_TIME.total_seconds()
            ),
        )

        retry_after_minutes = response.context[
            "retry_after_minutes"
        ]

        self.assertIsNotNone(
            retry_after_minutes
        )
        self.assertGreaterEqual(
            retry_after_minutes,
            1,
        )
        self.assertLessEqual(
            retry_after_minutes,
            ceil(
                settings.AXES_COOLOFF_TIME.total_seconds()
                / 60
            ),
        )

    def test_locked_username_remains_locked_from_another_ip(
        self,
    ) -> None:
        """Apply the username lockout independently of IP."""
        for attempt_number in range(
            settings.AXES_FAILURE_LIMIT
        ):
            response = self._post_login(
                username=self.user.username,
                password=WRONG_PASSWORD,
                ip_address=(
                    f"192.0.2.{attempt_number + 1}"
                ),
            )

            expected_status = (
                429
                if attempt_number
                == settings.AXES_FAILURE_LIMIT - 1
                else 200
            )

            self.assertEqual(
                response.status_code,
                expected_status,
            )

        response = self._post_login(
            username=self.user.username,
            password=TEST_PASSWORD,
            ip_address="198.51.100.25",
        )

        self.assertEqual(
            response.status_code,
            429,
        )

    def test_lockout_does_not_block_another_username(
        self,
    ) -> None:
        """Allow another username from the same address."""
        shared_ip = "192.0.2.50"

        for attempt_number in range(
            settings.AXES_FAILURE_LIMIT
        ):
            response = self._post_login(
                username=self.user.username,
                password=WRONG_PASSWORD,
                ip_address=shared_ip,
            )

            expected_status = (
                429
                if attempt_number
                == settings.AXES_FAILURE_LIMIT - 1
                else 200
            )

            self.assertEqual(
                response.status_code,
                expected_status,
            )

        response = self._post_login(
            username=self.other_user.username,
            password=TEST_PASSWORD,
            ip_address=shared_ip,
        )

        self.assertRedirects(
            response,
            self.home_url,
            fetch_redirect_response=False,
        )

    def test_successful_login_resets_previous_failures(
        self,
    ) -> None:
        """Clear accumulated failures after successful login."""
        for _attempt in range(
            settings.AXES_FAILURE_LIMIT - 1
        ):
            response = self._post_login(
                username=self.user.username,
                password=WRONG_PASSWORD,
            )

            self.assertEqual(
                response.status_code,
                200,
            )

        response = self._post_login(
            username=self.user.username,
            password=TEST_PASSWORD,
        )

        self.assertRedirects(
            response,
            self.home_url,
            fetch_redirect_response=False,
        )

        self.client.logout()

        for _attempt in range(
            settings.AXES_FAILURE_LIMIT - 1
        ):
            response = self._post_login(
                username=self.user.username,
                password=WRONG_PASSWORD,
            )

            self.assertEqual(
                response.status_code,
                200,
            )

        response = self._post_login(
            username=self.user.username,
            password=WRONG_PASSWORD,
        )

        self.assertEqual(
            response.status_code,
            429,
        )

    def test_locked_attempt_does_not_restart_cool_off(
        self,
    ) -> None:
        """Preserve the original expiry after another locked attempt."""
        response: HttpResponse | None = None

        for attempt_number in range(
            settings.AXES_FAILURE_LIMIT
        ):
            response = self._post_login(
                username=self.user.username,
                password=WRONG_PASSWORD,
            )

            expected_status = (
                429
                if attempt_number
                == settings.AXES_FAILURE_LIMIT - 1
                else 200
            )

            self.assertEqual(
                response.status_code,
                expected_status,
            )

        self.assertIsNotNone(
            response
        )

        access_attempt = (
            AccessAttempt.objects  # pylint: disable=no-member
            .filter(
                username=self.user.username,
            )
            .latest("attempt_time")
        )

        original_attempt_time = (
            access_attempt.attempt_time
        )
        original_retry_after = int(
            response.headers["Retry-After"]
        )

        response = self._post_login(
            username=self.user.username,
            password=TEST_PASSWORD,
        )

        self.assertEqual(
            response.status_code,
            429,
        )
        self.assertIn(
            "Retry-After",
            response.headers,
        )

        access_attempt.refresh_from_db()

        self.assertEqual(
            access_attempt.attempt_time,
            original_attempt_time,
        )
        self.assertLessEqual(
            int(response.headers["Retry-After"]),
            original_retry_after,
        )
