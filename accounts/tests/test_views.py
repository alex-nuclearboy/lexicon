"""Integration tests for the authentication views."""

from django.contrib.auth import (
    REDIRECT_FIELD_NAME,
    get_user_model,
)
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.messages import get_messages
from django.core.exceptions import NON_FIELD_ERRORS
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from accounts.models import ApplicationAccess
from accounts.ui_messages import (
    APPLICATION_ACCESS_DENIED,
    LOGIN_SUCCESSFUL,
    LOGOUT_SUCCESSFUL,
    PASSWORD_CHANGE_SUCCESSFUL,
)


User = get_user_model()

TEST_PASSWORD = "A-secure-test-password-123!"

TEST_CHANGE_PASSWORD = (
    "Another-secure-test-password-456!"
)

TEST_STORAGES = {
    "default": {
        "BACKEND": (
            "django.core.files.storage.FileSystemStorage"
        ),
    },
    "staticfiles": {
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage"
        ),
    },
}


@override_settings(STORAGES=TEST_STORAGES)
class AuthenticationViewTests(TestCase):
    """Verify login and logout behaviour through real HTTP requests."""

    @classmethod
    def setUpTestData(cls) -> None:
        """Create reusable accounts and the application permission."""
        content_type = ContentType.objects.get_for_model(
            ApplicationAccess,
            for_concrete_model=False,
        )
        access_permission = Permission.objects.get(
            content_type=content_type,
            codename="access_application",
        )

        cls.allowed_user = User.objects.create_user(
            username="member",
            password=TEST_PASSWORD,
        )
        cls.allowed_user.user_permissions.add(
            access_permission
        )

        cls.denied_user = User.objects.create_user(
            username="restricted",
            password=TEST_PASSWORD,
        )

        cls.superuser = User.objects.create_superuser(
            username="admin",
            password=TEST_PASSWORD,
        )

    def setUp(self) -> None:
        """Resolve the authentication URLs used by every test."""
        self.login_url = reverse("accounts:login")
        self.logout_url = reverse("accounts:logout")
        self.home_url = reverse("core:home")

    def assert_response_prevents_caching(
        self,
        response,
    ) -> None:
        """Assert that an authentication response is not cacheable."""
        cache_control = response.headers.get(
            "Cache-Control",
            "",
        )

        for directive in (
            "no-cache",
            "no-store",
            "must-revalidate",
            "private",
        ):
            with self.subTest(directive=directive):
                self.assertIn(
                    directive,
                    cache_control,
                )

    def test_login_page_is_available(self) -> None:
        """Render the login page for an anonymous user."""
        response = self.client.get(self.login_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "accounts/login.html",
        )
        self.assertIn("form", response.context)

    def test_empty_login_submission_shows_required_errors(
        self,
    ) -> None:
        """Show field errors when the login form is submitted empty."""
        response = self.client.post(
            self.login_url,
            {},
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn(
            "_auth_user_id",
            self.client.session,
        )

        form = response.context["form"]

        self.assertTrue(form.is_bound)
        self.assertTrue(
            form.has_error(
                "username",
                code="required",
            )
        )
        self.assertTrue(
            form.has_error(
                "password",
                code="required",
            )
        )

        self.assertContains(
            response,
            "Username is required.",
        )
        self.assertContains(
            response,
            "Password is required.",
        )

    def test_login_rejects_unsupported_http_methods(
        self,
    ) -> None:
        """Allow only GET and POST requests to the login view."""
        requests = (
            self.client.put,
            self.client.patch,
            self.client.delete,
        )

        for request_method in requests:
            with self.subTest(
                method=request_method.__name__.upper(),
            ):
                response = request_method(self.login_url)

                self.assertEqual(
                    response.status_code,
                    405,
                )

    def test_login_response_prevents_caching(self) -> None:
        """Prevent browsers from caching the login page."""
        response = self.client.get(self.login_url)

        self.assert_response_prevents_caching(response)

    def test_valid_credentials_start_session_and_record_log(
        self,
    ) -> None:
        """Authenticate an authorised user and record the event."""
        with self.assertLogs(
            "vocabio.audit.accounts.views",
            level="INFO",
        ) as captured_logs:
            response = self.client.post(
                self.login_url,
                {
                    "username": self.allowed_user.username,
                    "password": TEST_PASSWORD,
                },
            )

        self.assertRedirects(
            response,
            self.home_url,
            fetch_redirect_response=False,
        )
        self.assertEqual(
            self.client.session.get("_auth_user_id"),
            str(self.allowed_user.pk),
        )

        self.assertEqual(
            len(captured_logs.output),
            1,
        )
        self.assertIn(
            "[AUTH|LOGIN]",
            captured_logs.output[0],
        )
        self.assertIn(
            "username=member",
            captured_logs.output[0],
        )
        self.assertIn(
            f"user_id={self.allowed_user.pk}",
            captured_logs.output[0],
        )
        self.assertIn(
            "ip=127.0.0.1",
            captured_logs.output[0],
        )

        message_texts = [
            str(message)
            for message in get_messages(
                response.wsgi_request
            )
        ]

        self.assertIn(
            str(LOGIN_SUCCESSFUL),
            message_texts,
        )

    def test_invalid_credentials_are_rejected_and_logged(
        self,
    ) -> None:
        """Reject invalid credentials without creating a session."""
        with self.assertLogs(
            "vocabio.audit.accounts.views",
            level="WARNING",
        ) as captured_logs:
            response = self.client.post(
                self.login_url,
                {
                    "username": self.allowed_user.username,
                    "password": "incorrect-password",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn(
            "_auth_user_id",
            self.client.session,
        )

        form = response.context["form"]

        self.assertTrue(
            form.has_error(
                NON_FIELD_ERRORS,
                code="invalid_login",
            )
        )

        self.assertEqual(
            len(captured_logs.output),
            1,
        )
        self.assertIn(
            "[AUTH|FAILED]",
            captured_logs.output[0],
        )
        self.assertIn(
            "ip=127.0.0.1",
            captured_logs.output[0],
        )
        self.assertNotIn(
            TEST_PASSWORD,
            captured_logs.output[0],
        )

    def test_user_without_access_is_rejected_and_logged(
        self,
    ) -> None:
        """Reject valid credentials when application access is absent."""
        with self.assertLogs(
            "vocabio.audit.accounts.forms",
            level="WARNING",
        ) as captured_logs:
            response = self.client.post(
                self.login_url,
                {
                    "username": self.denied_user.username,
                    "password": TEST_PASSWORD,
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn(
            "_auth_user_id",
            self.client.session,
        )

        form = response.context["form"]

        self.assertTrue(
            form.has_error(
                NON_FIELD_ERRORS,
                code="access_denied",
            )
        )
        self.assertIn(
            str(APPLICATION_ACCESS_DENIED),
            [
                str(error)
                for error in form.non_field_errors()
            ],
        )

        self.assertEqual(
            len(captured_logs.output),
            1,
        )
        self.assertIn(
            "[AUTH|DENIED]",
            captured_logs.output[0],
        )
        self.assertIn(
            "username=restricted",
            captured_logs.output[0],
        )
        self.assertIn(
            f"user_id={self.denied_user.pk}",
            captured_logs.output[0],
        )
        self.assertIn(
            "ip=127.0.0.1",
            captured_logs.output[0],
        )

    def test_superuser_can_log_in(self) -> None:
        """Allow an active superuser without the custom permission."""
        with self.assertLogs(
            "vocabio.audit.accounts.views",
            level="INFO",
        ):
            response = self.client.post(
                self.login_url,
                {
                    "username": self.superuser.username,
                    "password": TEST_PASSWORD,
                },
            )

        self.assertRedirects(
            response,
            self.home_url,
            fetch_redirect_response=False,
        )
        self.assertEqual(
            self.client.session.get("_auth_user_id"),
            str(self.superuser.pk),
        )

    def test_safe_next_is_used_after_login(self) -> None:
        """Redirect an authorised user to a safe requested URL."""
        next_url = "/requested-page/?source=login"

        with self.assertLogs(
            "vocabio.audit.accounts.views",
            level="INFO",
        ):
            response = self.client.post(
                self.login_url,
                {
                    "username": self.allowed_user.username,
                    "password": TEST_PASSWORD,
                    REDIRECT_FIELD_NAME: next_url,
                },
            )

        self.assertRedirects(
            response,
            next_url,
            fetch_redirect_response=False,
        )

    def test_external_next_is_ignored(self) -> None:
        """Ignore a redirect target that points to another host."""
        with self.assertLogs(
            "vocabio.audit.accounts.views",
            level="INFO",
        ):
            response = self.client.post(
                self.login_url,
                {
                    "username": self.allowed_user.username,
                    "password": TEST_PASSWORD,
                    REDIRECT_FIELD_NAME: (
                        "https://example.com/"
                    ),
                },
            )

        self.assertRedirects(
            response,
            self.home_url,
            fetch_redirect_response=False,
        )

    def test_next_is_preserved_after_failed_login(
        self,
    ) -> None:
        """Keep the requested destination after a form error."""
        next_url = "/requested-page/?source=retry"

        with self.assertLogs(
            "vocabio.audit.accounts.views",
            level="WARNING",
        ):
            response = self.client.post(
                self.login_url,
                {
                    "username": self.allowed_user.username,
                    "password": "incorrect-password",
                    REDIRECT_FIELD_NAME: next_url,
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context[REDIRECT_FIELD_NAME],
            next_url,
        )
        self.assertContains(
            response,
            'name="next"',
        )
        self.assertContains(
            response,
            f'value="{next_url}"',
        )

    def test_authorised_user_is_redirected_away_from_login(
        self,
    ) -> None:
        """Redirect an already authorised user without showing the form."""
        next_url = "/requested-page/"

        allowed_user = User.objects.get(
            pk=self.allowed_user.pk
        )
        self.client.force_login(allowed_user)

        response = self.client.get(
            self.login_url,
            {
                REDIRECT_FIELD_NAME: next_url,
            },
        )

        self.assertRedirects(
            response,
            next_url,
            fetch_redirect_response=False,
        )

    def test_login_requires_csrf_token(self) -> None:
        """Reject a login POST request without a CSRF token."""
        csrf_client = Client(
            enforce_csrf_checks=True
        )

        response = csrf_client.post(
            self.login_url,
            {
                "username": self.allowed_user.username,
                "password": TEST_PASSWORD,
            },
        )

        self.assertEqual(response.status_code, 403)
        self.assertNotIn(
            "_auth_user_id",
            csrf_client.session,
        )

    def test_logout_rejects_get_requests(self) -> None:
        """Reject logout attempts made through a GET request."""
        self.client.force_login(self.allowed_user)

        response = self.client.get(self.logout_url)

        self.assertEqual(response.status_code, 405)
        self.assertIn(
            "_auth_user_id",
            self.client.session,
        )

    def test_logout_ends_session_and_records_log(
        self,
    ) -> None:
        """End the session through POST and record the event."""
        self.client.force_login(self.allowed_user)

        with self.assertLogs(
            "vocabio.audit.accounts.views",
            level="INFO",
        ) as captured_logs:
            response = self.client.post(
                self.logout_url
            )

        self.assertRedirects(
            response,
            self.home_url,
            fetch_redirect_response=False,
        )
        self.assertNotIn(
            "_auth_user_id",
            self.client.session,
        )

        self.assertEqual(
            len(captured_logs.output),
            1,
        )
        self.assertIn(
            "[AUTH|LOGOUT]",
            captured_logs.output[0],
        )
        self.assertIn(
            "username=member",
            captured_logs.output[0],
        )
        self.assertIn(
            f"user_id={self.allowed_user.pk}",
            captured_logs.output[0],
        )
        self.assertIn(
            "ip=127.0.0.1",
            captured_logs.output[0],
        )

        message_texts = [
            str(message)
            for message in get_messages(
                response.wsgi_request
            )
        ]

        self.assertIn(
            str(LOGOUT_SUCCESSFUL),
            message_texts,
        )

    def test_logout_response_prevents_caching(self) -> None:
        """Prevent browsers from caching a logout response."""
        self.client.force_login(self.allowed_user)

        with self.assertLogs(
            "vocabio.audit.accounts.views",
            level="INFO",
        ):
            response = self.client.post(
                self.logout_url
            )

        self.assert_response_prevents_caching(response)

    def test_logout_requires_csrf_token(self) -> None:
        """Reject a logout POST request without a CSRF token."""
        csrf_client = Client(
            enforce_csrf_checks=True
        )
        csrf_client.force_login(self.allowed_user)

        response = csrf_client.post(
            self.logout_url
        )

        self.assertEqual(response.status_code, 403)
        self.assertIn(
            "_auth_user_id",
            csrf_client.session,
        )

        def test_authenticated_header_contains_account_menu(
            self,
        ) -> None:
            """Show account actions to an authenticated user."""
            self.client.force_login(self.allowed_user)

            response = self.client.get(self.home_url)

            self.assertEqual(
                response.status_code,
                200,
            )
            self.assertContains(
                response,
                "data-header-menu-toggle",
            )
            self.assertContains(
                response,
                reverse("accounts:password_change"),
            )
            self.assertContains(
                response,
                reverse("accounts:logout"),
            )
            self.assertContains(
                response,
                "Change password",
            )
            self.assertContains(
                response,
                "Log out",
            )


        def test_anonymous_header_hides_account_menu(
            self,
        ) -> None:
            """Hide authenticated account actions from anonymous users."""
            response = self.client.get(self.home_url)

            self.assertEqual(
                response.status_code,
                200,
            )
            self.assertNotContains(
                response,
                "data-header-menu-toggle",
            )
            self.assertNotContains(
                response,
                reverse("accounts:password_change"),
            )
            self.assertContains(
                response,
                reverse("accounts:login"),
            )
            self.assertContains(
                response,
                "Log in",
            )


@override_settings(STORAGES=TEST_STORAGES)
class PasswordChangeViewTests(TestCase):
    """Verify self-service password change behaviour."""

    @classmethod
    def setUpTestData(cls) -> None:
        """Create a user with application access."""
        content_type = ContentType.objects.get_for_model(
            ApplicationAccess,
            for_concrete_model=False,
        )
        access_permission = Permission.objects.get(
            content_type=content_type,
            codename="access_application",
        )

        cls.user = User.objects.create_user(
            username="password-member",
            password=TEST_PASSWORD,
        )
        cls.user.user_permissions.add(
            access_permission
        )

    def setUp(self) -> None:
        """Resolve URLs used by password change tests."""
        self.password_change_url = reverse(
            "accounts:password_change"
        )
        self.login_url = reverse(
            "accounts:login"
        )
        self.home_url = reverse(
            "core:home"
        )

    def test_password_change_requires_authentication(
        self,
    ) -> None:
        """Redirect an anonymous user to the login page."""
        response = self.client.get(
            self.password_change_url
        )

        self.assertRedirects(
            response,
            (
                f"{self.login_url}"
                f"?next={self.password_change_url}"
            ),
            fetch_redirect_response=False,
        )

    def test_password_change_page_is_available(
        self,
    ) -> None:
        """Render the password change form for an authorised user."""
        self.client.force_login(self.user)

        response = self.client.get(
            self.password_change_url
        )

        self.assertEqual(
            response.status_code,
            200,
        )
        self.assertTemplateUsed(
            response,
            "accounts/password_change.html",
        )
        self.assertIn(
            "form",
            response.context,
        )
        self.assertEqual(
            response.context["form"].user,
            self.user,
        )

    def test_valid_password_change_updates_password(
        self,
    ) -> None:
        """Change the password and preserve the current session."""
        self.client.force_login(self.user)

        with self.assertLogs(
            "vocabio.audit.accounts.views",
            level="INFO",
        ) as captured_logs:
            response = self.client.post(
                self.password_change_url,
                {
                    "old_password": TEST_PASSWORD,
                    "new_password1": TEST_CHANGE_PASSWORD,
                    "new_password2": TEST_CHANGE_PASSWORD,
                },
            )

        self.assertRedirects(
            response,
            self.home_url,
            fetch_redirect_response=False,
        )

        self.user.refresh_from_db()

        self.assertFalse(
            self.user.check_password(
                TEST_PASSWORD
            )
        )
        self.assertTrue(
            self.user.check_password(
                TEST_CHANGE_PASSWORD
            )
        )

        self.assertEqual(
            self.client.session.get(
                "_auth_user_id"
            ),
            str(self.user.pk),
        )

        self.assertEqual(
            len(captured_logs.output),
            1,
        )
        self.assertIn(
            "[AUTH|PASSWORD_CHANGE]",
            captured_logs.output[0],
        )
        self.assertIn(
            "username=password-member",
            captured_logs.output[0],
        )
        self.assertIn(
            f"user_id={self.user.pk}",
            captured_logs.output[0],
        )
        self.assertIn(
            "ip=127.0.0.1",
            captured_logs.output[0],
        )
        self.assertNotIn(
            TEST_PASSWORD,
            captured_logs.output[0],
        )
        self.assertNotIn(
            TEST_CHANGE_PASSWORD,
            captured_logs.output[0],
        )

        message_texts = [
            str(message)
            for message in get_messages(
                response.wsgi_request
            )
        ]

        self.assertIn(
            str(PASSWORD_CHANGE_SUCCESSFUL),
            message_texts,
        )

    def test_incorrect_current_password_is_rejected(
        self,
    ) -> None:
        """Reject a password change with an incorrect current password."""
        self.client.force_login(self.user)

        response = self.client.post(
            self.password_change_url,
            {
                "old_password": "incorrect-password",
                "new_password1": TEST_CHANGE_PASSWORD,
                "new_password2": TEST_CHANGE_PASSWORD,
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        form = response.context["form"]

        self.assertTrue(
            form.has_error("old_password")
        )

        self.user.refresh_from_db()

        self.assertTrue(
            self.user.check_password(
                TEST_PASSWORD
            )
        )
        self.assertFalse(
            self.user.check_password(
                TEST_CHANGE_PASSWORD
            )
        )

    def test_mismatched_new_passwords_are_rejected(
        self,
    ) -> None:
        """Reject new password values that do not match."""
        self.client.force_login(self.user)

        response = self.client.post(
            self.password_change_url,
            {
                "old_password": TEST_PASSWORD,
                "new_password1": TEST_CHANGE_PASSWORD,
                "new_password2": (
                    "Different-secure-password-789!"
                ),
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        form = response.context["form"]

        self.assertTrue(
            form.has_error("new_password2")
        )

        self.user.refresh_from_db()

        self.assertTrue(
            self.user.check_password(
                TEST_PASSWORD
            )
        )

    def test_password_change_requires_csrf_token(
        self,
    ) -> None:
        """Reject password changes without a CSRF token."""
        csrf_client = Client(
            enforce_csrf_checks=True
        )
        csrf_client.force_login(self.user)

        response = csrf_client.post(
            self.password_change_url,
            {
                "old_password": TEST_PASSWORD,
                "new_password1": TEST_CHANGE_PASSWORD,
                "new_password2": TEST_CHANGE_PASSWORD,
            },
        )

        self.assertEqual(
            response.status_code,
            403,
        )

        self.user.refresh_from_db()

        self.assertTrue(
            self.user.check_password(
                TEST_PASSWORD
            )
        )

    def test_password_change_rejects_unsupported_methods(
        self,
    ) -> None:
        """Allow only GET and POST password change requests."""
        self.client.force_login(self.user)

        requests = (
            self.client.put,
            self.client.patch,
            self.client.delete,
        )

        for request_method in requests:
            with self.subTest(
                method=request_method.__name__.upper(),
            ):
                response = request_method(
                    self.password_change_url
                )

                self.assertEqual(
                    response.status_code,
                    405,
                )
