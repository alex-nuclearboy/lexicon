"""Tests for the application access policy."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser, Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from accounts.access import can_access_application
from accounts.models import ApplicationPermissions


User = get_user_model()


class ApplicationPermissionsPolicyTests(TestCase):
    """Verify every supported path through the access policy."""

    @classmethod
    def setUpTestData(cls) -> None:
        """Create reusable users and the custom application permission."""
        content_type = ContentType.objects.get_for_model(
            ApplicationPermissions,
            for_concrete_model=False,
        )
        cls.access_permission = Permission.objects.get(
            content_type=content_type,
            codename="access_application",
        )
        cls.user = User.objects.create_user(
            username="member",
            password="A-secure-test-password-123!",
        )

    def test_none_is_denied(self) -> None:
        """Return false when no user is available."""
        self.assertFalse(can_access_application(None))

    def test_anonymous_user_is_denied(self) -> None:
        """Return false for an anonymous user."""
        self.assertFalse(
            can_access_application(AnonymousUser())
        )

    def test_active_user_without_permission_is_denied(self) -> None:
        """Return false for an active user without application access."""
        self.assertFalse(can_access_application(self.user))

    def test_inactive_superuser_is_denied(self) -> None:
        """Require an account to be active even when it is a superuser."""
        user = User.objects.create_superuser(
            username="inactive-admin",
            password="A-secure-test-password-123!",
            is_active=False,
        )

        self.assertFalse(can_access_application(user))

    def test_active_superuser_is_allowed(self) -> None:
        """Allow an active superuser without the custom permission."""
        user = User.objects.create_superuser(
            username="admin",
            password="A-secure-test-password-123!",
        )

        self.assertTrue(can_access_application(user))

    def test_direct_permission_grants_access(self) -> None:
        """Allow a user who receives the permission directly."""
        self.user.user_permissions.add(self.access_permission)
        user = User.objects.get(pk=self.user.pk)

        self.assertTrue(can_access_application(user))

    def test_group_permission_grants_access(self) -> None:
        """Allow a user who inherits the permission from a group."""
        group = Group.objects.create(name="Vocabio users")
        group.permissions.add(self.access_permission)
        self.user.groups.add(group)
        user = User.objects.get(pk=self.user.pk)

        self.assertTrue(can_access_application(user))
